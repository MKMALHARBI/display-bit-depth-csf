"""
PARAMETERS.PY - Experiment Configuration
=========================================
CHANGED from MATLAB:
- font_size: 128 -> 108
- frame_size: (204, 204) -> (172, 172)
- size_noisefields removed: noise generated at frame_size directly
- quest_letters: ['H', 'N'] -> ['C', 'O', 'D'] (2AFC -> 3AFC)
- threshold saved to JSON instead of .mat
"""

import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_font(name, fallback):
    """Find font path via fc-match, fall back to a known path."""
    try:
        result = subprocess.run(
            ['fc-match', '--format=%{file}', name],
            capture_output=True, text=True, timeout=5)
        path = result.stdout.strip()
        if path and os.path.isfile(path):
            return path
    except Exception:
        pass
    return fallback

params = {
    'letters': ['C', 'D', 'H', 'K', 'N', 'O', 'R', 'S', 'V', 'Z'],
    'noise_levels': [0],
    'font_size': 200,  # MATLAB: 128
    'frame_size': (300, 300),  # MATLAB: (204, 204)
    'n_noise_fields': 500,
    'stim_duration': 1.0,
    'quest_letters': ['C', 'O', 'D'],  # MATLAB: ['H', 'N']
    'quest_trials': 40,
}

fonts = {
    'stimulus': _find_font(
        'Sloan',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
    'ui': _find_font(
        'Arial',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
}

paths = {
    'base_dir': BASE_DIR,
}
