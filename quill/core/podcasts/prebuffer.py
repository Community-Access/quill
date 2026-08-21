"""Getting the next episode ready before the current one ends.

The gap between two episodes in a queue is dead air, and its length is not the
few milliseconds people mean by "gapless" -- it is however long it takes to
resolve a source, open a network stream, fill a buffer and start decoding. On a
slow connection that is several seconds of silence, in the middle of a listening
session, with nothing to say what is happening.

True sample-accurate gapless playback is a property of the *decoder*, and neither
engine here offers it. What is achievable, and what actually removes the wait, is
**having the next episode's first seconds already on disk before the current one
ends**. The switch then costs an open and a seek rather than a download.

Four rules, and the last two are why this is not simply "download the next one":

* **Never at the expense of what is playing.** Prebuffering starts only in the
  final stretch of an episode, when the current download (if any) is long done.
* **Never for something already here.** A downloaded episode needs nothing; the
  work is skipped rather than repeated.
* **Never a commitment.** A prebuffer is a *cache*, not a download the listener
  asked for: it is capped, it lands in the playback cache rather than the
  library, and a prune may take it at any time.
* **Never over a metered connection the listener did not opt into.** It is a
  setting, and it is off unless asked for -- speculative bytes somebody pays for
  by the megabyte are not a courtesy.

wx-free, strict-typed, pure. What to fetch and when; never the fetching itself.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How close to the end of the current episode the next one starts loading.
#: Thirty seconds is comfortably longer than a stream takes to open on a poor
#: connection, and short enough that a listener who skips around does not
#: trigger it constantly.
LEAD_MS = 30_000

#: How much of the next episode is worth having early. Enough to cover the
#: open-and-fill that would otherwise be silence, and no more -- this is a
#: courtesy, not a download.
PREBUFFER_BYTES = 512 * 1024


@dataclass(frozen=True, slots=True)
class PrebufferPlan:
    """What (if anything) to fetch ahead, and why -- or why not."""

    should_fetch: bool = False
    show_id: str = ""
    episode_guid: str = ""
    url: str = ""
    byte_limit: int = PREBUFFER_BYTES
    #: In words, for the log and for a listener who asks. Never spoken
    #: unprompted: a player that narrates its own buffering is unbearable.
    reason: str = ""


def plan(
    *,
    enabled: bool,
    position_ms: int,
    duration_ms: int,
    next_show_id: str = "",
    next_episode_guid: str = "",
    next_url: str = "",
    next_is_local: bool = False,
    already_prebuffered: bool = False,
    on_metered: bool = False,
) -> PrebufferPlan:
    """Whether to start loading the next queue item now.

    Deliberately a pure decision with every input passed in: the caller knows
    what is playing and what is next, and this knows the policy. That split is
    what lets the policy be tested without a player, a queue or a network --
    which is also why *on_metered* is a plain flag rather than a call into
    ``core.net_metered`` from in here.
    """
    if not enabled:
        return PrebufferPlan(reason="Prebuffering is switched off.")
    if on_metered:
        # The clearest case of all for the metered guard: nobody asked for this
        # episode yet, and it may never be played at all.
        return PrebufferPlan(reason="Waiting until you are off a metered connection.")
    if already_prebuffered:
        return PrebufferPlan(reason="The next episode is already ready.")
    if not (next_show_id and next_episode_guid):
        return PrebufferPlan(reason="Nothing is queued after this.")
    if next_is_local:
        # A downloaded episode opens instantly; fetching anything would be
        # spending somebody's connection to save nothing.
        return PrebufferPlan(reason="The next episode is already on this computer.")
    if not next_url:
        return PrebufferPlan(reason="The next episode has no address to load yet.")
    if duration_ms <= 0:
        # A live item or a source that will not say how long it is: there is no
        # "nearly over" to detect, so there is no moment to start.
        return PrebufferPlan(reason="This episode has no known length, so there is no cue.")
    remaining = duration_ms - max(0, position_ms)
    if remaining > LEAD_MS:
        return PrebufferPlan(reason="Not near the end yet.")
    if remaining <= 0:
        return PrebufferPlan(reason="This episode has already finished.")
    return PrebufferPlan(
        should_fetch=True,
        show_id=next_show_id,
        episode_guid=next_episode_guid,
        url=next_url,
        reason=f"{remaining // 1000} seconds left, so the next episode is loading now.",
    )


def describe(plan_result: PrebufferPlan) -> str:
    """One sentence about the prebuffer state, for the log or on request.

    Never announced by itself. A player that says "buffering the next episode"
    unprompted is a player narrating its own internals at somebody trying to
    listen to a programme.
    """
    if plan_result.should_fetch:
        return f"Loading the next episode ahead of time. {plan_result.reason}"
    return plan_result.reason or "Nothing to load ahead."
