# Why is 3-AFC different from 2-AFC and 5-AFC? — full log of runs and numbers

## The original observation

Empirically, with the original setup (calibration on C/O/D for 3-AFC):

| Calibration | 10-AFC test accuracy at noise=0 |
|---|---|
| 2-AFC | 0.6 – 0.8 |
| 3-AFC (C/O/D) | 0.2 – 0.3 |

3-AFC calibration produced 10-AFC accuracy ~4× lower than 2-AFC. The question: **why?**

---

## The math model from the code

`step1_calibration.py:47-52` uses a Weibull psychometric function:

$$
W(x; t, \gamma) = \delta\gamma + (1-\delta)\bigl[1 - (1-\gamma)\exp(-10^{\beta(x-t)})\bigr],
\quad \beta=3.5,\ \delta=0.01.
$$

QUEST converges to the contrast where the participant scores 0.75 on the calibration task. Solving $W(x_\text{cal}; t, \gamma)=0.75$:

$$
x_\text{cal} - t = \frac{1}{\beta}\,\log_{10}\!\Bigl[-\ln\!\frac{(1-\delta)(1-\gamma)-(0.75-\delta\gamma)}{(1-\delta)(1-\gamma)}\Bigr]
$$

| N-AFC | γ | $x_\text{cal}-t$ (log10) |
|---|---|---|
| 2-AFC | 0.50 | $-0.0437$ |
| 3-AFC | 0.33 | $-0.0010$ |
| 4-AFC | 0.25 | $+0.0117$ |
| 5-AFC | 0.20 | $+0.0212$ |

**Math prediction:** thresholds should grow monotonically with N (more letters → brighter threshold), all within ~0.065 log10 of each other. Under this model, 10-AFC accuracy at all three contrasts should be roughly equal (~0.55–0.67 depending on exact framing).

**This prediction is wrong in the direction of the observed effect.** The math says 3-AFC's threshold should be slightly *brighter* than 2-AFC's. The empirical data showed 3-AFC's was dramatically *dimmer*.

So either (a) the procedure itself is broken for 3-AFC, or (b) the Weibull's assumption that the participant guesses at exactly $\gamma=1/N$ rate fails for the specific letter set used.

---

## Run 2 — first multi-AFC calibration run, original letters

Three configs in one session: 2-AFC (C/O), 3-AFC (C/O/D), 5-AFC (C/O/D/H/N). Two calibration runs back-to-back, then experiment three times.

### Calibration thresholds

| Config | Run 1 threshold (log10 / linear) | Run 2 threshold (log10 / linear) |
|---|---|---|
| 2-AFC | +0.222 / 1.666 (SD 0.20) | +0.230 / 1.700 (SD 0.06) |
| 3-AFC C/O/D | **+0.015 / 1.034** (SD 0.36) | **+0.043 / 1.104** (SD 0.08) |
| 5-AFC | +0.282 / 1.915 (SD 0.07) | +0.236 / 1.722 (SD 0.05) |

3-AFC came out **reproducibly ~0.2 log10 lower** than 2-AFC and 5-AFC across both calibration runs. The math predicts 3-AFC should sit between 2-AFC and 5-AFC, separated by 0.044 log10. Observed gap: 0.21 log10. Wrong direction and 5× the predicted magnitude.

### Experiment (10-AFC at each saved threshold)

| Calibration | Threshold used (linear) | 10-AFC accuracy |
|---|---|---|
| 2-AFC | 1.666 | **0.767** (46/60) |
| 3-AFC C/O/D | 1.034 | **0.167** (10/60) — failure |
| 5-AFC | 1.915 | **0.767** (46/60) |

### What killed 3-AFC C/O/D in the experiment

Per-letter accuracy at the saved threshold contrast (same letters, different choice sets):

| Letter | 3-AFC C/O/D calibration accuracy (at 1.034) | 10-AFC accuracy (at 1.034) |
|---|---|---|
| C | 0.96 | **0.00** (0/6) |
| D | 0.91 | **0.00** (0/6) |
| O | 0.73 | 0.17 (1/6) |

