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
from quill.core.windows_dictation.profiles import DEFAULT_PROFILE, coerce_profile
from quill.core.windows_dictation.rescue import coerce_history_days
from quill.core.windows_dictation.speech_language import coerce_speech_language
from quill.core.windows_dictation.vocabulary import DASH_STYLES
from quill.core.windows_dictation.wake import DEFAULT_STOP_PHRASE, DEFAULT_WAKE_PHRASE

__all__ = [
    "FAMILY_LOCAL_FIELDS",
    "SHARE_FIELD",
    "DictationSettings",
    "load_fields",
    "settle_share",
    "share_on",
    "shares_by_default",
]

#: "Share dictation settings with every QuillVille program" (dict.md D-13, family_store.py).
SHARE_FIELD = "windows_dictation_share_family"
#: The dictation settings each program keeps to itself even when it shares:
#: the ones a program sets differently on purpose (the working tick and strict
#: mode in QUILL Transcribe, the read-back's tone where the screen reader
#: echoes the typing), the one-time sentence, and every consent -- agreeing to
#: send speech to a provider from one program is not agreeing for another.
FAMILY_LOCAL_FIELDS: frozenset[str] = frozenset({
    SHARE_FIELD,
    "windows_dictation_working_tick",
    "windows_dictation_command_prefix_required",
    "windows_dictation_phrase_feedback",
    "windows_dictation_openai_consent",
    "windows_dictation_review_consent",
    "windows_dictation_speech_provider_consent",
    "windows_dictation_transcript_told",
    # Keeping your words on this computer (D-5's opt-in history) is a choice
    # about what each program stores, like a consent: never shared.
    "windows_dictation_history_days",
})


def shares_by_default(data: Mapping[str, Any]) -> bool:
    """Sharing's default: on for a program whose shared dictation settings are
    all still the defaults (it has nothing to lose), off for one where the
    person changed any, so an upgrade never swaps somebody's choices for
    another program's behind their back. Absent fields count as defaults, so
    a raw file and a full set of fields give the same answer."""
    defaults = DictationSettings()
    return not any(
        name in data and data[name] != getattr(defaults, name)
        for name in DictationSettings.__dataclass_fields__
        if name not in FAMILY_LOCAL_FIELDS
    )


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
    # 2026-10-15 (D-2): review before inserting (review_session.py). Sending
    # every phrase to the review first is off; the consent to send reviewed
    # words to an AI provider is a version number, 0 for never asked; the
    # document's dictation context goes with a request only when this is on.
    windows_dictation_review_first: bool = False
    windows_dictation_review_consent: int = 0
    windows_dictation_review_context: bool = False
    # 2026-10-16 (D-5): days of dictation history kept, text only, sealed;
    # 0 (off) by default, and turning it off deletes it (rescue.py).
    windows_dictation_history_days: int = 0
    # 2026-10-16 (D-31): cloud speech providers with the person's own account
    # (quill/core/windows_dictation/cloud/). Only the plain fields -- region,
    # project, endpoint ID -- by provider id; secrets live in the credential
    # store, never here. The consent is a version per provider, 0 for never.
    windows_dictation_speech_providers: dict[str, dict[str, str]] = field(default_factory=dict)
    windows_dictation_speech_provider_consent: dict[str, int] = field(default_factory=dict)
    # 2026-10-16 (D-23): the named dictation profile (profiles.py), and the lock
    # that stops it being switched by voice.
    windows_dictation_profile: str = DEFAULT_PROFILE
    windows_dictation_profile_locked: bool = False
    # 2026-10-16 (D-20): keep the second of "Thursday, no, Friday" (self_repair.py),
    # and (P3) allow "polish that", one AI request in Review Dictation. Both off.
    windows_dictation_self_repair: bool = False
    windows_dictation_polish: bool = False
    # 2026-10-16 (D-13): share these with the family (family_store.py), "on"
    # or "off". Empty means not decided yet, and the loader decides it once
    # (shares_by_default) -- a text rather than a bool so that QUILL Lite,
    # which saves only what differs from the default, keeps the decision too.
    windows_dictation_share_family: str = ""


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
        "windows_dictation_review_first": bool(data.get("windows_dictation_review_first", False)),
        "windows_dictation_review_consent": _consent_version(
            data.get("windows_dictation_review_consent", 0)
        ),
        "windows_dictation_review_context": bool(
            data.get("windows_dictation_review_context", False)
        ),
        "windows_dictation_history_days": coerce_history_days(
            data.get("windows_dictation_history_days", 0)
        ),
        "windows_dictation_speech_providers": _provider_fields(
            data.get("windows_dictation_speech_providers")
        ),
        "windows_dictation_speech_provider_consent": _provider_consent(
            data.get("windows_dictation_speech_provider_consent")
        ),
        "windows_dictation_profile": coerce_profile(data.get("windows_dictation_profile")),
        "windows_dictation_profile_locked": bool(
            data.get("windows_dictation_profile_locked", False)
        ),
        "windows_dictation_self_repair": bool(data.get("windows_dictation_self_repair", False)),
        "windows_dictation_polish": bool(data.get("windows_dictation_polish", False)),
        SHARE_FIELD: _loaded_share(data),
    }


def _loaded_share(data: Mapping[str, Any]) -> str:
    """The saved choice; for a file without one, empty (still undecided, and
    sharing) while every shared setting is a default, else "off"."""
    value = data.get(SHARE_FIELD, "")
    if value in ("on", "off"):
        return str(value)
    if isinstance(value, bool):
        return "on" if value else "off"
    return "" if shares_by_default(data) else "off"


def settle_share(stored: Any) -> None:
    """Decide sharing for good, just before a shared setting changes, so that
    the change cannot itself turn an undecided "on" into "off". *stored* is a
    settings object or a stored dict."""
    if isinstance(stored, dict):
        if stored.get(SHARE_FIELD) not in ("on", "off"):
            stored[SHARE_FIELD] = "on" if share_on(stored) else "off"
        return
    current = getattr(stored, SHARE_FIELD, "")
    if current not in ("on", "off"):
        from quill.core.windows_dictation.anywhere import dictation_fields

        setattr(stored, SHARE_FIELD, "on" if share_on(dictation_fields(stored)) else "off")


def share_on(data: Mapping[str, Any]) -> bool:
    """Whether the settings *data* share with the family: the saved choice,
    or for a file that has none, :func:`shares_by_default`."""
    value = data.get(SHARE_FIELD, "")
    if value in ("on", True):
        return True
    if value in ("off", False):
        return False
    return shares_by_default(data)


#: Field names a secret might hide under. A settings file edited by hand, or
#: written by a build with a bug, never carries one of these back in (D-31).
_SECRET_WORDS = ("key", "secret", "token", "password")


def _provider_fields(value: object) -> dict[str, dict[str, str]]:
    """The plain fields per provider, as text; anything secret-shaped dropped."""
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, dict[str, str]] = {}
    for provider, fields in value.items():
        if not isinstance(fields, Mapping):
            continue
        kept = {
            str(name): str(text)
            for name, text in fields.items()
            if isinstance(text, (str, int, float))
            and not any(word in str(name).lower() for word in _SECRET_WORDS)
        }
        if kept:
            out[str(provider)] = kept
    return out


def _provider_consent(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(provider): version
        for provider, raw in value.items()
        if (version := _consent_version(raw)) > 0
    }


def _consent_version(value: object) -> int:
    """A saved consent version; anything unreadable is "never asked"."""
    try:
        return max(0, int(str(value)))
    except (TypeError, ValueError):
        return 0
