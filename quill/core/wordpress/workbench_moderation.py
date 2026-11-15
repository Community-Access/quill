"""Comments in the Workbench, the rest of wp-admin's Comments screen (wordpress.md 9.18, package 4).

What the Workbench already did -- the status views, Approve, Unapprove, Spam,
Not Spam, Trash, Restore, Delete Permanently, Reply and the comment sheet --
lives where it always has. This adds the rest, each through ``wp/v2/comments``:

- **Counts** (:func:`comment_counts`): wp-admin's "All (12) | Mine (2) |
  Pending (4) ..." line, as one sentence, from the ``X-WP-Total`` header of a
  one-row read per status, so nothing is downloaded to count it.
- **A post's comments** (:func:`post_comment_count`): how many comments a post
  has, the number wp-admin shows in its comment bubble.
- **One result per comment**: Approve, Unapprove, Spam and Not Spam on many
  comments go through :func:`~quill.core.wordpress.workbench_parity.each`, so
  each failure is said and only the ones that changed are put back by Undo.
- **Empty Trash** (:func:`trashed_comments`): the ids of every comment in the
  Trash, which :func:`~quill.core.wordpress.workbench_create.empty_spam` then
  deletes permanently one by one (it deletes any ids it is given).
- **Conflict check** (:func:`version_of`): a comment and a user have no
  ``modified_gmt``, so the fields a person edits stand in for it; a sheet
  saved over someone else's change is caught the same way a post's is.

Author email and IP address come only with ``context=edit``, which WordPress
answers only for someone who can moderate comments, so the Workbench shows
them exactly where WordPress itself would. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import raw_text

__all__ = [
    "COUNTED",
    "SHEET_HELP",
    "comment_counts",
    "counts_sentence",
    "mine_count",
    "post_comment_count",
    "trashed_comments",
    "version_of",
]

COUNTED: tuple[tuple[str, str], ...] = (
    ("hold", "waiting"),
    ("approve", "approved"),
    ("spam", "spam"),
    ("trash", "in the Trash"),
)
"""The statuses wp-admin counts, in its order, with the words a person says."""

SHEET_HELP: dict[str, str] = {
    "author_ip": "Where it was sent from. WordPress shows it only to people who can moderate "
    "comments.",
    "date": "When it was written, in the site's own time, such as 2026-11-03T09:00:00. Change "
    "it as wp-admin's Edit Comment does.",
    "locale": "A WordPress language code such as en_US, for their wp-admin. Empty uses the "
    "site's language.",
}
"""F1 help for the comment and user sheet fields this package added."""

_VERSION_FIELDS: dict[str, tuple[str, ...]] = {
    "comment": ("status", "content", "author_name", "author_email", "author_url", "date_gmt"),
    "user": ("name", "email", "nickname", "first_name", "last_name", "url", "roles", "locale"),
    "menu": ("name", "description", "auto_add", "locations"),
}


def _total(api: WordPressApi, route: str, params: Mapping[str, object]) -> int:
    response = api.request(
        "GET", route, params={**params, "per_page": 1, "_fields": "id", "context": "edit"}
    )
    if response.total is not None:
        return int(response.total)
    return len(response.payload) if isinstance(response.payload, list) else 0


def comment_counts(api: WordPressApi, *, author: int = 0) -> dict[str, int]:
    """How many comments each status holds; ``author`` narrows to one person's (Mine)."""
    narrow: dict[str, object] = {"author": author} if author else {}
    return {
        status: _total(api, "wp/v2/comments", {**narrow, "status": status})
        for status, _w in COUNTED
    }


def counts_sentence(site: str, counts: Mapping[str, int], mine: int | None = None) -> str:
    """ "Community Radio: 4 waiting, 120 approved, 37 spam and 2 in the Trash; 124 in All."."""
    parts = [f"{counts.get(status, 0)} {words}" for status, words in COUNTED]
    listed = ", ".join(parts[:-1]) + f" and {parts[-1]}"
    everything = counts.get("hold", 0) + counts.get("approve", 0)
    said = f"{site}: {listed}; {everything} in All, which is waiting and approved together."
    if mine is not None:
        said += f" {mine} are yours."
    return said


def mine_count(api: WordPressApi, user_id: int) -> int:
    """wp-admin's Mine: the comments *user_id* wrote, waiting and approved."""
    return _total(api, "wp/v2/comments", {"author": user_id, "status": "all"})


def post_comment_count(api: WordPressApi, post_id: int) -> int:
    """The comments on *post_id* that wp-admin's bubble counts: approved and waiting."""
    return sum(
        _total(api, "wp/v2/comments", {"post": post_id, "status": status})
        for status in ("approve", "hold")
    )


def trashed_comments(api: WordPressApi, *, max_pages: int = 100) -> list[int]:
    """The ids of every comment in the Trash."""
    return [
        int(raw.get("id", 0) or 0)
        for raw in api.iter_collection(
            "wp/v2/comments",
            {"status": "trash", "_fields": "id"},
            per_page=100,
            max_pages=max_pages,
        )
    ]


def version_of(kind: str, raw: Mapping[str, Any]) -> str:
    """What stands for "last changed" on *raw*: ``modified_gmt``, or its edited fields."""
    modified = str(raw.get("modified_gmt", "") or "")
    if modified or kind not in _VERSION_FIELDS:
        return modified
    present = [key for key in _VERSION_FIELDS[kind] if key in raw]
    if not present:
        return ""
    return "\x1f".join(
        f"{key}={raw_text(raw[key]) if isinstance(raw[key], dict) else raw[key]}" for key in present
    )
