"""Disposable reference checks for manual Cast Listening Places sync and Play."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library
from quill.core.sync import listening_places as lp
from quill.core.sync.places_config import PlacesConfig
from quill.ui import sync_places_command
from quill.ui.podcasts.player_controller import PodcastPlayerState
from quill.ui.podcasts.show_actions import start_episode_playback

GUID = "synthetic-public-episode-189"
STAMP = "2026-11-26T22:40:00Z"


class CaptureController:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def play_episode(self, **kwargs: object) -> None:
        self.calls.append(kwargs)

    def set_volume_boost(self, value: object) -> None:
        pass


def setup(
    tmp_path: Path, monkeypatch: object, *, state: PodcastPlayerState = PodcastPlayerState.STOPPED
):
    from quill.core import paths
    from quill.core.podcasts import playback_cache

    data = tmp_path / "cast-data"
    remote = tmp_path / "shared"
    data.mkdir()
    remote.mkdir()
    monkeypatch.setattr(paths, "app_data_dir", lambda: data)
    monkeypatch.setattr(sync_places_command, "app_data_dir", lambda: data)
    monkeypatch.setattr(playback_cache, "cached_audio", lambda *_a, **_k: None)
    show = PodcastShow(
        id="synthetic-public-show",
        title="Synthetic Public Show",
        feed_url="https://example.com/synthetic.xml",
    )
    show.episodes = [
        PodcastEpisode(
            guid=GUID,
            title="Synthetic episode 189",
            audio_url="https://example.com/synthetic-189.mp3",
            duration_seconds=1800,
        )
    ]
    library = PodcastLibrary()
    library.shows = [show]
    save_library(data, library)
    host = SimpleNamespace(
        _startup_app_id="cast",
        _podcast_library=load_library(data),
        _podcast_controller=SimpleNamespace(state=SimpleNamespace(state=state)),
    )
    folder = lp.devices_dir(remote)
    folder.mkdir(parents=True)
    (folder / "1f4c8a2e.json").write_text(
        json.dumps({
            "format": lp.FORMAT_ID,
            "device": "1f4c8a2e",
            "device_label": "Synthetic phone",
            "app": "earshot/trial",
            "written_at": STAMP,
            "records": [
                {
                    "id": lp.episode_id(GUID),
                    "kind": "episode",
                    "position_ms": 44_000,
                    "duration_ms": 1_800_000,
                    "played": False,
                    "updated_at": STAMP,
                }
            ],
        })
    )
    config = PlacesConfig(
        enabled=True,
        remote_dir=str(remote),
        device="Synthetic desktop",
        encrypted=False,
        interchange=True,
        device_id="9b30d7f1",
    )
    return host, config, data, remote


def normal_play(library: PodcastLibrary) -> int:
    controller = CaptureController()
    show = library.shows[0]
    assert start_episode_playback(controller, library, show, show.episodes[0])
    return int(controller.calls[0]["resume_ms"])


def test_manual_sync_updates_open_play_and_keeps_peer_clock(
    tmp_path: Path, monkeypatch: object
) -> None:
    host, config, data, remote = setup(tmp_path, monkeypatch)
    assert "brought back 1 place" in sync_places_command.sync_now_with_open_library(
        host, config, ""
    )
    assert normal_play(host._podcast_library) == 44_000
    assert normal_play(load_library(data)) == 44_000
    owned = json.loads((lp.devices_dir(remote) / "9b30d7f1.json").read_text())
    assert owned["records"][0]["position_ms"] == 44_000
    assert owned["records"][0]["updated_at"] == STAMP


def test_manual_sync_refuses_loaded_player_without_touching_disk(
    tmp_path: Path, monkeypatch: object
) -> None:
    host, config, data, remote = setup(tmp_path, monkeypatch, state=PodcastPlayerState.PAUSED)
    assert "Stop the loaded episode" in sync_places_command.sync_now_with_open_library(
        host, config, ""
    )
    assert host._podcast_library.shows[0].episodes[0].position_ms == 0
    assert load_library(data).shows[0].episodes[0].position_ms == 0
    assert not (lp.devices_dir(remote) / "9b30d7f1.json").exists()


def test_manual_sync_refuses_error_state_with_loaded_episode(
    tmp_path: Path, monkeypatch: object
) -> None:
    host, config, data, remote = setup(tmp_path, monkeypatch, state=PodcastPlayerState.ERROR)
    host._podcast_controller.state.episode_guid = GUID
    assert "Stop the loaded episode" in sync_places_command.sync_now_with_open_library(
        host, config, ""
    )
    assert load_library(data).shows[0].episodes[0].position_ms == 0
    assert not (lp.devices_dir(remote) / "9b30d7f1.json").exists()


def test_manual_sync_refuses_unsaved_local_change(tmp_path: Path, monkeypatch: object) -> None:
    host, config, data, remote = setup(tmp_path, monkeypatch)
    host._podcast_library.shows[0].title = "Unsaved local title"
    assert "unsaved changes" in sync_places_command.sync_now_with_open_library(host, config, "")
    assert host._podcast_library.shows[0].title == "Unsaved local title"
    assert load_library(data).shows[0].title == "Synthetic Public Show"
    assert not (lp.devices_dir(remote) / "9b30d7f1.json").exists()


def test_manual_sync_does_not_overwrite_a_local_change_during_sync(
    tmp_path: Path, monkeypatch: object
) -> None:
    host, config, data, _remote = setup(tmp_path, monkeypatch)
    actual = sync_places_command.sync_once

    def concurrent_choice(cfg: PlacesConfig, phrase: str) -> str:
        result = actual(cfg, phrase)
        host._podcast_library.shows[0].episodes[0].position_ms = 55_000
        return result

    monkeypatch.setattr(sync_places_command, "sync_once", concurrent_choice)
    sync_places_command.sync_now_with_open_library(host, config, "")
    assert host._podcast_library.shows[0].episodes[0].position_ms == 55_000
    assert load_library(data).shows[0].episodes[0].position_ms == 44_000


def test_other_apps_keep_original_sync_behavior(tmp_path: Path, monkeypatch: object) -> None:
    host, config, data, _remote = setup(tmp_path, monkeypatch)
    host._startup_app_id = "radio"
    assert "brought back 1 place" in sync_places_command.sync_now_with_open_library(
        host, config, ""
    )
    assert host._podcast_library.shows[0].episodes[0].position_ms == 0
    assert load_library(data).shows[0].episodes[0].position_ms == 44_000


def test_combined_sync_keeps_original_behavior(tmp_path: Path, monkeypatch: object) -> None:
    host, config, data, _remote = setup(tmp_path, monkeypatch)
    config.encrypted = True
    host._podcast_controller.state.state = PodcastPlayerState.PAUSED
    monkeypatch.setattr(sync_places_command, "sync_once", lambda *_args: "Combined sync ran")
    assert sync_places_command.sync_now_with_open_library(host, config, "") == "Combined sync ran"
    assert load_library(data).shows[0].episodes[0].position_ms == 0
