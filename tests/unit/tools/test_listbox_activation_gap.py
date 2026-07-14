"""GATE-13: no keyboard-inaccessible wx.ListBox double-click activation."""

from __future__ import annotations

from quill.tools.check_listbox_activation import check_listbox_activation


def test_no_listbox_activation_violations() -> None:
    violations = check_listbox_activation()
    assert not violations, "Keyboard-inaccessible list activation:\n" + "\n".join(violations)
