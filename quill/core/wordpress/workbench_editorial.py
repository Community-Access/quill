"""The editorial queue and moving content between days (PRD 15.3, 15.4; W7).

- **A time on the site's clock** (:func:`site_moment`): what a person types
  ("2026-11-20", "9:00" or "9 AM") read in the site's own time zone, with the
  two daylight-saving traps named rather than guessed: a time the clocks
  skip ("2:30 AM does not happen that day") and a time that happens twice,
  which takes ``first`` or ``second`` after it. :func:`moment_words` says
  the result in the site's time and this computer's, which is the preview
  both Approve and Schedule and Move to Another Day show.
- **Reviewers** (:class:`Review`, :func:`load_reviews`, :func:`assign_reviewer`):
  WordPress has no reviewer field, so an assignment is a note on the draft
  (which the writer and the reviewer read in the editor) and a record on this
  computer, beside the site list, which the "review" Watch reads to say when
  the item leaves the queue. WordPress sends no email for either;
  :data:`NOTICE_WORDS` says so wherever an assignment is made.
- **Where it is in the queue** (:func:`queue_positions`): each item waiting
  for review, oldest first per site, "2 of 5 waiting on Radio", so a
  Contributor, who sees only their own, knows how far along theirs is.

Wx-free and network-free except :func:`queue_status`, which reads one item.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.schedule import ScheduleError, spoken_moment, zone_for
from quill.core.wordpress.sites import sites_path

__all__ = [
    "NOTICE_WORDS",
    "Review",
    "assign_reviewer",
    "load_reviews",
    "moment_words",
    "queue_positions",
    "queue_status",
    "save_reviews",
    "site_moment",
]

NOTICE_WORDS = (
    "WordPress sends no email for this: the note is on the draft, where its writer and "
    "the reviewer read it, and the Review Watch on this computer says when it leaves the queue."
)
_TIME = re.compile(r"^\s*(.*?)\s*(first|second)?\s*$", re.IGNORECASE)


def _clock(text: str) -> tuple[int, int] | None:
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


def site_moment(
    day_text: str,
    time_text: str,
    zone_key: str,
    *,
    future_only: bool = True,
    now: datetime | None = None,
) -> datetime:
    """An aware moment on the site's clock, or :class:`ScheduleError` saying what to fix."""
    try:
        day = date.fromisoformat(day_text.strip())
    except ValueError as exc:
        raise ScheduleError("Type the day as year, month and day, for example 2026-11-20.") from exc
    match = _TIME.match(time_text)
    which = (match.group(2) or "").lower() if match else ""
    clock = _clock(match.group(1) if match else time_text)
    if clock is None:
        raise ScheduleError("Type the time as 24-hour hours and minutes, or like 4:15 PM.")
    zone = zone_for(zone_key or "UTC")
    naive = datetime(day.year, day.month, day.day, *clock)
    if zone is None:
        when = naive.astimezone()
    else:
        when = naive.replace(tzinfo=zone, fold=1 if which == "second" else 0)
        problem = _wall_problem(naive, zone, zone_key)
        if problem == "missing":
            raise ScheduleError(
                f"{_hm(naive)} does not happen on {_day(naive)} in {zone_key}: the clocks go "
                "forward then. Choose another time."
            )
        if problem == "twice" and not which:
            raise ScheduleError(
                f"{_hm(naive)} happens twice on {_day(naive)} in {zone_key}, because the clocks "
                "go back. Type first or second after the time to say which."
            )
    if future_only and when <= (now or datetime.now(UTC)):
        raise ScheduleError("Choose a time that is in the future.")
    return when


def _wall_problem(naive: datetime, zone: tzinfo, key: str) -> str:
    if not isinstance(zone, ZoneInfo):
        return ""
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    if first.utcoffset() == second.utcoffset():
        return ""
    back = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
    return "missing" if back != naive else "twice"


def _hm(moment: datetime) -> str:
    return f"{moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def _day(moment: datetime) -> str:
    return f"{moment.day} {moment.strftime('%B %Y')}"


def moment_words(when: datetime, zone_key: str, *, here: tzinfo | None = None) -> str:
    """``Friday 20 November 2026, 9:00 AM at the site (Europe/London); 4:00 AM here``."""
    local = when.astimezone(here)
    site = f"{spoken_moment(when)} at the site ({zone_key or 'UTC'})"
    if local.utcoffset() == when.utcoffset():
        return f"{site}, which is the same time here"
    same_day = local.date() == when.date()
    there = _hm(local) if same_day else spoken_moment(local)
    return f"{site}; {there} here"


# -- reviewers -----------------------------------------------------------------


@dataclass
class Review:
    """One assignment, as this computer keeps it."""

    site: str
    item_id: int
    route: str
    title: str
    reviewer: str
    note: str = ""
    assigned: float = 0.0


def _path(base: Path | None) -> Path:
    return sites_path(base).parent / "workbench_reviews.json"


def load_reviews(base: Path | None = None) -> list[Review]:
    raw = read_json(_path(base), default=[])
    found: list[Review] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        try:
            found.append(
                Review(
                    site=str(entry["site"]),
                    item_id=int(entry["item_id"]),
                    route=str(entry.get("route", "")),
                    title=str(entry.get("title", "")),
                    reviewer=str(entry.get("reviewer", "")),
                    note=str(entry.get("note", "")),
                    assigned=float(entry.get("assigned", 0.0) or 0.0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return found


def save_reviews(reviews: Sequence[Review], base: Path | None = None) -> None:
    write_json_atomic(_path(base), [asdict(r) for r in reviews])


def assign_reviewer(
    base: Path | None,
    review: Review,
    *,
    clock: Callable[[], float] = time.time,
) -> list[Review]:
    """Keep *review*, replacing any earlier assignment of the same item; all of them."""
    kept = [r for r in load_reviews(base) if (r.site, r.item_id) != (review.site, review.item_id)]
    review.assigned = review.assigned or clock()
    kept.append(review)
    save_reviews(kept, base)
    return kept


def queue_status(api: WordPressApi, review: Review) -> str:
    """The item's status now ("" when the site would not say)."""
    try:
        raw = api.get(review.route, context="edit", _fields="id,status")
    except WordPressApiError as exc:
        return "trash" if exc.status in (404, 410) else ""
    return str(raw.get("status", "") or "") if isinstance(raw, dict) else ""


def queue_positions(rows: Sequence[Any]) -> dict[tuple[str, str], str]:
    """(site, key) -> "2 of 5 waiting on Radio", oldest first per site."""
    by_site: dict[str, list[Any]] = {}
    for row in rows:
        if getattr(row, "kind", "") == "item" and getattr(row, "status", "") == "pending":
            by_site.setdefault(row.site, []).append(row)
    said: dict[tuple[str, str], str] = {}
    for site, waiting in by_site.items():
        ordered = sorted(waiting, key=_when)
        for place, row in enumerate(ordered, start=1):
            said[(site, row.key)] = f"{place} of {len(ordered)} waiting on {site}"
    return said


def _when(row: Any) -> str:
    raw: Mapping[str, Any] = getattr(row, "raw", {}) or {}
    return str(raw.get("modified_gmt") or raw.get("date_gmt") or getattr(row, "modified_gmt", ""))
