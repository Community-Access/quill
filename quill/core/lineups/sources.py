"""Read-only adapters: everything Radio and Cast know, as :class:`ItemFacts`.

Each source reads one store from the family's data folder and never writes it.
A source that cannot read its store raises; :func:`build_catalogue` turns that
into "this kind is unavailable", which is what keeps a failed read from ever
costing the listener a row (``merge`` guarantee 1).

Completeness matters as much as content (:class:`~quill.core.lineups.merge.Catalogue`):

* **complete** kinds are listed in full -- Cast's shows and episodes, Radio's
  Local Media and recordings -- so a reference not found is *missing*;
* the others (stations, places, YouTube) come from lists that are only part of
  the world (Favorites, tags, history, saved items), so a reference not found
  is *unlisted*, and a row added by hand plays from its own stored record.

Videos in a followed channel's feed are fetched over the network and not kept
on disk, so rules see saved videos and playlists and followed channels, not
every upload; that is said in the user guide rather than hidden.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.merge import Catalogue
from quill.core.lineups.refs import (
    KIND_EPISODE,
    KIND_LOCAL,
    KIND_PLACE,
    KIND_RECORDING,
    KIND_SHOW,
    KIND_STATION,
    KIND_YT_CHANNEL,
    KIND_YT_PLAYLIST,
    KIND_YT_VIDEO,
    KINDS,
    ItemRef,
    episode_ref,
    local_ref,
)

logger = logging.getLogger(__name__)

COMPLETE_KINDS = frozenset({KIND_EPISODE, KIND_SHOW, KIND_LOCAL, KIND_RECORDING})
DAY = 86_400.0


# -- small readers -----------------------------------------------------------------


def _epoch_of_rfc(text: str) -> float:
    if not text:
        return 0.0
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        try:
            moment = datetime.fromisoformat(text)
        except ValueError:
            return 0.0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.timestamp()


def _epoch_of_iso(text: str) -> float:
    if not text:
        return 0.0
    try:
        moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return _epoch_of_rfc(str(text))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.timestamp()


def _days_since(epoch: float, now: float) -> int | None:
    return None if epoch <= 0 else max(0, int((now - epoch) // DAY))


# -- Cast -------------------------------------------------------------------------


def cast_items(
    data_dir: Path, *, now: float
) -> tuple[tuple[ItemFacts, ...], tuple[ItemFacts, ...]]:
    """``(shows, episodes)`` from Cast's library. Raises when it cannot be read."""
    from quill.core.podcasts.folder_membership import placements
    from quill.core.podcasts.subscriptions import load_library

    library = load_library(data_dir, strict=True)
    try:
        from quill.core.podcasts.radio_listens import finished_audio_urls

        finished_elsewhere = finished_audio_urls(data_dir)
    except Exception:  # noqa: BLE001 - a missing hand-off file is not a failure
        finished_elsewhere = frozenset()
    shows: list[ItemFacts] = []
    episodes: list[ItemFacts] = []
    for show in library.shows:
        folder_names = tuple(
            folder.name
            for folder in (library.find_folder(fid) for fid in placements(library, show) if fid)
            if folder is not None
        )
        labels = tuple(library.labels_for(show.id))
        unplayed = 0
        newest = 0.0
        next_up: tuple[float, dict[str, object]] | None = None
        for episode in show.episodes:
            published = _epoch_of_rfc(episode.published)
            newest = max(newest, published)
            finished = bool(episode.played) or episode.audio_url in finished_elsewhere
            if not finished:
                unplayed += 1
            duration = max(0, int(episode.duration_seconds or 0))
            heard = 0.0
            if duration and episode.position_ms > 0:
                heard = min(1.0, episode.position_ms / (duration * 1000))
            last = _epoch_of_iso(episode.last_played_on)
            # The record Radio's own browse tree plays an episode from
            # (browse_libraries._episode_leaves), so Radio playing it from a
            # Lineup is Radio playing it, with the same resume and listens.
            payload: dict[str, object] = {
                "name": episode.title,
                "stream_url": episode.audio_url,
                "homepage": show.feed_url,
                "source": show.title,
                "is_recording": True,
            }
            if not finished and (next_up is None or published > next_up[0]):
                next_up = (published, payload)
            episodes.append(
                ItemFacts(
                    ref=episode_ref(show.id, episode.guid),
                    name=episode.title or "Untitled episode",
                    facts={
                        "show": show.title,
                        "folder": folder_names[0] if folder_names else "",
                        "labels": labels + folder_names,
                        "age": _days_since(published, now),
                        "played": finished,
                        "in_progress": bool(episode.position_ms > 0 and not finished),
                        "percent_heard": int(heard * 100) if duration else None,
                        "downloaded": bool(episode.downloaded_path),
                        "season": episode.season or None,
                        "number": episode.episode_number or None,
                        "episode_type": (episode.episode_type or "full").lower(),
                        "days_since_played": _days_since(last, now),
                    },
                    length_seconds=duration,
                    source=show.title,
                    finished=finished,
                    position_fraction=heard,
                    published_at=published,
                    payload=payload,
                )
            )
        shows.append(
            ItemFacts(
                ref=ItemRef(KIND_SHOW, show.id),
                name=show.title or "Untitled podcast",
                facts={
                    "folder": folder_names[0] if folder_names else "",
                    "labels": labels + folder_names,
                    "favorite": bool(show.is_favorite),
                    "paused": bool(show.paused),
                    "language": show.language,
                    "category": show.category,
                    "unplayed": unplayed,
                    "newest_age": _days_since(newest, now),
                },
                source="Podcast",
                published_at=newest,
                # Playing a podcast from a Lineup plays its newest unplayed episode.
                payload=next_up[1] if next_up is not None else None,
            )
        )
    return tuple(shows), tuple(episodes)


