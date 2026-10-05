"""Which feeds are healthy, which are failing, and which have gone quiet (R2).

Cast already knows all of this. :mod:`quill.core.podcasts.check_state` records,
per podcast, when it was last read, how many checks have failed in a row, and
when it last carried something new -- and it uses those three facts to decide
when to check and when to speak. What it has never done is let somebody **ask**.

That asymmetry is the whole reason this module exists. The notices are latched:
a failing feed says so once per run of failures, and a quiet one once per
silence, which is right for an app that must not nag and wrong for a listener
who heard something a week ago and now wants to know what is going on. "Which of
my sixty podcasts is broken" had no answer at all except subscribing to each one
again and watching.

So: a report, built from the bookkeeping that is already there, and **no new
network code**. Reading this file never checks a feed. The window built on it
offers Retry, and a retry is the refresh Cast already has.

Two decisions worth naming:

* **Worst first.** A report sorted by title is a list you read all of; a report
  sorted by trouble is one you read the top of. A screen-reader user pays for
  every row, so the rows that need something come first, and the healthy
  majority sits below where it can be ignored.
* **A failing feed is never described as abandoned.** Every sentence about
  failure says Cast is still trying, because "this feed has failed eleven times"
  reads as "and I gave up", which is not what happens and would send somebody
  off to re-subscribe to a podcast that is merely having a bad week.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from quill.core.podcasts import feed_problems, schedule_policy
from quill.core.podcasts.check_state import (
    failure_kind,
    failure_reason,
    failure_run,
    is_empty,
    last_checked,
    last_published,
)
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "EMPTY_RANK",
    "FeedRow",
    "QUIET_DAYS",
    "failing_rows",
    "rows",
    "summary",
]

#: How long a feed must have published nothing before the report mentions it.
#: Deliberately *not* the per-podcast ``quiet_feed_weeks`` setting, which decides
#: when Cast **speaks** unprompted: a listener who opened this window is asking,
#: and a report that hid a three-month silence because the setting was off would
#: be answering a question nobody asked. Six weeks is long enough that a monthly
#: show is not flagged for being monthly.
QUIET_DAYS = 42

#: Where an empty feed sits: below a failing one, above everything else. It
#: answers, so it is not failing, and it has nothing to play, so it is not OK
#: either -- and it used to read "OK", which is how 29 emptied feeds in one
#: real library went unnoticed (check.md bug 3).
EMPTY_RANK = 15


@dataclass(frozen=True, slots=True)
class FeedRow:
    """One podcast's health, as the report shows it.

    Ordering carries in ``rank``: lower is worse, and it is computed here rather
    than in the window so the window cannot sort it wrongly and so the order is
    something a test can assert.
    """

    show_id: str
    title: str
    feed_url: str
    checked: datetime | None
    published: datetime | None
    failures: int
    status: str
    rank: int
    #: "3 hours ago" / "never", computed when the report was built. Stored
    #: rather than derived on demand because the row must describe the same
    #: moment the rest of the report does -- a row that read the clock
    #: itself described a different instant from its own status, and made
    #: the wording impossible to assert.
    checked_ago: str = "never"
    published_ago: str = "never"
    #: The schedule sentence and when it next fires (qc.md 5e), so "when
    #: will it look again?" is a column rather than a guess.
    schedule: str = ""
    next_check: str = "never"
    #: The last failure's plain reason and its kind (check.md bug 8), or "".
    reason: str = ""
    kind: str = ""

    @property
    def is_failing(self) -> bool:
        return self.failures > 0

    @property
    def is_empty(self) -> bool:
        return self.rank == EMPTY_RANK

    @property
    def worth_a_search(self) -> bool:
        """Whether Find This Show's New Feed is the useful next step: the feed is
        failing in a way that will not come back at this address, or it is
        empty. Not for a slow host or a bot check -- the show has not moved."""
        if self.is_local:
            return False
        return self.is_empty or (self.is_failing and self.kind in feed_problems.WORTH_A_SEARCH)

    @property
    def is_local(self) -> bool:
        """A local show has no feed, so Retry and Copy Feed Address mean nothing."""
        return not self.feed_url

    def row(self) -> str:
        """The whole row as one sentence, for a list a person hears.

        Status first. The columns after it are context, and context read before
        the thing it is context for makes somebody wait through four dates to
        find out whether this row needed them at all.
        """
        return ", ".join([
            self.title,
            self.status,
            f"last checked {self.checked_ago}",
            f"last new episode {self.published_ago}",
            f"next check {self.next_check}",
        ])


def _ago(moment: datetime | None, *, now: datetime | None = None) -> str:
    """ "3 days ago", "just now", "never" -- said the way somebody says it.

    An exact timestamp is the wrong answer here twice over: it is long to hear,
    and nobody is asking what time Tuesday's check ran. They are asking whether
    it was recent.
    """
    if moment is None:
        return "never"
    delta = (now or datetime.now(UTC)) - moment
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"  # a clock that moved backwards is not worth a sentence
    if seconds < 90:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'' if hours == 1 else 's'} ago"
    days = hours // 24
    if days < 14:
        return f"{days} day{'' if days == 1 else 's'} ago"
    weeks = days // 7
    if weeks < 9:
        return f"{weeks} weeks ago"
    months = days // 30
    if months < 24:
        return f"{months} month{'' if months == 1 else 's'} ago"
    return f"{days // 365} years ago"


def _status_and_rank(
    show: PodcastShow,
    *,
    failures: int,
    checked: datetime | None,
    published: datetime | None,
    now: datetime,
    reason: str = "",
    empty: bool = False,
) -> tuple[str, int]:
    """What to say about this feed, and how far up the list it goes.

    The ranks are spaced so a later kind of trouble can be inserted between two
    of them without renumbering the ones a test names.

    A failing row says **why** (check.md bug 8). "Failing, 3 checks in a row"
    told a listener something was wrong and nothing about what, so the only
    next step was to guess.
    """
    if failures > 0:
        said = f"Failing, {failures} check{'' if failures == 1 else 's'} in a row"
        if reason:
            said += f": {reason.rstrip('.')}"
        return (f"{said} (Cast is still trying)", 10)
    if empty and show.feed_url:
        return ("Empty: the feed has no episodes", EMPTY_RANK)
    if not show.feed_url:
        # A local show is not broken; it simply has no feed to check. Its own
        # rank, below trouble and above healthy feeds, because somebody scanning
        # for problems should meet it once and learn it is not one.
        return ("Local files, no feed to check", 40)
    if checked is None:
        return ("Never checked yet", 20)
    if published is not None and (now - published).days >= QUIET_DAYS:
        return (f"Quiet, nothing new for {(now - published).days // 7} weeks", 30)
    return ("OK", 50)


def rows(library: PodcastLibrary, *, now: datetime | None = None) -> list[FeedRow]:
    """Every subscription's health, worst first.

    Ties inside a rank break on the *least recently checked*, then on title, so
    the order is stable between two openings of the window -- a list that
    reshuffles under a screen-reader cursor is unusable, and two feeds failing
    the same number of times is the common case, not the rare one.
    """
    moment = now or datetime.now(UTC)
    built: list[FeedRow] = []
    for show in library.shows:
        failures = failure_run(library, show)
        checked = last_checked(library, show)
        published = last_published(library, show)
        reason = failure_reason(library, show) if failures else ""
        status, rank = _status_and_rank(
            show,
            failures=failures,
            checked=checked,
            published=published,
            now=moment,
            reason=reason,
            empty=is_empty(library, show),
        )
        built.append(
            FeedRow(
                show_id=show.id,
                title=show.title or "an untitled podcast",
                feed_url=show.feed_url,
                checked=checked,
                published=published,
                failures=failures,
                status=status,
                rank=rank,
                checked_ago=_ago(checked, now=moment),
                published_ago=_ago(published, now=moment),
                schedule=schedule_policy.describe_for(library, show),
                next_check=schedule_policy.next_check_words(
                    schedule_policy.next_check(library, show, now=moment), now=moment
                ),
                reason=reason,
                kind=failure_kind(library, show) if failures else "",
            )
        )
    built.sort(
        key=lambda item: (
            item.rank,
            -item.failures,
            item.checked.timestamp() if item.checked is not None else 0.0,
            item.title.lower(),
        )
    )
    return built


def failing_rows(report: list[FeedRow]) -> list[FeedRow]:
    """The rows Retry All Failed acts on. Only genuine failures -- a quiet feed
    is working perfectly and retrying it would say "nothing new" and teach the
    listener that the button does nothing."""
    return [item for item in report if item.is_failing]


def summary(report: list[FeedRow]) -> str:
    """One line for the top of the window, announced once when it opens.

    The good case is a *sentence*, not a count of zero: "60 podcasts, none
    failing" is what somebody opened the window to hear, and "0 failing" makes
    them work out that zero is the good number.
    """
    if not report:
        return "No podcasts yet."
    failing = len(failing_rows(report))
    empty = len([item for item in report if item.is_empty])
    quiet = len([item for item in report if item.rank == 30])
    total = len(report)
    head = f"{total} podcast{'' if total == 1 else 's'}"
    if not failing and not quiet and not empty:
        return f"{head}, all checking normally."
    parts = []
    if failing:
        parts.append(f"{failing} failing")
    if empty:
        parts.append(f"{empty} empty")
    if quiet:
        parts.append(f"{quiet} gone quiet")
    joined = ", ".join(parts[:-1]) + f" and {parts[-1]}" if len(parts) > 1 else parts[0]
    return f"{head}, {joined}. Worst first."
