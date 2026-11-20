#!/usr/bin/env python3
"""
PLOT_CALIBRATION_CONVERGENCE.PY - QUEST Convergence Check
==========================================================
For each participant, plot the QUEST staircase averaged across the two
blocks (trial-by-trial mean) and verify that the calibration converged
toward the 75% performance target.

Per panel (one participant):
  - x: trial position within a block (1..N)
  - y: mean log_contrast across Block 1 and Block 2 at that trial position
  - marker color = proportion correct across the two blocks at that
    position: green = both correct, orange = 1 of 2, red = both wrong
  - solid blue horizontal line = final averaged threshold (mean of blocks)
  - annotated text shows mean tail accuracy across the two blocks
    (last N trials of each block, then averaged). Target = 0.75.
"""

import os
import glob
import json
import math
import numpy as np
import matplotlib.pyplot as plt

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(ANALYSIS_DIR), "Emulated_Data")
OUT_PATH = os.path.join(ANALYSIS_DIR, "calibration_convergence.png")
GROUPS_OUT_PATH = os.path.join(
    os.path.dirname(ANALYSIS_DIR), "analysis", "calibration_convergence_groups.png"
)

TARGET_P = 0.75            # QUEST target performance level
TAIL_TRIALS = 20           # trials at the end of each block used for the convergence check
CONVERGENCE_TOLERANCE = 0.10  # |p_emp - 0.75| <= tol --> "converged"

# Three-group comparison: COD Mo, CO, NH
COD_DIR = os.path.join(os.path.dirname(ANALYSIS_DIR), "Emulated_Data")
OLD_DIR = os.path.join(os.path.dirname(ANALYSIS_DIR), "old data")
GROUP_FOLDERS = {
    'COD (P003)': (COD_DIR, ['P003_8bit', 'P003_10bit']),
    'CO':       (OLD_DIR, ['COTest_8bit', 'COTest_10bit']),
    'NH':       (OLD_DIR, ['NHTest_8bit', 'NHTest_10bit']),
}
BIT_COLORS = {'8bit': '#0072B2', '10bit': '#D55E00'}


def load_calibration_files(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "*", "*_calibration_threshold.json")))
    return _build_sessions(files)


def load_calibration_from_folders(base_dir, folder_names):
    files = []
    for folder in folder_names:
        files += sorted(glob.glob(
            os.path.join(base_dir, folder, "*_calibration_threshold.json")
        ))
    sessions = _build_sessions(files)
    # Tag with the bit-depth derived from the folder name
    for s, f in zip(sessions, files):
        folder = os.path.basename(os.path.dirname(f))
        s["bit"] = "10bit" if "10bit" in folder.lower() else (
            "8bit" if "8bit" in folder.lower() else "unknown"
        )
    return sessions


def _build_sessions(files):
    sessions = []
    for f in files:
        with open(f, "r") as fh:
            d = json.load(fh)
        if "trial_log" not in d or not d["trial_log"]:
            continue
        pid = d.get("participant", {}).get("name") or os.path.basename(os.path.dirname(f))
        blocks = {}
        for t in d["trial_log"]:
            blocks.setdefault(t.get("block", 1), []).append(t)
        sessions.append({
            "id": pid,
            "path": f,
            "blocks": blocks,
            "final_log10": d.get("threshold_log10"),
        })
    return sessions


def averaged_block_arrays(blocks):
    """Return (trial_pos, mean_log_contrast, mean_correct) averaged across blocks.
    At each trial position i, take the mean across all blocks that have a
    trial at that position."""
    block_ids = sorted(blocks.keys())
    max_n = max(len(blocks[b]) for b in block_ids)

    pos, mean_y, mean_c = [], [], []
    for i in range(max_n):
        ys, cs = [], []
        for b in block_ids:
            if i < len(blocks[b]):
                t = blocks[b][i]
                if t.get("log_contrast") is not None:
                    ys.append(t["log_contrast"])
                    cs.append(1.0 if t.get("is_correct") else 0.0)
        if ys:
            pos.append(i + 1)
            mean_y.append(np.mean(ys))
            mean_c.append(np.mean(cs))
    return np.array(pos), np.array(mean_y), np.array(mean_c)


