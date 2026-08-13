"""Unit tests for the playback cache -- the removal of the two-tier episode.

The point of this module is that a streamed episode stops being second class,
so the tests are mostly about the three things that only work once the bytes
are local: the fallback file after a drop, promotion without a second
download, and an audio path the analysis tiers can use.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.core.podcasts import playback_cache
from quill.core.podcasts.models import PodcastSettings


@dataclass
class _Episode:
    guid: str = "ep-1"
    audio_url: str = "https://example.test/show/ep1.mp3"
    downloaded_path: str = ""


@dataclass
class _Show:
    id: str = "show-1"
    episodes: list[_Episode] = field(default_factory=list)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the cache at a scratch directory, never the real app data dir."""
    root = tmp_path / "cache"
    monkeypatch.setattr(playback_cache, "cache_root", lambda: root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, size: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


# -- naming ------------------------------------------------------------------


def test_path_keeps_a_known_extension() -> None:
    path = playback_cache.playback_path("s", "g", "https://x.test/a/b.m4a?token=1")
    assert path.suffix == ".m4a"


def test_unknown_extension_becomes_audio() -> None:
    path = playback_cache.playback_path("s", "g", "https://x.test/stream?id=7")
    assert path.suffix == ".audio"


def test_key_is_show_and_guid_not_url() -> None:
    """A feed that moves its enclosures must not orphan every cached file."""
    first = playback_cache.playback_path("s", "g", "https://old.test/a.mp3")
    second = playback_cache.playback_path("s", "g", "https://new.test/b.mp3")
    assert first == second


def test_different_episodes_get_different_files() -> None:
    assert playback_cache.playback_path("s", "one") != playback_cache.playback_path("s", "two")


# -- what is available -------------------------------------------------------


def test_partial_is_not_offered_as_complete() -> None:
    """A chapter scan over two-thirds of a programme is worse than none."""
    _write(playback_cache.partial_path("s", "g"), 100)
    assert playback_cache.cached_audio("s", "g") is None


def test_partial_is_offered_for_recovery() -> None:
    """The same bytes that are not a whole episode are still playable audio."""
    _write(playback_cache.partial_path("s", "g"), 100)
    path, size, complete = playback_cache.cached_bytes("s", "g")
    assert path is not None
    assert (size, complete) == (100, False)


def test_finalize_makes_it_complete() -> None:
    _write(playback_cache.partial_path("s", "g"), 100)
    final = playback_cache.finalize("s", "g")
    assert final is not None
    assert playback_cache.cached_audio("s", "g") == final
    assert not playback_cache.partial_path("s", "g").exists()


def test_finalize_with_nothing_to_do() -> None:
    assert playback_cache.finalize("s", "g") is None


def test_empty_file_is_not_cached_audio() -> None:
    _write(playback_cache.playback_path("s", "g"), 0)
    assert playback_cache.cached_audio("s", "g") is None


# -- local_audio_path: the resolver every byte-hungry caller uses -------------


def test_download_wins_over_cache(tmp_path: Path) -> None:
    downloaded = _write(tmp_path / "downloads" / "ep1.mp3", 10)
    _write(playback_cache.playback_path("show-1", "ep-1"), 10)
    episode = _Episode(downloaded_path=str(downloaded))
    assert playback_cache.local_audio_path(_Show(), episode) == downloaded


def test_cache_answers_for_a_streamed_episode() -> None:
    cached = _write(
        playback_cache.playback_path("show-1", "ep-1", "https://example.test/show/ep1.mp3"), 10
    )
    assert playback_cache.local_audio_path(_Show(), _Episode()) == cached


def test_nothing_local_is_none() -> None:
    assert playback_cache.local_audio_path(_Show(), _Episode()) is None


def test_a_download_that_vanished_is_none(tmp_path: Path) -> None:
    """A stale downloaded_path must not be handed to ffmpeg."""
    episode = _Episode(downloaded_path=str(tmp_path / "gone.mp3"))
    assert playback_cache.local_audio_path(_Show(), episode) is None


# -- eviction ----------------------------------------------------------------


def test_eviction_removes_least_recently_used() -> None:
    old = _write(playback_cache.playback_path("s", "old"), 600)
    new = _write(playback_cache.playback_path("s", "new"), 600)
    os.utime(old, (1_000_000, 1_000_000))
    os.utime(new, (2_000_000, 2_000_000))
    removed = playback_cache.evict_to_cap(1000)
    assert [entry.path for entry in removed] == [old]
    assert new.exists()


def test_what_is_playing_is_never_evicted() -> None:
    """Disk pressure is not a reason to stop the audio."""
    playing = _write(playback_cache.playback_path("s", "playing"), 900)
    other = _write(playback_cache.playback_path("s", "other"), 900)
    os.utime(playing, (1_000_000, 1_000_000))
    os.utime(other, (2_000_000, 2_000_000))
    removed = playback_cache.evict_to_cap(1000, keep=frozenset({playing}))
    assert [entry.path for entry in removed] == [other]
    assert playing.exists()


def test_an_unreachable_cap_evicts_what_it_can_and_stops() -> None:
    playing = _write(playback_cache.playback_path("s", "playing"), 900)
    playback_cache.evict_to_cap(100, keep=frozenset({playing}))
    assert playing.exists()
    assert playback_cache.total_bytes() == 900


def test_no_cap_means_no_eviction() -> None:
    _write(playback_cache.playback_path("s", "a"), 5000)
    assert playback_cache.evict_to_cap(0) == []


def test_total_bytes_counts_partials_too() -> None:
    _write(playback_cache.playback_path("s", "a"), 10)
    _write(playback_cache.partial_path("s", "b"), 5)
    assert playback_cache.total_bytes() == 15


# -- promotion: "keep this one" costs nothing --------------------------------


def test_promote_moves_rather_than_copies(tmp_path: Path) -> None:
    source = _write(playback_cache.playback_path("s", "g"), 42)
    destination = tmp_path / "downloads" / "Show" / "Episode.mp3"
    assert playback_cache.promote("s", "g", "", destination) == destination
    assert destination.read_bytes() == b"x" * 42
    assert not source.exists()


def test_promote_without_a_complete_entry_declines(tmp_path: Path) -> None:
    """A half-filled cache must fall back to an ordinary download."""
    _write(playback_cache.partial_path("s", "g"), 42)
    assert playback_cache.promote("s", "g", "", tmp_path / "out.mp3") is None


# -- forget and clear --------------------------------------------------------


def test_forget_drops_both_halves() -> None:
    _write(playback_cache.playback_path("s", "g"), 10)
    _write(playback_cache.partial_path("s", "g"), 5)
    assert playback_cache.forget("s", "g") == 15
    assert playback_cache.total_bytes() == 0


def test_clear_spares_what_is_in_use() -> None:
    playing = _write(playback_cache.playback_path("s", "playing"), 10)
    _write(playback_cache.playback_path("s", "other"), 20)
    assert playback_cache.clear(keep=frozenset({playing})) == 20
    assert playing.exists()


def test_is_cache_path_distinguishes_a_download(tmp_path: Path) -> None:
    cached = _write(playback_cache.playback_path("s", "g"), 1)
    downloaded = _write(tmp_path / "downloads" / "ep.mp3", 1)
    assert playback_cache.is_cache_path(cached)
    assert not playback_cache.is_cache_path(downloaded)


# -- the settings that drive it ----------------------------------------------


def test_caching_is_on_by_default_with_a_bounded_cap() -> None:
    settings = PodcastSettings()
    assert settings.playback_cache is True
    assert settings.playback_cache_cap_mb == playback_cache.DEFAULT_CAP_MB


def test_settings_round_trip() -> None:
    settings = PodcastSettings(playback_cache=False, playback_cache_cap_mb=256)
    restored = PodcastSettings.from_dict(settings.to_dict())
    assert restored.playback_cache is False
    assert restored.playback_cache_cap_mb == 256


def test_a_library_written_before_this_shipped_gets_the_default() -> None:
    restored = PodcastSettings.from_dict({"speed": 1.5})
    assert restored.playback_cache is True
    assert restored.playback_cache_cap_mb == 1024
