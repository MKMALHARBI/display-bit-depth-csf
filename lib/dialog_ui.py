"""
DIALOG_UI.PY - Shared look and helpers for the participant dialog
=================================================================
This file is identical in every project. It holds only what is common:

  * the visual style (cards, fonts, colours, buttons),
  * automatic participant IDs (P001, P002, ...),
  * the "rerun a former participant" list and moving their old data aside,
  * small parsing helpers.

Which fields a project asks for, their choices and defaults, and what is
saved, all live in that project's own exp_dialog.py - not here.
"""

import glob
import json
import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

# ---- Automatic participant IDs ------------------------------------------

ID_PREFIX = "P"
ID_DIGITS = 3
ID_PATTERN = re.compile(r"^%s(\d+)$" % ID_PREFIX)
PRACTICE_PREFIX = "Practice_"
NON_PARTICIPANT_PREFIXES = ("Test_",)


def _log_names(log_file):
    """Participant names (first tab-separated column) from the subject log."""
    names = []
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        names.append(line.split('\t')[0])
        except OSError:
            pass
    return names


def next_participant_id(data_dirs, log_file=None):
    """Next unused automatic participant ID (P001, P002, ...).

    data_dirs: one folder or a list of folders that hold participant folders.
    Every P-number already used in any of them, or in the subject log, is
    skipped, so a number is never handed out twice.
    """
    if isinstance(data_dirs, str):
        data_dirs = [data_dirs]
    names = _log_names(log_file)
    for data_dir in data_dirs:
        names += [os.path.basename(p) for p in glob.glob(os.path.join(data_dir, "*")) if os.path.isdir(p)]
    used = [0]
    for name in names:
        if name.startswith(PRACTICE_PREFIX):
            continue
        match = ID_PATTERN.match(name)
        if match:
            used.append(int(match.group(1)))
    return f"{ID_PREFIX}{max(used) + 1:0{ID_DIGITS}d}"


def list_participants(data_dir, info_filename="participant_info.json"):
    """Former participants that can be rerun: {folder name: saved info dict}.

    Every folder in data_dir counts (test folders excluded). The saved info is
    read from info_filename when it exists, else an empty dict.
    """
    participants = {}
    for folder in sorted(glob.glob(os.path.join(data_dir, "*"))):
        name = os.path.basename(folder)
        if not os.path.isdir(folder) or name.startswith(NON_PARTICIPANT_PREFIXES):
            continue
        info = {}
        info_file = os.path.join(folder, info_filename)
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    info = json.load(f)
            except (OSError, ValueError):
                info = {}
        participants[name] = info
    return participants


def move_aside_participant_data(base_dir, name, timestamp, data_dirname="Data"):
    """Before a rerun, move a participant's existing folder to Data_replaced/.

    Nothing is deleted: the old session is kept outside the data folder, where
    the analysis scripts do not read it. Returns the new location, or None if
    the participant had no folder.
    """
    old_folder = os.path.join(base_dir, data_dirname, name)
    if not os.path.isdir(old_folder):
        return None
    replaced_root = os.path.join(base_dir, "Data_replaced")
    os.makedirs(replaced_root, exist_ok=True)
    target = os.path.join(replaced_root, f"{name}_replaced_{timestamp}")
    shutil.move(old_folder, target)
    print(f"RERUN of {name}: previous data moved to {target}")
    return target


def parse_number(text, minimum=None, allow_blank=True):
    """Return (ok, value). Blank -> (allow_blank, None)."""
    text = (text or "").strip()
    if not text:
        return allow_blank, None
    try:
        value = float(text)
    except ValueError:
        return False, None
    if minimum is not None and value < minimum:
        return False, None
    return True, value


# ---- The dialog window --------------------------------------------------

PAGE = "#eef1f5"        # window background
CARD = "#ffffff"        # section background
BORDER = "#d5dae1"      # card outline
TEXT = "#1f2328"        # main text
MUTED = "#5f6b7a"       # field labels, hints
ACCENT = "#2563eb"      # section titles, primary button
ACCENT_DARK = "#1d4ed8"
FONT = "Segoe UI"

FIELD_CHARS = 24        # width of every input, in characters
COL_GAP = 12            # half the gap between the two columns


