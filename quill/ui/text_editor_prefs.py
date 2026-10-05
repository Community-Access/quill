"""Preferences > Windows and your files: the two text-editor commands, as settings.

Somebody looking for "open my .txt files in this" goes to Preferences, so both
editors' Preferences carry the same group -- and since 2026-10-03 it is the only
door, with no menu row and no chord in either editor: a status
line saying which program opens in place of Notepad now, a button that runs
Make <app> My Text Editor, and a checkbox for Open <app> instead of Notepad.

None of it is a stored setting. Windows' registry is the truth, so the
checkbox is read from it when Preferences opens, and changing it does nothing
until OK (or QUILL's Apply): then the shared confirmation and administrator
prompt run, with Preferences still open as their owner,
and the checkbox is set from the registry again afterwards. If the person
says No, or Windows does not get approval, the box goes back to what is true
and the outcome is said once.

One implementation for both apps, like the commands themselves
(:mod:`quill.ui.text_editor_commands`). The host is the window that runs those
commands -- QUILL's ``MainFrame`` or a QUILL Lite document window.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core import windows_editor as editor
from quill.core.app_command import split_command

__all__ = ["GROUP_TITLE", "TextEditorPrefs", "notepad_status"]

GROUP_TITLE = "Windows and your files"


def notepad_status(profile: editor.EditorProfile, state: editor.NotepadState) -> str:
    """One line: which program opens in place of Notepad now."""
    if state.on:
        return f"{profile.app_name} opens in place of Notepad."
    if state.other_owner:
        return f"{state.other_owner} opens in place of Notepad."
    if state.other:
        program = Path(split_command(state.other)[0]).name or state.other
        return f"Another program opens in place of Notepad: {program}."
    return "Nothing opens in place of Notepad. Notepad opens as usual."


class TextEditorPrefs:
    """The group, built into one Preferences page.

    *make_key* and *notepad_key* are the access letters, chosen per window so
    no two controls share one (GATE-14); the wording is the same in both apps.
    """

    def __init__(
        self,
        dialog: Any,
        panel: Any,
        sizer: Any,
        host: Any,
        *,
        make_key: str,
        notepad_key: str,
        on_change: Callable[[], None] | None = None,
        pad: int = 6,
    ) -> None:
        self._dialog = dialog
        self._host = host
        profile = host._text_editor_profile()
        self._profile = profile
        name = profile.app_name
        self.heading = wx.StaticText(panel, label=GROUP_TITLE)
        self.heading.SetHelpText(
            f"Whether Windows opens your files, and Notepad, in {name}. Windows keeps "
            "these choices itself, so they are read from Windows each time."
        )
        sizer.Add(self.heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, pad)
        self.status = wx.StaticText(panel, label=self._status_text())
        self.status.SetHelpText(
            "Which program opens whenever anything on this computer starts Notepad: "
            f"nothing, {name}, the other QUILL editor, or another program by name."
        )
        sizer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.TOP, pad)
        self.make_button = wx.Button(
            panel, label=_with_key(f"Make {name} My Text Editor...", make_key)
        )
        self.make_button.SetHelpText(
            f"Tells Windows, for your account, that {name} can open text and the other "
            "types it reads, then opens Windows' Default apps page, where you choose."
        )
        sizer.Add(self.make_button, 0, wx.ALL, pad)
        self.notepad_check = wx.CheckBox(
            panel, label=_with_key(f"Open {name} instead of Notepad", notepad_key)
        )
        self.notepad_check.SetHelpText(
            f"When this is checked, {name} opens whenever anything on this computer "
            "starts Notepad. It affects every user, so after OK Windows asks for "
            "administrator approval. Uncheck it and press OK to put Notepad back."
        )
        self.notepad_check.SetValue(self._live())
        sizer.Add(self.notepad_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, pad)
        self.make_button.Bind(wx.EVT_BUTTON, lambda _e: self.make_default())
        if on_change is not None:
            self.notepad_check.Bind(wx.EVT_CHECKBOX, lambda _e: on_change())
        # OK commits before the window closes, so the questions belong to it.
        dialog.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        dialog.text_editor_prefs = self

    # -- reading Windows ------------------------------------------------------ #

    def _state(self) -> editor.NotepadState:
        reader = self._host._text_editor_system().MachineReader()
        try:
            return editor.read_notepad_state(self._profile, reader)
        except Exception:  # noqa: BLE001 - an unreadable registry reads as "off"
            return editor.NotepadState()

    def _live(self) -> bool:
        return self._state().on

    def _status_text(self) -> str:
        return notepad_status(self._profile, self._state())

    def refresh(self) -> None:
        """Show what Windows says now."""
        self.notepad_check.SetValue(self._live())
        self.status.SetLabel(self._status_text())

    # -- acting ------------------------------------------------------------------ #

    def _owned(self, run: Callable[[], Any]) -> Any:
        """Run a host command with this window as the owner of its questions."""
        self._host._text_editor_dialog_owner = self._dialog
        try:
            return run()
        finally:
            self._host._text_editor_dialog_owner = None

    def make_default(self) -> None:
        self._owned(self._host.cmd_make_default_editor)

    def commit(self) -> str:
        """Apply the checkbox, if it differs from Windows; what happened.

        ``"unchanged"`` when there was nothing to do. On No, a refusal or a
        declined prompt the box goes back to the truth; the command has already
        spoken every outcome except No, which is said here, once.
        """
        if bool(self.notepad_check.GetValue()) == self._live():
            return "unchanged"
        outcome = self._owned(self._host.cmd_toggle_notepad_replacement)
        if outcome == "cancelled":
            self._host._announce("Notepad is unchanged.")
        self.refresh()
        return str(outcome)

    def _on_ok(self, event: Any) -> None:
        self.commit()
        event.Skip()


def _with_key(label: str, key: str) -> str:
    """*label* with an ``&`` before the first *key* (case-insensitive)."""
    index = label.lower().find(key.lower()) if key else -1
    return label if index < 0 else f"{label[:index]}&{label[index:]}"
