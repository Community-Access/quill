"""More streaming providers over one WebSocket each: ElevenLabs Scribe, Gladia, Rev.ai (D-35).

The same shape as :mod:`~quill.core.windows_dictation.cloud.streaming_providers`:
each is a :class:`~quill.core.windows_dictation.cloud.ws_base.SocketAdapter`
plus the provider's facts, and every network call happens at the provider's
own call site (``_probe_*``, ``_init_*``, ``_connect_*``), so the egress audit
names each provider's fixed host.

Protocol facts, checked 2026-10-16 against each provider's public reference;
anything not confirmed there is marked **verify**:

* **ElevenLabs Scribe** realtime,
  ``wss://api.elevenlabs.io/v1/speech-to-text/realtime`` with ``model_id=
  scribe_v2_realtime``, ``audio_format=pcm_16000``, ``language_code``,
  ``commit_strategy=manual`` and one ``keyterms`` parameter per word (**verify**
  the limit: QUILL sends at most 50 words of 20 characters or less); the key
  in the ``xi-api-key`` header. Audio goes as JSON ``input_audio_chunk``
  messages with base64 audio; the same message with ``"commit": true`` and no
  audio ends the phrase now. Answers ``partial_transcript`` and
  ``committed_transcript``; any ``message_type`` naming an error is one
  (**verify** these message names). Test: ``GET /v1/user``. The key may be
  the one QUILL already keeps for ElevenLabs voices (Credential Manager,
  "ElevenLabs API key").
* **Gladia** live v2: an init ``POST https://api.gladia.io/v2/live`` with the
  key in ``x-gladia-key`` returns a session ``url``, which must be ``wss`` on
  a ``gladia.io`` host; the socket to it carries no other credential. Region
  ``eu-west`` or ``us-west`` as a ``region`` query parameter on the init call
  (**verify**). My Words go as ``custom_vocabulary_config`` with an
  ``intensity`` of 0.5 (**verify** the range). Answers ``transcript`` messages
  with ``data.is_final``; ``stop_recording`` ends. Test: ``GET /v2/live?limit=1``.
* **Rev.ai** streaming, ``wss://api.rev.ai/speechtotext/v1/stream``. **The
  access token goes in the query string** (``access_token``), because that is
  Rev.ai's streaming protocol: it has no header for it. The query travels
  inside the TLS connection and is never logged or said by QUILL. A custom
  vocabulary is used by its id (the person creates it in their Rev.ai account;
  QUILL creates nothing there). Answers ``partial`` and ``final`` hypotheses
  of ``elements``; ``EOS`` ends. Test: ``GET /speechtotext/v1/account``.

wx-free.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.errors import CloudFieldError, CloudSpeechError
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    LiveSession,
    ProviderField,
    Values,
)
from quill.core.windows_dictation.cloud.ws_base import Heard, SocketAdapter, SocketSession

__all__ = ["ElevenLabsScribe", "Gladia", "RevAI"]

#: Where QUILL's ElevenLabs voices keep their key (Windows Credential Manager).
_ELEVENLABS_TARGET = "ElevenLabs API key"
_ELEVENLABS_TERMS = 50  # verify
_ELEVENLABS_TERM_CHARS = 20  # verify


def _short_language(language: str) -> str:
    return (language or "en").split("-")[0].strip().lower() or "en"


# -- ElevenLabs Scribe -------------------------------------------------------------- #


def _shared_elevenlabs_key() -> str:
    """The key QUILL already keeps for ElevenLabs voices, or ``""``. Never logged."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential

        stored = load_generic_credential(_ELEVENLABS_TARGET)
        return str((stored.secret if stored else "") or "")
    except Exception:  # noqa: BLE001 - an unreadable store is "no key"
        return ""


