"""Every cloud speech provider QUILL can use with the person's own account.

The one list (D-31 to D-37), in the order the Speech Providers page shows it:
the three large clouds, then the streaming specialists, then the
phrase-at-a-time services, then IBM -- and OpenAI, which predates this layer
and keeps its own key in Use My Own AI Key.

**Engine ids.** A cloud provider is chosen as the speech engine under
``cloud-<provider id>`` ("cloud-azure"), so no provider can ever collide with
a downloadable model's id; OpenAI keeps ``openai``, which settings already
hold. :func:`engine_id_for` and :func:`provider_for_engine` are the only
places that know this.

**Where its settings are.** The plain fields live in
``windows_dictation_speech_providers`` (a mapping of provider id to its
fields) and the consent in ``windows_dictation_speech_provider_consent``
(provider id to version); secrets never do
(:mod:`~quill.core.windows_dictation.cloud.credentials`).

wx-free. Providers are imported on first use, never at QUILL's start.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from quill.core.windows_dictation.cloud.types import CloudProvider

__all__ = [
    "CONSENT_SETTING",
    "ENGINE_PREFIX",
    "FIELDS_SETTING",
    "consents_from",
    "engine_id_for",
    "engine_rows",
    "is_cloud_engine",
    "provider",
    "provider_for_engine",
    "providers",
    "stored_fields",
]

ENGINE_PREFIX = "cloud-"
FIELDS_SETTING = "windows_dictation_speech_providers"
CONSENT_SETTING = "windows_dictation_speech_provider_consent"

#: ``module:Class`` for each provider, in the page's order.
_PROVIDERS: tuple[str, ...] = (
    "azure:AzureSpeech",
    "google:GoogleSpeech",
    "amazon:AmazonTranscribe",
    "streaming_providers:Deepgram",
    "streaming_providers:AssemblyAI",
    "streaming_providers:Speechmatics",
    "streaming_more:ElevenLabsScribe",
    "streaming_more:Gladia",
    "streaming_more:RevAI",
    "rest_providers:Groq",
    "rest_providers:MistralVoxtral",
    "ibm:WatsonSpeech",
    "openai_provider:OpenAIProvider",
)


@lru_cache(maxsize=1)
def providers() -> tuple[CloudProvider, ...]:
    """Every provider, once each, in the page's order."""
    found: list[CloudProvider] = []
    for entry in _PROVIDERS:
        module_name, class_name = entry.split(":")
        try:
            module = importlib.import_module(f"quill.core.windows_dictation.cloud.{module_name}")
        except ImportError:  # pragma: no cover - every module ships
            continue
        found.append(getattr(module, class_name)())
    return tuple(found)


def provider(provider_id: str) -> CloudProvider | None:
    wanted = str(provider_id or "").strip().lower()
    return next((item for item in providers() if item.id == wanted), None)


def engine_id_for(provider_id: str) -> str:
    """The speech-engine id for *provider_id* (OpenAI keeps ``openai``)."""
    return provider_id if provider_id == "openai" else ENGINE_PREFIX + provider_id


def provider_for_engine(engine_id: str) -> CloudProvider | None:
    """The cloud provider *engine_id* names (``cloud-azure``), or None."""
    text = str(engine_id or "").strip().lower()
    if not text.startswith(ENGINE_PREFIX):
        return None
    return provider(text[len(ENGINE_PREFIX) :])


def is_cloud_engine(engine_id: str) -> bool:
    return provider_for_engine(engine_id) is not None


def _mapping(source: Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        value = source.get(name, {})
    else:
        value = getattr(source, name, {})
    return value if isinstance(value, Mapping) else {}


def stored_fields(source: Any, provider_id: str) -> dict[str, str]:
    """The plain (non-secret) fields saved for *provider_id* in *source*:
    a settings object or a settings mapping."""
    fields = _mapping(source, FIELDS_SETTING).get(provider_id, {})
    if not isinstance(fields, Mapping):
        return {}
    return {str(key): str(value) for key, value in fields.items() if value is not None}


def consents_from(source: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, value in _mapping(source, CONSENT_SETTING).items():
        try:
            out[str(key)] = int(str(value))
        except (TypeError, ValueError):
            continue
    return out


def engine_rows(source: Any, saved: str = "") -> list[tuple[str, str]]:
    """``(engine id, label)`` for each provider whose details are saved, and for
    *saved* when it names a provider whose details are not (so the list still
    shows what is chosen). OpenAI is listed by :func:`engines.engine_choices`."""
    from quill.core.windows_dictation.cloud.credentials import has_required, values_for

    rows: list[tuple[str, str]] = []
    for item in providers():
        if item.id == "openai":
            continue
        engine_id = engine_id_for(item.id)
        plain = stored_fields(source, item.id)
        try:  # the credential store is read only for a provider somebody saved
            ready = bool(plain) and has_required(item, values_for(item, plain))
        except Exception:  # noqa: BLE001 - an unreadable store is "not saved"
            ready = False
        if ready:
            rows.append((
                engine_id,
                f"{item.name} (your own account; sends your speech to {item.company})",
            ))
        elif engine_id == saved:
            rows.append((engine_id, f"{item.name} (not set up: open Speech Providers)"))
    return rows