def episode_facts(show: Any, episode: Any) -> ItemFacts:
    """One Cast episode as a row, for Add to Lineup (the same reference a rule makes)."""
    return ItemFacts(
        ref=episode_ref(show.id, episode.guid),
        name=episode.title or "Untitled episode",
        length_seconds=max(0, int(episode.duration_seconds or 0)),
        source=show.title,
        finished=bool(episode.played),
        published_at=_epoch_of_rfc(episode.published),
        payload={
            "name": episode.title,
            "stream_url": episode.audio_url,
            "homepage": show.feed_url,
            "source": show.title,
            "is_recording": True,
        },
    )


def show_facts(show: Any) -> ItemFacts:
    """One followed Cast podcast as a row, for Add to Lineup."""
    return ItemFacts(
        ref=ItemRef(KIND_SHOW, show.id), name=show.title or "Untitled podcast", source="Podcast"
    )


# -- Radio: stations and places ----------------------------------------------------------


def station_facts(
    station: Any,
    *,
    folder: str = "",
    favorite: bool = False,
    my_tags: Iterable[str] = (),
    listened_minutes: int | None = None,
    recent: bool = False,
) -> ItemFacts:
    """One ``RadioStation`` as a row: a station, a saved place, or a YouTube item.

    Used by the station sources and by every "Add to Lineup" command, so a row
    added by hand and the same row found by a rule are the same reference.
    """
    from quill.core.radio.favorites import is_place, place_node_id

    name = str(getattr(station, "name", "") or "")
    source = str(getattr(station, "source", "") or "")
    payload: dict[str, object] = dict(station.to_dict()) if hasattr(station, "to_dict") else {}
    if is_place(station):
        return ItemFacts(
            ref=ItemRef(KIND_PLACE, place_node_id(station)),
            name=name,
            facts={"folder": folder, "source": source},
            source=source,
            payload=payload,
        )
    url = str(getattr(station, "stream_url", "") or "")
    youtube = youtube_ref(url)
    if youtube is not None:
        return ItemFacts(
            ref=youtube,
            name=name,
            facts={"channel": source if source != "YouTube" else "", "saved": False},
            source="YouTube",
            payload=payload,
        )
    key = str(getattr(station, "station_uuid", "") or "") or url
    is_recording = bool(getattr(station, "is_recording", False))
    return ItemFacts(
        ref=ItemRef(KIND_STATION, key),
        name=name,
        facts={
            "folder": folder,
            "favorite": favorite,
            "my_tags": tuple(my_tags),
            "tags": tuple(getattr(station, "tags", ()) or ()),
            "country": str(getattr(station, "country", "") or ""),
            "language": str(getattr(station, "language", "") or ""),
            "codec": str(getattr(station, "codec", "") or ""),
            "bitrate": int(getattr(station, "bitrate_kbps", 0) or 0) or None,
            "source": source or "Radio Browser",
            "listened": listened_minutes,
            "recent": recent,
        },
        source=source,
        live=not is_recording,
        payload=payload,
    )


def youtube_ref(url: str) -> ItemRef | None:
    """The YouTube reference a URL names, or ``None`` when it is not YouTube.

    Always the canonical form ``youtube_saved.classify_link`` gives, so a video
    added by hand from a search and the same video in Saved are one reference.
    """
    from quill.core.radio import youtube_saved
    from quill.core.radio.youtube_urls import is_youtube_url

    try:
        if not is_youtube_url(url):
            return None
        kind, normal = youtube_saved.classify_link(url)
    except Exception:  # noqa: BLE001 - an odd URL is simply not a YouTube item
        return None
    if not normal:
        return None
    if kind == youtube_saved.PLAYLIST:
        return ItemRef(KIND_YT_PLAYLIST, normal)
    if kind == youtube_saved.VIDEO:
        return ItemRef(KIND_YT_VIDEO, normal)
    if kind == "channel":
        return ItemRef(KIND_YT_CHANNEL, normal)
    return None


