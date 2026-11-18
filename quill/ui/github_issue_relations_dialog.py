"""Relationships: an issue's parent, sub-issues, and what blocks it.

Opened from the GitHub Workbench's Item menu on an issue (Relationships...).
One list, each row starting with what it is ("Blocked by: #12 Fix the parser
(open)"), so a screen reader hears the kind first. Add Sub-issue (Alt+S) and
Add Blocked By (Alt+B) take an issue as #12, owner/repo#12 or its address;
Remove (Alt+R) undoes the selected sub-issue or blocked-by link. The parent
and "blocking" rows are the other side of another issue's link, so they are
changed from that issue. After every change the list is read back from
GitHub, so it shows what GitHub holds. Enter opens the selected issue.
"""

from __future__ import annotations

import threading
import webbrowser
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from quill.core.github.issue_relations import GitHubIssueRelations, IssueRef, Relations

__all__ = ["IssueRelationsDialog", "removable"]


def removable(relations: Relations, index: int) -> tuple[str, IssueRef] | None:
    """``("sub", ref)`` or ``("blocked", ref)`` for row *index*, or None for a row
    this issue cannot change (its parent, or an issue it blocks)."""
    offset = 1 if relations.parent is not None else 0
    index -= offset
    if 0 <= index < len(relations.sub_issues):
        return "sub", relations.sub_issues[index]
    index -= len(relations.sub_issues)
    if 0 <= index < len(relations.blocked_by):
        return "blocked", relations.blocked_by[index]
    return None


