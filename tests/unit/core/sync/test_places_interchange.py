"""Cast's half of Listening Places: a place that follows you to another app.

The worked example from the proposal is the shape of the main test: the phone
is at 40:12, the desktop reaches 52:00, and the phone picks the desktop's place
up on its next read. Here Cast is the desktop, and the "phone" is any app that
writes the published format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quill.core.podcasts import position_sync
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.sync import listening_places as lp
from quill.core.sync.places_interchange import sync_interchange


def _library() -> PodcastLibrary:
    show = PodcastShow(
        id="show-1", title="Blind Abilities", feed_url="https://feeds.example.com/ba"
    )
    show.episodes = [
        PodcastEpisode(
            guid="tag:example.com,2026:ep214",
            title="Episode 214",
            audio_url="https://cdn.example.com/ep214.mp3",
            duration_seconds=3894,
        ),
        PodcastEpisode(
            guid="tag:example.com,2026:ep215",
            title="Episode 215",
            audio_url="https://cdn.example.com/ep215.mp3",
            duration_seconds=1800,
        ),
    ]
    library = PodcastLibrary()
    library.shows = [show]
    return library


def _phone_file(root: Path, *, position_ms: int, updated_at: str, guid: str) -> None:
    folder = lp.devices_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "1f4c8a2e.json").write_text(
        json.dumps({
            "format": lp.FORMAT_ID,
            "device": "1f4c8a2e",
            "device_label": "Jeff's iPhone",
            "app": "earshot/1.0.3",
            "written_at": updated_at,
            "records": [
                {
                    "id": lp.episode_id(guid),
                    "kind": "episode",
                    "position_ms": position_ms,
                    "duration_ms": 3_894_000,
                    "played": False,
                    "updated_at": updated_at,
                    "label": "Blind Abilities: Episode 214",
                }
            ],
        }),
        encoding="utf-8",
    )


# -- the adapter -------------------------------------------------------------


def test_an_episode_nobody_has_started_is_not_a_place() -> None:
    """Tens of thousands of rows describing nothing is not a sync payload."""
    assert position_sync.collect_records(_library()) == []


def test_a_started_episode_becomes_a_record() -> None:
    library = _library()
    episode = library.shows[0].episodes[0]
    position_sync.remember_position(episode, 2_412_000)
    records = position_sync.collect_records(library)
    assert len(records) == 1
    assert records[0].id == lp.episode_id("tag:example.com,2026:ep214")
    assert records[0].position_ms == 2_412_000
    assert records[0].duration_ms == 3_894_000
    assert records[0].label == "Blind Abilities: Episode 214"
    assert records[0].updated_at.endswith("Z")


def test_finishing_is_played_with_the_position_cleared() -> None:
    """played true with position 0 is how "I finished it" is said."""
    library = _library()
    episode = library.shows[0].episodes[0]
    position_sync.mark_played(episode)
    record = position_sync.collect_records(library)[0]
    assert record.played is True
    assert record.position_ms == 0


def test_a_label_can_be_withheld() -> None:
    library = _library()
    position_sync.remember_position(library.shows[0].episodes[0], 1000)
    assert position_sync.collect_records(library, include_labels=False)[0].label == ""


def test_an_older_record_does_not_overwrite_a_newer_place() -> None:
    library = _library()
    episode = library.shows[0].episodes[0]
    position_sync.remember_position(episode, 3_120_000)
    episode.position_updated_at = "2026-08-20T15:30:44Z"
    stale = lp.PlaceRecord(
        id=lp.episode_id(episode.guid),
        position_ms=2_412_000,
        updated_at="2026-08-20T13:58:02Z",
    )
    assert position_sync.apply_record(library, stale) is False
    assert episode.position_ms == 3_120_000


def test_an_episode_this_machine_has_never_seen_is_not_an_error() -> None:
    unknown = lp.PlaceRecord(
        id="episode:ffffffffffffffff", position_ms=5, updated_at="2026-01-01T00:00:00Z"
    )
    assert position_sync.apply_record(_library(), unknown) is False


def test_the_timestamp_survives_a_save_and_reload() -> None:
    library = _library()
    episode = library.shows[0].episodes[0]
    position_sync.remember_position(episode, 12_345)
    reloaded = PodcastEpisode.from_dict(episode.to_dict())
    assert reloaded is not None
    assert reloaded.position_updated_at == episode.position_updated_at
    # An episode saved before this field existed simply has no timestamp yet.
    older = PodcastEpisode.from_dict({
        "guid": "g",
        "title": "t",
        "audio_url": "https://a",
        "position_ms": 10,
    })
    assert older is not None
    assert older.position_updated_at == ""


# -- one whole pass ----------------------------------------------------------


def test_the_worked_example(tmp_path: Path) -> None:
    """The phone reached 40:12; this machine is behind and picks it up."""
    remote = tmp_path / "Dropbox"
    remote.mkdir()
    _phone_file(
        remote,
        position_ms=2_412_000,
        updated_at="2026-08-20T13:58:02Z",
        guid="tag:example.com,2026:ep214",
    )
    library = _library()
    saved: list[Any] = []

    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="9b30d7f1",
        device_label="Studio PC",
        library=library,
        save_library=saved.append,
    )

    assert report.applied == 1
    assert library.shows[0].episodes[0].position_ms == 2_412_000
    assert saved == [library]
    # And this device now has its own file, which the phone will read next.
    mine = json.loads((lp.devices_dir(remote) / "9b30d7f1.json").read_text(encoding="utf-8"))
    assert mine["device_label"] == "Studio PC"
    assert mine["app"].startswith("quill-cast")
    assert mine["records"][0]["position_ms"] == 2_412_000
    assert "brought back 1 place" in report.summary()


def test_this_machine_being_ahead_changes_nothing_here(tmp_path: Path) -> None:
    remote = tmp_path / "Dropbox"
    remote.mkdir()
    _phone_file(
        remote,
        position_ms=2_412_000,
        updated_at="2026-08-20T13:58:02Z",
        guid="tag:example.com,2026:ep214",
    )
    library = _library()
    episode = library.shows[0].episodes[0]
    position_sync.remember_position(episode, 3_120_000)
    episode.position_updated_at = "2026-08-20T15:30:44Z"

    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="9b30d7f1",
        device_label="Studio PC",
        library=library,
        save_library=lambda _library: None,
    )
    assert report.applied == 0
    assert episode.position_ms == 3_120_000
    # It still shares its own newer place, which is the whole point.
    assert report.written is True


def test_a_second_pass_writes_nothing_when_nothing_moved(tmp_path: Path) -> None:
    remote = tmp_path / "Dropbox"
    remote.mkdir()
    library = _library()
    position_sync.remember_position(library.shows[0].episodes[0], 600_000)
    kwargs: dict[str, Any] = {
        "data_dir": tmp_path / "data",
        "remote_dir": remote,
        "device_id": "9b30d7f1",
        "device_label": "Studio PC",
        "library": library,
        "save_library": lambda _library: None,
    }
    assert sync_interchange(**kwargs).written is True
    second = sync_interchange(**kwargs)
    assert second.written is False
    assert second.summary() == "Everything was already up to date."


def test_a_folder_that_has_gone_missing_says_so(tmp_path: Path) -> None:
    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=tmp_path / "not-mounted",
        device_id="9b30d7f1",
        device_label="Studio PC",
        library=_library(),
        save_library=lambda _library: None,
    )
    assert report.applied == 0
    assert report.written is False
    assert "not there" in report.summary()
    assert "still saved on this device" in report.summary()


def test_a_disagreement_is_reported_in_words(tmp_path: Path) -> None:
    remote = tmp_path / "Dropbox"
    remote.mkdir()
    _phone_file(
        remote,
        position_ms=3_120_000,
        updated_at="2026-08-20T15:30:44Z",
        guid="tag:example.com,2026:ep214",
    )
    library = _library()
    episode = library.shows[0].episodes[0]
    position_sync.remember_position(episode, 2_412_000)
    episode.position_updated_at = "2026-08-20T13:58:02Z"

    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="9b30d7f1",
        device_label="Studio PC",
        library=library,
        save_library=lambda _library: None,
    )
    assert len(report.disagreements) == 1
    assert "disagreed between devices" in report.summary()
    assert "40 minutes" in report.disagreements[0].spoken()
