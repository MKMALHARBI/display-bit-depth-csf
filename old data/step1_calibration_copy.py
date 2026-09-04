#!/usr/bin/env python3
"""
STEP 1 - QUEST Threshold Calibration (multi-AFC version)
========================================================
Runs three QUEST calibrations back-to-back: 2-AFC, 3-AFC, 5-AFC.
Saves a per-variant `*_{N}AFC_threshold.json` (compatible with step 2)
plus a combined `*_calibration_all.json` with the full trial log,
per-trial QUEST posterior mean/SD, and block-by-block summaries.

OpenGL 10-bit rendering via GLFW + PyOpenGL + FreeType.
"""

import numpy as np
import json
import os
import random
import csv
import glfw
from datetime import datetime

from lib.parameters import params, paths, fonts
from lib.exp_dialog import get_participant_info, create_data_folder, save_participant_info
from lib.display_utils import DisplayCalibration, print_all_displays, setup_display_for_glfw
from lib.gl_renderer import GLRenderer


# Four 3-AFC variants with different letter triplets, to test which
# letter-set properties drive 3-AFC convergence (vs the procedure itself).
# Each config carries an explicit `tag` that becomes part of the filename
# so the four runs don't collide.
N_AFC_CONFIGS = [
    {'n': 3, 'letters': ['O', 'C', 'D'], 'gamma': 1.0 / 3.0, 'tag': '3AFC_OCD'},
    {'n': 3, 'letters': ['G', 'J', 'L'], 'gamma': 1.0 / 3.0, 'tag': '3AFC_GJL'},
    {'n': 3, 'letters': ['Q', 'G', 'O'], 'gamma': 1.0 / 3.0, 'tag': '3AFC_QGO'},
    {'n': 3, 'letters': ['F', 'G', 'H'], 'gamma': 1.0 / 3.0, 'tag': '3AFC_FGH'},
]


class SimpleQUEST:
    """Weibull QUEST. gamma = 1/N for an unbiased N-AFC task."""

    def __init__(self, start_val=0, start_val_sd=4, p_threshold=0.75,
                 beta=3.5, delta=0.01, gamma=0.5, grain=0.2, range_val=5):
        self.p_threshold = p_threshold
        self.beta = beta
        self.delta = delta
        self.gamma = gamma

        self.x = np.arange(-range_val, range_val, grain)
        self.pdf = np.exp(-0.5 * ((self.x - start_val) / start_val_sd) ** 2)
        self.pdf /= self.pdf.sum()

        self.intensities = []
        self.responses = []

    def weibull(self, x, t):
        p = self.delta * self.gamma + (1 - self.delta) * (
            1 - (1 - self.gamma) * np.exp(-10 ** (self.beta * (x - t)))
        )
        return np.clip(p, 0.0001, 0.9999)

    def quantile(self):
        cdf = np.cumsum(self.pdf)
        idx = np.searchsorted(cdf, self.p_threshold)
        idx = np.clip(idx, 0, len(self.x) - 1)
        return self.x[idx]

    def update(self, intensity, response):
        self.intensities.append(intensity)
        self.responses.append(response)
        if response:
            likelihood = self.weibull(intensity, self.x)
        else:
            likelihood = 1 - self.weibull(intensity, self.x)
        self.pdf *= likelihood
        self.pdf /= self.pdf.sum()

    def mean(self):
        return float(np.sum(self.x * self.pdf))

    def sd(self):
        m = self.mean()
        return float(np.sqrt(np.sum(self.pdf * (self.x - m) ** 2)))

    def snapshot(self):
        """Full posterior state for later analysis."""
        return {
            'x_grid': self.x.tolist(),
            'pdf': self.pdf.tolist(),
            'mean': self.mean(),
            'sd': self.sd(),
            'p_threshold': self.p_threshold,
            'beta': self.beta,
            'delta': self.delta,
            'gamma': self.gamma,
        }


