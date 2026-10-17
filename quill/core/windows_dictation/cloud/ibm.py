"""IBM Watson Speech to Text: live words over IBM's recognize socket (D-37).

The person brings their own Speech to Text instance: its API **Key** and its
**Service URL** (``https://api.<region>.speech-to-text.watson.cloud.ibm.com/
instances/<id>``), both on the instance's Manage page. Nothing here uses IBM's
SDK.

* **Token** -- the key is exchanged at ``https://iam.cloud.ibm.com/identity/token``
  (form ``grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey=...``) for
  a short-lived bearer token, kept only in memory for the one call or session.
* **Test** -- the token, then ``GET <service URL>/v1/models`` with it. It
  sends no audio.
* **Live** -- ``wss://<service host and path>/v1/recognize?access_token=..&model=..``
  (and ``language_customization_id`` for the person's own custom language
  model). The token goes in the query because that is where IBM's socket
  takes it. A ``start`` action configures 16 kHz little-endian 16-bit PCM,
  interim results and smart formatting with no inactivity timeout; audio goes
  as binary; ``results`` carry provisional and final transcripts; ``stop``
  ends the request.

**Learns your words: no.** IBM learns words only through a custom language
model the person trains in their own account; QUILL never creates resources
there, it only uses the ID it is given. The token lasts an hour; a session
longer than that keeps working on the open socket, and the next session asks
for a new token (**verify** that an open socket outlives its token).

wx-free.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.errors import CloudAuthError, CloudFieldError
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    LiveSession,
    ProviderField,
    Values,
)
from quill.core.windows_dictation.cloud.ws_base import Heard, SocketAdapter, SocketSession

__all__ = ["WatsonSpeech"]

_NAME = "IBM Watson"
_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
_SERVICE_DOMAIN = (".speech-to-text.watson.cloud.ibm.com",)
_DEFAULT_MODELS = {"es": "es-ES_Multimedia"}
_DEFAULT_MODEL = "en-US_Multimedia"


def _check_service_url(value: str) -> str:
    try:
        transport.require_host(value, _SERVICE_DOMAIN, field="Service URL")
    except CloudFieldError as error:
        return str(error.args[0])
    return ""


def _check_model(value: str) -> str:
    if re.fullmatch(r"[A-Za-z]{2,3}-[A-Za-z]{2,4}_[A-Za-z0-9]+", value.strip()):
        return ""
    return "Model must be an IBM model name such as en-US_Multimedia. Check Model."


def _check_id(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9-]{1,64}", value.strip()):
        return ""
    return "Custom language model ID has letters, digits and hyphens only. Check it."


def region_of(service_url: str) -> str:
    """The region in an IBM service address ("us-south"), or ""."""
    host = (urlsplit(service_url.strip()).hostname or "").lower()
    labels = host.split(".")
    if "speech-to-text" in labels:
        index = labels.index("speech-to-text")
        if index > 0:
            return labels[index - 1]
    return ""


class _WatsonAdapter(SocketAdapter):
    name = _NAME
    settle_seconds = 3.0
    # IBM closes a socket that hears nothing for 30 seconds (the session
    # timeout), whatever inactivity_timeout says; silence keeps it open.
    keepalive_seconds = 10.0

    def opening(self) -> Sequence[str]:
        return (
            json.dumps({
                "action": "start",
                "content-type": f"audio/l16;rate={self.rate};endianness=little-endian",
                "interim_results": True,
                "smart_formatting": True,
                "inactivity_timeout": -1,
            }),
        )

    def closing(self) -> Sequence[str]:
        return (json.dumps({"action": "stop"}),)

    def hear_json(self, event: dict[str, Any]) -> Heard:
        if "error" in event:
            return Heard(error=f"IBM Watson reported a problem: {event.get('error') or 'unknown'}.")
        results = event.get("results")
        if not isinstance(results, list) or not results:
            return Heard()  # {"state": "listening"}, warnings
        result = results[-1] if isinstance(results[-1], dict) else {}
        alternatives = result.get("alternatives") or [{}]
        first = alternatives[0] if isinstance(alternatives[0], dict) else {}
        text = str(first.get("transcript", "") or "")
        if result.get("final"):
            return Heard(final=text)
        return Heard(partial=text)


class WatsonSpeech(CloudProvider):
    id = "ibm"
    name = "IBM Watson Speech to Text"
    short_name = "IBM Watson"
    company = "IBM"
    console_url = "https://cloud.ibm.com/billing/usage"
    privacy_url = "https://www.ibm.com/privacy"
    hosts = ("iam.cloud.ibm.com", "*.speech-to-text.watson.cloud.ibm.com")
    description = (
        "IBM Watson Speech to Text, in your instance's region: live words while you "
        "speak, with your own custom language model if you have trained one."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField(
                "key",
                "Key",
                "secret",
                help=(
                    "The API key of your Speech to Text instance, from IBM Cloud, the "
                    "instance's Manage page. Kept in Windows Credential Manager, never in "
                    "QUILL's settings; leave this empty to keep the key already saved."
                ),
            ),
            ProviderField(
                "service_url",
                "Service URL",
                "text",
                validate=_check_service_url,
                help=(
                    "The URL shown beside the key on the instance's Manage page, ending "
                    "in speech-to-text.watson.cloud.ibm.com and the instance. Your speech "
                    "goes to that instance's region."
                ),
            ),
            ProviderField(
                "model",
                "Model",
                "text",
                required=False,
                default=_DEFAULT_MODEL,
                validate=_check_model,
                help=(
                    "Optional. The IBM model, such as en-GB_Multimedia. Blank uses "
                    "en-US_Multimedia, or es-ES_Multimedia when you dictate in Spanish."
                ),
            ),
            ProviderField(
                "customization_id",
                "Custom language model ID",
                "text",
                required=False,
                validate=_check_id,
                help=(
                    "Optional. The ID of a custom language model you trained in your IBM "
                    "account, which is how IBM learns your words. QUILL does not create "
                    "one for you, and does not send My Words to IBM."
                ),
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, biasing_limit=0, timestamps=True)

    def where(self, values: Values) -> str:
        return region_of(_value(values, "service_url"))

    def _service(self, values: Values) -> str:
        found = self.problem(values)
        if found is not None:
            raise found
        return transport.require_host(
            _value(values, "service_url"), _SERVICE_DOMAIN, field="Service URL"
        )

    def _model(self, values: Values, language: str) -> str:
        chosen = _value(values, "model")
        if chosen:
            return chosen
        return _DEFAULT_MODELS.get(language.strip().lower()[:2], _DEFAULT_MODEL)

    def _token_ibm(self, key: str) -> str:
        request = Request(
            _TOKEN_URL,
            data=urlencode({
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": key,
            }).encode("ascii"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        # IAM answers 400 for a key it does not know.
        with transport.failing_as(_NAME):
            try:
                with transport.urlopen(request, timeout=15) as response:
                    data = transport.read_json(response)
            except Exception as error:  # noqa: BLE001 - re-raised as a sentence
                if getattr(error, "code", 0) == 400:
                    raise CloudAuthError("The key was refused. Check Key.", field="Key") from None
                raise
        token = str(data.get("access_token", "") if isinstance(data, dict) else "")
        if not token:
            raise CloudAuthError("The key was refused. Check Key.", field="Key")
        return token

    def test(self, values: Values) -> str:
        service = self._service(values)
        return self._probe_ibm(service, self._token_ibm(_value(values, "key")), values)

    def _probe_ibm(self, service: str, token: str, values: Values) -> str:
        request = Request(
            service + "/v1/models",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",
        )
        with transport.failing_as(_NAME, place_field="Service URL"):
            with transport.urlopen(request, timeout=15) as response:
                data = transport.read_json(response)
        count = len(data.get("models", []) or []) if isinstance(data, dict) else 0
        region = self.where(values)
        place = f", {region}" if region else ""
        return f"IBM Watson answered: ready, {count} model{'s' if count != 1 else ''}{place}."

    def socket_url(self, values: Values, language: str, token: str) -> str:
        """The recognize socket for *values*, with the short-lived *token*."""
        service = self._service(values)
        query = [("access_token", token), ("model", self._model(values, language))]
        custom = _value(values, "customization_id")
        if custom:
            query.append(("language_customization_id", custom))
        return "wss://" + service.removeprefix("https://") + "/v1/recognize?" + urlencode(query)

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        del terms  # IBM learns words only through the person's custom model
        self._service(values)
        settled = dict(values)
        return SocketSession(
            _WatsonAdapter(), lambda: self._connect_ibm(settled, language), on_delta=on_delta
        )

    def _connect_ibm(self, values: Values, language: str) -> Any:
        token = self._token_ibm(_value(values, "key"))
        return transport.create_connection(self.socket_url(values, language, token))


def _value(values: Values, key: str) -> str:
    return str(values.get(key, "") or "").strip()