class IssueRelationsDialog:
    """The relationships of one issue, with add and remove."""

    def __init__(
        self,
        parent: object,
        relations_api: GitHubIssueRelations,
        *,
        repo: str,
        number: int,
        relations: Relations,
        announce_cb: Callable[[str], None] | None = None,
        ask_text: Callable[[str, str], str | None] | None = None,
        confirm: Callable[[str, str], bool] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._api = relations_api
        self._repo = repo
        self._number = number
        self._relations = relations
        self._announce = announce_cb or (lambda _message: None)
        self._ask_text = ask_text or self._default_ask
        self._confirm = confirm or self._default_confirm
        self._busy = False
        self.dialog = wx.Dialog(
            parent,
            title=f"Relationships of #{number}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 480, 360))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(panel, label="Re&lationships:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("Relationships")
        self._list.SetHelpText(
            "This issue's parent, sub-issues, the issues blocking it and the issues it "
            "blocks, each row starting with which. Enter opens the selected issue."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_sub = wx.Button(panel, label="Add &Sub-issue...")
        self._add_sub.SetHelpText(
            "Makes another issue a sub-issue of this one. Type it as #12, owner/repo#12, or "
            "paste its address. An issue with a parent already is moved here, after you say so."
        )
        self._add_blocked = wx.Button(panel, label="Add &Blocked By...")
        self._add_blocked.SetHelpText(
            "Records that another issue must be finished before this one can be."
        )
        self._remove = wx.Button(panel, label="&Remove")
        self._remove.SetHelpText(
            "Removes the selected sub-issue or blocked-by link. The issues themselves stay. "
            "A parent or an issue this one blocks is changed from that other issue."
        )
        close = wx.Button(panel, wx.ID_CANCEL, "Close")
        close.SetHelpText("Closes this window. Every change has already been sent.")
        for button in (self._add_sub, self._add_blocked, self._remove):
            row.Add(button, 0, wx.RIGHT, 6)
        row.AddStretchSpacer()
        row.Add(close)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Relationships status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize(dip_size(self.dialog, 600, 440))
        self._add_sub.Bind(wx.EVT_BUTTON, lambda _e: self.add_sub_issue())
        self._add_blocked.Bind(wx.EVT_BUTTON, lambda _e: self.add_blocked_by())
        self._remove.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        apply_listbox_activation(self._list, self._open_selected)
        bind_close_button(self.dialog, close, modeless=False)
        self._fill()
        self._list.SetFocus()

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle(), announce=self._announce)
        finally:
            self.dialog.Destroy()

    # -- helpers ---------------------------------------------------------------------

    def _fill(self) -> None:
        rows = self._relations.lines(self._repo) or ["No relationships yet."]
        self._list.Set(rows)
        self._list.SetSelection(0)

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _default_ask(self, title: str, prompt: str) -> str | None:
        wx = self._wx
        box = wx.TextEntryDialog(self.dialog, prompt, title)
        try:
            if show_modal_dialog(box, title) != wx.ID_OK:
                return None
            return str(box.GetValue())
        finally:
            box.Destroy()

    def _default_confirm(self, title: str, message: str) -> bool:
        wx = self._wx
        box = wx.MessageDialog(
            self.dialog, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        try:
            return bool(show_modal_dialog(box, title) == wx.ID_YES)
        finally:
            box.Destroy()

    def _open_selected(self, _event: object) -> None:
        relations = self._relations
        refs = [
            *([relations.parent] if relations.parent else []),
            *relations.sub_issues,
            *relations.blocked_by,
            *relations.blocking,
        ]
        index = self._list.GetSelection()
        if 0 <= index < len(refs):
            ref = refs[index]
            url = f"https://github.com/{ref.repo}/issues/{ref.number}"
            self._announce("Opened on GitHub." if webbrowser.open(url) else "Could not open it.")

    def _run(self, doing: str, work: Callable[[], str]) -> None:
        """Do *work* off the UI thread, then read the relationships back and say its sentence."""
        if self._busy:
            self._say("Wait for the last change to finish.")
            return
        self._busy = True
        self._status.SetLabel(doing)

        def worker() -> None:
            result: Any
            try:
                said = work()
                result = (said, self._api.relations(self._repo, self._number))
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say any failure
                result = GitHubItemsError(f"That did not work: {exc}")
            self._wx.CallAfter(self._done, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub write.

    def _done(self, result: Any) -> None:
        if not dialog_alive(self.dialog):
            return
        self._busy = False
        if isinstance(result, _NeedsMove):
            self._offer_move(result.child)
            return
        if isinstance(result, GitHubItemsError):
            self._say(str(result.args[0]) if result.args else str(result))
            return
        said, relations = result
        self._relations = relations
        self._fill()
        self._say(said)

    # -- commands --------------------------------------------------------------------

    def add_sub_issue(self) -> None:
        text = self._ask_text("Add Sub-issue", "&Issue to add (#12, owner/repo#12 or address):")
        if not text or not text.strip():
            return

        def work() -> str:
            child = self._api.issue_ref(text, self._repo)
            if child.number == self._number and child.repo == self._repo:
                raise GitHubItemsError("An issue cannot be its own sub-issue.")
            try:
                self._api.add_sub_issue(self._repo, self._number, child)
            except GitHubItemsError as exc:
                if "parent" not in str(exc).casefold():
                    raise
                # It has a parent already: moving it is a second decision, asked on the UI thread.
                raise _NeedsMove(child) from exc
            return f"#{child.number} is now a sub-issue of #{self._number}."

        self._run("Adding the sub-issue...", work)

    def _offer_move(self, child: IssueRef) -> None:
        if not self._confirm(
            "Move Sub-issue",
            f"#{child.number} {child.title!r} is already a sub-issue of another issue. "
            f"Move it to #{self._number}? It leaves its present parent.",
        ):
            self._say(f"#{child.number} was left where it is.")
            return

        def work() -> str:
            self._api.add_sub_issue(self._repo, self._number, child, move=True)
            return f"#{child.number} moved here; it is now a sub-issue of #{self._number}."

        self._run("Moving the sub-issue...", work)

    def add_blocked_by(self) -> None:
        text = self._ask_text("Add Blocked By", "&Blocked by (#12, owner/repo#12 or address):")
        if not text or not text.strip():
            return

        def work() -> str:
            blocker = self._api.issue_ref(text, self._repo)
            if blocker.number == self._number and blocker.repo == self._repo:
                raise GitHubItemsError("An issue cannot block itself.")
            self._api.add_blocked_by(self._repo, self._number, blocker)
            return f"#{self._number} is now blocked by #{blocker.number}."

        self._run("Adding the link...", work)

    def remove_selected(self) -> None:
        found = removable(self._relations, self._list.GetSelection())
        if found is None:
            self._say(
                "Select a sub-issue or a blocked-by row. A parent, or an issue this one blocks, "
                "is changed from that other issue."
            )
            return
        kind, ref = found
        what = "sub-issue" if kind == "sub" else "blocked-by link"
        if not self._confirm(
            "Remove",
            f"Remove #{ref.number} {ref.title!r} as a {what} of #{self._number}? "
            "Both issues stay; only the link goes, and you can add it again.",
        ):
            return

        def work() -> str:
            if kind == "sub":
                self._api.remove_sub_issue(self._repo, self._number, ref)
                return f"#{ref.number} is no longer a sub-issue of #{self._number}."
            self._api.remove_blocked_by(self._repo, self._number, ref)
            return f"#{self._number} is no longer blocked by #{ref.number}."

        self._run("Removing...", work)


class _NeedsMove(GitHubItemsError):
    """Adding failed because the issue already has a parent (asked, then retried)."""

    code = "QUILL-GITHUB-RELATIONS-HAS-PARENT"

    def __init__(self, child: IssueRef) -> None:
        super().__init__(
            f"#{child.number} already has a parent. Add it again and choose to move it, "
            "or remove it from its parent first."
        )
        self.child = child
