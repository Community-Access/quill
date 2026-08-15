"""The Libraries Hub window: one row per book, and honest buttons.

Two failures this pins, both of which are invisible on screen and obvious in
speech: four rows for one book, and a Download button that can be pressed on a
catalog record and then explains it cannot download.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.library.model import Book  # noqa: E402
from quill.ui.library_dialog import LibraryDialog  # noqa: E402

_BOOKS = [
    Book(
        book_id="pg",
        title="Middlemarch: A Study of Provincial Life",
        authors=("Eliot, George",),
        source="gutenberg",
        formats={"txt": "u", "epub": "u"},
    ),
    Book(
        book_id="se",
        title="Middlemarch",
        authors=("George Eliot",),
        source="standard-ebooks",
        formats={"epub": "u"},
    ),
    Book(
        book_id="lv",
        title="Middlemarch",
        authors=("George Eliot",),
        source="librivox",
        formats={"audio": "u"},
    ),
    Book(
        book_id="bard",
        title="Adam Bede",
        authors=("George Eliot",),
        source="bard",
        site_url="https://hdl.loc.gov/example",
    ),
]


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _search(tmp_path, said, books=None):
    frame = wx.Frame(None)
    dialog = LibraryDialog(
        frame,
        dest_dir=tmp_path / "books",
        data_dir=tmp_path,
        search_fn=lambda _q, **_k: list(_BOOKS if books is None else books),
        announce=said.append,
    )
    dialog.query.SetValue("eliot")
    dialog._on_search(None)
    return frame, dialog


def test_one_book_in_three_libraries_is_one_row(wx_app, tmp_path) -> None:
    said: list[str] = []
    frame, dialog = _search(tmp_path, said)
    try:
        assert dialog.results.GetCount() == 2
        first = dialog.results.GetString(0)
        assert first.startswith("Middlemarch, by ")
        assert "read or listen" in first
        assert "open now" in first
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_every_edition_stays_reachable(wx_app, tmp_path) -> None:
    # Grouping the row must not take away "which edition" -- a proofread text is
    # not a raw scan, and that is a real question.
    said: list[str] = []
    frame, dialog = _search(tmp_path, said)
    try:
        editions = [
            dialog.edition_choice.GetString(i) for i in range(dialog.edition_choice.GetCount())
        ]
        assert editions == ["Project Gutenberg", "Standard Ebooks", "LibriVox"]
        # Lands on the recommended edition rather than whichever arrived first.
        assert dialog.edition_choice.GetStringSelection() == "Standard Ebooks"
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_download_is_disabled_on_a_record_QUILL_cannot_open(wx_app, tmp_path) -> None:
    said: list[str] = []
    frame, dialog = _search(tmp_path, said)
    try:
        assert dialog.dl_btn.IsEnabled() is True  # the grouped, openable work
        dialog.results.SetSelection(1)  # the BARD record
        dialog._on_result_selected()
        assert dialog.dl_btn.IsEnabled() is False
        assert dialog.bard_btn.IsEnabled() is True
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_pressing_download_anyway_explains_rather_than_failing(wx_app, tmp_path) -> None:
    said: list[str] = []
    frame, dialog = _search(tmp_path, said)
    try:
        dialog.results.SetSelection(1)
        dialog._on_result_selected()
        dialog._download(open_after=False)
        assert "account" in said[-1].lower()
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_the_status_counts_by_what_can_be_done(wx_app, tmp_path) -> None:
    said: list[str] = []
    frame, dialog = _search(tmp_path, said)
    try:
        assert "2 books found" in said[-1]
        assert "1 you can open here" in said[-1]
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_the_filter_never_re_searches(wx_app, tmp_path) -> None:
    said: list[str] = []
    frame = wx.Frame(None)
    searches: list[str] = []

    def _search_fn(query, **_kwargs):
        searches.append(query)
        return list(_BOOKS)

    dialog = LibraryDialog(
        frame,
        dest_dir=tmp_path / "books",
        data_dir=tmp_path,
        search_fn=_search_fn,
        announce=said.append,
    )
    try:
        dialog.query.SetValue("eliot")
        dialog._on_search(None)
        assert len(searches) == 1
        dialog.filter_choice.SetSelection(3)  # only recordings
        dialog._apply_filter()
        assert len(searches) == 1  # the answer was already in hand
        assert dialog.results.GetCount() == 1
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_a_filter_that_hides_everything_says_so(wx_app, tmp_path) -> None:
    # An empty list and a failed search sound identical, and they are not the
    # same thing.
    said: list[str] = []
    frame, dialog = _search(tmp_path, said, books=[_BOOKS[3]])
    try:
        dialog.filter_choice.SetSelection(1)  # only what QUILL can open
        dialog._apply_filter()
        assert "match that filter" in said[-1]
        assert "Everything found" in said[-1]
    finally:
        dialog.Destroy()
        frame.Destroy()