Same letters, same contrast — accuracy collapsed by 56-96 percentage points when the choice set went from 3 to 10. Detection doesn't disappear with more options, so the 0.96 on C and 0.91 on D in calibration was **not** detection. It was the participant scoring high using the structure of the C/O/D set itself.

In contrast, at 2-AFC's threshold (1.666):
- C: 0.96 (cal) → 0.83 (10-AFC)
- O: 0.69 (cal) → 1.00 (10-AFC)

Per-letter accuracy was essentially preserved. The 2-AFC saved threshold reflected real detection.

Experiment confusion matrix at the 3-AFC threshold: the participant **defaulted to Z** for 42 of 60 trials. They could not see the letter at this contrast.

---

## Run 3 — swap C/O/D for H/V/Z (test the hypothesis)

If C/O/D is the cause, then changing to visually distinct letters should fix 3-AFC. H/V/Z is three angular shapes with very different topology — no round-and-closed letters, no obvious partial-cue scoring strategy.

Also added a 4-AFC (H/V/Z + K) for additional comparison.

### Calibration thresholds

| Config | Letters | Threshold (log10 / linear) | SD |
|---|---|---|---|
| 2-AFC | C, O | +0.280 / 1.906 | 0.068 |
| 3-AFC | **H, V, Z** | +0.200 / 1.584 | 0.018 |
| 4-AFC | H, V, Z, K | +0.300 / 1.995 | 0.002 |
| 5-AFC | C, O, D, H, N | +0.300 / 1.995 | 0.001 |

**3-AFC anomaly disappeared.** With H/V/Z instead of C/O/D, the 3-AFC threshold moved from +0.015 (Run 2) → +0.200 (Run 3). It's now in the same neighborhood as 2-AFC, 4-AFC, 5-AFC (all within 0.10 log10).

### Experiment (10-AFC at each saved threshold)

| Calibration | Threshold (linear) | 10-AFC accuracy |
|---|---|---|
| 2-AFC | 1.906 | **0.767** (46/60) |
| 3-AFC H/V/Z | 1.584 | **0.817** (49/60) |
| 4-AFC H/V/Z/K | 1.995 | **0.717** (43/60) |
| 5-AFC | 1.995 | **0.850** (51/60) |

All four cluster in the **0.72 – 0.85** range. None crash. The 3-AFC procedure is fine when the letters are visually distinct.

### What this established

- 3-AFC C/O/D: threshold 1.034 → 10-AFC 0.167 (broken)
- 3-AFC H/V/Z: threshold 1.584 → 10-AFC 0.817 (works)

Same procedure, same γ=1/3, same 80 trials, same participant. The only thing changed: the three letters. **The procedure is not broken; the C/O/D letter triplet specifically is.**

### Mechanism

QUEST assumes $\gamma_\text{true} = 1/N$ — that the participant guesses uniformly at chance when they can't see. For C/O/D, the participant can score above 1/3 at sub-detection contrasts because the three round/closed shapes admit partial-cue scoring + response bias. QUEST sees that elevated rate, interprets it as evidence of detection, and converges to a contrast *below* the participant's real detection threshold. For H/V/Z (no partial-cue advantage), the assumption holds.

---

## Run 4 — four different 3-AFC letter triplets (just calibrated)

To pin down whether it's specifically "round/closed" letters or some other property that breaks 3-AFC, ran four 3-AFC variants in one session.

### Calibration thresholds

| Tag | Letters | Threshold (log10 / linear) | SD |
|---|---|---|---|
| 3AFC_OCD | O, C, D | +0.229 / 1.696 | 0.050 |
| 3AFC_GJL | G, J, L | +0.400 / 2.512 | 0.004 |
| 3AFC_QGO | Q, G, O | +0.403 / 2.529 | 0.020 |
| 3AFC_FGH | F, G, H | +0.200 / 1.585 | 0.005 |

Spread: 0.20 log10 (factor of ~1.6 in linear contrast). **None of the four reproduced the dramatic Run-2 C/O/D failure** (1.03 in linear). Even OCD — same three letters as Run 2's failed 3-AFC — came out at 1.70 this session.

### Per-letter calibration accuracy at threshold

