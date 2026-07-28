# Luminance Experiment — 8-bit vs 10-bit Display Output

## Purpose
Verify that the 10-bit output pipeline of the display actually delivers
finer luminance steps than the 8-bit pipeline. Step through every
consecutive 10-bit code 504–520 (17 patches). On 8-bit, those codes
collapse onto 6 codes (125–130). If 10-bit truly works, the meter
should resolve ~17 distinct monotonic steps in 10-bit mode versus
~6 plateaus in 8-bit mode.

## Equipment
- **Display:** BenQ EX3210U-B, 32" 4K (3840 × 2160), 710 × 400 mm panel,
  pixel pitch ≈ 0.185 mm. DisplayPort connection (required for 10-bit).
- **Meter:** Konica Minolta CS-160 chroma meter (1/3° measuring angle).
- **Lens:** Close-up lens No.153 (the only lens available).
- **Mount:** Camera tripod with standard 1/4"-20 thread.
- **Computer:** Linux host running the measurement script
  (`luminance_test.py`) under the project's `lib/gl_renderer.py`
  framebuffer in 8-bit or 10-bit mode.

## Geometry
| Parameter | Value |
|---|---|
| Measuring distance | **700 mm** (from the measuring-distance reference mark on the meter body to the screen) |
| Measuring angle | 1/3° (only option on CS-160) |
| Close-up lens | **No.153**, registered on the meter |
| Spot diameter at this distance | ~2.9 mm (interpolated between 2.5 mm @ 627 mm and 5.9 mm @ 1219 mm) |
| Patch size on screen | 270 × 270 px ≈ 50 × 50 mm |
| **Patch center on screen** | **(1920, 1080) px** — geometric center of the 3840 × 2160 panel, i.e. 355 mm from the left edge and 200 mm from the top edge |
| Spot/patch ratio | ~1/17 (spot fits inside patch with large margin) |
| Mount | Tripod, perpendicular to screen, locked. |

The script displays a **positioning screen** before the first patch:
a red 270 × 270 px outline (the actual patch boundary), a red
crosshair at the patch center (1920, 1080), and a small green box
(~16 px) showing the expected meter spot size. Aim the CS-160 at the
crosshair and confirm the green box stays comfortably inside the red
square through the viewfinder before pressing SPACE to begin.

> **Critical:** the tripod must not move between the 8-bit and 10-bit runs.
> Mark the tripod foot positions on the floor with tape so the rig can be
> reproduced if disturbed.

## Environmental conditions (CS-160 manual, p.3–4)
- Ambient temperature **0–40 °C**, no rapid changes.
- Relative humidity **≤ 85 %** up to 35 °C, declining linearly to 66 % at 40 °C.
- No condensation; lens clean and untouched.
- No direct sunlight on instrument or screen.
- **Dark, constant ambient lighting** during measurement (the meter reads
  emitted + reflected light from the panel).

### Ambient light measurement
- **Primary app:** *Lux Light Meter* (iOS), free version, uncalibrated
  phone ambient-light sensor — treat as indicative only (≈ ±30 %).
- **Procedure:** phone placed face-up on the desk at meter level with
  the screen still off, room in the test-time lighting state.
- **Reading (this session, primary app):**

  | Min | Avg | Max |
  |---|---|---|
  | 0 lux | 1 lux | 2 lux |

- **Cross-check (second app):** *Light Meter* (iOS, the
  Camera / Lighting / Paper / Settings app) was used as an independent
  verification on the same spot in the same conditions. Reading:
  **min 2 lux, current 4 lux** (the app's MAX value is sensitive to
  brief transients — e.g. the phone being lifted past the desk lamp
  during placement — and is omitted from the record).
  Both apps agree the room is in the single-digit lux range.

  Effectively dark room — well below the level at which reflected
  ambient light would meaningfully contaminate the CS-160 readings on
  a near-50 % gray patch. Record this every session in the log below.

## Meter configuration
1. **Calibration channel: CH00** (Konica Minolta factory). No user
   calibration — this is a relative comparison.
