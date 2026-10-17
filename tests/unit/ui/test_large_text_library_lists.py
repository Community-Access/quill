"""Large snippet and abbreviation libraries open and filter quickly (2026-10-16).

Measured first (``scripts/bench_editor_completion.py lists``): loading ten
thousand snippets took 25 ms and filtering them 6.5 ms a key, but putting the
matches into the list took 2.2 to 3 seconds -- on opening, and again after
every key. The Abbreviations manager's report list took 3.7 seconds a refill.
The windows here are built in memory and never shown.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
import wx

from quill.core.abbreviations import Abbreviation, AbbreviationLibrary
from quill.ui.searchable_picker import SHOWN_LIMIT, choose_searchable_option, match_status
from tests.wx_session import shared_wx_app


@pytest.fixture
def app() -> Iterator[wx.App]:
    application = shared_wx_app()
    yield application
    application.Destroy()


def _picker_rows(app: wx.App, labels: list[str], query: str = "") -> dict[str, Any]:
    """Open the picker on *labels*, record what it shows, and cancel."""
    seen: dict[str, Any] = {}
    frame = wx.Frame(None)

    def _show(dialog: wx.Dialog, _label: str) -> int:
        results = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        status = [c for c in dialog.GetChildren() if isinstance(c, wx.StaticText)][-1]
        seen["rows"] = results.GetCount()
        seen["status"] = status.GetLabel()
        seen["selected"] = results.GetSelection()
        seen["name"] = results.GetName()
        return wx.ID_CANCEL

    remembered = {"Insert Snippet": query} if query else {}
    try:
        answer = choose_searchable_option(
            wx,
            frame,
            _show,
            remembered,
            title="Insert Snippet",
            prompt="Type to filter snippets",
            dialog_label="Insert Snippet",
            initial_choices=labels,
            search_callback=lambda q: [label for label in labels if q.lower() in label.lower()],
        )
    finally:
        frame.Destroy()
    seen["answer"] = answer
    return seen


def test_a_large_library_shows_a_window_of_rows_and_says_so(app: wx.App) -> None:
    labels = [f"Meeting notes {index}" for index in range(SHOWN_LIMIT * 5)]
    seen = _picker_rows(app, labels)
    assert seen["rows"] == SHOWN_LIMIT
    assert seen["status"].startswith(f"{len(labels)} matches; showing the first {SHOWN_LIMIT}.")
    assert "Type more to narrow them" in seen["status"]
    assert seen["selected"] == 0 and seen["answer"] is None
    # Said where the reader looks on arriving in the list, not only above it.
    assert seen["name"] == f"Insert Snippet, first {SHOWN_LIMIT} of {len(labels)} matches"


def test_a_small_library_shows_everything_as_before(app: wx.App) -> None:
    labels = ["Address", "Meeting notes", "Signature"]
    seen = _picker_rows(app, labels)
    assert seen["rows"] == 3
    assert seen["status"] == "3 match(es). Top match: Address"


def test_the_remembered_search_with_a_space_is_applied(app: wx.App) -> None:
    labels = ["Meeting agenda", "Meeting notes", "Notes"]
    seen = _picker_rows(app, labels, query="meeting notes")
    assert seen["rows"] == 1
    assert seen["status"] == "1 match(es). Top match: Meeting notes"


def test_the_status_sentences() -> None:
    assert match_status([], 0, ("email", "bug")) == "No matching options. Try: email, bug"
    assert match_status([], 0) == "No matching options"
    assert match_status(["a", "b"], 2) == "2 match(es). Top match: a"


def _library(count: int) -> AbbreviationLibrary:
    return AbbreviationLibrary(
        version=2,
        abbreviations=[
            Abbreviation(
                id=f"a{index}",
                abbreviation=f"abbr{index}",
                expansion=f"Expansion {index} about the meeting notes",
                category="Work" if index % 2 else "",
            )
            for index in range(count)
        ],
    )


def test_the_abbreviations_list_is_virtual_and_keeps_its_selection_by_identity(
    app: wx.App,
) -> None:
    from quill.ui.abbreviation_manager_dialog import AbbreviationManagerDialog

    frame = wx.Frame(None)
    try:
        manager = AbbreviationManagerDialog(frame, _library(5000))
        listing = manager._list
        assert listing.HasFlag(wx.LC_VIRTUAL)
        assert listing.GetItemCount() == 5000
        assert listing.GetItemText(4999, 0) == "abbr4999"
        # Select abbr42, then search for something it still matches.
        listing.Select(42)
        manager._search_ctrl.SetValue("abbr42")
        manager._on_search(None)
        shown = [listing.GetItemText(i, 0) for i in range(listing.GetItemCount())]
        assert "abbr42" in shown
        assert manager._selected_abbreviation().abbreviation == "abbr42", (
            "the same abbreviation, not whatever slid into row 42"
        )
        # Words in any order.
        manager._search_ctrl.SetValue("notes meeting expansion 7")
        manager._on_search(None)
        assert listing.GetItemCount() >= 1
        manager.close()
    finally:
        frame.Destroy()
