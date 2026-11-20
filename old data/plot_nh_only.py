#!/usr/bin/env python3
"""Compare COD (original Data/) vs CO (old data/COTest_*) vs NH (old data/NHTest_*).
Three groups on x-axis, 8-bit and 10-bit bars per group.
Reuses helpers from plot_results.py."""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from plot_results import (
    detect_bit_depth,
    dprime_from_pc,
)


GROUP_FOLDERS = {
    'COD': ['P003_8bit', 'P003_10bit'],
    'CO':  ['COTest_8bit', 'COTest_10bit'],
    'NH':  ['NHTest_8bit', 'NHTest_10bit'],
}


def load_folders(data_dir, folders, step):
    rows = []
    for i, folder in enumerate(folders):
        pattern = os.path.join(data_dir, folder, f"*_{step}_SR_Binocular_trials.csv")
        for csv_file in sorted(glob.glob(pattern)):
            df = pd.read_csv(csv_file)
            df['participant'] = i + 1
            df['bit_depth'] = detect_bit_depth(folder)
            rows.append(df)
    if not rows:
        return None
    return pd.concat(rows, ignore_index=True)


def plot_groups_avg(ax, group_dfs, title, bit_colors, chance=0.5, ylim=(0, 1)):
    """Grouped bars: x-axis = group, bars within = bit_depth."""
    groups = list(group_dfs.keys())
    bits = list(bit_colors.keys())
    x = np.arange(len(groups))
    n_bits = len(bits)
    width = 0.8 / n_bits

    drawn = set()
    for i, bit in enumerate(bits):
        means, sems, ns = [], [], []
        for g in groups:
            df = group_dfs[g]
            if df is None or df.empty or bit not in df['bit_depth'].unique():
                means.append(np.nan); sems.append(0); ns.append(0); continue
            sub = df[df['bit_depth'] == bit]
            per_part = sub.groupby('participant')['AnswerCorrect'].mean()
            means.append(per_part.mean())
            sems.append(per_part.std(ddof=1) / np.sqrt(len(per_part)) if len(per_part) > 1 else 0.0)
            ns.append(len(per_part))
        offset = (i - (n_bits - 1) / 2) * width
        valid = ~np.isnan(means)
        ax.bar(x[valid] + offset, np.array(means)[valid], width,
               yerr=np.array(sems)[valid], capsize=3,
               color=bit_colors[bit], edgecolor='black', linewidth=0.8,
               label=f'{bit}')
        drawn.add(bit)
        # annotate N above each bar
        for xi, m, n in zip(x[valid], np.array(means)[valid], np.array(ns)[valid]):
            ax.text(xi + offset, m + 0.02, f'N={n}', ha='center', va='bottom', fontsize=8)

    ax.axhline(chance, color='gray', linestyle='--', linewidth=0.8,
               label=f'Chance ({int(chance * 100)}%)')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 1e-9, 0.1))
    ax.set_xlabel('Group')
    ax.set_ylabel('Proportion correct')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False)


def plot_groups_dprime(ax, group_dfs, title, bit_colors, m, ylim=(0.0, 5.0)):
    """Grouped d' bars: x-axis = group, bars within = bit_depth."""
    groups = list(group_dfs.keys())
    bits = list(bit_colors.keys())
    x = np.arange(len(groups))
    n_bits = len(bits)
    width = 0.8 / n_bits

    for i, bit in enumerate(bits):
        means, sems, ns = [], [], []
        for g in groups:
            df = group_dfs[g]
            if df is None or df.empty or bit not in df['bit_depth'].unique():
                means.append(np.nan); sems.append(0); ns.append(0); continue
            sub = df[df['bit_depth'] == bit]
            per_part = sub.groupby('participant')['AnswerCorrect'].agg(['mean', 'count'])
            pc_corr = per_part['mean'].where(
                per_part['mean'] < 1.0,
                1.0 - 1.0 / (2.0 * per_part['count'])
            )
            dprimes = pc_corr.apply(lambda p: dprime_from_pc(p, m))
            means.append(dprimes.mean())
            sems.append(dprimes.std(ddof=1) / np.sqrt(len(dprimes)) if len(dprimes) > 1 else 0.0)
            ns.append(len(dprimes))
        offset = (i - (n_bits - 1) / 2) * width
        valid = ~np.isnan(means)
        ax.bar(x[valid] + offset, np.array(means)[valid], width,
               yerr=np.array(sems)[valid], capsize=3,
               color=bit_colors[bit], edgecolor='black', linewidth=0.8,
               label=f'{bit}')
        for xi, mv, n in zip(x[valid], np.array(means)[valid], np.array(ns)[valid]):
            ax.text(xi + offset, mv + 0.05, f'N={n}', ha='center', va='bottom', fontsize=8)

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_xlabel(f'Group ({m}-AFC)')
    ax.set_ylabel("d′ (sensitivity)")
    ax.set_ylim(*ylim)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 1e-9, 1.0))
    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='upper right', frameon=False)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cod_dir = os.path.join(base_dir, "Emulated_Data")
    old_dir = os.path.join(base_dir, "old data")
    out_dir = os.path.dirname(os.path.abspath(__file__))

    groups_step2 = {
        'COD': load_folders(cod_dir, GROUP_FOLDERS['COD'], "step2"),
        'CO':  load_folders(old_dir, GROUP_FOLDERS['CO'],  "step2"),
        'NH':  load_folders(old_dir, GROUP_FOLDERS['NH'],  "step2"),
    }
    groups_step3 = {
        'COD': load_folders(cod_dir, GROUP_FOLDERS['COD'], "step3"),
        'CO':  load_folders(old_dir, GROUP_FOLDERS['CO'],  "step3"),
        'NH':  load_folders(old_dir, GROUP_FOLDERS['NH'],  "step3"),
    }

    if all(v is None for v in groups_step2.values()) and all(v is None for v in groups_step3.values()):
        print("No step2/step3 data found across COD/CO/NH groups.")
        raise SystemExit(0)

    bit_colors = {'8bit': '#0072B2', '10bit': '#D55E00'}

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    plot_groups_avg(axes[0], groups_step2, 'Accuracy — 10 Choices (step2)',
                    bit_colors, chance=0.1, ylim=(0, 1))
    plot_groups_avg(axes[1], groups_step3, 'Accuracy — 2 Choices (step3)',
                    bit_colors, chance=0.5, ylim=(0, 1))
    fig.tight_layout()
    save_path = os.path.join(out_dir, "../analysis/COD_vs_CO_vs_NH_accuracy.png")
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {save_path}")

    fig2, axes2 = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
    plot_groups_dprime(axes2[0], groups_step2, "Sensitivity — 10-AFC (step2)",
                       bit_colors, m=10)
    plot_groups_dprime(axes2[1], groups_step3, "Sensitivity — 2-AFC (step3)",
                       bit_colors, m=2)
    fig2.tight_layout()
    save_path2 = os.path.join(out_dir, "../analysis/COD_vs_CO_vs_NH_dprime.png")
    fig2.savefig(save_path2, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {save_path2}")