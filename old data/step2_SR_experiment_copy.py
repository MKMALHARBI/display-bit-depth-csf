#!/usr/bin/env python3
"""
STEP 2 - Stochastic Resonance Experiment (BINOCULAR, multi-AFC version)
=======================================================================
Loads one of the per-variant thresholds produced by the multi-AFC
calibration (2-AFC / 3-AFC / 5-AFC) and measures 10-AFC identification
accuracy at that fixed contrast.

Usage:
    python step2_SR_experiment_copy.py --afc 2
    python step2_SR_experiment_copy.py --afc 3
    python step2_SR_experiment_copy.py --afc 5

If --afc is omitted and multiple threshold files exist, the script
prompts to pick one. Output files are tagged with the AFC variant so
the three runs do not overwrite each other.
"""

import numpy as np
import pandas as pd
import json
import os
import re
import random
import glob
import argparse
import glfw
from collections import defaultdict
from datetime import datetime

from lib.parameters import params, paths, fonts
from lib.exp_dialog import load_participant_info, save_participant_to_log
from lib.display_utils import DisplayCalibration, setup_display_for_glfw
from lib.gl_renderer import GLRenderer


AFC_FILENAME_RE = re.compile(r"_(\d+)AFC(?:_[A-Z]+)?_threshold\.json$")
TAG_FILENAME_RE = re.compile(r"_([0-9]+AFC(?:_[A-Z]+)?)_threshold\.json$")


def list_threshold_files(data_folder):
    """All `*_threshold.json` files in the folder, newest first."""
    files = glob.glob(os.path.join(data_folder, "*_threshold.json"))
    files.sort(key=os.path.getmtime, reverse=True)
    return files


def extract_afc(path):
    """Pull N from `*_{N}AFC[_LETTERS]_threshold.json`, or None for legacy."""
    m = AFC_FILENAME_RE.search(os.path.basename(path))
    return int(m.group(1)) if m else None


def extract_tag(path):
    """Pull the full tag (e.g. `3AFC_OCD`) from the filename, or None."""
    m = TAG_FILENAME_RE.search(os.path.basename(path))
    return m.group(1) if m else None


def pick_threshold_file(data_folder, requested_tag, requested_afc):
    """Choose a threshold file by tag (exact, e.g. `3AFC_OCD`), or fall
    back to N-AFC selection, or prompt the user."""
    files = list_threshold_files(data_folder)
    if not files:
        return None

    if requested_tag is not None:
        for f in files:
            if extract_tag(f) == requested_tag:
                return f
        return None

    if requested_afc is not None:
        matching = [f for f in files if extract_afc(f) == requested_afc]
        if len(matching) == 1:
            return matching[0]
        if len(matching) > 1:
            print(f"\nMultiple {requested_afc}-AFC threshold files found:")
            for i, f in enumerate(matching):
                print(f"  [{i}] {os.path.basename(f)}   (tag={extract_tag(f)})")
            while True:
                choice = input("Pick a number: ").strip()
                try:
                    idx = int(choice)
                    if 0 <= idx < len(matching):
                        return matching[idx]
                except ValueError:
                    pass
                print("Invalid choice; try again.")
        return None

    if len(files) == 1:
        return files[0]

    print("\nAvailable threshold files:")
    for i, f in enumerate(files):
        tag = extract_tag(f) or "untagged"
        print(f"  [{i}] {os.path.basename(f)}   (tag={tag})")
    while True:
        choice = input("Pick a number: ").strip()
        try:
            idx = int(choice)
            if 0 <= idx < len(files):
                return files[idx]
        except ValueError:
            pass
        print("Invalid choice; try again.")


def generate_noise_array(size, noise_level, rng):
    """2D float32 noise array (0..1) for additive overlay."""
    if noise_level == 0:
        return np.full(size, 127.0 / 255.0, dtype=np.float32)
    noise = noise_level * rng.standard_normal(size)
    noise = np.clip(127.0 + noise, 0.0, 255.0) / 255.0
    return noise.astype(np.float32)


