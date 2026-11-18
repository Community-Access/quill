"""Repositories > Star Lists: making, changing and filling star lists (GitHub PRD 14.2).

The node's rows are repositories (:mod:`quill.core.github.star_lists`). This
mixin adds **New Star List...** (``Ctrl+N`` in Star Lists), **Star Lists...**
on any repository row, which chooses the lists it is on, and **Rename or
Delete Star List...** on a row in Star Lists, for the list that row is on.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["STAR_LIST_REASONS", "STAR_LIST_VERBS", "GitHubWorkbenchStarListsMixin"]

STAR_LIST_VERBS: dict[str, frozenset[str]] = {
    "new_star_list": frozenset({"view"}),
    "star_lists": frozenset({"repo"}),
    "edit_star_list": frozenset({"repo"}),
}

STAR_LIST_REASONS: dict[str, str] = {
    "new_star_list": "New Star List is for Repositories > Star Lists, while you are signed in.",
    "star_lists": "Star Lists is for a repository, while you are signed in.",
    "edit_star_list": "Rename or Delete Star List is for a row in Star Lists.",
}

_CHANGES = ("Rename or describe it", "Make it private", "Make it public", "Delete it")


class GitHubWorkbenchStarListsMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _in_star_lists(self) -> bool:
        return getattr(getattr(self.frame, "current", None), "key", "") == "star_lists"

    @staticmethod
    def _repo_row(row: object) -> str:
        return row.repo if isinstance(row, ExploreRow) and row.kind == "repo" else ""

    def _fits_new_star_list(self, _row: object) -> bool:
        return self.signed_in and self._in_star_lists()

    def _fits_star_lists(self, row: object) -> bool:
        return self.signed_in and "/" in self._repo_row(row)

    def _fits_edit_star_list(self, row: object) -> bool:
        return self.signed_in and self._in_star_lists() and bool(self._repo_row(row))

    def _reload_saying(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    def _do_new_star_list(self, _ref: Any, _row: object) -> None:
        from quill.core.github.star_lists import create_list

        name = self._ask_text("New Star List", "Name of the new star list, up to 32 characters:")
        if not name:
            return
        description = self._ask_text(
            "New Star List", f"A short description of {name}, or leave it empty:"
        )
        private = self._choose(
            "New Star List", f"Who can see {name}?", ["Only you (private)", "Everyone (public)"]
        )
        if private < 0:
            return
        api = self.github_api()
        self._background(
            "make the star list",
            lambda: create_list(api, name, description, private=private == 0),
            self._reload_saying,
        )

    def _do_star_lists(self, _ref: Any, row: object) -> None:
        from quill.core.github.star_lists import fetch_lists

        repository = self._repo_row(row)
        api = self.github_api()
        self._background(
            "read your star lists",
            lambda: fetch_lists(api),
            lambda lists: self._choose_lists(repository, list(lists)),
        )

    def _choose_lists(self, repository: str, lists: list[Any]) -> None:
        from quill.core.github.star_lists import set_lists_for
        from quill.ui.dialog_contract import show_modal_dialog

        if not lists:
            self._say("You have no star lists yet. Make one in Repositories > Star Lists.")
            return
        wx = self.frame._wx
        labels = [found.label for found in lists]
        title = "Star Lists"
        with wx.MultiChoiceDialog(
            self.frame.frame, f"Which star lists is {repository} on?", title, labels
        ) as dialog:
            dialog.SetSelections([
                i
                for i, found in enumerate(lists)
                if any(repo == repository for repo, _d in found.repositories)
            ])
            if show_modal_dialog(dialog, title) != wx.ID_OK:
                return
            chosen = [lists[i] for i in dialog.GetSelections()]
        api = self.github_api()
        self._background(
            "change the star lists",
            lambda: set_lists_for(api, repository, chosen),
            self._reload_saying,
        )

    def _do_edit_star_list(self, _ref: Any, row: object) -> None:
        from quill.core.github.star_lists import fetch_lists

        name = row.label.split(":", 1)[0] if isinstance(row, ExploreRow) else ""
        api = self.github_api()
        self._background(
            "read your star lists",
            lambda: fetch_lists(api),
            lambda lists: self._edit_list(name, list(lists)),
        )

    def _edit_list(self, name: str, lists: list[Any]) -> None:
        from quill.core.github.star_lists import delete_list, update_list

        found = next((each for each in lists if each.name == name), None)
        if found is None:
            self._say(f"GitHub no longer has a star list called {name}.")
            return
        picked = self._choose("Star List", f"What to do with {found.label}?", list(_CHANGES))
        if picked < 0:
            return
        api = self.github_api()
        if picked == 3:
            if not self._confirm(
                "Delete Star List",
                f"Delete the star list {found.name}? Its repositories stay starred.",
            ):
                return
            work: Callable[[], Any] = lambda: delete_list(api, found)  # noqa: E731
        elif picked == 0:
            new_name = self._ask_text("Star List", "Name, up to 32 characters:", value=found.name)
            if not new_name:
                return
            description = self._ask_text(
                "Star List", "Description, or leave it empty:", value=found.description
            )
            work = lambda: update_list(  # noqa: E731
                api, found, name=new_name, description=description, private=found.private
            )
        else:
            private = picked == 1
            work = lambda: update_list(  # noqa: E731
                api, found, name=found.name, description=found.description, private=private
            )
        self._background("change the star list", work, self._reload_saying)
