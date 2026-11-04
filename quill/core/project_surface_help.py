"""What each project-task window is for: the F1 help's opening paragraph (code.md 5.7).

The windows are shared by QUILL and QUILL Lite (``quill/ui/project_*.py``), so
their purposes are written once, here, and merged into QUILL Lite's catalogue
(:mod:`quill.core.lite_surface_help`), whose gate (GATE-LITE-HELP) scans those
modules. Keyed by window title, as every catalogue in the family is. The same
wording rules: one to three sentences, to the listener, no key tours.

wx-free.
"""

from __future__ import annotations

__all__ = ["PROJECT_PURPOSES"]

PROJECT_PURPOSES: dict[str, str] = {
    "Do a Project Task": (
        "Tell the AI what to do in your project folder. It plans, reads and proposes "
        "changes; nothing is written until you accept it in Review Changes, and no "
        "command runs until you allow it. Plan, Changes and Output are one key each."
    ),
    "Review Changes": (
        "Every file this turn would change, then each change in it, with line numbers. "
        "Accept or reject each one; Apply Accepted Changes writes them all at once, "
        "after QUILL has kept a copy for Undo Last Turn."
    ),
    "Run This Command?": (
        "The agent wants to run a command in your project folder. The exact command "
        "is below the sentence, and a warning appears when QUILL sees a risk. QUILL "
        "cannot stop an allowed command from doing what your account can do."
    ),
    "Commands Allowed in This Project": (
        "The commands this project runs without asking, kept in QUILL and never in "
        "the project. Run commands without asking is here too, off until you check "
        "it and confirm."
    ),
    "Open Project Folder": (
        "Choose a folder to work on as a project. Your recent projects are listed "
        "first; Browse for a Folder picks any other."
    ),
    "Use This Project's Agent Notes?": (
        "This project has notes written for AI agents. Use them, leave them out, or "
        "read them first. QUILL asks once per project, and nothing in them can "
        "approve a command or a change."
    ),
    "Engine Tools for This Project": (
        "The engine's own tools, beside QUILL's. All are off until you check them, "
        "each use still asks you first, and their edits skip Review Changes."
    ),
}
