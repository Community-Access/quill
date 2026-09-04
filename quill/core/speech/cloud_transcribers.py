"""Config-driven cloud transcription adapters for host-mediated provider kinds (#669).

Most cloud speech-to-text providers share a shape: POST audio to an HTTPS endpoint
with an API-key header, get back JSON whose transcript lives at a known path. This
module describes each vetted provider as a :class:`RestSpec` (data) and performs the
call generically (:func:`transcribe_rest`), so adding a kind is a data entry, not new
code.

These run only inside the host's :class:`SpeechToTextProvider` adapter (declared by a
Quillin), under the network-egress audit, Safe Mode, and per-use consent. The single
``urlopen`` call site here is the one reviewed egress entry for every REST kind; the
endpoint is always one of the vetted specs below, never an arbitrary URL.
"""

from __future__ import annotations

import json
import mimetypes
import ssl
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quill.core.error_codes import CodedError

_VERIFIED_TLS = ssl.create_default_context()
_TIMEOUT_S = 300.0


class CloudTranscribeError(CodedError):
    """A cloud transcription call failed (clear, user-facing message)."""

    code = "QUILL-SPEECH-CLOUD-TRANSCRIBE"


@dataclass(frozen=True, slots=True)
class RestSpec:
    """How to call one vetted cloud provider's synchronous REST endpoint.

    ``body_mode`` is ``"multipart"`` (audio as a file part) or ``"raw"`` (audio bytes
    as the request body). ``text_path`` is the JSON path to the transcript string,
    e.g. ``("text",)`` or ``("results", "channels", 0, "alternatives", 0, "transcript")``.
    """

    host: str  # the outbound hostname (kept in sync with the egress-audit rationale)
    endpoint: str
    key_header: str  # e.g. "Authorization", "xi-api-key"
    key_scheme: str = ""  # e.g. "Bearer ", "Token "
    body_mode: str = "multipart"  # "multipart" | "raw"
    file_field: str = "file"
    fields: tuple[tuple[str, str], ...] = ()  # extra multipart fields (model, etc.)
    query: tuple[tuple[str, str], ...] = ()  # static URL query params
    language_field: str = ""  # multipart field (or query key in raw mode) for language
    diarize_field: str = ""  # field/query set to "true" when diarization is requested
    text_path: tuple[Any, ...] = ("text",)
    max_file_mb: float = 25.0
    #: Multipart parts sent with ``Content-Type: application/json``. Azure's
    #: Fast Transcription wants its ``definition`` typed that way and rejects
    #: an untyped text part, which every other provider here accepts.
    json_fields: tuple[tuple[str, str], ...] = ()
    #: True when ``endpoint`` is a placeholder and the caller must supply the
    #: real one -- Azure's is your own resource's address, so there is no
    #: constant to put here. Enforced in :func:`transcribe_rest`.
    endpoint_from_caller: bool = False


#: Host-implemented transcription provider "kinds". The host knows how to talk to
#: each vetted endpoint; a Quillin may only *declare* a provider of a known kind,
#: so a manifest can never point the host at an arbitrary URL. Add a new kind here
#: (and a host adapter in ``quill/core/speech/quillin_providers.py``) only after it
#: is vetted into the network-egress audit. Lives in this host module (not in
#: ``quill.core.quillins``) so the standalone Audio Studio, which ships without
#: Quillins, still has the canonical list; ``quill.core.quillins.model`` re-exports
#: it for back-compat with QUILL's Quillin validation.
TRANSCRIPTION_PROVIDER_KINDS: tuple[str, ...] = ("openai_whisper", "groq", "elevenlabs")

#: Kinds the *host* can call but a Quillin may not declare.
#:
#: Azure MAI-Transcribe is here rather than in the list above for one reason:
#: its endpoint is your own Speech resource's address, supplied in QUILL's own
#: settings. Every other kind has a fixed endpoint baked into its spec, which
#: is what makes "a manifest may only name a known kind" a real guarantee. A
#: kind whose address comes from configuration would let a manifest aim the
#: host at an arbitrary server if it were declarable, so it is not.
HOST_ONLY_PROVIDER_KINDS: tuple[str, ...] = ("azure_mai",)

