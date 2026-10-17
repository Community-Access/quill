"""Google Cloud Speech-to-Text v2, with the person's own service account (D-33).

One finished phrase at a time over HTTPS, no Google SDK:

* **Sign-in**: the service-account file's private key signs a JSON Web Token
  (RS256, with ``cryptography``), which ``https://oauth2.googleapis.com/token``
  exchanges for an access token (``grant_type`` JWT bearer, scope
  ``cloud-platform``). The token is kept in memory until a minute before it
  expires. The key itself is never sent; only the signed token is.
* **Speech**: ``POST https://<location>-speech.googleapis.com/v2/projects/<project>/locations/<location>/recognizers/<recognizer>:recognize``
  (``speech.googleapis.com`` for ``global``) with the phrase as a base64 WAV,
  ``autoDecodingConfig``, the language, the model (``chirp_3`` by default)
  and automatic punctuation. My Words go as an inline phrase set under
  ``adaptation`` with a boost of 10.
* **Test Connection**: list the project's recognizers (``pageSize=1``), which
  sends no audio.

Words while you speak (``StreamingRecognize``) are gRPC only, so they would
need Google's streaming pack; :func:`streaming_pack_problem` says why that is
not offered in this copy.

wx-free.
"""

from __future__ import annotations

import base64
import json
import re
import threading
import time
from collections.abc import Sequence
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudSpeechError,
)
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    ProviderField,
    Values,
    locale_for,
)
from quill.core.windows_dictation.cloud.wire import wav_bytes

__all__ = ["GoogleSpeech", "ServiceAccount", "make_jwt", "streaming_pack_problem"]

_NAME = "Google"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_FILE = "Service account file"
_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("us", "United States, multi-region (us)"),
    ("eu", "European Union, multi-region (eu)"),
    ("global", "Global (global)"),
    ("us-central1", "Iowa (us-central1)"),
    ("europe-west4", "Netherlands (europe-west4)"),
    ("asia-southeast1", "Singapore (asia-southeast1)"),
)
_LOCATION_RE = re.compile(r"^[a-z]+[a-z0-9-]*$")
_PROJECT_RE = re.compile(r"^[a-z0-9.:-]{4,100}$")
_RECOGNIZER_RE = re.compile(r"^(_|[a-z][a-z0-9-]{0,61}[a-z0-9])$")
_MODEL_RE = re.compile(r"^[a-z0-9_.-]{1,64}$")
#: Renew the access token this long before Google says it expires.
_EARLY = 60.0


def streaming_pack_problem() -> str:
    """Why this copy cannot give live words from Google ("" when it could).

    Google's ``StreamingRecognize`` is gRPC only; the pack is not built here.
    """
    try:
        import google.cloud.speech_v2  # type: ignore[import-not-found,import-untyped,unused-ignore]  # noqa: F401
        import grpc  # type: ignore[import-not-found,import-untyped,unused-ignore]  # noqa: F401
    except ImportError:
        return (
            "Live words from Google need the optional Google streaming pack, which is "
            "not installed in this copy of QUILL. Google works a phrase at a time."
        )
    return ""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class ServiceAccount:
    """The parts of a service-account file QUILL uses, checked before any request."""

    def __init__(self, text: str) -> None:
        refused = CloudFieldError(
            "That is not a Google service account key file. Choose the JSON key file you "
            "downloaded for the service account. Check Service account file.",
            field=_FILE,
        )
        try:
            data = json.loads(text or "")
        except ValueError:
            raise refused from None
        if not isinstance(data, dict):
            raise refused
        self.client_email = str(data.get("client_email", "") or "").strip()
        self.key_id = str(data.get("private_key_id", "") or "").strip()
        self.project_id = str(data.get("project_id", "") or "").strip()
        pem = str(data.get("private_key", "") or "")
        if data.get("type", "service_account") != "service_account" or not self.client_email:
            raise refused
        try:
            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
            from cryptography.hazmat.primitives.serialization import load_pem_private_key

            key = load_pem_private_key(pem.encode("utf-8"), password=None)
        except Exception:  # noqa: BLE001 - a damaged key is the file's problem
            raise refused from None
        if not isinstance(key, RSAPrivateKey):
            raise refused
        self._key = key

    def sign(self, data: bytes) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        return self._key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def make_jwt(account: ServiceAccount, now: float | None = None) -> str:
    """The signed assertion exchanged for an access token (valid one hour)."""
    issued = int(now if now is not None else time.time())
    header: dict[str, str] = {"alg": "RS256", "typ": "JWT"}
    if account.key_id:
        header["kid"] = account.key_id
    claims = {
        "iss": account.client_email,
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": issued,
        "exp": issued + 3600,
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    )
    return signing_input + "." + _b64url(account.sign(signing_input.encode("ascii")))


