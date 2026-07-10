"""Native macOS speech synthesis (the macOS TTS backend, #2 / #62 / #75).

Two surfaces, one native engine:

- **Announcement self-voicing** (:func:`speak_announcement` /
  :func:`stop_announcement`): a persistent ``NSSpeechSynthesizer`` singleton
  driven with the non-blocking ``startSpeakingString_``. This is the macOS
  equivalent of the Windows SAPI5 self-voicing fallback in
  ``prism_bridge.py`` -- it gives a low-vision Mac user running *without*
  VoiceOver audible announcements instead of silently swallowing them. It runs
  on the UI thread (where the announce dispatch lives); ``startSpeakingString_``
  returns immediately and speaks in the background, so it never blocks the UI.
  `` NSSpeechSynthesizer`` is used directly (not the ``say`` CLI) so a per-call
  process spawn and its latency are avoided for frequent short announcements.
- **Voice catalog** (:func:`list_voices`): the system voice list from
  ``NSSpeechSynthesizer.availableVoices()``, used by both the announcement voice
  picker and the read-aloud engine. The same voice identifiers are accepted by
  the ``say`` CLI, so the read-aloud runner (``quill.core.read_aloud._run_macos_live``)
  shells out to ``say`` -- safe on the read-aloud worker thread where
  instantiating an AppKit object off the main thread would be unsafe.

pyobjc is imported lazily inside each function (mirroring ``macos/announce.py``)
so the module imports cleanly on non-macOS / pyobjc-less machines and every
function degrades to ``False`` / ``[]`` / no-op.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MacosVoice:
    """One installed macOS voice (parallels the SAPI voice option shape)."""

    id: str
    name: str
    language: str = ""


def available() -> bool:
    """True when native macOS speech (``NSSpeechSynthesizer``) can be reached."""
    if sys.platform != "darwin":
        return False
    try:
        import AppKit  # type: ignore[import-not-found]

        AppKit.NSSpeechSynthesizer  # noqa: B018 - attribute presence is the probe
    except Exception:  # noqa: BLE001 - any failure means native TTS is unusable
        return False
    return True


def list_voices() -> list[MacosVoice]:
    """Return the installed macOS system voices (empty list when unavailable)."""
    try:
        import AppKit  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return []
    synth_cls = AppKit.NSSpeechSynthesizer
    try:
        raw_voices = synth_cls.availableVoices()
    except Exception:  # noqa: BLE001
        return []
    out: list[MacosVoice] = []
    for voice in raw_voices:
        vid = str(voice)
        name = vid
        language = ""
        try:
            attrs = synth_cls.attributesForVoice_(voice)
            if attrs:
                attrs_map = dict(attrs)
                name = str(attrs_map.get("VoiceName", vid))
                language = str(
                    attrs_map.get("VoiceLocaleIdent", attrs_map.get("VoiceLanguage", ""))
                )
        except Exception:  # noqa: BLE001 - per-voice attribute lookup is best-effort
            pass
        out.append(MacosVoice(id=vid, name=name, language=language))
    return out


# Persistent synthesizer for the announcement self-voice. Built lazily on first
# use and reused so frequent short announcements don't pay per-call init cost.
_synth: object = None


def _get_synth(voice: str | None = None, rate: int | None = None) -> object:
    """Return the cached ``NSSpeechSynthesizer``, applying *voice*/*rate* if given."""
    global _synth
    import AppKit  # type: ignore[import-not-found]

    if _synth is None:
        _synth = AppKit.NSSpeechSynthesizer.alloc().init()
    if voice:
        _synth.setVoice_(voice)  # type: ignore[union-attr]
    if rate is not None:
        _synth.setRate_(float(rate))  # type: ignore[union-attr]
    return _synth


def speak_announcement(text: str, *, voice: str | None = None, rate: int | None = None) -> bool:
    """Speak *text* via ``NSSpeechSynthesizer`` (non-blocking). Returns True if dispatched.

    For the self-voicing fallback when VoiceOver is off. ``startSpeakingString_``
    returns immediately and the system speaks in the background, so this is safe
    to call on the UI thread. A new call interrupts any in-progress utterance
    (matching the Windows SAPI fallback's interrupt semantics).
    """
    if not text:
        return False
    try:
        synth = _get_synth(voice, rate)
    except Exception:  # noqa: BLE001 - pyobjc missing or AppKit unreachable
        return False
    try:
        return bool(synth.startSpeakingString_(text))  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        return False


def stop_announcement() -> None:
    """Stop any in-progress self-voiced announcement (best-effort)."""
    if _synth is None:
        return
    try:
        _synth.stopSpeaking()  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