```
OCD: O=0.86 (25/29)   C=0.74 (20/27)   D=0.88 (21/24)
GJL: G=0.96 (22/23)   J=0.63 (19/30)   L=0.89 (24/27)
QGO: Q=0.52 (13/25)   G=0.97 (30/31)   O=0.83 (20/24)
FGH: F=0.78 (18/23)   G=0.85 (29/34)   H=0.78 (18/23)
```

Hard letters in each set:
- OCD: C is weakest (0.74). Old session had **O** as weakest. Different per-letter pattern despite same letters.
- GJL: J (0.63) is weakest.
- QGO: Q (0.52) is much weaker than G or O.
- FGH: balanced.

### Response distribution

```
OCD: O=32, C=23, D=25     — mild O over-bias
GJL: G=31, J=19, L=30     — J under-reported (G,L over)
QGO: Q=16, G=38, O=26     — strong G over-bias, Q under
FGH: F=23, G=31, H=26     — mild G bias
```

(Uniform would be 26.7 each.)

**G is a default letter for this participant**: in QGO it's reported 38/80 times. Whenever G appears in the triplet, it dominates responses. That's why QGO and GJL converged at *higher* thresholds (2.5 linear): the participant identified G reliably but was near chance on Q and J, so overall accuracy needed brighter contrast to reach 0.75.

### Why OCD didn't reproduce the failure

Old C/O/D 3-AFC: threshold 1.034 (failure mode).
New OCD 3-AFC (same letters, different order in prompt and different session position): threshold 1.696 (looks normal).

Candidate reasons:
- **Letter order in prompt** ("O, C, D" vs "C, O, D") shifts the participant's default key.
- **Position in session** (Run 2 had C/O/D as 2nd of 3; Run 4 has OCD as 1st of 4).
- **Practice/state effects** — this is the participant's third pass through C/O/D-style triplets.

The original failure was real and reproduced across both Run-2 calibrations, but is not a guaranteed property of the OCD letter set alone — context matters.

### Awaiting Run-4 experiment

Calibration is done. Experiment runs needed for each tag (`--tag 3AFC_OCD`, `--tag 3AFC_GJL`, `--tag 3AFC_QGO`, `--tag 3AFC_FGH`).

Predictions if "thresholds in the 1.6–2.5 linear range transfer to 10-AFC at ~0.72–0.85":
- OCD (1.70): expected ~0.77
- GJL (2.51): expected ~0.75–0.85
- QGO (2.53): expected ~0.75–0.85
- FGH (1.585): expected ~0.77–0.82

If any one crashes (10-AFC < 0.3), that letter triplet has the same problem the original C/O/D had. If all four work, the failure mode is rarer than we thought — it requires a specific combination of letters and session conditions.

---

## Summary so far

| Run | Calibration | Threshold (linear) | 10-AFC accuracy |
|---|---|---|---|
| 1 (informal) | 2-AFC | — | 0.6–0.8 |
| 1 (informal) | 3-AFC C/O/D | — | 0.2–0.3 |
| 2 | 2-AFC | 1.666 | 0.767 |
| 2 | 3-AFC C/O/D | 1.034 | **0.167** |
| 2 | 5-AFC | 1.915 | 0.767 |
| 3 | 2-AFC | 1.906 | 0.767 |
| 3 | 3-AFC H/V/Z | 1.584 | 0.817 |
| 3 | 4-AFC H/V/Z/K | 1.995 | 0.717 |
| 3 | 5-AFC | 1.995 | 0.850 |
| 4 | 3-AFC OCD | 1.696 | pending |
| 4 | 3-AFC GJL | 2.512 | pending |
| 4 | 3-AFC QGO | 2.529 | pending |
| 4 | 3-AFC FGH | 1.585 | pending |

## Conclusions to date

1. **The 3-AFC procedure itself is not broken.** When the letters are visually distinct (H/V/Z), 3-AFC produces a threshold that transfers to 10-AFC normally.

2. **The Run-2 C/O/D failure was a real, reproducible event.** Two consecutive Run-2 calibrations both produced a 3-AFC threshold ~0.2 log10 below the others, and the resulting 10-AFC accuracy was 0.167.

