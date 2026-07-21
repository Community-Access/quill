"""Command center (PRD 10.2, 3.2).

A single searchable list of every command. Keyboard-first: type to filter,
Up/Down to move, Enter to run, Escape to close. The palette shows each
command's current shortcut, includes synonyms in the match, and explains why an
unavailable command cannot run rather than hiding it silently (PRD 10.2,
"explain unavailable actions").
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import wx


@dataclass
class Command:
    command_id: str
    name: str
    handler: Callable[[], None]
    synonyms: list[str] = field(default_factory=list)
    hint: str = ""
    is_available: Callable[[], bool] = lambda: True
    unavailable_reason: str = ""
    shortcut: str = ""

    def matches(self, needle: str) -> bool:
        needle = needle.lower().strip()
        if not needle:
            return True
        hay = " ".join([self.name, self.command_id, *self.synonyms, self.hint]).lower()
        return all(part in hay for part in needle.split())

    def display(self) -> str:
        base = f"{self.name}  ({self.shortcut})" if self.shortcut else self.name
        if not self.is_available():
            base += "  -- unavailable"
        return base


class CommandPalette(wx.Dialog):
    """Modal palette over a list of Commands (PRD 10.2)."""

    def __init__(self, parent, commands: list[Command]):
        super().__init__(parent, title="Command Center",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._commands = commands
        self._chosen: Command | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        prompt = wx.StaticText(self, label="Type to filter commands:")
        sizer.Add(prompt, 0, wx.ALL, 8)
        self.filter = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.filter.SetName("Filter commands")
        sizer.Add(self.filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.list = wx.ListBox(self, style=wx.LB_SINGLE)
        self.list.SetName("Commands")
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.reason = wx.StaticText(self, label="")
        self.reason.SetName("Command status")
        sizer.Add(self.reason, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(sizer)
        self.SetSize((480, 420))
        self._populate("")
        self.filter.SetFocus()

        self.filter.Bind(wx.EVT_TEXT, self._on_text)
        self.filter.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._activate())
        self.list.Bind(wx.EVT_LISTBOX, self._on_select)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._activate())
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)

    def _populate(self, text: str) -> None:
        self.list.Clear()
        for cmd in self._commands:
            if cmd.matches(text):
                self.list.Append(cmd.display(), cmd)
        if self.list.GetCount():
            self.list.SetSelection(0)
            self._on_select(None)

    def _on_text(self, _e) -> None:
        self._populate(self.filter.GetValue())

    def _on_select(self, _e) -> None:
        cmd = self._current()
        if cmd and not cmd.is_available():
            self.reason.SetLabel(
                cmd.unavailable_reason or "This command is not available right now.")
        else:
            self.reason.SetLabel("")

    def _current(self) -> Command | None:
        sel = self.list.GetSelection()
        if sel < 0:
            return None
        return self.list.GetClientData(sel)

    def _on_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        if code in (wx.WXK_UP, wx.WXK_DOWN) and self.list.GetCount():
            if self.FindFocus() is self.filter:
                self.list.SetFocus()
        event.Skip()

    def _activate(self) -> None:
        cmd = self._current()
        if cmd is None:
            return
        if not cmd.is_available():
            self.reason.SetLabel(
                cmd.unavailable_reason or "This command is not available right now.")
            return
        self._chosen = cmd
        self.EndModal(wx.ID_OK)

    def chosen(self) -> Command | None:
        return self._chosen
