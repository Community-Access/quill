"""Transcribe a Recording in QUILL Transcribe: QUILL's own pipeline, reviewed here.

Nothing about turning a recording into text is QUILL Transcribe's own. The
command, the window that asks for the recording and model, the background
queue, the progress and the notifications are QUILL's and QUILL Lite's
:class:`~quill.ui.windows_dictation_transcribe.DictationTranscribeMixin`, which
runs :class:`~quill.core.windows_dictation.file_transcribe.FileTranscriber` on
the task manager. This module only answers the hooks that mixin asks an app
for -- where to say things, which window is the parent, which task manager --
and gives the finished text somewhere to go that is not an editor:

**Review Transcript** shows it read-only, to arrow through, with five explicit
actions: Type into a Field, Copy All, Save As, Open in QUILL, Close. Nothing goes
to the clipboard or into another program unless you choose it. **Type into a
Field** (D-5) types the transcript -- or only the part selected -- into the
program you go back to, through Recent Phrases' Insert Again: the same wait for
another program to come forward, the same field checks and never-type list as a
dictated phrase, and a part Windows did not take is kept for Recent Phrases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip_size
from quill.ui.windows_dictation_transcribe import DictationTranscribeMixin

__all__ = ["TranscribeFilesMixin", "TranscriptReviewDialog"]

_PAD = 8


class TranscriptReviewDialog(wx.Dialog):
    """A finished transcript, read-only, with what can be done with it."""

    def __init__(self, parent: Any, text: str) -> None:
        super().__init__(
            parent, title="Review Transcript", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.action = ""
        #: What Type into a Field types: the selected part, or all of it.
        self.chosen_text = text
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Transcript:")
        self.text = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.text.SetHelpText(
            "The transcript, read-only. Read it with the arrow keys; select part of "
            "it and press Ctrl+C to copy just that part."
        )
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        type_in = wx.Button(self, label="Type into a &Field")
        type_in.SetHelpText(
            "Type the transcript, or only the part you selected, into another program. "
            "Switch to the field you want and it is typed there, with the same checks as "
            "dictation: never into a password field or a program on your never-type list."
        )
        copy = wx.Button(self, label="&Copy All")
        copy.SetHelpText("Put the whole transcript on the clipboard.")
        save = wx.Button(self, label="&Save As...")
        save.SetHelpText("Save the transcript as a text file where you choose.")
        quill = wx.Button(self, label="Open in &QUILL")
        quill.SetHelpText("Open the transcript in QUILL to edit it.")
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the transcript. It stays in Notifications.")
        for button in (type_in, copy, save, quill, close):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.text, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(buttons, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize(dip_size(self, 680, 520))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        type_in.Bind(wx.EVT_BUTTON, lambda _e: self._finish("type"))
        copy.Bind(wx.EVT_BUTTON, lambda _e: self._finish("copy"))
        save.Bind(wx.EVT_BUTTON, lambda _e: self._finish("save"))
        quill.Bind(wx.EVT_BUTTON, lambda _e: self._finish("quill"))
        self.text.SetFocus()
        self.text.SetInsertionPoint(0)

    def _finish(self, action: str) -> None:
        self.action = action
        part = str(self.text.GetStringSelection())
        if action == "type" and part.strip():
            self.chosen_text = part
        self.EndModal(wx.ID_OK)


class TranscribeFilesMixin(DictationTranscribeMixin):
    """The hooks QUILL's file transcription asks of its host."""

    frame: Any
    _task_manager: Any

    def _dictation_parent(self) -> Any:
        return self.frame

    def _dictation_run_modal(self, dialog: Any, label: str) -> int:
        return int(self._show_modal_dialog(dialog, label))  # type: ignore[attr-defined]

    def _dictation_say(self, text: str) -> None:
        self._announce(text, force=True)  # type: ignore[attr-defined]

    def _dictation_say_quietly(self, text: str) -> None:
        self._announce(text)  # type: ignore[attr-defined]

    def _dictation_status(self, text: str) -> None:
        self._set_status(text)  # type: ignore[attr-defined]

    def _dictation_cue(self, event: str) -> None:
        from quill.ui.sound_manager import post_sound

        try:
            post_sound(event)
        except Exception:  # noqa: BLE001 - a missing sound is never a failure
            pass

    def _dictation_task_manager(self) -> Any:
        return self._task_manager

    def _dictation_app_name(self) -> str:
        return "QUILL Transcribe"

    def _dictation_profile_path(self) -> Path:
        from quill.core.speech.dictation_profile import default_profile_path

        return default_profile_path()

    def transcribe_a_recording(self) -> None:
        """File > Transcribe a Recording...: QUILL's own command."""
        self.cmd_transcribe_audio_file()

    def _dictation_open_file(self, path: Path) -> None:
        """A finished transcript's notice was opened: review it here."""
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as error:
            self._dictation_say(f"The transcript could not be opened: {error.strerror or error}")
            return
        dialog = TranscriptReviewDialog(self.frame, text)
        try:
            self._dictation_run_modal(dialog, "Review Transcript")
            action, chosen = dialog.action, dialog.chosen_text
        finally:
            dialog.Destroy()
        if action == "type":
            self.insert_recent_phrase(chosen)  # type: ignore[attr-defined]
        elif action == "copy":
            copied = self._copy_to_clipboard(text)  # type: ignore[attr-defined]
            self._dictation_say("Transcript copied." if copied else "Could not copy.")
        elif action == "save":
            self._save_transcript_as(text)
        elif action == "quill":
            self.open_in_quill(str(path))  # type: ignore[attr-defined]

    def _save_transcript_as(self, text: str) -> None:
        from quill.core.storage import write_text_atomic

        dialog = wx.FileDialog(
            self.frame,
            "Save Transcript As",
            wildcard="Text files (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if self._dictation_run_modal(dialog, "Save Transcript As") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        finally:
            dialog.Destroy()
        try:
            write_text_atomic(target, text, encoding="utf-8")
        except OSError as error:
            self._dictation_say(f"Could not save {target.name}: {error.strerror or error}")
            return
        self._dictation_say(f"Saved {target.name}.")
