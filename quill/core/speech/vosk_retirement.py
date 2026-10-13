"""Loading a saved Vosk choice after Vosk left dictation and the voice features.

On 2026-10-13 Vosk stopped being a dictation engine and a voice-features engine.
It stays, bundled, as the podcast chapter engine (``service.CHAPTER_PROVIDER_ID``),
because it scored best there (0.372 against Whisper medium's 0.316). For the
other two roles it is English only, its last release was in 2022 and its models
are checked by MD5 only, while the bundled Moonshine tiny is faster and more
accurate.

:func:`migrate_vosk_choices` is what ``Settings.from_dict`` calls: a saved voice
recognition engine of ``"vosk"`` becomes ``"moonshine_tiny"``, and (because the
dictation engine validation no longer accepts it) a saved ``speech_provider`` of
``"vosk"`` becomes ``""``, the default ladder. Neither happens silently: the
returned notice state is ``"voice"`` or ``"dictation"`` until
:mod:`quill.ui.vosk_retirement_notice` has said so once, then ``"done"``.
"""

from __future__ import annotations

from collections.abc import Mapping

VOICE_ENGINES = frozenset({"", "whispercpp", "moonshine_tiny"})
_NOTICE_STATES = frozenset({"", "voice", "dictation", "done"})


def _text(data: Mapping[str, object], key: str) -> str:
    return str(data.get(key, "") or "").strip().lower()


def migrate_vosk_choices(data: Mapping[str, object]) -> tuple[str, str]:
    """``(voice_recognition_engine, vosk_retirement_notice)`` for saved *data*."""
    voice = _text(data, "voice_recognition_engine")
    notice = _text(data, "vosk_retirement_notice")
    if notice not in _NOTICE_STATES:
        notice = ""
    retired = "dictation" if _text(data, "speech_provider") == "vosk" else ""
    if voice == "vosk":
        voice, retired = "moonshine_tiny", "voice"
    if voice not in VOICE_ENGINES:
        voice = ""
    if retired and notice in {"", "dictation"}:
        notice = retired
    return voice, notice
