# Does Display Bit Depth Change Measured Contrast Sensitivity?

A letter-detection experiment in which the **manipulated variable is the display itself**:
the same near-threshold task, the same observers, run once at **8-bit** (256 grey levels) and
once at **10-bit** (1024 grey levels).

The motivation is a measurement problem rather than a perceptual one. Near-threshold contrast
research asks observers to detect luminance increments smaller than an 8-bit display can
represent — one 8-bit step is 1/255 ≈ 0.39 % of full scale, one 10-bit step is 1/1023 ≈ 0.10 %.
If the increment you intend to present is finer than the display's quantisation step, the
display rounds it away and the threshold you measure is the display's, not the observer's.

13 participants each completed one 10-bit and one 8-bit session. Sensitivity (d′) came out
substantially higher at 10 bits in both tasks — roughly 0.72 vs 0.04 in the 10-AFC task and
0.63 vs 0.09 in the 2-AFC task.

Alongside the behavioural experiment, the project contains a **photometric verification** of
the display with a chroma meter, which is where the more unusual findings are.

## The experiment

| Step | Script | Task | Design |
|---|---|---|---|
| 1 | `step1_calibration.py` | QUEST contrast threshold, letters C/O/D | 3AFC, 2 blocks × 40 trials |
| 2 | `step2_SR_experiment.py` | identify the letter, full 10-letter set | 10AFC, 10 letters × 7 noise × 6 reps = 420 trials |
| 3 | `step3_SR_experiment.py` | identify the letter, V vs Z only | 2AFC, 2 letters × 7 noise × 30 reps = 420 trials |

Steps 2 and 3 are matched at 420 trials so the two tasks are equally powered. Both run at the
participant's own calibrated contrast, with additive dynamic Gaussian noise at seven levels
(σ = 0, 0.25, 0.76, 2.3, 6.96, 21.11, 64 on the 0–255 scale).

Running the same stimulus at two numbers of alternatives is what makes the bit-depth comparison
interpretable: 2AFC and 10AFC have different chance levels (0.5 vs 0.1), so proportion correct
is not comparable between them. Both are converted to **d′** under an unbiased m-AFC
equal-variance Gaussian model, which puts them on one bias-free scale. The derivation is in
[`analysis/dprime_method.md`](analysis/dprime_method.md), including the log-linear ceiling
correction that keeps d′ finite when a participant scores 100 %.

## How the two bit depths were realised

This is the neat part of the apparatus. Both conditions run on identical hardware, resolution
and refresh rate — the depth is set by **which desktop session you log into**:

- **10-bit** — the KDE Plasma **X11** session, with an Xorg drop-in
  (`/etc/X11/xorg.conf.d/10-nvidia-10bit.conf`) setting `DefaultDepth 30`. `xdpyinfo` then
  reports a 30-plane root window. NVIDIA output dithering off, so it is true 10-bit.
- **8-bit** — the KDE Plasma **Wayland** session. Wayland never starts the native Xorg server
  and so never reads that config; KWin-Wayland presents at 8 bits per channel and the
  experiment reaches the display through XWayland, at 24 planes.

The renderer queries the framebuffer at startup and prints what it really got
(`R=10 G=10 B=10 A=2 bits` or `R=8 G=8 B=8`), and that value is written into every result file
under `display_calibration`, so the depth actually used is recorded per session rather than
assumed. Each screen also draws a 1024-level gradient bar — smooth at 10-bit, visibly banded at
8-bit.

Full apparatus description: [`DISPLAY_SETUP_8bit_vs_10bit.md`](DISPLAY_SETUP_8bit_vs_10bit.md).

## Photometric verification

`luminance_analysis/` contains a direct measurement of the display with a **Konica Minolta
CS-160** chroma meter on a locked tripod at 700 mm, 1/3° measuring angle, in a darkened room.
The protocol — geometry, spot/patch ratio, environmental limits, warm-up, the on-screen
positioning target — is in [`luminance_analysis/EXPERIMENT.md`](luminance_analysis/EXPERIMENT.md).

