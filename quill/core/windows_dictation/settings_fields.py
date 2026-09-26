"""Dictation's settings as QUILL's settings loader reads them from JSON.

Nine fields, shared by name with QUILL Lite. Parsed here rather than inline in
:func:`quill.core.settings.load_settings` (GATE-11: that module is a single
hand-written loader at its size budget), and returned as keyword arguments for
the :class:`~quill.core.settings.Settings` constructor. QUILL Lite's settings
parse the same fields by type, so the two cannot disagree about a value.

wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.action_feedback import coerce as coerce_feedback
from quill.core.windows_dictation.engines import coerce_engine
from quill.core.windows_dictation.options import coerce_pause, coerce_silence
from quill.core.windows_dictation.vocabulary import DASH_STYLES
from quill.core.windows_dictation.wake import DEFAULT_STOP_PHRASE, DEFAULT_WAKE_PHRASE

__all__ = ["load_fields"]


def load_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    """The ``windows_dictation_*`` fields from saved settings *data*, cleaned."""
    dash = str(data.get("windows_dictation_dash", "em") or "em")
    return {
        "windows_dictation_microphone": str(data.get("windows_dictation_microphone", "") or ""),
        "windows_dictation_engine": coerce_engine(data.get("windows_dictation_engine", "")),
        "windows_dictation_language": str(data.get("windows_dictation_language", "") or ""),
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
    }
