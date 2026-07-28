#!/usr/bin/env python3
"""
LUMINANCE ANALYSIS
==================
Plots luminance gun measurements from the luminance test CSVs.

Produces three figures plus two data files:
  1. luminance_native_10bit.png  - two panels, HDR on vs off: 10-bit pair
                                    (10bit, 10bit_hdr_off) and 8-bit pair
                                    (8bit, 8bit_hdr_off).
  2. luminance_8bit_path.png      - L vs 10-bit value at brightness 0.38:
                                    10bit, dither and 10bit_mon8bit.
  3. luminance_carry.png          - carry / DNL test: one panel per binary
                                    carry transition (256, 512, 768).
  - luminance_summary.csv         - per-patch average and std dev for every
                                    mode, including the complete-black and
                                    complete-white extremes (kept off plots).
  - luminance_stats.md            - per-mode measurement summary.

Black (target 0.0) and white (target 1.0) patches are excluded from every
plot and recorded in luminance_summary.csv only.

Usage:
    python3 luminance_analysis.py
"""

import os
import glob
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, AutoMinorLocator


# ---------------------------------------------------------------
# MP journal figure style: sans-serif, large legible fonts, bold
# black axes, gray gridlines, outside-major / inside-minor ticks.
# ---------------------------------------------------------------
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'Liberation Sans', 'DejaVu Sans'],
    'font.size': 20,
    'axes.titlesize': 20,
    'axes.labelsize': 22,
    'axes.labelcolor': 'black',
    'axes.edgecolor': 'black',
    'axes.linewidth': 2.0,
    'text.color': 'black',
    'xtick.color': 'black',
    'ytick.color': 'black',
    'xtick.labelsize': 18,
    'ytick.labelsize': 18,
    'legend.frameon': False,
    'legend.fontsize': 20,
    'grid.color': '0.7',
    'grid.linewidth': 0.8,
    'savefig.dpi': 600,
})

# ---------------------------------------------------------------
# Uniform theme. One palette for every figure: strong, well
# separated Okabe-Ito hues for the data lines, plus a small set of
# shared accent colours for markers, highlights and reference lines.
# Co-plotted lines are always given different hues; the weak grays
# and the duplicate orange of earlier versions are removed.
# ---------------------------------------------------------------
THEME = {
    "mark":  "#D55E00",   # vertical carry-transition marker line
    "shade": "#A6CEE3",   # plateau highlight span
    "guide": "#566573",   # neutral reference dashed lines (0.0, 1.0)
    "ink":   "#1B2631",   # single-series (carry) data line
}

MODE_INFO = {
    "8bit":          {"label": "8-bit",                 "color": "#0072B2"},
    "8bit_hdr_off":  {"label": "8-bit (HDRi off)",      "color": "#CC79A7"},
    "10bit":         {"label": "10-bit",                "color": "#D55E00"},
    "10bit_hdr_off": {"label": "10-bit (HDRi off)",     "color": "#009E73"},
    "10bit_mon8bit": {"label": "10-bit (monitor 8-bit)", "color": "#CC79A7"},
    "dither":        {"label": "Temporal-dither",       "color": "#009E73"},
    "carry":         {"label": "Carry",                 "color": THEME["ink"]},
    "threshold_8bit":  {"label": "Threshold 8-bit",     "color": "#0072B2"},
    "threshold_10bit": {"label": "Threshold 10-bit",    "color": "#D55E00"},
}

THRESHOLD_MODES = ("threshold_8bit", "threshold_10bit")
EIGHT_BIT_MODES = ("8bit", "8bit_hdr_off")

# carry / DNL test: 10-bit codes are clustered around these binary-carry
# transitions; each gets its own panel.
CARRY_CENTERS = [256, 512, 768]


def mode_info(mode):
    return MODE_INFO.get(mode, {"label": str(mode), "color": "gray"})


def load_csv_files(analysis_dir):
    """Find and load all luminance CSV files."""
    pattern = os.path.join(analysis_dir, "luminance_*.csv")
    files = sorted(glob.glob(pattern))
    # Never read the analysis script's own output back in.
    files = [f for f in files
             if os.path.basename(f) != "luminance_summary.csv"]

    if not files:
        print("No luminance CSV files found in:", analysis_dir)
        print("Run luminance_test.py first.")
        return None

    print(f"Found {len(files)} CSV file(s):")
    for f in files:
        print(f"  {os.path.basename(f)}")

    combined = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    return combined