The test steps through every consecutive 10-bit code from 504 to 520 (17 patches). At 8-bit
those 17 codes collapse onto about 6. Measured, with 3 readings per patch and ±2σ:

| Mode | Distinguishable steps | Mean \|Δ\| (cd/m²) | White (cd/m²) |
|---|---|---|---|
| 10-bit | 15 of 17 | 0.52 | 442.57 ± 0.12 |
| 10-bit, monitor forced to 8-bit | 6 of 17 | 0.54 | 435.17 ± 0.23 |
| 8-bit | 5 of 5 | 1.98 | 434.20 ± 2.23 |

So the 10-bit path is real, and it resolves roughly three times finer luminance steps.

### A firmware bug found along the way

The 10-bit luminance ramp is monotonic **except** for a dip at codes 511→512→513 — exactly the
binary boundary 512 = `1000000000`. Luminance goes *down* by ~0.1 cd/m² where it should rise by
~0.5, losing about one 10-bit LSB.

[`luminance_analysis/FINDING_msb_carry_plateau.md`](luminance_analysis/FINDING_msb_carry_plateau.md)
identifies the cause by elimination across five measurement conditions rather than by curve
fitting. The dip:

- **disappears** when the monitor is driven in 8-bit mode, or fed an externally pre-dithered
  signal — so it is internal to the monitor's 10-bit decode, not the panel, backlight, GPU or link;
- is **invariant to refresh rate** (60 Hz vs 120 Hz identical) — so it is not residual frame-rate control;
- is present at 512 but **absent at 768**, which is equally a power-of-two LUT node — so it is not
  LUT-node interpolation.

The distinguishing property of 511→512 is that the carry propagates into the **most significant
bit**. The surviving explanation is fixed-point carry rounding at bit 9 inside the monitor's
internal pipeline, losing one LSB.

`hdr_luminance_effect.md` separately shows that HDR state imposes a near-constant luminance
offset (~11.7–12.6 cd/m²) while **preserving** dL/dV, so it shifts the adaptation level but
leaves the bit-depth comparison valid. It was held fixed across conditions regardless.

## The guess-rate investigation

`calibration_analysis/gamma_effect.md` documents a problem worth reading before reusing this
calibration: 3AFC calibration (letters C/O/D) produced 10-AFC test accuracy about **four times
lower** than 2AFC calibration did, 0.2–0.3 against 0.6–0.8.

The cause is in the Weibull guess rate γ. QUEST converges to the contrast where the observer
scores 0.75 *on the calibration task*, and where that lands relative to the true threshold
depends on γ — which changes with the number of alternatives. The document works through the
algebra and the empirical runs, and the accompanying figures show the psychometric functions for
2, 3, 5, 7 and 10 alternatives side by side.

## Requirements

Linux, Python 3.12, OpenGL 3.3 core profile. Rendering is raw GLFW + PyOpenGL + FreeType so a
requested 10-bit framebuffer is actually honoured.

To run the **10-bit** condition you need an X11 session at colour depth 30 and a 10-bit-capable
panel on DisplayPort. The 8-bit condition needs a Wayland session, or any ordinary depth-24
setup. A Sloan optotype font should be installed; the code falls back silently to Liberation
Sans, which is not an optotype face.

There is no `requirements.txt`. Package versions used are tabulated in
`DISPLAY_SETUP_8bit_vs_10bit.md` §3:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy==2.4.3 pandas==3.0.1 matplotlib glfw==2.10.0 \
            PyOpenGL==3.1.10 PyOpenGL-accelerate==3.1.10 freetype-py==2.5.1
