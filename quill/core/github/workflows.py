"""GitHub Actions workflow *definitions* (not runs) -- GHManage's Workflows
view: Enter (or the Actions... menu) runs the selected one on a branch you
choose.

Split out of :mod:`quill.core.github.items_provider` to keep that module
under its GATE-11 size budget. No import of ``items_provider`` needed --
:meth:`~quill.core.github.items_provider.GitHubItemsProvider.dispatch_workflow`
(already in that module) does the actual triggering, given the workflow's
``id`` from :class:`GitHubWorkflow` below.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubWorkflow:
    """One workflow definition (the ``.yml`` file itself), not a run of it."""

    id: int
    name: str
    path: str
    state: str
    url: str = ""
    badge_url: str = ""


def list_workflows(
    repo: Any, *, limit: int, take: Callable[[Any, int], list[Any]]
) -> list[GitHubWorkflow]:
    rows = take(repo.get_workflows(), limit)
    return [
        GitHubWorkflow(
            id=int(getattr(row, "id", 0) or 0),
            name=str(getattr(row, "name", "") or ""),
            path=str(getattr(row, "path", "") or ""),
            state=str(getattr(row, "state", "") or ""),
            url=str(getattr(row, "html_url", "") or ""),
            badge_url=str(getattr(row, "badge_url", "") or ""),
        )
        for row in rows
    ]


__all__ = ["GitHubWorkflow", "list_workflows"]
