#!/usr/bin/env python3
"""
PLOT_THRESHOLDS.PY - Calibration threshold 10-bit vs 8-bit per participant
==========================================================================
Loads every `*_calibration_threshold.json` under Data/, pairs each
participant's 8-bit and 10-bit sessions, and produces a grouped bar chart
of the final QUEST threshold (log10 contrast and linear contrast).
"""

import os
import re
import glob
import json
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


ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(ANALYSIS_DIR), "Data")
OUT_PATH = os.path.join(ANALYSIS_DIR, "thresholds_8bit_vs_10bit.png")

BIT_DEPTH_RE = re.compile(r'_(\d+)bit$', re.IGNORECASE)
BIT_COLORS = {'8bit': '#0072B2', '10bit': '#D55E00'}


def parse_folder(folder_name):
    """Return (participant_id, bit_depth) from a folder like 'Mo_10bit'."""
    m = BIT_DEPTH_RE.search(folder_name)
    if not m:
        return folder_name, "unknown"
    return BIT_DEPTH_RE.sub('', folder_name), f"{m.group(1)}bit"


def load_thresholds(data_dir):
    """Return dict[participant] -> dict[bit_depth] -> (log10, linear)."""
    files = sorted(glob.glob(os.path.join(data_dir, "*", "*_calibration_threshold.json")))
    out = {}
    for f in files:
        folder = os.path.basename(os.path.dirname(f))
        pid, bit = parse_folder(folder)
        with open(f, "r") as fh:
            d = json.load(fh)
        thr_log = d.get("threshold_log10")
        thr_lin = d.get("threshold_linear")
        if thr_log is None:
            continue
        out.setdefault(pid, {})[bit] = (thr_log, thr_lin)
    return out


def plot_panel(ax, participants, values_by_bit, ylabel, title, errors_by_bit=None):
    x = np.arange(len(participants))
    bit_depths = [b for b in BIT_COLORS.keys() if any(b in values_by_bit[p] for p in participants)]
    n_groups = len(bit_depths)
    width = 0.8 / max(n_groups, 1)

    for i, bit in enumerate(bit_depths):
        heights = [values_by_bit[p].get(bit, np.nan) for p in participants]
        offset = (i - (n_groups - 1) / 2) * width
        errs = None
        if errors_by_bit is not None:
            errs = [errors_by_bit[p].get(bit, 0.0) for p in participants]
        ax.bar(x + offset, heights, width, yerr=errs, capsize=3,
               color=BIT_COLORS[bit], edgecolor='black', linewidth=0.8,
               label=bit)

    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(participants, rotation=20, ha='right')
    ax.set_ylabel(ylabel)
    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(loc='best', frameon=False)


def main():
    data = load_thresholds(DATA_DIR)
    if not data:
        print(f"No calibration thresholds found under {DATA_DIR}")
        return

    participants = sorted(data.keys())
    log_by_bit = {p: {b: v[0] for b, v in data[p].items()} for p in participants}
    lin_by_bit = {p: {b: v[1] for b, v in data[p].items()} for p in participants}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    plot_panel(axes[0], participants, log_by_bit,
               ylabel="Threshold (log10 contrast)",
               title="QUEST threshold — log10 contrast")
    plot_panel(axes[1], participants, lin_by_bit,
               ylabel="Threshold (linear contrast)",
               title="QUEST threshold — linear contrast")

    fig.suptitle("Calibration threshold: 8-bit vs 10-bit per participant", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=150, bbox_inches='tight')
    print(f"Saved: {OUT_PATH}")

    print("\nThreshold summary:")
    print(f"{'Participant':<20} {'8bit log10':>12} {'10bit log10':>12} {'Δ (10-8)':>10}")
    for p in participants:
        t8 = log_by_bit[p].get('8bit')
        t10 = log_by_bit[p].get('10bit')
        d = (t10 - t8) if (t8 is not None and t10 is not None) else None
        s8 = f"{t8:>10.3f}" if t8 is not None else "    --    "
        s10 = f"{t10:>10.3f}" if t10 is not None else "    --    "
        sd = f"{d:>8.3f}" if d is not None else "    --   "
        print(f"{p:<20} {s8:>12} {s10:>12} {sd:>10}")


if __name__ == "__main__":
    main()