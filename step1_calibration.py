#!/usr/bin/env python3
"""
STEP 1 - QUEST Threshold Calibration
=====================================
Finds participant's contrast detection threshold using QUEST algorithm.
RUN THIS FIRST — saves participant_info.json for steps 2 and 3.
;
OpenGL 10-bit rendering via GLFW + PyOpenGL + FreeType.
Temporal dithering removed — true 10-bit precision (1024 gray levels).
"""

import numpy as np
import json
import os
import random
import time
import glfw
from datetime import datetime

from lib.parameters import params, paths, fonts
from lib.exp_dialog import get_participant_info, create_data_folder, save_participant_info
from lib.display_utils import DisplayCalibration, print_all_displays, setup_display_for_glfw
from lib.gl_renderer import GLRenderer


class SimpleQUEST:
    """
    CHANGED: gamma 0.5 -> 0.33
    MATLAB: 2 letters (H, N) -> 50% chance to guess right -> gamma=0.5
    Python: 3 letters (C, O, D) -> 33% chance to guess right -> gamma=0.33
    """

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
        """Weibull psychometric function."""
        p = self.delta * self.gamma + (1 - self.delta) * (
            1 - (1 - self.gamma) * np.exp(-10 ** (self.beta * (x - t)))
        )
        return np.clip(p, 0.0001, 0.9999)

    def quantile(self):
        """Get recommended test intensity."""
        cdf = np.cumsum(self.pdf)
        idx = np.searchsorted(cdf, self.p_threshold)
        idx = np.clip(idx, 0, len(self.x) - 1)
        return self.x[idx]

    def update(self, intensity, response):
        """Update pdf based on response."""
        self.intensities.append(intensity)
        self.responses.append(response)

        if response:
            likelihood = self.weibull(intensity, self.x)
        else:
            likelihood = 1 - self.weibull(intensity, self.x)

        self.pdf *= likelihood
        self.pdf /= self.pdf.sum()

    def mean(self):
        """Get mean threshold estimate."""
        return np.sum(self.x * self.pdf)

    def sd(self):
        """Get standard deviation of estimate."""
        mean = self.mean()
        return np.sqrt(np.sum(self.pdf * (self.x - mean) ** 2))


