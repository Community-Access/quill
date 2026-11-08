"""The Replace Jobs rows of QUILL Lite's menu bar: saved find-and-replace lists.

Split out of :mod:`quill.core.lite.commands` under GATE-11 and spliced back into
``COMMANDS`` after Replace Across Files, where somebody looking for a better
Replace already is. The handlers are QUILL's (``quill/ui/replace_jobs.py``,
shared), and QUILL has the same two rows beside its Multi Replace.

No chord: none was free in both editors (measured 2026-11-07), and running a
saved job is a once-a-document chore rather than an editing-loop key (rule 9).
Alt+E, J, then R or M.
"""

from __future__ import annotations

REPLACE_JOB_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Edit", "Replace &Jobs", "", "", "sub"),
    ("&Edit|Replace &Jobs", "&Run Replace Job...", "", "cmd_run_replace_job", ""),
    ("&Edit|Replace &Jobs", "&Manage Replace Jobs...", "", "cmd_manage_replace_jobs", ""),
)

__all__ = ["REPLACE_JOB_ROWS"]
