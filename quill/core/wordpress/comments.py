"""The Comments window's model: every status, threads, and the waiting count (wordpress.md 9.8).

Wx-free, like the rest of :mod:`quill.core.wordpress`. A comment row reads
the way a person would say it -- who, on what, when, and the first words --
and replies sit under the comment they answer, one level deeper, so a
conversation is read in order rather than as a pile of dates.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import friendly_date, plain_text, raw_text, rendered

#: The statuses the window offers, in its order: (REST status, what a person calls it).
STATUSES: tuple[tuple[str, str], ...] = (
    ("hold", "Waiting"),
    ("approve", "Approved"),
    ("spam", "Spam"),
    ("trash", "Trash"),
)
STATUS_NAMES = dict(STATUSES)


@dataclass(frozen=True)
class Comment:
    id: int
    post: int
    parent: int
    author_name: str
    date_gmt: str
    status: str
    content: str
    link: str = ""
    post_title: str = ""

    def first_words(self, count: int = 12) -> str:
        return " ".join(plain_text(self.content).split()[:count])

    def spoken(self, depth: int = 0, parent_author: str = "") -> str:
        on = f" on {self.post_title}" if self.post_title else ""
        reply = f"reply to {parent_author}, " if depth and parent_author else ""
        level = f", level {depth + 1}" if depth else ""
        return (
            f"{reply}{self.author_name}{on}, {friendly_date(self.date_gmt)}: "
            f"{self.first_words()}{level}"
        )


def comment_from_payload(raw: Any) -> Comment:
    return Comment(
        id=int(raw.get("id", 0)),
        post=int(raw.get("post", 0) or 0),
        parent=int(raw.get("parent", 0) or 0),
        author_name=str(raw.get("author_name", "") or "Anonymous"),
        date_gmt=str(raw.get("date_gmt", "") or ""),
        status=str(raw.get("status", "") or ""),
        content=raw_text(raw.get("content")),
        link=str(raw.get("link", "") or ""),
    )


def list_comments(api: WordPressApi, status: str = "hold") -> list[Comment]:
    """Every comment with *status*, each with the title of what it is on."""
    params: dict[str, object] = {"context": "edit", "status": status}
    found = [comment_from_payload(r) for r in api.iter_collection("wp/v2/comments", params)]
    titles = post_titles(api, {c.post for c in found if c.post})
    return [replace(c, post_title=titles.get(c.post, "")) for c in found]


def post_titles(api: WordPressApi, ids: Iterable[int]) -> dict[int, str]:
    """Titles for *ids*, looked up among posts and then pages."""
    wanted = sorted(set(ids))
    titles: dict[int, str] = {}
    for route in ("wp/v2/posts", "wp/v2/pages"):
        missing = [i for i in wanted if i not in titles]
        if not missing:
            break
        params: dict[str, object] = {
            "include": missing,
            "status": "any",
            "context": "edit",
            "_fields": "id,title",
        }
        for raw in api.iter_collection(route, params):
            titles[int(raw.get("id", 0))] = rendered(raw.get("title")) or "(untitled)"
    return titles


def threaded(comments: list[Comment]) -> list[tuple[int, Comment]]:
    """``(depth, comment)`` with each reply under its parent, oldest first in a thread.

    A reply whose parent is not in the list (another status, or deleted)
    starts its own thread at depth 0, so nothing is hidden.
    """
    by_id = {c.id: c for c in comments}
    children: dict[int, list[Comment]] = {}
    roots: list[Comment] = []
    for c in comments:
        if c.parent and c.parent in by_id:
            children.setdefault(c.parent, []).append(c)
        else:
            roots.append(c)
    out: list[tuple[int, Comment]] = []
    seen: set[int] = set()

    def visit(c: Comment, depth: int) -> None:
        if c.id in seen:
            return
        seen.add(c.id)
        out.append((depth, c))
        for child in sorted(children.get(c.id, []), key=lambda x: x.date_gmt):
            visit(child, depth + 1)

    for root in sorted(roots, key=lambda x: x.date_gmt, reverse=True):
        visit(root, 0)
    return out


def thread_rows(rows: list[tuple[int, Comment]]) -> list[str]:
    by_id = {c.id: c for _d, c in rows}
    return [
        c.spoken(depth, by_id[c.parent].author_name if c.parent in by_id else "")
        for depth, c in rows
    ]


def count_waiting(api: WordPressApi) -> int:
    response = api.request(
        "GET",
        "wp/v2/comments",
        params={"status": "hold", "per_page": 1, "_fields": "id", "context": "edit"},
    )
    if response.total is not None:
        return response.total
    return len(response.payload) if isinstance(response.payload, list) else 0


def waiting_sentence(site_name: str, count: int) -> str:
    noun = "comment" if count == 1 else "comments"
    return f"{site_name}: {count} {noun} waiting."


def set_status(api: WordPressApi, comment_id: int, status: str) -> Comment:
    return comment_from_payload(
        api.post(f"wp/v2/comments/{comment_id}", {"status": status}, context="edit")
    )


def edit_comment(api: WordPressApi, comment_id: int, content: str) -> Comment:
    return comment_from_payload(
        api.post(f"wp/v2/comments/{comment_id}", {"content": content}, context="edit")
    )


def reply(api: WordPressApi, parent: Comment, content: str) -> Comment:
    """A reply, approved at once: the person replying is the moderator."""
    return comment_from_payload(
        api.post(
            "wp/v2/comments",
            {"post": parent.post, "parent": parent.id, "content": content},
            context="edit",
        )
    )


def set_many(api: WordPressApi, ids: list[int], status: str) -> int:
    """Several comments after one confirmation (9.8, "many at once"). Returns how many.

    One request each: WordPress's comments route does not take part in
    ``batch/v1``.
    """
    for comment_id in ids:
        api.post(f"wp/v2/comments/{comment_id}", {"status": status})
    return len(ids)
