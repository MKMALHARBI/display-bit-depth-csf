# Supplementary Material: 8-bit vs 10-bit Display Configuration

This document describes the computer, display, and software configuration used to
present the experiment at **8-bit** and **10-bit** grayscale color depth. It is
supplementary material describing the apparatus; it is not an operating
procedure.

The experiment (`step1_calibration.py`, `step2_SR_experiment.py`,
`step3_SR_experiment.py`) presents low-contrast letters. At 8-bit depth the
display reproduces 256 gray levels (steps of 1/255 ≈ 0.39%); at 10-bit depth it
reproduces 1024 gray levels (steps of 1/1023 ≈ 0.10%). The two depths were the
manipulated display condition.

---

## 1. Computer

| Component | Specification |
|-----------|---------------|
| Host | Phoenix |
| CPU | AMD Ryzen 5 3600 (6 cores / 12 threads), x86_64 |
| Memory | 16 GB |
| GPU | NVIDIA GeForce RTX 2070 (TU106) |

## 2. Display

| Property | Value |
|----------|-------|
| Model | BenQ EX3210U (EDID serial ETA6P02919SL0) |
| Size | 4K panel, 710 mm × 400 mm |
| Connection | DisplayPort (port DP-2, primary) |
| Resolution | 3840 × 2160 |
| Refresh rate | 119.88 Hz (panel supports up to 144 Hz) |

The DisplayPort connection and the 10-bit-capable panel are what allow a 30-bit
(10-10-10) signal to be transmitted and displayed. The same physical display,
resolution, and refresh rate were used for both color-depth conditions.

## 3. Software environment

| Layer | Version |
|-------|---------|
| Operating system | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | 6.8.0-124-generic |
| Desktop | KDE Plasma 5.27.12 / KWin 5.27.11 |
| GPU driver | NVIDIA proprietary 580.159.03 |
| OpenGL | 4.6.0 NVIDIA (renderer: GeForce RTX 2070) |
| Python | 3.12.3 (project virtual environment, `.venv/`) |

Python packages used for stimulus rendering and data handling:

| Package | Version | Role |
|---------|---------|------|
| glfw | 2.10.0 | Window/OpenGL context creation (X11-only build) |
| PyOpenGL | 3.1.10 | OpenGL bindings |
| PyOpenGL-accelerate | 3.1.10 | Native acceleration for PyOpenGL |
| freetype-py | 2.5.1 | Glyph rendering (stimulus and UI fonts) |
| numpy | 2.4.3 | Stimulus and noise array generation |
| pandas | 3.0.1 | Trial data logging (CSV / JSON) |

The GLFW build in use reports the version string
`3.4.0 X11 GLX Null EGL OSMesa` — it has an X11 backend only and no native
Wayland backend. Consequently the application always communicates over the X11
protocol: directly to the Xorg server in an X11 session, or via XWayland in a
Wayland session.

## 4. The 10-bit condition

The 10-bit condition was realized by running the **KDE Plasma X11 (Xorg)**
session, in which the X screen runs at color depth 30 (10 bits per channel). This
depth is set by an Xorg drop-in configuration file:

`/etc/X11/xorg.conf.d/10-nvidia-10bit.conf`

```
Section "Device"
    Identifier  "Nvidia0"
    Driver      "nvidia"
    Option      "DefaultDepth" "30"
EndSection

Section "Screen"
    Identifier  "Screen0"
    Device      "Nvidia0"
    DefaultDepth 30
EndSection
```

This drop-in overrides `DefaultDepth 24` in the base `/etc/X11/xorg.conf`, so the
Xorg server starts at depth 30. With this configuration the X root window is 30
planes, confirming a 10-bit screen:

```
$ xdpyinfo | grep "depth of root"
  depth of root window:    30 planes
```

NVIDIA output dithering was disabled (`Dithering = 0`), so the 10-bit output is
true 10-bit with no temporal or spatial dithering.

## 5. The 8-bit condition

The 8-bit condition was realized by running the **KDE Plasma Wayland** session. A
Wayland session does not start the native Xorg server and therefore does not
read the depth-30 configuration in Section 4. On this NVIDIA / Plasma 5.27 setup,
the KWin-Wayland compositor presents at standard 8-bit (8 bits per channel), and
the experiment reaches the display through XWayland. The effective depth in this
condition is 24 planes (8 bits per channel):

```
$ echo $XDG_SESSION_TYPE
wayland
$ xdpyinfo | grep "depth of root"      # reported through XWayland
  depth of root window:    24 planes
```

