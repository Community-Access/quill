"""The GitHub Workbench's status bar cells (GitHub PRD section 4).

Split from :mod:`quill.ui.github_workbench_window` (GATE-11): Account,
Repository, Items (with the provider's local note, such as Across
Repositories' per-repository sentences), Filter and Loading.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.workbench.filters import describe
from quill.ui.workbench_status_bar import StatusCell

__all__ = ["github_status_cells"]


def _dry_run_words() -> str:
    from quill.core.github.dry_run import DRY_RUN

    return ". Dry Run: nothing is sent" if DRY_RUN.on else ""


def github_status_cells(provider: Any, frame: Any) -> Sequence[StatusCell]:
    """The five cells, reading *provider* and *frame* each time they are drawn."""

    def repository() -> str:
        current = frame.current
        if current is None or current.template != "repository":
            return ""
        return current.instance

    def items_text() -> str:
        if frame.current is None or not frame.node(frame.current).loader:
            return ""
        chosen = len(frame.selected_indices())
        shown = f"{len(frame.rows)} shown"
        said = f"{shown}, {chosen} selected" if chosen > 1 else shown
        return f"{said}. {provider.local_note}" if provider.local_note else said

    def loading() -> str:
        if frame.loading:
            return "Loading"
        return f"Up to date, {frame.loaded_at}" if frame.loaded_at else ""

    return (
        StatusCell(
            "account",
            "Account",
            lambda: ("Signed in" if provider.signed_in else "Not signed in") + _dry_run_words(),
            "Whether GitHub knows who you are. The editor's GitHub menu manages accounts.",
        ),
        StatusCell(
            "repository",
            "Repository",
            repository,
            "The repository the selected node belongs to. Enter selects its node.",
            activate=lambda: frame.go("github.workbench.go_repository"),
            menu=lambda: (("Open on GitHub", frame.open_in_browser),),
        ),
        StatusCell(
            "items",
            "Items",
            items_text,
            "How many rows the list shows and how many are selected.",
            activate=frame.list.SetFocus,
        ),
        StatusCell(
            "filter",
            "Filter",
            lambda: describe(frame.query) if frame.current is not None else "",
            "The filter in effect. Enter moves to the filter box.",
            activate=frame.filter.SetFocus,
            menu=lambda: (("Clear Filter", frame.clear_filter),),
        ),
        StatusCell(
            "loading",
            "Loading",
            loading,
            "Whether the list is still loading, or when it last loaded. Enter refreshes.",
            activate=frame.reload,
            menu=lambda: (("Refresh", frame.reload),),
        ),
    )
