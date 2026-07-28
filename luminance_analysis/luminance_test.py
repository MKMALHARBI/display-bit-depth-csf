#!/usr/bin/env python3
"""
LUMINANCE TEST TOOL
===================
Compares 8-bit, 10-bit, 10-bit HDR off, and 8-bit + temporal-dither output.

Steps through every 10-bit value 504-520 (17 patches).
  - 8-bit:         sends 8-bit codes 126-130 (val_10 >> 2).
  - 10-bit:        sends 10-bit codes via 10:10:10:2 framebuffer.
  - 10-bit HDR off: identical code path to 10-bit; separate mode tag so
                   the run made with the monitor's HDR setting disabled
                   is saved to its own CSV for comparison.
  - Dither:        sends 8-bit codes only, alternating between the two
                   nearest codes each frame via an error-diffusion
                   accumulator so the time-averaged output matches the
                   10-bit target.
  - DAC carry:     sends 10-bit codes clustered around the 1/4, 1/2 and
                   3/4 scale binary-carry transitions (256, 512, 768),
                   probing the converter's differential non-linearity
                   where the most bits flip at once.

Usage:
    python3 luminance_test.py
"""

import sys
import os
import csv
import glfw
import tkinter as tk
from tkinter import ttk
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.display_utils import print_all_displays, setup_display_for_glfw, DisplayCalibration
from lib.gl_renderer import GLRenderer


# ---------------------------------------------------------------
# Patches: (8-bit value, 10-bit value)
# ---------------------------------------------------------------
PATCHES = [
    (0, 0),
    (126, 504),
    (126, 505),
    (126, 506),
    (126, 507),
    (127, 508),
    (127, 509),
    (127, 510),
    (127, 511),
    (128, 512),
    (128, 513),
    (128, 514),
    (128, 515),
    (129, 516),
    (129, 517),
    (129, 518),
    (129, 519),
    (130, 520),
    (255, 1023),
]


# ---------------------------------------------------------------
# DAC carry / DNL test: 10-bit codes clustered around the major
# binary-carry transitions, where a converter's differential
# non-linearity is largest.
#   512  = 1/2 scale  -> MSB (bit 9) carries: 01_1111_1111 -> 10_0000_0000
#   256  = 1/4 scale  -> bit 8 carries:       00_1111_1111 -> 01_0000_0000
#   768  = 3/4 scale  -> bit 8 carries:       10_1111_1111 -> 11_0000_0000
# Each cluster spans CARRY_SPAN codes either side of the carry so the
# slope before and after the transition is captured as well.
# ---------------------------------------------------------------
CARRY_CENTERS = [256, 512, 768]
CARRY_SPAN = 4


# ---------------------------------------------------------------
# Participant detection-threshold averages. The calibration task
# (step1_calibration.py) showed the letter at 0.498 + threshold_linear/255
# on a 0.498 mid-gray background. These are the across-participant mean
# letter shades (normalised 0-1), computed by threshold_gray_average.py
# over Data/: the 8-bit average lands on 8-bit code 127.45 and the 10-bit
# average on 10-bit code 510.87. Measure each with the panel in the
# matching bit depth.
# ---------------------------------------------------------------
THRESHOLD_AVG = {
    "threshold_8bit":  {"value": 127.45, "gray": 0.499812},
    "threshold_10bit": {"value": 510.87, "gray": 0.499389},
}


def carry_codes():
    """10-bit codes for the carry/DNL test, low to high, no duplicates."""
    codes = set()
    for center in CARRY_CENTERS:
        for c in range(center - CARRY_SPAN, center + CARRY_SPAN + 1):
            codes.add(c)
    return sorted(codes)


