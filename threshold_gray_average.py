#!/usr/bin/env python3
"""
THRESHOLD GRAY COLOUR — AVERAGE ACROSS PARTICIPANTS
====================================================
Converts each participant's contrast-detection threshold into the actual
gray colour of the letter at threshold, then averages it separately for
the 8-bit and 10-bit conditions.

Background and stimulus model (from step1_calibration.py):
    GRAY        = 0.498                      # fixed mid-gray background (0-1)
    letter_gray = GRAY + threshold_linear/255   # letter shade at threshold (0-1)

The same float shade is quantised onto a different code grid per condition:
    8-bit  code = round(letter_gray * 255)
    10-bit code = round(letter_gray * 1023)

Participant data is read from ../Data/<name>_<bits>bit/*_calibration_threshold.json
(relative to this file). As participants are added, the averages update on
the next run.

Usage:
    python3 threshold_gray_average.py
"""

import os
import glob
import json
import numpy as np
import matplotlib.pyplot as plt


GRAY = 0.498              # fixed mid-gray background, normalised 0-1
MAXCODE = {'8bit': 255, '10bit': 1023}
COLORS = {'8bit': '#0072B2', '10bit': '#D55E00'}


def letter_gray_float(threshold_linear):
    """Normalised (0-1) gray shade of the letter at detection threshold."""
    return GRAY + threshold_linear / 255.0


def load_thresholds(data_dir):
    """Return (rows, groups).

    rows: list of per-participant dicts.
    groups: {'8bit': [code, ...], '10bit': [code, ...]} of letter codes
            at threshold, on each condition's native code grid.
    """
    groups = {'8bit': [], '10bit': []}
    rows = []

    pattern = os.path.join(data_dir, "*", "*_calibration_threshold.json")
    for path in sorted(glob.glob(pattern)):
        with open(path) as f:
            d = json.load(f)
        folder = os.path.basename(os.path.dirname(path))
        low = folder.lower()
        bits = '10bit' if '10bit' in low else ('8bit' if '8bit' in low else None)
        if bits is None:
            continue

        t_lin = d['threshold_linear']
        name = d.get('participant', {}).get('name', folder)

        gray_f = letter_gray_float(t_lin)
        maxcode = MAXCODE[bits]
        bg_code = GRAY * maxcode
        letter_code = gray_f * maxcode
        delta_code = letter_code - bg_code

        groups[bits].append(letter_code)
        rows.append({
            'name': name,
            'bits': bits,
            'threshold_linear': t_lin,
            'gray_float': gray_f,
            'bg_code': bg_code,
            'letter_code': letter_code,
            'delta_code': delta_code,
        })
    return rows, groups


def summarize(groups):
    """Return {bits: {mean, sem, n, ...}} of letter code at threshold."""
    out = {}
    for bits, vals in groups.items():
        arr = np.array(vals, dtype=float)
        n = len(arr)
        if n == 0:
            out[bits] = {'n': 0}
            continue
        mean = arr.mean()
        sd = arr.std(ddof=1) if n > 1 else 0.0
        sem = sd / np.sqrt(n) if n > 1 else 0.0
        out[bits] = {
            'n': n,
            'mean_code': mean,
            'sd_code': sd,
            'sem_code': sem,
            'mean_float': mean / MAXCODE[bits],
            'bg_code': GRAY * MAXCODE[bits],
            'mean_delta': mean - GRAY * MAXCODE[bits],
        }
    return out


def print_summary(rows, stats):
    print("Per-participant threshold gray colour:")
    print(f"  {'Participant':<14} {'Bits':<6} {'thr_lin':>9} "
          f"{'bg code':>9} {'letter code':>12} {'Δcode':>8} {'gray(0-1)':>10}")
    for r in sorted(rows, key=lambda x: (x['bits'], x['name'])):
        print(f"  {r['name']:<14} {r['bits']:<6} {r['threshold_linear']:>9.3f} "
              f"{r['bg_code']:>9.1f} {r['letter_code']:>12.2f} "
              f"{r['delta_code']:>8.2f} {r['gray_float']:>10.4f}")

    print("\nAverage threshold gray colour:")
    for bits in ('8bit', '10bit'):
        s = stats[bits]
        if s['n'] == 0:
            print(f"  {bits}: (no data)")
            continue
        print(f"  {bits} (N={s['n']}): "
              f"letter code = {s['mean_code']:.2f} ± {s['sem_code']:.2f} (SEM)  "
              f"[bg {s['bg_code']:.1f}, Δ = {s['mean_delta']:.2f} codes]  "
              f"| gray = {s['mean_float']:.4f} (0-1)")


def plot_summary(rows, stats, out_dir):
    """Bar of mean letter code at threshold per condition, with participant
    points and the fixed background code marked."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, bits in zip(axes, ('8bit', '10bit')):
        s = stats[bits]
        color = COLORS[bits]
        pts = [r['letter_code'] for r in rows if r['bits'] == bits]

        if s['n']:
            ax.bar([0], [s['mean_code']], yerr=[s['sem_code']], width=0.5,
                   color=color, edgecolor='black', linewidth=0.8, capsize=6,
                   zorder=2)
            for v in pts:
                ax.plot(0, v, 'o', color='black', alpha=0.6, markersize=6,
                        zorder=3)
            ax.axhline(s['bg_code'], color='gray', linestyle='--',
                       linewidth=1.0, zorder=1,
                       label=f"background ({s['bg_code']:.0f})")
            ax.text(0, s['mean_code'], f"  {s['mean_code']:.2f}",
                    va='center', ha='left', fontsize=11, fontweight='bold')
            ax.legend(loc='lower right', frameon=False, fontsize=9)
            ax.set_ylim(s['bg_code'] - 1, max(pts) + 1)

        ax.set_xticks([0])
        ax.set_xticklabels([f"{bits}\n(N={s['n']})"])
        ax.set_ylabel(f"Letter gray code at threshold ({MAXCODE[bits]} max)")
        ax.set_title(f"{bits} condition")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.suptitle("Average Threshold Gray Colour — by Bit Depth")
    fig.tight_layout()
    save_path = os.path.join(out_dir, "threshold_gray_average.png")
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved: {save_path}")
    plt.show()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(here, "Data")

    rows, groups = load_thresholds(data_dir)
    if not rows:
        print(f"No calibration_threshold.json files found under {data_dir}")
        return

    stats = summarize(groups)
    print_summary(rows, stats)
    plot_summary(rows, stats, here)


if __name__ == "__main__":
    main()