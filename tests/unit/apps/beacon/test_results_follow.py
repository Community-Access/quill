"""Beacon's results stay still while they refill (FUX-06).

The results list is virtual: it remembers row numbers, not beacons. A capture
or a sync used to leave the selection on the old number -- somebody else's
beacon now -- and show the details of row 0, and every refill said the count.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import wx

from quill.apps.beacon import results_follow
from tests.unit.ui.report_list_fake import FakeReportList


class _Virtual(FakeReportList):
    """A virtual list: a count, and selection kept by row number."""

    def SetItemCount(self, count: int) -> None:  # noqa: N802
        while len(self.rows) < count:
            self.InsertItem(len(self.rows), "")
        while len(self.rows) > count:
            self.DeleteItem(len(self.rows) - 1)

    def RefreshItems(self, _first: int, _last: int) -> None:  # noqa: N802
        pass


def _b(beacon_id: str, title: str = "") -> Any:
    return SimpleNamespace(beacon_id=beacon_id, title=title or beacon_id)


def _frame(monkeypatch) -> Any:
    said: list[str] = []
    details: list[str] = []
    frame = SimpleNamespace(
        results=_Virtual(),
        _results_cache=[],
        announcer=SimpleNamespace(
            say=lambda text, *_a, **_k: said.append(text),
            announce_count=lambda n, filtered=False: said.append(f"{n} results"),
        ),
        _show_details=lambda b: details.append(b.beacon_id),
        said=said,
        details=details,
    )
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    monkeypatch.setattr(wx, "GetTopLevelParent", lambda _c: SimpleNamespace(IsActive=lambda: True))
    return frame


def test_a_capture_above_keeps_the_reader_on_their_beacon_and_says_nothing(monkeypatch) -> None:
    frame = _frame(monkeypatch)
    results_follow.show(frame, [_b("a"), _b("b"), _b("c")], say_count=True, filtered=False)
    frame.results.Select(1)
    frame.results.Focus(1)
    frame.said.clear()
    frame.details.clear()
    results_follow.show(
        frame, [_b("new"), _b("a"), _b("b"), _b("c")], say_count=False, filtered=False
    )
    # Before FUX-06 the selection stayed on row 1, now "a", and the details said "new".
    assert frame.results.selected_rows() == [2]
    assert frame.details == ["b"]
    assert frame.said == []


def test_a_beacon_a_sync_took_away_is_said_once_and_its_neighbour_chosen(monkeypatch) -> None:
    frame = _frame(monkeypatch)
    results_follow.show(
        frame, [_b("a"), _b("b", "Recipes"), _b("c")], say_count=False, filtered=False
    )
    frame.results.Select(1)
    frame.results.Focus(1)
    frame.results.events.clear()
    gone = results_follow.show(frame, [_b("a"), _b("c")], say_count=False, filtered=False)
    assert frame.results.selected_rows() == [1]
    assert frame.details[-1] == "c"
    # The row number did not change, so the focus is set again: the screen
    # reader and the braille display read the beacon that is there now.
    assert ("focused", 1) in frame.results.events
    assert gone == "Recipes is no longer in the list."
    results_follow.say_with(frame, "Synced. Pushed 0, pulled 1.", gone)
    assert frame.said == ["Synced. Pushed 0, pulled 1. Recipes is no longer in the list."]


def test_a_new_search_without_the_readers_beacon_starts_at_the_top(monkeypatch) -> None:
    frame = _frame(monkeypatch)
    results_follow.show(frame, [_b("a"), _b("b"), _b("c")], say_count=True, filtered=False)
    frame.results.Select(2)
    results_follow.show(frame, [_b("x"), _b("y"), _b("z")], say_count=True, filtered=True)
    assert frame.results.selected_rows() == [0]