def _youtube_key(url: str, fallback_kind: str) -> ItemRef:
    return youtube_ref(url) or ItemRef(fallback_kind, url)


def radio_station_items(data_dir: Path) -> tuple[tuple[ItemFacts, ...], tuple[ItemFacts, ...]]:
    """``(stations, places)`` Radio knows by heart: Favorites, tags, recent history."""
    from quill.core.radio.favorites import is_place, load_favorites
    from quill.core.radio.history import load_history  # the one import Radio uses

    favorites = load_favorites(data_dir)
    try:
        from quill.core.radio import station_tags

        tag_store: Any = station_tags.load_tag_store(data_dir)
    except Exception:  # noqa: BLE001 - tags are an extra; no tags is fine
        tag_store = None
    listened = _listened_minutes(data_dir)
    try:
        history = load_history(data_dir)
        recent_stations = list(getattr(history, "stations", []) or [])
    except Exception:  # noqa: BLE001
        recent_stations = []
    from quill.core.radio.stats import station_key

    recent_keys = {station_key(s) for s in recent_stations}
    seen: set[ItemRef] = set()
    stations: list[ItemFacts] = []
    places: list[ItemFacts] = []

    def tags_of(station: Any, own: Iterable[str] = ()) -> tuple[str, ...]:
        extra = tag_store.tags_for(station) if tag_store is not None else ()
        return tuple(dict.fromkeys((*own, *extra)))

    def add(item: ItemFacts) -> None:
        if item.ref in seen:
            return
        seen.add(item.ref)
        (places if item.ref.kind == KIND_PLACE else stations).append(item)

    for favorite in favorites.favorites:
        station = favorite.station
        key = station_key(station)
        add(
            station_facts(
                station,
                folder=favorite.folder,
                favorite=True,
                my_tags=tags_of(station, favorite.user_tags),
                listened_minutes=listened.get(key),
                recent=key in recent_keys,
            )
            if not is_place(station)
            else station_facts(station, folder=favorite.folder, favorite=True)
        )
    if tag_store is not None:
        for station, tags in getattr(tag_store, "entries", {}).values():
            key = station_key(station)
            add(
                station_facts(
                    station,
                    my_tags=tags,
                    listened_minutes=listened.get(key),
                    recent=key in recent_keys,
                )
            )
    for station in recent_stations:
        key = station_key(station)
        add(
            station_facts(
                station, my_tags=tags_of(station), listened_minutes=listened.get(key), recent=True
            )
        )
    return tuple(stations), tuple(places)


