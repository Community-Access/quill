"""Why? in the GitHub Workbench: the things it did on its own, explained (GH-R-108).

The words come from :mod:`quill.core.github.why`. This mixin finds what they
are about: the selected watch, the selected notification, or the filter in
force. Shift+F1 lists Why? first whenever there is something to explain, and
the watch and notification rows have it on their context menu too.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["GitHubWorkbenchWhyMixin"]


class GitHubWorkbenchWhyMixin:
    """The provider's ``why_text`` hook and the ``why`` row verb."""

    frame: Any
    items: Any

    def why_text(self) -> str:
        """What Why? says for the selection, or "" when nothing here happened on its own."""
        frame = self.frame
        if frame is None:
            return ""
        row = frame.selected_row()
        if isinstance(row, ExploreRow) and row.kind == "watch":
            from quill.core.github.why import why_watch
            from quill.core.github.workbench_prefs import github_monitor_policy
            from quill.ui.github_workbench_watches import _store

            watch = _store(self.items).find(row.key)
            if watch is not None:
                return why_watch(watch, github_monitor_policy().poll_interval_minutes)
        if isinstance(row, ExploreRow) and row.kind == "notification":
            from quill.core.github.why import why_notification

            return why_notification(row.detail, row.repo)
        return self._why_filter()

    def _why_filter(self) -> str:
        from quill.core.github.items_provider_constants import DEFAULT_PAGE_LIMIT
        from quill.core.github.why import why_filter

        frame = self.frame
        current = frame.current
        if current is None or frame.query.is_empty:
            return ""
        node = frame.node(current)
        limit_for = getattr(self, "page_limit", None)
        limit = limit_for(current, DEFAULT_PAGE_LIMIT) if callable(limit_for) else 0
        loaded = len(frame.rows)
        return why_filter(
            frame.filter_words(),
            remote=bool(self.remote_words(node)),  # type: ignore[attr-defined]
            loaded=loaded,
            complete=loaded < limit,
        )

    def _fits_why(self, _row: object) -> bool:
        return bool(self.why_text())

    def _do_why(self, _ref: Any, _row: object) -> None:
        self.frame._announce(self.why_text() or "Nothing here happened on its own.")
