"""The three verbs Earshot publishes to Siri (ear.md R5).

The interesting one is Play an Unheard Episode, and the two things worth testing are
the ones that make it not-a-random-choice: **the order it looks in** (the queue is a
decision already made, so it wins) and **what it refuses to pick** (anything already
started, because starting it from a one-press key is indistinguishable from losing
your place).
"""

from __future__ import annotations

import random

from quill.core.podcasts import quick_plays
from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, *, published: str, **kwargs) -> PodcastEpisode:
    base = {
        "guid": guid,
        "title": guid.replace("-", " ").title(),
        "audio_url": f"https://e/{guid}.mp3",
        "published": published,
    }
    base.update(kwargs)
    return PodcastEpisode(**base)


def _show(show_id: str, title: str, *episodes: PodcastEpisode, **kwargs) -> PodcastShow:
    return PodcastShow(
        id=show_id,
        title=title,
        feed_url=f"https://e/{show_id}.xml",
        episodes=list(episodes),
        **kwargs,
    )


# -- the order it looks in ---------------------------------------------------- #


def test_the_queue_wins_because_it_is_a_decision_already_made() -> None:
    """Going hunting in the library would be the app second-guessing an explicit
    instruction."""
    queued = _show("s1", "Queued Show", _episode("q1", published="2026-01-01T00:00:00"))
    newer = _show("s2", "Newer Show", _episode("n1", published="2026-09-30T00:00:00"))
    library = PodcastLibrary(
        shows=[queued, newer], queue=[QueueItem(show_id="s1", episode_guid="q1")]
    )

    pick = quick_plays.unheard_pick(library)
    assert pick is not None
    assert pick.episode.guid == "q1"
    assert pick.source == "the queue"


def test_the_queue_is_taken_in_queue_order_not_by_date() -> None:
    """Its order is a decision the listener made; sorting it by date here would
    quietly answer a different question from the one the queue is an answer to."""
    show = _show(
        "s1",
        "A Show",
        _episode("old", published="2026-01-01T00:00:00"),
        _episode("new", published="2026-09-30T00:00:00"),
    )
    library = PodcastLibrary(
        shows=[show],
        queue=[
            QueueItem(show_id="s1", episode_guid="old"),
            QueueItem(show_id="s1", episode_guid="new"),
        ],
    )
    pick = quick_plays.unheard_pick(library)
    assert pick is not None
    assert pick.episode.guid == "old"


def test_the_inbox_comes_before_everything_else() -> None:
    """Routing a show to the Inbox is a standing statement that its episodes are
    the ones awaiting a decision."""
    inbox = _show(
        "s1", "Routed", _episode("i1", published="2026-01-01T00:00:00"), route_to_inbox=True
    )
    other = _show("s2", "Not Routed", _episode("o1", published="2026-09-30T00:00:00"))
    library = PodcastLibrary(shows=[inbox, other])

    pick = quick_plays.unheard_pick(library)
    assert pick is not None
    assert pick.source == "the Inbox"
    assert pick.episode.guid == "i1"


def test_newest_and_oldest_are_different_intentions() -> None:
    """Newest is "what is going on today"; oldest is "let me work through the
    backlog". Both are offered because they are genuinely different."""
    show = _show(
        "s1",
        "A Show",
        _episode("old", published="2026-01-01T00:00:00"),
        _episode("new", published="2026-09-30T00:00:00"),
    )
    library = PodcastLibrary(shows=[show])

    newest = quick_plays.unheard_pick(library, order=quick_plays.NEWEST)
    oldest = quick_plays.unheard_pick(library, order=quick_plays.OLDEST)
    assert newest is not None and oldest is not None
    assert newest.episode.guid == "new"
    assert oldest.episode.guid == "old"


# -- what it refuses to pick -------------------------------------------------- #


def test_nothing_already_started_is_ever_picked() -> None:
    """A resume position means the listener is in the middle of it, and starting it
    from a one-press key would be indistinguishable from losing their place."""
    show = _show(
        "s1",
        "A Show",
        _episode("started", published="2026-09-30T00:00:00", position_ms=90_000),
        _episode("fresh", published="2026-01-01T00:00:00"),
    )
    library = PodcastLibrary(shows=[show])

    pick = quick_plays.unheard_pick(library)
    assert pick is not None
    assert pick.episode.guid == "fresh", "a part-heard episode was picked"


def test_a_started_episode_in_the_queue_is_skipped_too() -> None:
    show = _show(
        "s1",
        "A Show",
        _episode("started", published="2026-09-30T00:00:00", position_ms=1),
        _episode("fresh", published="2026-09-29T00:00:00"),
    )
    library = PodcastLibrary(
        shows=[show],
        queue=[
            QueueItem(show_id="s1", episode_guid="started"),
            QueueItem(show_id="s1", episode_guid="fresh"),
        ],
    )
    pick = quick_plays.unheard_pick(library)
    assert pick is not None
    assert pick.episode.guid == "fresh"


