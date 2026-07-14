"""Host adapters for Quillin-contributed cloud transcription providers.

A Quillin may *declare* a transcription provider (the ``transcription_providers``
manifest contribution). It never performs the upload itself -- the QUILL host
runs a vetted adapter here, under the network-egress audit, using the existing
``quill.core.ai.transcription`` machinery. The sandbox therefore never touches
audio bytes or the API key.

Every adapter here sets ``requires_network = True`` so the *offline* paths
(``quill.core.speech.transcribe`` and the offline Watch Folder transcribe action)
skip it: cloud transcription only happens through explicit, consented UI.

The host loader populates the process-wide active set via
:func:`set_quillin_transcription_providers` when Quillins are enabled, and clears
it in Safe Mode / on disable, mirroring how other Quillin contributions apply.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from quill.core.quillins.model import TranscriptionProviderContribution

from .provider import (
    InstalledSpeechModel,
    ProgressCallback,
    ProviderInstallStatus,
    SizeEstimate,
    SpeechError,
    SpeechModelInfo,
    SpeechToTextProvider,
    TranscriptionRequest,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)

#: The virtual model id cloud providers report (they have no on-disk models).
_CLOUD_MODEL_ID = "cloud"


def _resolve_api_key(credential_label: str) -> str | None:
    """Return the API key for ``credential_label`` (or the OpenAI default).

    Kept as a module function so tests can monkeypatch it without real secrets.
    """
    if credential_label:
        try:
            from quill.platform.windows.credential_manager import load_generic_credential

            stored = load_generic_credential(credential_label)
            return stored.secret or None if stored is not None else None
        except Exception:  # noqa: BLE001 - missing/locked store is "no key", not a crash
            return None
    # Default: reuse the assistant's OpenAI key wiring.
    try:
        from quill.core.assistant_ai import load_assistant_api_key

        return load_assistant_api_key() or None
    except Exception:  # noqa: BLE001
        return None


def _safe_mode_active() -> bool:
    # Process-level, matching the offline providers and the assistant network gate.
    import os

    return os.environ.get("QUILL_SAFE_MODE") == "1"


class _CloudProviderBase:
    """Shared behavior for host-mediated, network-backed cloud providers.

    Implements :class:`SpeechToTextProvider` except :meth:`transcribe_file` (the
    per-provider call). Cloud providers have no downloadable models; they report a
    single virtual "cloud" model when a key is configured so they are selectable in
    the transcribe UI, and are unavailable in Safe Mode or without a key.
    """

    requires_network = True

    def __init__(self, contribution: TranscriptionProviderContribution) -> None:
        self.id = contribution.id
        self.display_name = contribution.display_name
        self.description = (
            contribution.description or f"Cloud transcription via {contribution.display_name}."
        )
        self._credential_label = contribution.credential
        self._max_file_mb = contribution.max_file_mb

    # -- availability ----------------------------------------------------

    def is_available(self) -> bool:
        if _safe_mode_active():
            return False
        return _resolve_api_key(self._credential_label) is not None

    def get_install_status(self) -> ProviderInstallStatus:
        if _safe_mode_active():
            return ProviderInstallStatus(installed=False, detail="Disabled in Safe Mode.")
        if _resolve_api_key(self._credential_label) is None:
            return ProviderInstallStatus(
                installed=False,
                detail="No API key configured for this provider.",
            )
        return ProviderInstallStatus(installed=True, detail="Cloud provider ready.")

    # -- models (virtual; nothing is downloaded) -------------------------

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return [
            SpeechModelInfo(
                id=_CLOUD_MODEL_ID,
                display_name=f"{self.display_name} (cloud)",
                language_mode="multilingual",
                approximate_size_mb=0,
                accuracy_tier="high",
                speed_tier="fast",
                recommended_use="Cloud transcription; requires an API key and consent.",
            )
        ]

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        # A cloud provider is "ready" when a key is set; surface one virtual model
        # so it is selectable in the transcribe UI. The path is a placeholder --
        # nothing on disk is read for cloud providers.
        if _resolve_api_key(self._credential_label) is None:
            return []
        return [
            InstalledSpeechModel(
                id=_CLOUD_MODEL_ID,
                display_name=f"{self.display_name} (cloud)",
                path=Path(self.id),
                size_mb=0,
                provider_id=self.id,
            )
        ]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:  # noqa: ARG002
        return SizeEstimate(download_mb=0, on_disk_mb=0)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:  # noqa: ARG002
        raise SpeechError("Cloud providers have no downloadable models.")

    def remove_model(self, model_id: str) -> None:  # noqa: ARG002
        raise SpeechError("Cloud providers have no downloadable models.")

    # -- transcription ---------------------------------------------------

    def _checked_key(self, path: Path, default_limit_mb: float) -> str:
        """Enforce the upload-size ceiling and return the API key, or raise."""
        limit = int((self._max_file_mb or default_limit_mb) * 1024 * 1024)
        size = path.stat().st_size if path.exists() else 0
        if size > limit:
            raise SpeechError(
                f"{path.name} is {size / (1024 * 1024):.1f} MB, over the "
                f"{limit / (1024 * 1024):.0f} MB cloud limit for {self.display_name}."
            )
        api_key = _resolve_api_key(self._credential_label)
        if not api_key:
            raise SpeechError(f"No API key configured for {self.display_name}.")
        return api_key

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:
        raise NotImplementedError

    def cancel(self) -> None:  # pragma: no cover - no cancellation for a single REST call
        pass

    def unload(self) -> None:  # pragma: no cover - nothing to unload
        pass


class OpenAiWhisperProvider(_CloudProviderBase):
    """Cloud transcription via OpenAI Whisper (kind ``openai_whisper``).

    Routes through ``quill.core.ai.transcription`` (GATE-9 reviewed egress).
    """

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:  # noqa: ARG002
        from quill.core.ai.transcription import (
            SUPPORTED_AUDIO_EXTENSIONS,
            TranscriptionError,
            transcribe_file,
        )

        path = Path(request.source_path)
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise SpeechError(
                f"{path.name} is not a supported audio format for cloud transcription."
            )
        api_key = self._checked_key(path, 25.0)
        try:
            text = transcribe_file(path, api_key, language=request.language)
        except TranscriptionError as exc:
            raise SpeechError(str(exc)) from exc
        return TranscriptionResult(full_text=text, provider_id=self.id, model_id=_CLOUD_MODEL_ID)


class RestCloudProvider(_CloudProviderBase):
    """Generic cloud provider for any kind described in ``CLOUD_REST_SPECS``.

    The host performs the REST call via ``cloud_transcribers.transcribe_rest`` under
    the network-egress audit; the kind selects the vetted endpoint spec.
    """

    def __init__(self, contribution: TranscriptionProviderContribution) -> None:
        super().__init__(contribution)
        from .cloud_transcribers import CLOUD_REST_SPECS

        self._spec = CLOUD_REST_SPECS[contribution.kind]

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:  # noqa: ARG002
        from .cloud_transcribers import CloudTranscribeError, transcribe_rest

        path = Path(request.source_path)
        api_key = self._checked_key(path, self._spec.max_file_mb)
        try:
            text = transcribe_rest(
                self._spec,
                path,
                api_key,
                language=request.language,
                diarize=request.diarize,
            )
        except CloudTranscribeError as exc:
            raise SpeechError(str(exc)) from exc
        return TranscriptionResult(full_text=text, provider_id=self.id, model_id=_CLOUD_MODEL_ID)


#: Maps a contribution ``kind`` to the host adapter that implements it.
_ADAPTERS: dict[str, Callable[[TranscriptionProviderContribution], SpeechToTextProvider]] = {
    "openai_whisper": OpenAiWhisperProvider,
}

# Every config-driven REST kind (Groq, ElevenLabs, ...) is served by the one
# generic RestCloudProvider, which selects its endpoint spec by ``kind``.
from .cloud_transcribers import CLOUD_REST_SPECS as _CLOUD_REST_SPECS  # noqa: E402

for _kind in _CLOUD_REST_SPECS:
    _ADAPTERS.setdefault(_kind, RestCloudProvider)

#: Process-wide active set, populated by the Quillin loader.
_ACTIVE: list[SpeechToTextProvider] = []


def build_provider(
    contribution: TranscriptionProviderContribution,
) -> SpeechToTextProvider | None:
    """Build a host provider for ``contribution``, or None for an unknown kind."""
    adapter = _ADAPTERS.get(contribution.kind)
    if adapter is None:
        logger.warning("No host adapter for transcription provider kind %r", contribution.kind)
        return None
    return adapter(contribution)


def set_quillin_transcription_providers(
    contributions: Sequence[TranscriptionProviderContribution],
) -> None:
    """Replace the active set from enabled Quillins' provider contributions.

    Called by the host loader on enable/disable and at startup; Safe Mode passes
    an empty sequence so no cloud providers are offered.
    """
    providers: list[SpeechToTextProvider] = []
    for contribution in contributions:
        provider = build_provider(contribution)
        if provider is not None:
            providers.append(provider)
    _ACTIVE[:] = providers


def register_quillin_transcription_providers(manifests: Sequence[object]) -> None:
    """Set the active providers from every manifest's contributions.

    Convenience for the host loader: collects each manifest's
    ``contributes.transcription_providers`` and replaces the active set. An empty
    or provider-less manifest list clears the set (disable / no Quillins).
    """
    contributions: list[TranscriptionProviderContribution] = []
    for manifest in manifests:
        contributes = getattr(manifest, "contributes", None)
        contributions.extend(getattr(contributes, "transcription_providers", ()) or ())
    set_quillin_transcription_providers(contributions)


def clear_quillin_transcription_providers() -> None:
    """Drop all Quillin-contributed providers (Safe Mode, shutdown)."""
    _ACTIVE.clear()


def quillin_transcription_providers() -> list[SpeechToTextProvider]:
    """Return the currently active Quillin-contributed providers."""
    return list(_ACTIVE)


__all__ = [
    "OpenAiWhisperProvider",
    "build_provider",
    "clear_quillin_transcription_providers",
    "quillin_transcription_providers",
    "register_quillin_transcription_providers",
    "set_quillin_transcription_providers",
]
