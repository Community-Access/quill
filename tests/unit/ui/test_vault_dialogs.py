"""Seam tests for VaultListDialog (no live wx control tree).

Guards the wx-free logic: the row labels it shows and how activating a row hands
the row's payload to the callback. The ListBox and keyboard wiring are exercised
by hand with a screen reader.
"""

from __future__ import annotations

from quill.ui.vault_dialogs import VaultListDialog


def _dialog(items, on_activate=None):
    return VaultListDialog(wx=object(), heading="Backlinks", items=items, on_activate=on_activate)


def test_labels_are_exposed_in_order() -> None:
    dialog = _dialog([("Note A — context", ("a.md", 0)), ("Note B — context", ("b.md", 12))])
    assert dialog.labels == ["Note A — context", "Note B — context"]


def test_activate_index_hands_payload_to_callback() -> None:
    got: list[object] = []
    dialog = _dialog([("A", ("a.md", 5)), ("B", ("b.md", 9))], on_activate=got.append)
    assert dialog.activate_index(1) is True
    assert got == [("b.md", 9)]


def test_activate_out_of_range_is_false_and_silent() -> None:
    got: list[object] = []
    dialog = _dialog([("A", 1)], on_activate=got.append)
    assert dialog.activate_index(5) is False
    assert dialog.activate_index(-1) is False
    assert got == []
