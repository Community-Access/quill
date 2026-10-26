"""Explicit offline screenshot-note dictation using QUILL's shared mic and speech services."""

from __future__ import annotations

import threading
import wave
from datetime import UTC, datetime
from typing import Any

from quill.core.dictation_owner import MicrophoneLock
from quill.core.speech.capture import MicRecorder
from quill.core.speech.service import load_input_device
from quill.core.speech.transcribe import transcribe_audio_file
from quill.core.storage import write_json_atomic
from quill.core.studio_capture import CaptureEvidence
from quill.stability.task_manager import CancellationToken


class ScreenshotNoteSession:
    def __init__(self) -> None:
        self.recorder = MicRecorder()
        self.microphone = MicrophoneLock("studio", key="Stop note recording")
        self.lock = threading.RLock()
        self.closed = False

    def start(self) -> None:
        with self.lock:
            if self.closed:
                raise RuntimeError("Note recording was cancelled.")
            refusal = self.microphone.take()
            if refusal:
                raise RuntimeError(refusal)
            try:
                self.recorder.start(load_input_device())
            except Exception:
                self.microphone.release()
                raise

    def finish(self, evidence: CaptureEvidence, token: CancellationToken) -> dict[str, Any]:
        with self.lock:
            if self.closed:
                raise RuntimeError("Note recording was cancelled.")
            path = self.recorder.stop()
            self.microphone.release()
        try:
            token.raise_if_cancelled()
            with wave.open(str(path), "rb") as recording:
                frames = recording.readframes(recording.getnframes())
            if not frames or not any(frames):
                raise ValueError("No sound was recorded. Check the microphone and try again.")
            result = transcribe_audio_file(path)
            token.raise_if_cancelled()
            record = {
                "schema_version": 1,
                "screenshot_sha256": evidence.sha256,
                "recorded_at": datetime.now(UTC).isoformat(),
                "text": result.full_text,
                "provider": result.provider_id,
                "model": result.model_id,
                "status": "Recognition unverified; review and correct before sharing",
                "audio_retained": False,
            }
            from pathlib import Path

            write_json_atomic(Path(evidence.path).with_suffix(".note.json"), record)
            return record
        finally:
            path.unlink(missing_ok=True)

    def close(self) -> None:
        with self.lock:
            self.closed = True
            try:
                if self.recorder.is_recording:
                    path = self.recorder.stop()
                    path.unlink(missing_ok=True)
            finally:
                self.microphone.release()
