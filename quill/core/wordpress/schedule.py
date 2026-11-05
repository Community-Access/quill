"""Scheduling, autosaves on the site, and spoken times (wordpress.md 5.8, 9.3).

No wx here. The commands ask for a date, a time and a time zone as text and
hand them to :func:`parse_schedule`, which either returns an aware moment or
raises :class:`ScheduleError` with a sentence to show beside the fields. The
date handling is the older publishing core's
(:func:`quill.core.publishing_schedule.validate_scheduled_publish_time`), so
"in the future, with a time zone" means the same thing in both places.

Time zones are keys: an IANA name (``America/New_York``), ``UTC``, a fixed
offset the site gave (``UTC+02:00``), or :data:`LOCAL` -- this computer's own
zone, which Python resolves through the operating system's rules for that date,
so a time across a daylight-saving change still lands on the hour typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from quill.core.error_codes import CodedError
from quill.core.publishing_schedule import validate_scheduled_publish_time
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import Item, item_from_payload, kind_route, raw_text

LOCAL = "local"
LOCAL_LABEL = "This computer's time zone"


class ScheduleError(CodedError):
    """A date, time or zone that cannot be scheduled; the message says which."""

    code = "QUILL-WP-SCHEDULE-INVALID"

    @property
    def plain(self) -> str:
        """The sentence alone, without the support code in front."""
        return str(self.args[0]) if self.args else ""


# --------------------------------------------------------------------------- #
# Time zones


def zone_keys(site_zone: str = "") -> list[str]:
    """The zones offered, the site's first (or this computer's when it gave none)."""
    first = [site_zone] if site_zone and site_zone not in (LOCAL, "UTC") else []
    try:
        names = sorted(z for z in available_timezones() if z != "UTC")
    except Exception:  # noqa: BLE001 - no tz database: the three below still work
        names = []
    return first + [LOCAL, "UTC"] + [n for n in names if n not in first]


def zone_label(key: str, site_zone: str = "") -> str:
    if key == LOCAL:
        return LOCAL_LABEL
    if site_zone and key == site_zone:
        return f"The site's time zone, {key}"
    return key


def zone_for(key: str) -> tzinfo | None:
    """The tzinfo behind a key; ``None`` means this computer's zone."""
    if key == LOCAL:
        return None
    match = re.fullmatch(r"UTC([+-])(\d{1,2}):?(\d{2})?", key)
    if match:
        sign = -1 if match.group(1) == "-" else 1
        offset = timedelta(hours=int(match.group(2)), minutes=int(match.group(3) or 0))
        return timezone(sign * offset)
    if key == "UTC":
        return UTC
    try:
        return ZoneInfo(key)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ScheduleError(f"QUILL does not know the time zone {key}. Choose another.") from exc


def offset_key(gmt_offset: float) -> str:
    """``-5`` -> ``UTC-05:00``; ``5.5`` -> ``UTC+05:30``."""
    sign = "-" if gmt_offset < 0 else "+"
    minutes = round(abs(gmt_offset) * 60)
    return f"UTC{sign}{minutes // 60:02d}:{minutes % 60:02d}"


def site_time_zone(api: WordPressApi) -> str:
    """The site's zone from its REST index, or ``""`` when it does not say."""
    raw = api.get("")
    if not isinstance(raw, dict):
        return ""
    name = str(raw.get("timezone_string", "") or "")
    if name:
        try:
            ZoneInfo(name)
            return name
        except (ZoneInfoNotFoundError, ValueError):
            pass
    offset = raw.get("gmt_offset")
    if isinstance(offset, (int, float, str)) and str(offset).strip() != "":
        try:
            return offset_key(float(offset))
        except ValueError:
            return ""
    return ""


# --------------------------------------------------------------------------- #
# Reading what was typed


def parse_schedule(
    date_text: str, time_text: str, zone_key: str, *, now: datetime | None = None
) -> datetime:
    """An aware moment in the future, or :class:`ScheduleError` saying what to fix."""
    try:
        day = date.fromisoformat(date_text.strip())
    except ValueError as exc:
        raise ScheduleError(
            "Type the date as year, month and day, for example 2026-11-20."
        ) from exc
    clock = _parse_time(time_text)
    if clock is None:
        raise ScheduleError("Type the time as 24-hour hours and minutes, or like 4:15 PM.")
    naive = datetime(day.year, day.month, day.day, clock[0], clock[1])
    zone = zone_for(zone_key)
    when = naive.astimezone() if zone is None else naive.replace(tzinfo=zone)
    problem = validate_scheduled_publish_time(when, now=now)
    if problem:
        raise ScheduleError(problem)
    return when


