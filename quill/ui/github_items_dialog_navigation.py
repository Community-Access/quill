"""Save and restore the local repository and row shown in GitHub Items."""

from __future__ import annotations

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
    GitHubTag,
    GitHubWorkflowRun,
)
from quill.core.github.navigation_state import GitHubItemsContext, GitHubNavigationState
from quill.core.github.workflows import GitHubWorkflow
from quill.ui.github_items_view import SORT_ORDERS, VIEWS


class GitHubNavigationMixin:
    """Keep a local per-account resume point for the shared Items window."""

    def _restore_navigation(self, provider: object, initial_reference: object | None) -> None:
        self._navigation_state = GitHubNavigationState.load(getattr(provider, "token", None))
        context = self._navigation_state.context
        self._restore_selection_key = ""
        self._resume_selection_missing = False
        if initial_reference is not None:
            return
        if not self._repo and context.repository:
            self._repo = context.repository
        if context.repository and self._repo.casefold() != context.repository.casefold():
            return
        self._restore_selection_key = context.selected_key
        if any(key == context.view for key, _label in VIEWS):
            self._view = context.view
        self._show = context.show
        self._state = context.state
        if any(key == context.sort for key, _label in SORT_ORDERS):
            self._sort = context.sort
        self._search_query = context.search_query
        self._quick_filter_query = context.quick_filter_query
        self._drill_branch = context.drill_branch or None

    def _restore_saved_selection(self) -> None:
        if self._initial_reference is not None:
            return
        selected_key = self._restore_selection_key
        self._restore_selection_key = ""
        self._resume_selection_missing = False
        if not selected_key:
            return
        index = next(
            (
                index
                for index, row in enumerate(self._rows)
                if self._navigation_key(row) == selected_key
            ),
            -1,
        )
        if index < 0:
            self._resume_selection_missing = True
            self._announce(
                "The previous item is outside the loaded results. "
                "Use View more or search to find it."
            )
            return
        self._list.SetFocus()
        self._list.Select(index)
        self._list.Focus(index)
        self._show_detail(index)
        self._announce("Restored the last selected GitHub item.")

    def _save_navigation_state(self) -> None:
        if not hasattr(self, "_navigation_state"):
            return
        timer = getattr(self, "_navigation_timer", None)
        if timer is not None:
            timer.Stop()
            self._navigation_timer = None
        context = (
            self._navigation_state.context
            if getattr(self, "_resume_selection_missing", False)
            else self._current_navigation_context()
        )
        self._navigation_state.save(context)
        self._update_navigation_buttons()

    def _current_navigation_context(self) -> GitHubItemsContext:
        selection = self._list.GetFirstSelected()
        selected_key = (
            self._navigation_key(self._rows[selection]) if 0 <= selection < len(self._rows) else ""
        )
        view_index = self._view_choice.GetSelection()
        show_index = self._show_choice.GetSelection()
        state_index = self._state_choice.GetSelection()
        sort_index = self._sort_choice.GetSelection()
        return GitHubItemsContext(
            repository=self._repo,
            view=VIEWS[view_index][0] if 0 <= view_index < len(VIEWS) else self._view,
            show=("both", "issues", "prs")[show_index] if 0 <= show_index < 3 else self._show,
            state=("open", "closed", "all")[state_index] if 0 <= state_index < 3 else self._state,
            sort=SORT_ORDERS[sort_index][0] if 0 <= sort_index < len(SORT_ORDERS) else self._sort,
            search_query=self._search_query,
            quick_filter_query=self._quick_filter_query,
            selected_key=selected_key,
            drill_branch=self._drill_branch or "",
        )

    def _record_navigation_location(self) -> None:
        if not hasattr(self, "_navigation_state"):
            return
        self._resume_selection_missing = False
        self._navigation_state.record(self._current_navigation_context())
        self._update_navigation_buttons()

    def _schedule_navigation_record(self) -> None:
        timer = getattr(self, "_navigation_timer", None)
        if timer is not None:
            timer.Stop()
        self._navigation_timer = self._wx.CallLater(450, self._record_navigation_location)

    def _update_navigation_buttons(self) -> None:
        if not hasattr(self, "_navigation_state"):
            return
        if hasattr(self, "_back_btn"):
            self._back_btn.Enable(self._navigation_state.can_go_back)
        if hasattr(self, "_forward_btn"):
            self._forward_btn.Enable(self._navigation_state.can_go_forward)

    def _go_back(self, _event: object | None = None) -> None:
        context = self._navigation_state.back()
        if context is None:
            self._announce("There is no previous GitHub location.")
            self._update_navigation_buttons()
            return
        self._apply_navigation_context(context)
        self._announce("Returned to the previous GitHub location.")

    def _go_forward(self, _event: object | None = None) -> None:
        context = self._navigation_state.forward()
        if context is None:
            self._announce("There is no next GitHub location.")
            self._update_navigation_buttons()
            return
        self._apply_navigation_context(context)
        self._announce("Moved forward to the next GitHub location.")

    def _apply_navigation_context(self, context: GitHubItemsContext) -> None:
        self._resume_selection_missing = False
        self._initial_reference = None
        self._repo = context.repository
        self._repo_ctrl.SetValue(context.repository)
        self._view = context.view
        self._show = context.show
        self._state = context.state
        self._sort = context.sort
        self._search_query = context.search_query
        self._quick_filter_query = context.quick_filter_query
        self._drill_branch = context.drill_branch or None
        self._drill_release = None
        self._restore_selection_key = context.selected_key
        self._page = 1
        self._view_choice.SetSelection(
            next((i for i, (key, _label) in enumerate(VIEWS) if key == context.view), 0)
        )
        self._show_choice.SetSelection({"both": 0, "issues": 1, "prs": 2}.get(context.show, 0))
        self._state_choice.SetSelection({"open": 0, "closed": 1, "all": 2}.get(context.state, 0))
        self._sort_choice.SetSelection(
            next(
                (i for i, (key, _label) in enumerate(SORT_ORDERS) if key == context.sort),
                0,
            )
        )
        self._search_ctrl.ChangeValue(context.search_query)
        self._quick_filter_ctrl.ChangeValue(context.quick_filter_query)
        self._rebuild_columns()
        self._apply_filter_enablement()
        self._update_navigation_buttons()
        self._on_load(None)

    @staticmethod
    def _navigation_key(row: object) -> str:
        if isinstance(row, GitHubItem):
            kind = "pr" if row.is_pr else "issue"
            return f"{kind}:{row.number}"
        if isinstance(row, GitHubBranch):
            return f"branch:{row.name}"
        if isinstance(row, GitHubCommit):
            return f"commit:{row.sha}"
        if isinstance(row, GitHubTag):
            return f"tag:{row.name}"
        if isinstance(row, GitHubRelease):
            return f"release:{row.tag}"
        if isinstance(row, GitHubWorkflowRun):
            return f"run:{row.id}"
        if isinstance(row, GitHubWorkflow):
            return f"workflow:{row.id}"
        return ""


__all__ = ["GitHubNavigationMixin"]