def run_main_experiment():
    parser = argparse.ArgumentParser(description="Step 2 - 10-AFC experiment")
    parser.add_argument(
        "--tag", type=str, default=None,
        help="Threshold file tag to use, e.g. '3AFC_OCD'. Exact match.",
    )
    parser.add_argument(
        "--afc", type=int, choices=[2, 3, 4, 5], default=None,
        help="Which N-AFC threshold to use. If multiple files share that "
             "N, you'll be prompted to pick one. Ignored if --tag is set.",
    )
    args, _ = parser.parse_known_args()

    print("=" * 60)
    selector = args.tag or (f"{args.afc}-AFC" if args.afc else "(prompt)")
    print(f"STEP 2 - 10-AFC EXPERIMENT  (threshold selector: {selector})")
    print("=" * 60)

    info, data_folder = load_participant_info(paths['base_dir'])
    if info is None:
        print("ERROR: No participant info found - run the calibration first!")
        return

    print(f"Participant: {info['name']}")
    print(f"Data folder: {data_folder}")

    threshold_path = pick_threshold_file(data_folder, args.tag, args.afc)
    if threshold_path is None:
        print("ERROR: No matching threshold file found in participant data folder!")
        if args.tag is not None:
            print(f"Looked for a file with tag '{args.tag}'.")
        elif args.afc is not None:
            print(f"Looked for a {args.afc}-AFC file.")
        return

    n_afc_used = extract_afc(threshold_path)
    file_tag = extract_tag(threshold_path)
    afc_tag = file_tag if file_tag else (f"{n_afc_used}AFC" if n_afc_used else "legacy")

    with open(threshold_path, 'r') as f:
        threshold_data = json.load(f)

    letter_contrast_value = float(threshold_data['threshold_linear'])
    print(f"\nUsing threshold from: {os.path.basename(threshold_path)}")
    print(f"  AFC tag         : {afc_tag}")
    print(f"  threshold_log10 = {threshold_data.get('threshold_log10', float('nan')):+.4f}")
    print(f"  threshold_linear= {letter_contrast_value:.4f}")
    if 'gamma' in threshold_data:
        print(f"  gamma           = {threshold_data['gamma']:.4f}")
    if 'letters' in threshold_data:
        print(f"  calib letters   = {threshold_data['letters']}")

    DISPLAY_INDEX, width, height = setup_display_for_glfw()

    random.seed(info['random_seed'])
    np.random.seed(info['random_seed'])
    rng = np.random.default_rng(info['random_seed'])

    display_cal = DisplayCalibration(DISPLAY_INDEX)
    display_cal.print_report()

    font_size = params['font_size']
    frame_size = params['frame_size']
    FPS = display_cal.get_corrected_fps()

    print(f"Using fixed settings: font_size={font_size}, frame_size={frame_size}")

    renderer = GLRenderer(width, height, monitor_index=DISPLAY_INDEX, fullscreen=False)
    width, height = renderer.width, renderer.height
    renderer.clear(0.498)
    renderer.flip()
    print(f"Display: {width}x{height} @ {FPS}Hz")

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
    options_font_size = min(font_size, int(width * 0.8 / 30))

    frame_x = (width - frame_size[0]) // 2
    frame_y = (height - frame_size[1]) // 2
    frame_cx = width // 2
    frame_cy = height // 2

    letter_contrast = float(np.clip(letter_contrast_value, 0.0001, 255.0))
    gray_level = float(letter_contrast / 255.0)
    print(f"Letter contrast (clipped): {letter_contrast:.4f}  -> gray_level={gray_level:.6f}")

    letters = params['letters']
    noise_levels = params['noise_levels']

    trials_block1 = []
    for rep in range(6):
        for idx, letter in enumerate(letters):
            for noise in noise_levels:
                trials_block1.append({
                    'letter': letter,
                    'letter_idx': idx,
                    'noise_level': noise,
                })
    rng.shuffle(trials_block1)
    n_trials = len(trials_block1)

    trial_seeds = rng.integers(0, 2**31 - 1, size=n_trials, dtype=np.uint32)

    n_noise_frames = params['n_noise_fields']
    all_data = []
    running = True

    for block_idx in range(1, 2):
        if not running:
            break

        renderer.clear(GRAY)
        if block_idx == 1:
            lines = [
                f"BINOCULAR - Block 1 of 1   (using {afc_tag} threshold)",
                "",
                "Identify the letter shown.",
                "Use BOTH eyes.",
                "",
                f"Letters: {', '.join(letters)}",
                "",
                "Press any key to begin.",
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

        for trial_idx, trial in enumerate(trials_block1):
            if not running:
                break

            trial_num = trial_idx + 1
            target_letter = trial['letter']
            noise_level = trial['noise_level']
            trial_wall_time = datetime.now().isoformat()

            trial_rng = np.random.default_rng(int(trial_seeds[trial_idx]))

            noise_tex_ids = []
            n_tex = min(n_noise_frames, 100)
            for _ in range(n_tex):
                arr = generate_noise_array(frame_size, noise_level, trial_rng)
                tex_id = renderer.create_noise_texture(arr)
                noise_tex_ids.append(tex_id)

            noise_order = list(range(len(noise_tex_ids)))
            trial_rng.shuffle(noise_order)

            n_frames = int(params['stim_duration'] * FPS)
            for frame in range(n_frames):
                renderer.poll_events()
                key = renderer.poll_key()
                if key == glfw.KEY_ESCAPE or renderer.should_close():
                    running = False
                    break

                renderer.clear(GRAY)
                renderer.draw_rect_filled(frame_x, frame_y, frame_size[0], frame_size[1], BLACK)
                renderer.draw_rect_outline(frame_x, frame_y, frame_size[0], frame_size[1], WHITE, 2)
                renderer.draw_text_centered(font_stim, target_letter,
                                            frame_cx, frame_cy, font_size, gray_level)
                noise_idx = noise_order[frame % len(noise_order)]
                renderer.draw_noise_texture(noise_tex_ids[noise_idx],
                                            frame_x, frame_y,
                                            frame_size[0], frame_size[1],
                                            additive=True)
                draw_top_gradient()
                renderer.flip()

            for tex_id in noise_tex_ids:
                renderer.delete_texture(tex_id)

            if not running:
                break

            # Response screen
            renderer.clear(GRAY)
            letters_display = "  ".join(letters)
            renderer.draw_text_centered(font_ui, letters_display,
                                        width // 2, height // 4, options_font_size, WHITE)
            renderer.draw_text_centered(font_ui, f"Block {block_idx} - Trial {trial_num}/{n_trials}",
                                        width // 2, height // 2 - 50, 40, LIGHT_GRAY)
            renderer.draw_text_centered(font_ui, "Which letter? Press the key.",
                                        width // 2, height // 2 + 10, 40, LIGHT_GRAY)
            draw_top_gradient()
            renderer.flip()

            response = None
            confirmed = False
            response_start = renderer.get_time()
            first_response_time = None
            response_changes = 0
            response_history = []  # ordered list of (letter, time_ms_from_start)

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
                        now = renderer.get_time()
                        if first_response_time is None:
                            first_response_time = int((now - response_start) * 1000)
                        if response is not None and letter != response:
                            response_changes += 1
                        response = letter
                        response_history.append({
                            'letter': letter,
                            't_ms_from_response_screen': int((now - response_start) * 1000),
                        })

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
            is_correct = (response == target_letter)
            all_data.append({
                'block': block_idx,
                'trial': trial_num,
                'wall_time': trial_wall_time,
                'noise_level': noise_level,
                'letter_idx': trial['letter_idx'] + 1,
                'presented_letter': target_letter,
                'response': response,
                'correct': is_correct,
                'reaction_time_ms': reaction_time_ms,
                'first_response_ms': first_response_time,
                'response_changes': response_changes,
                'response_history': response_history,
                'trial_seed': int(trial_seeds[trial_idx]),
            })

            pause_end = renderer.get_time() + 0.2
            while renderer.get_time() < pause_end:
                renderer.poll_events()

    if running:
        renderer.clear(GRAY)
        renderer.draw_text_centered(font_ui, "Experiment Complete!",
                                    width // 2, height // 2 - 30, 40, LIGHT_GRAY)
        renderer.draw_text_centered(font_ui, "Thank you. Press any key to exit.",
                                    width // 2, height // 2 + 30, 40, LIGHT_GRAY)
        draw_top_gradient()
        renderer.flip()
        renderer.wait_key()

    if all_data:
        df = pd.DataFrame(all_data)
        df.insert(0, 'ParticipantID', info['name'])
        df.insert(1, 'AFC_threshold_used', afc_tag)
        df['correct'] = df['correct'].astype(int)
        df = df.rename(columns={
            'noise_level': 'NoiseLevel',
            'letter_idx': 'LetterNumber',
            'presented_letter': 'PresentedLetter',
            'response': 'ReportedKey',
            'correct': 'AnswerCorrect',
            'block': 'Block',
        })

        filename_base = (
            f"{info['name']}_{info['timestamp']}_step2_SR_Binocular_{afc_tag}"
        )

        csv_file = os.path.join(data_folder, f"{filename_base}_trials.csv")
        df.to_csv(csv_file, index=False)
        print(f"Data saved to: {csv_file}")

        # Per-letter accuracy + confusion matrix for analysis
        letter_stats = (
            df.groupby('PresentedLetter')['AnswerCorrect']
              .agg(['mean', 'sum', 'count'])
              .rename(columns={'mean': 'accuracy', 'sum': 'n_correct', 'count': 'n_trials'})
              .reset_index()
              .to_dict(orient='records')
        )

        confusion = defaultdict(lambda: defaultdict(int))
        for trial in all_data:
            confusion[trial['presented_letter']][trial['response']] += 1
        confusion_dict = {k: dict(v) for k, v in confusion.items()}

        accuracy_by_noise = df.groupby('NoiseLevel')['AnswerCorrect'].mean()
        overall_accuracy = float(df['AnswerCorrect'].mean())
        first_rt_series = df['first_response_ms'].dropna()
        rt_summary = {
            'total_rt_ms': {
                'mean': float(df['reaction_time_ms'].mean()),
                'median': float(df['reaction_time_ms'].median()),
                'std': float(df['reaction_time_ms'].std()),
            },
            'first_response_ms': {
                'mean': float(first_rt_series.mean()) if len(first_rt_series) else None,
                'median': float(first_rt_series.median()) if len(first_rt_series) else None,
                'std': float(first_rt_series.std()) if len(first_rt_series) else None,
            },
            'response_changes': {
                'mean': float(df['response_changes'].mean()),
                'total': int(df['response_changes'].sum()),
                'n_trials_with_changes': int((df['response_changes'] > 0).sum()),
            },
        }

        json_file = os.path.join(data_folder, f"{filename_base}.json")
        full_data = {
            'participant': info,
            'afc_threshold_used': n_afc_used,
            'afc_tag': afc_tag,
            'threshold_file': os.path.basename(threshold_path),
            'threshold': threshold_data,
            'parameters': {
                'letters': params['letters'],
                'noise_levels': params['noise_levels'],
                'stim_duration': params['stim_duration'],
                'font_size': font_size,
                'frame_size': list(frame_size),
                'letter_contrast_used': letter_contrast,
                'gray_level_used': gray_level,
            },
            'display_calibration': display_cal.to_dict(),
            'trials': all_data,
            'analysis': {
                'overall_accuracy': overall_accuracy,
                'n_trials': len(all_data),
                'n_correct': int(df['AnswerCorrect'].sum()),
                'accuracy_by_noise': {
                    float(k): float(v) for k, v in accuracy_by_noise.items()
                },
                'letter_stats': letter_stats,
                'confusion_matrix': confusion_dict,
                'reaction_time': rt_summary,
            },
            'timestamp': datetime.now().isoformat(),
        }
        with open(json_file, 'w') as f:
            json.dump(full_data, f, indent=2)
        print(f"Full JSON saved to: {json_file}")

        # Original optimum-noise side file kept for downstream compatibility
        optimum_noise = float(accuracy_by_noise.idxmax())
        optimum_accuracy = float(accuracy_by_noise.max())
        optimum_data = {
            'afc_threshold_used': n_afc_used,
            'afc_tag': afc_tag,
            'optimum_noise_level': optimum_noise,
            'optimum_accuracy': optimum_accuracy,
            'accuracy_by_noise': {float(k): float(v) for k, v in accuracy_by_noise.items()},
            'overall_accuracy': overall_accuracy,
            'participant': info,
            'timestamp': datetime.now().isoformat(),
        }
        optimum_file = os.path.join(data_folder, f"{filename_base}_optimum.json")
        with open(optimum_file, 'w') as f:
            json.dump(optimum_data, f, indent=2)

        print(f"\n[{afc_tag}] Overall accuracy: {overall_accuracy:.3f}  "
              f"({int(df['AnswerCorrect'].sum())}/{len(all_data)})")
        print(f"\nAccuracy by noise level:")
        for noise, acc in accuracy_by_noise.items():
            marker = " <-- BEST" if float(noise) == optimum_noise else ""
            print(f"  Noise {noise:6.2f}: {acc:.3f}{marker}")
        print(f"\nPer-letter accuracy:")
        for row in letter_stats:
            print(f"  {row['PresentedLetter']}: {row['accuracy']:.3f}  "
                  f"({int(row['n_correct'])}/{int(row['n_trials'])})")
        print(f"\nOptimum noise level: {optimum_noise:.2f} (accuracy: {optimum_accuracy:.3f})")
        print(f"Saved to: {optimum_file}")

        if not info.get('practice', False):
            save_participant_to_log(info)

    renderer.delete_texture(gradient_tex)
    renderer.destroy()
    print("\nExperiment complete!")


if __name__ == "__main__":
    run_main_experiment()
