"""LibriVox's second route, and why the branch is not a duplicate.

LibriVox and the Internet Archive look like two sources for the same
audiobooks. They are one library with two doors: librivox.org holds the
catalogue, the Archive holds the recordings. When the catalogue door was shut
(Cloudflare 522, 2026-08-16) the branch was dead even though every book was
reachable. These tests pin the fallback and its honesty.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio import browse_librivox as blv
from quill.core.radio import browse_sources as bs
from quill.core.radio import internet_archive, librivox_archive


@dataclass
class _Item:
    identifier: str
    title: str


def test_the_collection_is_the_one_librivox_actually_publishes_to() -> None:
    assert librivox_archive.COLLECTION == "collection:librivoxaudio"


def test_recently_added_asks_for_newest_first() -> None:
    # Sorted by identifier -- the Archive default -- "Recently Added" would be
    # alphabetical, which is not what the folder says it is.
    seen: dict = {}

    def fake(query, *, limit=40, sort="identifier asc", safe_mode=False):
        seen.update(query=query, sort=sort)
        return []

    original = internet_archive.search
    internet_archive.search = fake  # type: ignore[assignment]
    try:
        librivox_archive.recent()
    finally:
        internet_archive.search = original  # type: ignore[assignment]
    assert seen["sort"] == "addeddate desc"
    assert seen["query"] == librivox_archive.COLLECTION


def test_a_genre_is_scoped_to_librivox_and_not_the_whole_archive() -> None:
    seen: dict = {}

    def fake(query, *, limit=40, sort="identifier asc", safe_mode=False):
        seen["query"] = query
        return []

    original = internet_archive.search
    internet_archive.search = fake  # type: ignore[assignment]
    try:
        librivox_archive.by_genre("Science Fiction")
        assert seen["query"].startswith(librivox_archive.COLLECTION)
        assert 'subject:"Science Fiction"' in seen["query"]
        librivox_archive.by_author("Mark Twain")
        assert 'creator:"Mark Twain"' in seen["query"]
    finally:
        internet_archive.search = original  # type: ignore[assignment]


def test_a_quote_in_a_name_cannot_end_the_query_early() -> None:
    # Genre and author reach here as text; an unescaped quote would turn the
    # rest of the name into query syntax.
    seen: dict = {}

    def fake(query, *, limit=40, sort="identifier asc", safe_mode=False):
        seen["query"] = query
        return []

    original = internet_archive.search
    internet_archive.search = fake  # type: ignore[assignment]
    try:
        librivox_archive.by_author('Twain" OR mediatype:texts')
    finally:
        internet_archive.search = original  # type: ignore[assignment]
    assert seen["query"].count('"') == 2, seen["query"]


def test_an_empty_genre_asks_nothing_at_all() -> None:
    assert librivox_archive.by_genre("  ") == []
    assert librivox_archive.by_author("") == []


# --- the branch itself ---------------------------------------------------------


def _no_librivox(monkeypatch) -> None:
    from quill.core.media import librivox

    def down(*_a, **_k):
        raise OSError("librivox.org is behind a 522")

    monkeypatch.setattr(librivox, "recent_books", down)
    monkeypatch.setattr(librivox, "books_by_genre", down)
    monkeypatch.setattr(librivox, "books_by_author", down)


def test_recently_added_still_lists_books_when_librivox_is_down(monkeypatch) -> None:
    _no_librivox(monkeypatch)
    monkeypatch.setattr(
        librivox_archive, "recent", lambda **_k: [_Item("sense_librivox", "Sense and Sensibility")]
    )
    nodes = bs.browse("librivoxrecent")
    assert [n.label for n in nodes] == ["Sense and Sensibility"]
    # Opened as an Archive item, because that is what it is.
    assert nodes[0].node_id == "archiveitem:sense_librivox"


def test_a_fallback_row_says_where_it_came_from(monkeypatch) -> None:
    # The reader credits and section list are missing on this route; saying so
    # beats letting it look like a thinner LibriVox.
    _no_librivox(monkeypatch)
    monkeypatch.setattr(librivox_archive, "recent", lambda **_k: [_Item("x_librivox", "A Book")])
    assert bs.browse("librivoxrecent")[0].note == librivox_archive.VIA_ARCHIVE_NOTE


def test_librivox_is_still_preferred_when_it_answers(monkeypatch) -> None:
    # The fallback is a fallback: the catalogue is richer when it is up.
    from quill.core.media import librivox

    called = []
    monkeypatch.setattr(librivox_archive, "recent", lambda **_k: called.append("archive") or [])

    class _Book:
        has_audio = True
        title = "From LibriVox"
        book_id = "lv1"
        sections: list = []

    monkeypatch.setattr(librivox, "recent_books", lambda *_a, **_k: [_Book()])
    monkeypatch.setattr(
        blv, "_librivox_book_nodes", lambda books: [blv.folder("x", b.title) for b in books]
    )
    assert [n.label for n in bs.browse("librivoxrecent")] == ["From LibriVox"]
    assert called == [], "the Archive was queried even though LibriVox answered"


def test_both_routes_down_says_unreachable_rather_than_empty(monkeypatch) -> None:
    # The distinction the whole branch is built on. Swallowing the second
    # failure reported "this folder is empty" during an outage of both
    # upstreams -- found by sweeping every provider on a day the Archive's
    # search backend happened to be down too.
    from quill.core.radio import browse_failure

    _no_librivox(monkeypatch)

    def also_down(**_k):
        raise OSError("the Archive is down too")

    monkeypatch.setattr(librivox_archive, "recent", also_down)
    assert bs.browse("librivoxrecent") == []
    assert browse_failure.last_error_was_network()


def test_a_genuinely_empty_genre_is_still_empty(monkeypatch) -> None:
    # LibriVox replied and had nothing: that is empty, and must not be
    # reported as an outage.
    from quill.core.media import librivox
    from quill.core.radio import browse_failure

    monkeypatch.setattr(librivox, "books_by_genre", lambda *_a, **_k: [])
    monkeypatch.setattr(librivox_archive, "by_genre", lambda *_a, **_k: [])
    assert bs.browse(bs.make_id("librivoxgenres", "Sudoku")) == []
    assert not browse_failure.last_error_was_network()
