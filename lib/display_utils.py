#!/usr/bin/env python3
"""
DISPLAY_UTILS.PY - Display Detection
=====================================
Detects displays and sets up pygame for correct monitor using xrandr.
"""

import os
import sys
import subprocess
import re
import ctypes
import ctypes.util


def get_ui_font():
    """Return a path to a usable sans-serif TTF for the current OS.

    Tries a list of common fonts per platform and returns the first that
    exists. Windows ships Arial/Segoe UI; Linux commonly has Liberation or
    DejaVu; macOS has Helvetica/Arial. Falls back to the Linux path so the
    return value is never None.
    """
    candidates = [
        # Windows
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[3]


def get_display_info():
    """Detect connected displays on any OS.

    Linux uses xrandr (gives gamma/brightness too). Windows and macOS use
    GLFW, which is cross-platform and already a dependency. If the primary
    method yields nothing, the other is tried as a fallback.
    """
    if sys.platform.startswith('linux'):
        info = _get_display_info_xrandr()
        return info if info else _get_display_info_glfw()
    info = _get_display_info_glfw()
    return info if info else _get_display_info_xrandr()


def _get_display_info_glfw():
    """Detect displays via GLFW. Works on Windows, macOS and Linux.

    Provides name, resolution, position and refresh rate. Gamma and
    brightness are not exposed by GLFW, so they stay 'unknown' (matching the
    fields the experiment records)."""
    try:
        import glfw
    except Exception as e:
        print(f"Error getting display info (glfw import): {e}")
        return []

    if not glfw.init():
        print("Error getting display info: glfw.init() failed")
        return []

    displays = []
    try:
        primary = glfw.get_primary_monitor()
        for i, mon in enumerate(glfw.get_monitors()):
            mode = glfw.get_video_mode(mon)
            try:
                px, py = glfw.get_monitor_pos(mon)
            except Exception:
                px, py = 0, 0

            name = None
            try:
                name = glfw.get_monitor_name(mon)
                if isinstance(name, bytes):
                    name = name.decode('utf-8', 'replace')
            except Exception:
                pass

            d = {
                'name': name or f'Monitor {i}',
                'primary': (mon == primary),
                'resolution_w': mode.size.width,
                'resolution_h': mode.size.height,
                'pos_x': px,
                'pos_y': py,
                'refresh_rate': float(mode.refresh_rate),
            }
            try:
                wmm, hmm = glfw.get_monitor_physical_size(mon)
                if wmm:
                    d['width_mm'] = wmm
                if hmm:
                    d['height_mm'] = hmm
            except Exception:
                pass
            displays.append(d)
    except Exception as e:
        print(f"Error getting display info (glfw): {e}")

    return displays


def _get_display_info_xrandr():
    displays = []

    try:
        result = subprocess.run(['xrandr', '--verbose'], capture_output=True, text=True)
        output = result.stdout

        current_display = None
        for line in output.split('\n'):
            match = re.match(r'^(\S+)\s+connected\s*(primary)?\s*(\d+)x(\d+)\+(\d+)\+(\d+)', line)
            if match:
                if current_display:
                    displays.append(current_display)
                current_display = {
                    'name': match.group(1),
                    'primary': match.group(2) == 'primary',
                    'resolution_w': int(match.group(3)),
                    'resolution_h': int(match.group(4)),
                    'pos_x': int(match.group(5)),
                    'pos_y': int(match.group(6)),
                }
                size_match = re.search(r'(\d+)mm\s*x\s*(\d+)mm', line)
                if size_match:
                    current_display['width_mm'] = int(size_match.group(1))
                    current_display['height_mm'] = int(size_match.group(2))
                continue

            if current_display:
                gamma_match = re.match(r'\s*Gamma:\s*([\d.-]+):([\d.-]+):([\d.-]+)', line)
                if gamma_match:
                    current_display['gamma_r'] = float(gamma_match.group(1))
                    current_display['gamma_g'] = float(gamma_match.group(2))
                    current_display['gamma_b'] = float(gamma_match.group(3))

                bright_match = re.match(r'\s*Brightness:\s*([\d.-]+)', line)
                if bright_match:
                    current_display['brightness'] = float(bright_match.group(1))

                # Refresh rate spans two lines of `xrandr --verbose`:
                #
                #   3840x2160 (0x23) 1496.750MHz ... *current +preferred
                #         v: height 2160 start ... clock  119.86Hz
                #
                # The header carries *current but its only frequency is the pixel
                # clock in MHz; the vertical-timing line carries the actual refresh
                # but not *current. Requiring both on one line (as this did before)
                # can never match, so refresh_rate stayed unset and callers silently
                # fell back to 60 Hz -- halving stimulus duration on a 120 Hz panel.
                # Mark the current mode, then read the v: line that follows it.
                if '*current' in line:
                    current_display['_in_current_mode'] = True
                elif current_display.get('_in_current_mode'):
                    # The h: line sits between, so hold the flag until v: is seen.
                    v_match = re.match(r'\s*v:.*?clock\s+([\d.]+)Hz', line)
                    if v_match:
                        rate = float(v_match.group(1))
                        if 20.0 <= rate <= 400.0:
                            current_display['refresh_rate'] = rate
                        current_display.pop('_in_current_mode', None)

        if current_display:
            displays.append(current_display)

    except Exception as e:
        print(f"Error getting display info: {e}")

    for d in displays:
        d.pop('_in_current_mode', None)   # scratch key, keep it out of saved JSON

    return displays


def get_display_at_position(x, y):
    displays = get_display_info()
    for i, d in enumerate(displays):
        dx = d.get('pos_x', 0)
        dy = d.get('pos_y', 0)
        dw = d.get('resolution_w', 1920)
        dh = d.get('resolution_h', 1080)
        if dx <= x < dx + dw and dy <= y < dy + dh:
            return i
    return 0


def get_mouse_display():
    # Windows: read the cursor position via the Win32 API.
    if sys.platform == 'win32':
        try:
            class _POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = _POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return get_display_at_position(pt.x, pt.y)
        except Exception:
            pass
        return 0

    # Query X11 cursor position directly (no window creation, no flicker)
    try:
        _xlib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('X11'))
        _xlib.XOpenDisplay.restype = ctypes.c_void_p
        dpy = _xlib.XOpenDisplay(None)
        if dpy:
            root_win = _xlib.XDefaultRootWindow(dpy)
            root_ret = ctypes.c_ulong()
            child_ret = ctypes.c_ulong()
            rx, ry = ctypes.c_int(), ctypes.c_int()
            wx, wy = ctypes.c_int(), ctypes.c_int()
            mask = ctypes.c_uint()
            _xlib.XQueryPointer(
                dpy, root_win,
                ctypes.byref(root_ret), ctypes.byref(child_ret),
                ctypes.byref(rx), ctypes.byref(ry),
                ctypes.byref(wx), ctypes.byref(wy),
                ctypes.byref(mask))
            _xlib.XCloseDisplay(dpy)
            return get_display_at_position(rx.value, ry.value)
    except Exception:
        pass
    # Fallback: tkinter (may flash briefly on depth-30 X11)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        x = root.winfo_pointerx()
        y = root.winfo_pointery()
        root.destroy()
        return get_display_at_position(x, y)
    except Exception:
        pass
    return 0



