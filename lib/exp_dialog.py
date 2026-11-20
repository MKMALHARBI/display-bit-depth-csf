"""
EXP_DIALOG.PY - Participant Information Dialog
===============================================
Collects participant info before experiment. Uses tkinter GUI.
Provides helpers to save/load participant info across pipeline steps.
"""

import random
import os
import re
import json
import glob
from datetime import datetime
from tkinter import messagebox

from lib.dialog_ui import (ParticipantDialog, parse_number, ID_PREFIX, ID_DIGITS, ID_PATTERN,
                           PRACTICE_PREFIX, NON_PARTICIPANT_PREFIXES)

DEFAULT_LOG_FILE = "SubjSeedinfo.txt"


def get_previous_subjects(log_file=None):
    if log_file is None:
        log_file = DEFAULT_LOG_FILE
    subjects = []
    if not os.path.exists(log_file):
        return subjects
    try:
        with open(log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 4:
                    subjects.append({
                        'name': parts[0],
                        'random_seed': parts[1],
                        'sex': parts[2],
                        'age': parts[3],
                        'level': parts[4] if len(parts) >= 5 else '',
                        'year': parts[5] if len(parts) >= 6 else '',
                    })
    except Exception as e:
        print(f"Warning: Could not read log file: {e}")
    return subjects


def save_participant_to_log(info, log_file=None):
    if log_file is None:
        log_file = DEFAULT_LOG_FILE
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    try:
        with open(log_file, 'a') as f:
            line = f"{info['name']}\t{info['random_seed']}\t{info['sex']}\t{info['age']}\t{info.get('ocular_dominance', '')}\t{info.get('level', '')}\t{info.get('year', '')}\n"
            f.write(line)
        print(f"Participant logged to: {log_file}")
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")


def check_duplicate_subject(subject_id, log_file=None):
    previous = get_previous_subjects(log_file)
    for subj in previous:
        if subj['name'] == subject_id:
            return True
    return False


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VIEWING_DISTANCE_MM = 700
BIT_DEPTHS = ["10-bit", "8-bit"]

# This project files each SESSION, not each participant, in its own folder:
# Data/<name>_10bit and Data/<name>_8bit (see create_data_folder). The shared
# dialog_ui helpers expect Data/<name>/, so the ID numbering and the list of
# former participants are worked out here instead, from the same folders.
_SESSION_FOLDER = re.compile(r"^(?P<name>.+?)_(?P<bits>10bit|8bit)$")
_REPLACED_SUFFIX = re.compile(r"_replaced_\d{8}_\d{6}$")


def _bit_tag(bit_depth):
    """'10-bit' -> '10bit', the tag used in the session folder name."""
    return (bit_depth or "10-bit").replace("-", "")


def session_folder_name(info):
    """Name of this session's folder inside Data/ - same rule as create_data_folder."""
    return f"{info['name']}_{_bit_tag(info.get('bit_depth'))}"


def _split_session_folder(folder_name):
    """'P001_10bit' -> ('P001', '10bit'). A folder without a depth tag -> (name, None)."""
    folder_name = _REPLACED_SUFFIX.sub("", folder_name)
    match = _SESSION_FOLDER.match(folder_name)
    if match:
        return match.group('name'), match.group('bits')
    return folder_name, None


def _next_participant_id(data_dirs, log_file=None):
    """Next unused automatic ID (P001, P002, ...) across every folder that holds
    session folders, and the subject log - so a number is never handed out twice."""
    names = []
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                names += [line.strip().split('\t')[0] for line in f if line.strip()]
        except OSError:
            pass
    for data_dir in data_dirs:
        for path in glob.glob(os.path.join(data_dir, "*")):
            if os.path.isdir(path):
                names.append(_split_session_folder(os.path.basename(path))[0])
    used = [0]
    for name in names:
        if name.startswith(PRACTICE_PREFIX):
            continue  # a practice run does not use up its number
        match = ID_PATTERN.match(name)
        if match:
            used.append(int(match.group(1)))
    return f"{ID_PREFIX}{max(used) + 1:0{ID_DIGITS}d}"


def _former_participants(data_dir, info_filename="participant_info.json"):
    """Former participants: {name: {'info': latest saved info, 'sessions': {bit tag: folder}}}.

    A participant's 10-bit and 8-bit folders are one entry. Test folders are left out.
    """
    former = {}
    for folder in sorted(glob.glob(os.path.join(data_dir, "*"))):
        if not os.path.isdir(folder):
            continue
        name, bits = _split_session_folder(os.path.basename(folder))
        if name.startswith(NON_PARTICIPANT_PREFIXES):
            continue
        record = former.setdefault(name, {'info': {}, 'sessions': {}, '_mtime': -1.0})
        if bits:
            record['sessions'][bits] = folder
        info_file = os.path.join(folder, info_filename)
        if os.path.exists(info_file):
            try:
                mtime = os.path.getmtime(info_file)
                if mtime > record['_mtime']:
                    with open(info_file, 'r') as f:
                        record['info'] = json.load(f)
                    record['_mtime'] = mtime
            except (OSError, ValueError):
                pass
    return former


class _SessionDialog(ParticipantDialog):
    """ParticipantDialog whose picker understands Data/<name>_<depth>/ folders.

    Same look and same methods as the shared dialog; only where the names come
    from differs. Picking a former participant is how their second bit depth is
    run (nothing is replaced), and it is a rerun only if that depth already has
    a folder.
    """

    def participant_picker(self, data_dirs, log_file=None, rerun_dir=None, on_pick=None,
                           info_filename="participant_info.json"):
        if isinstance(data_dirs, str):
            data_dirs = [data_dirs]
        self.new_id = _next_participant_id(data_dirs, log_file)
        records = _former_participants(rerun_dir or data_dirs[0], info_filename)
        self.former = {name: record['info'] for name, record in records.items()}
        self.sessions = {name: record['sessions'] for name, record in records.items()}
        self._new_choice = f"New participant: {self.new_id}"
        self._rerun_choices = {self._former_label(name): name for name in self.former}
        self._picker = self.combo("Participant", [self._new_choice] + list(self._rerun_choices),
                                  default=self._new_choice,
                                  hint="New ID is automatic. Former: other bit depth or rerun.")
        if on_pick:
            self._picker.bind("<<ComboboxSelected>>",
                              lambda event: self.rerun_name() and on_pick(self.former.get(self.rerun_name()) or {}))
        return self._picker

    def _former_label(self, name):
        done = [label for label in BIT_DEPTHS if _bit_tag(label) in self.sessions.get(name, {})]
        return f"{name}  (has {', '.join(done)})" if done else f"Rerun {name}"

    def has_session(self, name, bit_depth):
        """True if this former participant already has a folder at this bit depth."""
        return _bit_tag(bit_depth) in self.sessions.get(name, {})

    def confirm_rerun(self, bit_depth=None):
        """Ask before replacing a former participant's session at this bit depth."""
        name = self.rerun_name()
        if not name:
            return True
        if bit_depth is None:
            return super().confirm_rerun()
        return messagebox.askyesno(
            "Rerun participant",
            f"{name} already has a {bit_depth} session. Rerun it?\n\n"
            f"Their existing {bit_depth} data will be replaced by this new session; "
            "their other bit depth is not touched.\n"
            "(The old files are moved to the Data_replaced folder, not deleted.)")


def _last_experimenter(base_dir):
    """Experimenter name from the most recent session, to pre-fill the form."""
    files = glob.glob(os.path.join(base_dir, "Data", "*", "participant_info.json"))
    if not files:
        return None
    try:
        with open(max(files, key=os.path.getmtime), 'r') as f:
            name = json.load(f).get('experimenter')
    except (OSError, ValueError):
        return None
    return None if name in ('Test', 'Unknown') else name


def get_participant_info(experiment_name="Experiment", check_duplicates=True, log_file=None,
                         base_dir=None):
    """Show the participant dialog. Returns the info dict, or None if cancelled.

    Participant IDs are automatic (P001, P002, ...) - nothing is typed in. A
    former participant is picked from the list to run their other bit depth,
    or to rerun a depth they already did, which replaces that session's data
    ('rerun': True in the returned info).
    """
    base_dir = base_dir or PROJECT_DIR
    if log_file is None:
        log_file = os.path.join(base_dir, DEFAULT_LOG_FILE)
    data_dir = os.path.join(base_dir, "Data")
    # Every folder that holds session folders, so a P-number is never reused.
    id_dirs = [data_dir] + [os.path.join(base_dir, *parts) for parts in (
        ("Data_replaced",), ("old data",), ("old data", "Emulated_Data"), ("old code", "Data"))
        if os.path.isdir(os.path.join(base_dir, *parts))]

    def stamp():
        now = datetime.now()
        return {'timestamp': now.strftime("%Y%m%d_%H%M%S"),
                'date': now.strftime("%d %b %Y"),
                'time': now.strftime("%H:%M:%S")}

    def on_submit():
        quick = var_quicktest.get()

        ok, viewing_distance = parse_number(entry_view.get(), minimum=1)
        if not ok:
            dialog.error("Viewing distance must be a number of millimetres.")
            return
        if viewing_distance is None and not quick:
            dialog.error("Viewing distance is required!")
            return

        bit_depth = combo_bit.get() or "10-bit"
        output_bpc = combo_bpc.get() or "unknown"
        driver_dither = combo_dither.get() or "unknown"

        extras = {
            'quick_test': quick,
            'skip_calibration': var_skipcal.get(),
            'viewing_distance_mm': viewing_distance,
        }

        if quick:
            info = {
                'name': "Test_1",
                'age': 1,
                'sex': "O",
                'ocular_dominance': "OD (Right)",
                'level': "Undergraduate",
                'year': "1",
                'bit_depth': bit_depth,
                'output_bpc': output_bpc,
                'driver_dither': driver_dither,
                'random_seed': random.randint(1, 999999),
                'experimenter': "Test",
                'practice': True,
                'rerun': False,
            }
            info.update(extras)
            info.update(stamp())
            dialog.close(info)
            return

        name, former, practice = dialog.participant_name(practice=var_practice.get())
        # A former participant doing their other bit depth replaces nothing;
        # it is a rerun only when this depth already has a folder.
        rerun = bool(former) and dialog.has_session(name, bit_depth)
        if rerun and not dialog.confirm_rerun(bit_depth):
            return

        try:
            age = int(entry_age.get()) if entry_age.get().strip() else 0
        except ValueError:
            age = 0

        sex_map = {"Female": "F", "Male": "M", "Other": "O"}
        sex = sex_map.get(combo_sex.get(), "O")

        try:
            seed = int(entry_seed.get()) if entry_seed.get().strip() else random.randint(1, 999999)
        except ValueError:
            seed = random.randint(1, 999999)

        info = {
            'name': name,
            'age': age,
            'sex': sex,
            'ocular_dominance': combo_eye.get() or "OD (Right)",
            'level': combo_level.get() or "Undergraduate",
            'year': combo_year.get() or "1",
            'bit_depth': bit_depth,
            'output_bpc': output_bpc,
            'driver_dither': driver_dither,
            'random_seed': seed,
            'experimenter': entry_exp.get().strip() or "Unknown",
            'practice': practice,
            'rerun': rerun,
        }
        info.update(extras)
        info.update(stamp())
        dialog.close(info)

    def on_pick(saved):
        """Picking a former participant fills the form with their saved details.

        The seed keeps its fresh value (each session has always had its own),
        and the driver fields stay as they are: they describe today's display
        state, not the participant.
        """
        dialog.set_entry(entry_age, saved.get('age'))
        combo_sex.set({'F': 'Female', 'M': 'Male'}.get(saved.get('sex'), 'Other'))
        combo_eye.set(saved.get('ocular_dominance') or 'OD (Right)')
        combo_level.set(saved.get('level') or 'Undergraduate')
        combo_year.set(saved.get('year') or '1')
        if saved.get('experimenter'):
            dialog.set_entry(entry_exp, saved.get('experimenter'))
        if saved.get('viewing_distance_mm') is not None:
            dialog.set_entry(entry_view, float(saved['viewing_distance_mm']))
        # If only one bit depth has been run, the other one is what is due now.
        name = dialog.rerun_name()
        missing = [label for label in BIT_DEPTHS if not dialog.has_session(name, label)]
        if len(missing) == 1:
            combo_bit.set(missing[0])

    dialog = _SessionDialog(subtitle=experiment_name, on_submit=on_submit)

    dialog.section("Participant")
    dialog.participant_picker(id_dirs, log_file, rerun_dir=data_dir, on_pick=on_pick)
    entry_age = dialog.entry("Age")
    combo_sex = dialog.combo("Sex", ["Female", "Male", "Other"], default="Other")
    combo_eye = dialog.combo("Ocular dominance", ["OD (Right)", "OS (Left)"], default="OD (Right)")
    combo_level = dialog.combo("Level", ["Undergraduate", "Master", "PhD", "Other"], default="Undergraduate")
    combo_year = dialog.combo("Year", ["1", "2", "3", "4"], default="1")

    # Driver output state. Neither the link depth nor the driver's dithering is
    # readable from any API on Windows (NVIDIA Control Panel -> Change
    # resolution -> Output color depth; dithering is not exposed at all), so
    # both are entered per session and logged, as in luminance_test.py.
    dialog.section("Display")
    combo_bit = dialog.combo("Bit Depth", BIT_DEPTHS, default="10-bit")
    combo_bpc = dialog.combo("Driver Output Depth", ["8 bpc", "10 bpc", "unknown"], default="unknown")
    combo_dither = dialog.combo("Driver Dithering", ["on", "off", "unknown"], default="unknown")

    dialog.section("Session")
    entry_exp = dialog.entry("Experimenter", default=_last_experimenter(base_dir))
    entry_seed = dialog.entry("Random seed", default=random.randint(1, 999999))
    entry_view = dialog.entry("Viewing distance (mm)", default=DEFAULT_VIEWING_DISTANCE_MM, hint="Eye to screen")

    dialog.section("Options")
    var_practice = dialog.option("Practice mode", "Saved as Practice_ID, not logged")
    var_quicktest = dialog.option("Quick test", "Dummy participant, 10% of trials")
    var_skipcal = dialog.option("Skip calibration", "Reuse the last recorded calibration")

    return dialog.run(focus=entry_age)


def framebuffer_bits(info):
    """Framebuffer depth for this session, from the dialog's Bit Depth field.

    One source of truth for the condition. The same value names the data folder
    (Data/<name>_10bit), so a session cannot be run at one depth and filed under
    the other - which is what a separate module-level constant allowed.

    The depth has to be requested from OpenGL, not inherited from the OS:
    Windows grants a 10-bit framebuffer whatever the driver's output depth is
    set to and dithers the surplus away at scanout, so an "8-bit" run selected
    in the NVIDIA panel alone is a dithered 10-bit stimulus that still reports
    R=10. See DISPLAY_SETUP_8bit_vs_10bit.md section 9.
    """
    label = (info.get('bit_depth') or "10-bit").strip()
    return 8 if label.startswith("8") else 10


def create_data_folder(info, experiment_name=None, base_dir="."):
    """Create and return Data/{participant_name}_{bit_depth}/ folder."""
    bit_tag = (info.get('bit_depth') or "10-bit").replace("-", "")
    folder_name = f"{info['name']}_{bit_tag}"
    subject_folder = os.path.join(base_dir, "Data", folder_name)
    os.makedirs(subject_folder, exist_ok=True)
    return subject_folder


def save_participant_info(info, data_folder):
    """Save participant info to participant_info.json in the data folder."""
    info_file = os.path.join(data_folder, "participant_info.json")
    with open(info_file, 'w') as f:
        json.dump(info, f, indent=2)
    print(f"Participant info saved to: {info_file}")
    return info_file


def load_participant_info(base_dir):
    """Load participant info from the most recent participant_info.json.

    Searches Data/*/participant_info.json and returns the most recently
    modified one. Returns (info_dict, data_folder) or (None, None).
    """
    search_dir = os.path.join(base_dir, "Data")
    files = glob.glob(os.path.join(search_dir, "*", "participant_info.json"))
    if not files:
        return None, None
    files.sort(key=os.path.getmtime, reverse=True)
    latest = files[0]
    with open(latest, 'r') as f:
        info = json.load(f)
    data_folder = os.path.dirname(latest)
    print(f"Loaded participant info from: {latest}")
    return info, data_folder


if __name__ == "__main__":
    info = get_participant_info("Test Experiment")
    if info:
        print("Participant Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("Dialog cancelled")
