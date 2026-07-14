"""Tests for the Podcasts virtual-view aggregation (Favorites, New
Episodes, Continue Listening) -- pure, no wx."""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.podcasts.virtual_views import favorite_shows, virtual_view_pairs


def _episode(guid: str, *, played: bool = False, position_ms: int = 0) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=guid,
        audio_url=f"https://x/{guid}.mp3",
        played=played,
        position_ms=position_ms,
    )


def test_favorite_shows_returns_only_favorited_shows() -> None:
    library = PodcastLibrary()
    fav = PodcastShow(id="s1", title="Fav", is_favorite=True)
    other = PodcastShow(id="s2", title="Other", is_favorite=False)
    library.add_show(fav)
    library.add_show(other)
    assert favorite_shows(library) == [fav]


def test_favorite_shows_empty_when_none_favorited() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Show"))
    assert favorite_shows(library) == []


def test_new_episodes_includes_only_unplayed_across_shows() -> None:
    library = PodcastLibrary()
    show_a = PodcastShow(
        id="s1", title="A", episodes=[_episode("e1", played=False), _episode("e2", played=True)]
    )
    show_b = PodcastShow(id="s2", title="B", episodes=[_episode("e3", played=False)])
    library.add_show(show_a)
    library.add_show(show_b)
    pairs = virtual_view_pairs(library, "new_episodes")
    assert {(show.id, episode.guid) for show, episode in pairs} == {("s1", "e1"), ("s2", "e3")}


def test_continue_listening_requires_in_progress_and_unplayed() -> None:
    library = PodcastLibrary()
    show = PodcastShow(
        id="s1",
        title="A",
        episodes=[
            _episode("e1", played=False, position_ms=5000),  # in progress
            _episode("e2", played=False, position_ms=0),  # never started
            _episode("e3", played=True, position_ms=5000),  # already finished
        ],
    )
    library.add_show(show)
    pairs = virtual_view_pairs(library, "continue_listening")
    assert [episode.guid for _show, episode in pairs] == ["e1"]


def test_unknown_view_id_returns_empty() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="A", episodes=[_episode("e1")]))
    assert virtual_view_pairs(library, "not_a_real_view") == []


def test_inbox_includes_only_unplayed_from_routed_shows() -> None:
    library = PodcastLibrary()
    routed = PodcastShow(
        id="s1",
        title="Routed",
        route_to_inbox=True,
        episodes=[_episode("e1", played=False), _episode("e2", played=True)],
    )
    not_routed = PodcastShow(
        id="s2", title="Not Routed", route_to_inbox=False, episodes=[_episode("e3")]
    )
    library.add_show(routed)
    library.add_show(not_routed)
    pairs = virtual_view_pairs(library, "inbox")
    assert [(show.id, episode.guid) for show, episode in pairs] == [("s1", "e1")]
