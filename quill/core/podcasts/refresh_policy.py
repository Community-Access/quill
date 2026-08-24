"""When a subscribed feed is checked, and which feeds are checked at all.

Two questions, one place, because they were being answered in three:
``PodcastCheckMonitor`` decided *when* for QUILL and Quill Cast, Quill Radio
decided *nothing* (it only refreshed a show you happened to open), and the
per-show "don't check this one" switch was a boolean called ``paused`` that the
Manager described as being about **downloads** while the refresh path quietly
read it as being about **feeds** as well.

**What paused means, said once.** ``PodcastShow.paused`` is *"leave this show
alone"*: no automatic feed check, no automatic download. It is the switch for a
show you want to keep in the list -- its back catalogue, its place, its notes --
without it costing you a request every hour forever. A finished show, a seasonal
show between seasons, an archive you dip into. The label now says so.

**And what it must never mean: unreachable.** A paused show is still a show, so
**Refresh** on its own row works, always, and ignores the pause completely
(:func:`shows_to_refresh` with ``force=True``). That is the whole reason a pause
is safe to offer: it costs nothing you cannot undo with one keystroke on the row
in front of you. A switch that could strand a show would be a trap.

**The cadence is the listener's, and "manually only" is one of its answers.**
Not a hidden default, not a compromise: somebody on a metered connection, or
somebody who simply wants the app quiet, is entitled to a podcast client that
never reaches the network unless asked. That is why the interval list ends at
Manually rather than starting at fifteen minutes and calling it off.

wx-free, strict-typed, pure -- no clock of its own, no store, no network. The
callers supply *now* and the shows; this decides.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

#: How often the automatic check may run, as ``(minutes, label)``. 0 is
#: "never on its own". The gaps widen as they grow because the difference
#: between 15 and 30 minutes matters to somebody and the difference between 12
#: and 13 hours does not.
INTERVAL_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "Manually only -- never check on its own"),
    (15, "Every 15 minutes"),
    (30, "Every 30 minutes"),
    (60, "Every hour"),
    (180, "Every 3 hours"),
    (360, "Every 6 hours"),
    (720, "Every 12 hours"),
    (1440, "Once a day"),
)

#: The shipped answer. Manual, deliberately: an app that starts reaching the
#: network on a schedule nobody chose is an app making a decision that costs
#: somebody else's data allowance.
DEFAULT_INTERVAL_MINUTES = 0

#: Never check more often than this, whatever a stored file claims. Feeds are
#: published on the order of days; a client hammering one every minute is a
#: client being rude on its listener's behalf.
MIN_INTERVAL_MINUTES = 5
MAX_INTERVAL_MINUTES = 7 * 24 * 60


def normalize_interval(value: object) -> int:
    """A stored interval as a sane number of minutes (pure).

    Anything unreadable reads as manual -- the quiet answer, because a typo in
    a settings file should never start network traffic nobody asked for.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT_INTERVAL_MINUTES
    minutes = int(value)
    if minutes <= 0:
        return 0
    return max(MIN_INTERVAL_MINUTES, min(MAX_INTERVAL_MINUTES, minutes))


def interval_index(value: object) -> int:
    """Which row of :data:`INTERVAL_CHOICES` a stored interval is (pure).

    An interval that is valid but not one of the offered rows (a hand-edited
    file, or a value from a build that offered different rows) answers with the
    nearest row at or below it, so the control shows something true rather than
    silently rewriting the listener's number to a default.
    """
    minutes = normalize_interval(value)
    best = 0
    for position, (offered, _label) in enumerate(INTERVAL_CHOICES):
        if offered <= minutes:
            best = position
    return best


def interval_from_index(position: object) -> int:
    """The interval at *position*, or the default. Total for a wx selection."""
    if not isinstance(position, int) or not 0 <= position < len(INTERVAL_CHOICES):
        return DEFAULT_INTERVAL_MINUTES
    return INTERVAL_CHOICES[position][0]


def interval_label(value: object) -> str:
    """The label for a stored interval, for a status line or a readout."""
    return INTERVAL_CHOICES[interval_index(value)][1]


def is_paused(show: Any) -> bool:
    """Whether this show is left alone by the automatic check (pure)."""
    return bool(getattr(show, "paused", False))


