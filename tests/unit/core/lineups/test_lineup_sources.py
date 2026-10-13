"""The sources read real Radio and Cast files, and a failure costs nothing."""

from __future__ import annotations

from pathlib import Path

from quill.core.lineups import cast_queue, ops
from quill.core.lineups.describe import refresh_sentence, row_text, why_text
from quill.core.lineups.merge import refresh
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import (
    KIND_EPISODE,
    KIND_LOCAL,
    KIND_PLACE,
    KIND_SHOW,
    KIND_STATION,
    KIND_YT_VIDEO,
    Presence,
    episode_ref,
)
from quill.core.lineups.rules import KEEP_UNTIL_DONE, Keep, Rule
from quill.core.lineups.sources import build_catalogue, station_facts, youtube_ref
from quill.core.lineups.store import LineupStore
from quill.core.podcasts.models import PodcastShow, QueueItem
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.models_playlists import Playlist
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library
from quill.core.radio import favorites
from quill.core.radio.local_media import LocalMediaLibrary, MediaItem
from quill.core.radio.local_media import Playlist as MediaPlaylist
from quill.core.radio.local_media import save_library as save_media
from quill.core.radio.models import RadioStation

NOW = 1_800_000_000.0


def _cast(tmp_path: Path) -> PodcastLibrary:
    show = PodcastShow(
        id="daily",
        title="The Daily",
        episodes=[
            PodcastEpisode(
                guid="e1", title="Monday", audio_url="http://x/1", duration_seconds=1800
            ),
            PodcastEpisode(guid="e2", title="Tuesday", audio_url="http://x/2", played=True),
        ],
    )
    library = PodcastLibrary(shows=[show])
    save_library(tmp_path, library)
    return library


def _radio(tmp_path: Path) -> None:
    store = favorites.RadioFavoritesStore()
    store.favorites.append(
        favorites.FavoriteStation(
            RadioStation(name="BBC Radio 4", stream_url="http://bbc", station_uuid="u4"),
            folder="Morning",
        )
    )
    store.favorites.append(
        favorites.FavoriteStation(favorites.place_station("rbgenre:jazz", "Jazz"))
    )
    favorites.save_favorites(tmp_path, store)
    media = LocalMediaLibrary(
        playlists=[
            MediaPlaylist(
                id="p1",
                name="Talks",
                items=[MediaItem(id=1, path="C:/a.mp3", title="A talk", duration_seconds=600)],
            )
        ]
    )
    save_media(media, tmp_path)


def test_every_store_becomes_facts_with_the_right_completeness(tmp_path: Path) -> None:
    _cast(tmp_path)
    _radio(tmp_path)
    catalogue = build_catalogue(tmp_path, now=NOW)
    episodes = {item.name: item for item in catalogue.items[KIND_EPISODE] or ()}
    assert (
        episodes["Monday"].length_seconds == 1800 and episodes["Monday"].fact("show") == "The Daily"
    )
    assert episodes["Tuesday"].finished
    assert [i.name for i in catalogue.items[KIND_SHOW] or ()] == ["The Daily"]
    stations = catalogue.items[KIND_STATION] or ()
    assert stations[0].fact("folder") == "Morning" and stations[0].fact("favorite") is True
    assert [i.name for i in catalogue.items[KIND_PLACE] or ()] == ["Jazz"]
    assert [i.name for i in catalogue.items[KIND_LOCAL] or ()] == ["A talk"]
    # Episodes are listed in full; stations are not.
    assert catalogue.lookup(episode_ref("daily", "gone"))[0] is Presence.MISSING
    assert (
        catalogue.lookup(station_facts(RadioStation(name="x", stream_url="http://new")).ref)[0]
        is Presence.UNLISTED
    )


def test_an_unreadable_store_makes_only_its_kinds_unavailable(tmp_path: Path) -> None:
    _radio(tmp_path)
    (tmp_path / "podcasts_library.json").write_text("{broken", encoding="utf-8")
    catalogue = build_catalogue(tmp_path, now=NOW)
    assert not catalogue.available(KIND_EPISODE)
    assert catalogue.available(KIND_STATION)


def test_a_youtube_link_is_one_reference_however_it_was_written() -> None:
    a = youtube_ref("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10")
    b = youtube_ref("https://youtu.be/dQw4w9WgXcQ")
    assert a is not None and a.kind == KIND_YT_VIDEO and a == b
    assert youtube_ref("http://example.com/stream") is None


def test_an_end_to_end_refresh_reads_well(tmp_path: Path) -> None:
    _cast(tmp_path)
    rule = Rule(id="r1", kind=KIND_EPISODE, keep=Keep(KEEP_UNTIL_DONE))
    result = refresh(
        Lineup(id="l", name="Morning", rules=(rule,)), build_catalogue(tmp_path, now=NOW), NOW
    )
    assert [row.name for row in result.lineup.rows] == ["Monday"]  # Tuesday is already heard
    assert refresh_sentence(result) == "1 added."
    row = result.lineup.rows[0]
    presence, facts = build_catalogue(tmp_path, now=NOW).lookup(row.ref)
    assert row_text(row, facts, presence) == "Monday, episode, 30 minutes, The Daily"
    assert why_text(result.lineup, row, facts, now=NOW).startswith(
        "In Morning because rule 1 found it"
    )


# -- Cast's Play Queue ------------------------------------------------------------------


def test_save_queue_then_apply_to_queue(tmp_path: Path) -> None:
    library = _cast(tmp_path)
    library.queue = [QueueItem("daily", "e1"), QueueItem("daily", "e2")]
    store = LineupStore(tmp_path)
    _book, outcome = store.update(cast_queue.save_queue(library, "Tuesday"))
    lineup = store.load().find(outcome.lineup_id)
    assert lineup is not None and [row.name for row in lineup.rows] == ["Monday", "Tuesday"]
    library.queue = []
    counted = cast_queue.apply_to_queue(library, lineup)
    assert counted.done == 1 and counted.skipped == 1  # Tuesday is played
    assert [(q.show_id, q.episode_guid) for q in library.queue] == [("daily", "e1")]
    # Saving again under the same name replaces, never duplicates.
    library.queue = [QueueItem("daily", "e2")]
    store.update(cast_queue.save_queue(library, "tuesday"))
    book = store.load()
    assert len(book.lineups) == 1 and [r.name for r in book.lineups[0].rows] == ["Tuesday"]


def test_old_queue_snapshots_are_copied_in_once_and_left_in_place(tmp_path: Path) -> None:
    library = _cast(tmp_path)
    library.add_playlist(
        Playlist(
            id="lineup-1-tuesday", name="Tuesday", kind="manual", items=[QueueItem("daily", "e1")]
        )
    )
    library.add_playlist(Playlist(id="pl-other", name="Other playlist", kind="manual"))
    save_library(tmp_path, library)
    store = LineupStore(tmp_path)
    store.update(cast_queue.import_queue_snapshots(load_library(tmp_path)))
    book = store.load()
    assert [lineup.name for lineup in book.lineups] == ["Tuesday"]
    store.update(ops.delete_lineup(book.lineups[0].id))
    store.update(cast_queue.import_queue_snapshots(load_library(tmp_path)))
    assert store.load().lineups == ()  # deleted stays deleted
    assert [p.id for p in load_library(tmp_path).playlists] == ["lineup-1-tuesday", "pl-other"]
