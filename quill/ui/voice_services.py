"""Voice I/O for the chat companion: microphone STT + text-to-speech output.

A thin, wx-free executor over the existing speech stack (``core.speech.capture`` +
an injected speech-to-text provider) and TTS (``core.ai.tts``). It is constructed
by the UI with already-resolved dependencies (provider, model, mic device, TTS
key), so availability is decided by the caller and this object just runs the
capture / transcribe / speak / save steps on whatever thread the caller uses.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from quill.core.ai.tts import DEFAULT_MODEL, DEFAULT_VOICE

__all__ = ["VoiceServices"]


class VoiceServices:
    """Capture spoken questions to text and speak answers aloud."""

    def __init__(
        self,
        *,
        stt_provider: Any = None,
        stt_model_id: str = "",
        device_index: int | None = None,
        tts_api_key: str = "",
        tts_voice: str = DEFAULT_VOICE,
        tts_model: str = DEFAULT_MODEL,
    ) -> None:
        self._stt_provider = stt_provider
        self._stt_model_id = stt_model_id
        self._device_index = device_index
        self._tts_api_key = tts_api_key or ""
        self._tts_voice = tts_voice
        self._tts_model = tts_model
        self._recorder: Any = None

    # -- availability ------------------------------------------------------

    def input_available(self) -> bool:
        """True when a mic and a speech-to-text model are both usable."""
        try:
            from quill.core.speech.capture import capture_available
        except Exception:  # noqa: BLE001
            return False
        return bool(capture_available() and self._stt_provider is not None and self._stt_model_id)

    def output_available(self) -> bool:
        """True when synthesized speech (with save/playback) is available."""
        return bool(self._tts_api_key)

    # -- speech to text ----------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recorder is not None and bool(getattr(self._recorder, "is_recording", False))

    def start_recording(self) -> None:
        from quill.core.speech.capture import MicRecorder

        self._recorder = MicRecorder()
        self._recorder.start(self._device_index)

    def stop_and_transcribe(self) -> str:
        """Stop recording, transcribe the audio, and return the recognized text."""
        recorder = self._recorder
        self._recorder = None
        if recorder is None:
            return ""
        wav_path = recorder.stop()
        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(source_path=Path(wav_path), model_id=self._stt_model_id)
        try:
            result = self._stt_provider.transcribe_file(request)
            return (getattr(result, "full_text", "") or "").strip()
        finally:
            try:
                Path(wav_path).unlink()
            except OSError:
                pass

    # -- text to speech ----------------------------------------------------

    def play(
        self,
        text: str,
        *,
        stop_event: threading.Event,
        pause_event: threading.Event,
    ) -> None:
        """Synthesize and play *text* (blocking; run on a worker thread)."""
        from quill.core.ai.tts import speak_text

        speak_text(
            text,
            self._tts_api_key,
            model=self._tts_model,
            voice=self._tts_voice,
            stop_event=stop_event,
            pause_event=pause_event,
        )

    def save(self, text: str, output_path: str | Path) -> None:
        """Export *text* to an MP3 file (Save as media)."""
        from quill.core.ai.tts import export_to_mp3

        export_to_mp3(text, output_path, self._tts_api_key, voice=self._tts_voice)