def can_refresh(show: Any) -> bool:
    """Whether this show *has* a feed to refresh at all (pure).

    A local show -- audio dropped into a watched folder -- has no feed address,
    so refreshing it is not a thing that can happen, and offering it would be
    offering a verb that answers nothing.
    """
    return bool(str(getattr(show, "feed_url", "") or "").strip())


def shows_to_refresh(shows: Iterable[Any], *, force: bool = False) -> list[Any]:
    """The shows an automatic check should ask about (pure).

    ``force=True`` is the manual Refresh: it skips only the shows that have no
    feed, because a listener who pressed Refresh on a paused show has just told
    you, in the clearest possible terms, that they want this one checked now.
    """
    return [show for show in shows if can_refresh(show) and (force or not is_paused(show))]


def stamp_now(now: float) -> str:
    """*now* (unix seconds) as the stored form of "checked at". Pure."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(max(0.0, float(now)), tz=UTC).isoformat()


def seconds_since(stamp: object, now: float) -> float | None:
    """How long ago *stamp* was, or None when it cannot be read (pure)."""
    from datetime import UTC, datetime

    text = str(stamp or "").strip()
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0.0, float(now) - moment.timestamp())


def is_due(last_checked: object, interval_minutes: object, now: float) -> bool:
    """Whether an automatic check should actually run (pure).

    **This is the guard against two apps polling the same feeds.** Quill Radio
    and QUILL Cast read one shared library, and each decides for itself whether
    *it* is the one that checks -- which is right, because a single shared
    switch would mean turning the check on in one app turned it on in the other
    and neither could be told not to. The cost of that rightness is that
    somebody running both gets two timers over one set of feeds, and a
    publisher sees twice the requests for no extra information.

    So the *stamp* is shared even though the *cadence* is not: whichever app
    checks writes when it did, and the other one, arriving inside the same
    interval, finds the work already done and stays quiet. Nobody is asked to
    configure this and nobody has to know it happens.

    A stamp that cannot be read means "never checked", which runs the check --
    the safe direction, since the worst case is one extra fetch.
    """
    minutes = normalize_interval(interval_minutes)
    if not minutes:
        return False
    elapsed = seconds_since(last_checked, now)
    if elapsed is None:
        return True
    # A small tolerance, because two timers started seconds apart should not
    # both fire: within a tenth of the interval of each other is the same tick.
    return elapsed >= (minutes * 60) * 0.9


def describe_schedule(interval_minutes: object, *, on_launch: bool = False) -> str:
    """The whole policy as one spoken sentence (pure).

    Says what it does **and what it does not do**, in that order, because every
    misread of a setting in this area has been about the second half: whether
    "check every hour" also downloads, whether it covers paused shows, whether
    turning it off means the app never updates at all.
    """
    minutes = normalize_interval(interval_minutes)
    if not minutes:
        opening = (
            "Subscribed feeds are checked when you open a show, when you press "
            "Refresh, and at launch."
            if on_launch
            else "Subscribed feeds are checked only when you open a show or press Refresh."
        )
    else:
        every = (
            interval_label(minutes).replace("Every ", "every ").replace("Once a day", "once a day")
        )
        opening = f"Subscribed feeds are checked {every}"
        opening += ", starting at launch." if on_launch else ", but not at launch."
    return (
        f"{opening} Paused shows are skipped, and Refresh on a show's own row "
        "checks it anyway. Checking a feed reads the episode list; it does not "
        "download any audio."
    )


def summarise_check(new_by_show: Sequence[tuple[str, int]]) -> str:
    """What one completed check should say out loud (pure).

    Counted, and named where naming is possible: "3 new episodes" tells you
    something happened, and "2 in Blind Abilities, 1 in Main Menu" tells you
    whether it is something you care about. Beyond three shows it goes back to
    a count, because a sentence listing nine shows is a sentence nobody hears
    the end of.
    """
    found = [(title, count) for title, count in new_by_show if count > 0]
    total = sum(count for _title, count in found)
    if not total:
        return "No new episodes."
    if len(found) <= 3:
        parts = [f"{count} in {title}" for title, count in found]
        return f"{total} new episode{'' if total == 1 else 's'}: {', '.join(parts)}."
    return f"{total} new episodes across {len(found)} shows." if total != 1 else "1 new episode."
