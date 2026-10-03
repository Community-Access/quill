"""One podcast's refresh schedule, resolved, and the questions asked of it (qc.md 5e).

The schedule itself is pure (:mod:`refresh_schedule`); this is where it meets
the library: which schedule a podcast has after the four levels are
resolved, what it has learned, what the publisher said, when it is next due,
and the sentence that describes all of that. The monitor asks :func:`is_due`
per podcast; Feed Check asks :func:`describe_for` and :func:`next_check`;
Preferences asks :func:`summary` for the one-line count.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.podcasts import check_state, refresh_schedule
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.refresh_schedule import Hint, Pattern, Schedule
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "describe_for",
    "hint_for",
    "is_due",
    "next_check",
    "next_check_words",
    "pattern_for",
    "schedule_for",
    "set_schedule",
    "summary",
    "switch",
]


def schedule_for(library: PodcastLibrary, show: PodcastShow | None) -> Schedule:
    """The schedule in force for *show* (the shared default when None).

    An empty setting at every level means "nobody chose one", and the legacy
    ``refresh_minutes`` answers instead -- which is the migration: nothing is
    rewritten, and nothing changes on upgrade.
    """
    from quill.core.podcasts.show_policy import setting

    saved = refresh_schedule.decode(setting(library, show, "refresh_schedule"))
    if saved is not None:
        return saved
    legacy = setting(library, show, "refresh_minutes")
    return refresh_schedule.from_legacy(legacy)


def set_schedule(library: PodcastLibrary, show: PodcastShow | None, schedule: Schedule) -> None:
    """Save *schedule* for *show*, or as the shared default when None."""
    from quill.core.podcasts import settings_catalog
    from quill.core.podcasts.settings_resolver import set_value
    from quill.core.podcasts.settings_types import LEVEL_GLOBAL, LEVEL_SHOW

    definition = settings_catalog.definition("refresh_schedule")
    if definition is None:
        return
    encoded = refresh_schedule.encode(schedule)
    if show is None:
        set_value(library, definition, encoded, level=LEVEL_GLOBAL)
    else:
        set_value(library, definition, encoded, level=LEVEL_SHOW, scope_id=show.id)


def switch(library: PodcastLibrary, show: PodcastShow | None, setting_id: str) -> bool:
    """One of the four fetching switches, resolved."""
    from quill.core.podcasts.show_policy import setting

    return bool(setting(library, show, setting_id))


def pattern_for(show: PodcastShow) -> Pattern | None:
    """What the learning found for this podcast, from its own episodes."""
    moments = [refresh_schedule.parse_published(episode.published) for episode in show.episodes]
    return refresh_schedule.learn([moment for moment in moments if moment is not None])


def hint_for(library: PodcastLibrary, show: PodcastShow) -> Hint:
    return check_state.hint(library, show)


def next_check(
    library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None
) -> datetime | None:
    """When this podcast is next looked at; None for never (manual, or paused)."""
    if getattr(show, "paused", False) or not show.feed_url:
        return None
    moment = now or datetime.now(UTC)
    schedule = schedule_for(library, show)
    published = [
        parsed
        for parsed in (
            refresh_schedule.parse_published(episode.published) for episode in show.episodes
        )
        if parsed is not None
    ]
    return refresh_schedule.next_due(
        schedule,
        moment,
        check_state.last_checked(library, show),
        published=published,
        hint=hint_for(library, show),
    )


def is_due(library: PodcastLibrary, show: PodcastShow, *, now: datetime | None = None) -> bool:
    """Whether the monitor should check this podcast now."""
    moment = now or datetime.now(UTC)
    due = next_check(library, show, now=moment)
    return due is not None and due <= moment


def describe_for(library: PodcastLibrary, show: PodcastShow | None) -> str:
    """The schedule sentence Feed Check, the menu and the confirmation all use."""
    schedule = schedule_for(library, show)
    if show is None:
        return refresh_schedule.describe(schedule)
    return refresh_schedule.describe(
        schedule, pattern=pattern_for(show), hint=hint_for(library, show)
    )


def next_check_words(due: datetime | None, *, now: datetime | None = None) -> str:
    """ "in 40 minutes", "now", "tomorrow at 06:00", "never"."""
    if due is None:
        return "never"
    moment = now or datetime.now(UTC)
    if due <= moment:
        return "now"
    gap = due - moment
    minutes = int(gap.total_seconds() // 60)
    if minutes < 60:
        return f"in {max(1, minutes)} minute{'' if minutes == 1 else 's'}"
    if minutes < 24 * 60 and due.date() == moment.date():
        return f"today at {due.astimezone().strftime('%H:%M')}"
    if minutes < 48 * 60:
        return f"tomorrow at {due.astimezone().strftime('%H:%M')}"
    return f"{due.astimezone().strftime('%A')} at {due.astimezone().strftime('%H:%M')}"


def summary(library: PodcastLibrary) -> str:
    """ "40 podcasts: 31 on the shared schedule, 6 learned, 3 manual." -- the
    Preferences line that says what the app is doing to the connection."""
    from quill.core.podcasts import settings_catalog
    from quill.core.podcasts.settings_resolver import has_override
    from quill.core.podcasts.settings_types import LEVEL_SHOW

    shows = [show for show in library.shows if show.feed_url]
    if not shows:
        return "No podcasts with a feed to check."
    definition = settings_catalog.definition("refresh_schedule")
    on_default = 0
    kinds: dict[str, int] = {}
    for show in shows:
        own = definition is not None and has_override(
            library, definition, level=LEVEL_SHOW, scope_id=show.id
        )
        if not own:
            on_default += 1
            continue
        kind = schedule_for(library, show).kind
        kinds[kind] = kinds.get(kind, 0) + 1
    parts = [f"{on_default} on the shared schedule"]
    words = {
        refresh_schedule.MANUAL: "manual",
        refresh_schedule.INTERVAL: "on their own interval",
        refresh_schedule.TIMES: "at set times",
        refresh_schedule.LEARNED: "learned",
        refresh_schedule.PUBLISHER: "on the publisher's hint",
    }
    for kind in refresh_schedule.KINDS:
        if kinds.get(kind):
            parts.append(f"{kinds[kind]} {words[kind]}")
    shared = refresh_schedule.describe(schedule_for(library, None)).rstrip(".")
    noun = "podcast" if len(shows) == 1 else "podcasts"
    return f"{len(shows)} {noun}: {', '.join(parts)}. The shared schedule is: {shared.lower()}."
