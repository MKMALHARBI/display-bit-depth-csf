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


def _default_font():
    """First existing sans-serif TTF for the current OS."""
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    return next((p for p in candidates if os.path.isfile(p)), candidates[2])


def _fc_match(name):
    """Ask fontconfig for a font file. Linux only; returns None elsewhere.

    fc-match always answers with SOMETHING - ask it for a face that is not
    installed and it hands back the default sans face - so the caller has to
    check that the file it names is actually the font requested.
    """
    try:
        result = subprocess.run(
            ['fc-match', '--format=%{file}', name],
            capture_output=True, text=True, timeout=5)
        path = result.stdout.strip()
        if path and os.path.isfile(path) and name.lower() in os.path.basename(path).lower():
            return path
    except Exception:
        pass
    return None


def _find_font(name, fallback):
    """UI font: fontconfig if it has it, otherwise any sans face.

    Only used for on-screen instructions, where the exact face does not matter.
    """
    return _fc_match(name) or fallback


def _find_optotype():
    """Path to the Sloan optotype face used for the stimulus letters.

    This one is NOT allowed to fall back to a text font. Sloan letters are
    drawn on a 5x5 grid with stroke width exactly 1/5 of letter height, so
    every glyph is square and all ten are equally legible by construction;
    that is what makes a threshold measured on one letter comparable to
    another, and to the MATLAB experiment this reproduces. Arial's letters are
    variable-width with varying stroke weight, so a run drawing Arial is a
    different experiment wearing the same name.

    The old code asked fc-match for 'Sloan' and fell back to Arial when that
    failed. fc-match does not exist on Windows, so every Windows run silently
    drew Arial.

    Order, first hit wins:
      1. $SLOAN_FONT, for a machine that keeps its fonts somewhere else
      2. fonts/ in this project - bundled, so a run does not depend on what
         happens to be installed
      3. the per-user and system Windows font folders
      4. fc-match, for Linux

    Raises RuntimeError rather than returning a substitute.
    """
    candidates = []

    env = os.environ.get('SLOAN_FONT')
    if env:
        candidates.append(env)

    candidates += [os.path.join(BASE_DIR, 'fonts', name)
                   for name in ('Sloan.otf', 'Sloan.ttf')]

    for folder in (os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                'Microsoft', 'Windows', 'Fonts'),
                   os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')):
        if os.path.isdir(folder):
            candidates += sorted(os.path.join(folder, f) for f in os.listdir(folder)
                                 if f.lower().startswith('sloan')
                                 and f.lower().endswith(('.otf', '.ttf')))

    fc = _fc_match('Sloan')
    if fc:
        candidates.append(fc)

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    raise RuntimeError(
        "Sloan optotype font not found - refusing to draw the stimulus in a text "
        "font.\n"
        "Put Sloan.otf in %s, or point $SLOAN_FONT at it.\n"
        "It is free from Denis Pelli's software page (psych.nyu.edu/pelli)."
        % os.path.join(BASE_DIR, 'fonts'))

params = {
    'letters': ['C', 'D', 'H', 'K', 'N', 'O', 'R', 'S', 'V', 'Z'],
    'noise_levels': [0],
    'font_size': 200,  # MATLAB: 128
    'frame_size': (300, 300),  # MATLAB: (204, 204)
    'n_noise_fields': 500,
    'stim_duration': 1.0,
    'quest_letters': ['C', 'O', 'D'],  # MATLAB: ['H', 'N']
    'quest_trials': 40,
    'quick_test_fraction': 0.10,  # Quick Test runs this share of the trials
}

fonts = {
    'stimulus': _find_optotype(),
    'ui': _find_font('Arial', _default_font()),
}

paths = {
    'base_dir': BASE_DIR,
}
