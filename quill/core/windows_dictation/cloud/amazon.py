"""Amazon Transcribe, with the person's own AWS account (D-34).

Live words over Transcribe Streaming's WebSocket, no AWS SDK:

* the address ``wss://transcribestreaming.<region>.amazonaws.com:8443/stream-transcription-websocket``
  is presigned with Signature Version 4 in its query
  (:mod:`~quill.core.windows_dictation.cloud.amazon_sigv4`), service
  ``transcribe``, valid for 300 seconds -- the secret access key never leaves
  the computer, only the access key ID and the signature;
* the query says ``language-code``, ``media-encoding=pcm``,
  ``sample-rate=16000`` and, when the person named one, ``vocabulary-name``;
* audio goes as binary ``AudioEvent`` frames
  (:mod:`~quill.core.windows_dictation.cloud.amazon_eventstream`), and an
  empty ``AudioEvent`` ends the stream;
* answers are ``TranscriptEvent`` frames (``Results[].Alternatives[0].Transcript``
  with ``IsPartial``) or exception frames (``:exception-type``).

Amazon decides when a phrase is final by itself; there is no "finish now"
message, so :meth:`SocketSession.commit` waits up to 2.5 seconds for it.

**My Words are not sent.** Transcribe's biasing is a *custom vocabulary* the
person creates in their own AWS account and names here; QUILL never creates
anything in anybody's account.

Keys come from the page (Credential Manager), or -- only when the person
names a profile -- from that profile in the AWS shared credentials file
(``%USERPROFILE%\\.aws\\credentials``). Keys from the page win.

Test Connection: a signed ``Transcribe.ListVocabularies`` call with
``MaxResults`` 1, which sends no audio.

wx-free.
"""

from __future__ import annotations

import configparser
import json
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

from quill.core.windows_dictation.cloud import transport
from quill.core.windows_dictation.cloud.amazon_eventstream import (
    EventStreamError,
    audio_event,
    decode,
)
from quill.core.windows_dictation.cloud.amazon_sigv4 import presign_url, sign_headers
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudQuotaError,
    CloudSpeechError,
)
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    LiveSession,
    ProviderField,
    Values,
    locale_for,
)
from quill.core.windows_dictation.cloud.ws_base import Heard, SocketAdapter, SocketSession

__all__ = ["AmazonTranscribe", "credentials_file", "read_profile"]

_NAME = "Amazon Transcribe"
_DEFAULT_REGION = "us-east-1"
_REGIONS: tuple[tuple[str, str], ...] = (
    ("us-east-1", "US East, N. Virginia (us-east-1)"),
    ("us-east-2", "US East, Ohio (us-east-2)"),
    ("us-west-2", "US West, Oregon (us-west-2)"),
    ("ca-central-1", "Canada, Central (ca-central-1)"),
    ("eu-west-1", "Europe, Ireland (eu-west-1)"),
    ("eu-west-2", "Europe, London (eu-west-2)"),
    ("eu-central-1", "Europe, Frankfurt (eu-central-1)"),
    ("ap-southeast-2", "Asia Pacific, Sydney (ap-southeast-2)"),
    ("ap-northeast-1", "Asia Pacific, Tokyo (ap-northeast-1)"),
    ("ap-south-1", "Asia Pacific, Mumbai (ap-south-1)"),
    ("sa-east-1", "South America, Sao Paulo (sa-east-1)"),
)
_REGION_RE = re.compile(r"^[a-z]{2}(-[a-z]+)+-\d$")
_VOCABULARY_RE = re.compile(r"^[0-9A-Za-z._-]{1,200}$")
_LANGUAGE_RE = re.compile(r"^[a-z]{2,3}-[A-Z]{2}$")
_PROFILE_RE = re.compile(r"^[\w.+@-]{1,64}$")

#: Where the exception types Amazon names point the person.
_AUTH_TYPES = (
    "UnrecognizedClient",
    "InvalidSignature",
    "SignatureDoesNotMatch",
    "IncompleteSignature",
    "MissingAuthenticationToken",
    "InvalidClientTokenId",
)


