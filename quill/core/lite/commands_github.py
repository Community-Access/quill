"""The GitHub rows of QUILL Lite's File menu: the Workbench and Manage GitHub Accounts.

Split out of :mod:`quill.core.lite.commands` under GATE-11 and spliced back into
``COMMANDS`` where the Workbench row used to sit. The shape of every row is the
table's (``menu, label, key, handler, kind``).

**Manage GitHub Accounts** (2026-11-07) is QUILL's ``file.github_manage_accounts``
on the same shared flow (``quill/ui/github_accounts_flow.py``). It has no chord
because QUILL's has none (family rule 2), and it is a once-in-a-while command
(rule 9). Its access letter is H, for GitHub: every other letter in its name was
already spent in File, and Export as HTML gave H up because it keeps its chord,
Ctrl+Alt+Shift+End, as Print Preview keeps its own after giving V to Earlier
Versions. This row had no other keyboard route to fall back on.
"""

from __future__ import annotations

GITHUB_FILE_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&File", "&GitHub Workbench...", "", "cmd_github_workbench", ""),  # File, as in QUILL
    ("&File", "Manage Git&Hub Accounts...", "", "cmd_github_manage_accounts", ""),
)

__all__ = ["GITHUB_FILE_ROWS"]
