"""Project tasks' reviewed persistence sites (code.md, agentic coding).

Split out under GATE-11, as the ChatGPT plan's sites were: the audit itself is
at its ceiling, so these reach it through :data:`AI_ENTRIES`. Every file here
lives in QUILL's own data folder, under ``<data>/ai``, never in the project, so
a project someone downloads cannot approve its own commands or tools.
"""

from __future__ import annotations

PROJECT_ENTRIES: dict[str, str] = {
    # <data>/ai/projects/<key>/checkpoints/turns.json: the index of private
    # copies Undo Last Agent Turn restores from, under a version stamp, pruned
    # to the last turns. Lost, undo has nothing to offer for earlier turns and
    # says so; the project's files are untouched.
    "core/ai/checkpoints.py::_save": "cache",
    # <data>/ai/projects/<key>/allowed_commands.json: the person's own list of
    # commands that run without asking, and the Run commands without asking
    # switch. A version-1 envelope; a damaged or unknown file reads as an empty
    # list with the switch off, which only means more questions.
    "core/ai/command_runner.py::_write": "versioned",
    # <data>/ai/recent_projects.json: the recent projects, newest first, capped.
    # Recency only; lost, the list starts empty.
    "core/ai/project_store.py::add": "cache",
    "core/ai/project_store.py::remove": "cache",
    # <data>/ai/projects/<key>/instructions.json: the one answer to "use this
    # project's agent notes?". Lost, QUILL asks again.
    "core/ai/project_store.py::set_instruction_choice": "marker",
    # <data>/ai/projects/<key>/vendor_tools.json: which of an engine's own
    # tools the person checked, per engine. A version-1 envelope; a damaged or
    # unknown file reads as every tool off, the default.
    "core/ai/vendor_tools.py::set_enabled": "versioned",
}
