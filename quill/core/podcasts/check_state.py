"""Per-podcast check bookkeeping: when, how often, and when to say something.

Cast's background check had one stamp for the whole library, which was exactly
right while every podcast was checked on the same interval. It stops being
right the moment a podcast can have a **cadence of its own** (7.1): a shared
stamp can say when *a* check ran, and cannot say whether this particular
podcast's own hour has elapsed.

So each podcast gets three small facts, and the two notices the proposal asked
for fall out of them almost for free:

* ``checked`` -- when this feed was last read. The cadence is measured from
  here, so a daily news show checking hourly and a weekly interview checking
  daily coexist without either waiting on the other.
* ``failures`` -- consecutive failed checks, reset by any success. **The check
  never gives up**; this only decides when you are told (7.19).
* ``published`` -- when this feed last carried something new. A podcast that
  ends does so silently, and this is the only notice anybody gets that it did.

Two rules run through it:

* **Nothing here stops a check.** Every fact is used to decide *when* to check
  and *whether to speak*, never whether to keep trying. A feed that has failed
  forty times is still checked; it is simply mentioned once.
* **A notice fires once per event, not once per check.** A gone-quiet podcast
  that is checked hourly must not say so hourly, which is what ``notified``
  latches -- and publishing again clears the latch, so the *next* silence is
  reported too.

wx-free, strict-typed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

_CHECKED = "checked"
_FAILURES = "failures"
_PUBLISHED = "published"
_NOTIFIED_QUIET = "quiet_notified"
_NOTIFIED_FAILED = "failed_notified"


def _state(library: PodcastLibrary, show: PodcastShow) -> dict[str, object]:
    return library.show_check_state.setdefault(show.id, {})


def _stamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def last_checked(library: PodcastLibrary, show: PodcastShow) -> datetime | None:
    return _stamp(_state(library, show).get(_CHECKED))


def is_due(library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None) -> bool:
    """Whether this podcast's own cadence says it should be checked now.

    A cadence of zero is *manually only* -- an answer, not the absence of one --
    so it is never due. A podcast never checked before is always due, which is
    what makes a newly subscribed show arrive without waiting an hour for it.
    """
    from quill.core.podcasts.show_policy import cadence_minutes

    minutes = cadence_minutes(library, show)
    if minutes <= 0:
        return False
    previous = last_checked(library, show)
    if previous is None:
        return True
    return (now or datetime.now(UTC)) - previous >= timedelta(minutes=minutes)


def record_success(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    new_episodes: int = 0,
    now: datetime | None = None,
) -> None:
    """A check finished. Clears the failure run, and the notices it earned.

    Publishing something clears the gone-quiet latch as well as the stamp, so a
    podcast that goes quiet, comes back and goes quiet again is reported both
    times rather than once.
    """
    moment = (now or datetime.now(UTC)).isoformat()
    state = _state(library, show)
    state[_CHECKED] = moment
    state[_FAILURES] = 0
    state.pop(_NOTIFIED_FAILED, None)
    if new_episodes:
        state[_PUBLISHED] = moment
        state.pop(_NOTIFIED_QUIET, None)


def record_failure(
    library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None
) -> int:
    """A check failed; returns the length of the run it is part of."""
    state = _state(library, show)
    state[_CHECKED] = (now or datetime.now(UTC)).isoformat()
    try:
        failures = int(state.get(_FAILURES, 0)) + 1  # type: ignore[arg-type]
    except (TypeError, ValueError):
        failures = 1
    state[_FAILURES] = failures
    return failures


def failure_run(library: PodcastLibrary, show: PodcastShow) -> int:
    try:
        return max(0, int(_state(library, show).get(_FAILURES, 0)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def last_published(library: PodcastLibrary, show: PodcastShow) -> datetime | None:
    """When this feed last carried something new, as far as Cast has seen.

    Falls back to the newest episode's own date, so a podcast that has been
    subscribed for a year without this bookkeeping does not read as having
    gone quiet the moment the feature ships.
    """
    stored = _stamp(_state(library, show).get(_PUBLISHED))
    if stored is not None:
        return stored
    from quill.core.podcasts.row_speech import _parse  # noqa: PLC2701 - one parser, not two

    moments = [_parse(episode.published) for episode in show.episodes]
    real = [moment for moment in moments if moment is not None]
    return max(real) if real else None


# -- the two notices ---------------------------------------------------------


def failure_notice(library: PodcastLibrary, show: PodcastShow) -> str:
    """What to say about a feed that keeps failing, or ``""``.

    Latched: said once per run of failures, not once per failed check. Says
    plainly that Cast has not given up, because "this feed has failed" reads
    as "and I have stopped trying" and that is not what happens.
    """
    from quill.core.podcasts.show_policy import failed_check_notice

    wanted = failed_check_notice(library, show)
    if wanted <= 0:
        return ""
    state = _state(library, show)
    if state.get(_NOTIFIED_FAILED):
        return ""
    run = failure_run(library, show)
    if run < wanted:
        return ""
    state[_NOTIFIED_FAILED] = True
    return (
        f"{show.title} has failed to check {run} times in a row. Cast is still "
        "trying, and nothing has been unsubscribed or deleted -- the feed's "
        "address may have changed."
    )


def quiet_notice(library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None) -> str:
    """What to say about a podcast that has stopped publishing, or ``""``.

    A podcast that ends does not announce it. Without this the only signal is
    an absence, which is precisely the thing nobody notices -- and the reason
    the setting is per podcast is that "quiet for a fortnight" is news about a
    weekly show and nothing at all about an irregular one.
    """
    from quill.core.podcasts.show_policy import quiet_feed_weeks

    weeks = quiet_feed_weeks(library, show)
    if weeks <= 0:
        return ""
    state = _state(library, show)
    if state.get(_NOTIFIED_QUIET):
        return ""
    previous = last_published(library, show)
    if previous is None:
        return ""
    if (now or datetime.now(UTC)) - previous < timedelta(weeks=weeks):
        return ""
    state[_NOTIFIED_QUIET] = True
    return (
        f"{show.title} has published nothing for {weeks} "
        f"week{'' if weeks == 1 else 's'}. It is still subscribed and still "
        "being checked; nothing has changed except that there is nothing new."
    )


def forget(library: PodcastLibrary, show_id: str) -> None:
    """Drop a podcast's bookkeeping -- on unsubscribe, and nowhere else."""
    library.show_check_state.pop(show_id, None)


__all__ = [
    "failure_notice",
    "failure_run",
    "forget",
    "is_due",
    "last_checked",
    "last_published",
    "quiet_notice",
    "record_failure",
    "record_success",
]
