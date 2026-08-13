"""Blend Spotify search results into the Find Stations list.

Spotify's Web API search is open to *every* signed-in account, free tier
included -- it is only playback that Spotify restricts to Premium (see
``FREE_ACCOUNT_NOTICE`` in :mod:`quill.core.spotify.models`). That asymmetry is
exactly why these rows are worth blending in: finding a show or a track by name
is the part that is genuinely awkward with a screen reader, and it works for
everyone. What happens on Enter differs by tier, and the row says so.

Each result becomes a :class:`~quill.core.radio.models.RadioStation` whose

* ``stream_url`` is the ``spotify:`` URI -- the exact token the Web Playback
  engine plays, so a Premium listener presses Enter and hears it; and
* ``homepage`` is the ``open.spotify.com`` link, which the station browser's
  existing "Open Website" action already opens.

That second field is the whole free-account story: the link opens the track in
Spotify's own app, where a free account plays it normally. So a Spotify row is
never a dead end -- it is playable in-app for Premium and one keystroke from
playing for everyone else.

wx-free, strict-typed. Conversion is pure and separately tested; the searching
half is bounded and failure-tolerant in the same way as the other blended
directories, so a Spotify hiccup never blanks the surrounding results.
"""

from __future__ import annotations

from typing import Protocol

from quill.core.radio.models import RadioStation
from quill.core.spotify.models import (
    SearchResults,
    SpotifyEpisode,
    SpotifyShow,
    SpotifyTrack,
)

#: The ``source`` these rows carry, matching the other directories' title case.
SOURCE = "Spotify"

#: Per-search cap. Spotify returns one page for all types in a single GET, so
#: this trims the blend rather than bounding network cost.
SPOTIFY_RESULT_CAP = 8

_WEB_BASE = "https://open.spotify.com"


def web_url(uri: str) -> str:
    """The ``open.spotify.com`` page for a ``spotify:kind:id`` URI.

    Returns ``""`` for anything that is not a well-formed URI, so a malformed
    row simply arrives without a homepage instead of with a broken link.
    """
    parts = uri.split(":")
    if len(parts) != 3 or parts[0] != "spotify" or not parts[1] or not parts[2]:
        return ""
    return f"{_WEB_BASE}/{parts[1]}/{parts[2]}"


def _station(
    *,
    name: str,
    uri: str,
    tags: tuple[str, ...],
    homepage: str = "",
) -> RadioStation | None:
    """One Spotify row, or ``None`` if it has no name or nothing to play."""
    if not name.strip() or not uri.strip():
        return None
    return RadioStation(
        name=name.strip(),
        stream_url=uri,
        homepage=homepage or web_url(uri),
        tags=tuple(t for t in tags if t),
        source=SOURCE,
    )


def track_to_station(track: SpotifyTrack) -> RadioStation | None:
    """A track as a station row: ``"Song - Artist"``.

    The artist belongs in the name, not only in the tags: a list of bare song
    titles is close to useless when several results share one, and the browser
    reads the name first.
    """
    name = f"{track.name} - {track.artist}" if track.artist else track.name
    return _station(
        name=name,
        uri=track.uri,
        tags=("song", *(t for t in (track.artist, track.album) if t)),
    )


def show_to_station(show: SpotifyShow) -> RadioStation | None:
    """A podcast show as a station row."""
    name = f"{show.name} - {show.publisher}" if show.publisher else show.name
    return _station(
        name=name,
        uri=show.uri,
        tags=("podcast", *((show.publisher,) if show.publisher else ())),
        homepage=show.homepage,
    )


def episode_to_station(episode: SpotifyEpisode) -> RadioStation | None:
    """A single podcast episode as a station row."""
    return _station(name=episode.name, uri=episode.uri, tags=("episode",))


def stations_from_results(
    results: SearchResults, *, cap: int = SPOTIFY_RESULT_CAP
) -> list[RadioStation]:
    """Flatten one :class:`SearchResults` into station rows, capped per type.

    Interleaving by type rather than concatenating keeps one prolific category
    from crowding the others out of the cap: a search for a band name should
    still surface that band's podcast interview.
    """
    if cap <= 0:
        return []
    per_type = max(1, cap // 3)
    rows: list[RadioStation] = []
    for items, convert in (
        (results.tracks[:per_type], track_to_station),
        (results.shows[:per_type], show_to_station),
        (results.episodes[:per_type], episode_to_station),
    ):
        for item in items:
            station = convert(item)  # type: ignore[arg-type]
            if station is not None:
                rows.append(station)
    return rows[:cap]


def is_spotify_station(station: RadioStation) -> bool:
    """Whether *station* came from Spotify (search row or saved favorite)."""
    return station.source == SOURCE


def open_link_label(station: RadioStation) -> str:
    """The menu label for opening *station*'s web page.

    Spotify rows say "Open in Spotify" rather than "Open Website" because for
    a free account that action is not a footnote -- it is *the* way to hear the
    thing, and a label that hides it behind the word "website" hides the answer
    to "why won't this play?".
    """
    return "Open in &Spotify" if is_spotify_station(station) else "Open &Website"


class _Searcher(Protocol):
    def search(self, query: str, *, limit: int = ...) -> SearchResults: ...


def spotify_search_stations(
    query: str,
    *,
    client: _Searcher | None,
    cap: int = SPOTIFY_RESULT_CAP,
    safe_mode: bool = False,
) -> list[RadioStation]:
    """Spotify matches for *query* as station rows, or ``[]``.

    Returns empty -- never raises -- when Safe Mode is on, when no client was
    passed (nobody is signed in to Spotify, which is the common case), or when
    the search itself fails. Find Stations fans out across several sources and
    concatenates; a source that is merely absent must not disturb the rest.
    """
    if safe_mode or client is None or not query.strip():
        return []
    try:
        results = client.search(query, limit=max(cap, 1))
    except Exception:  # noqa: BLE001 -- a down source must not blank the list
        return []
    return stations_from_results(results, cap=cap)


def youtube_search_stations(
    query: str,
    *,
    cap: int = 8,
    safe_mode: bool = False,
    search: object = None,
) -> list[RadioStation]:
    """YouTube matches for *query* as station rows, or ``[]``.

    Lives next to the Spotify blend because it is the same idea: a source whose
    results become ordinary stations you can play, favorite and record. Rows
    carry the durable *page* URL, never a stream URL -- YouTube's expire within
    hours, which is why a saved YouTube station re-resolves on every play.

    Never raises. Safe Mode, a missing yt-dlp, and a failed search all mean the
    same thing here: no YouTube rows, and the other sources are undisturbed.
    """
    from quill.core.radio.youtube import search_youtube

    if safe_mode or not query.strip() or cap <= 0:
        return []
    finder = search or search_youtube
    try:
        entries = finder(query, limit=cap)  # type: ignore[operator]
    except Exception:  # noqa: BLE001 -- a down source must not blank the list
        return []
    rows: list[RadioStation] = []
    for entry in entries:
        page_url = str(getattr(entry, "page_url", "") or "")
        title = str(getattr(entry, "title", "") or "").strip()
        if not page_url or not title:
            continue
        uploader = str(getattr(entry, "uploader", "") or "").strip()
        rows.append(
            RadioStation(
                name=f"{title} - {uploader}" if uploader else title,
                stream_url=page_url,
                homepage=page_url,
                tags=("video", *((uploader,) if uploader else ())),
                source="YouTube",
            )
        )
    return rows[:cap]