2. **Close-up lens registered as No.153**: MENU → Selecting the
   Close-up Lens → No.153 (manual p.42). *Without this step the
   readings are uncorrected.*
3. **Integration time:** Manual, **0.7 s** (CS-160 minimum; MENU →
   Selecting the Integration Time, p.28). Note that spec'd
   repeatability (0.2 % + 1 digit) is measured at AUTO; fixing the
   integration time at the minimum may slightly increase noise on
   dim patches, but at ~50 % gray on this monitor the luminance is
   high enough that the trade-off for shorter sessions is acceptable.
4. **Color space:** Lv (cd/m²) is the field we care about.
5. **Power:** AC adapter preferred for stability over the full session.

## Display configuration
- **Model:** BenQ EX3210U-B, 32" 4K HDR IPS.
- **Transfer function / HDR:** the monitor was run in **HDR mode**
  (BenQ *HDRi* / "Display HDR", enabled in the OSD) for **both** the
  8-bit and 10-bit runs. What this actually means on this host:
  - The host is on **X11** (Plasma 5.27 / KWin 5.27, NVIDIA 580.159.03).
    X11 has no HDR output path, so the GPU sends an ordinary **SDR,
    gamma-2.2-encoded** signal — there is no PQ / HDR10 signal on the wire.
  - With the OSD in HDR mode the BenQ applies its proprietary
    **"Emulated HDR"** tone-mapping on top of that SDR input. This is
    **not** the PQ (ST 2084) curve (no PQ signal is being sent) and it is
    **not** the panel's native γ 2.2 either — entering HDR mode greys out
    the OSD gamma control, so the monitor, not the 2.2 setting, owns the
    curve. The realised code→light mapping is therefore neither a quotable
    gamma nor PQ; it is characterised **empirically** by the CS-160
    measurements written to the CSVs.
  - **The host applies no gamma in software.** The stimulus code writes
    the normalized code value straight to the framebuffer (`gl_renderer.py`:
    `clear()` → `glClearColor(gray, gray, gray, 1.0)` with `gray = code/255`
    or `code/1023` from `luminance_test.py`; there is no `pow()`, no sRGB
    encode, and `GL_FRAMEBUFFER_SRGB` is not enabled). So code 125 is sent
    as pixel code 125, byte-for-byte — the signal **is** the code value,
    with no transfer function attached by the PC.
  - **γ = 2.2 is therefore a display-side decode convention, not a host
    encoding.** It is how the monitor is expected to interpret the bare
    SDR code values (sRGB / Rec.709), set operator-side via BenQ OSD →
    *Picture* → *Gamma* level 3 (the 2.2 step; menu spans γ 1.8–2.6 in 0.2
    steps). In the active emulated-HDR mode (Display Mode 0x23, read back
    via `ddcutil getvcp DC`) the monitor decodes with its own curve
    instead, so 2.2 describes only the SDR-fallback interpretation.
  - **Signal-side verification (performed 2026-05-17 on this host):**
    1. `edid-decode` on the EDID pulled via `xrandr --props` for DP-0
       reports `Gamma: 2.20` in the Basic Display Parameters block.
       (Monitor identified as BenQ EX3210U, S/N ETA6P02919SL0, mfd. wk24 2023.)
    2. `xrandr --verbose` reports `Gamma: 1.0:1.0:1.0` and the CTM is
       identity, so the X server is **not** applying any additional
       gamma curve or color transform — the GPU output is a clean
       gamma-2.2 SDR signal.
    3. `modetest -M nvidia-drm -p` confirms the NVIDIA CRTC exposes
       `GAMMA_LUT`, `DEGAMMA_LUT`, and `NV_CRTC_REGAMMA_TF` properties
       but none are actively reshaping the curve in the current pipeline.
    Together these confirm the **host sends a clean gamma-2.2 SDR signal**;
    the monitor's HDR mode then applies its own curve on top of it.
  - **What the script records:** `lib/display_utils.py::get_display_info()`
    shells out to `xrandr --verbose` and parses the `Gamma: R:G:B`
    line into the `gamma_r / gamma_g / gamma_b` columns written to the
    CSV by `luminance_test.py`. **Important:** this value is the
    *X11 software gamma multiplier* sitting on top of the panel's
    intrinsic curve — not the panel's intrinsic γ. With identity X11
    gamma the CSV will read `1.0 / 1.0 / 1.0`, which means "no software
    correction; the host's gamma-2.2 SDR signal passes through to the
    monitor untouched" (the monitor's HDR mode then reshapes it). If you
    ever see anything other than `1.0 / 1.0 / 1.0` here, an X11
    calibration tool (or `xrandr --gamma`) has been applied and the run
    is no longer a clean gamma-2.2 signal.
