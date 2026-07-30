"""Spotify Web API data model and adapters onto QUILL's podcast model.

Small, tolerant dataclasses for the object kinds the Radio/Cast browse surfaces
need -- tracks, shows, and episodes -- each built from Spotify's raw JSON via a
lenient ``from_json`` that never raises on a missing or oddly-typed field.

The two adapters (:meth:`SpotifyShow.to_podcast_show`,
:meth:`SpotifyEpisode.to_podcast_episode`) let a Spotify show/episode flow into
the existing shared podcast player without a parallel UI. One deliberate quirk:
a Spotify episode has **no downloadable audio URL** (the audio is DRM-protected
and only the Web Playback SDK may play it), yet
:class:`quill.core.podcasts.models.PodcastEpisode` requires a non-empty
``audio_url``. So the adapter stores the ``spotify:episode:...`` URI there -- it
satisfies the invariant and doubles as the play token the Web engine needs.
:func:`is_spotify_uri` recognises those adapted episodes; the Spotify dataclasses
also carry an explicit :data:`SOURCE` marker.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

#: Marker stored on adapted objects and recognised by :func:`is_spotify_uri`.
SOURCE = "spotify"

#: Spotify play tokens are URIs like ``spotify:track:...`` / ``spotify:episode:...``.
SPOTIFY_URI_PREFIX = "spotify:"


def is_spotify_uri(value: str) -> bool:
    """True when *value* is a Spotify URI (e.g. an adapted episode's audio_url)."""
    return value.startswith(SPOTIFY_URI_PREFIX)


def _artist_names(value: dict[str, object]) -> str:
    artists = value.get("artists")
    if not isinstance(artists, list):
        return ""
    names = [str(a.get("name", "")) for a in artists if isinstance(a, dict) and a.get("name")]
    return ", ".join(names)


@dataclass(frozen=True, slots=True)
class SpotifyTrack:
    """One track in a search result, playlist, or saved-songs list."""

    id: str
    uri: str
    name: str
    artist: str = ""
    album: str = ""
    duration_ms: int = 0
    explicit: bool = False
    source: str = SOURCE

    @classmethod
    def from_json(cls, data: dict[str, object]) -> SpotifyTrack:
        album = data.get("album")
        album_name = str(album.get("name", "")) if isinstance(album, dict) else ""
        return cls(
            id=str(data.get("id", "")),
            uri=str(data.get("uri", "")),
            name=str(data.get("name", "")) or "Untitled",
            artist=_artist_names(data),
            album=album_name,
            duration_ms=_coerce_int(data.get("duration_ms"), 0),
            explicit=bool(data.get("explicit", False)),
        )


@dataclass(frozen=True, slots=True)
class SpotifyShow:
    """A saved / searched podcast show on Spotify."""

    id: str
    uri: str
    name: str
    publisher: str = ""
    description: str = ""
    total_episodes: int = 0
    homepage: str = ""
    artwork_url: str = ""
    source: str = SOURCE

    @classmethod
    def from_json(cls, data: dict[str, object]) -> SpotifyShow:
        return cls(
            id=str(data.get("id", "")),
            uri=str(data.get("uri", "")),
            name=str(data.get("name", "")) or "Untitled",
            publisher=str(data.get("publisher", "")),
            description=str(data.get("description", "")),
            total_episodes=_coerce_int(data.get("total_episodes"), 0),
            homepage=_external_url(data),
            artwork_url=_first_image(data),
        )

    def to_podcast_show(self) -> PodcastShow:
        """Adapt to a :class:`PodcastShow` for the shared player/browse tree.

        ``feed_url`` is left empty -- Spotify shows have no public RSS feed; the
        Spotify identity travels in ``homepage`` (the open.spotify.com page) and
        via the episodes' ``spotify:`` audio URIs. The show id is namespaced so
        it can never collide with a real subscribed show's id.
        """
        return PodcastShow(
            id=f"spotify:{self.id}",
            title=self.name,
            feed_url="",
            homepage=self.homepage,
            artwork_url=self.artwork_url,
        )


@dataclass(frozen=True, slots=True)
class SpotifyEpisode:
    """One podcast episode on Spotify (no downloadable audio -- SDK-only)."""

    id: str
    uri: str
    name: str
    description: str = ""
    duration_ms: int = 0
    release_date: str = ""
    show_name: str = ""
    show_publisher: str = ""
    explicit: bool = False
    artwork_url: str = ""
    source: str = SOURCE

    @classmethod
    def from_json(cls, data: dict[str, object]) -> SpotifyEpisode:
        show = data.get("show")
        show_name = str(show.get("name", "")) if isinstance(show, dict) else ""
        show_publisher = str(show.get("publisher", "")) if isinstance(show, dict) else ""
        return cls(
            id=str(data.get("id", "")),
            uri=str(data.get("uri", "")),
            name=str(data.get("name", "")) or "Untitled",
            description=str(data.get("description", "")),
            duration_ms=_coerce_int(data.get("duration_ms"), 0),
            release_date=str(data.get("release_date", "")),
            show_name=show_name,
            show_publisher=show_publisher,
            explicit=bool(data.get("explicit", False)),
            artwork_url=_first_image(data),
        )

    def to_podcast_episode(self) -> PodcastEpisode:
        """Adapt to a :class:`PodcastEpisode` for the shared player.

        ``audio_url`` is the ``spotify:episode:...`` URI: it satisfies the model's
        non-empty invariant *and* is the exact token the Web Playback engine
        plays. :func:`is_spotify_uri` on that field is the source marker on the
        podcast side. Duration is Spotify's milliseconds, rounded to whole
        seconds to match the podcast model's unit.
        """
        return PodcastEpisode(
            guid=self.uri or self.id,
            title=self.name,
            audio_url=self.uri,
            published=self.release_date,
            duration_seconds=self.duration_ms // 1000,
            description=self.description,
        )


@dataclass(frozen=True, slots=True)
class SavedItems:
    """A page of the user's saved library, as the browse surfaces consume it."""

    shows: list[SpotifyShow] = field(default_factory=list)
    episodes: list[SpotifyEpisode] = field(default_factory=list)
    tracks: list[SpotifyTrack] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SearchResults:
    """Grouped results of one Spotify search, per requested type."""

    tracks: list[SpotifyTrack] = field(default_factory=list)
    shows: list[SpotifyShow] = field(default_factory=list)
    episodes: list[SpotifyEpisode] = field(default_factory=list)


def _first_image(data: dict[str, object]) -> str:
    images = data.get("images")
    if not isinstance(images, list):
        return ""
    for image in images:
        if isinstance(image, dict) and image.get("url"):
            return str(image["url"])
    return ""


def _external_url(data: dict[str, object]) -> str:
    external = data.get("external_urls")
    if isinstance(external, dict) and external.get("spotify"):
        return str(external["spotify"])
    return ""


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


__all__ = [
    "SOURCE",
    "SPOTIFY_URI_PREFIX",
    "SavedItems",
    "SearchResults",
    "SpotifyEpisode",
    "SpotifyShow",
    "SpotifyTrack",
    "is_spotify_uri",
]
