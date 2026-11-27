"""Find a Person or Organization: type a name, hear the matches, act on one.

A search box, the matching accounts as one list, and the buttons that act on
the selected account. Typing searches after a short pause (a type-ahead, not a
button), and the list is replaced when the answer arrives; an answer to an
older search is dropped, so the list never jumps back. Nothing is spoken as
you type or move (GATE-13); each result of an action is said once, as a
plain sentence, by the host's announcer.

Three meanings are kept apart in the labels and the help: **Track** and
**Favorite** are shortcuts on this computer only; **Follow** is a public
action on GitHub, for a person (an organization is opened on GitHub instead);
the repositories window's **Star** is a public action too, and **GitHub List**
is GitHub's own collection. The logic is :class:`quill.core.github.account_desk.AccountDesk`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.account_desk import AccountDesk
from quill.core.github.account_discovery import KIND_ORGANIZATION, AccountHit, RepositoryHit
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

__all__ = ["FindAccountDialog", "show_repositories"]

#: The pause after the last key before a search is sent, in milliseconds.
TYPE_AHEAD_MS = 400

Background = Callable[[str, Callable[[], Any], Callable[[Any], None]], None]


def show_repositories(
    parent: Any,
    desk: AccountDesk,
    hit: AccountHit,
    repos: list[RepositoryHit],
    *,
    say: Callable[[str], None],
    background: Background,
    open_url: Callable[[str], None],
    add_to_list: Callable[[str], None],
) -> None:
    """An account's repositories, with what can be done to each (Enter opens it on GitHub)."""
    from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

    box: list[WorkbenchListDialog] = []

    def pick() -> RepositoryHit | None:
        index = box[0].selected()
        return repos[index] if 0 <= index < len(repos) else None

    def open_it(_i: int) -> None:
        if (repo := pick()) is not None:
            open_url(repo.page)

    def star(_i: int) -> None:
        if (repo := pick()) is not None:
            background(
                "star or unstar a repository",
                lambda: desk.toggle_star(repo.full_name),
                say,
            )

    def favorite(_i: int) -> None:
        if (repo := pick()) is not None:
            say(desk.toggle_favorite_repository(repo.full_name))

    def to_list(_i: int) -> None:
        if (repo := pick()) is not None:
            add_to_list(repo.full_name)

    def detail(index: int) -> str:
        repo = repos[index] if 0 <= index < len(repos) else None
        if repo is None:
            return ""
        local = "yes" if desk.store.is_favorite_repository(repo.full_name) else "no"
        return (
            f"{repo.label}\n{repo.page}\n"
            f"Favorite on this computer: {local}. A favorite is a local shortcut only."
        )

    rows = [repo.label for repo in repos]
    dialog = WorkbenchListDialog(
        parent,
        f"Repositories of {hit.login}",
        rows,
        list_name=f"Repositories of {hit.login}",
        list_help="Public repositories, newest push first. Enter opens one on GitHub.",
        detail=detail,
        actions=[
            ("&Open on GitHub", "Open the repository in your browser.", open_it),
            (
                "&Star or Unstar",
                "Star it on GitHub, or take your star away. A star is public: it shows on your "
                "GitHub profile.",
                star,
            ),
            (
                "&Favorite or Unfavorite",
                "Keep it as a shortcut on this computer. Nothing is sent to GitHub.",
                favorite,
            ),
            (
                "Add to GitHub &List...",
                "Put it on one of your GitHub Lists, GitHub's own collections of starred "
                "repositories.",
                to_list,
            ),
        ],
        copy_text=lambda text: None,
    )
    box.append(dialog)
    dialog.show()