- Native resolution **3840 × 2160 @ 60 Hz** over DisplayPort.
- Bit depth set per run by `luminance_test.py` via OpenGL framebuffer
  request (script captures actual `fb_red_bits/green_bits/blue_bits`
  and records them in the CSV).
- **Monitor warmup: ≥ 30 min** at the chosen brightness before any
  measurement begins. LCDs drift after power-on; an under-warmed run
  biases the comparison.
- **Do not change brightness, contrast, gamma, colour mode, or HDR
  settings between the 8-bit and 10-bit runs.** Lock them once before
  warmup. **HDR mode was kept ON (and identical) in both runs** — the
  comparison remains a valid bit-depth comparison because the HDR
  processing was the same in both; only the bit depth differed.
- Disable any *dynamic* display-side features that could differ between
  runs (Eco/Dynamic Contrast, Black eQualizer, Variable Refresh, ambient
  light sensor, etc.). HDR itself stays **on**; ensure its tone mapping is
  static (no auto / dynamic-brightness HDR variant) so it contributes
  identically to both runs.

## Patches (`PATCHES` in `luminance_test.py`)
19 patches total: **1 black bookend**, 17 central gray steps where
the 8-bit and 10-bit values map to the same nominal gray (~0.49–0.51),
and **1 white bookend**.

| # | 8-bit code | 10-bit code | 8-bit float | 10-bit float | Note |
|---|---|---|---|---|---|
| 1 | 0 | 0 | 0.0000 | 0.0000 | **Max darkness (black level)** |
| 2 | 125 | 504 | 0.4902 | 0.4927 | |
| 3 | 125 | 505 | 0.4902 | 0.4936 | |
| 4 | 126 | 506 | 0.4941 | 0.4946 | |
| 5 | 126 | 507 | 0.4941 | 0.4956 | |
| 6 | 127 | 508 | 0.4980 | 0.4966 | |
| 7 | 127 | 509 | 0.4980 | 0.4976 | |
| 8 | 127 | 510 | 0.4980 | 0.4985 | |
| 9 | 127 | 511 | 0.4980 | 0.4995 | |
| 10 | 128 | 512 | 0.5020 | 0.5005 | |
| 11 | 128 | 513 | 0.5020 | 0.5015 | |
| 12 | 128 | 514 | 0.5020 | 0.5024 | |
| 13 | 128 | 515 | 0.5020 | 0.5034 | |
| 14 | 129 | 516 | 0.5059 | 0.5044 | |
| 15 | 129 | 517 | 0.5059 | 0.5054 | |
| 16 | 129 | 518 | 0.5059 | 0.5064 | |
| 17 | 129 | 519 | 0.5059 | 0.5073 | |
| 18 | 130 | 520 | 0.5098 | 0.5083 | |
| 19 | 255 | 1023 | 1.0000 | 1.0000 | **Max brightness (peak white)** |

Black and white bookends let you compute the **on/off contrast ratio**
(peak white Lv ÷ black level Lv) and provide a sanity check that the
panel is being driven across its full range.

## Temporal dithering (`dither` mode)

