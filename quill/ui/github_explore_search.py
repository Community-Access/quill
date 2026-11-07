"""Saved search controls for the GitHub Explore dialog."""

from __future__ import annotations

from quill.core.github.explore_views import QUERY_VIEWS


class GitHubExploreSearchMixin:
    """Saved search commands for the Explore dialog."""

    def _save_search(self, _event: object) -> None:
        query = self._query.GetValue().strip()
        if self._saved.save_search(query):
            self._announce("Global search saved locally.")
        else:
            self._announce("Enter a new global search query to save.")

    def _saved_searches_menu(self, _event: object) -> None:
        wx = self._wx
        if not self._saved.searches:
            self._announce("No saved searches yet.")
            return
        menu = wx.Menu()
        ids: list[object] = []
        for query in self._saved.searches:
            item_id = wx.NewIdRef()
            ids.append(item_id)
            menu.Append(item_id, query)
            menu.Bind(wx.EVT_MENU, lambda _e, value=query: self._run_saved(value), id=item_id)
        try:
            self._saved_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _run_saved(self, query: str) -> None:
        self._query.SetValue(query)
        if self._view_key() not in QUERY_VIEWS:
            self._view.SetSelection(0)
        self._load(None)

    def _remove_search(self, query: str) -> None:
        self._announce(
            "Saved search removed."
            if self._saved.remove_search(query)
            else "This search is not saved."
        )


__all__ = ["GitHubExploreSearchMixin"]
