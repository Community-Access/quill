"""The free-music branches of Browse Stations: Audius, Mixcloud, ccMixter.

Split from :mod:`quill.core.radio.browse_sources` under GATE-11 (extract, never
rebaseline), and a coherent seam rather than a slice: all three are the
independent-music catalogs served by :mod:`quill.core.radio.free_music`, and
nothing else in the dispatcher touches them. The handlers are registered back
in ``browse_sources._HANDLERS`` exactly like every other source's.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id


def _stations(rows: list) -> list[BrowseNode]:
    return [leaf(station) for station in rows]


def browse_audius(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import free_music

    if args and args[0]:
        return _stations(free_music.audius_trending(args[0], safe_mode=safe_mode))
    # "Trending Now" needs its own kind: an "audius" id with an empty argument
    # parses back to no arguments at all, so the folder re-listed this root
    # inside itself, endlessly, instead of ever showing a track.
    nodes = [folder("audiustrending", "Trending Now")]
    nodes += [folder(make_id("audius", genre), genre) for genre in free_music.AUDIUS_GENRES]
    return nodes


def browse_audius_trending(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Audius's overall trending list -- no genre filter."""
    from quill.core.radio import free_music

    return _stations(free_music.audius_trending("", safe_mode=safe_mode))


def browse_mixcloud(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    return [
        folder(make_id("mixcloudfmt", "music"), "Music Categories"),
        folder(make_id("mixcloudfmt", "talk"), "Talk Categories"),
    ]


def browse_mixcloud_format(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import free_music

    wanted = args[0] if args else "music"
    return [
        folder(make_id("mixcloudcat", category.slug), category.name)
        for category in free_music.mixcloud_categories(safe_mode=safe_mode)
        if category.fmt == wanted
    ]


def browse_mixcloud_category(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import free_music

    slug = args[0] if args else ""
    # Mode A: the row's "stream" is the show's page, and it says so before Enter.
    return [
        leaf(show, note="opens on Mixcloud in your browser")
        for show in free_music.mixcloud_shows(slug, safe_mode=safe_mode)
    ]


def browse_ccmixter(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import free_music

    if args and args[0]:
        return [
            leaf(track, note=track.tags[0] if track.tags else "")
            for track in free_music.ccmixter_by_tag(args[0], safe_mode=safe_mode)
        ]
    return [folder(make_id("ccmixter", tag), tag.title()) for tag in free_music.CCMIXTER_TAGS]
