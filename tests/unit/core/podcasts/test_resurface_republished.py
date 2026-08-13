"""A re-published episode comes back to the Inbox (x.md item 6).

When a publisher re-issues an episode -- a corrected file, a re-cut, one pulled
and reissued -- an episode the Inbox had already trimmed was gone for good: the
trim marker was permanent and a refresh only refreshed metadata in place. The
corrected version sat in the show's own list, where nobody was looking.

The three exemptions are the load-bearing part, and they are the *same three*
``trim_inbox`` already applies. Getting them wrong in the other direction --
resurfacing something you had finished with, or were halfway through -- would
make a refresh feel like it was arguing with you.
"""

from __future__ import annotations

from quill.core.podcasts.inbox import TRIMMED_MARKER, inbox_key, resurface_republished
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.queue import QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary, merge_episodes


def _episode(
    guid: str, *, published: str = "2026-07-01T00:00:00", **kwargs: object
) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://example.com/{guid}.mp3",
        published=published,
        **kwargs,  # type: ignore[arg-type]
    )


def _library(*episodes: PodcastEpisode, route: bool = True) -> tuple[PodcastLibrary, PodcastShow]:
    show = PodcastShow(
        id="show-1",
        title="The Daily",
        feed_url="https://example.com/feed.xml",
        episodes=list(episodes),
    )
    show.route_to_inbox = route
    return PodcastLibrary(shows=[show]), show


def _trim(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> None:
    library.inbox_assignments[inbox_key(show.id, episode.guid)] = TRIMMED_MARKER


# -- detecting the re-publication --------------------------------------------


def test_a_later_published_stamp_is_what_marks_a_re_publication() -> None:
    """The signal is the publisher's own stamp moving forward -- a deliberate
    act, not an incidental metadata refresh."""
    show = PodcastShow(id="s", title="T", feed_url="https://e/f", episodes=[_episode("a")])
    republished: list[str] = []

    merge_episodes(show, [_episode("a", published="2026-08-01T00:00:00")], republished=republished)

    assert republished == ["a"]


def test_an_unchanged_stamp_is_not_a_re_publication() -> None:
    show = PodcastShow(id="s", title="T", feed_url="https://e/f", episodes=[_episode("a")])
    republished: list[str] = []

    merge_episodes(show, [_episode("a")], republished=republished)

    assert republished == []


def test_an_earlier_stamp_is_not_a_re_publication() -> None:
    """A feed that corrects a date *backwards* has not re-issued anything."""
    show = PodcastShow(
        id="s",
        title="T",
        feed_url="https://e/f",
        episodes=[_episode("a", published="2026-08-01T00:00:00")],
    )
    republished: list[str] = []

    merge_episodes(show, [_episode("a", published="2026-07-01T00:00:00")], republished=republished)

    assert republished == []


def test_a_genuinely_new_episode_is_new_not_republished() -> None:
    show = PodcastShow(id="s", title="T", feed_url="https://e/f", episodes=[])
    republished: list[str] = []

    new_count = merge_episodes(show, [_episode("a")], republished=republished)

    assert new_count == 1
    assert republished == []


def test_collecting_is_opt_in_so_existing_callers_are_unaffected() -> None:
    show = PodcastShow(id="s", title="T", feed_url="https://e/f", episodes=[_episode("a")])
    assert merge_episodes(show, [_episode("a", published="2026-09-01T00:00:00")]) == 0


# -- resurfacing -------------------------------------------------------------


def test_a_trimmed_episode_comes_back() -> None:
    episode = _episode("a")
    library, show = _library(episode)
    _trim(library, show, episode)

    returned = resurface_republished(library, show, ["a"])

    assert [e.guid for e in returned] == ["a"]
    assert inbox_key(show.id, "a") not in library.inbox_assignments


def test_a_played_episode_is_left_alone() -> None:
    """You are finished with it; a re-cut does not un-finish it."""
    episode = _episode("a", played=True)
    library, show = _library(episode)
    _trim(library, show, episode)

    assert resurface_republished(library, show, ["a"]) == []
    assert library.inbox_assignments[inbox_key(show.id, "a")] == TRIMMED_MARKER


def test_a_started_episode_is_left_alone() -> None:
    """Reappearing as though it were new would misrepresent your own history
    with it."""
    episode = _episode("a", position_ms=90_000)
    library, show = _library(episode)
    _trim(library, show, episode)

    assert resurface_republished(library, show, ["a"]) == []


def test_a_queued_episode_is_left_alone() -> None:
    """You already decided when to hear it; the Inbox is for episodes still
    awaiting that decision."""
    episode = _episode("a")
    library, show = _library(episode)
    _trim(library, show, episode)
    library.queue.append(QueueItem(show_id=show.id, episode_guid="a"))

    assert resurface_republished(library, show, ["a"]) == []


def test_a_hand_filed_episode_is_left_alone() -> None:
    """An assignment that is not the trim marker is the listener's own filing,
    and a publisher's re-issue does not overrule it."""
    episode = _episode("a")
    library, show = _library(episode)
    library.inbox_assignments[inbox_key(show.id, "a")] = "folder-42"

    assert resurface_republished(library, show, ["a"]) == []
    assert library.inbox_assignments[inbox_key(show.id, "a")] == "folder-42"


def test_an_episode_that_was_never_trimmed_needs_no_help() -> None:
    """It is already in the Inbox; "resurfacing" it would be a no-op reported
    as an event."""
    episode = _episode("a")
    library, show = _library(episode)

    assert resurface_republished(library, show, ["a"]) == []


def test_a_show_not_routed_to_the_inbox_is_untouched() -> None:
    episode = _episode("a")
    library, show = _library(episode, route=False)
    _trim(library, show, episode)

    assert resurface_republished(library, show, ["a"]) == []


def test_only_the_named_guids_are_considered() -> None:
    one, two = _episode("a"), _episode("b")
    library, show = _library(one, two)
    _trim(library, show, one)
    _trim(library, show, two)

    returned = resurface_republished(library, show, ["a"])

    assert [e.guid for e in returned] == ["a"]
    assert library.inbox_assignments[inbox_key(show.id, "b")] == TRIMMED_MARKER


def test_nothing_republished_does_nothing() -> None:
    library, show = _library(_episode("a"))
    assert resurface_republished(library, show, []) == []


def test_several_episodes_can_return_at_once() -> None:
    one, two, three = _episode("a"), _episode("b"), _episode("c", played=True)
    library, show = _library(one, two, three)
    for episode in (one, two, three):
        _trim(library, show, episode)

    returned = resurface_republished(library, show, ["a", "b", "c"])

    assert sorted(e.guid for e in returned) == ["a", "b"], "the played one stays out"


# -- end to end --------------------------------------------------------------


def test_a_refresh_that_re_publishes_a_trimmed_episode_brings_it_back() -> None:
    """The whole journey: trimmed, re-issued by the publisher, back."""
    episode = _episode("a")
    library, show = _library(episode)
    _trim(library, show, episode)

    republished: list[str] = []
    merge_episodes(show, [_episode("a", published="2026-08-13T00:00:00")], republished=republished)
    returned = resurface_republished(library, show, republished)

    assert [e.guid for e in returned] == ["a"]
    assert show.episodes[0].published == "2026-08-13T00:00:00", "metadata still refreshes"
