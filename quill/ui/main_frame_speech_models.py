"""Offline speech model selection for MainFrame: which model, and is one installed.

Split from ``main_frame_speech.py`` and ``main_frame_speech_voice.py`` under
GATE-11. Moving model enumeration off the UI thread gave both mixins the same
needs -- check for an installed model in the background before a command
starts, pick the default model, and transcribe a captured recording with it --
so those live here once instead of growing either file. ``SpeechModelsMixin``
composes onto ``MainFrame`` beside ``SpeechCommandsMixin`` and
``VoiceInteractionMixin``; it relies on the frame's ``settings``, ``_wx``,
``_speech_provider``, ``_show_message_box``, ``_run_background_task`` and
``open_speech_models``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def discard_recording(wav_path: Path) -> None:
    """Delete a captured recording; a file that is already gone is fine."""
    try:
        wav_path.unlink(missing_ok=True)
    except OSError:
        pass


class SpeechModelsMixin:
    """Installed-model checks and default-model choice for the speech commands."""

    def _select_model_and_diarize(self, installed: list) -> tuple[str, bool]:
        """Prefer an installed speaker-detection model (enables diarization)."""
        from quill.core.speech.catalog import is_diarization_model

        for model in installed:
            if is_diarization_model(model.id):
                return model.id, True
        return self._default_model_id(installed), False

    def _check_installed_speech_models(
        self,
        provider: object,
        title: str,
        on_ready: Callable[[object, list], None],
    ) -> None:
        """Enumerate installed models off-thread, then continue on the UI thread."""

        def work(_progress: Callable[[str, int, int], None]) -> tuple[object, list]:
            installed = list(provider.list_installed_models())  # type: ignore[attr-defined]
            if not installed:
                from quill.core.speech.service import DEFAULT_PROVIDER_ID

                if getattr(provider, "id", "") != DEFAULT_PROVIDER_ID:
                    fallback = self._speech_provider()
                    if fallback is not provider:
                        installed = list(fallback.list_installed_models())  # type: ignore[attr-defined]
                        if installed:
                            return fallback, installed
            return provider, installed

        def ready(result: object) -> None:
            selected_provider, installed = result  # type: ignore[misc]
            if installed:
                on_ready(selected_provider, installed)
                return
            wx = self._wx
            offer = self._show_message_box(
                "No offline speech model is installed yet. "
                "Open Manage Speech Models to download one?",
                title,
                wx.ICON_INFORMATION | wx.YES_NO,
            )
            if offer == wx.YES:
                self.open_speech_models()

        self._run_background_task(f"Checking speech models for {title}", work, ready)

    def _default_model_id(self, installed: list) -> str:
        """The model id to transcribe/dictate with: the user's explicit "Set as
        Default" choice when it is actually installed, else the catalog's
        recommended model, else whichever model is installed first."""
        from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

        ids = [m.id for m in installed]
        preferred = str(getattr(self.settings, "speech_default_model_id", "") or "")
        if preferred and preferred in ids:
            return preferred
        return RECOMMENDED_MODEL_ID if RECOMMENDED_MODEL_ID in ids else ids[0]

    def _transcribe_recording(
        self,
        provider: object,
        wav_path: Path,
        progress: Callable[[str, int, int], None],
        finish: Callable[[object], object] = lambda result: result,
    ) -> object | None:
        """Worker-thread body: transcribe ``wav_path`` with the default model.

        Returns None when no model is installed (the recording is left for the
        caller); otherwise ``finish`` applied to the provider's result, and the
        recording is deleted whether or not transcription succeeded."""
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if not installed:
            return None
        from quill.core.speech.provider import TranscriptionRequest

        model_id = self._default_model_id(installed)
        request = TranscriptionRequest(source_path=wav_path, model_id=model_id)

        def _on_progress(fraction: float, message: str) -> None:
            progress(message, int(fraction * 100), 100)

        try:
            return finish(provider.transcribe_file(request, _on_progress))  # type: ignore[attr-defined]
        finally:
            discard_recording(wav_path)
