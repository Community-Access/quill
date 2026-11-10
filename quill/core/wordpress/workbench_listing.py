"""How much of a list the WordPress Workbench reads, which columns it shows, how it groups.

Three things a long list needs (GitHub PRD 17.3 and 17.4, WordPress PRD 10):

- **Paging.** A list reads :data:`~quill.core.wordpress.workbench_load.MAX_PAGES`
  pages of 100 at first. :class:`Paging` remembers, per node, how many pages
  were asked for; View > Load More adds three more pages, and Load All reads
  until the site has no more (stopping at :data:`ALL_PAGES`, ten thousand
  rows, so a runaway site cannot hang the window). :func:`page_limit` is the
  context the loaders read, so no loader signature changes. :func:`cut_words`
  says, honestly, when a list stopped short.
- **Columns.** Every row family has the columns its node shows and the ones
  it can show (:data:`EXTRA_COLUMNS`); the extra cells come from the object
  the site sent (:func:`extra_cell`), so nothing is fetched again.
- **Group By.** Grouping by a column gives the node one child per value
  ("Draft (4)"), read by :func:`groups`; selecting a group lists its rows.
  The value travels in the group node's instance (:func:`group_instance`).

Wx-free and network-free.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.site import friendly_date, human_size
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "ALL_PAGES",
    "EXTRA_COLUMNS",
    "GROUP_MARK",
    "MORE_PAGES",
    "Paging",
    "column_title",
    "cut_words",
    "extra_cell",
    "group_instance",
    "group_of",
    "groups",
    "page_limit",
    "pages_for",
    "parse_group",
]

MORE_PAGES = 3
"""Pages Load More adds: another three hundred rows."""

ALL_PAGES = 100
"""The most Load All reads: ten thousand rows of a hundred."""

GROUP_MARK = "group="
"""Starts a group node's part of its instance: ``group=status=Draft``."""

_PAGES: ContextVar[int] = ContextVar("workbench_pages", default=0)


@contextmanager
def page_limit(pages: int) -> Iterator[None]:
    """Within the block, collections read at most *pages* pages (0 keeps the loader's own)."""
    token = _PAGES.set(pages)
    try:
        yield
    finally:
        _PAGES.reset(token)


def pages_for(default: int) -> int:
    """The page limit in effect: the block's, or *default*."""
    return _PAGES.get() or default


@dataclass
class Paging:
    """How many pages each node has asked for, by a key the provider makes."""

    first: int = 3
    asked: dict[str, int] = field(default_factory=dict)

    def pages(self, node: str) -> int:
        return self.asked.get(node, self.first)

    def more(self, node: str) -> int:
        self.asked[node] = min(ALL_PAGES, self.pages(node) + MORE_PAGES)
        return self.asked[node]

    def all(self, node: str) -> int:
        self.asked[node] = ALL_PAGES
        return ALL_PAGES

    def forget(self, node: str) -> None:
        self.asked.pop(node, None)


def cut_words(count: int, pages: int, *, per_page: int = 100) -> str:
    """ "First 300 shown; View > Load More reads more." when the list stopped at its limit."""
    limit = pages * per_page
    if count < limit:
        return ""
    if pages >= ALL_PAGES:
        return f"The first {limit} are shown, the most the Workbench reads at once."
    return (
        f"The first {limit} are shown, and the site has more. View > Load More reads "
        f"{MORE_PAGES * per_page} more; Load All reads every one."
    )


#: Columns each row kind can show beyond its node's own, by the name the cell reads.
EXTRA_COLUMNS: Mapping[str, tuple[str, ...]] = {
    "item": ("date", "slug", "id", "type", "comments", "sticky", "format", "parent", "site"),
    "media": ("mime_type", "size", "attached", "author", "id", "slug", "site"),
    "comment": ("author_email", "post", "id", "site"),
    "term": ("id", "description", "parent", "site"),
    "user": ("id", "slug", "registered", "site"),
    "plugin": ("description", "auto_update", "site"),
    "theme": ("author", "site"),
    "form_entry": ("id", "site"),
}

_TITLES = {
    "id": "Number",
    "mime_type": "File type",
    "author_email": "Email",
    "auto_update": "Updates itself",
    "comments": "Comments",
}


def column_title(name: str) -> str:
    """A column's heading: ``mime_type`` reads "File type"."""
    return _TITLES.get(name, name.replace("_", " ").capitalize())


def _text(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("raw", "rendered"):
            if key in value:
                return str(value[key] or "")
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return ""
    return str(value)


def extra_cell(row: WbRow, column: str) -> str:
    """The cell for *column*: the row's own, or read from the object the site sent."""
    own = row.cell(column)
    if own:
        return own
    raw = row.raw
    if column == "id":
        return row.key
    if column == "comments":
        return _text(raw.get("comment_status"))
    if column == "attached":
        parent = int(raw.get("post", 0) or 0)
        return f"post {parent}" if parent else "not attached"
    if column == "size":
        details = raw.get("media_details") if isinstance(raw.get("media_details"), dict) else {}
        size = int((details or {}).get("filesize", 0) or 0)
        return human_size(size) if size else ""
    if column == "registered":
        return friendly_date(str(raw.get("registered_date", "") or ""))
    if column == "date":
        date = str(raw.get("date_gmt", "") or raw.get("date", "") or "")
        return friendly_date(date) if date else ""
    return _text(raw.get(column))


def group_of(row: WbRow, column: str) -> str:
    """The group *row* falls in when grouping by *column* ("(none)" for an empty cell)."""
    return extra_cell(row, column) or "(none)"


def groups(rows: Sequence[WbRow], column: str) -> list[tuple[str, int]]:
    """Each value of *column* in *rows*, with how many rows have it, in first-seen order."""
    counts = Counter(group_of(row, column) for row in rows)
    seen: list[str] = []
    for row in rows:
        value = group_of(row, column)
        if value not in seen:
            seen.append(value)
    return [(value, counts[value]) for value in seen]


def group_instance(site: str, sep: str, column: str, value: str) -> str:
    """The instance a group node carries: the site, then ``group=<column>=<value>``."""
    return f"{site}{sep}{GROUP_MARK}{column}={value}"


def parse_group(kind: str) -> tuple[str, str] | None:
    """``group=status=Draft`` back to ``("status", "Draft")``; None for anything else."""
    if not kind.startswith(GROUP_MARK):
        return None
    column, _sep, value = kind.removeprefix(GROUP_MARK).partition("=")
    return (column, value) if column else None
