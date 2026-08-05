"""Wire the media player's AI chapter recap to QUILL's AI + transcription stacks.

This is the thin UI adapter over the tested core in
:mod:`quill.core.media.recap`. It resolves the two injected collaborators from
QUILL's existing machinery -- the **summarizer** from the configured AI provider
(`quill.core.ai_chat.send_prompt`), and the optional **transcriber** from the
offline speech engine plus ffmpeg (clip the segment, transcribe it) -- then runs
the summary off the UI thread and speaks/shows the result.

Guardrails: never on protected BARD content, off in Safe Mode, and a clear
message when no AI provider (or no transcription engine, for pure audio) is set
up. The network call is inside the already-reviewed `ai_chat.send_prompt`
(GATE-9); nothing here opens a socket.
"""

from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

#: Process-lifetime summary cache shared across invocations.
_CACHE: dict[str, str] = {}


def summarize_current_chapter(
    host: Any,
    *,
    book_key: str,
    chapter_index: int,
    title: str,
    audio_path: str,
    start_ms: int,
    duration_ms: int,
) -> None:
    """Summarize the current chapter with the configured AI; speak/show the result."""
    _run_recap(
        host,
        kind="chapter",
        heading="Chapter Summary",
        starting="Summarizing this chapter.",
        book_key=book_key,
        chapter_index=chapter_index,
        title=title,
        audio_path=audio_path,
        start_ms=start_ms,
        duration_ms=duration_ms,
    )


def welcome_back_recap(
    host: Any,
    *,
    book_key: str,
    chapter_index: int,
    title: str,
    audio_path: str,
    start_ms: int,
    duration_ms: int,
) -> None:
    """AI recap of the passage up to the current point ("where am I / welcome back")."""
    _run_recap(
        host,
        kind="recap",
        heading="Recap",
        starting="Recapping where you are.",
        book_key=book_key,
        chapter_index=chapter_index,
        title=title,
        audio_path=audio_path,
        start_ms=start_ms,
        duration_ms=duration_ms,
    )


def _run_recap(
    host: Any,
    *,
    kind: str,
    heading: str,
    starting: str,
    book_key: str,
    chapter_index: int,
    title: str,
    audio_path: str,
    start_ms: int,
    duration_ms: int,
) -> None:
    if getattr(host, "_safe_mode", False):
        host._announce("AI summaries are off in Safe Mode.")
        return
    if book_key.startswith("bard:"):
        host._announce("AI summaries are not available for protected BARD content.")
        return

    from quill.core.media import ChapterContext, RecapService

    service = RecapService(
        _make_summarizer(host.settings), transcriber=_make_transcriber(), cache=_CACHE
    )
    ctx = ChapterContext(
        book_key=book_key or "book",
        chapter_index=chapter_index,
        title=title,
        text=None,
        audio_path=audio_path,
        start_ms=start_ms,
        duration_ms=duration_ms,
    )
    host._announce(f"{starting} This may take a moment.")
    summarize = service.chapter_summary if kind == "chapter" else service.welcome_back

    def work() -> None:
        try:
            result = summarize(ctx)
        except Exception as error:  # noqa: BLE001 - surfaced on the UI thread
            wx.CallAfter(_show_result, host, str(error), heading=heading, is_error=True)
            return
        wx.CallAfter(_show_result, host, result, heading=heading, is_error=False)

    threading.Thread(target=work, daemon=True).start()  # GATE-40-OK: media recap worker.


def _show_result(host: Any, text: str, *, heading: str, is_error: bool) -> None:
    text = (text or "").strip() or "No summary was produced."
    host._announce(text if is_error else f"{heading}: {text}")
    host._show_message_box(text, heading)


def _make_summarizer(settings: Any) -> Callable[[str], str]:
    def summarize(prompt: str) -> str:
        from quill.core.ai_chat import send_prompt
        from quill.platform.windows.credential_store import load_secret

        provider_id = (getattr(settings, "ai_chat_default_provider", "") or "").strip()
        model_id = (
            getattr(settings, "ai_prompt_default_model", "")
            or getattr(settings, "ai_chat_default_model", "")
            or ""
        ).strip()
        if not provider_id or not model_id:
            raise RuntimeError(
                "No AI provider is configured. Set one up in QUILL's AI Hub, then try again."
            )
        api_key = load_secret(f"quill-{provider_id}-api-key")
        return send_prompt(provider_id, model_id, prompt, api_key=api_key)

    return summarize


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


__all__ = ["summarize_current_chapter", "welcome_back_recap"]
