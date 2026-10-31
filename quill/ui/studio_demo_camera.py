"""Check camera framing: hear whether your face is in view and which way to move.

The camera opens only while this window is open, frames stay in memory, and
face detection is Windows' own, on this computer. Advice is spoken when it
changes and has held for a moment -- the field is read-only and unfocused
text changes are not something a screen reader says on its own (GATE-13 lets
the app speak exactly that) -- and the latest advice is always in the field.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.demo_camera import Framing, FramingAnnouncer
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class CameraCheckDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        ffmpeg: str,
        device: str,
        *,
        mirrored: bool,
        announce: Callable[[str], None],
    ) -> None:
        super().__init__(parent, title="Check camera framing", style=wx.DEFAULT_DIALOG_STYLE)
        self._announce = announce
        self._announcer = FramingAnnouncer()
        self._ffmpeg = ffmpeg
        self._device = device
        self._check: object | None = None
        layout = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                f"Camera: {device}. Sit as you will when recording. Studio says when your "
                "face comes into view and which way to move. Nothing is recorded."
            ),
        )
        intro.Wrap(460)
        layout.Add(intro, 0, wx.ALL, 10)
        layout.Add(wx.StaticText(self, label="&Framing"), 0, wx.LEFT, 10)
        self.advice = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(self, 460, 70)
        )
        set_accessible_name(self.advice, "Framing")
        self.advice.SetHelpText(
            "The latest framing advice: no face, face in view and centred, or which way to "
            "move. Studio also says it aloud when it changes."
        )
        self.advice.ChangeValue("Starting the camera.")
        layout.Add(self.advice, 0, wx.EXPAND | wx.ALL, 10)
        self.mirror = wx.CheckBox(self, label="The camera gives a &mirror image")
        self.mirror.SetValue(mirrored)
        self.mirror.SetHelpText(
            "Turn on if the advice sends you the wrong way; some cameras flip left and right."
        )
        self.mirror.Bind(wx.EVT_CHECKBOX, self._mirror_changed)
        layout.Add(self.mirror, 0, wx.LEFT | wx.RIGHT, 10)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close the camera check; the camera is released.")
        layout.Add(close, 0, wx.ALL, 10)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(layout)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._poll, self._timer)
        self._start()
        self.advice.SetFocus()

    @property
    def mirrored(self) -> bool:
        return self.mirror.GetValue()

    def _start(self) -> None:
        from quill.platform.windows.demo_media import CameraCheck

        self._stop()
        check = CameraCheck(
            self._ffmpeg,
            self._device,
            lambda result: wx.CallAfter(self._framing, result),
            mirrored=self.mirror.GetValue(),
        )
        try:
            check.start()
        except OSError as error:
            self.advice.ChangeValue(str(error))
            self._announce(str(error))
            return
        self._check = check
        self._timer.Start(1000)

    def _stop(self) -> None:
        check, self._check = self._check, None
        if check is not None:
            check.stop()  # type: ignore[attr-defined]

    def _mirror_changed(self, _event: wx.Event) -> None:
        self._announcer = FramingAnnouncer()
        self._start()

    def _poll(self, _event: wx.TimerEvent) -> None:
        check = self._check
        if check is None:
            return
        failure = check.failure  # type: ignore[attr-defined]
        if failure:
            self._timer.Stop()
            self.advice.ChangeValue(failure)
            self._announce(failure)
            self._stop()

    def _framing(self, result: Framing) -> None:
        if not self or self._check is None:
            return
        if result.sentence != self.advice.GetValue():
            self.advice.ChangeValue(result.sentence)
        sentence = self._announcer.feed(result)
        if sentence:
            self._announce(sentence)

    def _on_destroy(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self:
            if self._timer.IsRunning():
                self._timer.Stop()
            self._stop()
        event.Skip()

    def latest(self) -> str:
        return self.advice.GetValue()