def get_user_choices():
    """Ask user to choose a test from a dropdown list."""
    tests = [
        ("8-bit",                   "8bit"),
        ("8-bit HDR off",           "8bit_hdr_off"),
        ("10-bit",                  "10bit"),
        ("10-bit HDR off",          "10bit_hdr_off"),
        ("10-bit (monitor 8-bit)",  "10bit_mon8bit"),
        ("8-bit + temporal dither", "dither"),
        ("DAC carry / DNL test",    "carry"),
        ("Threshold avg (8-bit)",   "threshold_8bit"),
        ("Threshold avg (10-bit)",  "threshold_10bit"),
    ]
    labels = [t[0] for t in tests]

    root = tk.Tk()
    root.title("Luminance Test")
    root.geometry("320x140")

    choice = {"mode": None}

    tk.Label(root, text="Select test:", pady=10, font=("Arial", 12)).pack()

    var = tk.StringVar(value=labels[0])
    combo = ttk.Combobox(root, textvariable=var, values=labels,
                         state="readonly", width=30)
    combo.pack(pady=5)

    def on_ok():
        choice["mode"] = dict(tests)[var.get()]
        root.quit()

    tk.Button(root, text="OK", width=12, command=on_ok).pack(pady=10)

    root.mainloop()
    try:
        root.destroy()
    except tk.TclError:
        pass
    return choice["mode"]


def draw_aim_square(renderer, width, height, measurement_num):
    """Draw one red outline square at the position for the current measurement.
    Order: 1=center, 2=right, 3=left."""
    sq_size = 270
    sq_y = height // 2 - sq_size // 2
    positions = {
        1: width // 2 - sq_size // 2,            # center
        2: width // 2 - sq_size // 2,            # center
        3: width // 2 - sq_size // 2,            # center
    }
    sq_x = positions[measurement_num]
    renderer.draw_rect_outline_color(sq_x, sq_y, sq_size, sq_size, 1.0, 0.0, 0.0, 2)


def show_positioning_screen(renderer, font_path, width, height, bg_gray=0.498):
    """Show a setup screen so the operator can aim the CS-160 at the
    center of the patch before starting the run. Draws the 270-px patch
    outline, a centered crosshair, and a small marker representing the
    expected meter spot size (~16 px = 2.9 mm on a 0.185 mm/px panel
    using the No.153 close-up lens at 700 mm)."""
    text_color = 0.1  # constant across patches; keeps average picture level stable
    sq_size = 270
    sq_x = width // 2 - sq_size // 2
    sq_y = height // 2 - sq_size // 2
    cx, cy = width // 2, height // 2

    while True:
        renderer.clear(bg_gray)

        renderer.draw_rect_outline_color(sq_x, sq_y, sq_size, sq_size, 1.0, 0.0, 0.0, 2)

        renderer.draw_rect_color(cx - 25, cy - 1, 50, 2, 1.0, 0.0, 0.0)
        renderer.draw_rect_color(cx - 1, cy - 25, 2, 50, 1.0, 0.0, 0.0)

        renderer.draw_rect_outline_color(cx - 8, cy - 8, 16, 16, 0.0, 1.0, 0.0, 1)

        renderer.draw_text_centered(font_path, "POSITION THE METER", cx, 40, 32, text_color)
        renderer.draw_text_centered(
            font_path,
            f"Aim CS-160 at the red crosshair. Center: ({cx}, {cy}) px.",
            cx, height - 130, 24, text_color
        )
        renderer.draw_text_centered(
            font_path,
            "Green box = expected meter spot (~2.9 mm). Must stay inside the red square.",
            cx, height - 100, 22, text_color
        )
        renderer.draw_text_centered(
            font_path,
            "Adjust tripod distance to 700 mm, then focus through the viewfinder.",
            cx, height - 70, 22, text_color
        )
        renderer.draw_text_centered(
            font_path,
            "SPACE = positioned, ready to start.  ESC = cancel.",
            cx, height - 35, 24, text_color
        )

        renderer.flip()
        key = renderer.wait_key()
        if key == glfw.KEY_ESCAPE:
            return False
        if key == glfw.KEY_SPACE:
            return True


