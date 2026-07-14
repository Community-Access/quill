"""Alt+1..Alt+0 jump-to-document switching."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.main_frame import MainFrame


class _Stub:
    go_to_document = MainFrame.go_to_document

    def __init__(self, tab_count: int) -> None:
        self._document_tabs = list(range(tab_count))
        self.document = SimpleNamespace(name="Notes")
        self.selected: int | None = None
        self.status: str | None = None

    def _select_tab(self, index: int) -> None:
        self.selected = index

    def _set_status(self, message: str) -> None:
        self.status = message


def test_switch_to_open_document() -> None:
    stub = _Stub(3)
    stub.go_to_document(2)
    assert stub.selected == 1  # 1-based position -> 0-based index
    assert stub.status == "Switched to Notes"


def test_alt_zero_targets_tenth_document() -> None:
    stub = _Stub(10)
    stub.go_to_document(10)
    assert stub.selected == 9


def test_out_of_range_announces_without_switching() -> None:
    stub = _Stub(2)
    stub.go_to_document(5)
    assert stub.selected is None
    assert stub.status == "No document 5 open"


def test_default_keymap_binds_alt_digits() -> None:
    for position in range(1, 10):
        assert DEFAULT_KEYMAP[f"window.go_to_document_{position}"] == f"Alt+{position}"
    # The tenth document is Alt+0.
    assert DEFAULT_KEYMAP["window.go_to_document_10"] == "Alt+0"


def test_alt_digit_bindings_are_unique() -> None:
    digit_bindings = [b for b in DEFAULT_KEYMAP.values() if b in {f"Alt+{n}" for n in range(10)}]
    assert len(digit_bindings) == len(set(digit_bindings)) == 10
