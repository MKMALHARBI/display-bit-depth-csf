#!/usr/bin/env python3
"""
PLOT_RESULTS.PY - Letter Detection Accuracy
=====================================================
2-panel figure (Step 2 | Step 3).
Each panel: per-letter proportion correct, grouped bars for 8-bit vs 10-bit,
mean across participants with SEM error bars. Each panel has its own legend.
"""

import os
import re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.integrate import quad
from scipy.optimize import brentq


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


BIT_DEPTH_RE = re.compile(r'(\d+)bit', re.IGNORECASE)


def detect_bit_depth(folder_name):
    m = BIT_DEPTH_RE.search(folder_name)
    return f"{m.group(1)}bit" if m else "unknown"


def load_step_data(data_dir, step):
    pattern = os.path.join(data_dir, "*", f"*_{step}_SR_Binocular_trials.csv")
    csv_files = sorted(glob.glob(pattern), key=os.path.getmtime)
    if not csv_files:
        return None
    rows = []
    for i, csv_file in enumerate(csv_files):
        df = pd.read_csv(csv_file)
        df['participant'] = i + 1
        df['bit_depth'] = detect_bit_depth(os.path.basename(os.path.dirname(csv_file)))
        rows.append(df)
    return pd.concat(rows, ignore_index=True)


def accuracy_per_letter(df):
    per = df.groupby(['participant', 'PresentedLetter'])['AnswerCorrect'].mean().reset_index()
    grouped = per.groupby('PresentedLetter')['AnswerCorrect'].agg(['mean', 'std', 'count'])
    grouped['sem'] = grouped['std'] / np.sqrt(grouped['count'])
    return grouped


def pc_from_dprime(d, m):
    """Expected proportion correct for unbiased m-AFC, equal-variance Gaussian."""
    if m == 2:
        return norm.cdf(d / np.sqrt(2))
    lo = min(-10.0, d - 10.0)
    hi = max(10.0, d + 10.0)
    val, _ = quad(lambda x: norm.pdf(x - d) * norm.cdf(x) ** (m - 1), lo, hi)
    return val


def dprime_from_pc(pc, m):
    """Invert pc_from_dprime to recover d' from observed proportion correct."""
    pc = float(pc)
    lo = pc_from_dprime(0.0, m)
    hi = pc_from_dprime(10.0, m)
    if pc <= lo:
        return 0.0
    if pc >= hi:
        return 10.0
    return brentq(lambda d: pc_from_dprime(d, m) - pc, 0.0, 10.0)


def plot_panel_dprime(ax, df, title, bit_colors, m, ylim=(0.0, 1.2)):
    """One bar per bit_depth, height = mean d' across participants (SEM error bars)."""
    if df is None or df.empty:
        ax.set_title(f'{title} (no data)')
        ax.set_xticks([])
        ax.set_yticks([])
        return

    bit_depths = [b for b in bit_colors.keys() if b in df['bit_depth'].unique()]
    x = np.arange(1)
    n_groups = len(bit_depths)
    width = 0.4

    for i, bit in enumerate(bit_depths):
        sub_df = df[df['bit_depth'] == bit]
        per_part = sub_df.groupby('participant')['AnswerCorrect'].agg(['mean', 'count'])
        # log-linear correction at ceiling: pc = 1 → 1 - 1/(2N) to keep d' finite
        pc_corr = per_part['mean'].where(
            per_part['mean'] < 1.0,
            1.0 - 1.0 / (2.0 * per_part['count'])
        )
        dprimes = pc_corr.apply(lambda p: dprime_from_pc(p, m))
        mean = dprimes.mean()
        sem = dprimes.std(ddof=1) / np.sqrt(len(dprimes)) if len(dprimes) > 1 else 0.0
        n = len(dprimes)
        offset = (i - (n_groups - 1) / 2) * width
        ax.bar(x + offset, [mean], width, yerr=[sem], capsize=3,
               color=bit_colors[bit], edgecolor='black', linewidth=0.8,
               label=f'{bit} (N={n})')

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{m}-AFC'])
    ax.set_ylabel("d′ (sensitivity)")
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 1e-9, 0.1))
    ax.set_box_aspect(4 / 3)  # each panel 3:4 (width:height)
    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False)


