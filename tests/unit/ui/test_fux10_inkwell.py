"""FUX-10 in Quill Inkwell: F1 on a disabled abbreviation says why it will not expand."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.apps import inkwell_row_help
from quill.ui import app_context_help


def _host(enabled: list[bool], selected: int) -> Any:
    return SimpleNamespace(
        _list=SimpleNamespace(GetFirstSelected=lambda: selected),
        _library=SimpleNamespace(
            abbreviations=[
                SimpleNamespace(
                    enabled=flag, abbreviation="brb", expansion="be right back", category=""
                )
                for flag in enabled
            ]
        ),
    )


def test_f1_on_a_disabled_entry_says_it_will_not_expand_and_where_to_turn_it_on() -> None:
    host = _host([True, False], 1)
    inkwell_row_help.install(host)
    assert app_context_help.selection_help_of(host._list) == (
        "This abbreviation is disabled, so typing it does not expand it. To turn it "
        "back on, press Ctrl+M for Manage Abbreviations, select it, and press "
        "Enable/Disable (Alt+B), or check Enabled in its Edit dialog."
    )


def test_f1_on_an_entry_that_is_on_adds_nothing() -> None:
    assert inkwell_row_help.describe_selected_row(_host([True, False], 0)) == ""
    assert inkwell_row_help.describe_selected_row(_host([], -1)) == ""


def test_the_list_gets_its_f1_paragraph_when_it_is_filled() -> None:
    from quill.apps.inkwell import QuillInkwellFrame

    calls: list[str] = []
    host = _host([False], 0)
    host._list.DeleteAllItems = lambda: calls.append("cleared")
    host._list.InsertItem = lambda _i, label: calls.append(label)
    host._list.SetItem = lambda *_a: None
    QuillInkwellFrame._reload_list(host)
    assert calls == ["cleared", "brb (disabled)"]
    assert app_context_help.selection_help_of(host._list) == inkwell_row_help.DISABLED
