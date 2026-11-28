"""Build the field values a template speaks from each kind of row model.

One function per source. Each returns ``(list_type_id, values)``, or None when
the row is not one a template can speak. Values are plain text; a field that
is not in the mapping at all is *missing* to the renderer, while an empty
string is *empty*, so the two stay distinct.

Wx-free; takes models by duck type so it imports nothing from the UI.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

__all__ = [
    "explore_row_fields",
    "github_item_fields",
    "spoken_age",
    "wordpress_row_fields",
]

#: ExploreRow kind -> list type id, for the Explore rows a template can speak.
_EXPLORE_KINDS = {
    "notification": "github_notifications",
    "repo": "github_repositories",
}


def spoken_age(stamp: str, today: date | None = None) -> str:
    """ "today", "yesterday", "3 days ago", or the date, for an ISO date or timestamp."""
    text = (stamp or "").strip()
    if not text:
        return ""
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return text[:10]
    days = ((today or date.today()) - when).days
    if days < 0:
        return text[:10]
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    if days < 365:
        return f"{days // 30} months ago"
    return text[:10]


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def github_item_fields(item: Any, today: date | None = None) -> tuple[str, dict[str, str]]:
    """An issue or pull request (a ``GitHubItem``)."""
    is_pr = bool(item.is_pr)
    state = str(item.state_display).lower()
    if is_pr and item.is_draft and state == "open":
        state = "draft"
    comments = int(item.comments or 0)
    values = {
        "number": f"number {item.number}",
        "title": str(item.title or ""),
        "state": state,
        "author": str(item.author or ""),
        "updated": str(item.updated_at or "")[:10],
        "updated_ago": spoken_age(str(item.updated_at or ""), today),
        "labels": ", ".join(item.labels or ()),
        "assignees": ", ".join(item.assignees or ()),
        "comments": "no comments" if comments == 0 else _plural(comments, "comment", "comments"),
    }
    if is_pr:
        head, base = str(item.head_branch or ""), str(item.base_branch or "")
        values["branches"] = f"{head} into {base}" if head and base else ""
        values["review"] = str(item.review_status or "").replace("_", " ").lower()
    return ("github_pulls" if is_pr else "github_issues", values)


def explore_row_fields(row: Any) -> tuple[str, dict[str, str]] | None:
    """An Explore row that carries structured fields (notifications, repositories)."""
    list_type = _EXPLORE_KINDS.get(str(getattr(row, "kind", "")))
    fields = getattr(row, "fields", ())
    if list_type is None or not fields:
        return None
    values = dict(fields)
    if "updated" in values and "updated_ago" not in values:
        values["updated_ago"] = spoken_age(values["updated"])
    return list_type, values


def _first_words(text: str, limit: int = 12) -> str:
    words = text.split()
    return " ".join(words[:limit]) + (" ..." if len(words) > limit else "")


def wordpress_row_fields(row: Any) -> tuple[str, dict[str, str]] | None:
    """A WordPress Workbench post, page or comment row (a ``WbRow``)."""
    cells: Mapping[str, str] = getattr(row, "cells", {})
    kind = str(getattr(row, "kind", ""))
    if kind == "item" and getattr(row, "subkind", "") in ("post", "page"):
        return "wordpress_posts", {
            k: str(cells.get(k, ""))
            for k in ("status", "title", "author", "modified", "date", "site")
        }
    if kind == "comment":
        values = {k: str(cells.get(k, "")) for k in ("author", "status", "on", "when", "site")}
        raw = getattr(row, "raw", {}) or {}
        content = raw.get("content")
        text = content.get("rendered", "") if isinstance(content, dict) else str(content or "")
        text = " ".join(_strip_tags(text).split())
        values["excerpt"] = _first_words(text)
        return "wordpress_comments", values
    if kind == "media":
        return "wordpress_media", {
            k: str(cells.get(k, "")) for k in ("title", "type", "alt_text", "uploaded")
        }
    if kind == "user":
        return "wordpress_users", {
            k: str(cells.get(k, "")) for k in ("name", "username", "role", "email")
        }
    return None


def _strip_tags(html: str) -> str:
    out: list[str] = []
    inside = False
    for ch in html:
        if ch == "<":
            inside = True
        elif ch == ">":
            inside = False
        elif not inside:
            out.append(ch)
    return "".join(out)
