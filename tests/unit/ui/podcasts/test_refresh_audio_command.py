"""Earshot R3 on the episode menu: the file is fetched again, the listening kept."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.ui.podcasts import refresh_audio_command


def _host(tmp_path: Path, queued: list) -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(
        _announce=said.append,
        said=said,
        _save_podcast_library=lambda: None,
        _podcast_download_queue=SimpleNamespace(),
        _podcast_download_root=lambda: tmp_path,
        _podcast_library=None,
    )


def test_a_moved_episode_is_fetched_again_and_keeps_its_place(tmp_path: Path, monkeypatch) -> None:
    queued: list[str] = []
    monkeypatch.setattr(
        "quill.ui.podcasts.show_actions.enqueue_episode_download",
        lambda _q, _root, _show, episode, **_k: queued.append(episode.audio_url),
    )
    old_file = tmp_path / "old.mp3"
    old_file.write_bytes(b"x")
    show = PodcastShow(id="s", title="Show", feed_url="https://feed.example/rss")
    episode = PodcastEpisode(
        guid="g", title="Ep", audio_url="https://old.example/a.mp3", position_ms=90_000
    )
    episode.downloaded_path = str(old_file)
    host = _host(tmp_path, queued)
    assert refresh_audio_command.finish(host, show, episode, "https://new.example/a.mp3", ask=False)
    assert queued == ["https://new.example/a.mp3"]
    assert episode.position_ms == 90_000 and episode.downloaded_path == ""
    assert not old_file.exists()
    assert host.said[-1] == "Downloading Ep from its new address."


def test_an_episode_the_feed_dropped_is_left_alone(tmp_path: Path) -> None:
    show = PodcastShow(id="s", title="Show", feed_url="https://feed.example/rss")
    episode = PodcastEpisode(guid="g", title="Ep", audio_url="https://old.example/a.mp3")
    host = _host(tmp_path, [])
    assert not refresh_audio_command.finish(host, show, episode, "", ask=False)
    assert "no longer lists Ep" in host.said[-1]
