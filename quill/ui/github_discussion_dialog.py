"""One GitHub discussion as a thread, and starting a discussion (QUILL and QUILL Lite).

The thread window lists the discussion, then each comment followed by its
replies; the detail box reads whichever is selected, with "Answered by X" and
any poll as text ("Option A: 12 votes, 40 percent"). Reply answers the
discussion or the selected comment; Mark as Answer and Unmark Answer follow the
permissions GitHub reports for each comment. Every write asks first or is the
reply you just wrote, and is reported only when GitHub confirms it.
"""

from __future__ import annotations

import threading
import webbrowser
from collections.abc import Callable
from typing import TYPE_CHECKING

from quill.core.github.discussion_actions import (
    DiscussionCategory,
    DiscussionComment,
    DiscussionThread,
)
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
    from quill.core.github.items_provider import GitHubItemsProvider

__all__ = ["GitHubDiscussionDialog", "NewDiscussionDialog", "ask_text"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


def ask_text(parent: object, message: str, title: str, announce: Callable[[str], None]) -> str:
    """A multi-line text prompt; ``""`` when cancelled."""
    import wx

    with wx.TextEntryDialog(
        parent, message, title, style=wx.OK | wx.CANCEL | wx.TE_MULTILINE
    ) as dlg:
        if show_modal_dialog(dlg, title, announce=announce) != wx.ID_OK:
            return ""
        return str(dlg.GetValue())


class GitHubDiscussionDialog:
    """Read a discussion thread; reply, and mark or unmark the answer."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        number: int,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._number = number
        self._announce = announce_cb or (lambda _message: None)
        self._thread: DiscussionThread | None = None
        self._entries: list[DiscussionComment] = []
        self._token = 0
        self._busy = False
        self.dialog = wx.Dialog(
            parent,
            title=f"Discussion #{number}: {repo}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 640, 480))
        self.dialog.SetSize(dip_size(self.dialog, 820, 620))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(panel, label="&Thread")
        list_label.SetHelpText("The discussion, then each comment followed by its replies.")
        root.Add(list_label, 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("Discussion thread")
        self._list.SetHelpText(
            "The first row is the discussion itself. Each comment says who wrote it, "
            "whether it is the answer, and how many replies it has."
        )
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        detail_label = wx.StaticText(panel, label="Te&xt")
        detail_label.SetHelpText("The selected row in full.")
        root.Add(detail_label, 0, wx.LEFT | wx.TOP, 8)
        self._detail = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._detail.SetName("Selected discussion text")
        self._detail.SetHelpText("Read-only. Polls read as one option to a line, with votes.")
        root.Add(self._detail, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="Loading the discussion...")
        self._status.SetName("Discussion status")
        self._status.SetHelpText("Says what is loading, what changed, or why it failed.")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._reply_btn = wx.Button(panel, label="&Reply...")
        self._reply_btn.SetName("Reply to the discussion or the selected comment")
        self._reply_btn.SetHelpText(
            "On the discussion row, adds a comment; on a comment or reply, replies under "
            "that comment."
        )
        self._answer_btn = wx.Button(panel, label="&Mark as Answer...")
        self._answer_btn.SetName("Mark or unmark the selected comment as the answer")
        self._answer_btn.SetHelpText(
            "Marks the selected comment as the discussion's answer, or unmarks it when it "
            "already is. Only in categories that take answers. QUILL asks first."
        )
        self._open_btn = wx.Button(panel, label="&Open on GitHub")
        self._open_btn.SetName("Open the selected row on GitHub")
        self._open_btn.SetHelpText("Opens the discussion or comment in your browser.")
        self._refresh_btn = wx.Button(panel, label="Re&fresh")
        self._refresh_btn.SetName("Load the discussion again")
        self._refresh_btn.SetHelpText("Asks GitHub for the thread again.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close the discussion")
        close_btn.SetHelpText("Close this window.")
        for button in (self._reply_btn, self._answer_btn, self._open_btn, self._refresh_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._list.Bind(wx.EVT_LISTBOX, lambda _event: self._on_select())
        apply_listbox_activation(self._list, lambda _event: self._detail.SetFocus())
        self._reply_btn.Bind(wx.EVT_BUTTON, lambda _event: self._reply())
        self._answer_btn.Bind(wx.EVT_BUTTON, lambda _event: self._toggle_answer())
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _event: self._open_selected())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _event: self._load())
        bind_close_button(self.dialog, close_btn, modeless=False)
        self._on_select()

    def show(self) -> None:
        wx = self._wx
        self._load()
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Discussion", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _load(self, then: str = "") -> None:
        self._token += 1
        token, repo, number = self._token, self._repo, self._number

        def worker() -> None:
            try:
                thread = self._provider.fetch_discussion_thread(repo, number)
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._loaded, token, None, _message(exc), then)
                return
            self._wx.CallAfter(self._loaded, token, thread, "", then)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: discussion read.

    def _loaded(self, token: int, thread: DiscussionThread | None, error: str, then: str) -> None:
        if token != self._token or not dialog_alive(self.dialog):
            return
        if thread is None:
            self._say(f"Could not load the discussion: {error}")
            return
        keep = self._list.GetSelection()
        self._thread = thread
        self._entries = thread.entries()
        self._list.Set(
            [f"Discussion: {thread.title}, {thread.answer_line}"]
            + [entry.label for entry in self._entries]
        )
        self._list.SetSelection(keep if 0 <= keep <= len(self._entries) else 0)
        self._on_select()
        count = len(self._entries)
        self._say(f"{then} {thread.answer_line} {count} comments and replies.".strip())

    def _selected_entry(self) -> DiscussionComment | None:
        index = self._list.GetSelection()
        return self._entries[index - 1] if 1 <= index <= len(self._entries) else None

    def _on_select(self) -> None:
        thread = self._thread
        entry = self._selected_entry()
        writable = self._provider.is_authenticated and thread is not None
        self._reply_btn.Enable(writable and not (thread is not None and thread.closed))
        can_answer = (
            entry is not None and not entry.is_reply and (entry.can_mark or entry.can_unmark)
        )
        self._answer_btn.Enable(writable and can_answer)
        self._answer_btn.SetLabel(
            "Un&mark Answer..." if entry is not None and entry.is_answer else "&Mark as Answer..."
        )
        if entry is not None:
            when = f" on {entry.created_at[:10]}" if entry.created_at else ""
            self._detail.SetValue(
                f"{'Reply' if entry.is_reply else 'Comment'} by {entry.author or 'unknown'}{when}"
                + (". This is the answer." if entry.is_answer else ".")
                + f"\n\n{entry.body}\n\n{entry.url}"
            )
        else:
            self._detail.SetValue(thread.text() + f"\n\n{thread.url}" if thread else "")
        self._open_btn.Enable(bool((entry and entry.url) or (thread and thread.url)))

    def _open_selected(self) -> None:
        entry = self._selected_entry()
        url = entry.url if entry else (self._thread.url if self._thread else "")
        if url:
            self._announce("Opened on GitHub." if webbrowser.open(url) else "Could not open it.")

    def _write(self, work: Callable[[], object], success: str) -> None:
        if self._busy:
            self._announce("Wait for the current change to finish.")
            return
        self._busy = True
        self._status.SetLabel("Sending to GitHub...")

        def worker() -> None:
            try:
                work()
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._written, _message(exc), "")
                return
            self._wx.CallAfter(self._written, "", success)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: discussion write.

    def _written(self, error: str, success: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._busy = False
        if error:
            self._say(error)
            return
        self._load(then=success)

    def _reply(self) -> None:
        thread = self._thread
        if thread is None:
            return
        entry = self._selected_entry()
        parent = (entry.parent_id or entry.id) if entry is not None else ""
        target = f"{entry.author}'s comment" if entry is not None else "the discussion"
        body = ask_text(self.dialog, f"Your reply to {target}:", "Reply", self._announce)
        if not body.strip():
            self._announce("Nothing was sent.")
            return
        discussion_id = thread.id
        self._write(
            lambda: self._provider.reply_to_discussion(discussion_id, body, reply_to=parent),
            f"Posted your reply to {target}.",
        )

    def _toggle_answer(self) -> None:
        entry = self._selected_entry()
        if entry is None or entry.is_reply:
            self._announce("Choose a comment first; a reply cannot be the answer.")
            return
        wx = self._wx
        unmark = entry.is_answer
        title = "Unmark Answer" if unmark else "Mark as Answer"
        question = (
            f"Stop treating {entry.author}'s comment as the answer?"
            if unmark
            else f"Mark {entry.author}'s comment as the answer to this discussion?"
        )
        with wx.MessageDialog(self.dialog, question, title, wx.YES_NO | wx.NO_DEFAULT) as confirm:
            if show_modal_dialog(confirm, title, announce=self._announce) != wx.ID_YES:
                self._announce("Cancelled; nothing was sent to GitHub.")
                return
        comment_id = entry.id
        self._write(
            lambda: self._provider.set_discussion_answer(comment_id, answer=not unmark),
            "Unmarked the answer." if unmark else f"Marked {entry.author}'s comment as the answer.",
        )


class NewDiscussionDialog:
    """Category, title and body for a new discussion."""

    def __init__(
        self,
        parent: object,
        categories: list[DiscussionCategory],
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._categories = categories
        self._announce = announce_cb or (lambda _message: None)
        self.values: tuple[DiscussionCategory, str, str] | None = None
        self.dialog = wx.Dialog(
            parent, title="New Discussion", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 520, 420))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        category_label = wx.StaticText(panel, label="&Category:")
        category_label.SetHelpText("Where the discussion goes, as the repository sets them up.")
        root.Add(category_label, 0, wx.LEFT | wx.TOP, 8)
        self._category = wx.Choice(
            panel,
            choices=[
                category.name + (", takes answers" if category.answerable else "")
                for category in categories
            ],
        )
        self._category.SetName("Discussion category")
        self._category.SetHelpText(
            "A category that takes answers lets someone mark a comment as the answer."
        )
        self._category.SetSelection(0)
        root.Add(self._category, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        title_label = wx.StaticText(panel, label="&Title:")
        title_label.SetHelpText("The discussion's title. Required.")
        root.Add(title_label, 0, wx.LEFT | wx.TOP, 8)
        self._title = wx.TextCtrl(panel)
        self._title.SetName("Discussion title")
        self._title.SetHelpText("Required.")
        root.Add(self._title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        body_label = wx.StaticText(panel, label="&Body:")
        body_label.SetHelpText("What you want to discuss. Required. Markdown works.")
        root.Add(body_label, 0, wx.LEFT | wx.TOP, 8)
        self._body = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        self._body.SetName("Discussion body")
        self._body.SetHelpText("Required. Markdown works.")
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._error = wx.StaticText(panel, label="")
        self._error.SetName("New discussion problem")
        self._error.SetHelpText("Says what to fill in before the discussion can start.")
        root.Add(self._error, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(panel, wx.ID_OK, "Start Discussion")
        ok.SetHelpText("Start the discussion on GitHub.")
        cancel = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without starting anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        bind_close_button(self.dialog, cancel, modeless=False)

    def _on_ok(self, _event: object) -> None:
        title, body = self._title.GetValue().strip(), self._body.GetValue()
        index = self._category.GetSelection()
        problem = (
            "Give the discussion a title."
            if not title
            else "Write the body of the discussion."
            if not body.strip()
            else ""
        )
        if problem:
            self._error.SetLabel(problem)
            self._announce(problem)
            (self._title if not title else self._body).SetFocus()
            return
        self.values = (self._categories[max(0, index)], title, body)
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[DiscussionCategory, str, str] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        try:
            show_modal_dialog(self.dialog, "New Discussion", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self.values