def tail_accuracy_avg(blocks, n_tail=TAIL_TRIALS):
    """Mean tail accuracy across blocks: per-block tail accuracy, then averaged."""
    per_block = []
    for b in sorted(blocks.keys()):
        trials = blocks[b][-n_tail:]
        if not trials:
            continue
        per_block.append(sum(1 for t in trials if t.get("is_correct")) / len(trials))
    if not per_block:
        return None, 0
    return float(np.mean(per_block)), n_tail


def plot_panel(ax, session):
    blocks = session["blocks"]
    pid = session["id"]

    pos, mean_y, mean_c = averaged_block_arrays(blocks)

    # Continuous trace
    ax.plot(pos, mean_y, color="0.6", linewidth=0.8, zorder=1)

    # Color markers by mean correctness at each position
    color_map = {0.0: "#c0392b", 0.5: "#e67e22", 1.0: "#2a8f3d"}
    for level, color in color_map.items():
        mask = np.isclose(mean_c, level)
        if mask.any():
            label = {0.0: "both wrong", 0.5: "1 of 2 correct",
                     1.0: "both correct"}[level]
            marker = "x" if level == 0.0 else "o"
            size = 26 if level == 0.0 else 16
            ax.scatter(pos[mask], mean_y[mask], s=size, c=color,
                       marker=marker, linewidths=1.4 if marker == "x" else 0,
                       zorder=3, label=label)

    final_thr = session["final_log10"]
    if final_thr is not None and len(pos):
        ax.hlines(final_thr, pos[0], pos[-1],
                  colors="#1f3a93", linestyles="-",
                  linewidth=1.6, zorder=2, label="final threshold")

    p_emp, n = tail_accuracy_avg(blocks)
    converged = (p_emp is not None
                 and abs(p_emp - TARGET_P) <= CONVERGENCE_TOLERANCE)

    title_color = "#1a6b2e" if converged else "#8b1a1a"
    ax.set_title(pid, fontsize=10, color=title_color, fontweight="bold")

    if p_emp is not None:
        mark = "OK" if converged else "X"
        ax.text(
            0.98, 0.95,
            f"tail-{n} avg: {p_emp*100:.0f}% [{mark}]\nthr={final_thr:.3f}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.25", fc="white",
                      ec="0.7", alpha=0.85),
        )

    ax.set_xlabel("Trial position (blocks averaged)", fontsize=8)
    ax.set_ylabel("log10 contrast (mean of blocks)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)


def main():
    sessions = load_calibration_files(DATA_DIR)
    if not sessions:
        print(f"No calibration files found under {DATA_DIR}")
        return

    n = len(sessions)
    n_cols = 4
    n_rows = math.ceil(n / n_cols)

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(n_cols * 3.6, n_rows * 2.6),
        sharey=False,
    )
    axes = np.atleast_2d(axes)

    summary_rows = []
    for i, s in enumerate(sessions):
        ax = axes[i // n_cols, i % n_cols]
        plot_panel(ax, s)
        p_emp, _ = tail_accuracy_avg(s["blocks"])
        summary_rows.append((s["id"], p_emp, s["final_log10"]))

    for j in range(n, n_rows * n_cols):
        axes[j // n_cols, j % n_cols].axis("off")

    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor="#2a8f3d", markersize=6, label="both correct"),
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor="#e67e22", markersize=6, label="1 of 2 correct"),
        plt.Line2D([0], [0], marker="x", color="#c0392b",
                   linestyle="None", markersize=7, label="both wrong"),
        plt.Line2D([0], [0], color="#1f3a93", linewidth=1.6,
                   label="final threshold (mean of blocks)"),
    ]
    fig.legend(
        handles=handles, loc="upper center",
        bbox_to_anchor=(0.5, 1.0), ncol=4, frameon=False, fontsize=9,
    )

    fig.suptitle(
        f"QUEST calibration convergence (blocks averaged) — target p(correct) = {TARGET_P:.2f} "
        f"(tail = last {TAIL_TRIALS} trials per block, tolerance ±{CONVERGENCE_TOLERANCE:.2f})",
        fontsize=11, y=1.03,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.99])
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"Saved: {OUT_PATH}")

    print("\nConvergence summary (mean tail accuracy across blocks vs 75% target):")
    print(f"{'ID':<22} {'Tail %':>10} {'Threshold':>12}   Status")
    for pid, p_emp, thr in summary_rows:
        if p_emp is None:
            status = "no data"
            tail_str = "   --   "
        else:
            ok = abs(p_emp - TARGET_P) <= CONVERGENCE_TOLERANCE
            status = "converged" if ok else "FAILED"
            tail_str = f"  {p_emp*100:5.1f}%"
        thr_str = f"{thr:>10.3f}" if thr is not None else "    --    "
        print(f"{pid:<22} {tail_str:>10} {thr_str:>12}   {status}")

    plot_groups()