3. **The failure is letter-set + state dependent.** Run-4's OCD (same letters) did *not* reproduce the failure. Letter order in the prompt, position in the session, and prior practice may matter.

4. **The math (Weibull QUEST) breaks when $\gamma_\text{true} \neq 1/N$.** If the participant can score above the assumed chance rate using non-detection strategies (response bias, partial cues), the saved threshold drops below real detection. C/O/D allows this in some contexts; H/V/Z does not.

5. **The Run-4 experiment will tell us whether any of the four new triplets reproduces the failure.** If OCD does at 1.70, the threshold-vs-accuracy relationship is non-monotone and noisier than we thought. If none does, the failure mode is rarer/more context-specific than expected.

---

## Threshold consistency — diagnosis and tweaks (TODO, look at tomorrow)

### What's actually inconsistent

Within-session block-to-block variability is **large**:

| Run | Config | Block 1 thr | Block 2 thr | Δ (log10) |
|---|---|---|---|---|
| 2 (Cal A) | 2-AFC | +0.364 | +0.080 | 0.28 |
| 2 (Cal B) | 2-AFC | +0.406 | +0.055 | 0.35 |
| 2 (Cal A) | 5-AFC | +0.400 | +0.164 | 0.24 |
| 4 | OCD | +0.400 | +0.058 | 0.34 |
| 4 | GJL | +0.400 | +0.400 | 0.00 |
| 4 | FGH | +0.200 | +0.200 | 0.00 |

Across-session averaged thresholds (same config, different sittings):

| Config | Run 2 final | Run 3 final | Δ (log10) |
|---|---|---|---|
| 2-AFC | +0.222 | +0.280 | 0.06 |
| 5-AFC | +0.282 | +0.300 | 0.02 |

So **averaged** thresholds are stable (~0.06 log10 across sessions), but **individual block** estimates jiggle by up to 0.35 log10.

### Sources of the noise, ranked by impact

1. **QUEST grain = 0.2 log10.** Block thresholds cluster on grid points {0.0, 0.2, 0.4}. With a tight posterior, `quest.mean()` snaps to within ±0.1 of a grid point. This is the dominant within-session noise source.

2. **Block 1 is biased by the prior.** Prior is `N(-0.5, SD=4)`. First trial sits at the 75th percentile of the prior = +2.2 (very bright). The first 5–10 trials are still moving the posterior off the prior. With only 40 trials/block, block 1 often ends biased upward.

3. **40 trials per block is on the low side.** Posterior variance at convergence scales as ~1/n. Going to 60–80 would tighten estimates noticeably.

4. **Letter-set difficulty.** A single hard letter (Q at 0.52 in QGO; J at 0.63 in GJL) drags QUEST upward in a real, non-noise way. Different letter sets *should* give different thresholds — but the effect makes cross-set comparison harder.

5. **Participant state.** Attention, fatigue, accommodation. Some session-to-session drift is unavoidable.

### Tweaks to try

| Change | Where | Expected effect |
|---|---|---|
| `grain=0.05` (down from 0.2) | `SimpleQUEST.__init__` defaults in `step1_calibration_copy.py` | 4× finer resolution; threshold values stop snapping to ±0.1 grid |
| `params['quest_trials'] = 60` (up from 40) | `lib/parameters.py` | Tighter per-block posterior |
| `start_val = 0.2` (up from −0.5) | `SimpleQUEST(...)` call in the calibration loop | Faster convergence — prior closer to where the participant's threshold actually sits |
| Drop block 1 from the average | `final_threshold = np.mean(...)` line | Removes the warm-up bias visible in the table above |
| Or add a 3rd block | block loop in `run_calibration_for_config` | More data for averaging; block 1 still discarded |

Biggest single win is probably **grain=0.05** — most of the within-session jiggle is a grid-snapping artifact, not real participant noise.

If reducing grain, also consider widening the range a bit (e.g. `range_val=4` is fine but check that the posterior never bumps into the boundary — print the final posterior's `argmax` for each block to make sure it isn't at ±4).