def _listened_minutes(data_dir: Path) -> dict[str, int]:
    try:
        from quill.core.radio.stats import summarize

        summary = summarize(data_dir)
    except Exception:  # noqa: BLE001 - no stats yet is not a failure
        return {}
    return {total.key: int(total.seconds // 60) for total in summary.keys}


# -- Radio: YouTube -----------------------------------------------------------------


def youtube_items(data_dir: Path, *, now: float) -> tuple[tuple[ItemFacts, ...], ...]:
    """``(videos, playlists, channels)`` saved or followed in Radio."""
    from quill.core.radio import youtube_saved
    from quill.core.radio.youtube_channels import ChannelStore

    saved = youtube_saved.SavedStore(data_dir)
    videos: list[ItemFacts] = []
    playlists: list[ItemFacts] = []
    for item in saved.all():
        payload: dict[str, object] = {
            "name": item.name,
            "stream_url": item.url,
            "source": "YouTube",
        }
        if item.kind == youtube_saved.PLAYLIST:
            playlists.append(
                ItemFacts(
                    ref=_youtube_key(item.url, KIND_YT_PLAYLIST),
                    name=item.name or item.url,
                    facts={"channel": item.uploader, "count": item.item_count or None},
                    source=item.uploader or "YouTube",
                    payload=payload,
                )
            )
        else:
            videos.append(
                ItemFacts(
                    ref=_youtube_key(item.url, KIND_YT_VIDEO),
                    name=item.name or item.url,
                    facts={"channel": item.uploader, "saved": True, "live": item.is_live},
                    length_seconds=max(0, item.duration_ms // 1000),
                    source=item.uploader or "YouTube",
                    live=item.is_live,
                    payload=payload,
                )
            )
    try:
        from quill.core.radio.youtube_channel_alerts import AlertStore

        alerts: Any = AlertStore(data_dir)
    except Exception:  # noqa: BLE001
        alerts = None
    channels = tuple(
        ItemFacts(
            ref=_youtube_key(channel.url, KIND_YT_CHANNEL),
            name=channel.name or channel.url,
            facts={
                "alerts": bool(alerts.is_notifying(channel.url)) if alerts is not None else False
            },
            source="YouTube",
            payload={"name": channel.name, "stream_url": channel.url, "source": "YouTube"},
        )
        for channel in ChannelStore(data_dir).all()
    )
    return tuple(videos), tuple(playlists), channels


# -- Radio: Local Media and recordings ------------------------------------------------


def local_item_facts(playlist: Any, item: Any, *, now: float) -> ItemFacts:
    """One Local Media file as a row: the same reference rules and Add to Lineup use."""
    return ItemFacts(
        ref=local_ref(playlist.id, item.id),
        name=item.display_title,
        facts={
            "artist": item.artist,
            "album": item.album,
            "playlist": playlist.name,
            "added_age": _days_since(float(item.added_at or 0), now),
            "video": bool(item.is_video),
        },
        length_seconds=max(0, int(item.duration_seconds or 0)),
        source=playlist.name,
        published_at=float(item.added_at or 0),
        payload={"path": item.path, "playlist": playlist.id, "item": item.id},
    )


def local_media_items(data_dir: Path, *, now: float) -> tuple[ItemFacts, ...]:
    from quill.core.radio.local_media import load_library

    library = load_library(data_dir)
    return tuple(
        local_item_facts(playlist, item, now=now)
        for playlist in library.playlists
        for item in playlist.items
    )


def recording_facts(entry: Any, *, now: float) -> ItemFacts | None:
    """One ``RecordingEntry`` as a row; ``None`` for a scheduled one (no file yet)."""
    path = getattr(entry, "path", None)
    if path is None:
        return None
    modified = getattr(entry, "modified", None) or getattr(entry, "started_at", None)
    when = modified.timestamp() if isinstance(modified, datetime) else 0.0
    seconds = int(getattr(entry, "duration_seconds", 0) or 0)
    return ItemFacts(
        ref=ItemRef(KIND_RECORDING, str(getattr(entry, "id", "") or path)),
        name=str(getattr(entry, "name", "") or Path(str(path)).stem),
        facts={"age": _days_since(when, now), "status": str(getattr(entry, "status", "") or "")},
        length_seconds=seconds,
        source="Recording",
        published_at=when,
        payload={
            "name": str(getattr(entry, "name", "")),
            "stream_url": str(path),
            "is_recording": True,
        },
    )


# -- the catalogue ---------------------------------------------------------------------

Reader = Callable[[], Mapping[str, tuple[ItemFacts, ...]]]


def build_catalogue(
    data_dir: Path,
    *,
    now: float,
    recordings: Callable[[], Iterable[Any]] | None = None,
) -> Catalogue:
    """Everything both apps know, by kind. A store that fails makes its kinds unavailable.

    *recordings* lists Radio's recordings (it needs the running app's recording
    settings); without it, recordings read as unavailable rather than as none.
    """
    items: dict[str, tuple[ItemFacts, ...] | None] = dict.fromkeys(KINDS)

    def read(
        kinds: tuple[str, ...], reader: Callable[[], tuple[tuple[ItemFacts, ...], ...]]
    ) -> None:
        try:
            results = reader()
        except Exception as exc:  # noqa: BLE001 - one store failing must not fail the rest
            logger.info("Lineups could not read %s: %s", "/".join(kinds), exc)
            return
        for kind, found in zip(kinds, results, strict=True):
            items[kind] = found

    read((KIND_SHOW, KIND_EPISODE), lambda: cast_items(data_dir, now=now))
    read((KIND_STATION, KIND_PLACE), lambda: radio_station_items(data_dir))
    read(
        (KIND_YT_VIDEO, KIND_YT_PLAYLIST, KIND_YT_CHANNEL), lambda: youtube_items(data_dir, now=now)
    )
    read((KIND_LOCAL,), lambda: (local_media_items(data_dir, now=now),))
    if recordings is not None:

        def read_recordings() -> tuple[tuple[ItemFacts, ...]]:
            found = (recording_facts(entry, now=now) for entry in recordings())
            return (tuple(item for item in found if item is not None),)

        read((KIND_RECORDING,), read_recordings)
    return Catalogue(items, COMPLETE_KINDS)


__all__ = [
    "COMPLETE_KINDS",
    "build_catalogue",
    "cast_items",
    "local_media_items",
    "radio_station_items",
    "recording_facts",
    "station_facts",
    "youtube_items",
    "youtube_ref",
]
