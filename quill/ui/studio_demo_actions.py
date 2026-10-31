"""Check, start and test in the Record a demonstration window.

Split from :mod:`quill.ui.studio_demo_dialog` (GATE-11). *Check* runs in the
background and puts one summary into a read-only field that takes focus;
Start recording stays disabled while any Stop remains, and any change after
a check asks for a new one rather than starting on stale facts.
"""

from __future__ import annotations

import wx

from quill.core.demo_recording import DemoRecordingError


class DemoActionsMixin:
    def _stale(self, _event: wx.Event | None) -> None:
        if self.checked_plan is not None:
            self.checked_plan = None
            self.summary.ChangeValue("Settings changed since the check. Press Check again.")
        if getattr(self, "start_button", None) is not None:
            self.start_button.Enable(False)
        if _event is not None:
            _event.Skip()

    def _check(self, _event: wx.Event) -> None:
        if self._checking:
            return
        try:
            plan = self.build_plan()
        except DemoRecordingError as error:
            self.summary.ChangeValue(f"Stop: {error}")
            self.summary.SetFocus()
            return
        self._checking = True
        self.check_button.Enable(False)
        self.summary.ChangeValue("Checking. This takes a few seconds.")

        def done(text: str, ok: bool) -> None:
            if not self:
                return
            self._checking = False
            self.check_button.Enable(True)
            self.summary.ChangeValue(text)
            self.checked_plan = plan if ok else None
            if self.start_button is not None:
                self.start_button.Enable(ok)
            self.summary.SetInsertionPoint(0)
            self.summary.SetFocus()

        self.callbacks.check(plan, done)

    def _summary_key(self, event: wx.KeyEvent) -> None:
        # A read-only multi-line field keeps Enter for itself; here it starts.
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if self.checked_plan is not None and self.start_button is not None:
                if self.start_button.IsEnabled():
                    self.EndModal(wx.ID_OK)
                    return
        event.Skip()

    def _test(self, _event: wx.Event) -> None:
        try:
            plan = self.build_plan()
        except DemoRecordingError as error:
            self.summary.ChangeValue(f"Stop: {error}")
            self.summary.SetFocus()
            return
        self.callbacks.test(plan, self.test_seconds.GetValue())
