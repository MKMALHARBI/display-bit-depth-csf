# Luminance Plateau at Code 512: Root-Cause Identification

**Subject:** Non-monotonic luminance plateau near 10-bit code 512 on monitor DP-2
**Date of analysis:** 2026-06-25
**Data source:** `luminance_analysis/` measurement sweeps, 2026-06-23
**Status:** Root cause identified by elimination across five independent datasets.

---

## Abbreviations and terms

| Term | Expansion / meaning |
|------|---------------------|
| **LSB** | Least Significant Bit. The smallest representable step of a digital code. One 10-bit LSB = 1/1023 of full scale. |
| **MSB** | Most Significant Bit. The highest-weight bit of a word. For a 10-bit value (range 0–1023) the MSB is bit 9, weight 512. |
| **bit 9** | The MSB of a 10-bit word. It flips from 0 to 1 at the 511→512 transition. |
| **10-bit / 8-bit** | Bit depth of the pixel value. 10-bit = 1024 levels (0–1023); 8-bit = 256 levels (0–255). |
| **code / value** | The integer pixel value sent to the display (the `value` column in the CSVs). |
| **LUT** | Look-Up Table. A table inside the GPU or monitor that maps input code → output code, often with interpolation between sparse entries ("nodes"). |
| **FRC** | Frame Rate Control. A temporal dithering technique that alternates a pixel between two levels across successive frames so the time-average yields an intermediate level (e.g. fakes 10-bit on an 8-bit panel). |
| **DNL** | Differential Non-Linearity. The deviation of one code's step size from the ideal uniform step. A negative DNL means the output went *down* when the code went *up*. |
| **EOTF** | Electro-Optical Transfer Function. The mapping from code to emitted light (the display's gamma curve). |
| **HDR** | High Dynamic Range mode. A display mode with an alternate internal transfer function and tone mapping. |
| **DP / HDMI** | DisplayPort / High-Definition Multimedia Interface. The video transport links. |
| **carry** | In binary addition, the bit propagated to a higher position when a sum overflows. At 511→512 the carry propagates all the way to the MSB (bit 9). |
| **fixed-point** | A method of representing fractional numbers using integers with an implied binary point (as opposed to floating-point). Rounding/truncation at a fixed-point boundary can lose one LSB. |
| **nit** | Candela per square metre (cd/m²), the unit of luminance used in all measurements here. |
| **plateau** | The observed region where luminance stops rising (or slightly falls) despite increasing code. |

---

## 1. Observation

In a direct luminance sweep of a 10-bit grayscale ramp (monitor DP-2, native 10-bit
mode, repeated measurements averaged, temporal dithering/FRC disabled), luminance
rises monotonically except for a localized **non-monotonic dip at codes 511–513**,
i.e. immediately at the binary boundary **512 = `1000000000`b**.

Raw means (`luminance_10bit_20260623_211959.csv`), with per-code step Δ:

| code | binary (10-bit) | mean (nit) | Δ (nit) |
|------|-----------------|-----------:|--------:|
| 510 | 0111111110 | 75.70 | +0.80 |
| 511 | 0111111111 | 76.53 | +0.83 |
| **512** | **1000000000** | **76.47** | **−0.07** |
| **513** | 1000000001 | 76.43 | **−0.03** |
| 514 | 1000000010 | 76.73 | +0.30 |
| 515 | 1000000011 | 77.27 | +0.53 |

The local nominal step is ~0.50 nit/code; at 512–513 the output instead *decreases*.
The lost rise is on the order of **1 LSB (10-bit)**.

---

## 2. Hypotheses considered

The plateau could in principle arise from any of:

1. Internal monitor LUT interpolation
2. Internal monitor gamma (EOTF) processing
3. Fixed-point arithmetic / carry boundary at the MSB (512)
4. Hidden FRC still active
5. GPU LUT processing
6. Panel driver quantization
7. Backlight stabilization
8. Measurement artifact
9. Signal transport issue (DP/HDMI)
10. True panel nonlinearity

---

## 3. Method: discrimination by controlled condition

The diagnosis does **not** rely on curve fitting (the sweep is only ~16 points wide and
the fit residual is comparable to the effect). It relies on comparing the **same code
region under conditions that each switch off one candidate mechanism**. Five datasets
in `luminance_analysis/` provide this:

| Dataset (file) | What it changes | Candidate it tests |
|----------------|-----------------|--------------------|
| `luminance_10bit_20260623_211959.csv` | baseline, native 10-bit | (reference) |
| `luminance_10bit_mon8bit_20260623_195630.csv` | monitor driven in **8-bit** mode | panel / backlight / transport vs 10-bit decode |
| `luminance_dither_20260623_201435.csv` | **software** (spatial) dithering | GPU / transport |
| 60 Hz vs 120 Hz sweep (operator-run) | **refresh rate** | hidden FRC |
| `luminance_carry_20260623_213601.csv` | boundaries **256 / 512 / 768** | periodic LUT node vs MSB-specific carry |

---

## 4. Results

### 4.1 Behaviour at code 512 across conditions

| Condition | 511 → 512 → 513 step pattern | Dip present? |
|-----------|------------------------------|:---:|
| 10-bit native (baseline) | +0.83, **−0.07, −0.03** | **Yes** |
| Monitor in 8-bit mode | uniform 4-code staircase; 512 steps like 508 & 516 | **No** |
| Software dithering | +0.67, +0.27, +0.70 (monotonic) | **No** |
| 60 Hz vs 120 Hz | identical | (refresh-invariant) |

In 8-bit monitor mode the response is a clean staircase — every 4 input codes produce
one luminance step, with jumps at 508, 512, 516, 520. Code 512 is an *ordinary* step
there, not an anomaly. The dip is therefore **absent whenever the monitor's 10-bit
decode is bypassed** (8-bit mode) **or fed an externally pre-dithered signal**.

### 4.2 Boundary comparison (carry test)

Same monitor, native 10-bit, three binary boundaries:

| Boundary | Code pattern | Step behaviour | Dip? |
|----------|--------------|----------------|:---:|
| 256 = `0100000000` | carry reaches bit 8 | flat, but at ~5 nit where meter resolves only 0.1 nit | inconclusive |
| 512 = `1000000000` | **carry reaches bit 9 (MSB)** | +0.90, **+0.07, −0.03** | **Yes** |
| 768 = `1100000000` | carry reaches bit 8 (bit 9 already 1) | +0.70, +0.70, +0.60 | **No** |

The boundary 768 is also a power of two and would be an interpolation node in any
regular LUT scheme, yet it shows **no** anomaly. Only 512 is affected.

The distinguishing property of 512 (vs 256 and 768) is that the 511→512 transition
**flips all ten bits and propagates the carry into the MSB (bit 9)**. At 768 the carry
stops at bit 8 because bit 9 is already set.

---

## 5. Elimination

| Hypothesis | Verdict | Decisive evidence |
|------------|---------|-------------------|
| Hidden FRC | **Rejected** | 60 Hz and 120 Hz sweeps identical; FRC patterns are refresh-locked and would shift. |
| GPU LUT processing | **Rejected** | Software-dithered signal through the same GPU/link is clean. |
| Signal transport (DP/HDMI) | **Rejected** | Same; transport carries the dithered path without defect. |
| Backlight stabilization | **Rejected** | Effect is code-locked to one value and absent in 8-bit mode; backlight is global. |
| Measurement artifact | **Rejected** | Reproduced in two independent sweeps; triplicate spread ≤0.1 nit; recovers cleanly. |
| True panel nonlinearity | **Rejected** | Disappears in 8-bit mode (same physical panel); a panel nonlinearity would persist. |
| Panel driver quantization | **Rejected** | Disappears in 8-bit mode; defect tracks the 10-bit word, not a native panel level. |
| Internal LUT node interpolation | **Rejected** | Boundary 768 (equally a power-of-two node) is clean; effect is not periodic. |
| Internal gamma (EOTF) | **Unlikely** | Requested gamma = 1.0; feature is a discrete dip, not a smooth slope change. |
| **Fixed-point / carry at the MSB** | **Supported** | Sole surviving hypothesis; uniquely explains 512-specific, refresh-invariant, 10-bit-decode-only, ~1 LSB dip absent at 768. |

---

## 6. Conclusion

The plateau is a **fixed-point / integer carry-rounding artifact at the most-significant
bit (bit 9) of the monitor's internal 10-bit processing pipeline.**

When the input code rolls from 511 (`0111111111`) to 512 (`1000000000`), the carry
propagates into the MSB of the 10-bit word and the internal fixed-point arithmetic
loses approximately **one 10-bit LSB**, producing the observed ~0.1 nit dip and the
~1-code stall in the rising luminance.

The defect is:

- **Internal to the monitor's 10-bit decode** — absent in 8-bit monitor mode and absent
  with externally pre-dithered input.
- **Not temporal** — invariant to refresh rate, so not residual FRC.
- **MSB-specific, not periodic** — present at 512 but absent at 768, so not LUT-node
  interpolation.

---

## 7. Limitations and suggested confirmation

- The 256 boundary sits at ~5 nit, where the photometer resolves only ~0.1 nit, so a
  smaller bit-8 carry effect there could not be confirmed or excluded. **Re-measure
  around code 256 at a brightness placing it near ~75 nit** to test whether carry
  magnitude scales with bit position (a bit-8 carry should lose ~0.5 LSB of the
  equivalent local step).
- The luminance step size (~0.5 nit/code) is comparable to single-code measurement
  scatter; the conclusion rests on the **cross-condition contrast**, not on the
  magnitude of any single curve.
- Recommended additional boundaries to map the carry signature fully: 64, 128, 384,
  640, 896, each at a brightness keeping them in a well-resolved luminance range.

---

## 8. Data inventory

| File | Mode | Role in this analysis |
|------|------|-----------------------|
| `luminance_10bit_20260623_211959.csv` | native 10-bit | baseline; shows the dip |
| `luminance_10bit_mon8bit_20260623_195630.csv` | monitor 8-bit | dip absent → isolates 10-bit decode |
| `luminance_dither_20260623_201435.csv` | software dither | dip absent → clears GPU/transport |
| `luminance_carry_20260623_213601.csv` | 256/512/768 | dip at 512 only → clears LUT-node hypothesis |
| `luminance_10bit_hdr_off_20260623_205405.csv` | 10-bit, HDR off | supplementary (different operating point) |
| 60 Hz / 120 Hz sweeps | refresh variation | clears FRC |