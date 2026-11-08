"""What the shared editing-tool windows are for: the F1 help's opening paragraph.

Paste Copied Files, the saved replace jobs and the fill-in form are shared by
QUILL and QUILL Lite (``quill/ui/paste_file.py``, ``quill/ui/replace_jobs*.py``,
``quill/ui/fill_in_dialog.py``), so their purposes are written once, here, and
merged into QUILL Lite's catalogue (:mod:`quill.core.lite_surface_help`) with the
project-task windows -- whose gate (GATE-LITE-HELP) scans those modules -- and
listed in its ``SHARED_WITH_QUILL``, so QUILL's F1 reads the same paragraph.
Keyed by window title, as every catalogue in the family is; the same wording
rules: one to three sentences, to the listener, no key tours.

wx-free.
"""

from __future__ import annotations

from quill.core.project_surface_help import PROJECT_PURPOSES

__all__ = ["EDITOR_TOOL_PURPOSES", "SHARED_TOOL_PURPOSES"]

EDITOR_TOOL_PURPOSES: dict[str, str] = {
    "Paste Copied Files": (
        "Choose what goes in for the files you copied in File Explorer: each "
        "file's text, read the way the editor opens it, or each file's full path. "
        "Files that are too large or are not text are left out and named."
    ),
    "Run Replace Job": (
        "Your saved find-and-replace jobs. Enter runs the one you are on, every "
        "step in order, on the selection or the whole document, as one change "
        "that Control Z takes back."
    ),
    "Manage Replace Jobs": (
        "Make, edit, rename and delete saved replace jobs. Every change is kept "
        "when this window closes."
    ),
    "Edit Replace Job": (
        "A replace job's name and its steps, in the order they run. Each step "
        "runs on the result of the one before."
    ),
    "Replace Step": (
        "One find-and-replace step: what to find, what it becomes, and whether "
        "to read it as a regular expression or match capital letters."
    ),
    "Fill In": (
        "This text asks for something before it goes in. Fill in each box or "
        "choose from each list, then press Enter; Escape puts nothing in."
    ),
}

#: Every shared window purpose QUILL Lite's catalogue merges in.
SHARED_TOOL_PURPOSES: dict[str, str] = {**PROJECT_PURPOSES, **EDITOR_TOOL_PURPOSES}
