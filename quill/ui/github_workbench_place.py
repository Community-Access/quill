"""Where the GitHub Workbench was, what it says on request, and what a result means.

Three small jobs for :class:`quill.ui.github_workbench_window.GitHubWorkbenchProvider`,
kept out of that module (GATE-11):

- **The place** (GitHub PRD 3.1 and 9): the last node, the expanded nodes and
  the repositories and people the tree showed, per account, in
  ``github_items_context.json`` beside GitHub Items' resume state
  (:mod:`quill.core.github.navigation_state`). A big account never means
  re-expanding everything.
- **The readouts** (Part C, C4): Alt+3, Alt+4, Alt+5, Alt+6 and Alt+9 say a
  fact and move nothing; the person asked, so GATE-13 allows them.
- **Explain That** (Shift+F9, Part D13): what the last result means and what
  you might do next, from the help catalogue
  (:func:`quill.core.github.workbench_help.explain_result`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem, GitHubWorkflowRun
from quill.core.github.navigation_state import (
    WorkbenchPlace,
    account_key_for_token,
    load_workbench_place,
    save_workbench_place,
)

__all__ = ["GitHubWorkbenchPlaceMixin"]


class GitHubWorkbenchPlaceMixin:
    """The GitHub provider's memory, readouts and explanations."""

    items: Any
    frame: Any
    _repositories: list[str]
    _people: list[str]

    def _account_key(self) -> str:
        return account_key_for_token(getattr(self.items, "token", None))

    def adopt_remembered_instances(self) -> None:
        """Put last time's repositories and people back in the tree, current first."""
        place = load_workbench_place(self._account_key())
        for name in place.repositories:
            if name not in self._repositories:
                self._repositories.append(name)
        for name in place.people:
            if name not in self._people:
                self._people.append(name)

    def recall_place(self) -> tuple[list[Any], Any] | None:
        from quill.ui.workbench_frame import NodeRef

        place = load_workbench_place(self._account_key())
        if place.last is None and not place.expanded:
            return None
        expanded = [NodeRef(*ref) for ref in place.expanded]
        last = NodeRef(*place.last) if place.last else None
        return expanded, last

    def remember_place(self, place: tuple[Sequence[Any], Any]) -> None:
        expanded, current = place
        save_workbench_place(
            self._account_key(),
            WorkbenchPlace(
                last=(current.template, current.key, current.instance) if current else None,
                expanded=tuple((r.template, r.key, r.instance) for r in expanded),
                repositories=tuple(self._repositories),
                people=tuple(self._people),
            ),
        )

    # -- readouts ---------------------------------------------------------------

    def readout(self, name: str) -> str | None:
        """The words for Alt+*number*; ``None`` when the answer comes later."""
        frame = self.frame
        if frame is None:
            return ""
        if name == "item":
            return _item_words(frame.selected_row())
        if name == "counts":
            shown, loaded = len(frame.rows), len(getattr(frame, "_loaded", frame.rows))
            chosen = len(frame.selected_indices())
            words = f"{shown} shown" if shown == loaded else f"{shown} of {loaded} shown"
            return f"{words}, {chosen} selected" if chosen > 1 else words
        if name == "access":
            if not getattr(self, "signed_in", False):
                return "You are not signed in, so you can read public repositories only."
            return (
                "You are signed in. Rows that need push or admin access ask GitHub when "
                "you use them, and say so if you do not have it."
            )
        if name == "account":
            signed = "Signed in" if getattr(self, "signed_in", False) else "Not signed in"
            return f"{signed}. The Workbench can read and change things for this account."
        if name == "rate":
            frame.run("github.workbench.rate_limit")
            return None
        return ""

    def explain(self, text: str) -> str:
        from quill.core.github.workbench_help import explain_result

        return explain_result(text)


def _item_words(row: object) -> str:
    """Alt+3: the selected item's state in one line."""
    if row is None:
        return "Nothing selected."
    if isinstance(row, GitHubItem):
        kind = "Pull request" if row.is_pr else "Issue"
        labels = f", labels {', '.join(row.labels)}" if row.labels else ""
        return f"{kind} #{row.number}, {row.state}, {row.title}{labels}"
    if isinstance(row, GitHubWorkflowRun):
        outcome = row.conclusion or row.status
        return f"Run {row.name}, {outcome}"
    if isinstance(row, ExploreRow):
        return row.label
    return str(getattr(row, "name", "") or getattr(row, "title", "") or "Selected.")
