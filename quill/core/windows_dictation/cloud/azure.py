"""Azure AI Speech: live words over the Speech service socket, or one phrase (D-32).

The person brings their own Speech resource: its **Key**, and its **Region**
or its own **Endpoint** (``https://<name>.cognitiveservices.azure.com``).
Nothing here uses Microsoft's SDK; the wire is spoken directly.

* **Test** -- ``POST https://<region>.api.cognitive.microsoft.com/sts/v1.0/issueToken``
  with ``Ocp-Apim-Subscription-Key`` and an empty body (or the same path on
  the Endpoint when only an Endpoint is given). It sends no audio.
* **Live** -- the Speech service WebSocket the Speech SDK itself uses,
  ``wss://<region>.stt.speech.microsoft.com/speech/recognition/conversation/
  cognitiveservices/v1?language=..&format=detailed`` (``&cid=`` for a Custom
  Speech endpoint), with ``Ocp-Apim-Subscription-Key`` and ``X-ConnectionId``
  headers. Text messages are ``Path`` / ``X-RequestId`` / ``X-Timestamp`` /
  ``Content-Type`` header lines, a blank line, then JSON: ``speech.config``
  first, then ``speech.context`` carrying My Words as the phrase list. Audio
  goes as binary messages: a two-byte big-endian header length, the header
  lines, then the PCM; the first one starts with a 44-byte WAV header. The
  service answers ``speech.hypothesis`` (provisional), ``speech.phrase``
  (final) and ``turn.end``.
* **Phrase** -- fast transcription, ``POST .../speechtotext/transcriptions:transcribe
  ?api-version=2024-11-15``, multipart with an ``audio`` part and a
  ``definition`` JSON part holding the locale and the phrase list.

**Risks (verify against a live resource).** The socket protocol is the SDK's
own and is less documented than the REST APIs. QUILL keeps **one**
``X-RequestId`` for the whole session; the SDK starts a new request id (and
resends ``speech.context``) after each ``turn.end``, and the service may
refuse audio sent under a finished turn's id. Keep-alive is a tenth of a
second of silence, which Azure bills as audio. The Endpoint form of the live
socket (``wss://<name>.cognitiveservices.azure.com/stt/speech/...``) is the
SDK's custom-domain form and is also **verify**.

wx-free.
"""

from __future__ import annotations

import json
import re
import struct
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.errors import CloudFieldError, CloudSpeechError
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    LiveSession,
    ProviderField,
    Values,
    locale_for,
)
from quill.core.windows_dictation.cloud.wire import multipart, wav_bytes
from quill.core.windows_dictation.cloud.ws_base import Heard, SocketAdapter, SocketSession

__all__ = ["REGIONS", "AzureSpeech"]

#: The regions offered in the Region list, as ``(value, label)``.
REGIONS: tuple[tuple[str, str], ...] = (
    ("eastus", "East US"),
    ("eastus2", "East US 2"),
    ("westus", "West US"),
    ("westus2", "West US 2"),
    ("westus3", "West US 3"),
    ("centralus", "Central US"),
    ("northcentralus", "North Central US"),
    ("southcentralus", "South Central US"),
    ("canadacentral", "Canada Central"),
    ("brazilsouth", "Brazil South"),
    ("northeurope", "North Europe"),
    ("westeurope", "West Europe"),
    ("uksouth", "UK South"),
    ("francecentral", "France Central"),
    ("germanywestcentral", "Germany West Central"),
    ("swedencentral", "Sweden Central"),
    ("switzerlandnorth", "Switzerland North"),
    ("norwayeast", "Norway East"),
    ("eastasia", "East Asia"),
    ("southeastasia", "Southeast Asia"),
    ("japaneast", "Japan East"),
    ("japanwest", "Japan West"),
    ("koreacentral", "Korea Central"),
    ("australiaeast", "Australia East"),
    ("centralindia", "Central India"),
    ("uaenorth", "UAE North"),
    ("southafricanorth", "South Africa North"),
)

