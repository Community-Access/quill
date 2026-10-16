"""Dictation's settings as QUILL's settings loader reads them from JSON.

Shared with QUILL Lite twice over: the fields themselves are declared once,
here, as :class:`DictationSettings`, which both editors' ``Settings`` inherit
(2026-10-05 -- before then each declared its own copy, and the two lists were
kept equal by hand), and they are cleaned once, by :func:`load_fields`, which
QUILL's loader and QUILL Lite's ``normalized`` both call. Parsed here rather
than inline in :func:`quill.core.settings.load_settings` (GATE-11: that module
is a single hand-written loader at its size budget).

wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.action_feedback import coerce as coerce_feedback
from quill.core.windows_dictation.command_mode import (
    DEFAULT_COMMAND_PREFIX,
    DEFAULT_COMMAND_TIMEOUT,
    coerce_prefix,
    coerce_timeout,
)
from quill.core.windows_dictation.engines import coerce_engine
from quill.core.windows_dictation.never_type import DEFAULT_NEVER_TYPE, coerce_never_type
from quill.core.windows_dictation.options import coerce_pause, coerce_silence
from quill.core.windows_dictation.preview import coerce_preview
from quill.core.windows_dictation.speech_language import coerce_speech_language
from quill.core.windows_dictation.vocabulary import DASH_STYLES
from quill.core.windows_dictation.wake import DEFAULT_STOP_PHRASE, DEFAULT_WAKE_PHRASE

__all__ = ["DictationSettings", "load_fields"]


@dataclass(slots=True)
class DictationSettings:
    """Tools > Dictation's settings, in both editors, under one set of names.

    Meanings are in :mod:`~quill.core.windows_dictation.preferences`.
    """

    windows_dictation_microphone: str = ""
    windows_dictation_engine: str = "moonshine"
    windows_dictation_language: str = ""
    windows_dictation_speech_language: str = "en"
    windows_dictation_dash: str = "em"
    windows_dictation_wake_enabled: bool = False
    windows_dictation_wake_phrase: str = "Quill dictate"
    windows_dictation_stop_phrase: str = "stop dictation"
    windows_dictation_phrase_feedback: str = "both"
    windows_dictation_cue_sounds: bool = True
    windows_dictation_announce: bool = True
    windows_dictation_pause: str = "normal"
    windows_dictation_remove_fillers: bool = False
    windows_dictation_auto_punctuation: bool = True
    windows_dictation_silence_minutes: int = 0
    windows_dictation_continuous: bool = False
    # 2026-10-05: hold-to-talk, the live preview, Talking to AI, and OpenAI.
    windows_dictation_hold_to_talk: bool = False
    windows_dictation_preview: str = "show"
    windows_dictation_ai_send: str = "pause"
    windows_dictation_ai_pause: str = "long"
    windows_dictation_ai_remove_fillers: bool = True
    windows_dictation_ai_auto_punctuation: bool = True
    windows_dictation_openai_model: str = ""
    windows_dictation_openai_consent: bool = False
    # 2026-10-05, the gap plan: marks said in the read-back, transcript times,
    # and the one-time sentence about recording other people.
    windows_dictation_readback_marks: bool = True
    windows_dictation_transcript_timestamps: bool = False
    windows_dictation_transcript_told: bool = False
    # 2026-10-13 (D-17): a soft tick while a heard phrase is still being
    # recognised. Off in both editors; QUILL Transcribe turns it on
    # (quill/core/transcribe/settings.py, TRANSCRIBE_DICTATION_DEFAULTS).
    windows_dictation_working_tick: bool = False
    # 2026-10-13 (D-24): programs dictation never types into, by file name
    # (never_type.py). Starts as the password managers; the person can change it.
    windows_dictation_never_type: list[str] = field(
        default_factory=lambda: list(DEFAULT_NEVER_TYPE)
    )
    # 2026-10-15 (D-1): the command word, strict mode and command mode's
    # timeout (command_mode.py). Strict mode is off in both editors; QUILL
    # Transcribe turns it on (TRANSCRIBE_DICTATION_DEFAULTS).
    windows_dictation_command_prefix: str = DEFAULT_COMMAND_PREFIX
    windows_dictation_command_prefix_required: bool = False
    windows_dictation_command_timeout: int = DEFAULT_COMMAND_TIMEOUT


def load_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    """The ``windows_dictation_*`` fields from saved settings *data*, cleaned."""
    dash = str(data.get("windows_dictation_dash", "em") or "em")
    return {
        "windows_dictation_microphone": str(data.get("windows_dictation_microphone", "") or ""),
        "windows_dictation_engine": coerce_engine(data.get("windows_dictation_engine", "")),
        "windows_dictation_language": str(data.get("windows_dictation_language", "") or ""),
        "windows_dictation_speech_language": coerce_speech_language(
            data.get("windows_dictation_speech_language", "en")
        ),
        "windows_dictation_dash": dash if dash in DASH_STYLES else "em",
        "windows_dictation_wake_enabled": bool(data.get("windows_dictation_wake_enabled", False)),
        "windows_dictation_wake_phrase": str(
            data.get("windows_dictation_wake_phrase", "") or DEFAULT_WAKE_PHRASE
        ),
        "windows_dictation_stop_phrase": str(
            data.get("windows_dictation_stop_phrase", "") or DEFAULT_STOP_PHRASE
        ),
        "windows_dictation_phrase_feedback": str(
            coerce_feedback(data.get("windows_dictation_phrase_feedback", "both"))
        ),
        "windows_dictation_cue_sounds": bool(data.get("windows_dictation_cue_sounds", True)),
        "windows_dictation_announce": bool(data.get("windows_dictation_announce", True)),
        "windows_dictation_pause": coerce_pause(data.get("windows_dictation_pause", "normal")),
        "windows_dictation_remove_fillers": bool(
            data.get("windows_dictation_remove_fillers", False)
        ),
        "windows_dictation_auto_punctuation": bool(
            data.get("windows_dictation_auto_punctuation", True)
        ),
        "windows_dictation_silence_minutes": coerce_silence(
            data.get("windows_dictation_silence_minutes", 0)
        ),
        "windows_dictation_continuous": bool(data.get("windows_dictation_continuous", False)),
        # 2026-10-05: hold-to-talk, the live preview, Talking to AI, OpenAI.
        "windows_dictation_hold_to_talk": bool(data.get("windows_dictation_hold_to_talk", False)),
        "windows_dictation_preview": coerce_preview(data.get("windows_dictation_preview", "show")),
        "windows_dictation_ai_send": (
            "enter" if data.get("windows_dictation_ai_send") == "enter" else "pause"
        ),
        "windows_dictation_ai_pause": coerce_pause(data.get("windows_dictation_ai_pause", "long")),
        "windows_dictation_ai_remove_fillers": bool(
            data.get("windows_dictation_ai_remove_fillers", True)
        ),
        "windows_dictation_ai_auto_punctuation": bool(
            data.get("windows_dictation_ai_auto_punctuation", True)
        ),
        "windows_dictation_openai_model": str(data.get("windows_dictation_openai_model", "") or ""),
        "windows_dictation_openai_consent": bool(
            data.get("windows_dictation_openai_consent", False)
        ),
        "windows_dictation_readback_marks": bool(
            data.get("windows_dictation_readback_marks", True)
        ),
        "windows_dictation_transcript_timestamps": bool(
            data.get("windows_dictation_transcript_timestamps", False)
        ),
        "windows_dictation_transcript_told": bool(
            data.get("windows_dictation_transcript_told", False)
        ),
        "windows_dictation_working_tick": bool(data.get("windows_dictation_working_tick", False)),
        "windows_dictation_never_type": coerce_never_type(data.get("windows_dictation_never_type")),
        "windows_dictation_command_prefix": coerce_prefix(
            data.get("windows_dictation_command_prefix", DEFAULT_COMMAND_PREFIX)
        ),
        "windows_dictation_command_prefix_required": bool(
            data.get("windows_dictation_command_prefix_required", False)
        ),
        "windows_dictation_command_timeout": coerce_timeout(
            data.get("windows_dictation_command_timeout", DEFAULT_COMMAND_TIMEOUT)
        ),
    }