def plot_groups():
    """3-panel comparison: COD (P003) vs CO vs NH calibration trajectories."""
    group_sessions = {
        name: load_calibration_from_folders(base, folders)
        for name, (base, folders) in GROUP_FOLDERS.items()
    }

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)
    handles_seen = {}

    for ax, (name, sessions) in zip(axes, group_sessions.items()):
        if not sessions:
            ax.set_title(f"{name} — no data")
            ax.axis("off")
            continue

        for s in sessions:
            bit = s.get("bit", "unknown")
            color = BIT_COLORS.get(bit, "0.5")
            pos, mean_y, _ = averaged_block_arrays(s["blocks"])
            line, = ax.plot(pos, mean_y, color=color, linewidth=1.1,
                            alpha=0.85, label=bit)
            handles_seen.setdefault(bit, line)

            if s["final_log10"] is not None and len(pos):
                ax.hlines(s["final_log10"], pos[0], pos[-1],
                          colors=color, linestyles="--",
                          linewidth=1.0, alpha=0.7)

        # Annotate tail accuracy / threshold for each session
        lines = []
        for s in sessions:
            p_emp, _ = tail_accuracy_avg(s["blocks"])
            tag = s.get("bit", "?")
            thr = s["final_log10"]
            tail_str = f"{p_emp*100:.0f}%" if p_emp is not None else "--"
            thr_str = f"{thr:.3f}" if thr is not None else "--"
            lines.append(f"{tag}: tail={tail_str}  thr={thr_str}")
        ax.text(0.02, 0.04, "\n".join(lines), transform=ax.transAxes,
                ha="left", va="bottom", fontsize=8, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white",
                          ec="0.7", alpha=0.9))

        ax.set_title(name, fontsize=11, fontweight="bold")
        ax.set_xlabel("Trial position (blocks averaged)")
        ax.set_ylabel("log10 contrast (mean of blocks)")
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    if handles_seen:
        fig.legend(handles=list(handles_seen.values()),
                   labels=list(handles_seen.keys()),
                   loc="upper center", bbox_to_anchor=(0.5, 1.02),
                   ncol=len(handles_seen), frameon=False)
    fig.suptitle(
        f"QUEST calibration convergence — group comparison "
        f"(target p={TARGET_P:.2f}, dashed = final threshold)",
        fontsize=11, y=1.06,
    )
    fig.tight_layout()
    fig.savefig(GROUPS_OUT_PATH, dpi=150, bbox_inches="tight")
    print(f"\nSaved: {GROUPS_OUT_PATH}")


if __name__ == "__main__":
    main()