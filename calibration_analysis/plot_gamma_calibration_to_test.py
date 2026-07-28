#!/usr/bin/env python3
"""Visualize what each psychophysical model predicts for the 10-AFC test
accuracy at noise=0 under 2-AFC and 3-AFC calibration (p_threshold=0.75),
and compare against the observed values.

Three panels:
  A: High-threshold / shared-Weibull — both calibrations save the same
     curve parameter t_d, so both predict the same 10-AFC accuracy.
  B: SDT — P_N(d') for N=2,3,10. The 3-AFC calibration converges at
     higher d' (brighter contrast) than 2-AFC, so SDT predicts 3-AFC
     test > 2-AFC test on 10-AFC.
  C: Predicted (HT, SDT) vs observed range — neither model reproduces
     the observed 2-AFC ≫ 3-AFC pattern.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from scipy.stats import norm


def weibull(x, t, gamma, beta=3.5, delta=0.01):
    return delta * gamma + (1 - delta) * (
        1 - (1 - gamma) * np.exp(-10 ** (beta * (x - t)))
    )


_Z_GRID = np.linspace(-8, 8, 4001)
_DZ = _Z_GRID[1] - _Z_GRID[0]
_PHI = norm.pdf(_Z_GRID)


def p_NAFC(dprime, N):
    """P(correct) for unbiased N-AFC identification with equal-variance
    Gaussians: P = integral phi(z) Phi(z + d')^(N-1) dz."""
    integrand = _PHI * norm.cdf(_Z_GRID + dprime) ** (N - 1)
    return np.trapz(integrand, dx=_DZ)


def dprime_at(p_target, N):
    return brentq(lambda d: p_NAFC(d, N) - p_target, 0.001, 6.0)


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8))

    # ------------------------------------------------------------------
    # Panel A: High-threshold / shared Weibull
    # ------------------------------------------------------------------
    ax = axes[0]
    t = 0.0
    beta = 3.5
    x = np.linspace(-1.0, 0.5, 600)

    curves_HT = [
        (0.10, '#117733', '10-AFC test (γ=0.10)'),
        (0.33, '#0072B2', '3-AFC calib (γ=0.33)'),
        (0.50, '#D55E00', '2-AFC calib (γ=0.50)'),
    ]
    for g, color, label in curves_HT:
        ax.plot(x, weibull(x, t, g), color=color, linewidth=2, label=label)

    p2_at_t = weibull(t, t, 0.50)
    p3_at_t = weibull(t, t, 0.33)
    p10_at_t = weibull(t, t, 0.10)

    ax.axvline(t, color='gray', linestyle='--', linewidth=0.9, alpha=0.7)
    ax.scatter([t], [p2_at_t], color='#D55E00', s=80, zorder=5,
               edgecolor='black', linewidth=1.0)
    ax.scatter([t], [p3_at_t], color='#0072B2', s=80, zorder=5,
               edgecolor='black', linewidth=1.0)
    ax.scatter([t], [p10_at_t], color='#117733', s=110, zorder=6,
               edgecolor='black', linewidth=1.4, marker='s')
    ax.annotate(f'10-AFC at $\\hat{{t}}=t_d$:\n  {p10_at_t:.3f}',
                xy=(t, p10_at_t), xytext=(t + 0.10, p10_at_t - 0.10),
                fontsize=10, color='#117733',
                arrowprops=dict(arrowstyle='->', color='#117733', lw=0.9))

    ax.text(-0.97, 0.05,
            'Both 2-AFC and 3-AFC QUEST\n'
            'are consistent estimators of\n'
            'the same $t_d$ (Lemma 2).\n'
            'Same test contrast →\n'
            'same predicted 10-AFC accuracy.',
            fontsize=9.5,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#fffbe6',
                      edgecolor='gray'))

    ax.set_xlabel('Log contrast  $x - t_d$')
    ax.set_ylabel('Probability correct')
    ax.set_title('A. High-threshold theory\n(shared $t_d$, only γ differs)')
    ax.set_ylim(0, 1.0)
    ax.set_xlim(x.min(), x.max())
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='lower right', frameon=False, fontsize=9)

    # ------------------------------------------------------------------
    # Panel B: Signal detection theory
    # ------------------------------------------------------------------
    ax = axes[1]
    dprime_grid = np.linspace(0, 4, 200)
    p2_curve = norm.cdf(dprime_grid / np.sqrt(2))
    p3_curve = np.array([p_NAFC(d, 3) for d in dprime_grid])
    p10_curve = np.array([p_NAFC(d, 10) for d in dprime_grid])

    ax.plot(dprime_grid, p2_curve, color='#D55E00', linewidth=2, label='2-AFC')
    ax.plot(dprime_grid, p3_curve, color='#0072B2', linewidth=2, label='3-AFC')
    ax.plot(dprime_grid, p10_curve, color='#117733', linewidth=2, label='10-AFC')

    # Calibration target accuracy (= γ + 0.632(1-γ), see Lemma 1)
    p_cal_2 = 0.5 + 0.632 * 0.5     # 0.816
    p_cal_3 = 0.33 + 0.632 * 0.67   # 0.754
    d_2 = dprime_at(p_cal_2, 2)
    d_3 = dprime_at(p_cal_3, 3)
    p10_at_d2 = p_NAFC(d_2, 10)
    p10_at_d3 = p_NAFC(d_3, 10)

    for d, p_cal, p10v, color, name in [
        (d_2, p_cal_2, p10_at_d2, '#D55E00', '2-AFC'),
        (d_3, p_cal_3, p10_at_d3, '#0072B2', '3-AFC'),
    ]:
        ax.plot([d, d], [0, p_cal], color=color, linestyle=':', linewidth=1.2)
        ax.scatter([d], [p_cal], color=color, s=80, zorder=5,
                   edgecolor='black', linewidth=1.0)
        ax.scatter([d], [p10v], color='#117733', s=100, zorder=5,
                   edgecolor=color, linewidth=1.6, marker='s')
        ax.annotate(f'{name}: d\'={d:.2f}\n10-AFC: {p10v:.2f}',
                    xy=(d, p10v), xytext=(d + 0.20, p10v - 0.10),
                    fontsize=9.5, color=color,
                    arrowprops=dict(arrowstyle='->', color=color, lw=0.8))

    ax.set_xlabel("Sensitivity  $d'$")
    ax.set_ylabel('P(correct)')
    ax.set_title("B. Signal detection theory\n(shared $d'(x)$ across tasks)")
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0, 4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='lower right', frameon=False, fontsize=9)

    # ------------------------------------------------------------------
    # Panel C: Predicted vs observed
    # ------------------------------------------------------------------
    ax = axes[2]
    groups = ['2-AFC calib', '3-AFC calib']
    HT_pred = [p10_at_t, p10_at_t]
    SDT_pred = [p10_at_d2, p10_at_d3]
    observed_lo = [0.6, 0.2]
    observed_hi = [0.8, 0.3]
    obs_mid = [(lo + hi) / 2 for lo, hi in zip(observed_lo, observed_hi)]
    obs_err = [(hi - lo) / 2 for lo, hi in zip(observed_lo, observed_hi)]

    x_pos = np.arange(len(groups))
    width = 0.26
    ax.bar(x_pos - width, HT_pred, width, color='#F0E442', edgecolor='black',
           label='HT prediction')
    ax.bar(x_pos, SDT_pred, width, color='#56B4E9', edgecolor='black',
           label='SDT prediction')
    ax.bar(x_pos + width, obs_mid, width, yerr=obs_err, capsize=5,
           color='#CC79A7', edgecolor='black', label='Observed (range)')

    for i, (ht, sdt, obs) in enumerate(zip(HT_pred, SDT_pred, obs_mid)):
        ax.text(i - width, ht + 0.02, f'{ht:.2f}', ha='center', fontsize=9)
        ax.text(i, sdt + 0.02, f'{sdt:.2f}', ha='center', fontsize=9)
        ax.text(i + width, obs + obs_err[i] + 0.02,
                f'{observed_lo[i]:.1f}–{observed_hi[i]:.1f}',
                ha='center', fontsize=9)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(groups)
    ax.set_ylabel('10-AFC test accuracy at noise = 0')
    ax.set_title('C. Predicted vs observed\n(neither model reproduces the gap)')
    ax.set_ylim(0, 1.0)
    ax.axhline(0.10, color='gray', linestyle=':', linewidth=0.8)
    ax.text(1.5, 0.115, 'chance (1/10)', fontsize=8, color='gray', ha='right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False, fontsize=9)

    fig.suptitle('Effect of γ at calibration (p_threshold=0.75) '
                 'on 10-AFC test accuracy at noise=0',
                 y=1.02, fontsize=13)
    fig.tight_layout()
    save_path = os.path.join(out_dir, "gamma_calibration_to_test.png")
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {save_path}")
    print()
    print(f"HT prediction (both groups):  {p10_at_t:.3f}")
    print(f"SDT prediction:")
    print(f"  2-AFC calib  (target 0.816, d'={d_2:.2f}):  10-AFC = {p10_at_d2:.3f}")
    print(f"  3-AFC calib  (target 0.754, d'={d_3:.2f}):  10-AFC = {p10_at_d3:.3f}")
    print(f"Observed: 2-AFC 0.6-0.8, 3-AFC 0.2-0.3")