```

## Running it

No command-line arguments. Step 1 first — it fixes the contrast steps 2 and 3 reuse, and they
load the participant record automatically.

```bash
python step1_calibration.py
python step2_SR_experiment.py     # 10AFC
python step3_SR_experiment.py     # 2AFC
```

For the luminance measurement, follow `luminance_analysis/EXPERIMENT.md` and run:

```bash
python luminance_analysis/luminance_test.py       # drive the patches, log meter readings
python luminance_analysis/luminance_analysis.py   # analyse the sweeps, produce the figures
```

## Analysis

```bash
python analysis/plot_results.py                                   # accuracy and d′, both tasks
python threshold_gray_average.py                                  # mean threshold grey code by depth
python calibration_analysis/plot_thresholds.py                    # per-participant thresholds
python calibration_analysis/plot_gamma_curves.py                  # Weibull curves vs guess rate
python calibration_analysis/plot_gamma_calibration_to_test.py     # calibration → test mapping
```

## Layout

```
step1_calibration.py               QUEST threshold calibration (3AFC)
step2_SR_experiment.py             10AFC letter detection
step3_SR_experiment.py             2AFC letter detection
threshold_gray_average.py          mean threshold grey code by bit depth
DISPLAY_SETUP_8bit_vs_10bit.md     apparatus: how each bit depth was realised

lib/
  parameters.py        letters, noise levels, aperture, fonts
  gl_renderer.py       OpenGL renderer, FreeType glyphs, noise textures
  display_utils.py     display detection and visual-angle calibration
  exp_dialog.py        participant intake dialog

analysis/
  dprime_method.md     the m-AFC d′ derivation
  plot_results.py      accuracy and d′ figures

calibration_analysis/
  gamma_effect.md                     why 3AFC calibration under-shot, worked through
  plot_gamma_curves.py                Weibull curves vs guess rate
  plot_gamma_calibration_to_test.py   calibration-to-test contrast mapping
  plot_thresholds.py                  per-participant thresholds

luminance_analysis/
  EXPERIMENT.md                    measurement protocol and rig geometry
  FINDING_msb_carry_plateau.md     root-cause analysis of the code-512 dip
  hdr_luminance_effect.md          HDR offset vs quantisation step
  luminance_stats.md               measurement summary table
  luminance_test.py                drives the patches, logs readings
  luminance_analysis.py            analyses the sweeps
  luminance_*.csv                  the measurement sweeps
```

## Known issues

- **`DISPLAY_SETUP_8bit_vs_10bit.md` starts with a stray character.** Line 1 reads
  `r# Supplementary Material…`, so the top-level heading does not render as a heading.
- **The Sloan font fallback is silent** — no warning if the optotype face is missing.
- **`lib/parameters.py` still carries the MATLAB-migration notes** describing font and frame
  sizes that no longer match the values in the file.
- **The 2AFC task uses V and Z specifically**, hard-coded in `step3_SR_experiment.py` rather
  than drawn from `parameters.py`. Changing the letter set means editing the script.
- **Self-report fields disagree between some participants' two sessions** — level, ocular
  dominance and sex differ between the 10-bit and 8-bit files for three participants. Worth
  reconciling against recruitment records before final reporting.

## Data

No participant data is included. The measurement sweeps in `luminance_analysis/` are photometer
readings from the display, not human data, and are included.

## References

Cited in the method documents:

Green, D. M., & Swets, J. A. (1966). *Signal detection theory and psychophysics.* Wiley.

Hautus, M. J. (1995). Corrections for extreme proportions and their biasing effects on estimated
values of d′. *Behavior Research Methods, Instruments, & Computers, 27*(1), 46–51.

Macmillan, N. A., & Creelman, C. D. (2005). *Detection theory: A user's guide* (2nd ed.).
Erlbaum.

Snodgrass, J. G., & Corwin, J. (1988). Pragmatics of measuring recognition memory: Applications
to dementia and amnesia. *Journal of Experimental Psychology: General, 117*(1), 34–50.

Watson, A. B., & Pelli, D. G. (1983). QUEST: A Bayesian adaptive psychometric method.
*Perception & Psychophysics, 33*(2), 113–120.
