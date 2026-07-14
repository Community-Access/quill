"""Quick Filter for :class:`~quill.ui.github_items_dialog.GitHubItemsDialog`
(GHManage parity, Ctrl+Shift+F): a live, local narrowing of the already-
loaded list, with no network request.

Split into its own mixin (same sibling-mixin-sharing-self pattern as
:class:`~quill.ui.github_items_dialog_branches.GitHubBranchActionsMixin`) so
``github_items_dialog.py`` stays under its GATE-11 size budget.

Two accessibility details worth calling out:

- A keystroke in the filter box never moves keyboard focus into the list
  (``move_focus=False``) -- only a real fetch completing does that.
- A keystroke never triggers a status announcement (``announce=False``) --
  re-announcing "N items..." on every character would fight the screen
  reader's own character echo. A completed fetch, or the Escape-to-clear
  action, still announces (both are discrete, not per-keystroke).
"""

from __future__ import annotations

from quill.ui.github_items_view import VIEW_BRANCHES, VIEW_WORKFLOWS, row_cells, view_label


class GitHubQuickFilterMixin:
    """Adds the Quick Filter box's live-narrowing behavior to ``GitHubItemsDialog``."""

    def _on_quick_filter_changed(self, _event: object) -> None:
        self._quick_filter_query = self._quick_filter_ctrl.GetValue().strip()
        self._apply_quick_filter(move_focus=False, announce=False)

    def _quick_filter_has_focus(self) -> bool:
        return self._wx.Window.FindFocus() is self._quick_filter_ctrl

    def _apply_quick_filter(self, *, move_focus: bool, announce: bool = True) -> None:
        query = self._quick_filter_query.lower()
        if not query:
            self._rows = list(self._unfiltered_rows)
        else:
            columns = self._current_columns()
            self._rows = [
                model
                for model in self._unfiltered_rows
                if query in " ".join(row_cells(model, columns, full=False)).lower()
            ]
        self._populate_list()
        count = len(self._rows)
        noun = view_label(self._view)
        prefix = f"search '{self._search_query}': " if self._search_query else ""
        if self._quick_filter_query:
            prefix += f"filter '{self._quick_filter_query}': "
        view_hint = "  Ctrl+Shift+B=compare branches" if self._view == VIEW_BRANCHES else ""
        if self._view == VIEW_WORKFLOWS:
            view_hint = "  Enter=run on branch"
        self._set_status(
            f"{self._repo} - {prefix}{count} {noun}{'' if count == 1 else 's'}. "
            "Enter=open/drill  Ctrl+R=refresh  Ctrl+O=browser  Ctrl+G=go to  "
            "Ctrl+F=search  Ctrl+Shift+F=quick filter  Ctrl+D=favorite  "
            f"Alt+N/Alt+P=comment  List={self._list_mode}{view_hint}",
            announce=announce,
        )
        if count:
            if move_focus:
                self._list.SetFocus()
            self._list.Select(0)
            self._list.Focus(0)
            self._show_detail(0)
        else:
            self._details.Clear()


__all__ = ["GitHubQuickFilterMixin"]
