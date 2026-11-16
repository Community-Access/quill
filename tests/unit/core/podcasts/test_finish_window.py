"""How close to the end counts as finished (PodcastSettings.finished_within_seconds).

A listener's finished episodes sat in Continue Listening at 99 percent because
they had stopped during the closing credits (2026-11). Pure, no wx.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.finish_window import within_finish_window
from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.settings_catalog import for_level
from quill.core.podcasts.settings_types import LEVEL_GLOBAL, LEVEL_SHOW
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.podcasts.virtual_views import virtual_view_pairs

HOUR_MS = 3_600_000


@pytest.mark.parametrize(
    ("position_ms", "length_ms", "window", "expected"),
    [
        (HOUR_MS - 30_000, HOUR_MS, 60, True),  # in the credits
        (HOUR_MS - 60_000, HOUR_MS, 60, True),  # exactly on the edge
        (HOUR_MS - 61_000, HOUR_MS, 60, False),  # just outside
        (HOUR_MS - 30_000, HOUR_MS, 0, False),  # off: only a true end counts
        (HOUR_MS - 30_000, 0, 60, False),  # length unknown
        (0, HOUR_MS, 60, False),  # nowhere
        (20_000, 90_000, 60, False),  # a short clip is not finished on starting
        (50_000, 90_000, 60, True),  # ...but is past its middle
    ],
)
def test_within_finish_window(
    position_ms: int, length_ms: int, window: int, expected: bool
) -> None:
    assert within_finish_window(position_ms, length_ms, window) is expected


def _library(position_ms: int, *, window: int | None = None) -> PodcastLibrary:
    library = PodcastLibrary()
    episode = PodcastEpisode(
        guid="e1",
        title="e1",
        audio_url="https://x/e1.mp3",
        position_ms=position_ms,
        duration_seconds=HOUR_MS // 1000,
    )
    library.add_show(PodcastShow(id="s1", title="Show", episodes=[episode]))
    if window is not None:
        library.settings.finished_within_seconds = window
    return library


def test_continue_listening_hides_a_place_inside_the_window() -> None:
    assert virtual_view_pairs(_library(HOUR_MS - 20_000), "continue_listening") == []


def test_continue_listening_keeps_a_place_outside_the_window() -> None:
    assert len(virtual_view_pairs(_library(HOUR_MS // 2), "continue_listening")) == 1


def test_window_zero_restores_the_old_list() -> None:
    pairs = virtual_view_pairs(_library(HOUR_MS - 20_000, window=0), "continue_listening")
    assert len(pairs) == 1


def test_a_podcast_can_set_its_own_window() -> None:
    library = _library(HOUR_MS - 120_000)
    show = library.shows[0]
    assert len(virtual_view_pairs(library, "continue_listening")) == 1
    library.apply_show_override(show, finished_within_seconds=300)
    assert virtual_view_pairs(library, "continue_listening") == []


def test_setting_round_trips_and_defaults_to_a_minute() -> None:
    assert PodcastSettings().finished_within_seconds == 60
    assert PodcastSettings.from_dict({}).finished_within_seconds == 60
    stored = PodcastSettings(finished_within_seconds=90).to_dict()
    assert PodcastSettings.from_dict(stored).finished_within_seconds == 90
    assert PodcastSettings.from_dict({"finished_within_seconds": -5}).finished_within_seconds == 0


def test_setting_is_offered_globally_and_per_podcast() -> None:
    for level in (LEVEL_GLOBAL, LEVEL_SHOW):
        assert any(d.id == "finished_within_seconds" for d in for_level(level))
