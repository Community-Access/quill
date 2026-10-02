"""The pinned views open (``quill/ui/podcasts/library_tree.py``).

A node that says "(12)" and cannot be opened is a dead end wearing a number,
and it was every pinned view in Cast's tree until 2026-09-30. These pin what
the module promises: an expander only when there is something under it; a
cross-show list that names the podcast on every row, newest first, capped with
a "more" row; Favorites that opens to podcasts (each with its own expander)
rather than flattening their episodes; and what Play means on a view.

Driven with a fake tree and real library objects. The view membership itself
belongs to ``virtual_views`` and is tested there, so it is stubbed here to the
pairs a test wants.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import library_tree


class _Tree:
    """Just enough of wx.TreeCtrl: items are ints, children are recorded."""

    def __init__(self) -> None:
        self._next = 1
        self.children: dict[int, list[int]] = {0: []}
        self.labels: dict[int, str] = {}
        self.data: dict[int, Any] = {}

    def AppendItem(self, parent: int, label: str) -> int:  # noqa: N802 - wx API shape
        item = self._next
        self._next += 1
        self.children.setdefault(parent, []).append(item)
        self.children[item] = []
        self.labels[item] = label
        return item

    def SetItemData(self, item: int, data: Any) -> None:  # noqa: N802
        self.data[item] = data

    def DeleteChildren(self, item: int) -> None:  # noqa: N802
        self.children[item] = []

    def rows(self, parent: int) -> list[tuple[str, Any]]:
        return [(self.labels[c], self.data.get(c)) for c in self.children[parent]]


def _episode(guid: str, published: str, *, played: bool = False, position: int = 0) -> Any:
    episode = PodcastEpisode(guid=guid, title=f"Episode {guid}", audio_url="", published=published)
    episode.played = played
    episode.position_ms = position
    return episode


@pytest.fixture
def library() -> PodcastLibrary:
    daily = PodcastShow(id="daily", title="The Daily", feed_url="https://example.invalid/d")
    daily.episodes = [_episode("d1", "2026-09-01"), _episode("d2", "2026-09-03", played=True)]
    daily.is_favorite = True
    history = PodcastShow(id="history", title="History Hour", feed_url="https://example.invalid/h")
    history.episodes = [_episode("h1", "2026-09-02")]
    empty = PodcastShow(id="empty", title="Empty Show", feed_url="https://example.invalid/e")
    empty.is_favorite = True
    return PodcastLibrary(shows=[daily, history, empty])


def _stub_view(monkeypatch: pytest.MonkeyPatch, pairs: list[tuple[Any, Any]]) -> None:
    from quill.core.podcasts import virtual_views

    monkeypatch.setattr(virtual_views, "virtual_view_pairs", lambda _lib, _view: list(pairs))


# -- the expander ---------------------------------------------------------------- #


def test_a_view_with_nothing_in_it_gets_no_expander() -> None:
    tree = _Tree()
    library_tree.add_view_placeholder(tree, 0, "inbox", 0)
    assert tree.rows(0) == []


def test_a_view_with_a_count_gets_one_placeholder_tagged_as_a_view() -> None:
    tree = _Tree()
    library_tree.add_view_placeholder(tree, 0, "inbox", 12)
    assert tree.rows(0) == [("Loading...", (library_tree.PLACEHOLDER_VIEW, "inbox"))]


# -- an episode view --------------------------------------------------------------- #


def test_an_episode_view_names_the_podcast_on_every_row_newest_first(
    library: PodcastLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    daily, history, _ = library.shows
    _stub_view(
        monkeypatch,
        [(daily, daily.episodes[0]), (history, history.episodes[0]), (daily, daily.episodes[1])],
    )
    tree = _Tree()
    host = SimpleNamespace(_shows_tree=tree, _podcast_library=library)
    view = tree.AppendItem(0, "Inbox (3)")
    tree.AppendItem(view, "Loading...")  # the placeholder the fill replaces
    library_tree.fill_view_children(host, view, "inbox")
    assert tree.rows(view) == [
        ("Episode d2 -- The Daily", ("episode", "daily\x00d2")),
        ("Episode h1 -- History Hour", ("episode", "history\x00h1")),
        ("Episode d1 -- The Daily", ("episode", "daily\x00d1")),
    ]


def test_a_huge_view_is_capped_with_a_row_that_says_how_many_more(
    library: PodcastLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    daily = library.shows[0]
    many = [(daily, _episode(f"x{i}", f"2026-01-{(i % 28) + 1:02d}")) for i in range(205)]
    _stub_view(monkeypatch, many)
    tree = _Tree()
    host = SimpleNamespace(_shows_tree=tree, _podcast_library=library)
    view = tree.AppendItem(0, "New Episodes")
    library_tree.fill_view_children(host, view, "new_episodes")
    rows = tree.rows(view)
    assert len(rows) == 201
    assert rows[-1] == ("5 more -- use the episode list to see them all", ("more", ""))


# -- Favorites ------------------------------------------------------------------- #


def test_favorites_opens_to_podcasts_each_with_its_own_expander(library: PodcastLibrary) -> None:
    tree = _Tree()
    host = SimpleNamespace(_shows_tree=tree, _podcast_library=library)
    view = tree.AppendItem(0, "Favorites (2)")
    library_tree.fill_view_children(host, view, "favorites")
    rows = tree.rows(view)
    labels = [label for label, _ in rows]
    assert "The Daily (1 unheard)" in labels
    assert "Empty Show" in labels  # nothing unheard: no "(0 unheard)"
    assert all(data[0] == "show" for _, data in rows)
    daily_item = next(c for c in tree.children[view] if tree.data[c] == ("show", "daily"))
    empty_item = next(c for c in tree.children[view] if tree.data[c] == ("show", "empty"))
    assert tree.rows(daily_item) == [("Loading episodes...", ("placeholder", "daily"))]
    assert tree.rows(empty_item) == []  # no episodes: no expander that opens to nothing


# -- what Play means on a view --------------------------------------------------- #


def test_play_on_a_view_takes_the_newest_unstarted_episode(
    library: PodcastLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    daily, history, _ = library.shows
    started = _episode("s1", "2026-09-09", position=5000)
    _stub_view(
        monkeypatch,
        [(daily, started), (daily, daily.episodes[1]), (history, history.episodes[0])],
    )
    show, episode = library_tree.first_playable_in_view(library, "inbox")
    # Newest is started (s1) and the next is played (d2): neither is a fresh start.
    assert (show.id, episode.guid) == ("history", "h1")


def test_play_on_continue_listening_carries_on_with_the_most_recent(
    library: PodcastLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    daily = library.shows[0]
    started = _episode("s1", "2026-09-09", position=5000)
    _stub_view(monkeypatch, [(daily, daily.episodes[0]), (daily, started)])
    show, episode = library_tree.first_playable_in_view(library, "continue_listening")
    assert episode.guid == "s1"


def test_play_on_favorites_takes_a_favourites_newest_unplayed(library: PodcastLibrary) -> None:
    show, episode = library_tree.first_playable_in_view(library, "favorites")
    assert (show.id, episode.guid) == ("daily", "d1")


def test_play_on_an_empty_view_is_none_so_the_caller_can_say_why(
    library: PodcastLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_view(monkeypatch, [])
    assert library_tree.first_playable_in_view(library, "inbox") is None
