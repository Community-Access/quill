"""Tests for podcast episode/show sorting (pure functions)."""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.sorting import sort_episodes, sort_pairs, sort_shows
from quill.core.podcasts.subscriptions import PodcastLibrary

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


# -- sort_pairs (cross-show views: Inbox, New Episodes, Continue Listening) --


def test_sort_pairs_grouped_keeps_shows_contiguous_sorted_by_title() -> None:
    banana = _show("s1", title="Banana Cast")
    apple = _show("s2", title="Apple Hour")
    library = PodcastLibrary(shows=[banana, apple])
    pairs = [
        (banana, _episode("b1", title="B1", published=_OLD)),
        (apple, _episode("a1", title="A1", published=_OLD)),
        (banana, _episode("b2", title="B2", published=_NEW)),
        (apple, _episode("a2", title="A2", published=_NEW)),
    ]
    result = sort_pairs(library, pairs, view_mode="grouped")
    assert [show.title for show, _e in result] == [
        "Apple Hour",
        "Apple Hour",
        "Banana Cast",
        "Banana Cast",
    ]
    # Within each show's group, still sorted by the (global default) episode
    # mode, date_newest.
    apple_group = [e.guid for show, e in result if show.title == "Apple Hour"]
    assert apple_group == ["a2", "a1"]


def test_sort_pairs_flat_is_one_chronological_stream() -> None:
    show_a = _show("s1", title="A")
    show_b = _show("s2", title="B")
    library = PodcastLibrary(shows=[show_a, show_b])
    pairs = [
        (show_a, _episode("a1", title="A1", published=_OLD)),
        (show_b, _episode("b1", title="B1", published=_NEW)),
        (show_a, _episode("a2", title="A2", published=_MID)),
    ]
    result = sort_pairs(library, pairs, view_mode="flat")
    assert [e.guid for _show, e in result] == ["b1", "a2", "a1"]


def test_sort_pairs_grouped_respects_the_library_default_sort_mode() -> None:
    show = _show("s1", title="Only Show")
    library = PodcastLibrary(
        shows=[show], settings=PodcastSettings(episode_sort_mode="date_oldest")
    )
    pairs = [
        (show, _episode("new", title="New", published=_NEW)),
        (show, _episode("old", title="Old", published=_OLD)),
    ]
    result = sort_pairs(library, pairs, view_mode="grouped")
    assert [e.guid for _show, e in result] == ["old", "new"]


def test_sort_pairs_grouped_respects_a_per_show_sort_override() -> None:
    """Two shows, each with a different effective sort mode: one show's own
    override wins for its own episodes without touching the other show's."""
    oldest_first_show = _show("s1", title="Oldest First Show")
    oldest_first_show.settings = PodcastSettings(episode_sort_mode="date_oldest")
    newest_first_show = _show("s2", title="Zzz Newest First Show")  # sorts after s1 by title
    library = PodcastLibrary(shows=[oldest_first_show, newest_first_show])
    pairs = [
        (oldest_first_show, _episode("s1-new", title="New", published=_NEW)),
        (oldest_first_show, _episode("s1-old", title="Old", published=_OLD)),
        (newest_first_show, _episode("s2-new", title="New", published=_NEW)),
        (newest_first_show, _episode("s2-old", title="Old", published=_OLD)),
    ]
    result = sort_pairs(library, pairs, view_mode="grouped")
    assert [e.guid for _show, e in result] == ["s1-old", "s1-new", "s2-new", "s2-old"]


def test_sort_pairs_flat_ignores_per_show_sort_overrides() -> None:
    """A per-show sort override only applies within that show's own group
    (grouped/folders); "flat" always uses the single global sort mode."""
    show = _show("s1", title="Only Show")
    show.settings = PodcastSettings(episode_sort_mode="date_oldest")
    library = PodcastLibrary(shows=[show])  # global default stays date_newest
    pairs = [
        (show, _episode("new", title="New", published=_NEW)),
        (show, _episode("old", title="Old", published=_OLD)),
    ]
    result = sort_pairs(library, pairs, view_mode="flat")
    assert [e.guid for _show, e in result] == ["new", "old"]


def test_sort_pairs_empty_list() -> None:
    library = PodcastLibrary()
    assert sort_pairs(library, [], view_mode="grouped") == []
    assert sort_pairs(library, [], view_mode="flat") == []
