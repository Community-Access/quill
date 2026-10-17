"""Phrase-at-a-time providers over plain HTTPS: Groq and Mistral Voxtral (D-36).

Neither gives words while you speak, so neither shows a live preview: each
finished phrase the voice detector heard goes as one short WAV, as OpenAI's
non-live path does, and the text comes back.

* **Groq** (Whisper), ``https://api.groq.com/openai/v1/audio/transcriptions``,
  OpenAI-compatible, ``Authorization: Bearer``; ``whisper-large-v3-turbo`` by
  default; My Words go as Whisper's ``prompt`` (**verify** in Groq's reference
  that the prompt is honoured). Test: ``GET /openai/v1/models``. The same
  endpoint and key as QUILL's file-transcription ``groq`` RestSpec
  (``quill/core/speech/cloud_transcribers.py``).
* **Mistral Voxtral**, ``https://api.mistral.ai/v1/audio/transcriptions``,
  ``Authorization: Bearer``; ``voxtral-mini-latest``; My Words as
  ``context_bias``, up to 100, one form part each (documented for batch; the
  multipart spelling is **verify**). Voxtral Realtime waits until its protocol
  and biasing are verified. Test: ``GET /v1/models``.

wx-free.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    ProviderField,
    Values,
)
from quill.core.windows_dictation.cloud.wire import multipart, wav_bytes

__all__ = ["Groq", "MistralVoxtral"]


def _key_field(where: str) -> ProviderField:
    return ProviderField(
        "key",
        "Key",
        "secret",
        help=(
            f"Your API key, from {where}. Kept in Windows Credential Manager, never in "
            "QUILL's settings; leave this empty to keep the key already saved."
        ),
    )


def _model_field(default: str, provider: str) -> ProviderField:
    return ProviderField(
        "model",
        "Model",
        "text",
        required=False,
        default=default,
        help=f"The {provider} speech model. Blank uses {default}.",
    )


def _text(data: Any) -> str:
    return str(data.get("text", "") if isinstance(data, dict) else "").strip()


def _models(data: Any) -> int:
    return len(data.get("data", []) or []) if isinstance(data, dict) else 0


class Groq(CloudProvider):
    id = "groq"
    name = "Groq"
    short_name = "Groq"
    company = "Groq"
    console_url = "https://console.groq.com/settings/usage"
    privacy_url = "https://groq.com/privacy-policy"
    hosts = ("api.groq.com",)
    description = "Groq runs Whisper very fast: one phrase at a time, no live preview."

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            _key_field("the Groq console, API Keys"),
            _model_field("whisper-large-v3-turbo", "Groq"),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=False, biasing_limit=40, biasing_name="prompt")

    def test(self, values: Values) -> str:
        return self._probe_groq(values)

    def _probe_groq(self, values: Values) -> str:
        request = Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {values.get('key', '')}"},
            method="GET",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                count = _models(transport.read_json(response))
        return f"Groq answered: ready, {count} models."

    def phrase(self, values: Values, samples: Any, *, language: str, terms: Sequence[str]) -> str:
        return self._send_groq(values, wav_bytes(samples), language, terms)

    def _send_groq(self, values: Values, audio: bytes, language: str, terms: Sequence[str]) -> str:
        fields = [
            ("model", str(values.get("model") or "whisper-large-v3-turbo")),
            ("response_format", "json"),
            ("temperature", "0"),
        ]
        if language:
            fields.append(("language", language.split("-")[0]))
        if terms:
            fields.append(("prompt", ", ".join(terms)))
        body, content_type = multipart(fields, [("file", "phrase.wav", "audio/wav", audio)])
        request = Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {values.get('key', '')}",
                "Content-Type": content_type,
            },
            method="POST",
        )
        with transport.failing_as(self.name, place_field="Model"):
            with transport.urlopen(request, timeout=30) as response:
                return _text(transport.read_json(response))


class MistralVoxtral(CloudProvider):
    id = "mistral"
    name = "Mistral Voxtral"
    short_name = "Mistral"
    company = "Mistral AI"
    console_url = "https://console.mistral.ai/usage"
    privacy_url = "https://mistral.ai/terms"
    hosts = ("api.mistral.ai",)
    description = (
        "Mistral's Voxtral, in the EU: one phrase at a time, no live preview, "
        "up to 100 of your words."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            _key_field("the Mistral console, API Keys"),
            _model_field("voxtral-mini-latest", "Mistral"),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=False, biasing_limit=100, biasing_name="context_bias")

    def where(self, values: Values) -> str:
        del values
        return "the European Union"

    def test(self, values: Values) -> str:
        return self._probe_mistral(values)

    def _probe_mistral(self, values: Values) -> str:
        request = Request(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {values.get('key', '')}"},
            method="GET",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                count = _models(transport.read_json(response))
        return f"Mistral answered: ready, {count} models."

    def phrase(self, values: Values, samples: Any, *, language: str, terms: Sequence[str]) -> str:
        return self._send_mistral(values, wav_bytes(samples), language, terms)

    def _send_mistral(
        self, values: Values, audio: bytes, language: str, terms: Sequence[str]
    ) -> str:
        fields = [("model", str(values.get("model") or "voxtral-mini-latest"))]
        if language:
            fields.append(("language", language.split("-")[0]))
        fields += [("context_bias", term) for term in terms[:100]]
        body, content_type = multipart(fields, [("file", "phrase.wav", "audio/wav", audio)])
        request = Request(
            "https://api.mistral.ai/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {values.get('key', '')}",
                "Content-Type": content_type,
            },
            method="POST",
        )
        with transport.failing_as(self.name, place_field="Model"):
            with transport.urlopen(request, timeout=30) as response:
                return _text(transport.read_json(response))
