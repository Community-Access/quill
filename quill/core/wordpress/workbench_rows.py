"""The WordPress Workbench's rows: one shape for every object a list can show.

A :class:`WbRow` is what the window's list, details pane, context menu and
Properties sheet read: the row type (which picks the menu and the sheet), the
site it came from, its cells by column name, one sentence for the details
pane, its REST route, and the object as the site sent it (``raw``), which the
Properties sheet reads so nothing the site said is lost. The converters here
turn a REST payload into a row, using the words the existing windows already
use (:func:`~quill.core.wordpress.site.friendly_date`, the status labels).

Wx-free and network-free; :mod:`quill.core.wordpress.workbench_load` asks
the site and calls these.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.site import (
    STATUS_LABELS,
    friendly_date,
    human_size,
    kind_route,
    raw_text,
    rendered,
)

__all__ = [
    "COMMENT_STATUS_WORDS",
    "WbRow",
    "comment_row",
    "fact_rows",
    "item_row",
    "media_row",
    "status_word",
    "term_row",
    "tree_order",
    "user_row",
]

COMMENT_STATUS_WORDS = {
    "hold": "Waiting",
    "unapproved": "Waiting",
    "approved": "Approved",
    "approve": "Approved",
    "spam": "Spam",
    "trash": "Trash",
}


@dataclass(frozen=True, eq=False)
class WbRow:
    """One row of a Workbench list.

    *kind* is the row type (``item``, ``media``, ``comment`` ...); *subkind*
    narrows it (an item's post type, a term's taxonomy, an entry's plugin).
    *route* is the object's own REST route (``wp/v2/posts/12``), empty for
    rows that are not one object (a fact, a help word).
    """

    kind: str
    site: str
    key: str
    cells: Mapping[str, str]
    detail: str
    route: str = ""
    link: str = ""
    status: str = ""
    subkind: str = ""
    modified_gmt: str = ""
    raw: Mapping[str, Any] = field(default_factory=dict)

    def cell(self, column: str) -> str:
        return self.cells.get(column, "")

    @property
    def title(self) -> str:
        for column in ("title", "name", "what", "plugin", "theme", "setting", "form", "site"):
            if self.cells.get(column):
                return self.cells[column]
        return self.key

    @property
    def object_id(self) -> int:
        try:
            return int(self.key)
        except ValueError:
            return 0


def status_word(status: str) -> str:
    """WordPress's own word for a post status ("Draft", "Scheduled")."""
    if status == "publish":
        return "Published"
    word = STATUS_LABELS.get(status, status.replace("-", " ").replace("_", " ").title())
    return word[:-1] if word.endswith("s") and status != "publish" else word


def item_row(
    raw: Mapping[str, Any], kind: str, site: str, *, authors: Mapping[int, str] | None = None
) -> WbRow:
    """A post, page or custom item."""
    item_id = int(raw.get("id", 0) or 0)
    title = rendered(raw.get("title")) or raw_text(raw.get("title")) or "(untitled)"
    status = str(raw.get("status", ""))
    author_id = int(raw.get("author", 0) or 0)
    author = (authors or {}).get(author_id, f"user {author_id}" if author_id else "")
    modified = str(raw.get("modified_gmt", "") or "")
    date = str(raw.get("date_gmt", "") or raw.get("date", "") or "")
    word = status_word(status)
    when = f"scheduled for {friendly_date(date)}" if status == "future" and date else ""
    detail = f"{title}. {word}" + (f", {when}" if when else "")
    detail += f". Last changed {friendly_date(modified)}." if modified else "."
    if author:
        detail += f" By {author}."
    return WbRow(
        kind="item",
        site=site,
        key=str(item_id),
        cells={
            "title": title,
            "status": word,
            "author": author,
            "modified": friendly_date(modified) if modified else "",
            "date": friendly_date(date) if date else "",
            "site": site,
        },
        detail=detail,
        route=f"{kind_route(kind)}/{item_id}",
        link=str(raw.get("link", "") or ""),
        status=status,
        subkind=kind,
        modified_gmt=modified,
        raw=dict(raw),
    )


def tree_order(rows: Sequence[WbRow], parent_key: str = "parent") -> list[WbRow]:
    """Rows ordered as a tree by their ``raw[parent_key]``, each with a "level" cell.

    A child whose parent is not among *rows* (filtered out, or on a later
    page) is treated as a top-level row, so nothing is dropped.
    """
    ids = {row.key for row in rows}
    children: dict[str, list[WbRow]] = {}
    for row in rows:
        parent = str(int(row.raw.get(parent_key, 0) or 0))
        children.setdefault(parent if parent in ids else "0", []).append(row)
    ordered: list[WbRow] = []
    seen: set[str] = set()

    def visit(parent: str, level: int) -> None:
        for row in children.get(parent, []):
            if row.key in seen:
                continue
            seen.add(row.key)
            cells = {**row.cells, "level": str(level)}
            ordered.append(
                WbRow(
                    row.kind,
                    row.site,
                    row.key,
                    cells,
                    row.detail if level == 1 else f"{row.detail} Level {level}.",
                    row.route,
                    row.link,
                    row.status,
                    row.subkind,
                    row.modified_gmt,
                    row.raw,
                )
            )
            visit(row.key, level + 1)

    visit("0", 1)
    ordered.extend(row for row in rows if row.key not in seen)
    return ordered


def media_row(raw: Mapping[str, Any], site: str) -> WbRow:
    media_id = int(raw.get("id", 0) or 0)
    mime = str(raw.get("mime_type", "") or "")
    top = mime.split("/", 1)[0]
    kind_word = {"image": "picture", "audio": "audio", "video": "video"}.get(top, "document")
    title = rendered(raw.get("title")) or str(raw.get("slug", "")) or f"media {media_id}"
    alt = str(raw.get("alt_text", "") or "")
    details = raw.get("media_details") if isinstance(raw.get("media_details"), dict) else {}
    size = int((details or {}).get("filesize", 0) or 0)
    uploaded = str(raw.get("date_gmt", "") or "")
    parts = [title, kind_word]
    if size:
        parts.append(human_size(size))
    parts.append(f"alt text: {alt}" if alt else ("no alt text" if top == "image" else ""))
    parts.append(f"uploaded {friendly_date(uploaded)}" if uploaded else "")
    return WbRow(
        kind="media",
        site=site,
        key=str(media_id),
        cells={
            "title": title,
            "type": kind_word,
            "alt_text": alt or ("none" if top == "image" else ""),
            "uploaded": friendly_date(uploaded) if uploaded else "",
        },
        detail=", ".join(p for p in parts if p) + ".",
        route=f"wp/v2/media/{media_id}",
        link=str(raw.get("source_url", "") or raw.get("link", "") or ""),
        status=str(raw.get("status", "") or ""),
        subkind=top or "file",
        modified_gmt=str(raw.get("modified_gmt", "") or ""),
        raw=dict(raw),
    )


def comment_row(raw: Mapping[str, Any], site: str, *, post_title: str = "") -> WbRow:
    comment_id = int(raw.get("id", 0) or 0)
    author = str(raw.get("author_name", "") or "Anonymous")
    status = str(raw.get("status", "") or "")
    when = str(raw.get("date_gmt", "") or "")
    words = " ".join(rendered(raw.get("content")).split())
    on = post_title or (f"post {raw.get('post')}" if raw.get("post") else "")
    detail = f"{author}" + (f" on {on}" if on else "") + f", {friendly_date(when)}: {words}"
    return WbRow(
        kind="comment",
        site=site,
        key=str(comment_id),
        cells={
            "author": author,
            "on": on,
            "status": COMMENT_STATUS_WORDS.get(status, status),
            "when": friendly_date(when) if when else "",
            "what": f"Comment by {author}" + (f" on {on}" if on else ""),
            "from": author,
            "site": site,
        },
        detail=detail,
        route=f"wp/v2/comments/{comment_id}",
        link=str(raw.get("link", "") or ""),
        status=status,
        subkind="comment",
        raw=dict(raw),
    )


def term_row(raw: Mapping[str, Any], site: str, taxonomy: str, route: str) -> WbRow:
    term_id = int(raw.get("id", 0) or 0)
    name = rendered(raw.get("name")) or str(raw.get("name", ""))
    count = int(raw.get("count", 0) or 0)
    noun = "item" if count == 1 else "items"
    return WbRow(
        kind="term",
        site=site,
        key=str(term_id),
        cells={"name": name, "count": str(count), "slug": str(raw.get("slug", "") or "")},
        detail=f"{name}, {count} {noun}."
        + (f" {raw.get('description')}" if raw.get("description") else ""),
        route=f"{route.strip('/')}/{term_id}",
        link=str(raw.get("link", "") or ""),
        subkind=taxonomy,
        raw=dict(raw),
    )


def user_row(raw: Mapping[str, Any], site: str, role_words: Mapping[str, str]) -> WbRow:
    user_id = int(raw.get("id", 0) or 0)
    roles = [str(r) for r in raw.get("roles", []) or []]
    role = role_words.get(roles[0], roles[0].replace("_", " ").title()) if roles else "no role"
    name = str(raw.get("name", "") or "")
    username = str(raw.get("username", "") or raw.get("slug", "") or "")
    email = str(raw.get("email", "") or "")
    return WbRow(
        kind="user",
        site=site,
        key=str(user_id),
        cells={"name": name, "username": username, "role": role, "email": email},
        detail=f"{name}, {username}, {role}" + (f", {email}" if email else "") + ".",
        route=f"wp/v2/users/{user_id}",
        link=str(raw.get("link", "") or ""),
        status=roles[0] if roles else "",
        subkind="user",
        raw=dict(raw),
    )


def fact_rows(site: str, facts: Iterable[tuple[str, str]]) -> list[WbRow]:
    """Rows of "fact, value" (a site's Overview, its settings), each its own sentence."""
    return [
        WbRow(
            kind="fact",
            site=site,
            key=str(index),
            cells={"fact": fact, "value": value, "setting": fact},
            detail=f"{fact}: {value}.",
        )
        for index, (fact, value) in enumerate(facts)
    ]
