"""LibriVox browsing, and its second route through the Internet Archive.

Extracted from ``browse_sources`` at its GATE-11 ceiling, which had already
named this split: "the spoken-word sources would move cleanly to a separate
module behind the same dispatch". LibriVox went first because it grew the
fallback -- see :mod:`quill.core.radio.librivox_archive` for why a catalogue
and a warehouse are not two sources for the same thing.

Registered in ``browse_sources._HANDLERS`` like every other source; this module
adds no dispatch of its own.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.browse_helpers import letter_groups
from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id
from quill.core.radio.models import RadioStation


def refuse_when_offline(safe_mode: bool) -> None:
    """Refuse LibriVox in Safe Mode.

    LibriVox reaches the network through the shared library egress chokepoint,
    which carries no Safe Mode flag of its own, so the refusal is made here --
    with LibriVox's own coded error rather than a bare RuntimeError, so it is
    auditable like every other source's.
    """
    if safe_mode:
        from quill.core.media.librivox import LibriVoxError

        raise LibriVoxError(
            "LibriVox is disabled in Safe Mode. Restart QUILL normally to browse it."
        )


def _librivox_book_nodes(books: list) -> list[BrowseNode]:
    """A book is a folder of sections; a single-section book is just playable."""
    nodes: list[BrowseNode] = []
    for book in books:
        if not book.has_audio:
            continue
        if len(book.sections) == 1:
            section = book.sections[0]
            nodes.append(
                leaf(
                    RadioStation(
                        name=book.title,
                        stream_url=section.url,
                        source="LibriVox",
                        is_recording=True,
                    ),
                    note=book.authors,
                )
            )
            continue
        nodes.append(
            folder(
                make_id("librivoxbook", book.book_id),
                book.title,
                note=book.authors,
                child_count=len(book.sections),
            )
        )
    return nodes


#: Books are fetched by axis and cached in-process for the session, so opening a
#: book's sections does not re-query the whole genre. Keyed by book id.
_LIBRIVOX_BOOKS: dict[str, Any] = {}


def _remember_books(books: list) -> list:
    for book in books:
        _LIBRIVOX_BOOKS[book.book_id] = book
    return books


def _browse_librivox(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """LibriVox's three working axes.

    There is deliberately no "By Title": the API supports no title filter in any
    form -- query string or path, with or without a caret -- while author, genre
    and since all work. An axis that quietly 404s is worse than one not offered.
    """
    refuse_when_offline(safe_mode)
    return [
        folder("librivoxrecent", "Recently Added"),
        folder("librivoxgenres", "By Genre"),
        folder("librivoxauthors", "By Author"),
    ]


def _archive_book_nodes(items: list) -> list[BrowseNode]:
    """LibriVox books that came the other way round -- see librivox_archive."""
    from quill.core.radio.librivox_archive import VIA_ARCHIVE_NOTE

    return [
        folder(make_id("archiveitem", item.identifier), item.title, note=VIA_ARCHIVE_NOTE)
        for item in items
        if getattr(item, "identifier", "")
    ]


def _librivox_or_archive(
    primary: Callable[[], list], fallback: Callable[[], list]
) -> list[BrowseNode]:
    """LibriVox's own catalogue, or the Archive when it cannot answer.

    librivox.org answered Cloudflare 522 for hours on 2026-08-16 and the branch
    was dead for the duration -- while every one of those books was sitting in
    the Archive's ``librivoxaudio`` collection, reachable. Falling back beats a
    branch that works only when its single upstream is healthy.

    **Both routes failing re-raises rather than returning nothing.** Swallowing
    it made the branch report "this folder is empty" during an outage of both
    upstreams, which is the exact confusion the empty-versus-unreachable
    distinction exists to prevent -- a sweep of every provider caught it on the
    day the Internet Archive's search backend was also down. A genuinely empty
    genre still answers empty, because that is the case where the catalogue
    *replied* and had nothing.
    """
    first_error: Exception | None = None
    try:
        nodes = _librivox_book_nodes(_remember_books(primary()))
    except Exception as error:  # noqa: BLE001 - the fallback exists for this
        nodes, first_error = [], error
    if nodes:
        return nodes
    try:
        return _archive_book_nodes(fallback())
    except Exception as second_error:  # noqa: BLE001
        if first_error is not None:
            # Neither route answered: that is unreachable, not empty, and
            # browse() turns a raise into exactly that message.
            raise first_error from second_error
        return []


def _browse_librivox_recent(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.media import librivox
    from quill.core.radio import librivox_archive

    refuse_when_offline(safe_mode)
    return _librivox_or_archive(
        librivox.recent_books,
        lambda: librivox_archive.recent(safe_mode=safe_mode),
    )


def _browse_librivox_genres(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.media import librivox
    from quill.core.radio import librivox_archive

    refuse_when_offline(safe_mode)
    if args and args[0]:
        genre = args[0]
        return _librivox_or_archive(
            lambda: librivox.books_by_genre(genre),
            lambda: librivox_archive.by_genre(genre, safe_mode=safe_mode),
        )
    return [folder(make_id("librivoxgenres", g), g) for g in librivox.BROWSE_GENRES]


def _browse_librivox_authors(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.media import librivox
    from quill.core.radio import librivox_archive

    refuse_when_offline(safe_mode)
    if args and args[0] and len(args[0]) > 1:
        name = args[0]
        return _librivox_or_archive(
            lambda: librivox.books_by_author(name),
            lambda: librivox_archive.by_author(name, safe_mode=safe_mode),
        )
    # The A-Z list itself has no Archive equivalent -- the Archive can search
    # for a creator but cannot enumerate LibriVox's authors -- so when
    # librivox.org is down this axis reports unreachable rather than inventing
    # a shorter list and calling it complete.
    authors = librivox.list_authors()
    if not (args and args[0]):
        return [
            folder(make_id("librivoxauthors", group), group, child_count=len(rows))
            for group, rows in letter_groups(authors, lambda a: a.last_name or a.first_name)
        ]
    wanted = args[0]
    for group, rows in letter_groups(authors, lambda a: a.last_name or a.first_name):
        if group == wanted:
            return [
                folder(make_id("librivoxauthors", author.last_name), author.display_name)
                for author in rows
                if author.last_name
            ]
    return []


def _browse_librivox_book(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.media.librivox import LibriVoxBook

    book = _LIBRIVOX_BOOKS.get(args[0]) if args else None
    if not isinstance(book, LibriVoxBook):
        return []
    return [
        leaf(
            RadioStation(
                name=section.title,
                stream_url=section.url,
                source="LibriVox",
                is_recording=True,
            ),
            note=f"section {section.index + 1}",
        )
        for section in book.sections
        if section.url
    ]
