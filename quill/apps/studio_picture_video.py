"""Studio's Make a YouTube video from a picture and sound command (roadmap V3, V4).

Thin adapter: the window is :mod:`quill.ui.studio_picture_video`, the work
:mod:`quill.platform.windows.picture_video_maker`. A sound-only recording's
result window offers this with the sound already filled in.
"""

from __future__ import annotations

import wx


class StudioPictureVideoMixin:
    def make_picture_video(self, sound: str = "", picture: str = "") -> None:
        if getattr(self, "_picture_video_busy", False):
            self._announce("A video is already being made.")
            return
        ffmpeg = self._demo_ffmpeg()
        if not ffmpeg:
            self._announce("Making a video needs FFmpeg. Use Voices, Get FFmpeg.")
            return
        if not picture:
            last = getattr(self, "_last_capture", None)
            picture = str(getattr(last, "path", "") or "")
        from quill.core.demo_recording import DemoRecordingError
        from quill.ui.studio_picture_video import PictureVideoDialog

        dialog = PictureVideoDialog(
            self.frame, choose_file=self._choose_media_file, picture=picture, sound=sound
        )
        try:
            while self._show_modal_dialog(dialog, dialog.GetTitle()) == wx.ID_OK:
                try:
                    plan = dialog.build_plan()
                    break
                except DemoRecordingError as error:
                    self._show_message_box(str(error), dialog.GetTitle(), wx.OK | wx.ICON_ERROR)
            else:
                return
        finally:
            dialog.Destroy()
        self._picture_video_busy = True
        self._announce("Making the video.")

        def work(*, cancellation_token, **_kwargs):
            from quill.platform.windows.picture_video_maker import make_picture_video

            return make_picture_video(ffmpeg, plan, cancellation_token)

        def done(_task, verification):
            self._picture_video_busy = False
            self._show_demo_result(verification, title=f"Video: {verification.state}")

        def failed(_task, error):
            self._picture_video_busy = False
            self._announce(f"The video could not be made: {error}")

        self._task_manager.submit(
            "Make a video",
            work,
            on_success=done,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )

    def _choose_media_file(self, parent: wx.Window, what: str, wildcard: str) -> str | None:
        dialog = wx.FileDialog(
            parent,
            f"Choose the {what.lower()}",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, f"Choose the {what.lower()}") == wx.ID_OK:
                return dialog.GetPath()
            return None
        finally:
            dialog.Destroy()
