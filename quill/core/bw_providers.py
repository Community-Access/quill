from __future__ import annotations

from dataclasses import dataclass

from quill.core.bw_speech import downloaded_model_ids, faster_whisper_status


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    id: str
    name: str
    provider_type: str  # local | cloud
    requires_api_key: bool
    description: str
    best_for: str


@dataclass(frozen=True, slots=True)
class ProviderReadiness:
    provider_id: str
    ready: bool
    summary: str
    next_steps: tuple[str, ...]


_PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        id="local_whisper",
        name="Local Whisper (faster-whisper)",
        provider_type="local",
        requires_api_key=False,
        description="On-device transcription using faster-whisper.",
        best_for="Privacy-first and offline-friendly workflows.",
    ),
    ProviderSpec(
        id="openai_whisper",
        name="OpenAI Whisper API",
        provider_type="cloud",
        requires_api_key=True,
        description="Cloud transcription with simple API integration.",
        best_for="Fast cloud setup with managed inference.",
    ),
    ProviderSpec(
        id="deepgram",
        name="Deepgram",
        provider_type="cloud",
        requires_api_key=True,
        description="Cloud transcription provider optimized for speed.",
        best_for="Realtime-heavy or low-latency cloud scenarios.",
    ),
    ProviderSpec(
        id="assemblyai",
        name="AssemblyAI",
        provider_type="cloud",
        requires_api_key=True,
        description="Cloud transcription with analytics and enrichment options.",
        best_for="Richer cloud post-processing workflows.",
    ),
    ProviderSpec(
        id="azure_speech",
        name="Azure Speech",
        provider_type="cloud",
        requires_api_key=True,
        description="Microsoft Azure speech transcription service.",
        best_for="Microsoft-centric enterprise environments.",
    ),
)


def list_providers(*, include_cloud: bool = True) -> list[ProviderSpec]:
    providers = list(_PROVIDERS)
    if include_cloud:
        return providers
    return [provider for provider in providers if provider.provider_type == "local"]


def get_provider(provider_id: str, *, include_cloud: bool = True) -> ProviderSpec | None:
    for provider in list_providers(include_cloud=include_cloud):
        if provider.id == provider_id:
            return provider
    return None


def recommended_provider_id(*, local_first: bool = True) -> str:
    if not local_first:
        return "openai_whisper"

    fw_ok, _ = faster_whisper_status()
    model_ids = downloaded_model_ids()
    if fw_ok and bool(model_ids):
        return "local_whisper"
    return "openai_whisper"


def provider_readiness(provider_id: str, *, local_first: bool = True) -> ProviderReadiness:
    provider = get_provider(provider_id)
    if provider is None:
        return ProviderReadiness(
            provider_id=provider_id,
            ready=False,
            summary="Provider is unknown.",
            next_steps=("Select a valid provider from BITS Whisperer menu.",),
        )

    if provider.id == "local_whisper":
        fw_ok, fw_status = faster_whisper_status()
        model_ids = downloaded_model_ids()
        if fw_ok and bool(model_ids):
            return ProviderReadiness(
                provider_id=provider.id,
                ready=True,
                summary="Local whisper provider is ready.",
                next_steps=("No further setup required in phase 1.",),
            )
        steps: list[str] = []
        if not fw_ok:
            steps.append(fw_status)
        if not model_ids:
            steps.append(
                "Download at least one whisper model from BITS Whisperer -> Speech Models."
            )
        return ProviderReadiness(
            provider_id=provider.id,
            ready=False,
            summary="Local whisper needs setup.",
            next_steps=tuple(steps),
        )

    # Cloud providers remain onboarding-only in this phase.
    recommendation = recommended_provider_id(local_first=local_first)
    if recommendation != provider.id:
        summary = f"{provider.name} is available for later phases."
    else:
        summary = f"{provider.name} is recommended for your current setup mode."
    return ProviderReadiness(
        provider_id=provider.id,
        ready=False,
        summary=summary,
        next_steps=(
            "Cloud provider runtime wiring is intentionally staged for later phases.",
            "Keep using model and provider setup flows for now.",
        ),
    )


def provider_mode_guidance(*, local_first: bool) -> str:
    if local_first:
        return "Provider mode: Local-first. QUILL will recommend local whisper when machine-ready."
    return "Provider mode: Cloud-first. QUILL will recommend cloud providers for setup planning."
