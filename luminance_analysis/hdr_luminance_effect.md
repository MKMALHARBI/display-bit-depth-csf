# Effect of HDR State on Contrast-Threshold Measurement

## Summary

The HDR rendering state (HDRi on versus off) was found to impose a near-constant additive offset on display luminance while preserving the per-code-value luminance step. Consequently, no effect is exerted on the 8-bit versus 10-bit contrast comparison. The HDR state must nonetheless be fixed across all conditions and reported.

## Measurement

Display luminance was characterised as a function of 10-bit code value over the range 504 to 520, under both 10-bit and 8-bit rendering and under both HDR states.

| Rendering mode | HDRi off offset (cd/m²) |
|----------------|-------------------------|
| 10-bit         | 11.72 ± 1.13            |
| 8-bit          | 12.58 ± 1.28            |

The offset was approximately constant across the measured code-value range, and the slope dL/dV was preserved between HDR states (the on and off curves are parallel).

## Interpretation

Two channels are relevant to a contrast-threshold task.

First, threshold contrast is governed by Weber's law, C_th = ΔL_th / L_bg. Disabling HDRi raises the background luminance L_bg, which shifts the adaptation state. For an identical physical increment ΔL, a smaller Weber contrast is therefore obtained on the higher background. This channel is sensitive to the HDR state.

Second, the smallest renderable contrast is set by the quantisation step dL/dV. Because this slope is preserved across HDR states, the contrast floor imposed by display bit depth is unchanged. The 8-bit versus 10-bit comparison is therefore unaffected by the HDR state.

## Conclusion

The HDR state introduces an offset to the adaptation luminance but does not alter the quantisation step that distinguishes 8-bit from 10-bit rendering. The bit-depth comparison is valid under either state. The HDR state was held fixed across all experimental conditions and is reported with the apparatus specification.
