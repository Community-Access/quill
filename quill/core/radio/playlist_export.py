"""Export radio favorites to a playlist (#1249).

The writer counterpart to :mod:`quill.core.radio.playlist_import`. Serializes a
list of :class:`~quill.core.radio.favorites.FavoriteStation` to extended-M3U
text so a listener can hand their stations to any media player, share them, or
back them up outside Quill Radio.

Pure and wx-free so it is unit-tested without files or a UI.
"""

from __future__ import annotations

from collections.abc import Iterable

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
