"""Headless smoke test of the accessible Book Library dialog."""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.library.model import Book  # noqa: E402


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def test_search_download_and_open(app, tmp_path):
    from quill.ui.library_dialog import LibraryDialog

    books = [
        Book(
            book_id="gutenberg:1",
            title="Pride and Prejudice",
            authors=("Jane Austen",),
            source="gutenberg",
            formats={"txt": "https://x/1.txt", "epub": "https://x/1.epub"},
        )
    ]
    said: list[str] = []
    opened: list[Path] = []

    def fake_search(query, *, sources, safe_mode=False):
        assert query == "pride"
        return books

    def fake_download(book, dest_dir, fmt="", *, safe_mode=False):
        path = Path(dest_dir) / "book.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"BODY")
        return path

    dlg = LibraryDialog(
        None,
        dest_dir=tmp_path,
        search_fn=fake_search,
        download_fn=fake_download,
        announce=said.append,
        on_open=opened.append,
    )
    try:
        dlg.query.SetValue("pride")
        dlg._on_search(None)
        assert dlg.results.GetCount() == 1
        assert "Pride and Prejudice" in dlg.results.GetString(0)
        assert any("Found 1" in s for s in said)

        dlg.results.SetSelection(0)
        dlg._download(open_after=True)
        assert opened and opened[0].read_bytes() == b"BODY"
        assert any("Saved" in s for s in said)
    finally:
        dlg.Destroy()


def test_find_within_results(app, tmp_path):
    from quill.ui.library_dialog import LibraryDialog

    books = [
        Book(book_id="1", title="The Odyssey", authors=("Homer",), formats={"txt": "https://x/1"}),
        Book(book_id="2", title="Moby-Dick", authors=("Melville",), formats={"txt": "https://x/2"}),
        Book(
            book_id="3", title="Moby Dick Notes", authors=("Ed.",), formats={"txt": "https://x/3"}
        ),
    ]
    said: list[str] = []
    dlg = LibraryDialog(
        None,
        dest_dir=tmp_path,
        search_fn=lambda q, **k: books,
        download_fn=lambda b, d, **k: Path(d) / "x",
        announce=said.append,
    )
    try:
        dlg.query.SetValue("x")
        dlg._on_search(None)
        assert dlg.results.GetCount() == 3

        dlg.results.SetSelection(0)
        dlg.find.SetValue("moby")
        assert dlg._find_in_results(1) == 1  # first "Moby" after row 0
        assert dlg._find_in_results(1) == 2  # next match
        assert dlg._find_in_results(1) == 1  # wraps back around

        # Backward search from the current selection (row 1) wraps to row 2.
        assert dlg._find_in_results(-1) == 2

        dlg.find.SetValue("nonexistent")
        assert dlg._find_in_results(1) == -1
        assert any("not found" in s.lower() for s in said)
    finally:
        dlg.Destroy()


def test_new_sources_offered(app, tmp_path):
    from quill.ui.library_dialog import LibraryDialog

    dlg = LibraryDialog(
        None,
        dest_dir=tmp_path,
        search_fn=lambda q, **k: [],
        download_fn=lambda b, d, **k: Path(d) / "x",
        announce=lambda _t: None,
    )
    try:
        labels = [dlg.source.GetString(i) for i in range(dlg.source.GetCount())]
        assert any("All free sources" in s for s in labels)
        assert any("Google Books" in s for s in labels)
        assert any("NLS BARD" in s for s in labels)
        assert any("Feedbooks" in s for s in labels)
    finally:
        dlg.Destroy()


def test_open_in_bard_opens_site_url(app, tmp_path, monkeypatch):
    from quill.ui import library_dialog
    from quill.ui.library_dialog import LibraryDialog

    opened: list[str] = []
    monkeypatch.setattr(library_dialog.webbrowser, "open", opened.append)

    book = Book(
        book_id="bard:DB55555",
        title="Sunset pass",
        authors=("Grey, Zane",),
        source="bard",
        site_url="http://hdl.loc.gov/loc.nls/db.55555",
    )
    said: list[str] = []
    dlg = LibraryDialog(
        None,
        dest_dir=tmp_path,
        search_fn=lambda q, **k: [book],
        download_fn=lambda b, d, **k: Path(d) / "x",
        announce=said.append,
    )
    try:
        dlg.query.SetValue("sunset")
        dlg._on_search(None)
        # A metadata-only BARD result is tagged for the "Open in BARD" action.
        assert "open in BARD" in dlg.results.GetString(0)
        dlg.results.SetSelection(0)
        dlg._open_in_bard()
        assert opened == ["http://hdl.loc.gov/loc.nls/db.55555"]
        assert any("Sign in on the BARD site" in s for s in said)
    finally:
        dlg.Destroy()


def test_format_chooser_populates_and_downloads_chosen_format(app, tmp_path):
    from quill.ui.library_dialog import LibraryDialog

    book = Book(
        book_id="1",
        title="Frankenstein",
        authors=("Mary Shelley",),
        formats={"txt": "https://x/1.txt", "epub": "https://x/1.epub"},
    )
    picked: dict = {}

    def fake_download(b, dest_dir, fmt="", *, safe_mode=False):
        picked["fmt"] = fmt
        return Path(dest_dir) / "b"

    dlg = LibraryDialog(
        None,
        dest_dir=tmp_path,
        search_fn=lambda q, **k: [book],
        download_fn=fake_download,
        announce=lambda _t: None,
    )
    try:
        dlg.query.SetValue("frank")
        dlg._on_search(None)
        # Chooser is filled from the book's formats, best (txt) preselected.
        choices = [dlg.format_choice.GetString(i) for i in range(dlg.format_choice.GetCount())]
        assert set(choices) == {"txt", "epub"}
        assert dlg.format_choice.GetStringSelection() == "txt"

        # Pick EPUB explicitly; download passes that format through.
        dlg.format_choice.SetStringSelection("epub")
        dlg.results.SetSelection(0)
        dlg._download(open_after=False)
        assert picked["fmt"] == "epub"
    finally:
        dlg.Destroy()


def test_empty_query_is_announced(app, tmp_path):
    from quill.ui.library_dialog import LibraryDialog

    said: list[str] = []
    dlg = LibraryDialog(
        None,
        dest_dir=tmp_path,
        search_fn=lambda q, **k: [],
        download_fn=lambda b, d, **k: Path(d) / "x",
        announce=said.append,
    )
    try:
        dlg._on_search(None)  # empty query
        assert any("search for first" in s.lower() for s in said)
        # Download with no selection is announced, not a crash.
        dlg._download(open_after=False)
        assert any("choose a book" in s.lower() for s in said)
    finally:
        dlg.Destroy()