def show_measure_screen(renderer, font_path, width, height, patch_num, total,
                        value, target_float, measurement_num, state):
    """Show the patch. SPACE = ready to enter reading. The red aim square
    is hidden by default and toggled with S, so its pixels cannot affect
    the meter reading. Re-draws every frame so dither can advance."""
    text_color = 0.1  # constant across patches; keeps average picture level stable
    show_square = False

    while True:
        gray = next_frame_gray(state)
        renderer.clear(gray)
        if show_square:
            draw_aim_square(renderer, width, height, measurement_num)

        renderer.draw_text_centered(
            font_path,
            f"Patch {patch_num}/{total}  |  Value: {value}  |  Float: {target_float:.6f}",
            width // 2, 30, 28, text_color
        )
        renderer.draw_text_centered(
            font_path,
            f"Measurement {measurement_num}/3 - S = show/hide aim square",
            width // 2, height - 70, 24, text_color
        )
        renderer.draw_text_centered(
            font_path,
            "Press SPACE after measuring to enter reading",
            width // 2, height - 35, 24, text_color
        )
        renderer.flip()

        key = renderer.poll_key()
        if key == glfw.KEY_ESCAPE:
            return False
        if key == glfw.KEY_S:
            show_square = not show_square
        if key == glfw.KEY_SPACE:
            return True


def get_reading_via_keyboard(renderer, font_path, width, height, patch_num, total,
                             value, target_float, measurement_num, state):
    """Get a luminance reading via keyboard input. Re-draws every frame so
    dither can advance."""
    input_str = ""
    # High-contrast against the patch so the prompt stays readable on dark
    # screens. This screen is shown after the meter reading is taken, so its
    # brightness does not affect the measurement.
    text_color = 0.9 if target_float < 0.5 else 0.1

    while True:
        gray = next_frame_gray(state)
        renderer.clear(gray)

        renderer.draw_text_centered(
            font_path,
            f"Patch {patch_num}/{total}  |  Value: {value}  |  Float: {target_float:.6f}",
            width // 2, 30, 28, text_color
        )

        renderer.draw_text_centered(
            font_path,
            f"Measurement {measurement_num}/3",
            width // 2, height // 2 - 60, 32, text_color
        )
        renderer.draw_text_centered(
            font_path,
            f"Type reading: {input_str}_",
            width // 2, height // 2, 36, text_color
        )
        renderer.draw_text_centered(
            font_path,
            "ENTER to confirm  |  BACKSPACE to delete  |  ESC to quit",
            width // 2, height // 2 + 60, 24, text_color
        )

        renderer.flip()

        key = renderer.poll_key()
        if key is None:
            continue
        if key == glfw.KEY_ESCAPE:
            return None

        if key == glfw.KEY_ENTER or key == glfw.KEY_KP_ENTER:
            if input_str:
                try:
                    return float(input_str)
                except ValueError:
                    input_str = ""
        elif key == glfw.KEY_BACKSPACE:
            input_str = input_str[:-1]
        elif key == glfw.KEY_PERIOD or key == glfw.KEY_KP_DECIMAL:
            if "." not in input_str:
                input_str += "."
        elif key == glfw.KEY_MINUS or key == glfw.KEY_KP_SUBTRACT:
            if not input_str:
                input_str = "-"
        else:
            num = None
            if glfw.KEY_0 <= key <= glfw.KEY_9:
                num = key - glfw.KEY_0
            elif glfw.KEY_KP_0 <= key <= glfw.KEY_KP_9:
                num = key - glfw.KEY_KP_0
            if num is not None:
                input_str += str(num)