def test_a_played_episode_is_never_picked() -> None:
    show = _show("s1", "A Show", _episode("done", published="2026-09-30T00:00:00", played=True))
    assert quick_plays.unheard_pick(PodcastLibrary(shows=[show])) is None


def test_an_imported_file_with_no_download_is_not_offered() -> None:
    """A local show's episode is only playable if its file is actually there."""
    local = _show("s1", "Mine", _episode("m1", published="x", audio_url=""), is_local=True)
    assert quick_plays.unheard_pick(PodcastLibrary(shows=[local])) is None


def test_nothing_to_pick_names_the_other_two_places_to_look() -> None:
    """ "Nothing unheard" invites the reasonable and wrong conclusion that the
    library is empty; the usual cause is that everything unplayed is part-started."""
    said = quick_plays.nothing_unheard()
    assert "Continue Listening" in said
    assert "still in its" in said


# -- what it says ------------------------------------------------------------- #


def test_the_pick_names_where_it_looked() -> None:
    """A key that chose on the listener's behalf has to say what it chose and why
    that one -- "from the queue" and "from your podcasts" are different facts."""
    show = _show("s1", "A Show", _episode("e1", published="2026-09-30T00:00:00"))
    pick = quick_plays.unheard_pick(PodcastLibrary(shows=[show]))
    assert pick is not None
    assert pick.announcement() == "E1, from your podcasts"


# -- shuffle ------------------------------------------------------------------ #


def test_shuffling_permutes_rather_than_relying_on_chance() -> None:
    show = _show(
        "s1",
        "A Show",
        *[_episode(f"e{n}", published=f"2026-09-{n:02d}T00:00:00") for n in range(1, 9)],
    )
    library = PodcastLibrary(
        shows=[show], queue=[QueueItem(show_id="s1", episode_guid=f"e{n}") for n in range(1, 9)]
    )
    before = [item.episode_guid for item in library.queue]

    count = quick_plays.shuffle_whole_queue(library, rng=random.Random(7))

    assert count == 8
    assert sorted(item.episode_guid for item in library.queue) == sorted(before)
    assert [item.episode_guid for item in library.queue] != before


def test_a_queue_of_one_answers_one_rather_than_zero() -> None:
    """Nothing changed, but the queue does hold one item, and reporting 0 would
    read as "the queue is empty"."""
    show = _show("s1", "A Show", _episode("e1", published="x"))
    library = PodcastLibrary(shows=[show], queue=[QueueItem(show_id="s1", episode_guid="e1")])
    assert quick_plays.shuffle_whole_queue(library) == 1


def test_an_empty_queue_shuffles_to_zero() -> None:
    assert quick_plays.shuffle_whole_queue(PodcastLibrary()) == 0


# -- clearing ----------------------------------------------------------------- #


def test_the_clear_question_carries_the_count_and_what_survives() -> None:
    """ "Clear the queue" reads as a delete, so somebody who would happily have
    cleared it cancels rather than find out what it costs."""
    show = _show("s1", "A Show", _episode("e1", published="x"), _episode("e2", published="y"))
    library = PodcastLibrary(
        shows=[show],
        queue=[
            QueueItem(show_id="s1", episode_guid="e1"),
            QueueItem(show_id="s1", episode_guid="e2"),
        ],
    )
    question = quick_plays.clear_queue_confirm(library)
    assert "all 2 items" in question
    assert "Nothing is deleted" in question
    assert "nothing is marked as played" in question
    assert "stay on this computer" in question


def test_an_empty_queue_asks_nothing() -> None:
    assert quick_plays.clear_queue_confirm(PodcastLibrary()) == ""


def test_clearing_is_one_act_and_reports_what_it_removed() -> None:
    """A half-cleared queue is a state nobody asked for and one the listener would
    have to inspect to discover."""
    show = _show("s1", "A Show", _episode("e1", published="x"))
    library = PodcastLibrary(shows=[show], queue=[QueueItem(show_id="s1", episode_guid="e1")])
    assert quick_plays.clear_queue(library) == 1
    assert library.queue == []


def test_clearing_leaves_every_episode_where_it_was() -> None:
    """The promise the question makes has to be true."""
    show = _show("s1", "A Show", _episode("e1", published="x", downloaded_path="C:/d/e1.mp3"))
    library = PodcastLibrary(shows=[show], queue=[QueueItem(show_id="s1", episode_guid="e1")])
    quick_plays.clear_queue(library)
    assert show.episodes[0].played is False
    assert show.episodes[0].downloaded_path == "C:/d/e1.mp3"
