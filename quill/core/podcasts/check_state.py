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
* ``published`` -- when this feed last carried something new: the newest
  episode's **own** date, not the time of the check (check.md bug 2). A podcast
  that ends does so silently, and this is the only notice anybody gets that it
  did -- so stamping it with the clock, as the first check after an import used
  to, made a show that stopped in 2005 read as "just now".

And a few facts about the last answer, so Feed Check can say *why* and a check
can be cheap: the plain reason for the last failure and its kind (bugs 7 and
8), whether the feed was empty or cut off (bugs 3 and 13), whether a plain-http
address was read over https (bug 14), and the ETag / Last-Modified validators
for a conditional request next time (bug 9). All additive keys in the same
per-podcast dict; an older file simply lacks them.

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
from quill.core.podcasts.models_queue import coerce_int
from quill.core.podcasts.refresh_schedule import Hint
from quill.core.podcasts.subscriptions import PodcastLibrary

_CHECKED = "checked"
_FAILURES = "failures"
_PUBLISHED = "published"
_NOTIFIED_QUIET = "quiet_notified"
_NOTIFIED_FAILED = "failed_notified"
_REASON = "failure_reason"
_KIND = "failure_kind"
_EMPTY = "empty"
_TRUNCATED = "truncated"
_SECURE = "read_securely"
_ETAG = "etag"
_LAST_MODIFIED = "last_modified"
_VALIDATED_URL = "validated_url"
_REBASE = "rebase"
_TWINS = "twin_guids"


def _state(library: PodcastLibrary, show: PodcastShow) -> dict[str, object]:
    """This podcast's bookkeeping, creating it. For writers only."""
    return library.show_check_state.setdefault(show.id, {})


def _read(library: PodcastLibrary, show: PodcastShow) -> dict[str, object]:
    """This podcast's bookkeeping without creating it. For readers.

    The distinction is not tidiness. Every reader used to go through the
    ``setdefault`` above, so merely *asking* about a podcast added an empty
    entry -- and the Feed Check window asks about every podcast at once,
    which on a large library meant opening a report grew the saved file by
    a thousand empty dicts. A read should leave no trace.
    """
    return library.show_check_state.get(show.id) or {}


def _stamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def last_checked(library: PodcastLibrary, show: PodcastShow) -> datetime | None:
    return _stamp(_read(library, show).get(_CHECKED))


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


def newest_episode_date(show: PodcastShow) -> datetime | None:
    """The newest date any of this podcast's episodes carries, or None."""
    from quill.core.podcasts.row_speech import _parse  # noqa: PLC2701 - one parser, not two

    moments = [_parse(episode.published) for episode in show.episodes]
    real = [moment for moment in moments if moment is not None]
    return max(real) if real else None


def record_success(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    new_episodes: int = 0,
    now: datetime | None = None,
    published: datetime | None = None,
) -> None:
    """A check finished. Clears the failure run, and the notices it earned.

    *published* is the newest episode's own date. When given it **is** the
    "last published" stamp -- overwriting, so a library whose stamps were set
    from the clock by an older Cast is healed by its next check. Only when the
    feed gives no dates at all does a check that brought something new fall
    back to the clock, because "something arrived just now" is then the best
    anybody knows.

    Publishing something clears the gone-quiet latch as well, so a podcast that
    goes quiet, comes back and goes quiet again is reported both times rather
    than once.
    """
    moment = (now or datetime.now(UTC)).isoformat()
    state = _state(library, show)
    state[_CHECKED] = moment
    state[_FAILURES] = 0
    state.pop(_NOTIFIED_FAILED, None)
    state.pop(_REASON, None)
    state.pop(_KIND, None)
    if published is not None:
        stamp = published if published.tzinfo is not None else published.replace(tzinfo=UTC)
        state[_PUBLISHED] = stamp.isoformat()
    elif new_episodes:
        state[_PUBLISHED] = moment
    if new_episodes:
        state.pop(_NOTIFIED_QUIET, None)


