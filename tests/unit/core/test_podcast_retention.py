"""Tests for podcast episode retention policies (pure; a real temp file
stands in for a downloaded episode)."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.retention import apply_delete_after_play, apply_keep_last_n


def _downloaded_episode(tmp_path: Path, name: str, *, published: str) -> PodcastEpisode:
    path = tmp_path / name
    path.write_bytes(b"audio")
    return PodcastEpisode(
        guid=name,
        title=name,
        audio_url=f"https://x/{name}",
        published=published,
        downloaded_path=str(path),
    )


def test_apply_keep_last_n_noop_when_not_that_policy(tmp_path: Path) -> None:
    episode = _downloaded_episode(tmp_path, "e1.mp3", published="2026-07-01")
    show = PodcastShow(id="s1", title="Show", episodes=[episode])
    settings = PodcastSettings(retention="keep_all")
    assert apply_keep_last_n(show, settings) == []
    assert episode.downloaded_path


def test_apply_keep_last_n_noop_when_under_the_limit(tmp_path: Path) -> None:
    episode = _downloaded_episode(tmp_path, "e1.mp3", published="2026-07-01")
    show = PodcastShow(id="s1", title="Show", episodes=[episode])
    settings = PodcastSettings(retention="keep_last_n", retention_count=5)
    assert apply_keep_last_n(show, settings) == []
    assert episode.downloaded_path


def test_apply_keep_last_n_prunes_oldest_beyond_the_count(tmp_path: Path) -> None:
    newest = _downloaded_episode(tmp_path, "new.mp3", published="2026-07-10")
    middle = _downloaded_episode(tmp_path, "mid.mp3", published="2026-07-05")
    oldest = _downloaded_episode(tmp_path, "old.mp3", published="2026-07-01")
    show = PodcastShow(id="s1", title="Show", episodes=[newest, middle, oldest])
    settings = PodcastSettings(retention="keep_last_n", retention_count=2)

    pruned = apply_keep_last_n(show, settings)

    assert pruned == [oldest]
    assert oldest.downloaded_path == ""
    assert not Path(f"{tmp_path}/old.mp3").exists()
    assert newest.downloaded_path and middle.downloaded_path


def test_apply_keep_last_n_ignores_episodes_without_a_downloaded_file(tmp_path: Path) -> None:
    downloaded = _downloaded_episode(tmp_path, "e1.mp3", published="2026-07-01")
    not_downloaded = PodcastEpisode(
        guid="e2", title="e2", audio_url="https://x/e2.mp3", published="2026-07-02"
    )
    show = PodcastShow(id="s1", title="Show", episodes=[downloaded, not_downloaded])
    settings = PodcastSettings(retention="keep_last_n", retention_count=0)

    pruned = apply_keep_last_n(show, settings)

    assert pruned == [downloaded]


def test_apply_delete_after_play_removes_file_and_clears_path(tmp_path: Path) -> None:
    episode = _downloaded_episode(tmp_path, "e1.mp3", published="2026-07-01")
    settings = PodcastSettings(retention="delete_after_play")

    assert apply_delete_after_play(episode, settings) is True
    assert episode.downloaded_path == ""
    assert not (tmp_path / "e1.mp3").exists()


def test_apply_delete_after_play_noop_when_not_that_policy(tmp_path: Path) -> None:
    episode = _downloaded_episode(tmp_path, "e1.mp3", published="2026-07-01")
    settings = PodcastSettings(retention="keep_all")

    assert apply_delete_after_play(episode, settings) is False
    assert episode.downloaded_path


def test_apply_delete_after_play_noop_without_a_downloaded_file() -> None:
    episode = PodcastEpisode(guid="e1", title="e1", audio_url="https://x/e1.mp3")
    settings = PodcastSettings(retention="delete_after_play")

    assert apply_delete_after_play(episode, settings) is False
