"""The dictation transcription worker (extracted from the hotkeys mixin, GATE-11).

One job: given a finished capture, produce the transcript on a background
thread and call the controller back — with the reliability passes from the
2026-08-17 dictation work applied in order:

1. **Silence pre-pass** (:mod:`quill.core.speech.speech_vad`): quiet lead-in
   and tail are trimmed before any engine hears the audio, and an all-quiet
   take short-circuits to the controller's honest NO_SPEECH path without
   paying for a transcription that could only hallucinate (the Whisper
   silence-failure this pass exists to prevent).
2. **The engine** — whichever the dictation preference ladder resolved
   (an installed Parakeet 3 outranks the whisper.cpp default;
   ``service.preferred_dictation_provider_id`` holds the reasoning).
3. **Profile replacements** (``dictation.md`` spoken→written); the core
   controller then applies the vocabulary and filler refinement
   (:mod:`quill.core.speech.dictation.refine`) before insertion.

UI-thread discipline: everything here runs on a worker thread; every
controller callback and dialog touch marshals through ``wx.CallAfter``.
"""

from __future__ import annotations

import logging
import tempfile
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def resolve_dictation_provider(frame: Any) -> Any:
    """The cached dictation engine for *frame*, via the preference ladder.

    Caching lives on the frame (``_dictation_provider_cache``/``_key``) so a
    loaded model persists across sessions and a startup prewarm stays warm;
    the cache key is the user's explicit engine choice, so changing engines
    rebuilds. Resolution: an explicit choice always wins; otherwise an
    installed Parakeet 3 outranks the whisper.cpp default — the reasoning
    lives on ``service.preferred_dictation_provider_id``.
    """
    from quill.core.speech.service import preferred_dictation_provider_id

    chosen = str(getattr(frame.settings, "speech_provider", "") or "")
    cached = getattr(frame, "_dictation_provider_cache", None)
    if cached is not None and getattr(frame, "_dictation_provider_key", None) == chosen:
        return cached
    registry = frame._speech_registry()
    resolved = preferred_dictation_provider_id(registry, chosen)
    provider = registry.get(resolved) or frame._speech_provider(registry=registry)
    frame._dictation_provider_cache = provider
    frame._dictation_provider_key = chosen
    return provider


def start_transcription(frame: Any, session: Any) -> None:
    """Kick off the background transcription for *session* (fire-and-forget)."""
    controller = frame._live_dictation
    provider = frame._dictation_provider()
    installed = provider.list_installed_models()
    if not installed:
        controller.transcription_failed(session.session_id, "No speech model installed.")
        return
    model_id = frame._default_model_id(installed)
    audio_path = Path(session.audio_path) if session.audio_path else None
    session_id = session.session_id

    from quill.core.speech.dictation_profile import load_profile
    from quill.core.speech.provider import SpeechError, TranscriptionRequest

    # Dictation profile: vocabulary -> initial_prompt (engines that accept a
    # hint); the same vocabulary reaches every other engine via the fuzzy
    # corrector inside the controller's refine pass.
    profile = load_profile()
    prompt = profile.initial_prompt() or None
    request = TranscriptionRequest(source_path=audio_path, model_id=model_id, initial_prompt=prompt)
    asize = audio_path.stat().st_size if (audio_path and audio_path.exists()) else -1
    logger.info("dictation: transcribe model=%s audio size=%d bytes", model_id, asize)

    from quill.ui.ai_transcribe_dialog import AIProgressDialog

    wx = frame._wx
    cancel = threading.Event()
    progress = AIProgressDialog(
        frame.frame,
        "Transcribing dictation",
        "Transcribing your dictation...",
        on_cancel=cancel.set,
        # Quiet mirroring so a minimized run isn't chatty; the controller's
        # state feedback announces the start and the inserted word count.
        status_fn=frame._set_status_quiet,
    )
    progress.show()

    def _on_progress(fraction: float, message: str) -> None:
        if cancel.is_set():
            raise SpeechError("Transcription cancelled.")
        percent = int(max(0.0, min(1.0, fraction)) * 100)
        progress.set_progress(percent, f"{message} {percent}%")

    def _run() -> None:
        try:
            effective = request
            with tempfile.TemporaryDirectory(prefix="quill-dictation-vad-") as vad_tmp:
                from quill.core.speech.speech_vad import trim_for_transcription

                trim = trim_for_transcription(request.source_path, Path(vad_tmp))
                if trim.silent:
                    logger.info("dictation: VAD found no speech; engine skipped")
                    wx.CallAfter(progress.close)
                    wx.CallAfter(controller.transcription_succeeded, session_id, "")
                    return
                if trim.path != request.source_path:
                    logger.info("dictation: VAD trimmed %.1fs of silence", trim.trimmed_seconds)
                    # Trust-building, not chatter: a quiet status line the user
                    # can read on demand (F6 into the status bar) — never
                    # spoken unprompted (polish.md P4.4).
                    wx.CallAfter(
                        frame._set_status_quiet,
                        f"Trimmed {trim.trimmed_seconds:.0f}s of silence before transcribing.",
                    )
                    effective = replace(request, source_path=trim.path)
                result = provider.transcribe_file(effective, _on_progress)
            text = (getattr(result, "full_text", "") or "").strip()
            text = profile.apply_replacements(text)
            # The engine's own language detection (Parakeet 3), forwarded as
            # filler-gate evidence; effective_language() treats "auto" as none.
            detected = str(getattr(result, "language", "") or "")
            logger.info("dictation: transcription ok, %d chars: %r", len(text), text[:120])
        except Exception as exc:  # noqa: BLE001 - report failure to the controller
            logger.warning("dictation: transcription failed: %s", exc)
            wx.CallAfter(progress.close)
            wx.CallAfter(controller.transcription_failed, session_id, str(exc))
            return
        wx.CallAfter(progress.close)
        wx.CallAfter(controller.transcription_succeeded, session_id, text, detected)

    threading.Thread(  # GATE-40-OK: dictation transcription worker.
        target=_run, daemon=True
    ).start()
