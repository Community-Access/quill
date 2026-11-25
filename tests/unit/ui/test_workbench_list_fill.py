"""Every Workbench list changes row by row around the reader (FUX-06)."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from quill.core.workbench.list_place import row_identities
from quill.ui.workbench_list_fill import fill_rows
from tests.unit.ui.report_list_fake import WX, FakeReportList


@dataclass
class _Row:
    url: str
    title: str


def _frame(rows: list[_Row]) -> SimpleNamespace:
    control = FakeReportList()
    frame = SimpleNamespace(list=control, rows=[], _shown_cells=[], _wx=WX)
    _fill(frame, rows, landing=0)
    return frame


def _fill(frame: SimpleNamespace, rows: list[_Row], *, landing: int, ours: bool = False) -> str:
    return fill_rows(frame, rows, [[r.title, r.url] for r in rows], landing, ours=ours)


def test_a_refill_keeps_the_readers_row_as_the_same_item_on_its_line() -> None:
    a, b, c = _Row("u/a", "A"), _Row("u/b", "B"), _Row("u/c", "C")
    frame = _frame([a, b, c])
    frame.list.Select(0, on=False)
    frame.list.Select(1)
    frame.list.Focus(1)
    item = frame.list.item(1)
    frame.list.events.clear()
    gone = _fill(frame, [_Row("u/new", "New"), a, b, c], landing=2)
    assert frame.list.selected_rows() == [2]
    assert frame.list.item(2) == item, "the reader's row is the same native row"
    assert frame.list.events == [], "nothing for the screen reader to read again"
    assert frame.list.delete_all == 0, "the list is never cleared"
    assert gone == ""


def test_the_watches_poll_does_not_rewrite_the_readers_row() -> None:
    first = [_Row("u/runs", "CI, checked just now"), _Row("u/runs", "Deploy, checked just now")]
    frame = _frame(first)
    frame.list.Select(0, on=False)
    frame.list.Select(1)
    frame.list.Focus(1)
    later = [
        _Row("u/runs", "CI, checked 1 minute ago"),
        _Row("u/runs", "Deploy, checked 1 minute ago"),
    ]
    _fill(frame, later, landing=1)
    assert frame.list.text(0) == "CI, checked 1 minute ago"
    assert frame.list.text(1) == "Deploy, checked just now", "the reader's row is left alone"
    _fill(frame, later, landing=1, ours=True)
    assert frame.list.text(1) == "Deploy, checked 1 minute ago"


def test_a_shift_selection_survives_and_a_gone_row_is_reported() -> None:
    a, b, c, d = (_Row(f"u/{n}", n) for n in "ABCD")
    frame = _frame([a, b, c, d])
    frame.list.Select(0, on=False)
    frame.list.Select(1)
    frame.list.Select(2)
    frame.list.Focus(2)
    _fill(frame, [a, b, c, d, _Row("u/E", "E")], landing=2)
    assert frame.list.selected_rows() == [1, 2]
    gone = _fill(frame, [a, b, d], landing=2)
    assert gone == "C"
    assert frame.list.focused_row() == 2 and frame.list.text(2) == "D"


def test_repeated_identities_are_numbered() -> None:
    rows = [_Row("u/runs", "CI"), _Row("u/runs", "Deploy"), _Row("u/x", "X")]
    assert row_identities(rows) == ["_Row:url:u/runs", "_Row:url:u/runs#1", "_Row:url:u/x"]


def test_a_row_that_names_its_site_is_that_sites_item() -> None:
    from quill.core.workbench.list_place import row_identity

    one = SimpleNamespace(site="Shop", key="7")
    two = SimpleNamespace(site="Blog", key="7")
    assert row_identity(one) != row_identity(two)
