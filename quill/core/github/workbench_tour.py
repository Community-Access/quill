"""The spoken tour of the GitHub Workbench (PRD D15, GH-R-115).

The first time the Workbench opens, and whenever Help > Take the Tour is
chosen, a short tour is spoken through the window's announcements: one step
per pane, in the order F6 visits them, each naming the pane and one thing to
do there. F6 moves on, F1 says the step again, Shift+F1 lists the steps, and
Escape skips the rest. It is the Walk Me Through It engine
(:mod:`quill.core.workbench.walk`), so a tour and a help task walk the same way.

The first-run tour starts once per person (``TOUR_ID`` in the tips file) and
not at all with **Show First time here? help** turned off. wx-free.
"""

from __future__ import annotations

__all__ = ["TOUR_ID", "TOUR_STEPS", "TOUR_TITLE"]

TOUR_ID = "workbench_tour"
TOUR_TITLE = "the GitHub Workbench tour"

#: One step per pane, in F6's order: tree, filter, list, details, status bar.
TOUR_STEPS: tuple[str, ...] = (
    "You are in the tree, the places GitHub has for you. Arrow to one and its rows "
    "fill the list; Right Arrow opens a branch. Press F6 for the next pane.",
    "This is the filter box. Type a word and only the rows with it stay; Escape "
    "clears it. Press F6.",
    "This is the list. Enter does the usual thing with a row, and Alt+Enter shows "
    "everything about it. Press F6.",
    "This is Details: the selected row in full, to read a line at a time. Press F6.",
    "This is the status bar: arrow across it to hear where you are and your hourly "
    "allowance. Press F6 to finish. F1, anywhere, is help for where you are.",
)