_ENDPOINT_DOMAIN = (".cognitiveservices.azure.com",)
_SOCKET_PATH = "/speech/recognition/conversation/cognitiveservices/v1"
_FAST_PATH = "/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
_PHRASE_LIMIT = 500
#: Statuses that mean "nothing was said", not a problem.
_QUIET = ("NoMatch", "InitialSilenceTimeout", "BabbleTimeout")


def _check_region(value: str) -> str:
    if re.fullmatch(r"[a-z0-9]{2,40}", value.strip()):
        return ""
    return "Region must be an Azure region name such as westeurope. Check Region."


def _check_endpoint(value: str) -> str:
    try:
        transport.require_host(value, _ENDPOINT_DOMAIN, field="Endpoint")
    except CloudFieldError as error:
        return str(error.args[0])
    return ""


def _check_id(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9-]{1,64}", value.strip()):
        return ""
    return "Custom speech endpoint ID has letters, digits and hyphens only. Check it."


def _check_language(value: str) -> str:
    if re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", value.strip()):
        return ""
    return "Language must be a locale such as en-US or es-MX. Check Language."


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def wav_header(rate: int = 16_000) -> bytes:
    """A 44-byte WAV header for 16-bit mono at *rate*, its length fields 0
    (the socket's audio has no known length)."""
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        0,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # mono
        rate,
        rate * 2,
        2,
        16,
        b"data",
        0,
    )


def split_message(message: str) -> tuple[dict[str, str], str]:
    """``(headers with lower-case names, body)`` of one Speech service text message."""
    head, _, body = message.partition("\r\n\r\n")
    headers: dict[str, str] = {}
    for line in head.split("\r\n"):
        name, sep, value = line.partition(":")
        if sep:
            headers[name.strip().lower()] = value.strip()
    return headers, body


class _AzureAdapter(SocketAdapter):
    """The Speech service's own framing: header lines, then JSON or audio."""

    name = "Azure"
    settle_seconds = 3.0
    keepalive_seconds = 5.0

    def __init__(self, terms: Sequence[str], request_id: str | None = None) -> None:
        self._terms = [term for term in terms if term.strip()][:_PHRASE_LIMIT]
        #: One request id for the whole session (see the module's risks).
        self.request_id = request_id or uuid.uuid4().hex.upper()
        self._first_audio = True

    def _text(self, path: str, payload: dict[str, Any]) -> str:
        return (
            f"Path: {path}\r\nX-RequestId: {self.request_id}\r\n"
            f"X-Timestamp: {_timestamp()}\r\nContent-Type: application/json\r\n\r\n"
            + json.dumps(payload)
        )

    def opening(self) -> Sequence[str]:
        config = {
            "context": {
                "system": {"name": "QUILL", "version": "1", "build": "Windows", "lang": "Python"},
                "os": {"platform": "Windows", "name": "Windows", "version": ""},
                "audio": {
                    "source": {
                        "samplerate": self.rate,
                        "bitspersample": 16,
                        "channelcount": 1,
                        "connectivity": "Unknown",
                        "type": "Microphones",
                    }
                },
            }
        }
        messages = [self._text("speech.config", config)]
        if self._terms:
            items = [{"Text": term} for term in self._terms]
            context = {"dgi": {"Groups": [{"Type": "Generic", "Items": items}]}}
            messages.append(self._text("speech.context", context))
        return messages

    def audio(self, pcm: bytes) -> bytes:
        header = (
            f"Path: audio\r\nX-RequestId: {self.request_id}\r\n"
            f"X-Timestamp: {_timestamp()}\r\nContent-Type: audio/x-wav\r\n"
        ).encode("ascii")
        if self._first_audio:
            pcm = wav_header(self.rate) + pcm
            self._first_audio = False
        return struct.pack(">H", len(header)) + header + pcm

    def closing(self) -> Sequence[bytes]:
        # An audio message with no audio is the end of the stream.
        return () if self._first_audio else (self.audio(b""),)

    def hear(self, message: str | bytes) -> Heard:
        if isinstance(message, bytes):
            return Heard()  # the service sends no binary messages for recognition
        headers, body = split_message(message)
        path = headers.get("path", "").lower()
        if path == "turn.end":
            return Heard(settled=True)
        if path not in ("speech.hypothesis", "speech.fragment", "speech.phrase"):
            return Heard()
        try:
            event = json.loads(body) if body.strip() else {}
        except ValueError:
            return Heard()
        if not isinstance(event, dict):
            return Heard()
        if path != "speech.phrase":
            return Heard(partial=str(event.get("Text", "") or ""))
        status = str(event.get("RecognitionStatus", "") or "")
        if status == "Success":
            return Heard(final=_display(event))
        if status in _QUIET:
            return Heard(final="")
        if status == "EndOfDictation":
            return Heard(settled=True)
        return Heard(error=f"Azure reported a problem: {status or 'unknown'}.")