def run_calibration_for_config(
        config, renderer, font_stim, font_ui, font_size, frame_size, FPS,
        draw_top_gradient, width, height, trials_per_block, GRAY, BLACK, WHITE, LIGHT_GRAY,
):
    """One 2-block QUEST run with the given config. Returns a result dict
    (and a list of trial dicts), or None if the participant pressed ESC
    before any block completed."""

    n_afc = config['n']
    letters = config['letters']
    gamma = config['gamma']

    frame_x = (width - frame_size[0]) // 2
    frame_y = (height - frame_size[1]) // 2
    frame_cx = width // 2
    frame_cy = height // 2

    block_results = []
    trial_log = []
    running = True

    for block_num in range(1, 3):
        if not running:
            break

        renderer.clear(GRAY)
        if block_num == 1:
            lines = [
                f"{n_afc}-AFC QUEST  -  Block 1 of 2",
                "",
                f"You will see one of these letters: {', '.join(letters)}",
                "Press the matching key.",
                "",
                "Press any key to start.",
            ]
        else:
            lines = [
                f"{n_afc}-AFC Block 1 complete.",
                "",
                f"{n_afc}-AFC Block 2 starting.",
                "",
                "Press any key to continue.",
            ]

        y_offset = height // 2 - 100
        for line in lines:
            if line:
                renderer.draw_text_centered(font_ui, line, width // 2, y_offset, 40, LIGHT_GRAY)
            y_offset += 40
        draw_top_gradient()
        renderer.flip()

        key = renderer.wait_key()
        if key == glfw.KEY_ESCAPE or renderer.should_close():
            running = False
            break

        quest = SimpleQUEST(start_val=-0.5, start_val_sd=4, p_threshold=0.75,
                            range_val=4, gamma=gamma)
        initial_quest_state = quest.snapshot()

        for trial_num in range(1, trials_per_block + 1):
            if not running:
                break

            trial_wall_time = datetime.now().isoformat()
            log_contrast = float(quest.quantile())
            contrast = 10 ** log_contrast
            contrast = float(np.clip(contrast, 0.0001, 255.0))

            correct_letter = random.choice(letters)
            letter_gray = float(GRAY + contrast / 255.0)

            # Show stimulus
            n_frames = int(params['stim_duration'] * FPS)
            for frame in range(n_frames):
                renderer.poll_events()
                key = renderer.poll_key()
                if key == glfw.KEY_ESCAPE or renderer.should_close():
                    running = False
                    break

                renderer.clear(GRAY)
                renderer.draw_rect_outline(frame_x, frame_y, frame_size[0], frame_size[1], WHITE, 2)
                renderer.draw_text_centered(font_stim, correct_letter,
                                            frame_cx, frame_cy, font_size, letter_gray)
                draw_top_gradient()
                renderer.flip()

            if not running:
                break

            # Response screen
            renderer.clear(GRAY)
            prompt = f"{n_afc}-AFC  Block {block_num} - Trial {trial_num}/{trials_per_block}"
            renderer.draw_text_centered(font_ui, prompt, width // 2, height // 2 - 50, 40, LIGHT_GRAY)
            renderer.draw_text_centered(font_ui, f"Which letter? Press one of: {', '.join(letters)}",
                                        width // 2, height // 2 + 10, 40, LIGHT_GRAY)
            draw_top_gradient()
            renderer.flip()

            response = None
            confirmed = False
            response_start = renderer.get_time()

            while not confirmed and running:
                key = renderer.wait_key()
                if key is None:
                    continue
                if key == glfw.KEY_ESCAPE or renderer.should_close():
                    running = False
                    break
                elif key == glfw.KEY_SPACE and response:
                    confirmed = True
                else:
                    letter = GLRenderer.key_to_letter(key)
                    if letter and letter in letters:
                        response = letter

                if response and not confirmed:
                    renderer.clear(GRAY)
                    renderer.draw_text_centered(font_ui, f"You selected: {response}",
                                                width // 2, height // 2 - 30, 40, LIGHT_GRAY)
                    renderer.draw_text_centered(font_ui, "SPACE to confirm, or press another letter",
                                                width // 2, height // 2 + 30, 40, LIGHT_GRAY)
                    draw_top_gradient()
                    renderer.flip()

            if not running:
                break

            reaction_time_ms = int((renderer.get_time() - response_start) * 1000)
            is_correct = (response == correct_letter)
            quest.update(log_contrast, is_correct)

            trial_log.append({
                'n_afc': n_afc,
                'gamma': gamma,
                'block': block_num,
                'trial': trial_num,
                'wall_time': trial_wall_time,
                'correct_letter': correct_letter,
                'response': response,
                'is_correct': bool(is_correct),
                'contrast': contrast,
                'log_contrast': log_contrast,
                'letter_gray_displayed': letter_gray,
                'reaction_time_ms': reaction_time_ms,
                'quest_mean_after': quest.mean(),
                'quest_sd_after': quest.sd(),
                # Full posterior over t after this trial's update. Grid is
                # the same `x_grid` as in `final_quest_state` (~40 floats),
                # so storing per trial is cheap and lets us redraw
                # convergence at any point.
                'quest_pdf_after': quest.pdf.tolist(),
            })

            print(f"  [{n_afc}-AFC] B{block_num} T{trial_num}: "
                  f"x={log_contrast:+.2f} (lin={contrast:.4f}), "
                  f"letter={correct_letter} resp={response} "
                  f"correct={is_correct} rt={reaction_time_ms}ms "
                  f"t_hat={quest.mean():+.3f}  sd={quest.sd():.3f}")

            # Brief inter-trial pause
            pause_end = renderer.get_time() + 0.2
            while renderer.get_time() < pause_end:
                renderer.poll_events()

        if running:
            n_correct = int(sum(quest.responses))
            n_total = len(quest.responses)
            accuracy = n_correct / n_total if n_total > 0 else 0.0
            block_results.append({
                'block': block_num,
                'threshold_log10': quest.mean(),
                'threshold_sd': quest.sd(),
                'threshold_linear': float(10 ** quest.mean()),
                'n_correct': n_correct,
                'n_total': n_total,
                'accuracy': accuracy,
                'initial_quest_state': initial_quest_state,
                'final_quest_state': quest.snapshot(),
            })
            print(f"\n[{n_afc}-AFC] Block {block_num} summary:")
            print(f"  accuracy = {n_correct}/{n_total} = {accuracy * 100:.1f}%")
            print(f"  t_hat = {quest.mean():.4f} (sd={quest.sd():.4f}) "
                  f"linear={10 ** quest.mean():.4f}")

    if not block_results:
        return None

    thresholds = [b['threshold_log10'] for b in block_results]
    sds = [b['threshold_sd'] for b in block_results]
    final_threshold = float(np.mean(thresholds))
    final_sd = float(np.mean(sds))

    # Aggregate diagnostics over the whole calibration run for this config
    empirical_curve = empirical_psychometric(trial_log)
    confusion = calibration_confusion_matrix(trial_log, letters)
    per_letter_accuracy = {}
    for l in letters:
        shown = sum(1 for r in trial_log if r['correct_letter'] == l)
        correct = sum(1 for r in trial_log if r['correct_letter'] == l and r['is_correct'])
        per_letter_accuracy[l] = {
            'n_shown': shown,
            'n_correct': correct,
            'accuracy': (correct / shown) if shown else None,
        }

    return {
        'n_afc': n_afc,
        'gamma': gamma,
        'letters': letters,
        'p_threshold': 0.75,
        'beta': 3.5,
        'delta': 0.01,
        'threshold_log10': final_threshold,
        'threshold_linear': float(10 ** final_threshold),
        'threshold_sd': final_sd,
        'thresholds_log10': thresholds,
        'thresholds_linear': [float(10 ** t) for t in thresholds],
        'sds': sds,
        'blocks': block_results,
        'trial_log': trial_log,
        # Diagnostics for comparing assumed model vs actual behavior:
        'empirical_psychometric': empirical_curve,
        'confusion_matrix': confusion,
        'per_letter_accuracy': per_letter_accuracy,
        'completed': running,
    }


def save_trial_csv(path, trial_log):
    """Per-trial CSV for spreadsheet analysis."""
    if not trial_log:
        return
    fieldnames = list(trial_log[0].keys())
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in trial_log:
            writer.writerow(row)


def empirical_psychometric(trial_log, bin_grain=0.2):
    """Per-contrast empirical accuracy from the trial log.

    Groups trials by log_contrast (rounded to `bin_grain` log10 units) and
    computes n_trials, n_correct, proportion correct. This is the raw
    psychometric the participant actually produced, which can be plotted
    against the assumed Weibull to see model misspecification."""
    if not trial_log:
        return []
    bins = {}
    for row in trial_log:
        x = round(row['log_contrast'] / bin_grain) * bin_grain
        bins.setdefault(x, {'log_contrast_bin': x, 'n_trials': 0, 'n_correct': 0})
        bins[x]['n_trials'] += 1
        bins[x]['n_correct'] += int(row['is_correct'])
    out = []
    for x in sorted(bins.keys()):
        b = bins[x]
        b['proportion_correct'] = b['n_correct'] / b['n_trials']
        b['linear_contrast_bin'] = float(10 ** x)
        out.append(b)
    return out


def calibration_confusion_matrix(trial_log, letters):
    """Confusion matrix for calibration trials.

    Returns {presented_letter: {reported_letter: count}}. C-O-D-style
    confusions would show off-diagonal mass concentrated in pairs of
    visually similar letters, which directly evidences that
    gamma_true != 1/N for the letter set."""
    matrix = {l: {l2: 0 for l2 in letters} for l in letters}
    for row in trial_log:
        p = row['correct_letter']
        r = row['response']
        if p in matrix and r in matrix[p]:
            matrix[p][r] += 1
    return matrix


def run_quest_calibration():
    print("=" * 60)
    print("STEP 1 - QUEST CALIBRATION (2-AFC, 3-AFC, 5-AFC)")
    print("=" * 60)

    print_all_displays()
    DISPLAY_INDEX, width, height = setup_display_for_glfw()

    info = get_participant_info("Step 1 - QUEST Calibration (multi-AFC)")
    if info is None:
        print("Experiment cancelled.")
        return

    random.seed(info['random_seed'])
    np.random.seed(info['random_seed'])

    data_folder = create_data_folder(info, base_dir=paths['base_dir'])
    print(f"Data folder: {data_folder}")
    save_participant_info(info, data_folder)

    display_cal = DisplayCalibration(DISPLAY_INDEX)
    display_cal.print_report()

    FPS = display_cal.get_corrected_fps()
    font_size = params['font_size']
    frame_size = params['frame_size']

    renderer = GLRenderer(width, height, monitor_index=DISPLAY_INDEX, fullscreen=False)
    width, height = renderer.width, renderer.height

    renderer.clear(0.498)
    renderer.flip()
    print(f"Display: {width}x{height} @ {FPS}Hz")
    print(f"Font size: {font_size}px, Frame size: {frame_size}")

    GRAY = 0.498
    BLACK = 0.0
    WHITE = 1.0
    LIGHT_GRAY = 200.0 / 255.0

    gradient_h = 192
    gradient_w = min(max(256, renderer.width - 80), 2048)
    gradient_x = (renderer.width - gradient_w) // 2
    gradient_y = 50

    gradient_array = np.linspace(0.0, 1.0, 1024, dtype=np.float32).reshape(1, 1024)
    gradient_tex = renderer.create_noise_texture(gradient_array)

    def draw_top_gradient():
        renderer.draw_rect_filled(gradient_x - 3, gradient_y - 3, gradient_w + 6, gradient_h + 6, BLACK)
        renderer.draw_noise_texture(gradient_tex, gradient_x, gradient_y, gradient_w, gradient_h, additive=False)
        renderer.draw_rect_outline(gradient_x - 2, gradient_y - 2, gradient_w + 4, gradient_h + 4, WHITE, 2)

    font_stim = renderer.load_font(fonts['stimulus'], font_size)
    font_ui = renderer.load_font(fonts['ui'], 40)

    trials_per_block = params['quest_trials']
    filename_base = f"{info['name']}_{info['timestamp']}_calibration"

    all_results = []
    aborted = False

    for cfg_idx, config in enumerate(N_AFC_CONFIGS):
        print(f"\n{'=' * 60}")
        print(f"Calibration {cfg_idx + 1}/{len(N_AFC_CONFIGS)}: "
              f"{config['n']}-AFC  letters={config['letters']}  "
              f"gamma={config['gamma']:.4f}")
        print(f"{'=' * 60}")

        # Between-config transition screen (skipped before the first config)
        if cfg_idx > 0:
            renderer.clear(GRAY)
            transition_lines = [
                f"Next: {config['n']}-AFC calibration",
                "",
                f"Letters: {', '.join(config['letters'])}",
                "",
                "Press any key to continue.",
            ]
            y_offset = height // 2 - 100
            for line in transition_lines:
                if line:
                    renderer.draw_text_centered(font_ui, line, width // 2, y_offset, 40, LIGHT_GRAY)
                y_offset += 40
            draw_top_gradient()
            renderer.flip()
            key = renderer.wait_key()
            if key == glfw.KEY_ESCAPE or renderer.should_close():
                aborted = True
                break

        result = run_calibration_for_config(
            config, renderer, font_stim, font_ui,
            font_size, frame_size, FPS,
            draw_top_gradient, width, height, trials_per_block,
            GRAY, BLACK, WHITE, LIGHT_GRAY,
        )

        if result is None:
            print(f"  Aborted before any block completed - no data for {config['n']}-AFC.")
            aborted = True
            break

        # Derive a filename-safe tag. Fall back to "{n}AFC_{letters}" if
        # no explicit tag is set (so legacy configs still work).
        tag = config.get('tag') or f"{config['n']}AFC_{''.join(config['letters'])}"

        record = {
            **result,
            'tag': tag,
            'participant': info,
            'timestamp': datetime.now().isoformat(),
            'display_calibration': display_cal.to_dict(),
        }

        # Per-variant threshold file (step-2 compatible)
        threshold_file = os.path.join(
            data_folder,
            f"{filename_base}_{tag}_threshold.json",
        )
        with open(threshold_file, 'w') as f:
            json.dump(record, f, indent=2)
        print(f"\n{tag} threshold saved to: {threshold_file}")
        print(f"  threshold_log10  = {result['threshold_log10']:+.4f}")
        print(f"  threshold_linear = {result['threshold_linear']:.4f}")

        # Per-variant CSV of trials
        csv_file = os.path.join(
            data_folder,
            f"{filename_base}_{tag}_trials.csv",
        )
        save_trial_csv(csv_file, result['trial_log'])
        print(f"  per-trial CSV    -> {csv_file}")

        all_results.append(record)

        if not result['completed']:
            print("Procedure was aborted mid-config; stopping.")
            aborted = True
            break

    # Combined summary across all configs that finished
    if all_results:
        summary_file = os.path.join(data_folder, f"{filename_base}_all.json")
        summary = {
            'participant': info,
            'timestamp': datetime.now().isoformat(),
            'display_calibration': display_cal.to_dict(),
            'n_afc_configs': N_AFC_CONFIGS,
            'global_params': {
                'p_threshold': 0.75,
                'beta': 3.5,
                'delta': 0.01,
                'start_val': -0.5,
                'start_val_sd': 4,
                'range_val': 4,
                'grain': 0.2,
                'trials_per_block': trials_per_block,
                'blocks_per_config': 2,
            },
            'results': all_results,
            'summary_table': [
                {
                    'n_afc': r['n_afc'],
                    'gamma': r['gamma'],
                    'letters': r['letters'],
                    'threshold_log10': r['threshold_log10'],
                    'threshold_linear': r['threshold_linear'],
                    'threshold_sd': r['threshold_sd'],
                    'completed': r['completed'],
                }
                for r in all_results
            ],
            'aborted': aborted,
        }
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\nCombined summary saved to: {summary_file}")

        # End-of-procedure screen showing the three thresholds
        renderer.clear(GRAY)
        result_lines = ["Calibration complete.", ""]
        for r in all_results:
            label = r.get('tag', f"{r['n_afc']}-AFC")
            result_lines.append(
                f"{label}: log10={r['threshold_log10']:+.3f}  "
                f"linear={r['threshold_linear']:.3f}  "
                f"sd={r['threshold_sd']:.3f}"
            )
        result_lines += ["", "Press any key to exit."]
        y_offset = height // 2 - 180
        for line in result_lines:
            if line:
                renderer.draw_text_centered(font_ui, line, width // 2, y_offset, 40, LIGHT_GRAY)
            y_offset += 40
        draw_top_gradient()
        renderer.flip()
        renderer.wait_key()
    else:
        print("No completed configs - nothing saved.")

    renderer.delete_texture(gradient_tex)
    renderer.destroy()
    print("\nCalibration session done.")


if __name__ == "__main__":
    run_quest_calibration()
