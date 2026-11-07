"""Milestones for one repository (QUILL and QUILL Lite).

Each milestone reads as one line: "Release 2.0: 62 percent done, 5 open, 8
closed, due 12 December". New, Edit, and Close or Reopen change it on GitHub;
closing asks first, and every change is reported only once GitHub's reply shows
it. A newer load wins over a slower earlier one through the load token.
"""

from __future__ import annotations

import threading
import webbrowser
from collections.abc import Callable
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.milestones import GitHubMilestone, due_date_to_iso
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

__all__ = ["GitHubMilestonesDialog", "MilestoneFormDialog"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


_STATES = (("open", "Open"), ("closed", "Closed"), ("all", "All"))


class MilestoneFormDialog:
    """Title, description and due date for a new or edited milestone."""

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        milestone: GitHubMilestone | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._title = title
        self._announce = announce_cb or (lambda _message: None)
        self.dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        self.dialog.SetMinSize(dip_size(self.dialog, 460, 320))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        name_label = wx.StaticText(panel, label="&Title:")
        name_label.SetHelpText("The milestone's name, as GitHub shows it.")
        root.Add(name_label, 0, wx.LEFT | wx.TOP, 8)
        self._name = wx.TextCtrl(panel, value=milestone.title if milestone else "")
        self._name.SetName("Milestone title")
        self._name.SetHelpText("Required. For example Release 2.0.")
        root.Add(self._name, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        desc_label = wx.StaticText(panel, label="&Description:")
        desc_label.SetHelpText("What the milestone is for. Optional.")
        root.Add(desc_label, 0, wx.LEFT | wx.TOP, 8)
        self._description = wx.TextCtrl(
            panel, value=milestone.description if milestone else "", style=wx.TE_MULTILINE
        )
        self._description.SetName("Milestone description")
        self._description.SetHelpText("Optional. Plain text or Markdown.")
        root.Add(self._description, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        due_label = wx.StaticText(panel, label="D&ue date (year-month-day):")
        due_label.SetHelpText("When the milestone is due. Leave it empty for no due date.")
        root.Add(due_label, 0, wx.LEFT | wx.TOP, 8)
        self._due = wx.TextCtrl(panel, value=(milestone.due_on[:10] if milestone else ""))
        self._due.SetName("Milestone due date, year-month-day, empty for none")
        self._due.SetHelpText("Type a date like 2026-12-12, or leave it empty for no due date.")
        root.Add(self._due, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._error = wx.StaticText(panel, label="")
        self._error.SetName("Milestone form problem")
        self._error.SetHelpText("Says what to fix before the milestone can be saved.")
        root.Add(self._error, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(panel, wx.ID_OK, "OK")
        ok.SetHelpText("Save the milestone on GitHub.")
        cancel = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        bind_close_button(self.dialog, cancel, modeless=False)
        self.values: tuple[str, str, str | None] | None = None

    def _on_ok(self, _event: object) -> None:
        title = self._name.GetValue().strip()
        try:
            if not title:
                raise GitHubItemsError("A milestone needs a title.")
            due = due_date_to_iso(self._due.GetValue())
        except GitHubItemsError as exc:
            self._error.SetLabel(_message(exc))
            self._announce(_message(exc))
            (self._due if title else self._name).SetFocus()
            return
        self.values = (title, self._description.GetValue(), due)
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[str, str, str | None] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        try:
            show_modal_dialog(self.dialog, self._title, announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self.values


class GitHubMilestonesDialog:
    """List, create, edit, close and reopen a repository's milestones."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._announce = announce_cb or (lambda _message: None)
        self._rows: list[GitHubMilestone] = []
        self._token = 0
        self._busy = False
        self.dialog = wx.Dialog(
            parent, title=f"Milestones: {repo}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 600, 440))
        self.dialog.SetSize(dip_size(self.dialog, 760, 560))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        state_row = wx.BoxSizer(wx.HORIZONTAL)
        state_label = wx.StaticText(panel, label="&Show:")
        state_label.SetHelpText("Which milestones to list.")
        state_row.Add(state_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._state = wx.Choice(panel, choices=[words for _key, words in _STATES])
        self._state.SetName("Show open, closed or all milestones")
        self._state.SetHelpText("Open milestones, closed ones, or all of them.")
        self._state.SetSelection(0)
        state_row.Add(self._state, 0)
        root.Add(state_row, 0, wx.ALL, 8)
        list_label = wx.StaticText(panel, label="&Milestones")
        list_label.SetHelpText("Each milestone with how far along it is and when it is due.")
        root.Add(list_label, 0, wx.LEFT, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("Milestones")
        self._list.SetHelpText(
            "Each line says the percent done, how many issues are open and closed, and the "
            "due date. Enter opens the milestone on GitHub."
        )
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        detail_label = wx.StaticText(panel, label="&Details")
        detail_label.SetHelpText("The selected milestone's description and address.")
        root.Add(detail_label, 0, wx.LEFT | wx.TOP, 8)
        self._detail = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._detail.SetName("Selected milestone details")
        self._detail.SetHelpText("Read-only.")
        root.Add(self._detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Milestones status")
        self._status.SetHelpText("Says what is loading, what changed, or why it failed.")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._new_btn = wx.Button(panel, label="&New...")
        self._new_btn.SetName("Create a milestone")
        self._new_btn.SetHelpText("Create a milestone with a title, description and due date.")
        self._edit_btn = wx.Button(panel, label="&Edit...")
        self._edit_btn.SetName("Edit the selected milestone")
        self._edit_btn.SetHelpText("Change the selected milestone's title, description or date.")
        self._close_ms_btn = wx.Button(panel, label="Close Mi&lestone...")
        self._close_ms_btn.SetName("Close or reopen the selected milestone")
        self._close_ms_btn.SetHelpText(
            "Closes the selected open milestone, or reopens a closed one. QUILL asks first."
        )
        self._open_btn = wx.Button(panel, label="&Open on GitHub")
        self._open_btn.SetName("Open the selected milestone in the browser")
        self._open_btn.SetHelpText("Opens the selected milestone's page on GitHub.")
        self._refresh_btn = wx.Button(panel, label="&Refresh")
        self._refresh_btn.SetName("Load the milestones again")
        self._refresh_btn.SetHelpText("Asks GitHub for the milestones again.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close milestones")
        close_btn.SetHelpText("Close this window.")
        for button in (
            self._new_btn,
            self._edit_btn,
            self._close_ms_btn,
            self._open_btn,
            self._refresh_btn,
        ):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._state.Bind(wx.EVT_CHOICE, lambda _event: self._load())
        self._list.Bind(wx.EVT_LISTBOX, lambda _event: self._on_select())
        apply_listbox_activation(self._list, lambda _event: self._open_selected())
        self._new_btn.Bind(wx.EVT_BUTTON, lambda _event: self._create())
        self._edit_btn.Bind(wx.EVT_BUTTON, lambda _event: self._edit())
        self._close_ms_btn.Bind(wx.EVT_BUTTON, lambda _event: self._toggle_state())
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _event: self._open_selected())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _event: self._load())
        bind_close_button(self.dialog, close_btn, modeless=False)
        writable = provider.is_authenticated
        self._new_btn.Enable(writable)
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
            show_modal_dialog(self.dialog, "Milestones", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _load(self, *, keep: int = 0, then: str = "") -> None:
        self._token += 1
        token, repo = self._token, self._repo
        state = _STATES[max(0, self._state.GetSelection())][0]
        self._status.SetLabel("Loading milestones...")

        def worker() -> None:
            try:
                rows = self._provider.fetch_milestones(repo, state=state)
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._loaded, token, [], _message(exc), keep, then)
                return
            self._wx.CallAfter(self._loaded, token, rows, "", keep, then)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: milestone read.

    def _loaded(
        self, token: int, rows: list[GitHubMilestone], error: str, keep: int, then: str
    ) -> None:
        if token != self._token or not dialog_alive(self.dialog):
            return
        if error:
            self._say(f"Could not load milestones: {error}")
            return
        self._rows = rows
        self._list.Set([row.label() for row in rows])
        index = next((i for i, row in enumerate(rows) if row.number == keep), 0)
        if rows:
            self._list.SetSelection(index)
        self._on_select()
        count = f"{len(rows)} milestone" + ("" if len(rows) == 1 else "s") + "."
        self._say(f"{then} {count}".strip())

    def _selected(self) -> GitHubMilestone | None:
        index = self._list.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _on_select(self) -> None:
        row = self._selected()
        writable = self._provider.is_authenticated and row is not None
        self._edit_btn.Enable(writable)
        self._close_ms_btn.Enable(writable)
        self._open_btn.Enable(bool(row and row.url))
        if row is not None:
            self._close_ms_btn.SetLabel(
                "Reopen Mi&lestone..." if row.state == "closed" else "Close Mi&lestone..."
            )
        self._detail.SetValue(
            ""
            if row is None
            else f"{row.label()}\n\n{row.description or 'No description.'}\n\n{row.url}"
        )

    def _open_selected(self) -> None:
        row = self._selected()
        if row and row.url:
            self._announce(
                "Opened on GitHub." if webbrowser.open(row.url) else "Could not open it."
            )

    def _write(
        self, work: Callable[[], GitHubMilestone], success: Callable[[GitHubMilestone], str]
    ) -> None:
        if self._busy:
            self._announce("Wait for the current change to finish.")
            return
        self._busy = True
        self._status.SetLabel("Sending the change to GitHub...")

        def worker() -> None:
            try:
                milestone = work()
            except GitHubItemsError as exc:
                # The message already carries github_exception_hint's advice
                # (rest_failure_message), so it says what to do next.
                self._wx.CallAfter(self._written, None, _message(exc), success)
                return
            self._wx.CallAfter(self._written, milestone, "", success)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: confirmed write.

    def _written(
        self,
        milestone: GitHubMilestone | None,
        error: str,
        success: Callable[[GitHubMilestone], str],
    ) -> None:
        if not dialog_alive(self.dialog):
            return
        self._busy = False
        if milestone is None:
            self._say(error)
            return
        self._load(keep=milestone.number, then=success(milestone))

    def _create(self) -> None:
        values = MilestoneFormDialog(
            self.dialog, title="New Milestone", announce_cb=self._announce
        ).show()
        if values is None:
            return
        title, description, due = values
        repo = self._repo
        self._write(
            lambda: self._provider.create_milestone(
                repo, title, description=description, due_on=due
            ),
            lambda made: f"Created milestone {made.title}.",
        )

    def _edit(self) -> None:
        row = self._selected()
        if row is None:
            return
        values = MilestoneFormDialog(
            self.dialog, title="Edit Milestone", milestone=row, announce_cb=self._announce
        ).show()
        if values is None:
            return
        title, description, due = values
        repo, number = self._repo, row.number
        self._write(
            lambda: self._provider.update_milestone(
                repo,
                number,
                title=title,
                description=description,
                due_on=due,
                clear_due=due is None,
            ),
            lambda saved: f"Saved milestone {saved.title}.",
        )

    def _toggle_state(self) -> None:
        row = self._selected()
        if row is None:
            return
        wx = self._wx
        closing = row.state != "closed"
        verb = "Close" if closing else "Reopen"
        question = f"{verb} milestone {row.title} in {self._repo}?" + (
            f" It still has {row.open_issues} open issues; they keep the milestone."
            if closing and row.open_issues
            else ""
        )
        with wx.MessageDialog(
            self.dialog, question, f"{verb} Milestone", wx.YES_NO | wx.NO_DEFAULT
        ) as confirm:
            if (
                show_modal_dialog(confirm, f"{verb} Milestone", announce=self._announce)
                != wx.ID_YES
            ):
                self._announce("Cancelled; nothing was sent to GitHub.")
                return
        repo, number = self._repo, row.number
        self._write(
            lambda: self._provider.update_milestone(
                repo, number, state="closed" if closing else "open"
            ),
            lambda saved: f"{'Closed' if closing else 'Reopened'} milestone {saved.title}.",
        )
