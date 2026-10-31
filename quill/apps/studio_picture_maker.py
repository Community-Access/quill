"""Studio's Make a picture with AI command (roadmap V1).

Each request is approved first, naming the provider, model and endpoint, and
the cost notice; AI off and Safe Mode refuse it. The picture is saved, then
described by the configured vision model in a separate request (covered by
the same approval), so the description is an independent look.
"""

from __future__ import annotations

import re
from datetime import datetime
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
        """``(settings, image provider, api key)`` or ``None`` after saying why not."""
        from quill.core.ai.image_generation import image_provider_for
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.assistant_ai import (
            load_assistant_connection_settings,
            load_provider_api_key,
        )

        if self._safe_mode or not load_ai_enabled():
            self._announce("AI is turned off or Studio is in Safe Mode, so no picture can be made.")
            return None
        settings = load_assistant_connection_settings()
        provider = settings.provider.strip()
        image_provider = image_provider_for(provider)
        if image_provider is None:
            self._announce(
                f"Your AI provider ({provider or 'none'}) does not make pictures. Choose OpenAI "
                "or Google Gemini in AI, Set Up AI."
            )
            return None
        return settings, image_provider, load_provider_api_key(provider)

    def _request_picture(self, turns, size, done, failed) -> None:
        from quill.core.ai.image_generation import (
            DEFAULT_HOSTS,
            DEFAULT_MODELS,
            ImageGenerationError,
            ImageRequest,
            conversation_prompt,
            generate_image,
        )

        connection = self._picture_connection()
        if connection is None:
            failed("No picture was made.")
            return
        settings, provider, api_key = connection
        model = DEFAULT_MODELS[provider]
        host = DEFAULT_HOSTS[provider].removeprefix("https://")
        try:
            prompt = conversation_prompt(turns)
        except ImageGenerationError as error:
            failed(str(error))
            return
        answer = self._show_message_box(
            f"Send this description to {settings.provider} to make a picture?\n"
            f"Model: {model}\nEndpoint: {host}\n\n"
            "The picture is then sent to your AI vision model to be described for you.\n"
            "Service charges may apply; Studio cannot estimate this request's price.",
            "Make a picture with AI",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if answer not in (wx.YES, wx.ID_YES):
            failed("Nothing was sent.")
            return
        self._announce("Making the picture. This can take a minute.")

        def work(**_kwargs):
            from quill.core.ai.vision import describe_image
            from quill.core.demo_recording import unique_path

            data = generate_image(ImageRequest(provider, api_key, prompt, size=size))
            folder = self._picture_folder()
            folder.mkdir(parents=True, exist_ok=True)
            words = re.sub(r"[^\w ]+", "", turns[0])[:40].strip() or "Picture"
            path = unique_path(folder / f"Picture - {words} - {datetime.now():%Y-%m-%d %H%M%S}.png")
            _save_png(data, path)
            description, error = describe_image(
                settings,
                api_key,
                path,
                prompt=(
                    "Describe this picture for a blind person who asked for it, so they can judge "
                    "whether it matches what they wanted: subject, layout, colours, any text "
                    "exactly as written, and anything odd or missing."
                ),
            )
            text = description or f"The picture was saved, but it could not be described: {error}"
            path.with_suffix(".description.txt").write_text(
                f"Asked for:\n{prompt}\n\nDescription:\n{text}\n", encoding="utf-8"
            )
            return path, text

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


def _save_png(data: bytes, path: Path) -> None:
    """Save the provider's image as PNG whatever format it arrived in."""
    import io

    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        image.save(path, format="PNG")
