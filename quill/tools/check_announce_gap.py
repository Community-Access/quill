"""Announce-gap gate (GATE-12).

Prevents the regression where a dialog updates a status StaticText via
``SetLabel`` without announcing the change to screen readers (finding #43
from the 2026-06-12 golden-state review).

A file is flagged when ALL of the following are true:
  1. It lives under ``quill/ui/`` or ``quill/devtools/``.
  2. It assigns a wx.StaticText to a variable whose name contains one of the
     status-signal words: status, progress, info, msg, error, hint.
  3. It calls ``.SetLabel(`` somewhere (updating a control label).
  4. It contains NO announcement calls: ``_announce(``, ``announce_cb``,
     or a standalone ``announce(`` call.

This gate is intentionally narrow: it only catches the systemic gap pattern
(silent status-text updates) and does NOT flag every SetLabel call, since
many are legitimate (button labels, column headers, display names).

Run directly::

    python -m quill.tools.check_announce_gap

Or via pytest (``tests/unit/tools/test_announce_gap.py``). Exit code is
non-zero when any violation is found.

ALLOWLIST: add entries here for known-safe files where SetLabel is used
legitimately without announce (e.g., purely navigational path labels that
are backed by a list control whose selection event already announces, or
files where a positional ``announce`` parameter name differs from the
detection pattern).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Variable names that signal a status-display control.
_STATUS_NAME_RE = re.compile(
    r"(?:self\._?|_?)(?:status|progress|info|msg|error|hint)[_A-Za-z0-9]*\s*="
    r"\s*(?:wx\.StaticText|StaticText)\s*\(",
    re.IGNORECASE,
)

# Any announcement mechanism: _announce, _announce_fn, announce_cb, announce param.
_ANNOUNCE_RE = re.compile(
    r"(?:self\._announce(?:_fn)?\(|announce_cb|announce\(|announce_fn)",
)

# Files known to use SetLabel legitimately without announcement.
_ALLOWLIST: frozenset[str] = frozenset({
    # RemoteBrowserDialog path_label is a navigation indicator backed by
    # the list control's selection event (which already announces).
    # The _populate() call does announce via _announce(self._cwd) now,
    # but the control variable name doesn't match the status pattern.
    # quillin_wizard.py uses a positional `announce` param, not _announce.
    "quill/ui/quillin_wizard.py",
    # The four AI dialogs below are pre-existing violations that existed before
    # GATE-12 was introduced in the x3 wave. They need announce_cb + _set_status
    # added in a follow-up pass (tracked as part of the a11y backlog).
    "quill/ui/ai_document_qa_dialog.py",
    "quill/ui/ai_spell_check_dialog.py",
    "quill/ui/ai_thesaurus_dialog.py",
    "quill/ui/ai_translation_dialog.py",
})


def check_announce_gap(root: Path = _REPO_ROOT) -> list[str]:
    """Return a list of violation messages (empty = clean)."""
    violations: list[str] = []
    search_dirs = [root / "quill" / "ui", root / "quill" / "devtools"]
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for py_file in sorted(search_dir.glob("*.py")):
            rel = py_file.relative_to(root).as_posix()
            if rel in _ALLOWLIST:
                continue
            src = py_file.read_text(encoding="utf-8")
            if not _STATUS_NAME_RE.search(src):
                continue
            if ".SetLabel(" not in src:
                continue
            if _ANNOUNCE_RE.search(src):
                continue
            count = src.count(".SetLabel(")
            violations.append(
                f"{rel}: {count} SetLabel call(s) on a status control "
                f"but no announcement mechanism found. "
                f"Add announce_cb parameter and _set_status() helper "
                f"(see ai_chat_dialog.py for the pattern), or add to "
                f"_ALLOWLIST in check_announce_gap.py if SetLabel is not "
                f"used for user-facing status messages."
            )
    return violations


def main() -> int:
    violations = check_announce_gap()
    if violations:
        for v in violations:
            print(f"GATE-12 violation: {v}", file=sys.stderr)
        return 1
    print("GATE-12 announce-gap check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
