"""Hold-to-Dictate and Locked Dictation controller (wx-free core).

This package implements the keyboard-driven dictation feature (Hold-to-Dictate on
F9, Locked Dictation on Ctrl+F9). It is the
pure-domain half of the feature: an explicit state machine
(:class:`DictationController`), the session/insertion-context records, the
conservative insertion normalization, and the crash-recovery repository. It
never imports ``wx`` and performs no microphone or transcription I/O itself —
the wx shell injects those as a small :class:`DictationServices` callback bundle
so the controller stays deterministic and unit-testable.

The companion module ``quill.core.dictation`` is a *different*, older feature
(it launches the Windows Win+H dictation panel); do not confuse the two.
"""

from __future__ import annotations

from quill.core.speech.dictation.controller import (
    DictationController,
    DictationServices,
)
from quill.core.speech.dictation.insertion import normalize_for_insertion
from quill.core.speech.dictation.recovery import (
    DictationRecoveryRepository,
    RecoveredSession,
)
from quill.core.speech.dictation.session import DictationSession, InsertionContext
from quill.core.speech.dictation.states import (
    ACTIVE_RECORDING_STATES,
    DictationMode,
    DictationState,
    is_valid_transition,
)

__all__ = [
    "ACTIVE_RECORDING_STATES",
    "DictationController",
    "DictationMode",
    "DictationRecoveryRepository",
    "DictationServices",
    "DictationSession",
    "DictationState",
    "InsertionContext",
    "RecoveredSession",
    "is_valid_transition",
    "normalize_for_insertion",
]
