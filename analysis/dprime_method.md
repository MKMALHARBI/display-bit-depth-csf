# Sensitivity (d′) Computation for m-AFC Letter Detection

This document describes the method used in `plot_results.py` to convert proportion-correct scores from the 10-AFC (Step 2) and 2-AFC (Step 3) letter-detection tasks into a sensitivity index, **d′**, that is comparable across tasks with different numbers of alternatives.

## Why d′ rather than proportion correct

Proportion correct (`pc`) is not directly comparable between a 2-AFC and a 10-AFC task because the chance levels differ (0.5 vs 0.1) and the mapping from underlying sensitivity to `pc` is non-linear. Converting `pc` to d′ under signal-detection theory places both tasks on a single, bias-free sensitivity scale in standard-deviation units of the internal noise distribution.

## Model

We use the **unbiased m-alternative forced-choice (m-AFC) model with equal-variance Gaussian internal representations** (Green & Swets, 1966; Macmillan & Creelman, 2005):

- On each trial, the target generates an internal sample drawn from `N(d′, 1)`.
- The `m − 1` non-targets each generate samples from `N(0, 1)`.
- The observer is unbiased and selects the alternative with the largest internal sample.

Under this model the expected proportion correct is

$$
P_c(d', m) \;=\; \int_{-\infty}^{\infty} \varphi(x - d')\, \Phi(x)^{\,m-1} \, dx
$$

where `φ` and `Φ` denote the standard-normal PDF and CDF.

For the special case `m = 2` this reduces to the closed-form

$$
P_c(d', 2) \;=\; \Phi\!\left( \frac{d'}{\sqrt{2}} \right).
$$

## Inversion: recovering d′ from observed pc

For each participant × bit-depth × task we:

1. Compute the observed proportion correct `p̂c`.
2. Apply a log-linear ceiling correction to keep d′ finite when `p̂c = 1` (Hautus, 1995; Snodgrass & Corwin, 1988):

$$
p̂_c \leftarrow 1 - \frac{1}{2N} \quad \text{if } p̂_c = 1,
$$

   where `N` is the number of trials contributing to that participant's score.
3. If `p̂c ≤ 1/m` (at or below chance), set d′ = 0.
4. Otherwise, solve

$$
P_c(d', m) - p̂_c = 0
$$

   for d′ on the interval [0, 10] using Brent's method (`scipy.optimize.brentq`). The forward integral is evaluated with adaptive Gaussian quadrature (`scipy.integrate.quad`) over `[-10, 10]`, which contains essentially all of the Gaussian mass.

## Aggregation

For each `(bit-depth, task)` condition we compute d′ per participant, then report

- group mean d′,
- standard error of the mean: `SEM = SD / √n`, with `SD` using `ddof = 1`.

These are plotted as grouped bars (8-bit vs 10-bit) with SEM error bars. Both panels share a common y-axis so 10-AFC and 2-AFC sensitivities are visually comparable.

## Assumptions and limitations

- **Equal-variance Gaussian noise.** Standard but unverified for this stimulus set; unequal-variance models would require ROC data.
- **Unbiased decision rule.** m-AFC with a max-rule decision has no bias parameter, so this is appropriate here.
- **Independent trials.** Per-participant pooling assumes trials within a condition are exchangeable.
- **Ceiling correction.** The `1 − 1/(2N)` adjustment trades a small downward bias near ceiling for finite, well-behaved d′ estimates; alternative corrections (e.g. Hautus, 1995) give similar results.

## References

- Green, D. M., & Swets, J. A. (1966). *Signal Detection Theory and Psychophysics.* Wiley.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection Theory: A User's Guide* (2nd ed.). Lawrence Erlbaum Associates. (See Chapter 6 on m-AFC and the forced-choice tables.)
- Hacker, M. J., & Ratcliff, R. (1979). A revised table of d′ for m-alternative forced choice. *Perception & Psychophysics, 26*(2), 168–170.
- Hautus, M. J. (1995). Corrections for extreme proportions and their biasing effects on estimated values of d′. *Behavior Research Methods, Instruments, & Computers, 27*(1), 46–51.
- Snodgrass, J. G., & Corwin, J. (1988). Pragmatics of measuring recognition memory: Applications to dementia and amnesia. *Journal of Experimental Psychology: General, 117*(1), 34–50.
- Virtanen, P., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. *Nature Methods, 17*, 261–272. (Used for `scipy.integrate.quad` and `scipy.optimize.brentq`.)

## Code entry points (in `plot_results.py`)

- `pc_from_dprime(d, m)` — forward model `P_c(d′, m)`.
- `dprime_from_pc(pc, m)` — numerical inverse via Brent's method, with the ceiling correction handled by the caller.
- `plot_panel_dprime(ax, df, title, bit_colors, m)` — per-participant d′, group mean ± SEM, grouped by bit depth.