#: Vetted synchronous-REST cloud kinds. Hosts here are reflected in the egress audit.
CLOUD_REST_SPECS: dict[str, RestSpec] = {
    "groq": RestSpec(
        host="api.groq.com",
        endpoint="https://api.groq.com/openai/v1/audio/transcriptions",
        key_header="Authorization",
        key_scheme="Bearer ",
        body_mode="multipart",
        fields=(("model", "whisper-large-v3-turbo"), ("response_format", "json")),
        language_field="language",
        text_path=("text",),
        max_file_mb=25.0,
    ),
    "azure_mai": RestSpec(
        # The host is your own resource, so there is no constant to allow-list
        # here; `endpoint_from_caller` makes the caller supply it and
        # `transcribe_rest` refuses to run without one. Host-only (see
        # HOST_ONLY_PROVIDER_KINDS) precisely because that address is
        # configuration rather than a fixed, vetted endpoint.
        host="*.cognitiveservices.azure.com",
        endpoint="",
        endpoint_from_caller=True,
        key_header="Ocp-Apim-Subscription-Key",
        key_scheme="",
        body_mode="multipart",
        file_field="audio",
        text_path=("combinedPhrases", 0, "text"),
        max_file_mb=300.0,
    ),
    "elevenlabs": RestSpec(
        host="api.elevenlabs.io",
        endpoint="https://api.elevenlabs.io/v1/speech-to-text",
        key_header="xi-api-key",
        key_scheme="",
        body_mode="multipart",
        fields=(("model_id", "scribe_v1"),),
        language_field="language_code",
        diarize_field="diarize",
        text_path=("text",),
        max_file_mb=100.0,
    ),
}


def azure_mai_definition(
    *,
    language: str = "auto",
    style: str = "clean",
    diarize: bool = True,
    word_timestamps: bool = True,
    phrases: Sequence[str] = (),
) -> str:
    """The ``definition`` part for an Azure MAI-Transcribe request, as JSON.

    Built here rather than inline so it can be read and tested on its own.
    Two rules from Microsoft's documentation are easy to get wrong and are
    therefore explicit: a locale is omitted entirely for automatic detection
    (a strong hint towards the wrong language is worse than no hint), and a
    phrase list biases recognition rather than substituting into the result.
    """
    options: dict[str, Any] = {
        "timestamps": "word" if word_timestamps else "segment",
        "transcribeStyle": style if style in {"clean", "verbatim"} else "clean",
    }
    definition: dict[str, Any] = {
        "enhancedMode": {"enabled": True, "model": "MAI-Transcribe-2", "modelOptions": options},
    }
    if language in {"en", "es"}:
        definition["locales"] = [language]
    if diarize:
        definition["diarization"] = {"enabled": True}
    wanted = [str(p).strip() for p in phrases if str(p).strip()]
    if wanted:
        definition["phraseList"] = {"phrases": wanted}
    return json.dumps(definition)


def azure_mai_url(endpoint: str, api_version: str = "2025-10-15") -> str:
    """The Fast Transcription address for one Speech resource."""
    return (
        f"{endpoint.rstrip('/')}/speechtotext/transcriptions:transcribe?api-version={api_version}"
    )


def _dig(data: Any, path: Sequence[Any]) -> str:
    """Walk ``path`` (dict keys / list indices) into ``data`` and return a string."""
    cur = data
    for step in path:
        if isinstance(step, int):
            if not isinstance(cur, list) or not (0 <= step < len(cur)):
                return ""
            cur = cur[step]
        else:
            if not isinstance(cur, dict) or step not in cur:
                return ""
            cur = cur[step]
    return str(cur) if cur is not None else ""


