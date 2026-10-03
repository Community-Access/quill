"""What QUILL Cast tells you, as records first and sounds second (qc.md 5b).

Jeff: "don't forget about notifications like Quill Radio has."

The store is the family's (:mod:`quill.core.notifications`); this module is
what Cast puts in it and what it says about it. Six kinds, each with its own
switch in Preferences (the defaults) and, where it is about one podcast, in
Settings for This Podcast. Nothing else is ever recorded, because a list that
holds everything is a list nobody reads.

* **new_episode** -- a feed carried something new.
* **feed_failed** -- a feed has failed N times (latched: once per run).
* **gone_quiet** -- a podcast has stopped publishing (latched).
* **download_finished** -- a download you started by hand finished.
* **sleep_last_minute** -- the sleep timer's last minute.
* **import_finished** -- a Personal Audio import finished.

:func:`digest` is the one sentence on launch about what arrived while Cast
was closed: "Since yesterday: 4 new episodes from 3 podcasts. They are in the
Inbox." Never more than one sentence, off in Quiet Hours, off by a checkbox.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "APP",
    "KINDS",
    "KIND_LABELS",
    "SWITCH_FIELDS",
    "digest",
    "is_kind",
    "kind_of",
    "record",
    "since_sentence",
    "unread_for_cast",
    "wants",
]

APP = "QUILL Cast"

NEW_EPISODE = "new_episode"
FEED_FAILED = "feed_failed"
GONE_QUIET = "gone_quiet"
DOWNLOAD_FINISHED = "download_finished"
SLEEP_LAST_MINUTE = "sleep_last_minute"
IMPORT_FINISHED = "import_finished"
KINDS: tuple[str, ...] = (
    NEW_EPISODE,
    FEED_FAILED,
    GONE_QUIET,
    DOWNLOAD_FINISHED,
    SLEEP_LAST_MINUTE,
    IMPORT_FINISHED,
)
KIND_LABELS: dict[str, str] = {
    NEW_EPISODE: "A new episode",
    FEED_FAILED: "A feed that keeps failing",
    GONE_QUIET: "A podcast that has gone quiet",
    DOWNLOAD_FINISHED: "A download you started finished",
    SLEEP_LAST_MINUTE: "The sleep timer's last minute",
    IMPORT_FINISHED: "A Personal Audio import finished",
}
#: The ``PodcastHistory`` field that switches each kind, all on by default.
SWITCH_FIELDS: dict[str, str] = {kind: f"notify_{kind}" for kind in KINDS}


def is_kind(value: object) -> bool:
    return str(value or "") in KINDS


def kind_of(notice: Any) -> str:
    """The kind a stored notice carries (its ``category``), or ""."""
    category = str(getattr(notice, "category", "") or "")
    return category if category in KINDS else ""


def wants(history: Any, kind: str) -> bool:
    """Whether the listener left this kind switched on."""
    field_name = SWITCH_FIELDS.get(kind)
    if field_name is None:
        return False
    return bool(getattr(history, field_name, True))


def record(
    history: Any,
    kind: str,
    *,
    title: str,
    body: str,
    target: str = "",
) -> bool:
    """Write one notice, when its switch is on. Returns whether it was written.

    A record first: the sound and the toast are the caller's, and are gated
    separately, because the record is what survives being away.
    """
    if not wants(history, kind):
        return False
    from quill.core.notifications import add_notice

    try:
        add_notice(app=APP, title=title, body=body, target=target, category=kind)
    except Exception:  # noqa: BLE001 - a notice that cannot be written is not a failure
        return False
    return True


def unread_for_cast(entries: Iterable[Any]) -> int:
    return sum(1 for notice in entries if not getattr(notice, "read", True))


# -- the digest -------------------------------------------------------------------- #


def since_sentence(then: datetime, now: datetime) -> str:
    """ "Since yesterday", "Since Tuesday", "In the last hour"."""
    gap = now - then
    if gap.total_seconds() < 3600:
        return "In the last hour"
    if gap.days < 1 and now.date() == then.date():
        return "Since this morning" if then.hour < 12 else "Since earlier today"
    if gap.days < 2:
        return "Since yesterday"
    if gap.days < 7:
        return f"Since {then.strftime('%A')}"
    return f"In the last {gap.days} days"


def digest(
    entries: Iterable[Any],
    *,
    since: datetime | None,
    now: datetime | None = None,
    inbox_on: bool = True,
) -> str:
    """One sentence about the new-episode notices written since *since*.

    Empty when there is nothing to say, so the caller says nothing. Counts the
    episodes from the notices' titles ("3 new episodes") and the podcasts from
    their bodies, which is what Cast writes into them.
    """
    if since is None:
        return ""
    moment = now or datetime.now(UTC)
    episodes = 0
    podcasts: set[str] = set()
    for notice in entries:
        if kind_of(notice) != NEW_EPISODE:
            continue
        stamp = _stamp(getattr(notice, "timestamp", ""))
        if stamp is None or stamp <= since:
            continue
        episodes += _count_in(str(getattr(notice, "title", "") or ""))
        body = str(getattr(notice, "body", "") or "").strip()
        if body:
            podcasts.add(body)
    if not episodes:
        return ""
    plural = "" if episodes == 1 else "s"
    from_where = (
        f" from {len(podcasts)} podcast{'' if len(podcasts) == 1 else 's'}" if podcasts else ""
    )
    where = " They are in the Inbox." if inbox_on else ""
    return f"{since_sentence(since, moment)}: {episodes} new episode{plural}{from_where}.{where}"


def _count_in(title: str) -> int:
    head = title.strip().split(" ", 1)[0]
    try:
        return max(1, int(head))
    except ValueError:
        return 1


def _stamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
