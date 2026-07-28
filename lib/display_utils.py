#!/usr/bin/env python3
"""
DISPLAY_UTILS.PY - Display Detection
=====================================
Detects displays and sets up pygame for correct monitor using xrandr.
"""

import subprocess
import re
import ctypes
import ctypes.util


def get_display_info():
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

                mode_match = re.search(r'(\d+\.\d+)Hz', line)
                if mode_match and 'refresh_rate' not in current_display:
                    if '*current' in line:
                        current_display['refresh_rate'] = float(mode_match.group(1))

        if current_display:
            displays.append(current_display)

    except Exception as e:
        print(f"Error getting display info: {e}")

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