The `dither` mode emulates 10-bit luminance resolution on the **8-bit
output path** using host-side **temporal dithering** (a software analogue
of the frame-rate-control, FRC, that panels use internally). It writes
only integer 8-bit codes to an 8-bit framebuffer (`fb_*_bits = 8`) but
time-multiplexes between the two codes that bracket the 10-bit target, so
the *time-averaged* drive level lands between two 8-bit codes.

### Target mapping (`build_patch_list`)
For a 10-bit target value `v` (the same 504–520 codes used everywhere
else), the script computes the equivalent **fractional 8-bit code**:

```
T          = v / 1023                # normalized 10-bit target, ∈ [0,1]
c          = 255 · T                 # equivalent 8-bit code (fractional)
base_code  = floor(c)                # lower bracketing 8-bit code
frac (f)   = c − base_code           # fractional part, ∈ [0,1)
```

The two output codes are therefore `base_code` and `base_code + 1`, which
are adjacent on the 8-bit grid (1/255 apart in normalized level). For the
central patches `base_code` is 125–129 and `f` is the sub-code remainder
that a plain 8-bit pipeline would simply discard.

### Per-frame modulation (`make_render_state`, `next_frame_gray`)
Each patch carries a first-order **error-diffusion accumulator** `a`
(initialised to 0). On every rendered frame:

```
a ← a + f
if a ≥ 1:   a ← a − 1;   emit (base_code + 1) / 255
else:                    emit  base_code      / 255
```

This is exactly a **first-order ΔΣ (sigma–delta) modulator** / Bresenham
remainder: the accumulator carries the unspent quantization error forward,
firing the higher code whenever the accrued error reaches one code step.
For a given `f` it produces the most uniformly spaced on/off sequence
possible, with fundamental period ≈ `1/f` frames.

### Why the time-average reproduces the 10-bit target
Over a window of `N` frames the higher code is emitted `≈ f·N` times and
the lower code `≈ (1−f)·N` times, so the **time-averaged code** is

```
⟨code⟩ = (1−f)·base_code + f·(base_code+1) = base_code + f = c = 255·T
```

i.e. the averaged normalized drive equals the 10-bit target `T` to within
the accumulator's residual (≤ one code, decaying as `1/N`). The dither
thus synthesises drive levels *between* 8-bit codes without a 10-bit
signal path.

### Reconstruction by the meter / eye
The averaging is performed by the integrator downstream, not by the GPU:

- **Refresh:** 60 Hz, so the dither's fundamental flicker frequency is
  `f·60 Hz` (≈ 30 Hz at `f ≈ 0.5`, higher as `f → 0` or `1`).
- **CS-160 integration:** fixed at **0.7 s** (see *Meter configuration*),
  which spans ≈ **42 frames** at 60 Hz — many dither periods — so the
  reading reflects the time-averaged luminance rather than any single
  frame. This is the key reason the integration time is fixed rather than
  AUTO for this mode.

### Scope and caveats
- **Two codes only, no spatial dithering.** Every pixel of the patch runs
  the same temporal sequence, so spatial uniformity is preserved; the cost
  is temporal flicker at the dither frequency.
- **Averaging is in code space, not luminance space.** The reconstructed
  time-averaged *code* equals the target, but the time-averaged
  *luminance* is `L = (1−f)·L(base_code) + f·L(base_code+1)`. This equals
  the luminance of the fractional code `c` only where the panel transfer
  function (the emulated-HDR curve, see *Display configuration*) is locally
  linear across one 8-bit step. Over a 1/255 interval the curve is very
  nearly linear, so the discrepancy is second-order — but for this reason
  the `dither` run is **compared empirically** against the native `10bit`
  run rather than assumed identical.
- **Not panel FRC.** This is deliberate host-side modulation in the
  stimulus code; any additional FRC the panel applies acts on top of it.

## Procedure

### One-time setup
1. Position tripod ~700 mm from the screen, perpendicular, meter at the
   height of the screen centre. Mark the tripod foot positions on the
   floor with tape.
2. Mount the CS-160 on the tripod. Attach close-up lens No.153.
3. Power the meter; **register the No.153 lens** (MENU → Selecting the
   Close-up Lens → No.153).