def plot_panel_avg(ax, df, title, bit_colors, chance=0.5, ylim=(0.4, 1.0)):
    """Single grouped bar: average across letters, one bar per bit_depth."""
    if df is None or df.empty:
        ax.set_title(f'{title} (no data)')
        ax.set_xticks([])
        ax.set_yticks([])
        return

    bit_depths = [b for b in bit_colors.keys() if b in df['bit_depth'].unique()]
    x = np.arange(1)
    n_groups = len(bit_depths)
    width = 0.4

    for i, bit in enumerate(bit_depths):
        sub_df = df[df['bit_depth'] == bit]
        per_part = sub_df.groupby('participant')['AnswerCorrect'].mean()
        mean = per_part.mean()
        sem = per_part.std(ddof=1) / np.sqrt(len(per_part)) if len(per_part) > 1 else 0.0
        n = len(per_part)
        offset = (i - (n_groups - 1) / 2) * width
        ax.bar(x + offset, [mean], width, yerr=[sem], capsize=3,
               color=bit_colors[bit], edgecolor='black', linewidth=0.8,
               label=f'{bit} (N={n})')

    letters = sorted(df['PresentedLetter'].dropna().unique().tolist())
    ax.axhline(chance, color='gray', linestyle='--', linewidth=0.8,
               label=f'Chance ({int(chance * 100)}%)')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(['+'.join(map(str, letters))])
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 1e-9, 0.1))
    ax.set_xlabel('Letters (averaged)')
    ax.set_ylabel('Proportion correct')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False)


def plot_panel(ax, df, title, bit_colors):
    """Grouped bar plot: one bar per (letter, bit_depth)."""
    if df is None or df.empty:
        ax.set_title(f'{title} (no data)')
        ax.set_xticks([])
        ax.set_yticks([])
        return

    bit_depths = [b for b in bit_colors.keys() if b in df['bit_depth'].unique()]
    accs = {b: accuracy_per_letter(df[df['bit_depth'] == b]) for b in bit_depths}
    letters = sorted(set().union(*[acc.index for acc in accs.values()]))
    x = np.arange(len(letters))
    n_groups = len(bit_depths)
    width = 0.8 / max(n_groups, 1)

    n_per_bit = {}
    for i, bit in enumerate(bit_depths):
        acc = accs[bit].reindex(letters)
        means = acc['mean'].fillna(0).values
        sems = acc['sem'].fillna(0).values
        offset = (i - (n_groups - 1) / 2) * width
        sub_df = df[df['bit_depth'] == bit]
        n = sub_df['participant'].nunique()
        n_per_bit[bit] = n
        ax.bar(x + offset, means, width, yerr=sems, capsize=3,
               color=bit_colors[bit], edgecolor='black', linewidth=0.8,
               label=f'{bit} (N={n})')

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(letters)
    ax.set_ylim(0, 1.0)
    ax.set_yticks(np.arange(0, 1.1, 0.1))
    ax.set_xlabel('Letter')
    ax.set_ylabel('Proportion correct')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "Data")
    out_dir = os.path.dirname(os.path.abspath(__file__))

    df2 = load_step_data(data_dir, "step2")
    df3 = load_step_data(data_dir, "step3")

    if df2 is None and df3 is None:
        print("No step2 or step3 data found. Run the experiments first.")
        raise SystemExit(0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 8))

    bit_colors = {'8bit': '#0072B2', '10bit': '#D55E00'}

    plot_panel_avg(axes[0], df2, 'Accuracy — 10 Choices', bit_colors,
                   chance=0.1, ylim=(0, 1))
    plot_panel_avg(axes[1], df3, 'Accuracy — 2 Choices', bit_colors,
                   chance=0.5, ylim=(0, 1))

    fig.tight_layout()

    save_path = os.path.join(out_dir, "letter_accuracy_step2_step3.png")
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {save_path}")

    fig2, axes2 = plt.subplots(1, 2, figsize=(10, 8), sharey=True)  # each panel set to 3:4 via set_box_aspect
    plot_panel_dprime(axes2[0], df2, "Sensitivity — 10-AFC", bit_colors, m=10)
    plot_panel_dprime(axes2[1], df3, "Sensitivity — 2-AFC", bit_colors, m=2)
    fig2.tight_layout()
    save_path2 = os.path.join(out_dir, "letter_dprime_step2_step3.png")
    fig2.savefig(save_path2, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {save_path2}")