class ParticipantDialog:
    """A styled two-column form. Build it with section()/entry()/combo()/option(),
    then call run(). on_submit is called for Start / Enter; call close(result)
    from it to accept, or just return to keep the dialog open."""

    def __init__(self, title="Participant setup", subtitle="", on_submit=None):
        self.result = None
        self._on_submit = on_submit
        self._card = None
        self._row = 0

        self.root = root = tk.Tk()
        root.title(title)
        root.resizable(False, False)
        root.configure(bg=PAGE)

        self.field_font = (FONT, 13)
        label_font = (FONT, 11)
        style = ttk.Style()
        style.configure("Page.TFrame", background=PAGE)
        style.configure("Card.TFrame", background=CARD)
        style.configure("Title.TLabel", background=PAGE, foreground=TEXT, font=(FONT, 18, "bold"))
        style.configure("Sub.TLabel", background=PAGE, foreground=MUTED, font=label_font)
        style.configure("Section.TLabel", background=CARD, foreground=ACCENT, font=(FONT, 12, "bold"))
        style.configure("Field.TLabel", background=CARD, foreground=MUTED, font=label_font)
        style.configure("Hint.TLabel", background=CARD, foreground=MUTED, font=(FONT, 10))
        style.configure("Option.TCheckbutton", background=CARD, foreground=TEXT, font=self.field_font)
        style.map("Option.TCheckbutton", background=[("active", CARD)])
        root.option_add("*TCombobox*Listbox.font", self.field_font)

        self.page = ttk.Frame(root, padding=(28, 22, 28, 22), style="Page.TFrame")
        self.page.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self.page, text=title, style="Title.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(self.page, text=subtitle, style="Sub.TLabel").pack(anchor="w")

    # -- layout ----------------------------------------------------------

    def section(self, title):
        """Start a new white card with a coloured heading."""
        outline = tk.Frame(self.page, bg=BORDER)
        outline.pack(fill="x", pady=(14, 0))
        card = ttk.Frame(outline, padding=(20, 14, 20, 16), style="Card.TFrame")
        card.pack(fill="both", expand=True, padx=1, pady=1)
        card.grid_columnconfigure(0, weight=1, uniform="col")
        card.grid_columnconfigure(1, weight=1, uniform="col")
        ttk.Label(card, text=title, style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self._card = card
        self._row = 1
        self._column = 0

    def _next_cell(self):
        """Fields fill the card left to right, two per row."""
        row, column = self._row, self._column
        if column == 0:
            self._column = 1
        else:
            self._column = 0
            self._row += 1
        return row, column

    def _field_cell(self, label, hint):
        row, column = self._next_cell()
        cell = ttk.Frame(self._card, style="Card.TFrame")
        cell.grid(row=row, column=column, sticky="new", pady=7,
                  padx=(0, COL_GAP) if column == 0 else (COL_GAP, 0))
        ttk.Label(cell, text=label, style="Field.TLabel").pack(anchor="w")
        return cell

    def _place(self, cell, widget, hint):
        widget.pack(anchor="w", fill="x", pady=(3, 0), ipady=3)
        if hint:
            ttk.Label(cell, text=hint, style="Hint.TLabel").pack(anchor="w", pady=(3, 0))
        return widget

    def entry(self, label, default=None, hint=None):
        """A text field. Returns the ttk.Entry."""
        cell = self._field_cell(label, hint)
        widget = self._place(cell, ttk.Entry(cell, width=FIELD_CHARS, font=self.field_font), hint)
        if default not in (None, ""):
            widget.insert(0, f"{default:g}" if isinstance(default, float) else str(default))
        return widget

    def combo(self, label, values, default=None, hint=None, readonly=True):
        """A drop-down. Returns the ttk.Combobox. Its list is as wide as its longest entry."""
        cell = self._field_cell(label, hint)
        widget = self._place(cell, ttk.Combobox(cell, values=list(values), width=FIELD_CHARS - 2,
                                                font=self.field_font,
                                                state="readonly" if readonly else "normal"), hint)
        if default is not None:
            widget.set(default)
        longest = max((len(str(v)) for v in values), default=0)
        widget.configure(postcommand=lambda: widget.tk.eval(
            f"catch {{[ttk::combobox::PopdownWindow {widget}].f.l configure -width {longest + 2}}}"))
        return widget

    def option(self, text, hint="", default=False):
        """A checkbox with a muted one-line explanation. Returns its tk.BooleanVar."""
        row, column = self._next_cell()
        variable = tk.BooleanVar(value=default)
        cell = ttk.Frame(self._card, style="Card.TFrame")
        cell.grid(row=row, column=column, sticky="nw", pady=6,
                  padx=(0, COL_GAP) if column == 0 else (COL_GAP, 0))
        ttk.Checkbutton(cell, text=text, variable=variable, style="Option.TCheckbutton").pack(anchor="w")
        if hint:
            ttk.Label(cell, text=hint, style="Hint.TLabel").pack(anchor="w", padx=(26, 0))
        return variable

    # -- participant picker ------------------------------------------------

    def participant_picker(self, data_dirs, log_file=None, rerun_dir=None, on_pick=None,
                           info_filename="participant_info.json"):
        """The 'Participant' drop-down: a new automatic ID, or a former participant to rerun.

        data_dirs : folder(s) scanned so a P-number is never reused.
        rerun_dir : folder whose participants are offered for rerun (default: first data dir).
        on_pick   : called with the saved info dict when a former participant is chosen,
                    so the project can fill its own fields.
        """
        if isinstance(data_dirs, str):
            data_dirs = [data_dirs]
        self.new_id = next_participant_id(data_dirs, log_file)
        self.former = list_participants(rerun_dir or data_dirs[0], info_filename)
        self._new_choice = f"New participant: {self.new_id}"
        self._rerun_choices = {f"Rerun {name}": name for name in self.former}
        self._picker = self.combo("Participant", [self._new_choice] + list(self._rerun_choices),
                                  default=self._new_choice,
                                  hint="New ID is automatic. Rerun replaces that person's data.")
        if on_pick:
            self._picker.bind("<<ComboboxSelected>>",
                              lambda event: self.rerun_name() and on_pick(self.former.get(self.rerun_name()) or {}))
        return self._picker

    def rerun_name(self):
        """Folder name of the former participant chosen for rerun, or None for a new one."""
        return self._rerun_choices.get(self._picker.get())

    def confirm_rerun(self):
        """Ask before replacing a former participant's data. True if OK (or not a rerun)."""
        name = self.rerun_name()
        if not name:
            return True
        return messagebox.askyesno(
            "Rerun participant",
            f"Rerun {name}?\n\n"
            "Their existing data will be replaced by this new session.\n"
            "(The old files are moved to the Data_replaced folder, not deleted.)")

    def participant_name(self, practice=False):
        """(name, rerun, practice) for the current picker choice."""
        rerun = self.rerun_name()
        if rerun:
            return rerun, True, rerun.startswith(PRACTICE_PREFIX)
        return (f"{PRACTICE_PREFIX}{self.new_id}" if practice else self.new_id), False, practice

    # -- helpers for filling fields ------------------------------------------

    @staticmethod
    def set_entry(entry, value):
        entry.delete(0, tk.END)
        if value not in (None, ""):
            entry.insert(0, f"{value:g}" if isinstance(value, float) else str(value))

    @staticmethod
    def error(message):
        messagebox.showerror("Error", message)

    # -- running -------------------------------------------------------------

    def close(self, result):
        """Accept the dialog with this result."""
        self.result = result
        self.root.destroy()

    def cancel(self):
        self.result = None
        self.root.destroy()

    def run(self, focus=None):
        """Add the buttons, show the window, and return the result (None if cancelled)."""
        btn_frame = ttk.Frame(self.page, style="Page.TFrame")
        btn_frame.pack(fill="x", pady=(20, 0))
        tk.Button(btn_frame, text="Start", command=self._on_submit, font=(FONT, 12, "bold"), width=12,
                  bg=ACCENT, fg="#ffffff", activebackground=ACCENT_DARK, activeforeground="#ffffff",
                  relief="flat", bd=0, padx=10, pady=7, cursor="hand2").pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="Cancel", command=self.cancel, font=(FONT, 12), width=12,
                  bg=CARD, fg=TEXT, activebackground=BORDER, relief="flat", bd=0,
                  highlightthickness=1, highlightbackground=BORDER,
                  padx=10, pady=7, cursor="hand2").pack(side=tk.RIGHT, padx=(0, 12))
        self.root.bind("<Return>", lambda event: self._on_submit())
        self.root.bind("<Escape>", lambda event: self.cancel())
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)

        # Size the window to fit its content and centre it.
        self.root.update_idletasks()
        req_w, req_h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        pos_x = max(0, (self.root.winfo_screenwidth() - req_w) // 2)
        pos_y = max(0, (self.root.winfo_screenheight() - req_h) // 2 - 20)
        self.root.geometry(f"{req_w}x{req_h}+{pos_x}+{pos_y}")

        if focus is not None:
            focus.focus()
        self.root.mainloop()
        return self.result