4. Select calibration channel **CH00**.
5. Confirm room is dark, climate stable. Close blinds, turn off any
   light source that hits the screen.

### Per-run setup (do this twice: once at 8-bit, once at 10-bit)
1. Set the OS / driver to the target bit depth before launching the
   script.
2. Launch `luminance_test.py`, choose the matching bit depth in the
   dialog. Confirm the framebuffer bits printed in the console match
   (e.g. `R=10 G=10 B=10` for the 10-bit run).
3. **Warm up display ≥ 30 min** at the gray level used during the test
   (the script's pre-test grey background works fine — leave it running).
4. Through the viewfinder, adjust the visibility ring so the measuring
   circle is sharp.
5. Adjust the objective focus ring so the screen patch is sharp.
6. Confirm only the centre of the patch falls inside the measuring
   circle (target is in the middle of the red guide square drawn by
   the script).
7. **Do not move the tripod from this point until both bit-depth runs
   are complete.**

### Per-patch procedure
For each of the 17 patches the script will:
1. Display the gray patch full-screen with a red outline guide square
   in the centre.
2. Wait for SPACE on the keyboard.
3. For each of the 3 measurements at the same spot:
   - Show the aim screen — confirm aim is steady, press SPACE.
   - Press the **Measuring button on the CS-160** once. Wait for the
     value on the meter's LCD.
   - Type the displayed Lv value into the script (digits + ENTER).

After all 17 patches: the script writes
`luminance_{bit_depth}bit_{timestamp}.csv` in the
`luminance_analysis/` folder.

### Run order
1. **8-bit run** (set driver to 8 bpc → launch script → 17 patches).
2. **10-bit run** (set driver to 10 bpc → launch script → 17 patches).
3. Do not move the tripod between runs. Do not change brightness.

## Data files
- `luminance_8bit_<timestamp>.csv` — 17 rows, columns include
  `patch_number, bit_depth, monitor_name, resolution, refresh_rate,
  brightness, gamma_*, fb_red_bits, fb_green_bits, fb_blue_bits,
  value, gray_float, measurement_1, measurement_2, measurement_3, mean`.
- `luminance_10bit_<timestamp>.csv` — same schema.

## Analysis
Run `python3 luminance_analysis.py` from the same folder. It will:
- Load all `luminance_*.csv` in the directory.
- For each bit depth, compute mean ± standard deviation across the
  3 measurements per patch.
- Plot luminance vs `gray_float` with 8-bit and 10-bit overlaid
  (errorbars), saving `luminance_plot.png`.

### Expected outcome
- **10-bit run:** ~17 distinct monotonic luminance steps across the
  504–520 range.
- **8-bit run:** ~6 plateaus (codes 125–130), with adjacent 10-bit
  codes that share an 8-bit code producing identical luminance.

If both curves look identical (6 plateaus on both), the 10-bit
pipeline is not actually reaching the panel — investigate the driver,
DP cable, monitor's "10-bit" toggle, and the GLFW context hints in
`lib/gl_renderer.py`.

## Failure modes / things to record manually
- Distance changed mid-run → invalidates the run.
- Brightness control bumped → invalidates the run.
- Room lighting changed → invalidates the run.
- Monitor switched between SDR/HDR mode → invalidates the run.
- If any measurement reading looks anomalous (>3× the local std-dev),
  redo that patch before continuing.

## Session log template
Keep a paper or text log alongside the CSVs:

```
Date / time:
Operator:
Room temperature (°C):
Room humidity (%):
Ambient lighting — min/avg/max (lux, Lux Light Meter iOS app):
Ambient lighting cross-check — min/current (lux, Light Meter iOS app):
Monitor brightness setting:
Monitor colour mode (record exact mode, e.g. HDRi / emulated HDR):
Distance measured (mm):
Tripod position marked? (Y/N):
Lens registered on meter (Y/N):
Calibration channel:
Display warmup time before first measurement (min):
Notes:
```
