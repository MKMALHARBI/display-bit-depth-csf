#!/usr/bin/env python3
"""Visualize Lemma 1 from gamma_effect.md: the Weibull at γ=0.33 (3-AFC
calibration) and γ=0.50 (2-AFC calibration), both with the same curve
parameter t, showing what `quest.mean()` actually corresponds to vs
where the curve crosses p=0.75."""

import os
import numpy as np
import matplotlib.pyplot as plt


def weibull(x, t, gamma, beta=3.5, delta=0.01):
    return delta * gamma + (1 - delta) * (
        1 - (1 - gamma) * np.exp(-10 ** (beta * (x - t)))
    )


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    t = 0.0
    beta = 3.5
    x = np.linspace(-1.0, 0.5, 600)

    gammas = [
        (0.33, '#0072B2', '3-AFC calibration (γ=0.33)'),
        (0.50, '#D55E00', '2-AFC calibration (γ=0.50)'),
    ]

    fig, ax = plt.subplots(figsize=(10, 6.5))
    for g, color, label in gammas:
        p = weibull(x, t, gamma=g)
        ax.plot(x, p, color=color, linewidth=2.2, label=label)

        # Point at x = t — what quest.mean() actually saves
        p_at_t = weibull(t, t, gamma=g)
        ax.scatter([t], [p_at_t], color=color, s=110, zorder=5,
                   edgecolor='black', linewidth=1.4)
        ax.annotate(f'p(t; t) = {p_at_t:.3f}',
                    xy=(t, p_at_t),
                    xytext=(t + 0.06, p_at_t + (0.05 if g == 0.5 else -0.07)),
                    fontsize=10.5, color=color, fontweight='bold')

        # Triangle marker at the literal 0.75-crossing
        x_at_75 = t + np.log10(np.log(4 * (1 - g))) / beta
        ax.scatter([x_at_75], [0.75], color=color, s=70, zorder=5,
                   marker='v', edgecolor='black', linewidth=0.9)
        ax.annotate(f'p=0.75 crossing\n  Δ = {x_at_75:+.3f}',
                    xy=(x_at_75, 0.75),
                    xytext=(x_at_75 - 0.43, 0.62 if g == 0.5 else 0.84),
                    fontsize=9, color=color,
                    arrowprops=dict(arrowstyle='->', color=color, lw=0.7))

    ax.axvline(t, color='gray', linestyle='--', linewidth=0.9, alpha=0.7)
    ax.axhline(0.75, color='gray', linestyle=':', linewidth=0.9, alpha=0.6)
    ax.text(t + 0.01, 0.04, 'x = t   (= quest.mean())', fontsize=10,
            color='gray', fontweight='bold')
    ax.text(-0.98, 0.77, 'p = 0.75', fontsize=10, color='gray')

    # Box explaining the takeaway
    ax.text(0.04, 0.30,
            'quest.mean() saves t (curve parameter).\n'
            'At x = t, the curve sits at γ + 0.632·(1−γ):\n'
            '   • 3-AFC (γ=0.33):  0.754   ≈ p_threshold\n'
            '   • 2-AFC (γ=0.50):  0.816   ≠ p_threshold\n\n'
            'So `p_threshold = 0.75` is exact only\n'
            'when γ = 0.33. For γ = 0.50 the saved\n'
            'point sits 0.045 log-units above the\n'
            'literal 75% crossing.',
            fontsize=9.5, family='monospace',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='#fffbe6',
                      edgecolor='gray', linewidth=1))

    ax.set_xlabel('Log contrast  $x - t$', fontsize=11)
    ax.set_ylabel('Probability correct  $p(x; t)$', fontsize=11)
    ax.set_title('What `p_threshold = 0.75` actually saves under each γ\n'
                 'Weibull at γ=0.33 vs γ=0.50, shared curve parameter t  (β=3.5)',
                 fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.set_xlim(x.min(), x.max())
    ax.set_yticks(np.arange(0, 1.01, 0.1))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='lower right', frameon=False, fontsize=10)

    fig.tight_layout()
    save_path = os.path.join(out_dir, "gamma_psychometric_curves.png")
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {save_path}")
