"""
EXP_DIALOG.PY - Participant Information Dialog
===============================================
Collects participant info before experiment. Uses tkinter GUI.
Provides helpers to save/load participant info across pipeline steps.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
import os
import json
import glob
from datetime import datetime

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


def get_participant_info(experiment_name="Experiment", check_duplicates=True, log_file=None):
    result = {'cancelled': True}

    def on_submit():
        if var_quicktest.get():
            result['data'] = {
                'name': "Test_1",
                'age': 1,
                'sex': "O",
                'ocular_dominance': "OD (Right)",
                'level': "Undergraduate",
                'year': "1",
                'bit_depth': combo_bit.get() or "10-bit",
                'output_bpc': combo_bpc.get() or "unknown",
                'driver_dither': combo_dither.get() or "unknown",
                'random_seed': random.randint(1, 999999),
                'experimenter': "Test",
                'practice': True,
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'date': datetime.now().strftime("%d %b %Y"),
                'time': datetime.now().strftime("%H:%M:%S"),
            }
            result['cancelled'] = False
            root.destroy()
            return

        subject_id = entry_id.get().strip()
        if not subject_id:
            messagebox.showerror("Error", "Subject ID is required!")
            return

        if check_duplicates and not var_practice.get():
            if check_duplicate_subject(subject_id, log_file):
                if not messagebox.askyesno("Duplicate", f"Subject ID '{subject_id}' exists. Continue?"):
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

        experimenter = entry_exp.get().strip() or "Unknown"
        practice = var_practice.get()
        level = combo_level.get() or "Undergraduate"
        year = combo_year.get() or "1"

        ocular_dominance = combo_eye.get() or "OD (Right)"
        bit_depth = combo_bit.get() or "10-bit"
        output_bpc = combo_bpc.get() or "unknown"
        driver_dither = combo_dither.get() or "unknown"

        result['data'] = {
            'name': f"Practice_{subject_id}" if practice else subject_id,
            'age': age,
            'sex': sex,
            'ocular_dominance': ocular_dominance,
            'level': level,
            'year': year,
            'bit_depth': bit_depth,
            'output_bpc': output_bpc,
            'driver_dither': driver_dither,
            'random_seed': seed,
            'experimenter': experimenter,
            'practice': practice,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'date': datetime.now().strftime("%d %b %Y"),
            'time': datetime.now().strftime("%H:%M:%S"),
        }
        result['cancelled'] = False
        root.destroy()

    def on_cancel():
        root.destroy()

    root = tk.Tk()
    root.title(f"{experiment_name} - Participant Info")
    root.resizable(False, False)

    big_font = ("Arial", 18)
    entry_font = ("Arial", 16)
    btn_font = ("Arial", 16)

    style = ttk.Style()
    style.configure("Big.TLabel", font=big_font)
    style.configure("Big.TEntry", font=entry_font)
    style.configure("Big.TCheckbutton", font=big_font)
    style.configure("Big.TButton", font=btn_font)
    style.configure("Big.TCombobox", font=entry_font)
    root.option_add("*TCombobox*Listbox.font", entry_font)

    frame = ttk.Frame(root, padding="30")
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Subject ID:", style="Big.TLabel").grid(row=0, column=0, sticky="w", pady=10)
    entry_id = ttk.Entry(frame, width=25, font=entry_font)
    entry_id.grid(row=0, column=1, pady=10)

    ttk.Label(frame, text="Age:", style="Big.TLabel").grid(row=1, column=0, sticky="w", pady=10)
    entry_age = ttk.Entry(frame, width=25, font=entry_font)
    entry_age.grid(row=1, column=1, pady=10)

    ttk.Label(frame, text="Sex:", style="Big.TLabel").grid(row=2, column=0, sticky="w", pady=10)
    combo_sex = ttk.Combobox(frame, values=["Female", "Male", "Other"], width=23, font=entry_font, style="Big.TCombobox")
    combo_sex.set("Other")
    combo_sex.grid(row=2, column=1, pady=10)

    ttk.Label(frame, text="Ocular Dominance:", style="Big.TLabel").grid(row=3, column=0, sticky="w", pady=10)
    combo_eye = ttk.Combobox(frame, values=["OD (Right)", "OS (Left)"], width=23, font=entry_font, style="Big.TCombobox", state="readonly")
    combo_eye.set("OD (Right)")
    combo_eye.grid(row=3, column=1, pady=10)

    ttk.Label(frame, text="Level:", style="Big.TLabel").grid(row=4, column=0, sticky="w", pady=10)
    combo_level = ttk.Combobox(frame, values=["Undergraduate", "Master", "PhD", "Other"], width=23, font=entry_font, style="Big.TCombobox", state="readonly")
    combo_level.set("Undergraduate")
    combo_level.grid(row=4, column=1, pady=10)

    ttk.Label(frame, text="Year:", style="Big.TLabel").grid(row=5, column=0, sticky="w", pady=10)
    combo_year = ttk.Combobox(frame, values=["1", "2", "3", "4"], width=23, font=entry_font, style="Big.TCombobox", state="readonly")
    combo_year.set("1")
    combo_year.grid(row=5, column=1, pady=10)

    ttk.Label(frame, text="Bit Depth:", style="Big.TLabel").grid(row=6, column=0, sticky="w", pady=10)
    combo_bit = ttk.Combobox(frame, values=["10-bit", "8-bit"], width=23, font=entry_font, style="Big.TCombobox", state="readonly")
    combo_bit.set("10-bit")
    combo_bit.grid(row=6, column=1, pady=10)

    # Driver output state. Neither the link depth nor the driver's dithering is
    # readable from any API on Windows (NVIDIA Control Panel -> Change
    # resolution -> Output color depth; dithering is not exposed at all), so
    # both are entered per session and logged, as in luminance_test.py.
    ttk.Label(frame, text="Driver Output Depth:", style="Big.TLabel").grid(row=7, column=0, sticky="w", pady=10)
    combo_bpc = ttk.Combobox(frame, values=["8 bpc", "10 bpc", "unknown"], width=23, font=entry_font, style="Big.TCombobox", state="readonly")
    combo_bpc.set("unknown")
    combo_bpc.grid(row=7, column=1, pady=10)

    ttk.Label(frame, text="Driver Dithering:", style="Big.TLabel").grid(row=8, column=0, sticky="w", pady=10)
    combo_dither = ttk.Combobox(frame, values=["on", "off", "unknown"], width=23, font=entry_font, style="Big.TCombobox", state="readonly")
    combo_dither.set("unknown")
    combo_dither.grid(row=8, column=1, pady=10)

    ttk.Label(frame, text="Random Seed:", style="Big.TLabel").grid(row=9, column=0, sticky="w", pady=10)
    entry_seed = ttk.Entry(frame, width=25, font=entry_font)
    entry_seed.grid(row=9, column=1, pady=10)

    ttk.Label(frame, text="Experimenter:", style="Big.TLabel").grid(row=10, column=0, sticky="w", pady=10)
    entry_exp = ttk.Entry(frame, width=25, font=entry_font)
    entry_exp.grid(row=10, column=1, pady=10)

    var_practice = tk.BooleanVar()
    ttk.Checkbutton(frame, text="Practice Mode", variable=var_practice, style="Big.TCheckbutton").grid(row=11, column=1, sticky="w", pady=10)

    var_quicktest = tk.BooleanVar()
    ttk.Checkbutton(frame, text="Quick Test (skip dialog, all values = 1)", variable=var_quicktest, style="Big.TCheckbutton").grid(row=12, column=1, sticky="w", pady=10)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=13, column=0, columnspan=2, pady=30)
    ttk.Button(btn_frame, text="OK", command=on_submit, width=12, style="Big.TButton").pack(side=tk.LEFT, padx=15)
    ttk.Button(btn_frame, text="Cancel", command=on_cancel, width=12, style="Big.TButton").pack(side=tk.LEFT, padx=15)

    # Size the window to fit its content and center it, so no field, label or
    # checkbox is clipped regardless of font sizes or label lengths.
    root.update_idletasks()
    req_w, req_h = root.winfo_reqwidth(), root.winfo_reqheight()
    pos_x = max(0, (root.winfo_screenwidth() - req_w) // 2)
    pos_y = max(0, (root.winfo_screenheight() - req_h) // 2)
    root.geometry(f"{req_w}x{req_h}+{pos_x}+{pos_y}")

    entry_id.focus()
    root.mainloop()

    if result['cancelled']:
        return None
    return result['data']


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
