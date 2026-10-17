"""Streaming providers over one WebSocket each: Deepgram, AssemblyAI, Speechmatics (D-35).

Each is a :class:`~quill.core.windows_dictation.cloud.ws_base.SocketAdapter`
(what to send, what the answers mean) plus the provider's facts. The socket is
opened at each provider's own call site (``_connect``), so the egress audit
names each provider's fixed host.

Protocol facts, checked 2026-10-16 against each provider's public reference;
anything not confirmed there is marked **verify** in the design record
(section 23):

* **Deepgram**, ``wss://api.deepgram.com/v1/listen``, ``Authorization: Token``;
  Nova-3; ``keyterm`` once per word (up to 100); ``interim_results``;
  ``Finalize`` ends the phrase now, ``KeepAlive`` holds an idle connection,
  ``CloseStream`` ends. Test: ``GET /v1/projects``.
* **AssemblyAI** Universal Streaming v3,
  ``wss://streaming.assemblyai.com/v3/ws`` (EU: ``streaming.eu.assemblyai.com``),
  ``Authorization`` with the key; ``keyterms_prompt`` (a JSON list, up to 100
  terms of 50 characters or less); audio blocks of 50 to 1,000 ms;
  ``ForceEndpoint`` ends the turn now; ``Terminate`` ends. Test: a temporary
  streaming token (``GET /v3/token``), which sends no audio.
* **Speechmatics** real-time v2, ``wss://eu2.rt.speechmatics.com/v2`` or
  ``us2``, ``Authorization: Bearer``; ``StartRecognition`` with
  ``additional_vocab`` (**verify** the current schema), ``enable_partials``;
  ``AddPartialTranscript`` / ``AddTranscript``; ``EndOfStream``. Test:
  ``GET https://asr.api.speechmatics.com/v2/jobs``.

wx-free.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    LiveSession,
    ProviderField,
    Values,
    locale_for,
)
from quill.core.windows_dictation.cloud.ws_base import Heard, SocketAdapter, SocketSession

__all__ = ["AssemblyAI", "Deepgram", "Speechmatics"]


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


# -- Deepgram -------------------------------------------------------------------- #


class _DeepgramAdapter(SocketAdapter):
    name = "Deepgram"
    keepalive_seconds = 5.0

    def keepalive(self) -> str:
        return json.dumps({"type": "KeepAlive"})

    def finish_phrase(self) -> Sequence[str]:
        return (json.dumps({"type": "Finalize"}),)

    def closing(self) -> Sequence[str]:
        return (json.dumps({"type": "CloseStream"}),)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        kind = str(event.get("type", ""))
        if kind == "Error" or "err_msg" in event:
            return Heard(
                error="Deepgram reported a problem: "
                + f"{event.get('description') or event.get('err_msg') or 'unknown'}."
            )
        if kind != "Results":
            return Heard()
        alternatives = (event.get("channel") or {}).get("alternatives") or [{}]
        text = str(alternatives[0].get("transcript", "") or "")
        if event.get("is_final"):
            return Heard(final=text, settled=bool(event.get("from_finalize")))
        return Heard(partial=text)


class Deepgram(CloudProvider):
    id = "deepgram"
    name = "Deepgram"
    short_name = "Deepgram"
    company = "Deepgram"
    console_url = "https://console.deepgram.com"
    privacy_url = "https://deepgram.com/privacy"
    hosts = ("api.deepgram.com",)
    description = (
        "Deepgram Nova-3: fast live words while you speak, and it learns up to 100 of your words."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            _key_field("the Deepgram console, API Keys"),
            ProviderField(
                "model",
                "Model",
                "text",
                required=False,
                default="nova-3",
                help="The Deepgram model. Blank uses nova-3, which takes your words as keyterms.",
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            biasing_limit=100,
            biasing_name="keyterm",
            diarization=True,
            timestamps=True,
        )

    def test(self, values: Values) -> str:
        return self._probe_deepgram(values)

    def _probe_deepgram(self, values: Values) -> str:
        request = Request(
            "https://api.deepgram.com/v1/projects",
            headers={"Authorization": f"Token {values.get('key', '')}"},
            method="GET",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                data = transport.read_json(response)
        count = len(data.get("projects", []) or []) if isinstance(data, dict) else 0
        return f"Deepgram answered: ready, {count} project{'s' if count != 1 else ''}."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        query: list[tuple[str, str]] = [
            ("model", str(values.get("model") or "nova-3")),
            ("encoding", "linear16"),
            ("sample_rate", "16000"),
            ("channels", "1"),
            ("interim_results", "true"),
            ("punctuate", "true"),
            ("smart_format", "true"),
            ("language", locale_for(language)),
        ]
        query += [("keyterm", term) for term in terms[:100]]
        url = "wss://api.deepgram.com/v1/listen?" + urlencode(query)
        key = str(values.get("key", ""))
        return SocketSession(
            _DeepgramAdapter(), lambda: self._connect_deepgram(url, key), on_delta=on_delta
        )

    def _connect_deepgram(self, url: str, key: str) -> Any:
        return transport.create_connection(url, {"Authorization": f"Token {key}"})


# -- AssemblyAI ------------------------------------------------------------------ #

_ASSEMBLY_HOSTS = {"us": "streaming.assemblyai.com", "eu": "streaming.eu.assemblyai.com"}


class _AssemblyAdapter(SocketAdapter):
    name = "AssemblyAI"
    min_chunk_ms = 100
    keepalive_seconds = 10.0

    def finish_phrase(self) -> Sequence[str]:
        return (json.dumps({"type": "ForceEndpoint"}),)

    def closing(self) -> Sequence[str]:
        return (json.dumps({"type": "Terminate"}),)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        kind = str(event.get("type", ""))
        if kind == "Error" or "error" in event:
            return Heard(error=f"AssemblyAI reported a problem: {event.get('error') or 'unknown'}.")
        if kind != "Turn":
            return Heard()
        text = str(event.get("transcript", "") or "")
        if event.get("end_of_turn") and event.get("turn_is_formatted"):
            return Heard(final=text, settled=True)
        if event.get("end_of_turn"):
            return Heard(partial=text)  # the formatted turn follows
        return Heard(partial=text)


class AssemblyAI(CloudProvider):
    id = "assemblyai"
    name = "AssemblyAI"
    short_name = "AssemblyAI"
    company = "AssemblyAI"
    console_url = "https://www.assemblyai.com/app"
    privacy_url = "https://www.assemblyai.com/legal/privacy-policy"
    hosts = tuple(_ASSEMBLY_HOSTS.values())
    description = (
        "AssemblyAI Universal Streaming: live words, in the US or the EU, and up "
        "to 100 of your words."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            _key_field("your AssemblyAI dashboard"),
            ProviderField(
                "region",
                "Region",
                "choice",
                required=False,
                default="us",
                choices=(("us", "United States"), ("eu", "European Union")),
                help=(
                    "Where AssemblyAI hears your speech: the United States, or the European Union."
                ),
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, biasing_limit=100, biasing_name="keyterms_prompt")

    def where(self, values: Values) -> str:
        return "the European Union" if values.get("region") == "eu" else "the United States"

    def _host(self, values: Values) -> str:
        return _ASSEMBLY_HOSTS.get(str(values.get("region") or "us"), _ASSEMBLY_HOSTS["us"])

    def test(self, values: Values) -> str:
        return self._probe_assemblyai(values)

    def _probe_assemblyai(self, values: Values) -> str:
        request = Request(
            f"https://{self._host(values)}/v3/token?expires_in_seconds=60",
            headers={"Authorization": str(values.get("key", ""))},
            method="GET",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                transport.read_json(response)
        return f"AssemblyAI answered: ready, {self.where(values)}."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        query: list[tuple[str, str]] = [
            ("sample_rate", "16000"),
            ("encoding", "pcm_s16le"),
            ("format_turns", "true"),
        ]
        if not language.lower().startswith("en"):
            query.append(("speech_model", "universal-streaming-multilingual"))
        kept = [term for term in terms if len(term) <= 50][:100]
        if kept:
            query.append(("keyterms_prompt", json.dumps(kept)))
        url = f"wss://{self._host(values)}/v3/ws?" + urlencode(query)
        key = str(values.get("key", ""))
        return SocketSession(
            _AssemblyAdapter(), lambda: self._connect_assemblyai(url, key), on_delta=on_delta
        )

    def _connect_assemblyai(self, url: str, key: str) -> Any:
        return transport.create_connection(url, {"Authorization": key})


# -- Speechmatics ---------------------------------------------------------------- #

_SPEECHMATICS_HOSTS = {"eu": "eu2.rt.speechmatics.com", "us": "us2.rt.speechmatics.com"}


class _SpeechmaticsAdapter(SocketAdapter):
    name = "Speechmatics"
    settle_seconds = 3.0
    keepalive_seconds = 5.0

    def __init__(self, language: str, terms: Sequence[str]) -> None:
        self._language = language
        self._terms = list(terms)
        self._sent = 0

    def opening(self) -> Sequence[str]:
        config: dict[str, Any] = {
            "language": self._language,
            "enable_partials": True,
            "max_delay": 2,
            "operating_point": "enhanced",
        }
        if self._terms:
            config["additional_vocab"] = [{"content": term} for term in self._terms]
        return (
            json.dumps({
                "message": "StartRecognition",
                "audio_format": {"type": "raw", "encoding": "pcm_s16le", "sample_rate": 16000},
                "transcription_config": config,
            }),
        )

    def audio(self, pcm: bytes) -> bytes:
        self._sent += 1
        return pcm

    def closing(self) -> Sequence[str]:
        return (json.dumps({"message": "EndOfStream", "last_seq_no": self._sent}),)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        kind = str(event.get("message", ""))
        if kind == "Error":
            return Heard(
                error="Speechmatics reported a problem: "
                + f"{event.get('reason') or event.get('type') or 'unknown'}."
            )
        text = str((event.get("metadata") or {}).get("transcript", "") or "")
        if kind == "AddTranscript":
            return Heard(final=text)
        if kind == "AddPartialTranscript":
            return Heard(partial=text)
        return Heard()


class Speechmatics(CloudProvider):
    id = "speechmatics"
    name = "Speechmatics"
    short_name = "Speechmatics"
    company = "Speechmatics"
    console_url = "https://portal.speechmatics.com"
    privacy_url = "https://www.speechmatics.com/privacy-policy"
    hosts = (*_SPEECHMATICS_HOSTS.values(), "asr.api.speechmatics.com")
    description = (
        "Speechmatics real-time: live words, in the EU or the US, with your words "
        "as additional vocabulary."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            _key_field("the Speechmatics portal, API Keys"),
            ProviderField(
                "region",
                "Region",
                "choice",
                required=False,
                default="eu",
                choices=(("eu", "European Union"), ("us", "United States")),
                help=(
                    "Where Speechmatics hears your speech: the European Union, or the "
                    "United States."
                ),
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True, biasing_limit=1000, biasing_name="additional_vocab", diarization=True
        )

    def where(self, values: Values) -> str:
        return "the United States" if values.get("region") == "us" else "the European Union"

    def test(self, values: Values) -> str:
        return self._probe_speechmatics(values)

    def _probe_speechmatics(self, values: Values) -> str:
        request = Request(
            "https://asr.api.speechmatics.com/v2/jobs",
            headers={"Authorization": f"Bearer {values.get('key', '')}"},
            method="GET",
        )
        with transport.failing_as(self.name):
            with transport.urlopen(request, timeout=15) as response:
                transport.read_json(response)
        return f"Speechmatics answered: ready, {self.where(values)}."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        host = _SPEECHMATICS_HOSTS.get(str(values.get("region") or "eu"), _SPEECHMATICS_HOSTS["eu"])
        url = f"wss://{host}/v2"
        key = str(values.get("key", ""))
        adapter = _SpeechmaticsAdapter(language.split("-")[0] or "en", terms)
        return SocketSession(
            adapter, lambda: self._connect_speechmatics(url, key), on_delta=on_delta
        )

    def _connect_speechmatics(self, url: str, key: str) -> Any:
        return transport.create_connection(url, {"Authorization": f"Bearer {key}"})
