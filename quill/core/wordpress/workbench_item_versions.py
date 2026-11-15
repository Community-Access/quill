"""Earlier Versions on a post, page or custom item's Workbench row (wp_missing.md, Posts).

The editor's Previous Versions (``cmd_versions`` in
:mod:`quill.ui.wordpress_more_commands`) reads ``{type}/{id}/revisions`` and ``/autosaves`` through
:func:`quill.core.wordpress.site.list_revisions`; this is the same history
from a row, without opening the item. A version is compared with the item as
it is now in words, line by line (:func:`quill.core.wordpress.workbench_site_editor.change_lines`,
as template rows do), and restoring it sends its title and content back to
the item, which WordPress keeps as a new revision of its own:

- the item is read again just before the write, and one changed on the site
  since it was read (its ``modified_gmt`` or its content) is left alone;
- :func:`put_back`, the undo, sends the earlier title and content again, and
  refuses when somebody changed the item after the restore.

Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import Revision, friendly_date, list_revisions, raw_text, rendered
from quill.core.wordpress.workbench_edit import EditConflict
from quill.core.wordpress.workbench_site_editor import change_lines

__all__ = [
    "ItemText",
    "compare_lines",
    "earlier_versions",
    "load_item",
    "put_back",
    "restore_version",
    "version_label",
]


@dataclass(frozen=True)
class ItemText:
    """An item's title and content as the site has them, and when it last changed."""

    route: str
    title: str
    content: str
    modified_gmt: str


def load_item(api: Any, route: str) -> ItemText:
    """The item at *route*, read with ``context=edit`` so its raw markup comes back."""
    raw = api.get(route, context="edit")
    if not isinstance(raw, dict) or not raw.get("id"):
        raise WordPressApiError("The site did not return this item, so nothing was changed.")
    return ItemText(
        route,
        raw_text(raw.get("title")) or rendered(raw.get("title")),
        raw_text(raw.get("content")) or rendered(raw.get("content")),
        str(raw.get("modified_gmt", "") or ""),
    )


def earlier_versions(api: Any, kind: str, item_id: int, now: ItemText) -> list[Revision]:
    """The site's revisions and autosaves, newest first, leaving out any the same as now."""
    return [
        rev
        for rev in list_revisions(api, kind, item_id)
        if (rev.title, rev.content) != (now.title, now.content)
    ]


def version_label(rev: Revision) -> str:
    """One version in words: when, its title, and whether it is an autosave."""
    when = friendly_date(rev.date_gmt) if rev.date_gmt else "a date not said"
    what = "an autosave" if rev.autosave else "a revision"
    return f"Saved {when}, {rev.title or '(untitled)'}, {what}"


def compare_lines(now: ItemText, rev: Revision) -> list[str]:
    """What restoring *rev* changes, in words: the title, then the content line by line."""
    lines: list[str] = []
    if rev.title != now.title:
        lines.append(f"Title: {now.title or '(untitled)'} becomes {rev.title or '(untitled)'}.")
    return lines + change_lines(now.content, rev.content)


def _check(api: Any, seen: ItemText, what: str) -> None:
    current = load_item(api, seen.route)
    if current.modified_gmt != seen.modified_gmt or current.content != seen.content:
        raise EditConflict(
            f"{what} was changed on the site after QUILL read it. Nothing was sent; read it "
            "again and choose the version there."
        )


def _send(api: Any, route: str, title: str, content: str) -> ItemText:
    answer = api.post(route, {"title": title, "content": content}, context="edit")
    modified = str(answer.get("modified_gmt", "") or "") if isinstance(answer, dict) else ""
    return ItemText(route, title, content, modified)


def restore_version(api: Any, loaded: ItemText, rev: Revision) -> ItemText:
    """Conflict-checked: give the item *rev*'s title and content; returns the item after."""
    _check(api, loaded, loaded.title or "This item")
    return _send(api, loaded.route, rev.title, rev.content)


def put_back(api: Any, saved: ItemText, before: ItemText) -> None:
    """The undo of a restore: *before*'s title and content, unless the item changed since."""
    current = load_item(api, saved.route)
    if current.content != saved.content or current.title != saved.title:
        raise EditConflict(
            f"{saved.title or 'This item'} was changed on the site after the restore, so it "
            "was left as it is."
        )
    _send(api, saved.route, before.title, before.content)
