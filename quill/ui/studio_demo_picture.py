"""Screen and camera choices of the Record a demonstration window.

Split from :mod:`quill.ui.studio_demo_dialog` (GATE-11). Two check boxes,
Screen and Camera, make every combination: screen alone, screen with a
camera corner, the camera filling the picture, or neither (sound only).
Only the controls that apply to the chosen combination are enabled.
"""

from __future__ import annotations

import wx


class DemoPictureMixin:
    def _camera_toggled(self, _event: wx.Event | None) -> None:
        on = self.camera_on.GetValue() and bool(self.callbacks.cameras)
        for control in (
            self.camera_panel,
            self.face_alerts,
            self.mirrored,
            self.camera_check_button,
        ):
            control.Enable(on)
        if self.camera_on.GetValue() and not self.callbacks.cameras:
            self.summary.ChangeValue("No camera was found. Connect one and open this window again.")
        self._picture_changed(None)

    def _picture_changed(self, _event: wx.Event | None) -> None:
        """Enable what applies to the chosen picture: screen, camera, both or neither."""
        screen = self.screen_on.GetValue()
        camera = self.camera_on.GetValue() and bool(self.callbacks.cameras)
        for control in (self.target, self.refresh_button, self.pointer, self.ceiling):
            control.Enable(screen)
        # Corner and size apply only when the camera sits on top of the screen.
        self.position.Enable(screen and camera)
        self.camera_size.Enable(screen and camera)
        self.fps.Enable(screen or camera)
        self.silent_track.Enable(screen or camera)
        self.sound_format.Enable(not (screen or camera))
        self._stale(None)

    def _camera_check(self, _event: wx.Event) -> None:
        if self.callbacks.cameras:
            self.callbacks.camera_check(
                self.camera.GetString(self.camera.GetSelection()), self.mirrored.GetValue()
            )

    def _browse(self, _event: wx.Event) -> None:
        chosen = self.callbacks.choose_folder(self, self.folder.GetValue())
        if chosen:
            self.folder.SetValue(chosen)
