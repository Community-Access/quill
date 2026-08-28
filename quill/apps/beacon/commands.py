"""Command Palette (PRD 18.3, Appendix B).

A single searchable list of every command in the app. Fuzzy prefix match,
keyboard-first: type to filter, Up/Down to move, Enter to run, Esc to close.
"""

from __future__ import annotations

import wx

from quill.ui.dialog_contract import apply_modal_ids


def _name(ctrl: wx.Control, name: str) -> None:
    ctrl.SetName(name)


class Command:
    def __init__(self, name: str, shortcut: str, handler, hint: str = "") -> None:
        self.name = name
        self.shortcut = shortcut
        self.handler = handler
        self.hint = hint

    def display(self) -> str:
        return f"{self.name}  ({self.shortcut})" if self.shortcut else self.name


class CommandPalette(wx.Dialog):
    """Modal palette over a list of Commands."""

    def __init__(self, parent, commands: list[Command]):
        super().__init__(
            parent, title="Command Palette", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._commands = commands
        self._chosen: Command | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.filter = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        _name(self.filter, "Type to filter commands")
        self.filter.SetHelpText(
            "Type part of a command's name to filter the list below. Enter "
            "runs the highlighted command, Down arrow moves into the list, "
            "Escape closes without running anything."
        )
        sizer.Add(self.filter, 0, wx.EXPAND | wx.ALL, 8)

        self.list = wx.ListBox(self, style=wx.LB_SINGLE)
        _name(self.list, "Commands")
        self.list.SetHelpText(
            "Every command in the app, with its keyboard shortcut in "
            "parentheses when it has one. Enter or double-click runs the "
            "selected command."
        )
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._populate("")

        self.SetSizer(sizer)
        self.SetSize((420, 360))
        self.filter.SetFocus()

        self.filter.Bind(wx.EVT_TEXT, self._on_text)
        self.filter.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._activate())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._activate())
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)

        # No visible OK/Cancel buttons: Enter activates the selected command
        # (EndModal ID_OK) and Escape closes (EndModal ID_CANCEL) via the char
        # hook. Wire the shared contract with no backing-button ids so the
        # button-contract audit has nothing unbacked to flag.
        apply_modal_ids(self)
        # F1 context help (GATE-BEACON-HELP): the palette is shown with a
        # bare ShowModal(), so it binds the family hook itself. Bound after
        # the palette's own char hook, so F1 answers here and every other
        # key falls through to the filter behavior above.
        from quill.ui.app_context_help import install as _install_f1

        _install_f1(self)

    def _populate(self, text: str) -> None:
        text = text.lower().strip()
        self.list.Clear()
        for cmd in self._commands:
            if not text or text in cmd.name.lower():
                self.list.Append(cmd.display(), cmd)

    def _on_text(self, _e) -> None:
        self._populate(self.filter.GetValue())

    def _on_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        if event.GetKeyCode() in (wx.WXK_UP, wx.WXK_DOWN) and self.list.GetCount():
            self.list.SetFocus()
            self.list.SetSelection(0)
            return
        event.Skip()

    def _activate(self) -> None:
        sel = self.list.GetSelection()
        if sel < 0:
            return
        self._chosen = self.list.GetClientData(sel)
        self.EndModal(wx.ID_OK)

    def chosen(self) -> Command | None:
        return self._chosen