def _region_problem(value: str) -> str:
    if _REGION_RE.match(value):
        return ""
    return "Region must be an AWS region such as us-east-1. Check Region."


def _vocabulary_problem(value: str) -> str:
    if _VOCABULARY_RE.match(value):
        return ""
    return (
        "Vocabulary name may hold only letters, digits, dots, dashes and underscores. "
        "Check Vocabulary name."
    )


def _language_problem(value: str) -> str:
    if _LANGUAGE_RE.match(value):
        return ""
    return "Language must be a code such as en-US or es-US. Check Language."


def _profile_problem(value: str) -> str:
    if _PROFILE_RE.match(value):
        return ""
    return "That is not a profile name AWS uses. Check Profile name."


# -- the shared credentials file --------------------------------------------- #


def credentials_file() -> Path:
    """The AWS shared credentials file: ``%USERPROFILE%\\.aws\\credentials``."""
    home = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(home) / ".aws" / "credentials"


def read_profile(name: str) -> tuple[str, str, str]:
    """``(access key ID, secret access key, session token)`` for profile *name*.

    Read only when the person named the profile. Raises
    :class:`CloudFieldError` naming Profile name when the file or the profile
    is missing; the sentence never holds a key.
    """
    path = credentials_file()
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error):
        raise CloudFieldError(
            "The AWS credentials file in your user folder could not be read. Check Profile name.",
            field="Profile name",
        ) from None
    if not parser.has_section(name):
        raise CloudFieldError(
            f"The AWS credentials file has no profile called {name}. Check Profile name.",
            field="Profile name",
        )
    section = parser[name]
    access = section.get("aws_access_key_id", "").strip()
    secret = section.get("aws_secret_access_key", "").strip()
    token = section.get("aws_session_token", "").strip()
    if not access or not secret:
        raise CloudFieldError(
            f"The profile {name} has no access key in the AWS credentials file. "
            "Check Profile name.",
            field="Profile name",
        )
    from quill.stability.redaction import remember_secret

    for value in (access, secret, token):
        if value:
            remember_secret(value)
    return access, secret, token


# -- the WebSocket ----------------------------------------------------------- #


class _AmazonAdapter(SocketAdapter):
    name = _NAME
    auth_field = "Secret access key"
    settle_seconds = 2.5
    min_chunk_ms = 100
    # Amazon closes a stream that hears nothing for 15 seconds; a tenth of a
    # second of silence every 5 seconds holds it between phrases.
    keepalive_seconds = 5.0

    def audio(self, pcm: bytes) -> bytes:
        return audio_event(pcm)

    def closing(self) -> Sequence[bytes]:
        return (audio_event(b""),)

    def hear(self, message: str | bytes) -> Heard:
        if isinstance(message, str):
            message = message.encode("utf-8")
        try:
            frame = decode(message)
        except EventStreamError:
            return Heard()
        if frame.message_type == "exception":
            return Heard(error=_exception_sentence(frame.exception_type))
        if frame.message_type != "event" or frame.event_type != "TranscriptEvent":
            return Heard()
        return _transcript(frame.json())


def _exception_sentence(kind: str) -> str:
    if kind == "LimitExceededException":
        return f"{_NAME} says the account is over its limit. Check your AWS account."
    if kind == "BadRequestException":
        return (
            f"{_NAME} did not accept the request. Check Language, and that the Vocabulary "
            "name exists in that region for that language."
        )
    if kind == "ServiceUnavailableException" or kind == "InternalFailureException":
        return f"{_NAME} had a problem of its own. Try again shortly."
    if kind == "ConflictException":
        return f"{_NAME} already has a stream open for this. Try again shortly."
    return f"{_NAME} reported a problem: {kind or 'unknown'}."


def _transcript(event: Any) -> Heard:
    results = ((event or {}).get("Transcript") or {}).get("Results") or []
    finals: list[str] = []
    partial: str | None = None
    for result in results:
        if not isinstance(result, dict):
            continue
        alternatives = result.get("Alternatives") or [{}]
        text = str((alternatives[0] or {}).get("Transcript", "") or "")
        if result.get("IsPartial"):
            partial = text
        else:
            finals.append(text)
    if finals:
        return Heard(final=" ".join(finals), partial=partial)
    if partial is not None:
        return Heard(partial=partial)
    return Heard()


