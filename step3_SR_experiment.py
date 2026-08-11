#!/usr/bin/env python3
"""
STEP 2 - Stochastic Resonance Experiment (BINOCULAR)
=====================================================
Tests whether adding noise to low-contrast letters improves recognition.
Binocular viewing condition.

RUN step1_calibration.py FIRST!
Loads participant info from Data/{name}/participant_info.json (no dialog).

OpenGL 10-bit rendering via GLFW + PyOpenGL + FreeType.
Temporal dithering removed — true 10-bit precision (1024 gray levels).
Noise textures uploaded as GL_R16F for full precision.
"""

import numpy as np
import pandas as pd
import json
import os
import random
import glob
import glfw
from datetime import datetime

from lib.parameters import params, paths, fonts
from lib.exp_dialog import load_participant_info, save_participant_to_log
from lib.display_utils import DisplayCalibration, setup_display_for_glfw
from lib.gl_renderer import GLRenderer


def find_threshold_file(data_folder):
    """Find the most recent *_threshold.json in the participant's data folder."""
    files = glob.glob(os.path.join(data_folder, "*_threshold.json"))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def generate_noise_array(size, noise_level, rng):
    """Generate a 2D float32 noise array (0.0-1.0) for GL upload.

    noise_level is in the same 0-255 scale as before; the array is
    normalized to 0.0-1.0 for the GPU.
    """
    if noise_level == 0:
        return np.full(size, 127.0 / 255.0, dtype=np.float32)

    noise = noise_level * rng.standard_normal(size)
    noise = np.clip(127.0 + noise, 0.0, 255.0) / 255.0
    return noise.astype(np.float32)