def _display(event: dict[str, Any]) -> str:
    text = event.get("DisplayText")
    if not text:
        best = event.get("NBest") or [{}]
        text = best[0].get("Display", "") if isinstance(best[0], dict) else ""
    return str(text or "")


class AzureSpeech(CloudProvider):
    id = "azure"
    name = "Azure AI Speech"
    short_name = "Azure"
    company = "Microsoft"
    console_url = "https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/SpeechServices"
    privacy_url = "https://learn.microsoft.com/legal/cognitive-services/speech-service/speech-to-text/data-privacy-security"
    hosts = (
        *(f"{region}.api.cognitive.microsoft.com" for region, _label in REGIONS),
        *(f"{region}.stt.speech.microsoft.com" for region, _label in REGIONS),
        "*.cognitiveservices.azure.com",
    )
    description = (
        "Microsoft's Azure AI Speech, in the region you choose: live words while you "
        "speak, and up to 500 of your words as a phrase list."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField(
                "key",
                "Key",
                "secret",
                help=(
                    "Key 1 or Key 2 of your Speech resource, from the Azure portal, under "
                    "the resource's Keys and Endpoint. Kept in Windows Credential Manager, "
                    "never in QUILL's settings; leave this empty to keep the key already saved."
                ),
            ),
            ProviderField(
                "region",
                "Region",
                "choice",
                required=False,
                choices=REGIONS,
                validate=_check_region,
                help=(
                    "The Azure region of your Speech resource, shown as Location on its "
                    "Keys and Endpoint page. Your speech goes to that region. Needed "
                    "unless you fill in Endpoint."
                ),
            ),
            ProviderField(
                "endpoint",
                "Endpoint",
                "text",
                required=False,
                validate=_check_endpoint,
                help=(
                    "Optional. Your resource's own address, ending in "
                    "cognitiveservices.azure.com. When given, phrase-at-a-time "
                    "transcription goes there instead of the region's address."
                ),
            ),
            ProviderField(
                "endpoint_id",
                "Custom speech endpoint ID",
                "text",
                required=False,
                validate=_check_id,
                help=(
                    "Optional. The ID of a Custom Speech model you deployed in Speech "
                    "Studio. QUILL does not create one for you. Blank uses Microsoft's "
                    "standard model."
                ),
            ),
            ProviderField(
                "language",
                "Language",
                "text",
                required=False,
                validate=_check_language,
                help=(
                    "Optional. The locale Azure listens for, such as en-GB or es-MX. Blank "
                    "follows the dictation language."
                ),
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(
            streaming=True,
            biasing_limit=_PHRASE_LIMIT,
            biasing_name="phrase list",
            diarization=False,
            timestamps=True,
        )

    def problem(self, values: Values) -> CloudFieldError | None:
        found = super().problem(values)
        if found is not None:
            return found
        if not _value(values, "region") and not _value(values, "endpoint"):
            return CloudFieldError(
                "Region is empty. Choose a Region, or fill in Endpoint.", field="Region"
            )
        return None

    def where(self, values: Values) -> str:
        return _value(values, "region")

    # -- addresses -------------------------------------------------------------- #

    def _ready(self, values: Values) -> None:
        found = self.problem(values)
        if found is not None:
            raise found

    def _endpoint(self, values: Values) -> str:
        endpoint = _value(values, "endpoint")
        if not endpoint:
            return ""
        return transport.require_host(endpoint, _ENDPOINT_DOMAIN, field="Endpoint")

    def _rest_base(self, values: Values, *, prefer_endpoint: bool) -> str:
        endpoint = self._endpoint(values)
        region = _value(values, "region")
        if endpoint and (prefer_endpoint or not region):
            return endpoint
        return f"https://{region}.api.cognitive.microsoft.com"

    def socket_url(self, values: Values, language: str) -> str:
        """The live socket's address for *values* (no secrets in it)."""
        query = [
            ("language", locale_for(language, _value(values, "language"))),
            ("format", "detailed"),
        ]
        endpoint_id = _value(values, "endpoint_id")
        if endpoint_id:
            query.append(("cid", endpoint_id))
        region = _value(values, "region")
        if region:
            base = f"wss://{region}.stt.speech.microsoft.com"
        else:
            host = urlsplit(self._endpoint(values)).hostname or ""
            base = f"wss://{host}/stt"
        return base + _SOCKET_PATH + "?" + urlencode(query)

    # -- the verbs -------------------------------------------------------------- #

    def test(self, values: Values) -> str:
        self._ready(values)
        return self._probe_azure(values)

    def _probe_azure(self, values: Values) -> str:
        base = self._rest_base(values, prefer_endpoint=False)
        place = "Region" if _value(values, "region") else "Endpoint"
        request = Request(
            base + "/sts/v1.0/issueToken",
            data=b"",
            headers={"Ocp-Apim-Subscription-Key": _value(values, "key")},
            method="POST",
        )
        with transport.failing_as("Azure", place_field=place):
            with transport.urlopen(request, timeout=15) as response:
                response.read()  # a short-lived token, never kept
        region = _value(values, "region")
        if region:
            return f"Azure answered: ready, region {region}."
        return f"Azure answered: ready, {urlsplit(base).hostname}."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        self._ready(values)
        url = self.socket_url(values, language)
        key = _value(values, "key")
        adapter = _AzureAdapter(terms)
        return SocketSession(adapter, lambda: self._connect_azure(url, key), on_delta=on_delta)

    def _connect_azure(self, url: str, key: str) -> Any:
        return transport.create_connection(
            url,
            {"Ocp-Apim-Subscription-Key": key, "X-ConnectionId": uuid.uuid4().hex.upper()},
        )

    def phrase(self, values: Values, samples: Any, *, language: str, terms: Sequence[str]) -> str:
        self._ready(values)
        return self._send_azure(values, wav_bytes(samples), language, terms)

    def _send_azure(self, values: Values, audio: bytes, language: str, terms: Sequence[str]) -> str:
        definition: dict[str, Any] = {"locales": [locale_for(language, _value(values, "language"))]}
        kept = [term for term in terms if term.strip()][:_PHRASE_LIMIT]
        if kept:
            definition["phraseList"] = {"phrases": kept}
        body, content_type = multipart(
            [],
            [("audio", "phrase.wav", "audio/wav", audio)],
            json_fields=[("definition", json.dumps(definition))],
        )
        base = self._rest_base(values, prefer_endpoint=True)
        place = "Endpoint" if self._endpoint(values) else "Region"
        request = Request(
            base + _FAST_PATH,
            data=body,
            headers={
                "Ocp-Apim-Subscription-Key": _value(values, "key"),
                "Content-Type": content_type,
                "Accept": "application/json",
            },
            method="POST",
        )
        with transport.failing_as("Azure", place_field=place):
            with transport.urlopen(request, timeout=30) as response:
                data = transport.read_json(response)
        return _combined(data)


def _combined(data: Any) -> str:
    if not isinstance(data, dict):
        raise CloudSpeechError("Azure's answer could not be read.")
    phrases = data.get("combinedPhrases") or []
    if not phrases or not isinstance(phrases[0], dict):
        return ""
    return str(phrases[0].get("text", "") or "").strip()


def _value(values: Values, key: str) -> str:
    return str(values.get(key, "") or "").strip()
