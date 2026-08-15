"""Export radio favorites to a playlist (#1249).

The writer counterpart to :mod:`quill.core.radio.playlist_import` and
:mod:`quill.core.radio.playlist_formats`. Serializes a list of
:class:`~quill.core.radio.favorites.FavoriteStation` to extended-M3U, PLS, or
XSPF text so a listener can hand their stations to any media player, share
them, or back them up outside Quill Radio.

Three formats because the reader now understands three: exporting only the one
format we happened to import first is the kind of asymmetry that makes a
feature feel half-built. Each one round-trips through its own parser, which is
what the tests assert rather than merely comparing strings.

Pure and wx-free so it is unit-tested without files or a UI.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from xml.sax.saxutils import escape, quoteattr

from quill.core.radio.favorites import FavoriteStation


def _clean_label(text: str) -> str:
    """A single-line label safe for an ``#EXTINF`` line (no embedded newlines)."""
    return " ".join((text or "").split()).strip()


def export_m3u(favorites: Iterable[FavoriteStation]) -> str:
    """Serialize *favorites* to extended-M3U (``#EXTM3U``) playlist text.

    Each favorite becomes an ``#EXTINF:-1,<label>`` line -- using the favorite's
    ``display_label`` so a custom name is honored -- followed by its stream URL.
    Favorites without a playable stream URL are skipped. M3U is flat, so folder
    structure is not represented (matching how :func:`parse_m3u` discards it on
    import). The result round-trips through ``parse_m3u``.
    """
    lines = ["#EXTM3U"]
    for fav in favorites:
        url = (fav.station.stream_url or "").strip()
        if not url:
            continue
        lines.append(f"#EXTINF:-1,{_clean_label(fav.display_label)}")
        lines.append(url)
    return "\n".join(lines) + "\n"


def _playable_entries(favorites: Iterable[FavoriteStation]) -> list[tuple[str, str]]:
    """``(label, url)`` for every favorite that has a stream to export."""
    entries: list[tuple[str, str]] = []
    for fav in favorites:
        url = (fav.station.stream_url or "").strip()
        if url:
            entries.append((_clean_label(fav.display_label), url))
    return entries


def export_pls(favorites: Iterable[FavoriteStation]) -> str:
    """Serialize *favorites* to PLS (``[playlist]``) text.

    The format most SHOUTcast and Icecast servers hand out, so a listener's
    exported favorites drop straight into the players that expect it. Entries
    are numbered from 1, each with a ``File``/``Title``/``Length`` triple;
    ``Length=-1`` is the conventional "live stream, unknown length". The
    trailing ``NumberOfEntries`` and ``Version=2`` are both required by strict
    readers. Round-trips through :func:`playlist_formats.parse_pls`.
    """
    entries = _playable_entries(favorites)
    lines = ["[playlist]"]
    for index, (label, url) in enumerate(entries, start=1):
        lines.append(f"File{index}={url}")
        lines.append(f"Title{index}={label}")
        lines.append(f"Length{index}=-1")
    lines.append(f"NumberOfEntries={len(entries)}")
    lines.append("Version=2")
    return "\n".join(lines) + "\n"


def export_xspf(favorites: Iterable[FavoriteStation]) -> str:
    """Serialize *favorites* to XSPF text.

    Xiph's own playlist format, which is what ``dir.xiph.org`` serves and what
    several open-source players prefer. Text is XML-escaped rather than
    hand-quoted, because a station name containing ``&`` is ordinary and a
    playlist that breaks on one is not. Round-trips through
    :func:`playlist_formats.parse_xspf`.
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<playlist version="1" xmlns="http://xspf.org/ns/0/">',
        "  <title>Quill Radio Favorites</title>",
        "  <trackList>",
    ]
    for label, url in _playable_entries(favorites):
        lines.append("    <track>")
        lines.append(f"      <location>{escape(url)}</location>")
        lines.append(f"      <title>{escape(label)}</title>")
        lines.append("    </track>")
    lines.append("  </trackList>")
    lines.append("</playlist>")
    return "\n".join(lines) + "\n"


def export_asx(favorites: Iterable[FavoriteStation]) -> str:
    """Serialize *favorites* to ASX text.

    Included for symmetry with the reader, and because the older players still
    in use by some radio reading services read ASX and nothing newer. The href
    is attribute-quoted properly, which much real-world ASX is not.
    Round-trips through :func:`playlist_formats.parse_asx`.
    """
    lines = ['<ASX version="3.0">', "  <TITLE>Quill Radio Favorites</TITLE>"]
    for label, url in _playable_entries(favorites):
        lines.append("  <ENTRY>")
        lines.append(f"    <TITLE>{escape(label)}</TITLE>")
        lines.append(f"    <REF HREF={quoteattr(url)} />")
        lines.append("  </ENTRY>")
    lines.append("</ASX>")
    return "\n".join(lines) + "\n"


#: Export formats offered by "Export Favorites as...", in menu order:
#: ``(label, file extension, writer)``. One registry so the menu, the file
#: dialog's wildcard, and the writer cannot drift apart.
PlaylistWriter = Callable[[Iterable[FavoriteStation]], str]

EXPORT_FORMATS: tuple[tuple[str, str, PlaylistWriter], ...] = (
    ("Extended M3U", "m3u", export_m3u),
    ("PLS", "pls", export_pls),
    ("XSPF", "xspf", export_xspf),
    ("ASX", "asx", export_asx),
)


def export_as(kind: str, favorites: Iterable[FavoriteStation]) -> str:
    """Serialize *favorites* in the format named by *kind* (its extension).

    Unknown kinds fall back to M3U rather than raising: an export that silently
    produces the wrong extension is bad, but an export command that throws in
    a file dialog is worse.
    """
    for _label, extension, writer in EXPORT_FORMATS:
        if extension == kind.strip().lower().lstrip("."):
            return writer(favorites)
    return export_m3u(favorites)
