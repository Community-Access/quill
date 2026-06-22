"""Speech-to-text provider protocol and data model (#617 section 8.1).

Pure, wx-free types shared by every provider (whisper.cpp, Faster Whisper, cloud,
Windows). A provider is anything that satisfies :class:`SpeechToTextProvider`;
the registry (:mod:`quill.core.speech.registry`) holds the live instances and
imports heavy engines lazily.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

# A progress callback receives a fraction in [0.0, 1.0] and a short, speakable
# status message. Providers should call it sparingly (no per-token chatter).
ProgressCallback = Callable[[float, str], None]


@dataclass(frozen=True, slots=True)
class SpeechModelInfo:
    """A model the provider can offer for download."""

    id: str
    display_name: str
    language_mode: str  # "multilingual" | "english"
    approximate_size_mb: int
    accuracy_tier: str  # "low" | "medium" | "high" | "highest"
    speed_tier: str  # "fast" | "medium" | "slow"
    recommended_use: str
    download_url: str | None = None
    sha256: str | None = None
    # Optional MD5 integrity hash. Some model sources (e.g. Vosk on alphacephei)
    # publish MD5 rather than SHA-256; providers verify whichever they pin.
    md5: str | None = None
    license_name: str | None = None
    # Pinned Hugging Face commit SHA (Faster Whisper repos). whisper.cpp pins the
    # revision in download_url instead. Empty = follow the default branch.
    revision: str = ""


@dataclass(frozen=True, slots=True)
class InstalledSpeechModel:
    """A model present on disk."""

    id: str
    display_name: str
    path: Path
    size_mb: int
    provider_id: str
    sha256: str | None = None
    installed_at: str = ""


@dataclass(frozen=True, slots=True)
class SizeEstimate:
    """Approximate download and on-disk footprint for a model."""

    download_mb: int
    on_disk_mb: int


@dataclass(frozen=True, slots=True)
class ProviderInstallStatus:
    """Whether a provider's runtime is usable on this machine."""

    installed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class TranscriptionRequest:
    """A request to transcribe an audio/video file."""

    source_path: Path
    model_id: str
    language: str | None = None
    output_timestamps: bool = False
    translate_to_english: bool = False
    initial_prompt: str | None = None
    temperature: float | None = None
    diarize: bool = False  # mark speaker turns (needs a diarization-capable model)


@dataclass(frozen=True, slots=True)
class RecordingTranscriptionRequest:
    """A request to transcribe captured microphone audio (dictation)."""

    model_id: str
    language: str | None = None
    device_index: int | None = None


@dataclass(frozen=True, slots=True)
class TranscriptionSegment:
    """One timestamped span of transcribed text.

    ``speaker`` is a human-facing label ("Speaker 1") when speaker attribution
    (diarization) is available, else an empty string.
    """

    start_seconds: float
    end_seconds: float
    text: str
    speaker: str = ""


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """The outcome of a transcription."""

    full_text: str
    segments: tuple[TranscriptionSegment, ...] = ()
    provider_id: str = ""
    model_id: str = ""
    language: str | None = None
    duration_seconds: float | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


class SpeechError(Exception):
    """Base class for speech-provider failures (clear, user-facing messages)."""


class SpeechCancelledError(SpeechError):
    """Raised when a transcription or download was cancelled."""


@runtime_checkable
class SpeechToTextProvider(Protocol):
    """The contract every speech provider implements.

    Implementations keep all heavy imports inside their own methods so an
    uninstalled optional engine never breaks QUILL startup or other providers.
    """

    id: str
    display_name: str
    description: str

    def is_available(self) -> bool: ...
    def get_install_status(self) -> ProviderInstallStatus: ...
    def list_supported_models(self) -> list[SpeechModelInfo]: ...
    def list_installed_models(self) -> list[InstalledSpeechModel]: ...
    def estimate_model_size(self, model_id: str) -> SizeEstimate: ...
    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel: ...
    def remove_model(self, model_id: str) -> None: ...
    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult: ...
    def cancel(self) -> None: ...
    def unload(self) -> None: ...