class _ElevenLabsAdapter(SocketAdapter):
    name = "ElevenLabs"
    keepalive_seconds = 10.0
    settle_seconds = 4.0

    def _chunk(self, pcm: bytes, *, commit: bool = False) -> str:
        message: dict[str, Any] = {
            "message_type": "input_audio_chunk",
            "audio_base_64": base64.b64encode(pcm).decode("ascii"),
            "sample_rate": self.rate,
        }
        if commit:
            message["commit"] = True
        return json.dumps(message)

    def audio(self, pcm: bytes) -> str:
        return self._chunk(pcm)

    def finish_phrase(self) -> Sequence[str]:
        return (self._chunk(b"", commit=True),)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        kind = str(event.get("message_type", ""))
        if "error" in kind.lower():
            detail = event.get("error") or event.get("message") or kind
            return Heard(error=f"ElevenLabs reported a problem: {detail}.")
        text = str(event.get("text", "") or "")
        if kind == "partial_transcript":
            return Heard(partial=text)
        if kind == "committed_transcript":
            return Heard(final=text, settled=True)
        return Heard()


class ElevenLabsScribe(CloudProvider):
    id = "elevenlabs"
    name = "ElevenLabs Scribe"
    short_name = "ElevenLabs"
    company = "ElevenLabs"
    console_url = "https://elevenlabs.io/app/usage"
    privacy_url = "https://elevenlabs.io/privacy-policy"
    hosts = ("api.elevenlabs.io",)
    description = (
        "ElevenLabs Scribe realtime: live words while you speak, and up to 50 of your "
        "words as keyterms. It can use the key already saved for ElevenLabs voices."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField(
                "key",
                "Key",
                "secret",
                required=False,
                help=(
                    "Your ElevenLabs API key, from the ElevenLabs website, API Keys. Kept "
                    "in Windows Credential Manager, never in QUILL's settings. Leave this "
                    "empty to use the key already saved for ElevenLabs voices, or to keep "
                    "the key already saved here."
                ),
            ),
        )

    def fallback_secret(self, key: str) -> str:
        """The key saved for ElevenLabs voices, when none is saved here."""
        return _shared_elevenlabs_key() if key == "key" else ""

    def problem(self, values: Values) -> CloudFieldError | None:
        if not str(values.get("key", "") or "").strip():
            return CloudFieldError(
                "Key is empty, and no key is saved for ElevenLabs voices. Fill in Key.",
                field="Key",
            )
        return super().problem(values)

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True, biasing_limit=_ELEVENLABS_TERMS, biasing_name="keyterms"
        )

    def test(self, values: Values) -> str:
        return self._probe_elevenlabs(values)

    def _probe_elevenlabs(self, values: Values) -> str:
        request = Request(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": str(values.get("key", ""))},
            method="GET",
        )
        with transport.failing_as(self.short_name):
            with transport.urlopen(request, timeout=15) as response:
                transport.read_json(response)
        return "ElevenLabs answered: ready."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        query: list[tuple[str, str]] = [
            ("model_id", "scribe_v2_realtime"),
            ("audio_format", "pcm_16000"),
            ("language_code", _short_language(language)),
            ("commit_strategy", "manual"),
        ]
        kept = [term for term in terms if len(term) <= _ELEVENLABS_TERM_CHARS]
        query += [("keyterms", term) for term in kept[:_ELEVENLABS_TERMS]]
        url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?" + urlencode(query)
        key = str(values.get("key", ""))
        return SocketSession(
            _ElevenLabsAdapter(), lambda: self._connect_elevenlabs(url, key), on_delta=on_delta
        )

    def _connect_elevenlabs(self, url: str, key: str) -> Any:
        return transport.create_connection(url, {"xi-api-key": key})


# -- Gladia ------------------------------------------------------------------------- #

_GLADIA_REGIONS = (("eu-west", "European Union"), ("us-west", "United States"))


def _gladia_socket_url(url: str) -> str:
    """*url* when it is a ``wss`` address on Gladia's own domain; refused otherwise."""
    parts = urlsplit(str(url or "").strip())
    host = (parts.hostname or "").lower()
    if parts.scheme != "wss" or not (host == "gladia.io" or host.endswith(".gladia.io")):
        raise CloudSpeechError(
            "Gladia answered with an address that is not Gladia's own, so QUILL sent nothing to it."
        )
    return str(url).strip()


