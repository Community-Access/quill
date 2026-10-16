"""Programs Dictation Never Types Into: the never-type list, in a window (D-24).

Reached from More Dictation Settings (**Programs Dictation Never Types
Into...**, Alt+N) in QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell --
the one window, over the one setting, ``windows_dictation_never_type``
(:mod:`quill.core.windows_dictation.never_type`).

* **The list** -- each program by name and file name: "KeePass (keepass.exe)".
* **Add the Program in Front** -- the program you were in before you opened
  the settings. It is found when this window opens, from the order Windows
  keeps its windows in (:func:`quill.platform.windows.foreground.program_behind`),
  because by the time the button is pressed this window is in front.
* **Add by Name** -- a file name typed in the field beside it: keepass.exe, or
  just KeePass.
* **Remove** -- the program chosen in the list.

Each outcome is said once, because the list changing beside the focused
button is exactly what a screen reader does not announce (GATE-12). Nothing is
kept until OK; More Dictation Settings keeps it until its own OK, and Dictation
Settings applies it with its OK.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import wx

from quill.core.windows_dictation.never_type import friendly_name, normalise_image_name
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["NeverTypeDialog", "program_in_front"]

_PAD = 8


def program_in_front() -> str:
    """The file name of the program behind this one's windows, or ``""``."""
    try:
        from quill.platform.windows.foreground import program_behind

        return str(program_behind(os.getpid()).process_name or "")
    except Exception:  # noqa: BLE001 - not Windows: there is no program to name
        return ""


def _row(name: str) -> str:
    friendly = friendly_name(name)
    return name if friendly == name else f"{friendly} ({name})"


class NeverTypeDialog(wx.Dialog):
    """The never-type list. Read with :meth:`names` after OK."""

    def __init__(
        self,
        parent: Any,
        names: list[str],
        announce: Callable[[str], None] | None = None,
        *,
        front: Callable[[], str] = program_in_front,
    ) -> None:
        super().__init__(
            parent,
            title="Programs Dictation Never Types Into",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._announce = announce or (lambda _text: None)
        self._names = [name for name in (normalise_image_name(n) for n in names) if name]
        #: Found now, while the person's own program is still the one behind us.
        self._front = normalise_image_name(front())
        root = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, label="&Programs dictation never types into:")
        self.list = wx.ListBox(self, choices=[_row(name) for name in self._names])
        self.list.SetHelpText(
            "Dictation never types into these programs, from QUILL Transcribe, Quill "
            "Inkwell's Dictate Anywhere or Insert Again: it says so and types nothing, "
            "and words already held stay held. Programs are matched by their file "
            "name, never by a window title. It starts with the common password "
            "managers and the Windows sign-in prompts. Delete removes the chosen one."
        )
        self.list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        if self._names:
            self.list.SetSelection(0)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)

        # Say which program: the button adds it to a list that blocks typing.
        front_label = (
            f"Add &Front Program: {_row(self._front)}"
            if self._front
            else "Add the Program in &Front"
        )
        self.add_front = wx.Button(self, label=front_label)
        self.add_front.SetHelpText(
            "Adds the program you were using before you opened these settings, by "
            "its file name. Switch to that program, come back to dictation's "
            "settings, then press this."
        )
        self.add_front.Bind(wx.EVT_BUTTON, lambda _e: self.add_program_in_front())
        self.remove = wx.Button(self, label="&Remove")
        self.remove.SetHelpText("Takes the program chosen in the list off it.")
        self.remove.Bind(wx.EVT_BUTTON, lambda _e: self.remove_chosen())
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.add_front, 0, wx.RIGHT, _PAD)
        row.Add(self.remove, 0)
        root.Add(row, 0, wx.ALL, _PAD)

        name_label = wx.StaticText(self, label="Program file &name, like keepass.exe:")
        # Enter adds the name here instead of pressing OK past it.
        self.name = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.name.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.add_by_name())
        self.name.SetHelpText(
            "Type a program's file name, like keepass.exe, then press Add by Name. "
            "A name without .exe has it added. Enter adds it too."
        )
        self.add_name = wx.Button(self, label="&Add by Name")
        self.add_name.SetHelpText("Adds the program file name typed in the field before it.")
        self.add_name.Bind(wx.EVT_BUTTON, lambda _e: self.add_by_name())
        root.Add(name_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(self.name, 1, wx.RIGHT, _PAD)
        name_row.Add(self.add_name, 0)
        root.Add(name_row, 0, wx.EXPAND | wx.ALL, _PAD)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((560, 420))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.list.SetFocus()

    # -- the buttons ------------------------------------------------------------ #

    def _on_list_key(self, event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.remove_chosen()
            return
        event.Skip()

    def _on_ok(self, event: Any) -> None:
        # A name typed and never added is kept rather than thrown away.
        if normalise_image_name(self.name.GetValue()):
            self.add_by_name()
        event.Skip()

    def _add(self, name: str) -> bool:
        if name in self._names:
            self._announce(f"{name} is already on the list.")
            return False
        self._names.append(name)
        self.list.Append(_row(name))
        self.list.SetSelection(len(self._names) - 1)
        self._announce(f"Added {_row(name)}.")
        return True

    def add_program_in_front(self) -> bool:
        if not self._front:
            self._announce(
                "No other program was in front when these settings opened. Type its "
                "file name instead, like keepass.exe."
            )
            return False
        return self._add(self._front)

    def add_by_name(self) -> bool:
        name = normalise_image_name(self.name.GetValue())
        if not name:
            self._announce("Type a program file name first, like keepass.exe.")
            self.name.SetFocus()
            return False
        added = self._add(name)
        if added:
            self.name.SetValue("")
        return added

    def remove_chosen(self) -> bool:
        row = self.list.GetSelection()
        if not 0 <= row < len(self._names):
            self._announce("Choose a program in the list first.")
            return False
        name = self._names.pop(row)
        self.list.Delete(row)
        if self._names:
            self.list.SetSelection(min(row, len(self._names) - 1))
        self._announce(f"Removed {_row(name)}.")
        return True

    def names(self) -> list[str]:
        """The list as it stands, in order."""
        return list(self._names)
