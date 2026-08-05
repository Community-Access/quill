"""Hands-free voice capture for the Media Player (PRD Section 18).

The bridge between QUILL's offline speech stack (#617) and the media-command
grammar (:mod:`quill.core.media.voice`). Capture + transcription come from the
existing, shipping pieces -- :class:`~quill.core.speech.capture.MicRecorder` and a
small Whisper model via :class:`~quill.ui.voice_services.VoiceServices` -- so this
module only:

* resolves a provider + a *small* Whisper model for short commands
  (:func:`build_media_voice_services`), and
* turns a finished transcript into a :class:`VoiceFeedback` (event + phrase) by
  parsing and dispatching it (:func:`dispatch_transcript`).

The event model and its announce/earcon/interrupt styling follow the Desktop
Accessibility guidance: every state transition is independently perceivable
(spoken + earcon) and the styling table is pure data, unit-tested here. The wx
shell (the player app) owns the microphone toggle, the background thread, ducking
the audiobook, the reviewable status text, and the check-menu state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from quill.core.sound_events import SoundEvent

__all__ = [
    "VoiceCommandEvent",
    "VoiceFeedback",
    "build_media_voice_services",
    "dispatch_transcript",
    "event_style",
    "preferred_provider_ids",
    "resolve_provider_and_model",
]


class VoiceCommandEvent(StrEnum):
    """A discrete moment in the push-to-talk lifecycle (Desktop A11y model)."""

    LISTENING_START = "listening_start"
    TRANSCRIBING = "transcribing"
    RECOGNIZED_EXECUTED = "recognized_executed"
    NOT_RECOGNIZED = "not_recognized"
    NO_SPEECH = "no_speech"
    MIC_UNAVAILABLE = "mic_unavailable"
    ERROR = "error"
    CANCELLED = "cancelled"
    AUTO_STOPPED = "auto_stopped"


@dataclass(frozen=True, slots=True)
class VoiceFeedback:
    """What to announce for one lifecycle moment: an event and its phrase."""

    event: VoiceCommandEvent
    message: str


# force_speech (interrupt?) + the earcon to lead with, per event. Routine success
# queues politely (the earcon carries the moment); every failure interrupts so the
# user hears it immediately. Reuses the existing "Hey QUILL" conversation cues.
_EVENT_STYLE: dict[VoiceCommandEvent, tuple[bool, SoundEvent]] = {
    VoiceCommandEvent.LISTENING_START: (True, SoundEvent.CONVERSATION_LISTEN),
    VoiceCommandEvent.TRANSCRIBING: (True, SoundEvent.CONVERSATION_REVIEW),
    VoiceCommandEvent.RECOGNIZED_EXECUTED: (False, SoundEvent.CONVERSATION_READY),
    VoiceCommandEvent.NOT_RECOGNIZED: (True, SoundEvent.CONVERSATION_ERROR),
    VoiceCommandEvent.NO_SPEECH: (True, SoundEvent.CONVERSATION_IDLE),
    VoiceCommandEvent.MIC_UNAVAILABLE: (True, SoundEvent.CONVERSATION_ERROR),
    VoiceCommandEvent.ERROR: (True, SoundEvent.CONVERSATION_ERROR),
    VoiceCommandEvent.CANCELLED: (True, SoundEvent.CONVERSATION_OFF),
    VoiceCommandEvent.AUTO_STOPPED: (True, SoundEvent.CONVERSATION_IDLE),
}


def event_style(event: VoiceCommandEvent) -> tuple[bool, str]:
    """Return ``(force_speech, sound_event_name)`` for ``event``."""
    force, sound = _EVENT_STYLE.get(event, (True, SoundEvent.CONVERSATION_IDLE))
    return force, str(sound)


def dispatch_transcript(host: Any, transcript: str) -> VoiceFeedback:
    """Parse ``transcript`` as a media command, carry it out, and report back.

    Announces the *effect* on success (e.g. "Paused", "Bookmark added"); echoes
    what was heard on failure so the user can adjust their diction.
    """
    text = (transcript or "").strip()
    if not text:
        return VoiceFeedback(VoiceCommandEvent.NO_SPEECH, "No speech detected.")
    from quill.core.media.voice import parse_voice_command
    from quill.ui.media.voice_control import apply_voice_intent

    intent = parse_voice_command(text)
    if intent is None:
        return VoiceFeedback(
            VoiceCommandEvent.NOT_RECOGNIZED, f'Heard: "{text}". Command not recognized.'
        )
    result = apply_voice_intent(host, intent)
    return VoiceFeedback(VoiceCommandEvent.RECOGNIZED_EXECUTED, result or "Done.")


# Offline engines, in the order the player falls back through them when the user
# has not chosen one. whisper.cpp is the always-present default; Nemotron (the
# torch-free NVIDIA engine), Vosk, and Faster Whisper follow if installed.
_PROVIDER_FALLBACK = ("whispercpp", "nemotron", "vosk", "fasterwhisper")


def preferred_provider_ids(saved_provider: str = "") -> list[str]:
    """The order to try providers in: the user's saved engine first, then the
    offline fallback order, deduplicated."""
    order: list[str] = []
    saved = (saved_provider or "").strip()
    if saved:
        order.append(saved)
    for provider_id in _PROVIDER_FALLBACK:
        if provider_id not in order:
            order.append(provider_id)
    return order


def resolve_provider_and_model(registry: Any, saved_provider: str = "") -> tuple[Any, str]:
    """Pick the first usable provider (honouring ``saved_provider``) that has an
    installed model, and the best small model for it. ``(None, "")`` if none.

    Engine-agnostic: any registered provider works. For whisper.cpp this favours
    the small tiers; for Nemotron/Vosk (single-model packs) it takes what's
    installed.
    """
    from quill.core.speech.service import preferred_command_model

    try:
        available = {provider.id: provider for provider in registry.available()}
    except Exception:  # noqa: BLE001
        return None, ""
    order = preferred_provider_ids(saved_provider)
    order += [pid for pid in available if pid not in order]
    for provider_id in order:
        provider = available.get(provider_id)
        if provider is None:
            continue
        try:
            installed = [
                (getattr(model, "model_id", "") or getattr(model, "id", ""))
                for model in provider.list_installed_models()
            ]
        except Exception:  # noqa: BLE001 - a broken provider must not hide the rest
            continue
        installed = [model_id for model_id in installed if model_id]
        if installed:
            return provider, preferred_command_model(installed)
    return None, ""


def _saved_speech_provider() -> str:
    try:
        from quill.core.settings import load_settings

        return str(getattr(load_settings(), "speech_provider", "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def build_media_voice_services() -> Any | None:
    """Resolve a provider + model into a ``VoiceServices`` for hands-free capture.

    Returns ``None`` (never raises) when capture support, a usable provider, or an
    installed model is missing -- the caller treats ``None`` as "unavailable" and
    guides the user to install a speech model. Honours the engine the user chose
    in QUILL (``settings.speech_provider``), so Nemotron / Vosk / Faster Whisper
    are used when selected, falling back to whisper.cpp with a small, fast model.
    """
    try:
        from quill.core.speech.capture import capture_available

        if not capture_available():
            return None
        from quill.core.speech.service import default_registry, load_input_device

        provider, model_id = resolve_provider_and_model(
            default_registry(), _saved_speech_provider()
        )
        if provider is None or not model_id:
            return None
        from quill.ui.voice_services import VoiceServices

        return VoiceServices(
            stt_provider=provider,
            stt_model_id=model_id,
            device_index=load_input_device(),
        )
    except Exception:  # noqa: BLE001 - availability is decided by the caller (None)
        return None
