"""Shared F1 purposes for recording transcription surfaces."""

from __future__ import annotations

TRANSCRIPTION_PURPOSES: dict[str, str] = {
    "Transcribe a Recording": (
        "Choose a recording and model; transcription runs in the background and "
        "the finished text stays in Notifications."
    ),
    "Transcriptions on This Computer": (
        "Queued, running and finished recordings stay here across restarts. Open "
        "a transcript, retry or stop work, or forget a finished row."
    ),
}


__all__ = ["TRANSCRIPTION_PURPOSES"]