def record_shape(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    empty: bool,
    truncated: bool = False,
    read_securely: bool = False,
) -> None:
    """What the last successful read looked like (bugs 3, 13 and 14).

    Stored only when true, so the common case -- a feed with episodes, under
    the size cap, read as given -- adds nothing to the saved file.
    """
    state = _state(library, show)
    for key, value in ((_EMPTY, empty), (_TRUNCATED, truncated), (_SECURE, read_securely)):
        if value:
            state[key] = True
        else:
            state.pop(key, None)


def is_empty(library: PodcastLibrary, show: PodcastShow) -> bool:
    """The last read found a feed with no episodes in it."""
    return bool(_read(library, show).get(_EMPTY))


def is_truncated(library: PodcastLibrary, show: PodcastShow) -> bool:
    """The last read was cut off at the size cap; the oldest episodes are missing."""
    return bool(_read(library, show).get(_TRUNCATED))


def read_securely(library: PodcastLibrary, show: PodcastShow) -> bool:
    """A plain-http address was last read over https."""
    return bool(_read(library, show).get(_SECURE))


def record_validators(
    library: PodcastLibrary, show: PodcastShow, etag: str, last_modified: str
) -> None:
    """Keep the response's ETag and Last-Modified for a conditional request.

    Tied to the address they came from: a podcast whose feed address changes
    must be read in full once, not asked "has this changed" about a feed the
    validators never described.
    """
    state = _state(library, show)
    if etag or last_modified:
        state[_ETAG] = str(etag or "")
        state[_LAST_MODIFIED] = str(last_modified or "")
        state[_VALIDATED_URL] = str(show.feed_url or "")
    else:
        for key in (_ETAG, _LAST_MODIFIED, _VALIDATED_URL):
            state.pop(key, None)


def validators(library: PodcastLibrary, show: PodcastShow) -> tuple[str, str]:
    """``(etag, last_modified)`` to send, or two empty strings.

    Empty when the podcast has no episodes yet -- a "not modified" answer is
    only useful to somebody who already has the feed -- or when the stored pair
    describes a different address.
    """
    read = _read(library, show)
    if not show.episodes or str(read.get(_VALIDATED_URL, "") or "") != str(show.feed_url or ""):
        return ("", "")
    return (str(read.get(_ETAG, "") or ""), str(read.get(_LAST_MODIFIED, "") or ""))


def record_failure(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    now: datetime | None = None,
    reason: str = "",
    kind: str = "",
) -> int:
    """A check failed; returns the length of the run it is part of.

    *reason* is the plain sentence for this failure and *kind* its sort
    (:mod:`quill.core.podcasts.feed_problems`). Kept so Feed Check can say
    *why* a feed is failing, and offer to find the show's new feed when the
    old one is not coming back (check.md bug 8).
    """
    state = _state(library, show)
    state[_CHECKED] = (now or datetime.now(UTC)).isoformat()
    if reason:
        state[_REASON] = str(reason)
    if kind:
        state[_KIND] = str(kind)
    # coerce_int already answers 0 for a stored value that is not a number, so
    # a hand-edited state file cannot stop a podcast being checked.
    failures = coerce_int(state.get(_FAILURES, 0), 0) + 1
    state[_FAILURES] = failures
    return failures


def failure_run(library: PodcastLibrary, show: PodcastShow) -> int:
    return max(0, coerce_int(_read(library, show).get(_FAILURES, 0), 0))


def failure_reason(library: PodcastLibrary, show: PodcastShow) -> str:
    """The plain sentence for the last failure, or ``""``."""
    return str(_read(library, show).get(_REASON, "") or "")


def failure_kind(library: PodcastLibrary, show: PodcastShow) -> str:
    """The sort of the last failure (a :mod:`feed_problems` kind), or ``""``."""
    return str(_read(library, show).get(_KIND, "") or "")


_HINT_MINUTES = "hint_minutes"
_HINT_WORDS = "hint_words"


def record_hint(library: PodcastLibrary, show: PodcastShow, minutes: int, words: str) -> None:
    """What the feed declared about its own cadence (qc.md 5e, the publisher's
    hint). Written only when the feed says something; a feed that stops saying
    it keeps the last answer, which is better than forgetting it hourly."""
    if minutes <= 0:
        return
    state = _state(library, show)
    state[_HINT_MINUTES] = int(minutes)
    state[_HINT_WORDS] = str(words or "")


