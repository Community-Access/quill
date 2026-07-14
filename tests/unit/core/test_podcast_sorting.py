"""Tests for podcast episode/show sorting (pure functions)."""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.sorting import sort_episodes, sort_shows

_OLD = "Wed, 01 Jul 2026 00:00:00 GMT"
_MID = "Wed, 08 Jul 2026 00:00:00 GMT"
_NEW = "Wed, 15 Jul 2026 00:00:00 GMT"


def _episode(
    guid: str, *, title: str, published: str = "", duration: int = 0, played: bool = False
) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=title,
        audio_url=f"https://x/{guid}.mp3",
        published=published,
        duration_seconds=duration,
        played=played,
    )


def test_sort_episodes_date_newest_default() -> None:
    old = _episode("g1", title="Old", published=_OLD)
    new = _episode("g2", title="New", published=_NEW)
    mid = _episode("g3", title="Mid", published=_MID)
    result = sort_episodes([old, new, mid], "date_newest")
    assert [e.guid for e in result] == ["g2", "g3", "g1"]


def test_sort_episodes_date_oldest() -> None:
    old = _episode("g1", title="Old", published=_OLD)
    new = _episode("g2", title="New", published=_NEW)
    result = sort_episodes([new, old], "date_oldest")
    assert [e.guid for e in result] == ["g1", "g2"]


def test_sort_episodes_title_az_is_case_insensitive() -> None:
    b = _episode("g1", title="banana")
    a = _episode("g2", title="Apple")
    result = sort_episodes([b, a], "title_az")
    assert [e.title for e in result] == ["Apple", "banana"]


def test_sort_episodes_duration_longest_and_shortest() -> None:
    short = _episode("g1", title="Short", duration=100)
    long = _episode("g2", title="Long", duration=900)
    assert [e.guid for e in sort_episodes([short, long], "duration_longest")] == ["g2", "g1"]
    assert [e.guid for e in sort_episodes([long, short], "duration_shortest")] == ["g1", "g2"]


def test_sort_episodes_unplayed_first_then_newest() -> None:
    played_new = _episode("g1", title="Played new", published=_NEW, played=True)
    unplayed_old = _episode("g2", title="Unplayed old", published=_OLD, played=False)
    unplayed_new = _episode("g3", title="Unplayed new", published=_NEW, played=False)
    result = sort_episodes([played_new, unplayed_old, unplayed_new], "unplayed_first")
    assert [e.guid for e in result] == ["g3", "g2", "g1"]


def test_sort_episodes_unrecognized_mode_falls_back_to_date_newest() -> None:
    old = _episode("g1", title="Old", published=_OLD)
    new = _episode("g2", title="New", published=_NEW)
    result = sort_episodes([old, new], "bogus")
    assert [e.guid for e in result] == ["g2", "g1"]


def test_sort_episodes_missing_or_unparseable_date_sorts_as_oldest() -> None:
    dated = _episode("g1", title="Dated", published=_NEW)
    undated = _episode("g2", title="Undated", published="")
    junk_date = _episode("g3", title="Junk", published="not a date")
    result = sort_episodes([dated, undated, junk_date], "date_newest")
    assert result[0].guid == "g1"
    assert {e.guid for e in result[1:]} == {"g2", "g3"}


def _show(show_id: str, *, title: str, episodes: list[PodcastEpisode] | None = None) -> PodcastShow:
    return PodcastShow(id=show_id, title=title, episodes=episodes or [])


def test_sort_shows_title_az_default() -> None:
    b = _show("s1", title="Banana Cast")
    a = _show("s2", title="apple hour")
    result = sort_shows([b, a], "title_az")
    assert [s.id for s in result] == ["s2", "s1"]


def test_sort_shows_unheard_first() -> None:
    few_unheard = _show("s1", title="Few", episodes=[_episode("e1", title="e1", played=True)])
    many_unheard = _show(
        "s2",
        title="Many",
        episodes=[_episode("e2", title="e2"), _episode("e3", title="e3")],
    )
    result = sort_shows([few_unheard, many_unheard], "unheard_first")
    assert [s.id for s in result] == ["s2", "s1"]


def test_sort_shows_recently_updated() -> None:
    stale = _show("s1", title="Stale", episodes=[_episode("e1", title="e1", published=_OLD)])
    fresh = _show("s2", title="Fresh", episodes=[_episode("e2", title="e2", published=_NEW)])
    result = sort_shows([stale, fresh], "recently_updated")
    assert [s.id for s in result] == ["s2", "s1"]


def test_sort_shows_recently_updated_show_with_no_episodes_sorts_last() -> None:
    empty = _show("s1", title="Empty")
    has_episodes = _show("s2", title="Has", episodes=[_episode("e1", title="e1", published=_NEW)])
    result = sort_shows([empty, has_episodes], "recently_updated")
    assert [s.id for s in result] == ["s2", "s1"]