def _google_problem(error: HTTPError) -> CloudSpeechError | None:
    """A sentence from the reason in Google's error body (never the body)."""
    try:
        raw = error.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None
    if "SERVICE_DISABLED" in raw or "accessNotConfigured" in raw:
        return CloudFieldError(
            "The Speech-to-Text API is not turned on in that project. Turn it on in the "
            "Google Cloud console, APIs and services, then check Project.",
            field="Project",
        )
    if int(error.code or 0) == 403:
        return CloudAuthError(
            "Google says this service account may not use Speech-to-Text in that project. "
            "Give it the Cloud Speech Client role, then check Service account file.",
            field=_FILE,
        )
    if int(error.code or 0) == 400 and ("model" in raw.lower() or "language" in raw.lower()):
        return CloudFieldError(
            "Google did not accept the model or language for that location. Check Model, "
            "Language and Location.",
            field="Model",
        )
    return None


def _transcript(data: Any) -> str:
    parts: list[str] = []
    for result in (data.get("results") or []) if isinstance(data, dict) else []:
        alternatives = (result or {}).get("alternatives") or []
        if alternatives:
            parts.append(str((alternatives[0] or {}).get("transcript", "") or "").strip())
    return " ".join(part for part in parts if part)


class GoogleSpeech(CloudProvider):
    id = "google"
    name = "Google Cloud Speech-to-Text"
    short_name = "Google"
    company = "Google"
    console_url = "https://console.cloud.google.com/billing"
    privacy_url = "https://cloud.google.com/terms/cloud-privacy-notice"
    hosts = (
        "oauth2.googleapis.com",
        "speech.googleapis.com",
        *(f"{value}-speech.googleapis.com" for value, _label in _LOCATIONS if value != "global"),
    )
    description = (
        "Google Cloud Speech-to-Text with Chirp 3: one phrase at a time, in the location "
        "you choose, and up to 1,000 of your words."
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        #: (client email, key id) -> (access token, monotonic expiry)
        self._tokens: dict[tuple[str, str], tuple[str, float]] = {}

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField(
                "service_account",
                _FILE,
                "file",
                help=(
                    "The JSON key file of a Google Cloud service account allowed to use "
                    "Speech-to-Text, from the Google Cloud console, IAM and admin, Service "
                    "accounts, Keys. QUILL keeps a protected copy; the key itself is never sent."
                ),
            ),
            ProviderField(
                "project",
                "Project",
                "text",
                required=False,
                help=(
                    "The Google Cloud project ID to bill. Leave it empty to use the project "
                    "named in the service account file."
                ),
                validate=lambda value: (
                    "" if _PROJECT_RE.match(value) else "That is not a project ID. Check Project."
                ),
            ),
            ProviderField(
                "location",
                "Location",
                "choice",
                required=False,
                default="us",
                choices=_LOCATIONS,
                help="Where Google hears your speech. Chirp 3 is offered in us and eu.",
                validate=lambda value: (
                    ""
                    if _LOCATION_RE.match(value)
                    else "That is not a Google Cloud location. Check Location."
                ),
            ),
            ProviderField(
                "recognizer",
                "Recognizer",
                "text",
                required=False,
                default="_",
                help=(
                    "The name of a recognizer you made in that project and location. Leave "
                    "it as an underscore to use none, which is usual."
                ),
                validate=lambda value: "" if _RECOGNIZER_RE.match(value) else "Check Recognizer.",
            ),
            ProviderField(
                "model",
                "Model",
                "text",
                required=False,
                default="chirp_3",
                help="The Google speech model. Blank uses chirp_3.",
                validate=lambda value: "" if _MODEL_RE.match(value) else "Check Model.",
            ),
            ProviderField(
                "language",
                "Language",
                "text",
                required=False,
                help=(
                    "The language code Google is told, such as en-US or en-GB. Leave it "
                    "empty to follow the dictation language."
                ),
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=False, biasing_limit=1000, biasing_name="adaptation phrases")

    def where(self, values: Values) -> str:
        return self._location(values)

    def _location(self, values: Values) -> str:
        return str(values.get("location") or "us").strip()

    def _host(self, location: str) -> str:
        return (
            "speech.googleapis.com" if location == "global" else f"{location}-speech.googleapis.com"
        )

    def problem(self, values: Values) -> CloudFieldError | None:
        found = super().problem(values)
        if found is not None:
            return found
        try:
            self._account(values)
        except CloudFieldError as error:
            return error
        return None

    def _account(self, values: Values) -> tuple[ServiceAccount, str]:
        """The service account and the project, before anything is sent."""
        text = str(values.get("service_account", "") or "")
        if not text.strip():
            raise CloudFieldError(f"{_FILE} is empty. Choose {_FILE}.", field=_FILE)
        account = ServiceAccount(text)
        project = str(values.get("project", "") or "").strip() or account.project_id
        if not project:
            raise CloudFieldError("Project is empty. Fill in Project.", field="Project")
        if not _PROJECT_RE.match(project):
            raise CloudFieldError("That is not a project ID. Check Project.", field="Project")
        return account, project

    def _prepare(self, values: Values) -> tuple[ServiceAccount, str, str]:
        found = super().problem(values)
        if found is not None:
            raise found
        account, project = self._account(values)
        return account, project, self._location(values)

    # -- sign-in ------------------------------------------------------------- #

    def _access_token(self, account: ServiceAccount) -> str:
        cache_key = (account.client_email, account.key_id)
        with self._lock:
            kept = self._tokens.get(cache_key)
            if kept is not None and time.monotonic() < kept[1]:
                return kept[0]
        token, lifetime = self._token_google(account)
        from quill.stability.redaction import remember_secret

        remember_secret(token)
        with self._lock:
            self._tokens[cache_key] = (token, time.monotonic() + max(0.0, lifetime - _EARLY))
        return token

    def _token_google(self, account: ServiceAccount) -> tuple[str, float]:
        body = urlencode({"grant_type": _GRANT, "assertion": make_jwt(account)}).encode("ascii")
        request = Request(
            TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with transport.failing_as(_NAME, auth_field=_FILE):
            try:
                with transport.urlopen(request, timeout=15) as response:
                    data = transport.read_json(response)
            except HTTPError as error:
                if int(error.code or 0) in (400, 401, 403):
                    raise CloudAuthError(
                        "Google refused the service account. It may have been deleted or "
                        "its key withdrawn. Check Service account file.",
                        field=_FILE,
                    ) from None
                raise
        token = str(data.get("access_token", "") if isinstance(data, dict) else "")
        if not token:
            raise CloudAuthError(
                "Google gave no access token. Check Service account file.", field=_FILE
            )
        try:
            lifetime = float(data.get("expires_in", 3600))
        except (TypeError, ValueError):
            lifetime = 3600.0
        return token, lifetime

    # -- Test Connection ----------------------------------------------------- #

    def test(self, values: Values) -> str:
        account, project, location = self._prepare(values)
        token = self._access_token(account)
        try:
            self._probe_google(token, project, location)
        except CloudAuthError:
            self.forget_tokens()
            raise
        return f"Google answered: ready, project {project}, location {location}."

    def _probe_google(self, token: str, project: str, location: str) -> None:
        url = (
            f"https://{self._host(location)}/v2/projects/{project}/locations/{location}"
            "/recognizers?pageSize=1"
        )
        request = Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
        with transport.failing_as(_NAME, auth_field=_FILE, place_field="Project"):
            try:
                with transport.urlopen(request, timeout=15) as response:
                    transport.read_json(response)
            except HTTPError as error:
                raise (_google_problem(error) or error) from None

    # -- one phrase ---------------------------------------------------------- #

    def request_body(
        self, values: Values, audio: bytes, language: str, terms: Sequence[str]
    ) -> dict[str, Any]:
        """The ``recognize`` body for *audio* (a WAV file)."""
        config: dict[str, Any] = {
            "autoDecodingConfig": {},
            "languageCodes": [locale_for(language, str(values.get("language", "") or ""))],
            "model": str(values.get("model") or "chirp_3"),
            "features": {"enableAutomaticPunctuation": True},
        }
        kept = [str(term) for term in terms if str(term).strip()][:1000]
        if kept:
            config["adaptation"] = {
                "phraseSets": [
                    {
                        "inlinePhraseSet": {
                            "phrases": [{"value": term, "boost": 10} for term in kept]
                        }
                    }
                ]
            }
        return {"config": config, "content": base64.b64encode(audio).decode("ascii")}

    def phrase(self, values: Values, samples: Any, *, language: str, terms: Sequence[str]) -> str:
        account, project, location = self._prepare(values)
        body = self.request_body(values, wav_bytes(samples), language, terms)
        token = self._access_token(account)
        recognizer = str(values.get("recognizer") or "_").strip()
        try:
            return self._send_google(token, project, location, recognizer, body)
        except CloudAuthError:
            self.forget_tokens()  # a withdrawn key: sign in again next time
            raise

    def forget_tokens(self) -> None:
        """Drop every access token kept in memory."""
        with self._lock:
            self._tokens.clear()

    def _send_google(
        self, token: str, project: str, location: str, recognizer: str, body: dict[str, Any]
    ) -> str:
        url = (
            f"https://{self._host(location)}/v2/projects/{project}/locations/{location}"
            f"/recognizers/{recognizer}:recognize"
        )
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        with transport.failing_as(_NAME, auth_field=_FILE, place_field="Recognizer"):
            try:
                with transport.urlopen(request, timeout=30) as response:
                    return _transcript(transport.read_json(response))
            except HTTPError as error:
                raise (_google_problem(error) or error) from None