def build_patch_list(mode):
    """Build list of (value, target_float, base_code, frac) for each patch.

    - 8bit:   value = 8-bit code,  target_float = value/255
    - 10bit:  value = 10-bit code, target_float = value/1023
    - dither: value = 10-bit code, target_float = value/1023,
              base_code = floor(target_float*255),
              frac = target_float*255 - base_code
              (used to alternate between base_code and base_code+1)
    """
    if mode in THRESHOLD_AVG:
        info = THRESHOLD_AVG[mode]
        gray = info["gray"]
        target_code = gray * 255.0
        base_code = int(target_code)
        frac = target_code - base_code
        return [(info["value"], gray, base_code, frac)]

    if mode == "carry":
        patches = []
        for val_10 in carry_codes():
            target_float = val_10 / 1023.0
            target_code = target_float * 255.0
            base_code = int(target_code)
            frac = target_code - base_code
            patches.append((val_10, target_float, base_code, frac))
        return patches

    patches = []
    seen_8bit = set()
    for val_8, val_10 in PATCHES:
        if mode in ("8bit", "8bit_hdr_off"):
            if val_8 in seen_8bit:
                continue
            seen_8bit.add(val_8)
            value = val_8
            target_float = value / 255.0
            base_code = value
            frac = 0.0
        else:
            value = val_10
            target_float = value / 1023.0
            target_code = target_float * 255.0
            base_code = int(target_code)
            frac = target_code - base_code
        patches.append((value, target_float, base_code, frac))
    return patches


def make_render_state(mode, target_float, base_code, frac):
    """Per-patch render state consumed by next_frame_gray()."""
    if mode == "dither":
        return {"mode": "dither", "base_code": base_code,
                "frac": frac, "acc": 0.0}
    return {"mode": "static", "gray": target_float}


def next_frame_gray(state):
    """Return the gray float to clear with this frame."""
    if state["mode"] != "dither":
        return state["gray"]
    state["acc"] += state["frac"]
    if state["acc"] >= 1.0:
        state["acc"] -= 1.0
        return (state["base_code"] + 1) / 255.0
    return state["base_code"] / 255.0


MODE_LABELS = {
    "8bit":          "8-BIT",
    "8bit_hdr_off":  "8-BIT HDR OFF",
    "10bit":         "10-BIT",
    "10bit_hdr_off": "10-BIT HDR OFF",
    "10bit_mon8bit": "10-BIT (MONITOR 8-BIT)",
    "dither":        "8-BIT + TEMPORAL DITHER",
    "carry":         "DAC CARRY / DNL TEST",
    "threshold_8bit":  "THRESHOLD AVG (8-BIT)",
    "threshold_10bit": "THRESHOLD AVG (10-BIT)",
}