Thus the color-depth manipulation corresponds to the session type: the X11
session provides 10-bit and the Wayland session provides 8-bit, using the same
hardware, resolution, and refresh rate.

## 6. Rendering pipeline and stimulus precision

Stimuli were rendered with OpenGL 3.3 core (GLFW + PyOpenGL + FreeType;
`lib/gl_renderer.py`). The renderer takes a `bits` argument selecting the
framebuffer format explicitly — `10` for 10-10-10-2, `8` for 8-8-8-8:

```python
if bits == 10:
    glfw.window_hint(glfw.RED_BITS, 10)
    glfw.window_hint(glfw.GREEN_BITS, 10)
    glfw.window_hint(glfw.BLUE_BITS, 10)
    glfw.window_hint(glfw.ALPHA_BITS, 2)
else:
    glfw.window_hint(glfw.RED_BITS, 8)
    glfw.window_hint(glfw.GREEN_BITS, 8)
    glfw.window_hint(glfw.BLUE_BITS, 8)
    glfw.window_hint(glfw.ALPHA_BITS, 8)
```

`step1`–`step3` set it from the module constant `FRAMEBUFFER_BITS`;
`luminance_test.py` in the display-measurement project sets it per mode from `MODE_BITS`.

Requesting the depth rather than inheriting it from the session matters on any
platform that grants a 10-bit framebuffer regardless of the output link depth
(see Section 9). On a 10-bit framebuffer an 8-bit code value does not land on an
8-bit code: `127/255` is stored as 10-bit code 509 and reads back as 126.8755,
and only 4 of the 256 8-bit codes survive the round trip exactly. The residue is
what a driver's output dithering then spreads across neighbouring codes, so an
"8-bit" condition presented that way is a dithered 10-bit stimulus. Requesting
8-8-8-8 makes the codes exact — verified by reading the framebuffer back:

| framebuffer | value written | 16-bit readback | residue |
|-------------|---------------|-----------------|---------|
| 8-8-8-8     | 127/255       | 127.0000        | 0.0000 LSB |
| 10-10-10-2  | 127/255       | 126.8755        | −0.1245 LSB |

Gray levels were specified as floating-point values in the range 0.0–1.0 and
written directly to the framebuffer; no temporal dithering was applied. Noise
fields were uploaded to the GPU as 16-bit float textures (`GL_R16F`) to preserve
precision before quantization at the framebuffer. In the 10-bit condition the
framebuffer quantizes to 1024 levels; in the 8-bit condition it quantizes to 256
levels.

## 7. Verification of the active bit depth

The renderer queries the real framebuffer bit depth at startup and prints it, for
example:

```
Framebuffer: R=10 G=10 B=10 A=2 bits
  -> 10-bit rendering CONFIRMED
```

In the 8-bit condition this line reports `R=8 G=8 B=8`. The renderer compares
the granted depth against the requested one and warns in both directions — a
request for 8 that is granted 10 is called out explicitly, because that is the
silent-dithering case rather than a harmless upgrade.

The reported framebuffer depth and the full display information are stored in
every result file under `display_calibration`, and the bit-depth condition
itself under `display_bit_depth`:

| field | meaning |
|-------|---------|
| `framebuffer_bits_requested` | what the condition asked for |
| `framebuffer_bits_actual` | what OpenGL granted |
| `framebuffer_confirmed` | whether they match |
| `lut_state` | `identity`, `inverse_gamma_2.2`, or `other`, read back from the GPU |
| `lut_mid` | midpoint entry of the ramp, as a fingerprint |

`luminance_test.py` records the same fields per CSV row, plus `output_bpc` and
`driver_dither` entered at the start of the session (neither is readable in
software — see Section 9).

**The hardware LUT is asserted, not assumed.** The measurement tool loads a
known ramp before measuring, verifies it by reading it back, and restores the
previous one afterwards. Simply not applying gamma correction is not sufficient:
that leaves whatever the last program left loaded, and a Psychtoolbox script
exiting through its error path leaves an inverse-gamma table in the LUT
system-wide, which would distort every subsequent reading with nothing in the
output to indicate it.

Which ramp is a startup choice (`LUT_CHOICES`):

| choice | measures | use |
|--------|----------|-----|
| experiment gamma (2.2) — default | the stimulus as presented | matches `step1`–`step3`, which load the same table, so the readings describe what the participant sees end to end |
| identity (raw panel) | the panel's own response | needed to derive a measured gamma table — characterising the panel through a correction derived from that panel is circular |

`lut_state` in each CSV row records which was used.