def run_main_experiment():
    print("=" * 60)
    print("STEP 2 — STOCHASTIC RESONANCE EXPERIMENT (BINOCULAR)")
    print("=" * 60)

    # Load participant info (no dialog)
    info, data_folder = load_participant_info(paths['base_dir'])
    if info is None:
        print("ERROR: No participant info found!")
        print("Run step1_calibration.py first!")
        return

    print(f"Participant: {info['name']}")
    print(f"Data folder: {data_folder}")

    # Find threshold from step 1
    threshold_path = find_threshold_file(data_folder)
    if threshold_path is None:
        print("ERROR: No threshold file found in participant data folder!")
        print("Run step1_calibration.py first!")
        return

    with open(threshold_path, 'r') as f:
        threshold_data = json.load(f)

    letter_contrast = threshold_data['threshold_linear']
    print(f"Loaded threshold: {letter_contrast:.6f} (from {os.path.basename(threshold_path)})")

    DISPLAY_INDEX, width, height = setup_display_for_glfw()

    random.seed(info['random_seed'])
    np.random.seed(info['random_seed'])
    rng = np.random.default_rng(info['random_seed'])

    display_cal = DisplayCalibration(DISPLAY_INDEX)
    display_cal.print_report()

    # Fixed settings
    font_size = params['font_size']
    frame_size = params['frame_size']
    FPS = display_cal.get_corrected_fps()

    print(f"Using fixed settings: font_size={font_size}, frame_size={frame_size}")

    # Create OpenGL renderer (10-bit framebuffer)
    renderer = GLRenderer(width, height, monitor_index=DISPLAY_INDEX, fullscreen=False)
    width, height = renderer.width, renderer.height

    renderer.clear(0.498)
    renderer.flip()
    print(f"Display: {width}x{height} @ {FPS}Hz")

    # Gray levels (0.0-1.0)
    GRAY = 0.498
    BLACK = 0.0
    WHITE = 1.0
    LIGHT_GRAY = 200.0 / 255.0
    gradient_h = 192
    gradient_w = min(max(256, renderer.width - 80), 2048)
    gradient_x = (renderer.width - gradient_w) // 2
    gradient_y = 50

    # 10-bit test bar: 1024-level horizontal gradient rendered at top of screen.
    gradient_array = np.linspace(0.0, 1.0, 1024, dtype=np.float32).reshape(1, 1024)
    gradient_tex = renderer.create_noise_texture(gradient_array)

    def draw_top_gradient():
        renderer.draw_rect_filled(gradient_x - 3, gradient_y - 3, gradient_w + 6, gradient_h + 6, BLACK)
        renderer.draw_noise_texture(gradient_tex, gradient_x, gradient_y, gradient_w, gradient_h, additive=False)
        renderer.draw_rect_outline(gradient_x - 2, gradient_y - 2, gradient_w + 4, gradient_h + 4, WHITE, 2)

    # Load fonts
    font_stim = renderer.load_font(fonts['stimulus'], font_size)
    font_ui = renderer.load_font(fonts['ui'], 40)
    options_font_size = min(font_size, int(width * 0.8 / 30))

    # Stimulus area
    frame_x = (width - frame_size[0]) // 2
    frame_y = (height - frame_size[1]) // 2
    frame_cx = width // 2
    frame_cy = height // 2

    # 10-bit: direct float gray level, no dithering needed
    letter_contrast = np.clip(letter_contrast, 0.0001, 255.0)
    letter_delta = float(letter_contrast / 255.0)
    print(f"Letter contrast: {letter_contrast:.4f} (letter_delta={letter_delta:.6f})")

    # Create trial list
    letters = ['V', 'Z']
    noise_levels = params['noise_levels']

    trials_block1 = []
    for rep in range(30):
        for idx, letter in enumerate(letters):
            for noise in noise_levels:
                trials_block1.append({
                    'letter': letter,
                    'letter_idx': idx,
                    'noise_level': noise
                })
    rng.shuffle(trials_block1)
    n_trials = len(trials_block1)

    # Generate trial seeds for reproducibility across blocks
    trial_seeds = rng.integers(0, 2**31 - 1, size=n_trials, dtype=np.uint32)

    n_noise_frames = params['n_noise_fields']
    all_data = []
    running = True

    # Run blocks
    for block_idx in range(1, 2):
        if not running:
            break

        # Show instructions
        renderer.clear(GRAY)
        if block_idx == 1:
            lines = [
                "BINOCULAR — Block 1 of 1",
                "",
                "Identify the letter shown.",
                "Use BOTH eyes.",
                "",
                f"Letters: {', '.join(letters)}",
                "",
                "Press any key to begin."
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

        # Trial loop
        for trial_idx, trial in enumerate(trials_block1):
            if not running:
                break

            trial_num = trial_idx + 1
            target_letter = trial['letter']
            noise_level = trial['noise_level']

            # Create trial-specific RNG
            trial_rng = np.random.default_rng(int(trial_seeds[trial_idx]))

            # Pre-generate noise arrays and upload as GL textures
            noise_tex_ids = []
            n_tex = min(n_noise_frames, 100)
            for _ in range(n_tex):
                arr = generate_noise_array(frame_size, noise_level, trial_rng)
                tex_id = renderer.create_noise_texture(arr)
                noise_tex_ids.append(tex_id)

            noise_order = list(range(len(noise_tex_ids)))
            trial_rng.shuffle(noise_order)

            # Show stimulus
            n_frames = int(params['stim_duration'] * FPS)

            for frame in range(n_frames):
                renderer.poll_events()
                key = renderer.poll_key()
                if key == glfw.KEY_ESCAPE or renderer.should_close():
                    running = False
                    break

                renderer.clear(GRAY)

                # Noise field replaces the mid-gray inside the frame, drawn BEFORE the
                # letter so the letter composites onto it. At noise_level 0 the field is
                # flat mid-gray -- what clear(GRAY) already put there -- so it is skipped.
                if noise_level > 0:
                    noise_idx = noise_order[frame % len(noise_order)]
                    renderer.draw_noise_texture(noise_tex_ids[noise_idx],
                                                frame_x, frame_y,
                                                frame_size[0], frame_size[1],
                                                additive=False)

                renderer.draw_rect_outline(frame_x, frame_y, frame_size[0], frame_size[1], WHITE, 2)

                # Letter added as an increment over whatever is beneath, so it rides on
                # the noise instead of replacing it. Identical to step1_calibration.py.
                renderer.draw_text_centered(font_stim, target_letter,
                                            frame_cx, frame_cy, font_size, letter_delta,
                                            additive=True)

                draw_top_gradient()
                renderer.flip()

            # Free noise textures for this trial
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

            # Record data
            reaction_time_ms = int((renderer.get_time() - response_start) * 1000)
            is_correct = (response == target_letter)
            all_data.append({
                'block': block_idx,
                'trial': trial_num,
                'noise_level': noise_level,
                'letter_idx': trial['letter_idx'] + 1,
                'presented_letter': target_letter,
                'response': response,
                'correct': is_correct,
                'reaction_time_ms': reaction_time_ms,
                'trial_seed': int(trial_seeds[trial_idx])
            })

            # Brief inter-trial pause (200ms)
            pause_end = renderer.get_time() + 0.2
            while renderer.get_time() < pause_end:
                renderer.poll_events()

    # End screen
    if running:
        renderer.clear(GRAY)
        renderer.draw_text_centered(font_ui, "Experiment Complete!",
                                    width // 2, height // 2 - 30, 40, LIGHT_GRAY)
        renderer.draw_text_centered(font_ui, "Thank you. Press any key to exit.",
                                    width // 2, height // 2 + 30, 40, LIGHT_GRAY)
        draw_top_gradient()
        renderer.flip()
        renderer.wait_key()

    # Save data
    if all_data:
        df = pd.DataFrame(all_data)
        df.insert(0, 'ParticipantID', info['name'])
        df['correct'] = df['correct'].astype(int)
        df = df.rename(columns={
            'noise_level': 'NoiseLevel',
            'letter_idx': 'LetterNumber',
            'presented_letter': 'PresentedLetter',
            'response': 'ReportedKey',
            'correct': 'AnswerCorrect',
            'block': 'Block'
        })

        filename_base = f"{info['name']}_{info['timestamp']}_step3_SR_Binocular"

        csv_file = os.path.join(data_folder, f"{filename_base}_trials.csv")
        df.to_csv(csv_file, index=False)
        print(f"Data saved to: {csv_file}")

        json_file = os.path.join(data_folder, f"{filename_base}.json")
        full_data = {
            'participant': info,
            'parameters': {
                'letters': letters,
                'noise_levels': params['noise_levels'],
                'stim_duration': params['stim_duration'],
                'font_size': font_size,
                'frame_size': list(frame_size),
            },
            'threshold': threshold_data,
            'display_calibration': display_cal.to_dict(),
            'trials': all_data,
            'timestamp': datetime.now().isoformat()
        }
        with open(json_file, 'w') as f:
            json.dump(full_data, f, indent=2)

        # Determine optimum noise level (stochastic resonance peak)
        accuracy_by_noise = df.groupby('NoiseLevel')['AnswerCorrect'].mean()
        optimum_noise = float(accuracy_by_noise.idxmax())
        optimum_accuracy = float(accuracy_by_noise.max())

        optimum_data = {
            'optimum_noise_level': optimum_noise,
            'optimum_accuracy': optimum_accuracy,
            'accuracy_by_noise': {float(k): float(v) for k, v in accuracy_by_noise.items()},
            'participant': info,
            'timestamp': datetime.now().isoformat(),
        }

        optimum_file = os.path.join(data_folder, f"{filename_base}_optimum.json")
        with open(optimum_file, 'w') as f:
            json.dump(optimum_data, f, indent=2)

        print(f"\nAccuracy by noise level:")
        for noise, acc in accuracy_by_noise.items():
            marker = " <-- BEST" if float(noise) == optimum_noise else ""
            print(f"  Noise {noise:6.2f}: {acc:.3f}{marker}")
        print(f"Optimum noise level: {optimum_noise:.2f} (accuracy: {optimum_accuracy:.3f})")
        print(f"Saved to: {optimum_file}")

        if not info.get('practice', False):
            save_participant_to_log(info)

    renderer.delete_texture(gradient_tex)
    renderer.destroy()
    print("\nExperiment complete!")


if __name__ == "__main__":
    run_main_experiment()