def main():
    mode = get_user_choices()
    if mode is None:
        print("Cancelled.")
        return

    patches = build_patch_list(mode)
    total = len(patches)

    print(f"Luminance Test: {MODE_LABELS[mode]}, {total} patches")
    print_all_displays()

    DISPLAY_INDEX, width, height = setup_display_for_glfw()
    display_cal = DisplayCalibration(DISPLAY_INDEX)
    monitor_info = {
        'monitor_name': display_cal.info.get('name', 'unknown'),
        'resolution': f"{display_cal.info.get('resolution_w', '?')}x{display_cal.info.get('resolution_h', '?')}",
        'refresh_rate': display_cal.info.get('refresh_rate', 'unknown'),
        'brightness': display_cal.info.get('brightness', 'unknown'),
        'gamma_r': display_cal.info.get('gamma_r', 'unknown'),
        'gamma_g': display_cal.info.get('gamma_g', 'unknown'),
        'gamma_b': display_cal.info.get('gamma_b', 'unknown'),
    }
    print(f"Monitor: {monitor_info['monitor_name']}, {monitor_info['resolution']} @ {monitor_info['refresh_rate']}Hz")
    print(f"Brightness: {monitor_info['brightness']}, Gamma: {monitor_info['gamma_r']}/{monitor_info['gamma_g']}/{monitor_info['gamma_b']}")

    renderer = GLRenderer(width, height, monitor_index=DISPLAY_INDEX, fullscreen=False)
    width, height = renderer.width, renderer.height

    # Record actual framebuffer bit depth from OpenGL
    monitor_info['fb_red_bits'] = renderer.fb_red_bits
    monitor_info['fb_green_bits'] = renderer.fb_green_bits
    monitor_info['fb_blue_bits'] = renderer.fb_blue_bits
    print(f"Framebuffer: R={renderer.fb_red_bits} G={renderer.fb_green_bits} B={renderer.fb_blue_bits}")

    font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    renderer.load_font(font_path, 36)
    renderer.show_cursor()

    # Instructions
    renderer.clear(0.498)

    title = f"LUMINANCE TEST - {MODE_LABELS[mode]}"
    desc = "Different values per mode. Tight 10-bit steps."

    lines = [
        title,
        desc,
        "",
        f"Total patches: {total}",
        "",
        "For each patch:",
        "  - Press SPACE when ready",
        "  - Take 3 readings, type each + ENTER",
        "",
        "ESC = quit early",
        "",
        "Press any key to start."
    ]
    y = 100
    for line in lines:
        if line:
            renderer.draw_text_centered(font_path, line, width // 2, y, 28, 0.9)
        y += 38
    renderer.flip()

    key = renderer.wait_key()
    if key == glfw.KEY_ESCAPE:
        renderer.destroy()
        return

    if not show_positioning_screen(renderer, font_path, width, height):
        renderer.destroy()
        return

    results = []
    quit_early = False

    for i, (value, target_float, base_code, frac) in enumerate(patches):
        if quit_early:
            break

        state = make_render_state(mode, target_float, base_code, frac)

        measurements = []
        for m in range(1, 4):
            ok = show_measure_screen(
                renderer, font_path, width, height,
                i + 1, total, value, target_float, m, state
            )
            if not ok:
                quit_early = True
                break

            reading = get_reading_via_keyboard(
                renderer, font_path, width, height,
                i + 1, total, value, target_float, m, state
            )
            if reading is None:
                quit_early = True
                break
            measurements.append(reading)
            print(f"  Patch {i + 1}/{total} (value={value}, "
                  f"float={target_float:.6f}, mode={mode}): "
                  f"measurement {m} = {reading}")

        if quit_early:
            break

        results.append({
            "patch_number": i + 1,
            "mode": mode,
            "monitor_name": monitor_info['monitor_name'],
            "resolution": monitor_info['resolution'],
            "refresh_rate": monitor_info['refresh_rate'],
            "brightness": monitor_info['brightness'],
            "gamma_r": monitor_info['gamma_r'],
            "gamma_g": monitor_info['gamma_g'],
            "gamma_b": monitor_info['gamma_b'],
            "fb_red_bits": monitor_info['fb_red_bits'],
            "fb_green_bits": monitor_info['fb_green_bits'],
            "fb_blue_bits": monitor_info['fb_blue_bits'],
            "value": value,
            "target_float": f"{target_float:.6f}",
            "base_code": base_code,
            "frac": f"{frac:.6f}",
            "measurement_1": measurements[0],
            "measurement_2": measurements[1],
            "measurement_3": measurements[2],
            "mean": sum(measurements) / 3,
        })

    # Save CSV
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"luminance_{mode}_{timestamp}.csv"
        )
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "patch_number", "mode",
                "monitor_name", "resolution", "refresh_rate",
                "brightness", "gamma_r", "gamma_g", "gamma_b",
                "fb_red_bits", "fb_green_bits", "fb_blue_bits",
                "value", "target_float", "base_code", "frac",
                "measurement_1", "measurement_2", "measurement_3", "mean"
            ])
            writer.writeheader()
            writer.writerows(results)

        renderer.clear(0.498)
        renderer.draw_text_centered(font_path, "DONE!", width // 2, height // 2 - 60, 48, 0.9)
        renderer.draw_text_centered(font_path, f"Saved {len(results)} patches to:", width // 2, height // 2, 28, 0.9)
        renderer.draw_text_centered(font_path, os.path.basename(csv_path), width // 2, height // 2 + 40, 24, 0.9)
        renderer.draw_text_centered(font_path, "Press any key to exit.", width // 2, height // 2 + 100, 24, 0.9)
        renderer.flip()
        renderer.wait_key()

        print(f"\nResults saved to: {csv_path}")
    else:
        print("No measurements taken.")

    renderer.destroy()


if __name__ == "__main__":
    main()
