"""Tkinter GUI: load files, see a traffic-light list, save cleaned copies."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .cleaner import clean_file
from .cli import summary
from .core import Finding, Risk, scan_file

# Drag-and-drop is optional: it only switches on if tkinterdnd2 loads cleanly.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # the "gui" extra is not installed
    DND_FILES = TkinterDnD = None

_ROW_COLORS = {Risk.HIGH: "#f6c6c0", Risk.MEDIUM: "#fbe9a6", Risk.LOW: "#cfe8cf"}
_FILETYPES = [
    ("Supported files", "*.jpg *.jpeg *.png *.webp *.heic *.heif *.pdf *.docx *.xlsx *.pptx"),
    ("All files", "*.*"),
]


def make_root() -> tk.Tk:
    """Create the main window, with drag-and-drop support if it works here."""
    if TkinterDnD is not None:
        try:
            return TkinterDnD.Tk()
        except (RuntimeError, tk.TclError):
            pass
    return tk.Tk()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.files: list[Path] = []
        self.results: dict[Path, list[Finding] | str] = {}  # findings, or an error text

        root.title(f"metamoult {__version__}")
        root.geometry("1000x520")
        self._build()
        self._enable_drop()

    # --- layout -----------------------------------------------------------

    def _build(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Open files…", command=self.open_dialog).pack(side="left")
        self.save_button = ttk.Button(
            top, text="Save cleaned copy", command=self.save_cleaned, state="disabled")
        self.save_button.pack(side="left", padx=8)
        self.hint = ttk.Label(top, text="Open files or drop them here. Originals are never changed.")
        self.hint.pack(side="left", padx=8)

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8)

        self.listbox = tk.Listbox(body, selectmode="extended", exportselection=False, width=28)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self._on_select())
        body.add(self.listbox, weight=1)

        right = ttk.Frame(body)
        body.add(right, weight=4)
        self.summary = ttk.Label(right, text="No file loaded.", font=("TkDefaultFont", 10, "bold"))
        self.summary.pack(anchor="w", pady=(0, 4))

        columns = ("risk", "field", "value", "meaning")
        self.tree = ttk.Treeview(right, columns=columns, show="headings", selectmode="browse")
        for name, title, width in (("risk", "Risk", 70), ("field", "Field", 170),
                                   ("value", "Value", 220), ("meaning", "What it means", 420)):
            self.tree.heading(name, text=title)
            self.tree.column(name, width=width, anchor="w")
        for risk, color in _ROW_COLORS.items():
            self.tree.tag_configure(risk.value, background=color, foreground="black")
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.status = ttk.Label(self.root, text="", padding=8)
        self.status.pack(fill="x")

    def _enable_drop(self) -> None:
        if DND_FILES is None or not hasattr(self.root, "drop_target_register"):
            return
        try:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", lambda e: self.add_files(self.root.tk.splitlist(e.data)))
        except (tk.TclError, RuntimeError):
            pass  # drag-and-drop is a bonus; the dialog always works

    # --- actions ----------------------------------------------------------

    def open_dialog(self) -> None:
        paths = filedialog.askopenfilenames(title="Choose files", filetypes=_FILETYPES)
        if paths:
            self.add_files(paths)

    def add_files(self, paths) -> None:
        """Scan the given files and add them to the list."""
        new = []
        for raw in paths:
            path = Path(raw)
            if path in self.results:
                continue
            try:
                self.results[path] = scan_file(path)
            except Exception as exc:  # unsupported, damaged, protected, ...
                self.results[path] = str(exc)
            self.files.append(path)
            self.listbox.insert("end", path.name)
            new.append(len(self.files) - 1)
        if new:
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(new[-1])
            self.listbox.see(new[-1])
            self._on_select()

    def _selected(self) -> list[Path]:
        return [self.files[i] for i in self.listbox.curselection()]

    def _on_select(self) -> None:
        selected = self._selected()
        self.tree.delete(*self.tree.get_children())
        self.save_button.configure(state="normal" if selected else "disabled")
        if not selected:
            self.summary.configure(text="No file selected.")
            return
        result = self.results[selected[0]]
        if isinstance(result, str):
            self.summary.configure(text=f"{selected[0].name}: {result}")
            self.save_button.configure(state="disabled")
            return
        self.summary.configure(text=f"{selected[0].name}: {summary(result)}")
        for f in result:
            self.tree.insert("", "end", tags=(f.risk.value,), values=(
                f.risk.value.upper(), f.field, " ".join(f.value.split()), f.explanation))

    def save_cleaned(self) -> None:
        """Write cleaned copies of the selected files and show the re-scan."""
        lines, last = [], None
        for path in self._selected():
            if isinstance(self.results.get(path), str):
                continue
            try:
                result = clean_file(path)
            except Exception as exc:
                messagebox.showerror("metamoult", f"{path.name}: {exc}")
                continue
            self.add_files([result.output])
            last = result.output
            lines.append(f"{result.output.name}: {summary(result.after)}")
        if last is not None:
            self.status.configure(text="Saved: " + "; ".join(lines))
            index = self.files.index(last)
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(index)
            self._on_select()


def main() -> int:
    root = make_root()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
