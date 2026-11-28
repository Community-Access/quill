"""Resume rewind and natural Queue peer lookup through Cast's playback entry point."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from time import monotonic
from types import SimpleNamespace
from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.sync import listening_places as places
from quill.core.sync.places_config import PlacesConfig
from quill.ui.podcasts import queue_synced_place, show_actions


class Controller:
    def __init__(self) -> None:
        self.starts: list[dict[str, Any]] = []

    def play_episode(self, **kwargs: Any) -> None:
        self.starts.append(kwargs)


def _episode() -> tuple[PodcastLibrary, PodcastShow, PodcastEpisode]:
    library = PodcastLibrary()
    show = PodcastShow(id="s", title="Public", feed_url="https://example.org/feed")
    episode = PodcastEpisode(guid="episode-1", title="One", audio_url="https://example.org/one.mp3")
    show.episodes = [episode]
    library.shows = [show]
    return library, show, episode


def test_resume_rewind_defaults_to_exact_and_does_not_change_saved_event(
    monkeypatch: Any,
) -> None:
    library, show, episode = _episode()
    episode.position_ms = 414_000
    episode.position_updated_at = "2026-11-28T01:00:00Z"
    monkeypatch.setattr(show_actions, "_apply_volume_boost", lambda *_a: None)
    controller = Controller()
    assert show_actions.start_episode_playback(controller, library, show, episode)
    assert controller.starts[-1]["resume_ms"] == 414_000
    library.settings.resume_rewind_seconds = 20
    assert show_actions.start_episode_playback(controller, library, show, episode)
    assert controller.starts[-1]["resume_ms"] == 394_000
    assert (episode.position_ms, episode.position_updated_at) == (414_000, "2026-11-28T01:00:00Z")
    assert show_actions.start_episode_playback(controller, library, show, episode, resume_ms=30_000)
    assert controller.starts[-1]["resume_ms"] == 30_000  # explicit seek
    assert show_actions.start_episode_playback(
        controller, library, show, episode, resume_ms=5_000, automatic_resume=True
    )
    assert controller.starts[-1]["resume_ms"] == 0


def test_setting_is_accessible_and_round_trips() -> None:
    from quill.core.podcasts.settings_catalog import for_level

    assert PodcastSettings.from_dict({}).resume_rewind_seconds == 0
    assert PodcastSettings.from_dict({"resume_rewind_seconds": 999}).resume_rewind_seconds == 300
    assert (
        PodcastSettings.from_dict(
            PodcastSettings(resume_rewind_seconds=15).to_dict()
        ).resume_rewind_seconds
        == 15
    )
    for level in ("global", "show"):
        setting = next(d for d in for_level(level) if d.id == "resume_rewind_seconds")
        assert "&" in setting.label and "saved place" in setting.help


def test_peer_lookup_uses_newest_valid_event_and_respects_consent(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from quill.core import paths
    from quill.core.sync import places_config

    library, show, episode = _episode()
    episode.position_ms = 40_000
    episode.position_updated_at = "2026-11-28T01:00:00Z"
    config = PlacesConfig(
        enabled=True,
        remote_dir=str(tmp_path),
        encrypted=False,
        interchange=True,
        device_id="desktop",
    )
    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(places_config, "load", lambda _path: config)
    host = SimpleNamespace(_startup_app_id="cast")

    def lookup() -> int | None:
        queue_synced_place.prefetch(host)
        if host._cast_queue_places is not None:
            assert host._cast_queue_places.ready.wait(1)
        return queue_synced_place.newest_queue_place(host, show, episode)

    folder = places.devices_dir(tmp_path)
    folder.mkdir(parents=True)
    for name, position, stamp in (
        ("older", 90_000, "2026-11-28T01:10:00Z"),
        ("newer", 20_000, "2026-11-28T01:20:00Z"),
    ):
        places.write_device_file(
            tmp_path,
            device_id=name,
            device_label=name,
            app="earshot/test",
            records=[
                places.PlaceRecord(
                    id=places.episode_id(episode.guid),
                    position_ms=position,
                    duration_ms=0,
                    played=False,
                    updated_at=stamp,
                )
            ],
        )
    assert lookup() == 20_000
    episode.position_updated_at = "2026-11-28T01:30:00Z"
    assert lookup() is None
    episode.position_updated_at = "2026-11-28T01:00:00Z"
    from quill.core.sync.subscriptions_sync import subscription_id

    config.local_only = [subscription_id(show.feed_url)]
    assert lookup() is None
    config.local_only = []
    config.encrypted = True
    assert lookup() is None
    config.encrypted = False
    config.share_subscriptions = True
    assert lookup() is None
    config.share_subscriptions = False
    show.feed_username = "private"
    assert lookup() is None


def test_unavailable_reader_falls_back_without_late_seek(monkeypatch: Any) -> None:
    entered, release = Event(), Event()

    def slow(_source: Any) -> dict[str, Any]:
        entered.set()
        release.wait(1)
        return {"episode:late": object()}

    monkeypatch.setattr(queue_synced_place, "_read", slow)
    monkeypatch.setattr(
        queue_synced_place,
        "_source",
        lambda: (
            queue_synced_place.Source("data", "shared", "desktop", "eligible"),
            PlacesConfig(),
        ),
    )
    host = SimpleNamespace(_startup_app_id="cast")
    before = monotonic()
    queue_synced_place.prefetch(host)
    assert monotonic() - before < 0.1
    assert entered.wait(1)
    pending = host._cast_queue_places
    queue_synced_place.prefetch(host)
    assert host._cast_queue_places is pending
    result = queue_synced_place.newest_queue_place(host, object(), object())
    assert result is None
    release.set()  # a completed late read has no callback into the player


def test_switching_folders_rejects_completed_a_and_applies_current_b(monkeypatch: Any) -> None:
    from quill.core import paths
    from quill.core.sync import places_config

    _library, show, episode = _episode()
    config = PlacesConfig(
        enabled=True, interchange=True, encrypted=False, remote_dir="folder-A", device_id="desktop"
    )
    monkeypatch.setattr(paths, "app_data_dir", lambda: Path("synthetic-data"))
    monkeypatch.setattr(places_config, "load", lambda _path: config)
    key = places.episode_id(episode.guid)

    def read(source: queue_synced_place.Source) -> dict[str, places.PlaceRecord]:
        position = 44_000 if source.remote_dir == "folder-A" else 88_000
        return {
            key: places.PlaceRecord(id=key, position_ms=position, updated_at="2026-11-28T01:00:00Z")
        }

    monkeypatch.setattr(queue_synced_place, "_read", read)
    host = SimpleNamespace(_startup_app_id="cast")
    queue_synced_place.prefetch(host)
    assert host._cast_queue_places.ready.wait(1)
    assert queue_synced_place.newest_queue_place(host, show, episode) == 44_000
    config.remote_dir = "folder-B"
    assert queue_synced_place.newest_queue_place(host, show, episode) is None
    assert host._cast_queue_places is None
    queue_synced_place.prefetch(host)
    assert host._cast_queue_places.ready.wait(1)
    assert queue_synced_place.newest_queue_place(host, show, episode) == 88_000
    config.device_id = "different-device"
    assert queue_synced_place.newest_queue_place(host, show, episode) is None
    assert host._cast_queue_places is None
    config.device_id = "desktop"
    assert queue_synced_place.newest_queue_place(host, show, episode) is None


def test_inflight_a_cannot_replace_b_after_switch(monkeypatch: Any) -> None:
    from quill.core import paths
    from quill.core.sync import places_config

    _library, show, episode = _episode()
    config = PlacesConfig(
        enabled=True, interchange=True, encrypted=False, remote_dir="folder-A", device_id="desktop"
    )
    monkeypatch.setattr(paths, "app_data_dir", lambda: Path("synthetic-data"))
    monkeypatch.setattr(places_config, "load", lambda _path: config)
    key = places.episode_id(episode.guid)
    entered_a, release_a = Event(), Event()

    def read(source: queue_synced_place.Source) -> dict[str, places.PlaceRecord]:
        if source.remote_dir == "folder-A":
            entered_a.set()
            release_a.wait(1)
        position = 44_000 if source.remote_dir == "folder-A" else 88_000
        return {
            key: places.PlaceRecord(id=key, position_ms=position, updated_at="2026-11-28T01:00:00Z")
        }

    monkeypatch.setattr(queue_synced_place, "_read", read)
    host = SimpleNamespace(_startup_app_id="cast")
    queue_synced_place.prefetch(host)
    assert entered_a.wait(1)
    old = host._cast_queue_places
    config.remote_dir = "folder-B"
    assert queue_synced_place.newest_queue_place(host, show, episode) is None
    queue_synced_place.prefetch(host)
    current = host._cast_queue_places
    assert current is not old and current.ready.wait(1)
    assert queue_synced_place.newest_queue_place(host, show, episode) == 88_000
    release_a.set()
    assert old.ready.wait(1)
    assert queue_synced_place.newest_queue_place(host, show, episode) == 88_000
    config.share_subscriptions = True
    assert queue_synced_place.newest_queue_place(host, show, episode) is None


def test_natural_queue_uses_peer_then_local_fallback(monkeypatch: Any) -> None:
    from quill.ui.podcasts.queue_advance import start_next

    library, show, episode = _episode()
    library.queue = [SimpleNamespace(show_id="s", episode_guid="episode-1")]
    host = SimpleNamespace(
        _startup_app_id="cast",
        _podcast_library=library,
        _podcast_controller=Controller(),
        _announce=lambda _text: None,
    )
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        show_actions, "start_episode_playback", lambda *_a, **kw: calls.append(kw) or True
    )
    monkeypatch.setattr(queue_synced_place, "newest_queue_place", lambda *_a: 60_000)
    assert start_next(host, show, episode, "Up next", from_queue=True)
    assert calls.pop() == {"resume_ms": 60_000, "automatic_resume": True}
    monkeypatch.setattr(queue_synced_place, "newest_queue_place", lambda *_a: None)
    assert start_next(host, show, episode, "Up next", from_queue=True)
    assert calls.pop() == {}
    monkeypatch.setattr(
        queue_synced_place,
        "newest_queue_place",
        lambda *_a: (_ for _ in ()).throw(OSError("cloud folder unavailable")),
    )
    assert start_next(host, show, episode, "Up next", from_queue=True)
    assert calls.pop() == {}
    assert start_next(host, show, episode, "Up next", from_queue=False)
    assert calls.pop() == {}


def test_manual_queue_skip_does_not_read_peer(monkeypatch: Any) -> None:
    from quill.core.podcasts import queue_steps
    from quill.ui.podcasts import queue_commands
    from quill.ui.podcasts.queue_commands import next_in_queue

    library, show, episode = _episode()
    host = SimpleNamespace(
        _startup_app_id="cast",
        _podcast_library=library,
        _podcast_controller=SimpleNamespace(
            state=SimpleNamespace(show_id="s", episode_guid="before")
        ),
        _save_podcast_library=lambda: None,
        _announce=lambda _text: None,
    )
    monkeypatch.setattr(
        queue_commands,
        "step_next",
        lambda *_a: queue_steps.Step(kind="play", show=show, episode=episode),
    )
    monkeypatch.setattr(
        queue_synced_place,
        "newest_queue_place",
        lambda *_a: (_ for _ in ()).throw(AssertionError("manual skip read peer")),
    )
    starts: list[dict[str, Any]] = []
    monkeypatch.setattr(show_actions, "start_episode_playback", lambda *_a, **kw: starts.append(kw))
    next_in_queue(host)
    assert starts == [{}]
