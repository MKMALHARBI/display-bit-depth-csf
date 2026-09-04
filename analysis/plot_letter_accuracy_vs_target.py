#!/usr/bin/env python3
"""
PLOT_LETTER_ACCURACY_VS_TARGET.PY - Per-letter accuracy against the 0.75 target
==============================================================================
3-panel figure comparing every letter used in the study with the QUEST target
of 0.75 proportion correct.

  Panel A  Calibration  C, O, D                      (3-AFC, chance 1/3)
  Panel B  Step 2       C D H K N O R S V Z          (10-AFC, chance 1/10)
  Panel C  Step 3       V, Z                         (2-AFC, chance 1/2)

Calibration accuracy uses the converged part of each QUEST block (second half
of the trials in the block), because the early trials sample contrasts far from
threshold. Steps 2 and 3 use all trials; both run at the fixed calibrated
threshold contrast with no noise.

Bars are the mean across sessions of each session's per-letter proportion
correct, with SEM error bars; dots are individual sessions.
"""

import os
import glob
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 12.5,
    'axes.linewidth': 1.0,
    'axes.labelweight': 'normal',
    'axes.titlesize': 14,
    'axes.titleweight': 'normal',
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 4,
    'ytick.major.size': 4,
    'legend.frameon': False,
})

TARGET = 0.75
BAR_COLOR = '#8FA9C4'
DOT_COLOR = '#3A4A5C'


def load_calibration(data_dir):
    """Per-trial calibration data, keeping only converged trials per block."""
    rows = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*", "*_calibration_threshold.json"))):
        session = os.path.basename(os.path.dirname(path))
        with open(path) as fh:
            data = json.load(fh)
        trials = pd.DataFrame(data.get('trial_log', []))
        if trials.empty:
            continue
        trials['session'] = session
        trials['trial_in_block'] = trials.groupby('block').cumcount()
        n_per_block = trials.groupby('block')['trial_in_block'].transform('max') + 1
        converged = trials[trials['trial_in_block'] >= n_per_block // 2]
        rows.append(converged)
    if not rows:
        return None
    df = pd.concat(rows, ignore_index=True)
    return df.rename(columns={'correct_letter': 'PresentedLetter',
                              'is_correct': 'AnswerCorrect'})[
        ['session', 'PresentedLetter', 'AnswerCorrect']]


def load_step(data_dir, step):
    """Per-trial data for step2 / step3, pooled over sessions."""
    rows = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*", f"*_{step}_SR_Binocular_trials.csv"))):
        df = pd.read_csv(path)
        df['session'] = os.path.basename(os.path.dirname(path))
        rows.append(df)
    if not rows:
        return None
    return pd.concat(rows, ignore_index=True)[['session', 'PresentedLetter', 'AnswerCorrect']]


def per_letter_stats(df, letter_order=None):
    """Session-level accuracy per letter -> mean, SEM, n across sessions."""
    per_session = (df.groupby(['session', 'PresentedLetter'])['AnswerCorrect']
                     .mean().reset_index())
    stats = per_session.groupby('PresentedLetter')['AnswerCorrect'].agg(['mean', 'std', 'count'])
    stats['sem'] = stats['std'] / np.sqrt(stats['count'])
    if letter_order is not None:
        stats = stats.reindex([l for l in letter_order if l in stats.index])
    return stats, per_session


def plot_panel(ax, df, title, chance, letter_order=None):
    if df is None or df.empty:
        ax.set_title(f'{title} (no data)')
        ax.set_xticks([])
        ax.set_yticks([])
        return

    stats, per_session = per_letter_stats(df, letter_order)
    letters = list(stats.index)
    x = np.arange(len(letters))

    ax.bar(x, stats['mean'].values, 0.62, yerr=stats['sem'].values, capsize=3,
           color=BAR_COLOR, edgecolor='black', linewidth=0.8, zorder=2)

    # individual sessions, jittered
    rng = np.random.default_rng(0)
    for i, letter in enumerate(letters):
        vals = per_session.loc[per_session['PresentedLetter'] == letter, 'AnswerCorrect'].values
        jitter = rng.uniform(-0.16, 0.16, size=len(vals))
        ax.scatter(i + jitter, vals, s=9, color=DOT_COLOR, alpha=0.35,
                   linewidths=0, zorder=3)

    ax.axhline(TARGET, color='#B4433B', linestyle='--', linewidth=1.2, zorder=4,
               label=f'QUEST target ({TARGET:.2f})')
    ax.axhline(chance, color='gray', linestyle=':', linewidth=1.2, zorder=4,
               label=f'Chance ({chance:.2f})')

    n_sessions = df['session'].nunique()
    ax.set_title(f'{title}  (N={n_sessions} sessions)')
    ax.set_xticks(x)
    ax.set_xticklabels(letters)
    ax.set_xlabel('Letter')
    ax.set_ylim(0, 1.0)
    ax.set_yticks(np.arange(0, 1.01, 0.1))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', fontsize=10)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), 'Data')

    cal = load_calibration(data_dir)
    step2 = load_step(data_dir, 'step2')
    step3 = load_step(data_dir, 'step3')

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4),
                             gridspec_kw={'width_ratios': [3, 10, 2]})

    plot_panel(axes[0], cal, 'Calibration (converged QUEST trials)',
               chance=1 / 3, letter_order=['C', 'O', 'D'])
    plot_panel(axes[1], step2, 'Step 2 - 10 letters',
               chance=1 / 10,
               letter_order=['C', 'D', 'H', 'K', 'N', 'O', 'R', 'S', 'V', 'Z'])
    plot_panel(axes[2], step3, 'Step 3 - 2 letters',
               chance=1 / 2, letter_order=['V', 'Z'])

    axes[0].set_ylabel('Proportion correct')

    fig.suptitle('Per-letter accuracy vs the 0.75 threshold criterion', y=0.99)
    fig.tight_layout()

    out_path = os.path.join(script_dir, 'letter_accuracy_vs_target.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    print(f"Saved: {out_path}")

    for name, df, chance in [('Calibration', cal, 1 / 3),
                             ('Step 2', step2, 1 / 10),
                             ('Step 3', step3, 1 / 2)]:
        if df is None or df.empty:
            continue
        stats, _ = per_letter_stats(df)
        overall = df.groupby('session')['AnswerCorrect'].mean()
        print(f"\n{name}: overall {overall.mean():.3f} +/- {overall.std(ddof=1)/np.sqrt(len(overall)):.3f} "
              f"(chance {chance:.2f})")
        print(stats[['mean', 'sem', 'count']].round(3).to_string())


if __name__ == '__main__':
    main()