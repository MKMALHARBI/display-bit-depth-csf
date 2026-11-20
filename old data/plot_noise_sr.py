#!/usr/bin/env python3
"""
PLOT_NOISE_SR.PY - Stochastic-resonance noise curves
=====================================================
Noise-staircase participants (FG, Mo, OK/OK8) only.
Proportion correct vs noise level, 8-bit vs 10-bit, mean across
participants with SEM error bars. Chance = 1/10 (10 letters).
"""

import os
import re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.linewidth': 1.0,
    'axes.titlesize': 12,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 4,
    'ytick.major.size': 4,
    'legend.frameon': False,
})

# Folders holding the noise-staircase ("plain" SR_Binocular) sessions.
NOISE_FOLDERS = {
    '8bit':  ['P004_8bit', 'P003_8bit', 'P002_8bit'],
    '10bit': ['P004_10bit', 'P003_10bit', 'P001_10bit'],
}
BIT_COLORS = {'8bit': '#0072B2', '10bit': '#D55E00'}
CHANCE = 0.1


def load_noise_data(data_dir):
    rows = []
    for bit, folders in NOISE_FOLDERS.items():
        for folder in folders:
            matches = glob.glob(os.path.join(data_dir, folder, "*_SR_Binocular_trials.csv"))
            matches = [m for m in matches if not re.search(r'_step\d_', os.path.basename(m))]
            for m in matches:
                df = pd.read_csv(m)
                df['bit_depth'] = bit
                df['participant'] = re.sub(r'8?_\d+bit$', '', folder).rstrip('_')
                rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else None


def plot_noise_curve(ax, df):
    noise_levels = sorted(df['NoiseLevel'].unique())
    x = np.arange(len(noise_levels))  # evenly spaced (noise is ~geometric incl. 0)

    for bit in ['8bit', '10bit']:
        sub = df[df['bit_depth'] == bit]
        # per-participant accuracy at each noise level, then mean +/- SEM across participants
        per = sub.groupby(['participant', 'NoiseLevel'])['AnswerCorrect'].mean().reset_index()
        agg = per.groupby('NoiseLevel')['AnswerCorrect'].agg(['mean', 'std', 'count'])
        agg = agg.reindex(noise_levels)
        sem = agg['std'] / np.sqrt(agg['count'])
        n = sub['participant'].nunique()
        ax.errorbar(x, agg['mean'].values, yerr=sem.values,
                    marker='o', markersize=6, capsize=3, linewidth=1.8,
                    color=BIT_COLORS[bit], label=f'{bit} (N={n})')

    ax.axhline(CHANCE, color='gray', linestyle='--', linewidth=0.8,
               label=f'Chance ({int(CHANCE * 100)}%)')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{lv:g}' for lv in noise_levels])
    ax.set_ylim(0, 1.0)
    ax.set_yticks(np.arange(0, 1.1, 0.1))
    ax.set_xlabel('Noise level')
    ax.set_ylabel('Proportion correct')
    ax.set_title('Letter detection vs noise (stochastic resonance)')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right')


if __name__ == "__main__":
    data_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = data_dir

    df = load_noise_data(data_dir)
    if df is None or df.empty:
        print("No noise-staircase data found.")
        raise SystemExit(0)

    fig, ax = plt.subplots(figsize=(9, 6))
    plot_noise_curve(ax, df)
    fig.tight_layout()
    save_path = os.path.join(out_dir, "noise_sr_curve.png")
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {save_path}")