class DisplayCalibration:

    def __init__(self, display_index=0):
        self.display_index = display_index
        displays = get_display_info()
        self.info = displays[display_index] if display_index < len(displays) else self._get_defaults()

    def _get_defaults(self):
        return {
            'name': 'Unknown',
            'resolution_w': 1920,
            'resolution_h': 1080,
            'refresh_rate': 60.0,
        }

    def get_corrected_fps(self):
        return int(round(self.info.get('refresh_rate', 60.0)))

    def print_report(self):
        """Print display info."""
        print("\n" + "=" * 60)
        print("DISPLAY INFO")
        print("=" * 60)
        print(f"Display: {self.info.get('name', 'Unknown')} (index {self.display_index})")
        print(f"Resolution: {self.info.get('resolution_w', '?')}x{self.info.get('resolution_h', '?')}")
        print(f"Refresh Rate: {self.info.get('refresh_rate', '?')} Hz")
        print("=" * 60 + "\n")

    def to_dict(self):
        """Export as dictionary for saving to JSON."""
        return {
            'display_index': self.display_index,
            'display_info': self.info,
        }


def print_all_displays():
    """Print info for all connected displays."""
    displays = get_display_info()
    print("\n" + "=" * 60)
    print(f"DETECTED {len(displays)} DISPLAY(S)")
    print("=" * 60)

    for i, d in enumerate(displays):
        print(f"\n[{i}] {d.get('name', 'Unknown')}" + (" (PRIMARY)" if d.get('primary') else ""))
        print(f"    Resolution: {d.get('resolution_w')}x{d.get('resolution_h')}")
        print(f"    Refresh:    {d.get('refresh_rate', '?')} Hz")


def setup_display_for_glfw(display_index=None):
    """Return (monitor_index, width, height) for GLFW window creation.

    Uses the same xrandr detection as the pygame helper but does not set
    any SDL environment variables.
    """
    if display_index is None:
        display_index = get_mouse_display()

    displays = get_display_info()
    if display_index < len(displays):
        d = displays[display_index]
        w = d.get('resolution_w', 1920)
        h = d.get('resolution_h', 1080)
    else:
        w, h = 1920, 1080

    return display_index, w, h


if __name__ == "__main__":
    print_all_displays()
