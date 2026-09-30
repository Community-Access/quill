"""Three verbs Earshot exposes to Siri, as keys and palette entries (R5).

Earshot publishes Play an Unheard Episode, Play Queue Shuffled and Clear Entire
Queue as Shortcuts actions, which on a phone means "say it and it happens". The
desktop equivalent of saying something is a key, and the desktop's advantage is
that a key works with the app in the background and needs no microphone.

All three are one-press verbs, and the interesting one is the first.

**Play an Unheard Episode is not "play a random thing".** It is the verb for a
listener who wants *something* on and does not want to choose, and the order it
looks in is the order somebody would look themselves:

1. **The queue**, if there is anything in it. The queue is a decision already
   made; overriding it to go hunting in the library would be the app second-
   guessing an explicit instruction.
2. **The Inbox**, next, for the same reason in weaker form: routing a show to the
   Inbox is a standing statement that its episodes are the ones awaiting a
   decision.
3. **Everything unplayed**, last.

Within a tier it takes the newest or the oldest, which the caller chooses --
Earshot offers both, and they are genuinely different intentions: newest is "what
is going on today", oldest is "let me work through the backlog". The default is
newest, because that is the one people press when they have not thought about it.

Two guarantees that keep this from being annoying:

* **Nothing already started is ever picked.** A resume position means somebody is
  in the middle of that episode, and starting it from a one-press "something
  unheard" key would be indistinguishable from losing their place. Continue
  Listening is the verb for that, and it already exists.
* **Clearing the queue is never silent, and never partial.** It reports the count
  it is about to discard so the confirmation is a real decision, and it is a
  single act: a queue half cleared is worse than either end state.

wx-free, strict-typed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "NEWEST",
    "OLDEST",
    "Pick",
    "clear_queue",
    "clear_queue_confirm",
    "nothing_unheard",
    "shuffle_whole_queue",
    "unheard_pick",
]

NEWEST = "newest"
OLDEST = "oldest"


@dataclass(frozen=True, slots=True)
class Pick:
    """What to play, and where it was found.

    *source* is part of the result rather than a detail of the search because the
    announcement needs it: "Playing the newest unheard episode, from the queue"
    and "... from your podcasts" tell a listener something they cannot otherwise
    find out about a key that chose on their behalf.
    """

    show: PodcastShow
    episode: PodcastEpisode
    source: str

    def announcement(self) -> str:
        return f"{self.episode.title}, from {self.source}"


def _unstarted(episode: PodcastEpisode) -> bool:
    """Genuinely unheard: not played, and not part-way through."""
    return not episode.played and int(getattr(episode, "position_ms", 0) or 0) <= 0


def _sort_key(pair: tuple[PodcastShow, PodcastEpisode]) -> tuple[str, str]:
    _show, episode = pair
    return (episode.published or "", episode.title or "")


def _pick_from(
    pairs: list[tuple[PodcastShow, PodcastEpisode]], order: str, source: str
) -> Pick | None:
    usable = [pair for pair in pairs if _unstarted(pair[1])]
    if not usable:
        return None
    usable.sort(key=_sort_key, reverse=order == NEWEST)
    show, episode = usable[0]
    return Pick(show=show, episode=episode, source=source)


def unheard_pick(library: PodcastLibrary, *, order: str = NEWEST) -> Pick | None:
    """One unheard episode to play, or ``None`` when there is nothing.

    Queue first, Inbox second, everything else third -- see the module docstring
    for why that order is not arbitrary. The queue is taken **in queue order**
    rather than by date: its order is a decision the listener made, and sorting
    it by date here would quietly answer a different question from the one the
    queue is an answer to.
    """
    for item in library.queue:
        show = library.find_show(item.show_id)
        if show is None:
            continue
        episode = show.find_episode(item.episode_guid)
        if episode is not None and _unstarted(episode):
            return Pick(show=show, episode=episode, source="the queue")

    from quill.core.podcasts.inbox import inbox_pairs

    found = _pick_from(inbox_pairs(library), order, "the Inbox")
    if found is not None:
        return found

    everything = [
        (show, episode)
        for show in library.shows
        for episode in show.episodes
        if not show.is_local or episode.downloaded_path
    ]
    return _pick_from(everything, order, "your podcasts")


def nothing_unheard(order: str = NEWEST) -> str:
    """What to say when there was nothing to pick.

    Names the two other places a listener would look, because "nothing unheard"
    invites the reasonable and wrong conclusion that the library is empty -- the
    usual cause is that everything unplayed is also part-started.
    """
    which = "newest" if order == NEWEST else "oldest"
    return (
        f"Nothing unheard to play. Anything you have already started is in "
        f"Continue Listening, and anything you have finished is still in its "
        f"podcast. ({which.capitalize()} first was the order asked for.)"
    )


def shuffle_whole_queue(library: PodcastLibrary, *, rng: random.Random | None = None) -> int:
    """Shuffle the entire queue in place; returns how many items moved through.

    A queue of one is left exactly as it is and answers 1 rather than 0: nothing
    changed, but the listener's queue does still hold one item, and reporting 0
    would read as "the queue is empty".
    """
    count = len(library.queue)
    if count > 1:
        (rng or random).shuffle(library.queue)
    return count


def clear_queue_confirm(library: PodcastLibrary) -> str:
    """The question Clear Entire Queue asks, or ``""`` when the queue is empty.

    Two facts, both load-bearing: **how many** (so the decision is informed --
    "clear the queue" feels very different at three items and at forty) and **what
    survives** (nothing is deleted, nothing is marked played, and the episodes
    stay in their podcasts). Without the second sentence this reads as a delete,
    which is the reason somebody would not press it.
    """
    count = len(library.queue)
    if not count:
        return ""
    return (
        f"Clear all {count} item{'' if count == 1 else 's'} from the Play Queue?\n\n"
        "Nothing is deleted and nothing is marked as played -- the episodes stay "
        "in their podcasts, and any downloads you have stay on this computer."
    )


def clear_queue(library: PodcastLibrary) -> int:
    """Empty the queue; returns how many items were in it.

    One act, not a loop the caller can interrupt: a half-cleared queue is a state
    nobody asked for and one the listener would have to inspect to discover.
    """
    count = len(library.queue)
    library.queue = []
    return count