def extract_curves(data):
    """Build {mode: (grouped_df, means, stds)} for every mode present."""
    curves = {}
    for mode in data['mode'].unique():
        subset = data[data['mode'] == mode]
        if subset.empty:
            continue
        grouped = subset.groupby('patch_number').agg(
            value=('value', 'first'),
            target_float=('target_float', 'first'),
            m1=('measurement_1', 'first'),
            m2=('measurement_2', 'first'),
            m3=('measurement_3', 'first'),
        ).reset_index().sort_values('patch_number').reset_index(drop=True)
        ms = grouped[['m1', 'm2', 'm3']].values
        means = ms.mean(axis=1)
        stds = ms.std(axis=1, ddof=1)
        curves[mode] = (grouped, means, stds)
    return curves


def mode_xcodes(mode, grouped):
    """Return x positions for a mode on a common 10-bit code scale.
    8-bit codes are mapped up via value << 2 so 8-bit and 10-bit curves
    align on the same axis."""
    val = grouped['value'].astype(float).values
    if mode in EIGHT_BIT_MODES:
        return (val.astype(int) << 2).astype(float)
    return val


def interior_mask(grouped):
    """Boolean mask dropping the black (0.0) and white (1.0) extremes."""
    tf = grouped['target_float'].astype(float).values
    return (tf > 0.0) & (tf < 1.0)


def interior_xy(mode, grouped, means, stds):
    """Common 10-bit x, mean, std for a mode's interior patches, sorted by x.
    Black and white are dropped via interior_mask."""
    interior = interior_mask(grouped)
    x = mode_xcodes(mode, grouped)[interior]
    order = np.argsort(x)
    return x[order], means[interior][order], stds[interior][order]


def style_axes(ax):
    """Apply MP house style: bold black box, gray gridlines, outside-major
    and inside-minor tick marks."""
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(2.0)
    ax.tick_params(which='major', direction='out', length=8, width=2.0,
                   colors='black')
    ax.tick_params(which='minor', direction='in', length=4, width=1.2,
                   colors='black')
    ax.grid(True, which='major', color='0.7', linewidth=0.8)


def save_fig(fig, analysis_dir, name):
    path = os.path.join(analysis_dir, name)
    fig.savefig(path, dpi=600, bbox_inches='tight')
    print(f"Saved: {path}")
    plt.close(fig)


