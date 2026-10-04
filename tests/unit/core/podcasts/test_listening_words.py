"""qc.md section 18: the spoken answers about what is playing."""

from __future__ import annotations

from quill.core.podcasts import listening_words as lw
from quill.core.podcasts.models import PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


def test_time_left_reads_position_length_and_what_is_left() -> None:
    assert lw.time_left(724_000, 1_910_000) == "12:04 of 31:50, 20 minutes left."


def test_time_left_says_the_real_time_at_speed_and_the_sleep_timer() -> None:
    said = lw.time_left(0, 3_600_000, speed=1.5, sleep_seconds=33 * 60)
    assert said == "0:00 of 1:00:00, 1 hour left, 40 minutes at 1.5 times; sleep in 33 minutes."
    assert lw.time_left(0, 600_000, sleep_at_end=True).endswith(
        "; sleep at the end of this episode."
    )


def test_an_unknown_length_is_said_plainly() -> None:
    assert lw.time_left(65_000, 0) == "1:05 in; the length is not known yet."


def test_up_next_is_due_in_the_last_ten_real_seconds() -> None:
    assert not lw.up_next_due(100_000, 200_000)
    assert lw.up_next_due(191_000, 200_000)
    assert lw.up_next_due(182_000, 200_000, speed=2.0)  # 18 s of audio is 9 real seconds
    assert not lw.up_next_due(0, 200_000)


def test_up_next_names_the_podcast_only_when_it_changes() -> None:
    show = PodcastShow(id="s", title="Accidental Tech Podcast", feed_url="")

    class Ep:
        title = "Episode 412"

    assert lw.up_next_sentence(show, Ep(), same_show=False) == (
        "Next: Episode 412 from Accidental Tech Podcast."
    )
    assert lw.up_next_sentence(show, Ep(), same_show=True) == "Next: Episode 412."


def test_play_this_next_goes_after_the_playing_episode() -> None:
    library = PodcastLibrary()
    library.queue = [QueueItem("s", "a", ""), QueueItem("s", "b", ""), QueueItem("s", "c", "")]
    assert lw.play_this_next(library, "s", "c", playing=("s", "a")) == 1
    assert [q.episode_guid for q in library.queue] == ["a", "c", "b"]
    assert lw.play_this_next(library, "t", "new", playing=None) == 0
    assert library.queue[0].episode_guid == "new"


def test_a_queue_slot_remembers_why_it_is_waiting() -> None:
    from quill.core.podcasts import queue as queue_ops

    library = PodcastLibrary()
    queue_ops.add_to_queue(library, "s", "a", reason="Auto-Queue")
    queue_ops.add_to_queue(library, "s", "b")
    again = [QueueItem.from_dict(item.to_dict()) for item in library.queue]
    assert [item.reason for item in again if item] == ["Auto-Queue", ""]
    assert "reason" not in library.queue[1].to_dict()
