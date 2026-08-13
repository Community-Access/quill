"""Queue true-order advance and group moves (1.1.0)."""

from __future__ import annotations

from quill.core.podcasts import queue as queue_ops
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library() -> PodcastLibrary:
    shows = []
    for show_index in ("a", "b"):
        episodes = [
            PodcastEpisode(guid=f"{show_index}{i}", title=f"{show_index}{i}", audio_url="https://x")
            for i in range(3)
        ]
        shows.append(
            PodcastShow(id=f"s{show_index}", title=f"Show {show_index}", episodes=episodes)
        )
    return PodcastLibrary(shows=shows)


def _queue(library: PodcastLibrary, *pairs: tuple[str, str]) -> None:
    for show_id, guid in pairs:
        queue_ops.add_to_queue(library, show_id, guid)


class TestPopNextAfter:
    def test_finishing_a_mid_queue_episode_continues_from_after_it(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sa", "a1"), ("sa", "a2"))

        result = queue_ops.pop_next_after(library, "sa", "a1")

        assert result is not None
        assert result[1].guid == "a2"
        # a1 is consumed; a0 is still ahead of it and untouched.
        assert [item.episode_guid for item in library.queue] == ["a0"]

    def test_an_episode_not_in_the_queue_advances_from_the_front(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sa", "a1"))

        result = queue_ops.pop_next_after(library, "sb", "b0")

        assert result is not None
        assert result[1].guid == "a0"

    def test_finishing_the_last_queued_item_falls_back_to_what_is_ahead(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sa", "a2"))

        result = queue_ops.pop_next_after(library, "sa", "a2")

        assert result is not None
        assert result[1].guid == "a0"

    def test_finishing_the_only_queued_item_leaves_nothing(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"))

        assert queue_ops.pop_next_after(library, "sa", "a0") is None
        assert library.queue == []

    def test_a_stale_slot_after_it_is_skipped_not_returned(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("gone", "ghost"), ("sa", "a2"))

        result = queue_ops.pop_next_after(library, "sa", "a0")

        assert result is not None
        assert result[1].guid == "a2"


class TestQueueGroups:
    def test_groups_appear_in_first_appearance_order(self) -> None:
        library = _library()
        _queue(library, ("sb", "b0"), ("sa", "a0"), ("sb", "b1"))

        groups = queue_ops.queue_groups(library)

        assert [show.id for show, _indices in groups] == ["sb", "sa"]
        assert groups[0][1] == [0, 2]

    def test_move_group_to_top(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sb", "b0"), ("sa", "a1"))

        moved = queue_ops.move_group(library, "sb", where="top")

        assert moved == 1
        assert [item.episode_guid for item in library.queue] == ["b0", "a0", "a1"]

    def test_move_group_to_bottom(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sb", "b0"), ("sa", "a1"))

        queue_ops.move_group(library, "sa", where="bottom")

        assert [item.episode_guid for item in library.queue] == ["b0", "a0", "a1"]

    def test_move_group_up_steps_past_a_whole_group(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sa", "a1"), ("sb", "b0"))

        queue_ops.move_group(library, "sb", where="up")

        assert [item.episode_guid for item in library.queue] == ["b0", "a0", "a1"]

    def test_moving_past_the_end_does_nothing(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"), ("sb", "b0"))

        assert queue_ops.move_group(library, "sa", where="up") == 0
        assert [item.episode_guid for item in library.queue] == ["a0", "b0"]

    def test_a_show_with_nothing_queued_moves_nothing(self) -> None:
        library = _library()
        _queue(library, ("sa", "a0"))

        assert queue_ops.move_group(library, "sb", where="top") == 0


class TestAddedAt:
    def test_adding_stamps_the_slot(self) -> None:
        library = _library()

        queue_ops.add_to_queue(library, "sa", "a0")

        assert library.queue[0].added_at

    def test_play_next_keeps_an_existing_timestamp(self) -> None:
        library = _library()
        queue_ops.add_to_queue(library, "sa", "a0")
        queue_ops.add_to_queue(library, "sa", "a1")
        original = library.queue[1].added_at

        queue_ops.play_next(library, "sa", "a1")

        # Reordering is not re-adding: the expiry clock must not reset.
        assert library.queue[0].added_at == original