def _multipart_body(
    audio_path: Path,
    file_field: str,
    fields: Sequence[tuple[str, str]],
    json_fields: Sequence[tuple[str, str]] = (),
) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    mime_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
    parts: list[bytes] = []
    for name, value in json_fields:
        # Typed, unlike the plain fields below. Azure rejects an untyped part
        # where it expects JSON; every other provider here accepts one.
        disposition = f'Content-Disposition: form-data; name="{name}"'
        parts.append(
            f"--{boundary}\r\n{disposition}\r\n"
            f"Content-Type: application/json\r\n\r\n{value}\r\n".encode()
        )
    for name, value in fields:
        disposition = f'Content-Disposition: form-data; name="{name}"'
        parts.append(f"--{boundary}\r\n{disposition}\r\n\r\n{value}\r\n".encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
        f'filename="{audio_path.name}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode()
        + audio_path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def transcribe_rest(
    spec: RestSpec,
    audio_path: Path,
    api_key: str,
    *,
    language: str | None = None,
    diarize: bool = False,
    endpoint: str = "",
    json_fields: Sequence[tuple[str, str]] = (),
) -> str:
    """Transcribe ``audio_path`` via ``spec`` and return the transcript text.

    Raises :class:`CloudTranscribeError` on any failure with a clean message. The
    endpoint must be HTTPS (enforced); the request uses a verified TLS context.

    ``endpoint`` overrides the spec's, for the one kind whose address is not a
    constant: Azure MAI-Transcribe talks to *your* Speech resource. It is
    checked for HTTPS like any other, and a spec that requires one refuses to
    run without it rather than falling back to a placeholder.
    """
    target = (endpoint or spec.endpoint).strip()
    if spec.endpoint_from_caller and not endpoint.strip():
        raise CloudTranscribeError(
            "This provider needs the address of your own resource, and none "
            "was given. Set it in Settings."
        )
    if not target.lower().startswith("https://"):
        raise CloudTranscribeError("Cloud transcription must use a secure (HTTPS) endpoint.")

    query: list[tuple[str, str]] = list(spec.query)
    extra_fields: list[tuple[str, str]] = list(spec.fields)
    if language and spec.language_field:
        (query if spec.body_mode == "raw" else extra_fields).append((spec.language_field, language))
    if diarize and spec.diarize_field:
        (query if spec.body_mode == "raw" else extra_fields).append((spec.diarize_field, "true"))

    url = target + (f"?{urlencode(query)}" if query else "")
    headers = {spec.key_header: f"{spec.key_scheme}{api_key}"}
    if spec.body_mode == "raw":
        body = audio_path.read_bytes()
        headers["Content-Type"] = (
            mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
        )
    else:
        body, content_type = _multipart_body(
            audio_path,
            spec.file_field,
            extra_fields,
            json_fields=tuple(spec.json_fields) + tuple(json_fields),
        )
        headers["Content-Type"] = content_type

    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, context=_VERIFIED_TLS, timeout=_TIMEOUT_S) as response:  # noqa: S310 - HTTPS enforced above
            raw: str = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code == 401:
            raise CloudTranscribeError("Authentication failed (401). Check the API key.") from exc
        detail = ""
        try:
            detail = exc.read().decode(errors="replace")[:200]
        except Exception:  # noqa: BLE001
            pass
        raise CloudTranscribeError(
            f"The cloud provider returned HTTP {exc.code}. {detail}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - clean message for any transport error
        raise CloudTranscribeError(f"The cloud transcription request failed: {exc}") from exc

    raw = raw.strip()
    if not raw.startswith("{") and not raw.startswith("["):
        return raw  # a plain-text response body
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CloudTranscribeError("The cloud provider returned an unreadable response.") from exc
    text = _dig(data, spec.text_path)
    return text.strip()


__all__ = [
    "CLOUD_REST_SPECS",
    "HOST_ONLY_PROVIDER_KINDS",
    "CloudTranscribeError",
    "RestSpec",
    "azure_mai_definition",
    "azure_mai_url",
    "transcribe_rest",
]
