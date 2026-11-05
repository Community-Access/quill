"""Coming Up, and What Changed on My Sites, across every connected site (wordpress.md 9.16).

* **Coming Up:** everything scheduled on every site, by date. It answers "what
  goes out next week?" in one place.
* **What Changed on My Sites:** since the person last looked, per site: new
  comments, posts other people published, and Site Health warnings. One list,
  read on request; never a pop-up. When it was last looked at is kept per site
  (:class:`LastLooked`), and a site never looked at before shows the last
  week.

Plugin updates are not in it: WordPress's REST API does not say which plugins
have one waiting, and QUILL does not guess.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress import site as wp
from quill.core.wordpress.api import WordPressApi, WordPressApiError

#: The Site Health tests the REST API runs on request; a critical one is a change worth hearing.
HEALTH_TESTS = (
    "background-updates",
    "loopback-requests",
    "https-status",
    "dotorg-communication",
    "authorization-header",
)

# --------------------------------------------------------------------------- #
# Coming Up


@dataclass(frozen=True)
class Scheduled:
    site: str
    kind: str
    id: int
    title: str
    date_gmt: str
    link: str

    def spoken(self) -> str:
        what = "page" if self.kind == "page" else "post"
        return f"{wp.friendly_date(self.date_gmt)}, {self.title}, {what} on {self.site}"


def scheduled_on(api: WordPressApi, site_name: str) -> list[Scheduled]:
    found: list[Scheduled] = []
    for kind in ("post", "page"):
        params: dict[str, object] = {
            "context": "edit",
            "status": "future",
            "orderby": "date",
            "order": "asc",
            "_fields": "id,type,title,date_gmt,link",
        }
        for raw in api.iter_collection(wp.kind_route(kind), params):
            found.append(
                Scheduled(
                    site=site_name,
                    kind=wp.kind_from_payload(raw, kind),
                    id=int(raw.get("id", 0)),
                    title=wp.rendered(raw.get("title")) or "(untitled)",
                    date_gmt=str(raw.get("date_gmt", "") or ""),
                    link=str(raw.get("link", "") or ""),
                )
            )
    return found


SiteCall = tuple[str, str, Callable[[], WordPressApi]]


def coming_up(sites: list[SiteCall]) -> tuple[list[Scheduled], list[str]]:
    """Every scheduled item on every site, soonest first, and the sites that did not answer.

    *sites* is ``(site id, site name, make the api)`` per site.
    """
    items: list[Scheduled] = []
    failed: list[str] = []
    for _site_id, name, make in sites:
        try:
            items.extend(scheduled_on(make(), name))
        except WordPressApiError as exc:
            failed.append(f"{name}: {exc.plain}")
    return sorted(items, key=lambda s: s.date_gmt), failed


def coming_up_sentence(items: list[Scheduled], failed: list[str], sites: int) -> str:
    where = "your site" if sites == 1 else f"your {sites} sites"
    if not items:
        said = f"Nothing is scheduled on {where}."
    else:
        first = items[0]
        noun = "item is" if len(items) == 1 else "items are"
        said = (
            f"{len(items)} {noun} scheduled on {where}. The next is {first.title} on "
            f"{first.site}, {wp.friendly_date(first.date_gmt)}."
        )
    if failed:
        said += f" {len(failed)} sites did not answer."
    return said


# --------------------------------------------------------------------------- #
# What Changed on My Sites


class LastLooked:
    """When each site was last looked at, in UTC."""

    def __init__(self, base: Path | None = None) -> None:
        self.path = (base or app_data_dir()) / "wordpress" / "what-changed.json"

    def since(self, site_id: str, now: datetime) -> str:
        raw = read_json(self.path, default={})
        stamp = raw.get(site_id) if isinstance(raw, dict) else None
        if isinstance(stamp, str) and stamp:
            return stamp
        return (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")

    def mark(self, site_ids: list[str], now: datetime) -> None:
        raw = read_json(self.path, default={})
        every: dict[str, Any] = raw if isinstance(raw, dict) else {}
        for site_id in site_ids:
            every[site_id] = now.strftime("%Y-%m-%dT%H:%M:%S")
        write_json_atomic(self.path, every)


@dataclass(frozen=True)
class Change:
    site: str
    kind: str  # comment, post, health
    text: str
    link: str = ""

    def spoken(self) -> str:
        return f"{self.site}: {self.text}"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def changes_on(api: WordPressApi, site_name: str, since: str) -> list[Change]:
    out: list[Change] = []
    me = wp.load_account(api)
    out += _comments(api, site_name, since)
    params: dict[str, object] = {
        "context": "edit",
        "status": "publish",
        "after": since,
        "author_exclude": me.id,
        "_fields": "id,title,link,date_gmt",
    }
    try:
        for raw in api.iter_collection("wp/v2/posts", params):
            title = wp.rendered(raw.get("title")) or "(untitled)"
            out.append(
                Change(
                    site_name,
                    "post",
                    f"{title} was published by someone else.",
                    str(raw.get("link", "")),
                )
            )
    except WordPressApiError as exc:
        if exc.status not in (400, 401, 403):
            raise
    out += _health(api, site_name)
    return out


def _comments(api: WordPressApi, site_name: str, since: str) -> list[Change]:
    for status in ("all", ""):
        params: dict[str, object] = {"after": since, "_fields": "id,author_name,post,status,link"}
        if status:
            params.update(status=status, context="edit")
        try:
            rows = list(api.iter_collection("wp/v2/comments", params))
        except WordPressApiError as exc:
            if exc.status in (400, 401, 403) and status:
                continue
            if exc.status in (401, 403):
                return []
            raise
        waiting = sum(1 for r in rows if r.get("status") == "hold")
        if not rows:
            return []
        text = f"{len(rows)} new comments" if len(rows) != 1 else "1 new comment"
        if waiting:
            text += f", {waiting} waiting for you"
        return [Change(site_name, "comment", text + ".")]
    return []


def _health(api: WordPressApi, site_name: str) -> list[Change]:
    out: list[Change] = []
    for test in HEALTH_TESTS:
        try:
            raw = api.get(f"wp-site-health/v1/tests/{test}")
        except WordPressApiError as exc:
            if exc.status in (401, 403):
                return []
            continue
        if isinstance(raw, dict) and raw.get("status") == "critical":
            label = wp.rendered(raw.get("label")) or test.replace("-", " ")
            out.append(Change(site_name, "health", f"Site Health warning: {label.rstrip('.')}."))
    return out


def what_changed(
    sites: list[SiteCall], looked: LastLooked, now: datetime
) -> tuple[list[Change], list[str]]:
    changes: list[Change] = []
    failed: list[str] = []
    for site_id, name, make in sites:
        try:
            changes.extend(changes_on(make(), name, looked.since(site_id, now)))
        except WordPressApiError as exc:
            failed.append(f"{name}: {exc.plain}")
    return changes, failed


def what_changed_sentence(changes: list[Change], failed: list[str], sites: int) -> str:
    where = "your site" if sites == 1 else f"your {sites} sites"
    if not changes:
        said = f"Nothing new on {where} since you last looked."
    else:
        touched = len({c.site for c in changes})
        said = f"{len(changes)} changes on {touched} of {where.removeprefix('your ')}."
        if sites == 1:
            said = f"{len(changes)} changes on {where} since you last looked."
    if failed:
        said += f" {len(failed)} sites did not answer."
    return said
