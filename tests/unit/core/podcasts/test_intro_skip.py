"""Skip the intro on a first play, and never again (ear.md R20).

It used to fire on every start, which is wrong in the one case a listener
notices: you press Previous to hear the beginning again, and the app helpfully
skips the part you deliberately came back for.
"""

from __future__ import annotations

from quill.core.podcasts.intro_skip import START_TOLERANCE_MS, mark_skipped, skip_ms_for
from quill.core.podcasts.models import PodcastEpisode, PodcastSettings


def _episode(**kwargs) -> PodcastEpisode:
    return PodcastEpisode(
        guid="e1",
        title="Episode",
        audio_url="https://e/1.mp3",
        published="2026-07-01T00:00:00",
        **kwargs,
    )


def _settings(seconds: int = 30) -> PodcastSettings:
    return PodcastSettings(auto_skip_intro_seconds=seconds)


def test_a_first_play_from_zero_skips() -> None:
    assert skip_ms_for(_settings(30), _episode(), 0) == 30_000


def test_no_skip_is_configured_means_no_skip() -> None:
    assert skip_ms_for(_settings(0), _episode(), 0) == 0


def test_a_resume_does_not_skip() -> None:
    """The listener is already past the intro; jumping again loses content."""
    assert skip_ms_for(_settings(30), _episode(), 600_000) == 0


def test_a_stop_during_the_opening_bars_still_counts_as_the_beginning() -> None:
    """Otherwise the skip would never fire for anybody who stopped early once."""
    assert skip_ms_for(_settings(30), _episode(), START_TOLERANCE_MS - 1) == 30_000
    assert skip_ms_for(_settings(30), _episode(), START_TOLERANCE_MS + 1) == 0


def test_an_episode_already_skipped_is_not_skipped_again() -> None:
    """The R20 rule: a replay from the start plays the intro."""
    episode = _episode()
    mark_skipped(episode)
    assert skip_ms_for(_settings(30), episode, 0) == 0


def test_skipped_is_a_separate_fact_from_played() -> None:
    """Unplayed and already intro-skipped is the "started it, went back" case."""
    episode = _episode()
    mark_skipped(episode)
    assert episode.intro_skipped is True
    assert episode.played is False


def test_the_flag_survives_a_save_and_a_load() -> None:
    """An intro skipped last night must not be skipped again this morning."""
    episode = _episode()
    mark_skipped(episode)
    restored = PodcastEpisode.from_dict(episode.to_dict())
    assert restored.intro_skipped is True
    assert skip_ms_for(_settings(30), restored, 0) == 0


def test_an_episode_written_before_the_flag_existed_loads_as_not_skipped() -> None:
    data = _episode().to_dict()
    data.pop("intro_skipped", None)
    assert PodcastEpisode.from_dict(data).intro_skipped is False