def _http_problem(error: HTTPError, auth_field: str) -> CloudSpeechError:
    """A sentence for an HTTP refusal, from the exception type in the body
    (never the body itself)."""
    try:
        body = json.loads(error.read().decode("utf-8", errors="replace") or "{}")
    except Exception:  # noqa: BLE001 - an unreadable body says nothing more
        body = {}
    kind = str((body or {}).get("__type", "") if isinstance(body, dict) else "")
    kind = kind.rsplit("#", 1)[-1]
    if "ExpiredToken" in kind:
        return CloudAuthError(
            "The session token has expired. Check Session token.", field="Session token"
        )
    if any(name in kind for name in _AUTH_TYPES):
        return CloudAuthError(
            f"The {auth_field.lower()} was refused. Check {auth_field}.", field=auth_field
        )
    if "AccessDenied" in kind:
        return CloudAuthError(
            f"Amazon says these keys may not use Transcribe. Give them the transcribe "
            f"permissions in AWS, then check {auth_field}.",
            field=auth_field,
        )
    if "LimitExceeded" in kind or "Throttling" in kind:
        return CloudQuotaError(f"{_NAME} says the account is sending too fast. Try again shortly.")
    return transport.failure(_NAME, error, auth_field=auth_field, place_field="Region")


class AmazonTranscribe(CloudProvider):
    id = "amazon"
    name = _NAME
    short_name = "Amazon"
    company = "Amazon Web Services"
    console_url = "https://console.aws.amazon.com/billing/home"
    privacy_url = "https://aws.amazon.com/privacy/"
    hosts = tuple(
        host
        for region, _label in _REGIONS
        for host in (
            f"transcribe.{region}.amazonaws.com",
            f"transcribestreaming.{region}.amazonaws.com",
        )
    )
    description = (
        "Amazon Transcribe: live words while you speak, in the AWS region you choose, "
        "with your own custom vocabulary."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        kept = (
            "Kept in Windows Credential Manager, never in QUILL's settings; leave this "
            "empty to keep the one already saved."
        )
        return (
            ProviderField(
                "access_key",
                "Access key ID",
                "secret",
                required=False,
                help=(
                    "The access key ID of an AWS user allowed to use Transcribe, from the "
                    f"AWS console, IAM, Users, Security credentials. {kept} Leave it empty "
                    "when you give a Profile name instead."
                ),
            ),
            ProviderField(
                "secret_key",
                "Secret access key",
                "secret",
                required=False,
                help=(
                    "The secret access key that goes with the access key ID. It is never "
                    f"sent: QUILL signs with it. {kept}"
                ),
            ),
            ProviderField(
                "session_token",
                "Session token",
                "secret",
                required=False,
                help=(
                    "Only for temporary keys, such as those from single sign-on. Leave it "
                    f"empty for an ordinary access key. {kept}"
                ),
            ),
            ProviderField(
                "region",
                "Region",
                "choice",
                required=False,
                default=_DEFAULT_REGION,
                choices=_REGIONS,
                help="The AWS region where Amazon hears your speech.",
                validate=_region_problem,
            ),
            ProviderField(
                "profile",
                "Profile name",
                "text",
                required=False,
                help=(
                    "Instead of typing keys: the name of a profile in the AWS credentials "
                    "file in your user folder. QUILL reads that file only when you give a "
                    "name here, and keys typed on this page win."
                ),
                validate=_profile_problem,
            ),
            ProviderField(
                "vocabulary",
                "Vocabulary name",
                "text",
                required=False,
                help=(
                    "The name of a custom vocabulary, so Amazon spells your words your way. "
                    "Create it in your AWS account first, in the same region; QUILL does not "
                    "create anything in anybody's account. Its language must match the "
                    "language you dictate in. Leave it empty for none."
                ),
                validate=_vocabulary_problem,
            ),
            ProviderField(
                "language",
                "Language",
                "text",
                required=False,
                help=(
                    "The language code Amazon is told, such as en-US or en-GB. Leave it empty "
                    "to follow the dictation language."
                ),
                validate=_language_problem,
            ),
        )

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, biasing_limit=0, timestamps=True)

    def where(self, values: Values) -> str:
        return self._region(values)

    def _region(self, values: Values) -> str:
        return str(values.get("region") or _DEFAULT_REGION).strip()

    def problem(self, values: Values) -> CloudFieldError | None:
        found = super().problem(values)
        if found is not None:
            return found
        access = str(values.get("access_key", "") or "").strip()
        secret = str(values.get("secret_key", "") or "").strip()
        profile = str(values.get("profile", "") or "").strip()
        if access and secret:
            return None
        if profile:
            try:
                read_profile(profile)
            except CloudFieldError as error:
                return error
            return None
        if access:
            return CloudFieldError(
                "Secret access key is empty. Fill in Secret access key.",
                field="Secret access key",
            )
        if secret:
            return CloudFieldError(
                "Access key ID is empty. Fill in Access key ID.", field="Access key ID"
            )
        return CloudFieldError(
            "Access key ID is empty. Fill in Access key ID and Secret access key, or a "
            "Profile name.",
            field="Access key ID",
        )

    def _keys(self, values: Values) -> tuple[str, str, str, str]:
        """``(access, secret, token, field to check when refused)``."""
        found = self.problem(values)
        if found is not None:
            raise found
        access = str(values.get("access_key", "") or "").strip()
        secret = str(values.get("secret_key", "") or "").strip()
        if access and secret:
            token = str(values.get("session_token", "") or "").strip()
            return access, secret, token, "Secret access key"
        access, secret, token = read_profile(str(values.get("profile", "")).strip())
        return access, secret, token, "Profile name"

    # -- Test Connection ----------------------------------------------------- #

    def test(self, values: Values) -> str:
        access, secret, token, auth_field = self._keys(values)
        region = self._region(values)
        self._probe_amazon(region, access, secret, token, auth_field)
        return f"Amazon answered: ready, region {region}."

    def _probe_amazon(
        self, region: str, access: str, secret: str, token: str, auth_field: str
    ) -> None:
        host = f"transcribe.{region}.amazonaws.com"
        body = json.dumps({"MaxResults": 1}).encode("utf-8")
        headers = sign_headers(
            method="POST",
            host=host,
            path="/",
            headers={
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "Transcribe.ListVocabularies",
            },
            body=body,
            access_key=access,
            secret_key=secret,
            session_token=token,
            region=region,
            service="transcribe",
        )
        request = Request(f"https://{host}/", data=body, headers=dict(headers), method="POST")
        with transport.failing_as(_NAME, auth_field=auth_field, place_field="Region"):
            try:
                with transport.urlopen(request, timeout=15) as response:
                    transport.read_json(response)
            except HTTPError as error:
                raise _http_problem(error, auth_field) from None

    # -- live words ---------------------------------------------------------- #

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        del terms  # Amazon's biasing is the named custom vocabulary, not a word list
        access, secret, token, auth_field = self._keys(values)
        region = self._region(values)
        params: list[tuple[str, str]] = [
            ("language-code", locale_for(language, str(values.get("language", "") or ""))),
            ("media-encoding", "pcm"),
            ("sample-rate", "16000"),
        ]
        vocabulary = str(values.get("vocabulary", "") or "").strip()
        if vocabulary:
            params.append(("vocabulary-name", vocabulary))
        adapter = _AmazonAdapter()
        adapter.auth_field = auth_field
        return SocketSession(
            adapter,
            lambda: self._connect_amazon(region, params, access, secret, token),
            on_delta=on_delta,
        )

    def _connect_amazon(
        self,
        region: str,
        params: Sequence[tuple[str, str]],
        access: str,
        secret: str,
        token: str,
    ) -> Any:
        # Signed at connect time, so the five-minute signature is always fresh.
        url = presign_url(
            scheme="wss",
            host=f"transcribestreaming.{region}.amazonaws.com:8443",
            path="/stream-transcription-websocket",
            params=params,
            access_key=access,
            secret_key=secret,
            session_token=token,
            region=region,
            service="transcribe",
            expires=300,
        )
        return transport.create_connection(url)