def run_quest_calibration():
    print("=" * 60)
    print("STEP 1 — QUEST THRESHOLD CALIBRATION")
    print("=" * 60)

    print_all_displays()
    DISPLAY_INDEX, width, height = setup_display_for_glfw()

    info = get_participant_info("Step 1 — QUEST Calibration")
    if info is None:
        print("Experiment cancelled.")
        return

    random.seed(info['random_seed'])
    np.random.seed(info['random_seed'])

    data_folder = create_data_folder(info, base_dir=paths['base_dir'])
    print(f"Data folder: {data_folder}")

    # Save participant info for steps 2 and 3
    save_participant_info(info, data_folder)

    display_cal = DisplayCalibration(DISPLAY_INDEX)
    display_cal.print_report()

    # Fixed settings
    FPS = display_cal.get_corrected_fps()
    font_size = params['font_size']
    frame_size = params['frame_size']

    # Create OpenGL renderer (10-bit framebuffer)
    renderer = GLRenderer(width, height, monitor_index=DISPLAY_INDEX, fullscreen=False)
    width, height = renderer.width, renderer.height

    renderer.clear(0.498)
    renderer.flip()
    print(f"Display: {width}x{height} @ {FPS}Hz")
    print(f"Font size: {font_size}px, Frame size: {frame_size}")

    # Gray levels (0.0-1.0)
    GRAY = 0.498  # ~127/255
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

    # Stimulus area (top-left corner)
    frame_x = (width - frame_size[0]) // 2
    frame_y = (height - frame_size[1]) // 2
    frame_cx = width // 2
    frame_cy = height // 2

    # QUEST eters
    quest_letters = params['quest_letters']
    trials_per_block = params['quest_trials']

    all_thresholds = []
    all_sds = []
    trial_log = []
    running = True

    for block_num in range(1, 3):
        if not running:
            break

        # Show block instructions
        renderer.clear(GRAY)
        if block_num == 1:
            lines = [
                "QUEST Block 1 of 2",
                "",
                "You will see 'C', 'O', or 'D'.",
                "Press the matching key.",
                "",
                "Press any key to start."
            ]
        else:
            lines = [
                "Block 1 complete.",
                "",
                "Block 2 starting.",
                "",
                "Press any key to continue."
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

        # Create QUEST
        quest = SimpleQUEST(start_val=-0.5, start_val_sd=4, p_threshold=0.75, range_val=4, gamma=0.33)

        # Trial loop
        for trial_num in range(1, trials_per_block + 1):
            if not running:
                break

            log_contrast = quest.quantile()
            contrast = 10 ** log_contrast
            contrast = np.clip(contrast, 0.0001, 255.0)

            correct_letter = random.choice(quest_letters)

            # 10-bit: direct float gray level on mid-gray background
            # Letter appears at GRAY + contrast/255 (same physical delta as original)
            letter_delta = float(contrast / 255.0)
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

                # Draw letter slightly brighter than background
                renderer.draw_text_centered(font_stim, correct_letter,
                                            frame_cx, frame_cy, font_size, letter_delta,
                                            additive=True)

                draw_top_gradient()
                renderer.flip()

            if not running:
                break

            # Response screen
            renderer.clear(GRAY)
            prompt = f"Block {block_num} - Trial {trial_num}/{trials_per_block}"
            renderer.draw_text_centered(font_ui, prompt, width // 2, height // 2 - 50, 40, LIGHT_GRAY)
            renderer.draw_text_centered(font_ui, "Which letter? Press C, O, or D",
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
                elif key == glfw.KEY_C:
                    response = 'C'
                elif key == glfw.KEY_O:
                    response = 'O'
                elif key == glfw.KEY_D:
                    response = 'D'
                elif key == glfw.KEY_SPACE and response:
                    confirmed = True

                if response and not confirmed:
                    renderer.clear(GRAY)
                    renderer.draw_text_centered(font_ui, f"You selected: {response}",
                                                width // 2, height // 2 - 30, 40, LIGHT_GRAY)
                    renderer.draw_text_centered(font_ui, "SPACE to confirm, C/O/D to change",
                                                width // 2, height // 2 + 30, 40, LIGHT_GRAY)
                    draw_top_gradient()
                    renderer.flip()

            if not running:
                break

            reaction_time_ms = int((renderer.get_time() - response_start) * 1000)
            is_correct = (response == correct_letter)
            quest.update(log_contrast, is_correct)

            trial_log.append({
                'block': block_num,
                'trial': trial_num,
                'correct_letter': correct_letter,
                'response': response,
                'is_correct': is_correct,
                'contrast': float(contrast),
                'log_contrast': float(log_contrast),
                'reaction_time_ms': reaction_time_ms,
            })

            print(f"  Trial {trial_num}: contrast={contrast:.4f} (log={log_contrast:.2f}), "
                  f"letter={correct_letter}, response={response}, correct={is_correct}, "
                  f"rt={reaction_time_ms}ms")

            # Brief inter-trial pause (200ms)
            pause_end = renderer.get_time() + 0.2
            while renderer.get_time() < pause_end:
                renderer.poll_events()

        if running:
            threshold = quest.mean()
            threshold_sd = quest.sd()
            all_thresholds.append(threshold)
            all_sds.append(threshold_sd)

            n_correct = sum(quest.responses)
            n_total = len(quest.responses)
            accuracy = n_correct / n_total * 100 if n_total > 0 else 0
            print(f"\nBlock {block_num} Summary:")
            print(f"  Accuracy: {n_correct}/{n_total} = {accuracy:.1f}%")
            print(f"  Threshold = {threshold:.4f} (SD = {threshold_sd:.4f})")
            print(f"  Threshold linear = {10**threshold:.4f}")

    # Calculate final threshold
    if len(all_thresholds) == 2:
        final_threshold = np.mean(all_thresholds)
        final_sd = np.mean(all_sds)

        print(f"\nFinal Threshold (log10): {final_threshold:.4f}")
        print(f"Final Threshold (linear): {10**final_threshold:.6f}")

        renderer.clear(GRAY)
        results = [
            "Calibration Complete!",
            "",
            f"Block 1: {all_thresholds[0]:.4f} (SD: {all_sds[0]:.4f})",
            f"Block 2: {all_thresholds[1]:.4f} (SD: {all_sds[1]:.4f})",
            "",
            f"Final Threshold: {final_threshold:.4f}",
            f"Linear: {10**final_threshold:.4f}",
            "",
            "Press any key to exit."
        ]
        y_offset = height // 2 - 180
        for line in results:
            if line:
                renderer.draw_text_centered(font_ui, line, width // 2, y_offset, 40, LIGHT_GRAY)
            y_offset += 40
        draw_top_gradient()
        renderer.flip()

        renderer.wait_key()

        # Save to JSON
        threshold_data = {
            'threshold_log10': final_threshold,
            'threshold_linear': float(10 ** final_threshold),
            'threshold_sd': final_sd,
            'thresholds_log10': all_thresholds,
            'thresholds_linear': [float(10**t) for t in all_thresholds],
            'sds': all_sds,
            'participant': info,
            'timestamp': datetime.now().isoformat(),
            'display_calibration': display_cal.to_dict(),
            'trial_log': trial_log,
        }

        filename_base = f"{info['name']}_{info['timestamp']}_calibration"

        # Threshold file (used by step 2)
        threshold_file = os.path.join(data_folder, f"{filename_base}_threshold.json")
        with open(threshold_file, 'w') as f:
            json.dump(threshold_data, f, indent=2)
        print(f"Threshold saved to: {threshold_file}")

        # Full QUEST session log
        quest_file = os.path.join(data_folder, f"{filename_base}_quest.json")
        with open(quest_file, 'w') as f:
            json.dump(threshold_data, f, indent=2)

    renderer.delete_texture(gradient_tex)
    renderer.destroy()
    print("\nCalibration complete!")


if __name__ == "__main__":
    run_quest_calibration()
