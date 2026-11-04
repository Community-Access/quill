"""Studio's Make a picture with AI command (roadmap V1).

Each request is approved first, naming the provider, model and endpoint, and
the cost notice; AI off and Safe Mode refuse it. The picture is saved, then
described by the configured vision model in a separate request (covered by
the same approval), so the description is an independent look.
"""

from __future__ import annotations

from pathlib import Path

import wx


class StudioPictureMakerMixin:
    def make_picture_with_ai(self) -> None:
        from quill.ui.studio_picture_maker import PictureMakerDialog

        dialog = PictureMakerDialog(
            self.frame,
            request=self._request_picture,
            make_video=lambda picture: wx.CallAfter(self.make_picture_video, "", str(picture)),
            announce=self._announce,
        )
        self._picture_maker = dialog
        try:
            self._show_modal_dialog(dialog, dialog.GetTitle())
        finally:
            self._picture_maker = None
            dialog.Destroy()

    def _picture_connection(self):
        """The :class:`~quill.core.ai.picture_maker.PictureConnection`, or None after saying why."""
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.ai.picture_maker import picture_connection

        if self._safe_mode or not load_ai_enabled():
            self._announce("AI is turned off or Studio is in Safe Mode, so no picture can be made.")
            return None
        connection = picture_connection()
        if isinstance(connection, str):
            self._announce(connection)
            return None
        return connection

    def _request_picture(self, turns, size, done, failed) -> None:
        """One version, through the shared Picture Maker core (wordpress.md 6.9)."""
        from quill.core.ai.image_generation import ImageGenerationError, conversation_prompt
        from quill.core.ai.picture_maker import consent_message, make_picture

        connection = self._picture_connection()
        if connection is None:
            failed("No picture was made.")
            return
        try:
            conversation_prompt(turns)
        except ImageGenerationError as error:
            failed(str(error))
            return
        answer = self._show_message_box(
            consent_message(connection).replace("QUILL cannot", "Studio cannot"),
            "Make a picture with AI",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if answer not in (wx.YES, wx.ID_YES):
            failed("Nothing was sent.")
            return
        self._announce("Making the picture. This can take a minute.")

        def describe(path, prompt):
            from quill.core.ai.vision import describe_image

            return describe_image(connection.settings, connection.api_key, path, prompt=prompt)

        def work(**_kwargs):
            made = make_picture(connection, turns, size, self._picture_folder(), describe=describe)
            return made.path, made.description

        def ready(_task, result):
            path, text = result
            done(path, text)

        def broke(_task, error):
            failed(f"No picture was made: {error}")

        self._task_manager.submit(
            "Make a picture",
            work,
            on_success=ready,
            on_failure=broke,
            ui_lifetime=self._demo_lifetime(),
        )

    def _picture_folder(self) -> Path:
        return self._demo_default_folder().parent / "QUILL Studio Pictures"