class FindAccountDialog:
    def __init__(
        self,
        parent: Any,
        desk: AccountDesk,
        *,
        say: Callable[[str], None],
        background: Background,
        open_url: Callable[[str], None],
        add_to_list: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self.desk = desk
        self._say = say
        self._background = background
        self._open_url = open_url
        self._add_to_list = add_to_list
        self._parent = parent
        self.hits: list[AccountHit] = []
        self._ticket = 0
        self.dialog = wx.Dialog(
            parent,
            title="Find a Person or Organization",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(dip_size(self.dialog, 720, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.dialog, label="&Search by username or name:")
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.query = wx.TextCtrl(self.dialog)
        set_spoken_name(self.query, "Search by username or name")
        self.query.SetHelpText(
            "Type at least two letters of a GitHub username or name. Matching people and "
            "organizations appear in the list below after a short pause; Down Arrow moves there."
        )
        root.Add(self.query, 0, wx.EXPAND | wx.ALL, 8)
        results = wx.StaticText(self.dialog, label="&Matches:")
        root.Add(results, 0, wx.LEFT | wx.RIGHT, 8)
        self.list = wx.ListBox(self.dialog)
        set_spoken_name(self.list, "Matches")
        self.list.SetHelpText(
            "Each row says whether it is a person or an organization, then the username, the "
            "name, the public repositories and a description. Enter opens the account's "
            "repositories."
        )
        root.Add(self.list, 2, wx.EXPAND | wx.ALL, 8)
        self.details = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_spoken_name(self.details, "Details")
        self.details.SetHelpText(
            "The selected account in full, and what this computer keeps for it."
        )
        root.Add(self.details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        specs: list[tuple[str, str, Callable[[], None]]] = [
            (
                "&Repositories...",
                "List its public repositories, to star, favorite or add to a GitHub List.",
                self.open_repositories,
            ),
            (
                "&Track or Untrack",
                "Keep the account in People > Tracked Accounts, or remove it. A list on this "
                "computer only; GitHub is not told.",
                self.toggle_track,
            ),
            (
                "&Favorite or Unfavorite",
                "Mark the account as a favorite on this computer. Nothing is sent to GitHub.",
                self.toggle_favorite,
            ),
            (
                "Fo&llow or Unfollow",
                "Follow a person on GitHub, or stop. This is public. For an organization, opens "
                "its page on GitHub, where you can follow it.",
                self.toggle_follow,
            ),
            ("Open on &GitHub", "Open the account's page in your browser.", self.open_page),
        ]
        for text, what, action in specs:
            button = wx.Button(self.dialog, label=text)
            button.SetHelpText(what)
            button.Bind(wx.EVT_BUTTON, lambda _e, a=action: a())
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        close = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Escape does the same.")
        bind_close_button(self.dialog, close, modeless=False)
        buttons.Add(close)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog)
        self.dialog.SetEscapeId(wx.ID_CANCEL)
        self._timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, lambda _e: self.search_now(), self._timer)
        self.query.Bind(wx.EVT_TEXT, lambda _e: self._timer.StartOnce(TYPE_AHEAD_MS))
        self.query.Bind(wx.EVT_KEY_DOWN, self._query_key)
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._show_detail())
        apply_listbox_activation(self.list, lambda _e: self.open_repositories())

    # -- searching ----------------------------------------------------------------

    def _query_key(self, event: Any) -> None:
        if event.GetKeyCode() == self._wx.WXK_DOWN and self.hits:
            self.list.SetFocus()
            return
        event.Skip()

    def search_now(self) -> None:
        text = str(self.query.GetValue()).strip()
        self._ticket += 1
        ticket = self._ticket
        if len(text) < 2:
            self._show_hits([], [])
            return
        self._background(
            "search for people and organizations",
            lambda: self.desk.search(text),
            lambda found: self._arrived(ticket, found),
        )

    def _arrived(self, ticket: int, found: Any) -> None:
        if ticket != self._ticket:
            return  # a newer search is on its way; this answer is out of date
        hits, labels = found
        self._show_hits(hits, labels)
        count = len(hits)
        self._say(
            "No people or organizations match."
            if not count
            else f"{count} {'match' if count == 1 else 'matches'}."
        )

    def _show_hits(self, hits: list[AccountHit], labels: list[str]) -> None:
        self.hits = hits
        self.list.Set(labels)
        if hits:
            self.list.SetSelection(0)
        self._show_detail()

    def selected(self) -> AccountHit | None:
        index = int(self.list.GetSelection())
        return self.hits[index] if 0 <= index < len(self.hits) else None

    def _show_detail(self) -> None:
        hit = self.selected()
        if hit is None:
            self.details.ChangeValue("")
            return
        store = self.desk.store
        self.details.ChangeValue(
            f"{hit.detail()}\n"
            f"Tracked on this computer: {'yes' if store.is_tracked(hit.login) else 'no'}. "
            f"Favorite on this computer: {'yes' if store.is_favorite(hit.login) else 'no'}."
        )

    # -- actions ----------------------------------------------------------------------

    def _need(self) -> AccountHit | None:
        hit = self.selected()
        if hit is None:
            self._say("Choose an account first.")
        return hit

    def open_repositories(self) -> None:
        if (hit := self._need()) is None:
            return
        self._background(
            "read the account's repositories",
            lambda: self.desk.repositories(hit),
            lambda repos: self._show_repos(hit, list(repos)),
        )

    def _show_repos(self, hit: AccountHit, repos: list[RepositoryHit]) -> None:
        if not repos:
            self._say(f"{hit.login} has no public repositories.")
            return
        show_repositories(
            self.dialog,
            self.desk,
            hit,
            repos,
            say=self._say,
            background=self._background,
            open_url=self._open_url,
            add_to_list=self._add_to_list,
        )

    def toggle_track(self) -> None:
        if (hit := self._need()) is not None:
            self._say(self.desk.toggle_track(hit))
            self._show_detail()

    def toggle_favorite(self) -> None:
        if (hit := self._need()) is not None:
            self._say(self.desk.toggle_favorite(hit))
            self._show_detail()

    def toggle_follow(self) -> None:
        if (hit := self._need()) is None:
            return
        if hit.kind == KIND_ORGANIZATION:
            self._say(self.desk.toggle_follow(hit))
            self._open_url(hit.page)
            return
        self._background(
            "follow or unfollow a person", lambda: self.desk.toggle_follow(hit), self._say
        )

    def open_page(self) -> None:
        if (hit := self._need()) is not None:
            self._open_url(hit.page)

    def show(self, start: str = "") -> None:
        if start:
            self.query.SetValue(start)
        self.query.SetFocus()
        try:
            show_modal_dialog(self.dialog, "Find a Person or Organization")
        finally:
            self._timer.Stop()
            self.dialog.Destroy()