class _GladiaAdapter(SocketAdapter):
    name = "Gladia"
    settle_seconds = 3.0

    def closing(self) -> Sequence[str]:
        return (json.dumps({"type": "stop_recording"}),)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        kind = str(event.get("type", ""))
        if kind == "error" or (kind != "transcript" and event.get("error")):
            detail = event.get("error") or event.get("message") or "unknown"
            if isinstance(detail, dict):
                detail = detail.get("message") or "unknown"
            return Heard(error=f"Gladia reported a problem: {detail}.")
        if kind != "transcript":
            return Heard()
        data = event.get("data") or {}
        text = str((data.get("utterance") or {}).get("text", "") or "")
        if data.get("is_final"):
            return Heard(final=text)
        return Heard(partial=text)


class Gladia(CloudProvider):
    id = "gladia"
    name = "Gladia"
    short_name = "Gladia"
    company = "Gladia"
    console_url = "https://app.gladia.io"
    privacy_url = "https://www.gladia.io/privacy-policy"
    hosts = ("api.gladia.io",)
    description = (
        "Gladia live: words while you speak, in the EU or the US, with up to 100 of your words."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField(
                "key",
                "Key",
                "secret",
                help=(
                    "Your Gladia API key, from the Gladia app, API Keys. Kept in Windows "
                    "Credential Manager, never in QUILL's settings; leave this empty to "
                    "keep the key already saved."
                ),
            ),
            ProviderField(
                "region",
                "Region",
                "choice",
                required=False,
                default="eu-west",
                choices=_GLADIA_REGIONS,
                help="Where Gladia hears your speech: the European Union, or the United States.",
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, biasing_limit=100, biasing_name="custom vocabulary")

    def _region(self, values: Values) -> str:
        region = str(values.get("region") or "eu-west")
        return region if region in dict(_GLADIA_REGIONS) else "eu-west"

    def where(self, values: Values) -> str:
        return "the United States" if self._region(values) == "us-west" else "the European Union"

    def test(self, values: Values) -> str:
        return self._probe_gladia(values)

    def _probe_gladia(self, values: Values) -> str:
        request = Request(
            "https://api.gladia.io/v2/live?limit=1",
            headers={"x-gladia-key": str(values.get("key", ""))},
            method="GET",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                transport.read_json(response)
        return "Gladia answered: ready."

    def _session_body(self, language: str, terms: Sequence[str]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "encoding": "wav/pcm",
            "sample_rate": 16000,
            "bit_depth": 16,
            "channels": 1,
            "language_config": {"languages": [_short_language(language)], "code_switching": False},
            "messages_config": {"receive_partial_transcripts": True},
        }
        if terms:
            body["realtime_processing"] = {
                "custom_vocabulary": True,
                "custom_vocabulary_config": {
                    "vocabulary": [{"value": term, "intensity": 0.5} for term in terms[:100]]
                },
            }
        return body

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        key = str(values.get("key", ""))
        region = self._region(values)
        body = self._session_body(language, terms)
        return SocketSession(
            _GladiaAdapter(),
            lambda: self._connect_gladia(self._init_gladia(key, region, body)),
            on_delta=on_delta,
        )

    def _init_gladia(self, key: str, region: str, body: dict[str, Any]) -> str:
        """Ask Gladia for a live session; its socket address, checked."""
        request = Request(
            "https://api.gladia.io/v2/live?" + urlencode({"region": region}),
            data=json.dumps(body).encode("utf-8"),
            headers={"x-gladia-key": key, "Content-Type": "application/json"},
            method="POST",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                data = transport.read_json(response)
        url = data.get("url", "") if isinstance(data, dict) else ""
        return _gladia_socket_url(str(url or ""))

    def _connect_gladia(self, url: str) -> Any:
        return transport.create_connection(url)


# -- Rev.ai ------------------------------------------------------------------------- #

_REV_CONTENT_TYPE = "audio/x-raw;layout=interleaved;rate=16000;format=S16LE;channels=1"


def _rev_text(elements: Any, *, final: bool) -> str:
    """The words of a Rev.ai hypothesis. Final elements carry their own spaces
    and punctuation; partial elements are words, joined with spaces."""
    if not isinstance(elements, list):
        return ""
    if not final:
        words = [str(item.get("value", "")) for item in elements if isinstance(item, dict)]
        return " ".join(word.strip() for word in words if word.strip())
    out = ""
    for item in elements:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", "") or "")
        if item.get("type") == "punct":
            out += value
        elif value:
            if out and not out[-1].isspace():
                out += " "
            out += value
    return " ".join(out.split())


class _RevAdapter(SocketAdapter):
    name = "Rev.ai"
    auth_field = "Access token"
    settle_seconds = 3.0

    def closing(self) -> Sequence[str]:
        return ("EOS",)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        kind = str(event.get("type", ""))
        if kind == "error":
            detail = event.get("message") or event.get("error") or "unknown"
            return Heard(error=f"Rev.ai reported a problem: {detail}.")
        if kind == "partial":
            return Heard(partial=_rev_text(event.get("elements"), final=False))
        if kind == "final":
            return Heard(final=_rev_text(event.get("elements"), final=True))
        return Heard()  # "connected", and anything new


class RevAI(CloudProvider):
    id = "revai"
    name = "Rev.ai"
    short_name = "Rev.ai"
    company = "Rev"
    console_url = "https://www.rev.ai/account"
    privacy_url = "https://www.rev.com/about/privacy"
    hosts = ("api.rev.ai",)
    description = (
        "Rev.ai streaming: live words while you speak, with a custom vocabulary from "
        "your Rev.ai account."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField(
                "token",
                "Access token",
                "secret",
                help=(
                    "Your Rev.ai access token, from your Rev.ai account, Access Token. Kept "
                    "in Windows Credential Manager, never in QUILL's settings; leave this "
                    "empty to keep the token already saved."
                ),
            ),
            ProviderField(
                "vocabulary",
                "Custom vocabulary ID",
                "text",
                required=False,
                help=(
                    "The ID of a custom vocabulary to use, or blank for none. Create the "
                    "vocabulary in your Rev.ai account first: QUILL does not create "
                    "resources in anybody's account."
                ),
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            biasing_limit=0,
            biasing_name="custom vocabulary",
            languages="English and some other languages",
        )

    def test(self, values: Values) -> str:
        return self._probe_revai(values)

    def _probe_revai(self, values: Values) -> str:
        request = Request(
            "https://api.rev.ai/speechtotext/v1/account",
            headers={"Authorization": f"Bearer {values.get('token', '')}"},
            method="GET",
        )
        with transport.failing_as(self.name, auth_field="Access token"):
            with transport.urlopen(request, timeout=15) as response:
                transport.read_json(response)
        return "Rev.ai answered: ready."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        del language, terms  # Rev.ai takes a saved vocabulary by id, not a word list
        query: list[tuple[str, str]] = [
            ("access_token", str(values.get("token", ""))),
            ("content_type", _REV_CONTENT_TYPE),
        ]
        vocabulary = str(values.get("vocabulary", "") or "").strip()
        if vocabulary:
            query.append(("custom_vocabulary_id", vocabulary))
        # Rev.ai's own clients send the content type's ";" "/" and "=" unescaped.
        url = "wss://api.rev.ai/speechtotext/v1/stream?" + urlencode(
            query, safe="/;=", quote_via=quote
        )
        return SocketSession(_RevAdapter(), lambda: self._connect_revai(url), on_delta=on_delta)

    def _connect_revai(self, url: str) -> Any:
        return transport.create_connection(url)
