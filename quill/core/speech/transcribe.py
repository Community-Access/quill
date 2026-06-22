"""Offline file transcription entry point (WATCH-9, BITS Whisperer consolidation).

A thin, wx-free seam that transcribes a single audio/video file with the best
available *offline* speech provider (whisper.cpp or Faster Whisper). Callers that
just want "turn this file into text" -- the watch-folder transcribe action, and
any future batch caller -- use this instead of reaching into providers, models,
and the registry themselves.

Nothing here uploads anything: it only routes to the on-device engines already
registered by :func:`quill.core.speech.service.default_registry`.
"""

from __future__ import annotations

from pathlib import Path

from .provider import (
    SpeechError,
    SpeechToTextProvider,
    TranscriptionRequest,
    TranscriptionResult,
)
from .registry import SpeechProviderRegistry


def _default_registry() -> SpeechProviderRegistry:
    # Imported lazily so this module stays import-cheap and the heavy engines
    # load only when a transcription is actually requested.
    from .service import default_registry

    return default_registry()


def _is_offline(provider: SpeechToTextProvider) -> bool:
    """True for on-device providers. Network providers (Quillin cloud adapters)
    set ``requires_network = True`` and are skipped here so the offline transcribe
    paths never upload audio without explicit, consented UI."""
    return not getattr(provider, "requires_network", False)


def has_installed_offline_model(registry: SpeechProviderRegistry | None = None) -> bool:
    """Return True when some available offline provider has a model on disk.

    Cheap enough to call from a validate()/preview() path: it lists installed
    models but never loads an engine or transcribes. Network providers are
    excluded so a cloud Quillin never satisfies the offline path.
    """
    reg = registry if registry is not None else _default_registry()
    return any(
        provider.list_installed_models() for provider in reg.available() if _is_offline(provider)
    )


def _provider_and_model(
    registry: SpeechProviderRegistry, preferred_model_id: str | None
) -> tuple[SpeechToTextProvider, str]:
    """Pick an available provider and an installed model id to transcribe with.

    Prefers ``preferred_model_id`` when an available provider has it installed;
    otherwise uses the first installed model of the first available provider.
    Raises :class:`SpeechError` when no offline provider has a usable model.
    """
    for provider in registry.available():
        if not _is_offline(provider):
            continue  # cloud providers are used only via explicit consented UI
        installed = provider.list_installed_models()
        if not installed:
            continue
        if preferred_model_id:
            for model in installed:
                if model.id == preferred_model_id:
                    return provider, model.id
        return provider, installed[0].id
    raise SpeechError(
        "No offline speech model is installed. Open Tools > Speech > Whisperer > "
        "Manage Speech Models to download one, then try again."
    )


def transcribe_audio_file(
    source_path: Path,
    *,
    model_id: str | None = None,
    language: str | None = None,
    registry: SpeechProviderRegistry | None = None,
) -> TranscriptionResult:
    """Transcribe ``source_path`` with the best available offline provider.

    ``model_id`` is preferred when installed; otherwise the first installed model
    is used. Raises :class:`SpeechError` (or a subclass) when no offline provider
    with an installed model is available, or when the provider itself fails.
    """
    reg = registry if registry is not None else _default_registry()
    provider, resolved_model_id = _provider_and_model(reg, model_id)
    request = TranscriptionRequest(
        source_path=Path(source_path),
        model_id=resolved_model_id,
        language=language,
    )
    return provider.transcribe_file(request)


__all__ = [
    "has_installed_offline_model",
    "transcribe_audio_file",
]