As an additional visual check, each program draws a 1024-level horizontal
grayscale gradient bar (`numpy.linspace(0.0, 1.0, 1024)`) at the top of the
screen. It appears smooth at 10-bit and shows visible banding at 8-bit.

## 8. Bit-depth signal chain (framebuffer → link → panel)

The 10-bit pathway was confirmed at each verifiable stage on this machine:

- **Framebuffer (GPU):** the Xorg log records the screen starting at depth 30 in
  the X11 session (`NVIDIA(0): Depth 30, framebuffer bpp 32`), and the renderer's
  runtime query returns `R=10 G=10 B=10 A=2 bits` (Section 7).
- **Panel (monitor EDID):** the BenQ EX3210U EDID declares a digital display with
  **10 bits per primary color channel** (decoded from the monitor's EDID; product
  name "BenQ EX3210U", serial ETA6P02919SL0).
- **Link (DisplayPort bits-per-color):** the NVIDIA proprietary driver does not
  expose the transmitted bits-per-color through a readable property
  (RandR "max bpc" is absent and `nvidia-settings` returns no value), so the
  on-wire value could not be read directly. With a depth-30 framebuffer, a panel
  that accepts 10 bits per channel, and dithering disabled, the link carries the
  10-bit signal.

Note that an EDID declaration of 10 bits per channel reports the depth the panel
accepts and displays; it does not by itself distinguish a native 10-bit panel
from an 8-bit panel using frame-rate control (FRC). This distinction is a
property of the BenQ EX3210U panel hardware and is taken from the manufacturer
specification rather than measured here.

In the 8-bit condition (Wayland session), the same chain operates at 8 bits per
channel: the framebuffer query returns `R=8 G=8 B=8`, and the depth reported
through XWayland is 24 planes.

---

## 9. Second apparatus (Windows) and why the condition is set in code

Sections 1–8 describe the Ubuntu machine on which the reported data were
collected. A second machine was subsequently used, with the same display model
but a different host, GPU and operating system. The bit-depth manipulation does
**not** transfer to it, which is why the framebuffer depth is now requested
explicitly (Section 6) rather than inherited from the session.

| Property | Machine A (Sections 1–8) | Machine B |
|----------|--------------------------|-----------|
| OS | Ubuntu 24.04.4 LTS | Windows 10 Home 19045 |
| GPU | NVIDIA GeForce RTX 2070 | NVIDIA GeForce GTX 1650 |
| GPU driver | 580.159.03 (proprietary) | 32.0.15.6094 |
| Display | BenQ EX3210U | BenQ EX3210U (same model) |
| Mode | 3840 × 2160 @ 119.88 Hz | 3840 × 2160 @ 60 Hz |
| Python / glfw | 3.12.3 / 2.10.0 | 3.14.6 / 2.10.2 |
| Depth selection | X11 depth 30 vs Wayland session | `FRAMEBUFFER_BITS` / `MODE_BITS` in code |
| Output dithering | disabled (`Dithering = 0`) | on; not exposed to any API |

Three differences matter for interpretation.

**The framebuffer depth is not controlled by the OS setting.** On Machine B the
driver grants a 10-10-10-2 framebuffer whether NVIDIA Control Panel → Change
resolution → Output color depth is set to 8 bpc or 10 bpc; this was verified
directly, windowed and fullscreen. The session-type method of Sections 4–5 has
no Windows equivalent, and changing the driver setting alone leaves the
framebuffer — and therefore the logged `R=10` — unchanged. The condition must
come from `bits`.

**Windows reports the 8 bpc mode as "8-bit with dithering."** With the output
link at 8 bpc, the display engine dithers anything of higher precision down to
8 bits rather than truncating it, so surplus precision reaches the panel as a
spatial/temporal mixture instead of being discarded. There is no supported API
for reading or disabling this, and no equivalent of the `Dithering = 0` setting
used on Machine A. It is therefore recorded per session rather than controlled:
`output_bpc` and `driver_dither` are entered at the start of a
`luminance_test.py` run and written to every CSV row.

With an 8-8-8-8 framebuffer there is no sub-8-bit information left for the
driver to dither, so the 8-bit condition is well defined on Machine B despite
this. The `dither` mode is the exception: its deliberate temporal dithering can
be compounded by the driver's, and it is interpretable only with
`driver_dither` recorded.

**Refresh rate differs by a factor of two** (60 Hz vs 119.88 Hz). The temporal
dither modes alternate codes per frame, so the duty cycle integrated by the
photometer is not the same on the two machines. Measurements from Machine B
should carry their own condition tag and should not be pooled with the
Machine A CSVs without justification.
