"""Explicit local record, recognize and review journey for a screenshot note."""

from __future__ import annotations

import wx

from quill.core.screenshot_note import ScreenshotNoteSession
from quill.stability.task_manager import UiLifetimeToken
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class ScreenshotNoteDialog(wx.Dialog):
    def __init__(self, host, evidence):
        super().__init__(
            host.frame,
            title="Add a spoken screenshot note",
            size=(700, 520),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.host, self.evidence = host, evidence
        self.session = ScreenshotNoteSession()
        self.lifetime = UiLifetimeToken()
        self.task = None
        self.busy = self.recording = False
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(
            wx.StaticText(
                self,
                label="Add a note using your chosen microphone. Recognition "
                "stays local and needs an installed speech model. Audio is deleted after "
                "recognition or cancellation. Stops after two minutes. Nothing is sent to AI.",
            ),
            0,
            wx.ALL,
            8,
        )
        start = wx.Button(self, label="&Start recording note")
        start.SetHelpText(
            "Open the shared microphone explicitly. Another QUILL recording blocks this action."
        )
        start.Bind(wx.EVT_BUTTON, self._start)
        layout.Add(start, 0, wx.ALL, 8)
        stop = wx.Button(self, label="S&top and recognize")
        stop.SetHelpText(
            "Close the microphone and recognize the note locally, then review its text."
        )
        stop.Bind(wx.EVT_BUTTON, self._finish)
        layout.Add(stop, 0, wx.ALL, 8)
        layout.Add(wx.StaticText(self, label="&Review and correct your note"), 0, wx.LEFT, 8)
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        set_accessible_name(self.text, "Review and correct your note")
        self.text.SetHelpText(
            "Edit the words before using them with this screenshot. Recognition can be wrong."
        )
        layout.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        self.reviewed = wx.CheckBox(self, label="I reviewed and corrected this note")
        self.reviewed.SetHelpText(
            "Check this after reviewing the words. Editing clears the acknowledgment."
        )
        self.text.Bind(wx.EVT_TEXT, lambda event: self.reviewed.SetValue(False))
        layout.Add(self.reviewed, 0, wx.ALL, 8)
        self.status = wx.StaticText(self, label="Microphone off. Start when ready, or type a note.")
        layout.Add(self.status, 0, wx.ALL, 8)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Use reviewed note",
            cancel_id=wx.ID_CANCEL,
        )
        self.Bind(wx.EVT_BUTTON, self._accept, id=wx.ID_OK)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._finish, self.timer)
        self.SetSizer(layout)
        start.SetFocus()
        # a11y: needs manual verification — microphone feedback, focus and review with AT.

    def _say(self, message):
        self.status.SetLabel(message)
        self.host._announce(message)

    def _run(self, name, work, ready):
        if self.busy:
            self._say("Please wait for the current note operation to finish.")
            return
        self.busy = True

        def success(task, result):
            self.busy = False
            ready(result)

        def failed(task, error):
            self.busy = self.recording = False
            self.session.close()
            self._say(f"Could not complete the note: {error}. Microphone off.")

        self.task = self.host._task_manager.submit(
            name, work, on_success=success, on_failure=failed, ui_lifetime=self.lifetime
        )

    def _start(self, event):
        if self.recording:
            self._say("Already recording. Choose Stop and recognize when finished.")
            return

        def work(**kwargs):
            from quill.core.speech.transcribe import has_installed_offline_model

            if not has_installed_offline_model():
                raise ValueError(
                    "No offline speech model is installed. Use the shared Speech Hub first."
                )
            self.session.start()

        def ready(result):
            self.recording = True
            self.timer.StartOnce(120000)
            self._say("Recording your note. Choose Stop and recognize when finished.")

        self._run("Record screenshot note", work, ready)

    def _finish(self, event):
        if not self.recording or self.busy:
            self._say("No note is recording, or recognition is already running.")
            return
        self.recording = False
        self.timer.Stop()
        self._say("Stopping the microphone and recognizing your note locally...")

        def ready(record):
            self.text.ChangeValue(record["text"])
            self.reviewed.SetValue(False)
            self._say("Microphone off. Review and correct the note, then choose Use reviewed note.")

        self._run(
            "Recognize screenshot note",
            lambda cancellation_token, **kw: self.session.finish(self.evidence, cancellation_token),
            ready,
        )

    def _accept(self, event):
        if self.busy or self.recording:
            self._say("Stop recording and wait for recognition before using the note.")
            return
        if not self.text.GetValue().strip() or not self.reviewed.GetValue():
            self._say("Enter or recognize a note, review it, and check the review box.")
            self.text.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def stop(self):
        self.timer.Stop()
        self.lifetime.invalidate()
        if self.task is not None:
            self.task.cancellation_token.cancel()
        self.session.close()
