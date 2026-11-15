"""The WordPress Workbench's status bar cells (PRD section 4).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:
site, role, items, filter, loading, waiting comments and Workbench access, each
with what Enter does and its context menu. Nothing here is announced; the
cells are read when the user moves to them.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress.workbench_actions import PREFIX
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.filters import describe
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame
from quill.ui.workbench_status_bar import StatusCell

__all__ = ["WorkbenchStatusCells"]


class WorkbenchStatusCells:
    """The status bar cells the shared Workbench frame shows for WordPress."""

    frame: Any
    view_as: dict[str, str]
    _contexts: dict[str, Any]
    _waiting: dict[str, int]
    site_of: Callable[[Any], str]
    cut_for: Callable[[Any], Any]
    access_for: Callable[[str], Any]

    def status_cells(self, frame: WorkbenchFrame) -> Sequence[StatusCell]:
        self.frame = frame

        def site_status() -> str:
            if frame.current is not None and frame.current.key == "search":
                selected = frame.selected_row()
                if isinstance(selected, WbRow) and selected.site:
                    return selected.site
                return "All connected sites"
            return self.site_of(frame.current)

        def items_text() -> str:
            if frame.current is None or not frame.node(frame.current).loader:
                return ""
            chosen = len(frame.selected_indices())
            shown = f"{len(frame.rows)} shown"
            if self.cut_for(frame.current):
                shown += ", more on the site"
            return f"{shown}, {chosen} selected" if chosen > 1 else shown

        def loading() -> str:
            if frame.loading:
                return "Loading"
            return f"Up to date, {frame.loaded_at}" if frame.loaded_at else ""

        def role() -> str:
            site = self.site_of(frame.current)
            ctx = self._contexts.get(site)
            if not site or ctx is None or ctx.account is None:
                return ""
            viewing = self.view_as.get(site)
            if viewing:
                return f"Viewing as {viewing.title()} on {site}"
            return f"{ctx.account.role_name} on {site}"

        def waiting() -> str:
            count = sum(self._waiting.values())
            return f"{count} comments waiting" if count else ""

        def access() -> str:
            site = self.site_of(frame.current)
            return self.access_for(site).words if site else ""

        return (
            StatusCell(
                "site",
                "Site",
                site_status,
                "The site the selected node belongs to. Enter selects its overview.",
                activate=lambda: frame.go(f"{PREFIX}go_site"),
                menu=lambda: (
                    ("Site Properties", lambda: self.do_site_sheet(frame.current, None)),
                ),
            ),
            StatusCell(
                "role",
                "Your role",
                role,
                "Your role on this site. Enter says what it lets you do here.",
                activate=lambda: self.do_what_can_i_do(frame.current, None),
                menu=lambda: (("View As Role...", lambda: self.do_view_as(frame.current, None)),),
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
            StatusCell(
                "waiting",
                "Waiting",
                waiting,
                "Comments waiting on your sites, when there are any. Enter goes to them.",
                activate=lambda: frame.select(NodeRef("", "waiting")),
            ),
            StatusCell(
                "links",
                "Link check",
                lambda: self.link_check_status(),  # type: ignore[attr-defined]
                "Check Every Link's count while it runs. Enter stops it; what it found is kept.",
                activate=lambda: self.stop_link_check(),  # type: ignore[attr-defined]
                menu=lambda: (("Stop Checking Links", self.stop_link_check),),  # type: ignore[attr-defined]
            ),
            StatusCell(
                "access",
                "Workbench access",
                access,
                "How much the Workbench may change on this site. Enter changes it.",
                activate=lambda: self.do_access(frame.current, None),
            ),
        )
