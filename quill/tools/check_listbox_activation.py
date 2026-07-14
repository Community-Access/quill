"""No keyboard-inaccessible list activation gate (GATE-13).

A ``wx.ListBox`` emits no item-activated event, so a list that binds **only**
``EVT_LISTBOX_DCLICK`` to an action is unreachable for keyboard and screen-reader
users — they cannot trigger the double-click action at all. The accessible fix is
``quill.ui.dialog_contract.apply_listbox_activation`` (which binds the double-click
plus Enter / NumpadEnter / Space), or a hand-written key handler.

This gate flags any ``quill/ui`` module that binds ``EVT_LISTBOX_DCLICK`` directly
**and** has no keyboard-activation mechanism in the same file (no
``apply_listbox_activation`` call and no ``EVT_KEY_DOWN`` / ``EVT_CHAR_HOOK``
handler). A reviewer adding a new ``EVT_LISTBOX_DCLICK`` binding must pair it with
keyboard activation, which this forces.

Run::

    python -m quill.tools.check_listbox_activation

Or via pytest (``tests/unit/tools/test_listbox_activation_gap.py``). Exit code is
non-zero on any violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# A direct double-click bind: ``something.Bind(wx.EVT_LISTBOX_DCLICK, ...)``.
_DIRECT_DCLICK_RE = re.compile(r"\.Bind\(\s*[\w.]*EVT_LISTBOX_DCLICK")
# Any keyboard-activation mechanism that makes the list reachable by keyboard.
_KEYBOARD_RE = re.compile(r"apply_listbox_activation|EVT_KEY_DOWN|EVT_CHAR_HOOK")

# Files allowed to bind EVT_LISTBOX_DCLICK directly for a documented reason.
_ALLOWLIST: frozenset[str] = frozenset({
    # dialog_contract.py defines apply_listbox_activation (the sanctioned helper).
    "quill/ui/dialog_contract.py",
})


def check_listbox_activation(root: Path = _REPO_ROOT) -> list[str]:
    """Return a list of violation messages (empty = clean)."""
    violations: list[str] = []
    ui_dir = root / "quill" / "ui"
    if not ui_dir.is_dir():
        return violations
    for py_file in sorted(ui_dir.glob("*.py")):
        rel = py_file.relative_to(root).as_posix()
        if rel in _ALLOWLIST:
            continue
        src = py_file.read_text(encoding="utf-8")
        if not _DIRECT_DCLICK_RE.search(src):
            continue
        if _KEYBOARD_RE.search(src):
            continue
        violations.append(
            f"{rel}: binds EVT_LISTBOX_DCLICK with no keyboard activation. Use "
            f"quill.ui.dialog_contract.apply_listbox_activation(listbox, handler) so "
            f"Enter/Space also activate the item (GATE-13)."
        )
    return violations


def main() -> int:
    violations = check_listbox_activation()
    if violations:
        print("GATE-13 keyboard-inaccessible list activation:")
        for message in violations:
            print(f"  {message}")
        return 1
    print("GATE-13 listbox-activation check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