def _parse_time(text: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)?\s*", text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    half = (match.group(3) or "").lower().replace(".", "")
    if half:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if half == "pm" else 0)
    elif match.group(2) is None:
        return None
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def date_gmt(when: datetime) -> str:
    """What WordPress takes as ``date_gmt``."""
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def spoken_moment(when: datetime) -> str:
    """``Friday 20 November 2026, 9:00 AM`` in the moment's own zone."""
    hour = when.hour % 12 or 12
    half = "AM" if when.hour < 12 else "PM"
    day = f"{when.strftime('%A')} {when.day} {when.strftime('%B %Y')}"
    return f"{day}, {hour}:{when.minute:02d} {half}"


def when_spoken(stamp_gmt: str, *, now: datetime | None = None, zone: tzinfo | None = None) -> str:
    """A site stamp (GMT) as a person says it, in this computer's time.

    ``today, 4:12 PM``, ``yesterday, 4:12 PM``, or ``3 November, 4:12 PM``
    (with the year when it is not this one).
    """
    try:
        moment = datetime.fromisoformat(stamp_gmt.replace("Z", "")).replace(tzinfo=UTC)
    except ValueError:
        return stamp_gmt or "an unknown time"
    local = moment.astimezone(zone)
    today = (now or datetime.now(UTC)).astimezone(zone).date()
    hour = local.hour % 12 or 12
    clock = f"{hour}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"
    if local.date() == today:
        return f"today, {clock}"
    if local.date() == today - timedelta(days=1):
        return f"yesterday, {clock}"
    year = "" if local.year == today.year else f" {local.year}"
    return f"{local.day} {local.strftime('%B')}{year}, {clock}"


def later_than(stamp: str, other: str) -> bool:
    """True when site stamp *stamp* is after *other* (empty is never later)."""
    first, second = _stamp(stamp), _stamp(other)
    return first is not None and (second is None or first > second)


def _stamp(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "")) if text else None
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# On the site


def send_scheduled(api: WordPressApi, item: Item, when_gmt: str) -> Item:
    """Create or update *item* with status ``future`` (or publish now) at *when_gmt*."""
    body = item.to_body() | {"status": item.status, "date_gmt": when_gmt}
    route = f"{kind_route(item.kind)}/{item.id}" if item.id else kind_route(item.kind)
    return item_from_payload(api.post(route, body, context="edit"), item.kind)


@dataclass(frozen=True)
class Autosave:
    modified_gmt: str
    title: str
    content: str
    excerpt: str


def latest_autosave(api: WordPressApi, kind: str, item_id: int) -> Autosave | None:
    """The account's newest autosave of an item, or ``None`` (none, or not allowed)."""
    try:
        rows = api.get(f"{kind_route(kind)}/{item_id}/autosaves", context="edit")
    except WordPressApiError as exc:
        if exc.status in (401, 403, 404):
            return None
        raise
    found = [
        Autosave(
            modified_gmt=str(r.get("modified_gmt") or r.get("date_gmt") or ""),
            title=raw_text(r.get("title")),
            content=raw_text(r.get("content")),
            excerpt=raw_text(r.get("excerpt")),
        )
        for r in (rows if isinstance(rows, list) else [])
        if isinstance(r, dict)
    ]
    return max(found, key=lambda a: a.modified_gmt, default=None)


def newer_autosave(api: WordPressApi, item: Item) -> Autosave | None:
    """An autosave worth offering on Open: newer than the item, and different."""
    autosave = latest_autosave(api, item.kind, item.id)
    if autosave is None or not later_than(autosave.modified_gmt, item.modified_gmt):
        return None
    if autosave.content == item.content and autosave.title == item.title:
        return None
    return autosave


def find_landed(
    api: WordPressApi,
    *,
    kind: str,
    title: str,
    slug: str,
    since_gmt: str,
    item_id: int = 0,
    content: str = "",
) -> Item | None:
    """Did a send that was never confirmed reach the site? (wordpress.md 5.10)

    For an update, the item itself is re-read: it landed when it changed after
    *since_gmt* and now holds exactly what was sent. For a new item, the site
    is searched by title (and slug) for one changed since the send began.
    """
    slack = (_stamp(since_gmt) or datetime.min) - timedelta(minutes=5)
    if item_id:
        raw = api.get(f"{kind_route(kind)}/{item_id}", context="edit")
        item = item_from_payload(raw, kind)
        changed = _stamp(item.modified_gmt) or datetime.min
        same = item.title == title and (not content or item.content == content)
        return item if changed >= slack and same else None
    params: dict[str, Any] = {
        "context": "edit",
        "status": ["publish", "draft", "pending", "future", "private"],
        "orderby": "modified",
        "order": "desc",
        "per_page": 20,
    }
    if slug:
        params["slug"] = slug
    else:
        params["search"] = title
    rows = api.get(kind_route(kind), **params)
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        item = item_from_payload(raw, kind)
        changed = _stamp(item.modified_gmt) or datetime.min
        if changed >= slack and (item.title == title or (slug and item.slug == slug)):
            return item
    return None
