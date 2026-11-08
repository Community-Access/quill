"""The Problems pane widget (quill.ui.problems_pane), on a real wx panel.

What is locked in: the list fills from a report in report order, the filter
row narrows it and says the new count once, Enter and the context menu reach
Go To, Escape goes back to the editor, and nothing in the pane changes text.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.problems.model import CheckReport, Problem
from quill.ui.problems_pane import NOT_CHECKED_ROW, ProblemsPane

wx = pytest.importorskip("wx")

REPORT = CheckReport(
    language="json",
    problems=(
        Problem(1, 1, "error", "Expecting value", "JSON"),
        Problem(4, 2, "warning", "Trailing comma", "JSON"),
        Problem(7, 3, "info", "Long line", "ruff"),
    ),
    checked_with=("JSON", "ruff"),
)


class _Event:
    def __init__(self, key: int) -> None:
        self.key, self.skipped = key, False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx spelling
        return self.key

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


@pytest.fixture
def pane(wx_session_app: Any):
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # without one, SetHelpText stores nothing
    frame = wx.Frame(None)
    record: dict[str, list[Any]] = {"go": [], "back": [], "copy": [], "say": []}
    widget = ProblemsPane(
        wx,
        frame,
        go_to=record["go"].append,
        back_to_editor=lambda: record["back"].append(True),
        copy_text=record["copy"].append,
        say=record["say"].append,
    )
    widget.record = record  # type: ignore[attr-defined]
    yield widget
    frame.Destroy()


def _rows(pane: ProblemsPane) -> list[str]:
    return list(pane._list.GetStrings())


def test_an_unchecked_pane_says_so_rather_than_being_empty(pane) -> None:
    assert _rows(pane) == [NOT_CHECKED_ROW]
    pane.go_to_selected()
    assert pane.record["go"] == []


def test_a_report_fills_rows_severity_first(pane) -> None:
    pane.show_report(REPORT)
    assert _rows(pane)[0] == "Error, line 1, column 1: Expecting value (JSON)"
    assert len(_rows(pane)) == 3
    assert pane.count_sentence() == "3 problems"


def test_errors_only_filters_and_says_the_count_once(pane) -> None:
    pane.show_report(REPORT)
    pane._show.SetSelection(2)
    pane._on_filter(None)
    assert _rows(pane) == ["Error, line 1, column 1: Expecting value (JSON)"]
    assert pane.record["say"] == ["3 problems, 1 shown"]


def test_source_filter_keeps_report_indices_for_go_to(pane) -> None:
    pane.show_report(REPORT)
    pane._source.SetSelection(pane._source.FindString("ruff"))
    pane._on_filter(None)
    assert len(_rows(pane)) == 1
    pane._list.SetSelection(0)
    pane.go_to_selected()
    assert pane.record["go"] == [2]


def test_a_filter_that_hides_everything_shows_the_count_row(pane) -> None:
    clean = CheckReport(
        language="json", problems=(Problem(2, 1, "info", "x", "ruff"),), checked_with=("ruff",)
    )
    pane.show_report(clean)
    pane._show.SetSelection(2)
    pane._on_filter(None)
    assert _rows(pane) == ["1 problem, 0 shown."]
    pane.go_to_selected()
    assert pane.record["go"] == []


def test_no_checker_says_so_not_no_problems(pane) -> None:
    pane.show_report(CheckReport(language="Go"))
    assert _rows(pane) == ["No checker for Go."]


def test_refilling_keeps_the_selected_problem(pane) -> None:
    pane.show_report(REPORT)
    pane._list.SetSelection(2)
    pane.show_report(REPORT)
    assert pane._list.GetSelection() == 2


def test_escape_goes_back_to_the_editor_and_enter_goes_to(pane, monkeypatch) -> None:
    pane.show_report(REPORT)
    pane._on_char_hook(_Event(wx.WXK_ESCAPE))
    assert pane.record["back"] == [True]
    monkeypatch.setattr(pane._list, "HasFocus", lambda: True)
    pane._list.SetSelection(1)
    pane._on_char_hook(_Event(wx.WXK_RETURN))
    assert pane.record["go"] == [1]
    other = _Event(ord("A"))
    pane._on_char_hook(other)
    assert other.skipped


def test_copy_message_copies_and_says_so(pane) -> None:
    pane.show_report(REPORT)
    pane._list.SetSelection(1)
    pane._copy_selected()
    assert pane.record["copy"] == ["Trailing comma"]
    assert pane.record["say"] == ["Message copied"]


def test_every_control_has_inline_help(pane) -> None:
    for control in (pane.panel, pane._show, pane._source, pane._list):
        assert control.GetHelpText()
