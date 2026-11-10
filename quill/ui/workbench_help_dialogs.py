"""The Workbench's help windows: What Can I Do Here?, What Is This?, Search Help, Keys.

GitHub PRD Part D (D2, D5, D6, D7), provider-neutral, so the WordPress
Workbench shows the same windows. Each is a small modal dialog parented to the
Workbench, so it blocks only the Workbench, shown through the dialog contract:

- :class:`ActionListDialog` lists rows a person can run (What Can I Do Here?,
  Search Help's results). Enter or Run does the selected row; a greyed row
  says why and does nothing.
- :class:`HelpTextDialog` is one read-only, multi-line text box, focused on
  open so a screen reader reads it in one pass (What Is This?, Workbench Keys).
- :class:`SearchHelpDialog` is a search box over a results list; typing
  narrows the list, Enter in the box moves to it.

Opening says nothing (GATE-13): the reader says the title and the focused
control. OK and Close carry no access key (GATE-14's first fix).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = ["ActionChoice", "ActionListDialog", "HelpTextDialog", "SearchHelpDialog"]


@dataclass(frozen=True)
class ActionChoice:
    """One row a person can run: how it reads, whether it can run, and the run."""

    text: str
    enabled: bool
    run: Callable[[], None] | None = None
    help: str = ""


class ActionListDialog:
    """A list of actions; Enter runs the selected one after the dialog closes."""

    def __init__(self, parent: Any, title: str, prompt: str, rows: Sequence[ActionChoice]) -> None:
        import wx

        self._wx = wx
        self.rows = list(rows)
        self.title = title
        self.chosen: ActionChoice | None = None
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 520, 420))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label=prompt), 0, wx.ALL, 8)
        self.list = wx.ListBox(self.dialog, choices=[row.text for row in self.rows])
        self.list.SetName(title)
        self.list.SetHelpText(
            "Arrow to an action and press Enter to do it. A greyed one says why it "
            "cannot be done here."
        )
        if self.rows:
            self.list.SetSelection(0)
        apply_listbox_activation(self.list, lambda _e: self._run())
        root.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.detail = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self.detail.SetName("About this action")
        self.detail.SetHelpText("What the selected action does, and why it is greyed if it is.")
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._show_detail())
        root.Add(self.detail, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        run = wx.Button(self.dialog, wx.ID_OK, "&Run")
        run.SetHelpText("Do the selected action. Enter does the same.")
        run.SetDefault()
        run.Bind(wx.EVT_BUTTON, lambda _e: self._run())
        close = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this list without doing anything. Escape does the same.")
        bind_close_button(self.dialog, close, modeless=False)
        buttons.AddStretchSpacer()
        buttons.Add(run, 0, wx.RIGHT, 8)
        buttons.Add(close)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self._show_detail()

    def selected(self) -> ActionChoice | None:
        index = self.list.GetSelection()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def _show_detail(self) -> None:
        row = self.selected()
        self.detail.ChangeValue(row.help if row is not None else "")

    def _run(self) -> None:
        row = self.selected()
        if row is None or not row.enabled or row.run is None:
            self._wx.Bell()
            return
        self.chosen = row
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> None:
        """Show it; run the chosen action once the dialog is gone."""
        try:
            show_modal_dialog(self.dialog, self.title)
        finally:
            self.dialog.Destroy()
        if self.chosen is not None and self.chosen.run is not None:
            self.chosen.run()


class HelpTextDialog:
    """One read-only text box and a Close button."""

    def __init__(self, parent: Any, title: str, text: str) -> None:
        import wx

        self.title = title
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 560, 420))
        root = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.TextCtrl(
            self.dialog, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self.text.SetName(title)
        self.text.SetHelpText("Read with the arrow keys. Escape closes it.")
        root.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        close = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Escape does the same.")
        bind_close_button(self.dialog, close, modeless=False)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        buttons.Add(close)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self.text.SetFocus()

    def show(self) -> None:
        try:
            show_modal_dialog(self.dialog, self.title)
        finally:
            self.dialog.Destroy()


class SearchHelpDialog:
    """A search box over a results list; Enter on a result does what it says."""

    def __init__(
        self,
        parent: Any,
        search: Callable[[str], Sequence[ActionChoice]],
        title: str = "Search Help",
    ) -> None:
        import wx

        self._wx = wx
        self._search = search
        self.title = title
        self.rows: list[ActionChoice] = []
        self.chosen: ActionChoice | None = None
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 560, 460))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label="&Look for:"), 0, wx.LEFT | wx.TOP, 8)
        self.box = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self.box.SetName("Look for")
        self.box.SetHelpText(
            "Type a few words, such as who can merge or re-run. The results below "
            "narrow as you type; Enter moves to them."
        )
        self.box.Bind(wx.EVT_TEXT, lambda _e: self.refresh())
        self.box.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.results.SetFocus())
        root.Add(self.box, 0, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(self.dialog, label="R&esults:"), 0, wx.LEFT, 8)
        self.results = wx.ListBox(self.dialog)
        self.results.SetName("Results")
        self.results.SetHelpText(
            "Each result says what it is: a place, a command with its key, a GitHub "
            "word or a task. Enter goes there, runs it or reads it."
        )
        apply_listbox_activation(self.results, lambda _e: self._run())
        root.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        go = wx.Button(self.dialog, wx.ID_OK, "&Go")
        go.SetHelpText("Do the selected result. Enter does the same.")
        go.Bind(wx.EVT_BUTTON, lambda _e: self._run())
        close = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close Search Help. Escape does the same.")
        bind_close_button(self.dialog, close, modeless=False)
        buttons.AddStretchSpacer()
        buttons.Add(go, 0, wx.RIGHT, 8)
        buttons.Add(close)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

    def refresh(self) -> None:
        self.rows = list(self._search(self.box.GetValue()))
        self.results.Set([row.text for row in self.rows])
        if self.rows:
            self.results.SetSelection(0)

    def _run(self) -> None:
        index = self.results.GetSelection()
        if not 0 <= index < len(self.rows):
            self._wx.Bell()
            return
        self.chosen = self.rows[index]
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> None:
        try:
            show_modal_dialog(self.dialog, self.title)
        finally:
            self.dialog.Destroy()
        if self.chosen is not None and self.chosen.run is not None:
            self.chosen.run()
