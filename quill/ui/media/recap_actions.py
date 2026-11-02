"""Gather the text the media player's AI recaps are made from, off the UI thread.

The thin UI side of :mod:`quill.core.media.recap`. It builds the recap service
from QUILL's offline speech stack (ffmpeg clips the segment, the local speech
engine transcribes it) and runs the slow part -- finding the text -- on a
worker, handing the text back on the UI thread.

Sending it is not done here (codex.md 10E.8): ``quill.apps.player_ai`` sends
``recap_prompt(kind, text)`` to the AI the person chose, through the family's
shared service, which is where the reviewed network call lives. Nothing here
opens a socket, and the audio never leaves the computer.
"""

from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

#: Process-lifetime answers, per book and chapter, shared across invocations.
_CACHE: dict[str, str] = {}

BARD_REFUSAL = "AI summaries are not available for protected BARD content."


def is_protected(book_key: str) -> bool:
    """Whether *book_key* is protected BARD content, which no AI ever sees."""
    return book_key.startswith("bard:")


def recap_service() -> Any:
    """The recap service: the local transcriber when there is one, and the shared cache."""
    from quill.core.media import RecapService

    return RecapService(transcriber=_make_transcriber(), cache=_CACHE)


def gather_in_background(
    service: Any,
    ctx: Any,
    on_text: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    """Find *ctx*'s text on a worker; call *on_text* or *on_error* on the UI thread."""

    def work() -> None:
        try:
            text = service.text_for(ctx)
        except Exception as error:  # noqa: BLE001 - surfaced on the UI thread
            wx.CallAfter(on_error, str(error) or "No text was available to summarize.")
            return
        wx.CallAfter(on_text, text)

    threading.Thread(target=work, daemon=True).start()  # GATE-40-OK: media recap worker.


def _make_transcriber() -> Callable[[str, int, int], str] | None:
    try:
        from quill.core.speech.ffmpeg import find_ffmpeg
        from quill.core.speech.transcribe import has_installed_offline_model
    except Exception:  # noqa: BLE001 - speech stack absent -> no transcription path
        return None
    if not has_installed_offline_model() or not find_ffmpeg():
        return None

    def transcribe(audio_path: str, start_ms: int, duration_ms: int) -> str:
        clip = _clip_audio(audio_path, start_ms, duration_ms)
        try:
            from quill.core.speech.transcribe import transcribe_audio_file

            return transcribe_audio_file(Path(clip)).full_text
        finally:
            try:
                os.remove(clip)
            except OSError:
                pass

    return transcribe


def _clip_audio(audio_path: str, start_ms: int, duration_ms: int) -> str:
    """Clip a ``[start, start+duration]`` segment to a mono 16 kHz wav for Whisper."""
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available for transcription.")
    out = str(Path(tempfile.gettempdir()) / f"quill-recap-{os.getpid()}.wav")
    start_s = max(0, int(start_ms)) / 1000.0
    span_ms = duration_ms if duration_ms > 0 else 300_000
    # Cap at five minutes so transcription stays quick.
    dur_s = min(max(1_000, int(span_ms)) / 1000.0, 300.0)
    run_subprocess_safely(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{start_s:.3f}",
            "-t",
            f"{dur_s:.3f}",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            out,
        ],
        timeout_seconds=180.0,
    )
    return out


__all__ = ["BARD_REFUSAL", "gather_in_background", "is_protected", "recap_service"]
