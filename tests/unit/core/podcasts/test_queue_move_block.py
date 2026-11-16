"""A whole group picked up by its heading and dropped next to another
(earshot.md E10). Pure."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.podcasts.models import QueueItem
from quill.core.podcasts.queue_selection import move_block_next_to


def _library(*guids: str) -> SimpleNamespace:
    return SimpleNamespace(queue=[QueueItem(show_id="s", episode_guid=g) for g in guids])


def _order(library: SimpleNamespace) -> list[str]:
    return [item.episode_guid for item in library.queue]


def test_drop_a_group_above_another() -> None:
    library = _library("a1", "a2", "b1", "c1", "c2")
    moved = move_block_next_to(library, [3, 4], [0, 1], above=True)
    assert _order(library) == ["c1", "c2", "a1", "a2", "b1"]
    assert moved == [0, 1]


def test_drop_a_group_below_an_episode() -> None:
    library = _library("a1", "a2", "b1", "c1")
    moved = move_block_next_to(library, [0, 1], [3], above=False)
    assert _order(library) == ["b1", "c1", "a1", "a2"]
    assert moved == [2, 3]


def test_dropping_on_itself_does_nothing() -> None:
    library = _library("a1", "a2", "b1")
    assert move_block_next_to(library, [0, 1], [1], above=True) == []
    assert _order(library) == ["a1", "a2", "b1"]
