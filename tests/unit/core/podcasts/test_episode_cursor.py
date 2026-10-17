"""Where you were in each feed, by episode identity (item 43, 2026-10-16)."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.episode_cursor import (
    CURSOR_FILE,
    EpisodeCursor,
    EpisodeMark,
    feed_key,
    neighbour_index,
)
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode


def _ep(guid: str, day: int) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://example.invalid/{guid}.mp3",
        published=f"Mon, {day:02d} Jun 2026 08:00:00 +0000",
    )


SHOW = PodcastShow(id="s1", title="Talks", feed_url="HTTPS://Example.invalid/Feed/")


def test_the_feed_is_known_by_its_address_or_its_id() -> None:
    assert feed_key(SHOW) == "https://example.invalid/feed"
    assert feed_key(PodcastShow(id="local7", title="Mine")) == "id:local7"


def test_the_same_episode_is_found_after_a_sort_flip_and_a_new_arrival() -> None:
    cursor = EpisodeCursor()
    episodes = [_ep("a", 1), _ep("b", 2), _ep("c", 3)]
    cursor.remember(SHOW, episodes[1])
    newest_first = [_ep("d", 4), *reversed(episodes)]
    assert cursor.row_for(SHOW, newest_first) == 2
    assert newest_first[2].guid == "b"


def test_a_vanished_episode_lands_on_its_nearest_neighbour_by_date() -> None:
    mark = EpisodeMark.of(_ep("gone", 10))
    remaining = [_ep("x", 1), _ep("y", 9), _ep("z", 12)]
    assert neighbour_index(mark, remaining) == 1  # day 9 is closer than day 12
    tie = [_ep("older", 8), _ep("newer", 12)]
    assert neighbour_index(EpisodeMark.of(_ep("gone", 10)), tie) == 1, "the newer of two"


def test_a_changed_guid_still_matches_by_audio_address() -> None:
    episode = _ep("old-guid", 5)
    mark = EpisodeMark.of(episode)
    renamed = PodcastEpisode(guid="new-guid", title="t", audio_url=episode.audio_url)
    assert neighbour_index(mark, [_ep("q", 1), renamed]) == 1


def test_no_dates_and_no_match_is_the_first_row() -> None:
    mark = EpisodeMark(guid="gone")
    assert neighbour_index(mark, [PodcastEpisode(guid="a", title="", audio_url="")]) == 0
    assert EpisodeCursor().row_for(SHOW, [_ep("a", 1)]) is None, "nothing remembered"


def test_it_survives_a_restart_and_a_damaged_file(tmp_path: Path) -> None:
    cursor = EpisodeCursor.load(tmp_path)
    assert cursor.remember(SHOW, _ep("b", 2)) is True
    assert cursor.remember(SHOW, _ep("b", 2)) is False, "unchanged is not a write"
    cursor.save()
    again = EpisodeCursor.load(tmp_path)
    assert again.row_for(SHOW, [_ep("a", 1), _ep("b", 2)]) == 1
    (tmp_path / CURSOR_FILE).write_text("{not json", encoding="utf-8")
    assert EpisodeCursor.load(tmp_path).marks == {}
