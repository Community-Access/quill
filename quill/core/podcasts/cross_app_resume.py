"""An episode started in Quill Radio picks up in QUILL Cast, and back again.

Both apps can play the same subscribed episode, and until now only one
direction of that fact travelled: ``radio_listens`` was a **handoff** --
Radio appended what it heard, Cast merged it at its next launch, and nothing
went the other way. Half an episode heard in Cast over lunch left Radio none
the wiser, and even the Radio-to-Cast direction only arrived at a launch,
which is the one moment somebody is least likely to be mid-episode
(list.md 11.11).

What was missing was never a format. Listening Places already defines what a
place *is*, and ``radio_listens`` already keys one by the episode's audio
address. What was missing is **one shared local store both apps write** and
**the write on pause** -- so this module is the small amount of decision-making
that turns the handoff file into a shared place, plus the rule for what
happens when the two apps disagree.

**The rule: last write wins, not furthest wins.** The same rule
:mod:`quill.core.podcasts.position_sync` states for cross-device sync, for
the same reason. Furthest-wins sounds generous and is wrong: somebody who
skipped to the end to check the outro, then went back to the middle, has
*decided* the middle is where they are, and an app that dragged them forward
again would be overruling them with arithmetic.

**A finish is a finish.** If either app says the episode finished, it is
finished, whichever is newer -- because "finished" and "at 0:00" are the same
stored state (position_sync.mark_played zeroes the position), and reading a
newer zero as "start again" would undo a completion every time.

Pure and wx-free: it takes two records and answers which one to use.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Place", "better_place", "describe_resume", "should_seek"]

#: How far in a place has to be before it is worth resuming to at all. Below
#: this the difference is a fumbled keypress, and jumping the listener two
#: seconds into an episode reads as a bug.
MIN_RESUME_MS = 15_000

#: How close to a stored place is "already there". Prevents a seek that would
#: move playback by less than the gap between two poll ticks.
SAME_PLACE_MS = 3_000


@dataclass(frozen=True, slots=True)
class Place:
    """Where one app thinks the listener is in one episode."""

    position_ms: int = 0
    #: Unix seconds when this was decided. The whole basis of the rule.
    updated_at: float = 0.0
    finished: bool = False
    #: Which app decided it ("radio", "cast"), for the spoken sentence.
    app: str = ""

    @property
    def is_a_place(self) -> bool:
        """Whether this is somewhere worth going back to."""
        return self.finished or self.position_ms >= MIN_RESUME_MS


def better_place(local: Place | None, shared: Place | None) -> Place | None:
    """Which of the two to use -- the later decision, with finish sticky.

    ``None`` for either side means "this app has no opinion", which is not the
    same as "position zero": a fresh install has no opinion about an episode
    the other machine is halfway through.
    """
    candidates = [place for place in (local, shared) if place is not None and place.is_a_place]
    if not candidates:
        return None
    if any(place.finished for place in candidates):
        # A finish is sticky. Report it as whichever app decided it, preferring
        # the finisher over a later "still at 0:00" from the other side.
        finished = [place for place in candidates if place.finished]
        return max(finished, key=lambda place: place.updated_at)
    return max(candidates, key=lambda place: place.updated_at)


def should_seek(current_ms: int, chosen: Place | None) -> bool:
    """Whether playback should actually move to *chosen*.

    False when there is no place, when the place is a finish (there is nothing
    to resume to), or when playback is already there -- a seek that moves the
    playhead by two seconds is noise, and on a streamed episode it costs a
    rebuffer.
    """
    if chosen is None or chosen.finished or not chosen.is_a_place:
        return False
    return abs(int(current_ms) - chosen.position_ms) > SAME_PLACE_MS


def describe_resume(chosen: Place | None, *, this_app: str) -> str:
    """What to say when a place from the *other* app is used. "" otherwise.

    Silent when the place is this app's own: resuming where you left off in
    the app you left off in is the ordinary behaviour and does not need
    narrating. It is the cross-app case that is surprising, and a jump nobody
    explained is indistinguishable from a bug.
    """
    if chosen is None or chosen.finished or not chosen.app or chosen.app == this_app:
        return ""
    from quill.core.media.timecode import format_spoken

    other = {"radio": "Quill Radio", "cast": "QUILL Cast"}.get(chosen.app, chosen.app)
    return f"Picking up where you left off in {other}, at {format_spoken(chosen.position_ms)}."
