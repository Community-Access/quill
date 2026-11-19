"""Discussions' own places: the categories by section, and voting from the sheet.

Repository > Discussions > Categories lists :mod:`quill.core.github.discussion_categories`'
rows. Enter on a section ("Section: Q&A (3 categories)") opens it, and its
first row, "All sections", comes back; the open section is kept apart from
Files' folder (:func:`~quill.ui.github_workbench_loaders.place_key`). Enter on a
category goes to Discussions with the list narrowed to that category's name.

A discussion's Properties sheet shows its poll as a table; Add... or Change...
on that table is Vote..., the same quick command the discussion's row has
(:mod:`quill.core.github.quick_table_discuss`), so there is one way to vote.
GitHub has no way to take a vote back, and the table's Remove says so.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["DISCUSSION_REASONS", "DISCUSSION_VERBS", "GitHubWorkbenchDiscussionsMixin"]

DISCUSSION_VERBS: dict[str, frozenset[str]] = {
    "open_section": frozenset({"discussion_section"}),
    "category_discussions": frozenset({"discussion_category"}),
}
DISCUSSION_REASONS: dict[str, str] = {
    "open_section": "Open Section is for a section under Discussions, Categories.",
    "category_discussions": (
        "Find Discussions in Category is for a category under Discussions, Categories."
    ),
}

#: Said by the poll table's Remove: GitHub keeps a poll vote once it is cast.
NO_UNVOTE = "GitHub does not let a poll vote be taken back, here or on its own page."


class GitHubWorkbenchDiscussionsMixin:
    frame: Any
    _folders: dict[str, str]
    _say: Callable[[str], None]
    # Annotations only: a stub here would shadow the real ones later in the MRO.
    _go_filtered: Callable[[str, str, str, str], None]
    quick_start: Callable[[Any, dict[str, str]], None]

    @staticmethod
    def _discussion_row(row: object, kind: str) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == kind
        return row if found and isinstance(row, ExploreRow) else None

    def _fits_open_section(self, row: object) -> bool:
        return self._discussion_row(row, "discussion_section") is not None

    def _do_open_section(self, ref: Any, row: object) -> None:
        from quill.ui.github_workbench_loaders import place_key

        found = self._discussion_row(row, "discussion_section")
        if found is None:
            return
        self._folders[place_key(str(ref.key), str(ref.instance))] = found.key
        self.frame.reload()

    def _fits_category_discussions(self, row: object) -> bool:
        found = self._discussion_row(row, "discussion_category")
        return found is not None and bool(found.key)

    def _do_category_discussions(self, ref: Any, row: object) -> None:
        found = self._discussion_row(row, "discussion_category")
        if found is None:
            return
        name = found.key
        words = f'"{name}"' if " " in name else name
        self._go_filtered("repository", "discussions", found.repo or str(ref.instance), words)

    def vote_from_sheet(self, ident: dict[str, str], verb: str) -> None:
        """The Properties sheet's poll table: Add... and Change... vote; Remove cannot."""
        if verb == "remove":
            self._say(NO_UNVOTE)
            return
        from quill.core.github.quick_tables import QUICK

        vote = next(q for q in QUICK if q.verb == "poll_vote")
        number = str(ident.get("number") or "")
        ctx = {"repo": str(ident.get("repo") or ""), "key": number, "name": f"#{number}"}
        self.quick_start(vote, ctx)