# ---------------------------------------------------------------
# 1. Native 10-bit at brightness 1.0
# ---------------------------------------------------------------
def plot_native_10bit(curves, analysis_dir):
    """Two panels of HDR on vs HDR off, on a 10-bit value axis: the 10-bit
    pair (10bit, 10bit_hdr_off) at brightness 1.0 and the 8-bit pair (8bit,
    8bit_hdr_off) at brightness 0.38."""
    panels = [("10bit", "10bit_hdr_off"), ("8bit", "8bit_hdr_off")]
    fig, axes = plt.subplots(1, 2, figsize=(22, 9))
    any_drawn = False
    for ax, modes in zip(axes, panels):
        drawn = {}
        for mode in modes:
            if mode not in curves:
                continue
            x, y, s = interior_xy(mode, *curves[mode])
            info = mode_info(mode)
            ax.errorbar(x, y, yerr=2 * s, fmt='o-', color=info['color'],
                        label=info['label'], capsize=3, markersize=7,
                        linewidth=2.2)
            drawn[mode] = (x, y)
        if not drawn:
            continue
        any_drawn = True

        # Double-headed arrow between the two lines, labelled with the mean
        # per-value luminance gap and its sample std (cd/m^2).
        if len(drawn) == 2:
            (xa, ya), (xb, yb) = drawn[modes[0]], drawn[modes[1]]
            common = np.intersect1d(xa, xb)
            if len(common) >= 2:
                da = ya[np.isin(xa, common)]
                db = yb[np.isin(xb, common)]
                diff = db - da
                mean_d, std_d = float(np.mean(diff)), float(np.std(diff, ddof=1))
                # Place the arrow midway between two adjacent values so it
                # does not sit on a measured data point.
                mid = max(1, len(common) // 3)
                xpos = float(common[mid - 1] + common[mid]) / 2.0
                y0 = float(da[mid - 1] + da[mid]) / 2.0
                y1 = float(db[mid - 1] + db[mid]) / 2.0
                ax.annotate('', xy=(xpos, y1), xytext=(xpos, y0),
                            arrowprops=dict(arrowstyle='<->', color='black',
                                            lw=2))
                ax.text(xpos + 0.4, (y0 + y1) / 2.0,
                        f"Δ = {mean_d:.2f} ± {std_d:.2f} cd/m²",
                        ha='left', va='center', fontsize=20,
                        bbox=dict(boxstyle='round', fc='white', ec='0.5',
                                  alpha=0.9))

        ax.set_xlabel("10-bit value")
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.xaxis.set_minor_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        style_axes(ax)
        ax.legend(loc='upper left')

    if not any_drawn:
        plt.close(fig)
        return

    axes[0].set_ylabel("Luminance (cd/m²)")
    fig.tight_layout()
    save_fig(fig, analysis_dir, "luminance_native_10bit.png")


# ---------------------------------------------------------------
# 2. 8-bit-output path at brightness 0.38
# ---------------------------------------------------------------
def plot_8bit_path(curves, analysis_dir):
    """L vs 10-bit code for the 10-bit runs at brightness 0.38: temporal
    dither and 10-bit values sent to a monitor in 8-bit mode."""
    fig, ax = plt.subplots(figsize=(13, 9))
    drawn = False
    for mode in ("10bit", "dither", "10bit_mon8bit"):
        if mode not in curves:
            continue
        x, y, s = interior_xy(mode, *curves[mode])
        info = mode_info(mode)
        ax.errorbar(x, y, yerr=2 * s, fmt='o-', color=info['color'],
                    label=info['label'], capsize=3, markersize=7,
                    linewidth=2.2)
        drawn = True
    if not drawn:
        plt.close(fig)
        return

    ax.set_xlabel("10-bit value")
    ax.set_ylabel("Luminance (cd/m²)")
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    style_axes(ax)
    ax.legend(loc='upper left')
    fig.tight_layout()
    save_fig(fig, analysis_dir, "luminance_8bit_path.png")


# ---------------------------------------------------------------
# 3. Carry / DNL test, one panel per transition
# ---------------------------------------------------------------
def plot_carry(curves, analysis_dir):
    """One panel per binary-carry transition (256, 512, 768). Each shows L vs
    10-bit code for that cluster with 2sigma error bars and a dashed line at
    the carry code. Panels do not share a y-axis: the three clusters sit at
    very different luminance levels."""
    if "carry" not in curves:
        return
    grouped, means, stds = curves["carry"]
    codes = grouped['value'].astype(int).values
    info = mode_info("carry")

    fig, axes = plt.subplots(1, len(CARRY_CENTERS), figsize=(20, 7))
    if len(CARRY_CENTERS) == 1:
        axes = [axes]

    for ax, center in zip(axes, CARRY_CENTERS):
        sel = np.abs(codes - center) <= 8
        if not np.any(sel):
            continue
        xs = codes[sel].astype(float)
        ys = means[sel]
        ss = stds[sel]
        order = np.argsort(xs)
        xs, ys, ss = xs[order], ys[order], ss[order]
        ax.errorbar(xs, ys, yerr=2 * ss, fmt='o-', color=info['color'],
                    capsize=3, markersize=7, linewidth=2.2)

        # Shade the plateau at the carry transition: the maximal run of
        # consecutive values that spans the carry center and whose steps are
        # not distinguishable from zero at 2 sigma.
        flat = np.abs(np.diff(ys)) <= 2.0 * np.maximum(ss[:-1], ss[1:])
        i = 0
        while i < len(flat):
            if flat[i]:
                k = i
                while k < len(flat) and flat[k]:
                    k += 1
                if xs[i] <= center <= xs[k]:
                    ax.axvspan(xs[i], xs[k], color=THEME["shade"], alpha=0.55,
                               linewidth=0)
                i = k
            else:
                i += 1

        ax.axvline(center, color=THEME["mark"], linewidth=2.0, linestyle='--')
        ax.annotate(f"carry @ {center}", xy=(0.5, 0.97),
                    xycoords='axes fraction', ha='center', va='top',
                    fontsize=22)
        ax.set_xlabel("10-bit value")
        ax.xaxis.set_major_locator(MultipleLocator(2))
        ax.xaxis.set_minor_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        style_axes(ax)

    axes[0].set_ylabel("Luminance (cd/m²)")
    fig.tight_layout()
    save_fig(fig, analysis_dir, "luminance_carry.png")


def mode_stats(mode, grouped, means, stds):
    """Per-mode resolution and extreme stats over the interior patches.
    Returns a dict of values; uncertainties are 2sigma, in cd/m^2."""
    info = mode_info(mode)
    interior = interior_mask(grouped)
    m = means[interior]
    s = stds[interior]
    diffs = np.abs(np.diff(m))
    if len(diffs):
        thresh = 2.0 * np.maximum(s[:-1], s[1:])
        distinct = int(np.sum(diffs > thresh)) + 1
        mean_step = float(np.mean(diffs))
    else:
        distinct = len(m)
        mean_step = 0.0
    return {
        "mode": mode,
        "label": info["label"],
        "n": len(m),
        "distinct": distinct,
        "mean_step": mean_step,
        "black": float(means[0]),
        "black_2s": float(2 * stds[0]),
        "white": float(means[-1]),
        "white_2s": float(2 * stds[-1]),
    }


def write_summary_csv(data, curves, analysis_dir):
    """Per-patch average and standard deviation for every mode, written to a
    CSV. This file is the home for the complete-black and complete-white
    extremes, which are excluded from the plots. The std is the sample
    (ddof=1) std over the 3 readings, matching the plot error bars."""
    rows = []
    for mode, (grouped, means, stds) in curves.items():
        for i in range(len(grouped)):
            g = grouped.iloc[i]
            rows.append({
                "mode": mode,
                "patch_number": int(g['patch_number']),
                "value": g['value'],
                "target_float": g['target_float'],
                "average": round(float(means[i]), 4),
                "std_dev": round(float(stds[i]), 4)
                if not np.isnan(stds[i]) else 0.0,
            })
    out = pd.DataFrame(rows)
    path = os.path.join(analysis_dir, "luminance_summary.csv")
    out.to_csv(path, index=False)
    print(f"Saved: {path}")
    return path


def read_edid_info():
    """Read the connected monitor's declared info from its EDID via
    edid-decode. Returns {name, gamma, bits} (any key may be missing) or {}
    if no EDID / edid-decode is available."""
    info = {}
    for path in sorted(glob.glob("/sys/class/drm/*/edid")):
        try:
            with open(path, "rb") as f:
                raw = f.read()
            if not raw:
                continue
            out = subprocess.run(["edid-decode"], input=raw,
                                  capture_output=True).stdout.decode(
                                      "utf-8", "replace")
        except (OSError, ValueError):
            continue
        if "Basic Display Parameters" not in out:
            continue
        for line in out.splitlines():
            ls = line.strip()
            if ls.startswith("Display Product Name:"):
                info["name"] = ls.split(":", 1)[1].strip().strip("'")
            elif ls.startswith("Gamma:"):
                info["gamma"] = ls.split(":", 1)[1].strip()
            elif ls.startswith("Bits per primary color channel:"):
                info["bits"] = ls.split(":", 1)[1].strip()
        if info:
            return info
    return info


def write_stats_md(data, curves, analysis_dir):
    """Write all per-mode measurement stats to a Markdown file (kept off the
    figure itself, per MP style). Returns the path written."""
    rows = [mode_stats(m, *curves[m]) for m in curves]
    meta = data.iloc[0]
    edid = read_edid_info()

    lines = ["# Luminance Test — Measurement Summary", ""]
    if edid.get("name"):
        lines.append(f"- **Display (EDID):** {edid['name']}  ")
    lines.append(f"- **Output:** {meta['monitor_name']}  ")
    lines.append(f"- **Resolution / refresh:** {meta['resolution']} @ "
                 f"{meta['refresh_rate']} Hz  ")
    lines.append(f"- **Brightness:** {meta['brightness']}  ")
    if edid.get("gamma"):
        lines.append(f"- **Screen gamma (EDID, declared):** "
                     f"{edid['gamma']}  ")
    lines.append(f"- **GPU LUT gamma (xrandr):** "
                 f"{meta['gamma_r']}/{meta['gamma_g']}/{meta['gamma_b']}  ")
    bits = edid.get("bits", "?")
    lines.append(f"- **Bits per channel:** EDID {bits}; framebuffer "
                 f"R={meta['fb_red_bits']} G={meta['fb_green_bits']} "
                 f"B={meta['fb_blue_bits']}  ")
    lines.append("- **N:** 3 readings per patch. Uncertainties and ± are 2σ.")
    lines.append("")
    lines.append("| Mode | Distinguishable steps (2σ) | Mean \\|Δ\\| (cd/m²) | "
                 "Black (cd/m²) | White (cd/m²) |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['label']} | {r['distinct']}/{r['n']} | "
            f"{r['mean_step']:.2f} | {r['black']:.2f} ± {r['black_2s']:.2f} | "
            f"{r['white']:.2f} ± {r['white_2s']:.2f} |"
        )
    lines.append("")

    path = os.path.join(analysis_dir, "luminance_stats.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Saved: {path}")
    return path


def main():
    analysis_dir = os.path.dirname(os.path.abspath(__file__))
    data = load_csv_files(analysis_dir)

    if data is None:
        return

    print(f"\nTotal rows: {len(data)}")
    print(f"Modes found: {list(data['mode'].unique())}")

    curves = extract_curves(data)
    # Always write the per-patch average/std CSV: it holds the complete-black
    # and complete-white extremes, which are kept off the plots.
    write_summary_csv(data, curves, analysis_dir)

    try:
        plot_native_10bit(curves, analysis_dir)
        plot_8bit_path(curves, analysis_dir)
        plot_carry(curves, analysis_dir)
    except Exception as e:
        print(f"Plotting failed ({e}); see luminance_summary.csv.")

    write_stats_md(data, curves, analysis_dir)


if __name__ == "__main__":
    main()