def hint(library: PodcastLibrary, show: PodcastShow) -> Hint:
    read = _read(library, show)
    return Hint(
        max(0, coerce_int(read.get(_HINT_MINUTES, 0), 0)), str(read.get(_HINT_WORDS, "") or "")
    )


def last_published(library: PodcastLibrary, show: PodcastShow) -> datetime | None:
    """When this feed last carried something new, as far as Cast has seen.

    Falls back to the newest episode's own date, so a podcast that has been
    subscribed for a year without this bookkeeping does not read as having
    gone quiet the moment the feature ships.
    """
    stored = _stamp(_read(library, show).get(_PUBLISHED))
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
    from quill.core.podcasts.feed_problems import WORTH_A_SEARCH

    reason = failure_reason(library, show)
    said = f"{show.title} has failed to check {run} times in a row."
    if reason:
        said += f" {reason}"
    said += " Cast is still trying, and nothing has been unfollowed or deleted."
    # "Look for its new feed" only where that is the likely story -- a removed
    # feed, a domain that is gone, a web page where the feed was. Said about a
    # slow host, "the address may have changed" sent people looking for a feed
    # that had not moved (check.md bug 8).
    if failure_kind(library, show) in WORTH_A_SEARCH:
        said += " Find This Show's New Feed, in Feed Check, can look for where it went."
    return said


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
        f"week{'' if weeks == 1 else 's'}. You still follow it and it is still "
        "being checked; nothing has changed except that there is nothing new."
    )


def mark_rebase(library: PodcastLibrary, show: PodcastShow) -> None:
    """The podcast's feed address was replaced: start its bookkeeping afresh.

    Everything that described the old address goes -- the failure run and its
    reason, the validators, "empty", the latched notices -- and the next
    successful read is marked as a starting point (:func:`take_rebase`).
    """
    state = _state(library, show)
    for key in (
        _FAILURES,
        _REASON,
        _KIND,
        _EMPTY,
        _TRUNCATED,
        _SECURE,
        _ETAG,
        _LAST_MODIFIED,
        _VALIDATED_URL,
        _NOTIFIED_FAILED,
        _NOTIFIED_QUIET,
        _TWINS,
    ):
        state.pop(key, None)
    state[_REBASE] = True


def twin_guids(library: PodcastLibrary, show: PodcastShow) -> frozenset[str]:
    """Episode ids on a replaced feed that are episodes the podcast already has.

    After Replace Feed the new host lists the same episodes under its own ids.
    The podcast keeps its own copies (with what you have heard of them), and
    these ids are remembered so a later read does not add them back as new.
    """
    raw = _read(library, show).get(_TWINS)
    return frozenset(str(item) for item in raw) if isinstance(raw, list) else frozenset()


def add_twin_guids(library: PodcastLibrary, show: PodcastShow, guids: set[str]) -> None:
    if not guids:
        return
    state = _state(library, show)
    state[_TWINS] = sorted(twin_guids(library, show) | guids)


def take_rebase(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether this read is the first since the address was replaced; clears it."""
    state = library.show_check_state.get(show.id)
    if not state or not state.get(_REBASE):
        return False
    state.pop(_REBASE, None)
    return True


def forget(library: PodcastLibrary, show_id: str) -> None:
    """Drop a podcast's bookkeeping -- on unsubscribe, and nowhere else."""
    library.show_check_state.pop(show_id, None)


__all__ = [
    "add_twin_guids",
    "failure_kind",
    "failure_notice",
    "failure_reason",
    "failure_run",
    "forget",
    "is_due",
    "is_empty",
    "is_truncated",
    "last_checked",
    "last_published",
    "mark_rebase",
    "newest_episode_date",
    "quiet_notice",
    "read_securely",
    "record_failure",
    "record_shape",
    "record_success",
    "record_validators",
    "take_rebase",
    "twin_guids",
    "validators",
]
