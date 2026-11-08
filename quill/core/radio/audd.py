"""AudD: a second way to answer "what song is this?", with the listener's own token.

AcoustID (:mod:`quill.core.radio.acoustid`) stays the default: it is free and
open, and only a fingerprint leaves the computer. AudD is the choice for a
listener who wants a commercial recogniser that copes better with live radio
-- talk over an intro, a cross-fade, a station that never sends titles. The
trade is plain and the help says it: **AudD is sent a short clip of the audio
itself**, about twenty seconds of what you just heard, together with your own
AudD API token. Nothing is sent until you choose AudD in Preferences, paste a
token, and press Identify This Song; there is no automatic listening.

The clip is the same one AcoustID fingerprints -- cut from the buffer already
playing, never from a fresh connection (:mod:`quill.core.radio.song_recognition`)
-- only shorter, because AudD needs less and a smaller upload is faster.

The answer is turned into the same :class:`~quill.core.radio.acoustid.Match`
AcoustID's lookup returns, so everything after it -- the spoken sentence, the
song facts -- is shared. AudD gives no confidence score: a match is a match,
and is reported as AudD's answer rather than with a percentage.

The idea, the request and the answer shape come from BlindRadio by serrebidev
(MIT), ``crates/blindradio-core/src/recognize.rs``, and AudD's documentation at
https://docs.audd.io/. One reviewed egress site (:func:`_post`), HTTPS-only
over a verified TLS context with a bounded timeout and size; refused in Safe
Mode. wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import ssl
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import radio_credentials
from quill.core.radio.acoustid import Match

_ENDPOINT = "https://api.audd.io/"
_TIMEOUT_SECONDS = 30.0
_MAX_ANSWER_BYTES = 1_000_000
#: AudD's standard endpoint refuses files over 10 MB.
MAX_SAMPLE_BYTES = 10 * 1024 * 1024

#: Seconds of the buffer sent to AudD.
SAMPLE_SECONDS = 20

#: Where a listener gets a token.
DASHBOARD_URL = "https://dashboard.audd.io/"

NO_TOKEN_SENTENCE = (
    "Song recognition is set to AudD, and no AudD API token has been entered. "
    f"Get one at {DASHBOARD_URL}, then paste it into Preferences, in the AudD "
    "API token box. Or set Song recognition service back to AcoustID."
)

NO_MATCH = (
    "AudD found no match for this song. Talk, a live performance or a "
    "station's own jingle will not match, so try again in a minute."
)

#: AudD's documented error numbers: 900 a token it does not know, 901 no token
#: and the free limit used up, 300 a sample too short to fingerprint.
_BAD_TOKEN_CODES = frozenset({900})
_LIMIT_CODES = frozenset({901})
_TOO_SHORT_CODES = frozenset({300})


class AudDError(CodedError):
    """An AudD request failed, or was refused."""

    code = "QUILL-RADIO-AUDD-LOOKUP"
    listener_facing = True


def stored_token() -> str:
    return radio_credentials.load(radio_credentials.AUDD_TOKEN).secret


def save_token(value: str) -> bool:
    return radio_credentials.save(radio_credentials.AUDD_TOKEN, value)


def build_body(token: str, sample: bytes, *, boundary: str = "") -> tuple[bytes, str]:
    """``(multipart body, content type)`` for one recognition (pure)."""
    mark = boundary or f"quill-{uuid.uuid4().hex}"
    lines = [
        f"--{mark}".encode(),
        b'Content-Disposition: form-data; name="api_token"',
        b"",
        token.encode("utf-8"),
        f"--{mark}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="sample"',
        b"Content-Type: application/octet-stream",
        b"",
        sample,
        f"--{mark}--".encode(),
        b"",
    ]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={mark}"


def _post(body: bytes, content_type: str) -> str:
    """One HTTPS POST to AudD -- the reviewed egress site."""
    request = urllib.request.Request(
        _ENDPOINT,
        data=body,
        method="POST",
        headers={
            "User-Agent": http_client.user_agent(),
            "Accept": "application/json",
            "Content-Type": content_type,
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            payload: bytes = resp.read(_MAX_ANSWER_BYTES)
    except urllib.error.HTTPError as error:
        try:
            return error.read(_MAX_ANSWER_BYTES).decode("utf-8", errors="replace")
        except OSError:
            raise AudDError(f"AudD refused the request ({error.code}).") from error
    except (
        urllib.error.URLError,
        TimeoutError,
        ssl.SSLError,
        OSError,
        http.client.HTTPException,
    ) as error:
        raise AudDError("Could not reach AudD. Check the internet connection.") from error
    return payload.decode("utf-8", errors="replace")


def parse_answer(json_text: str) -> list[Match]:
    """AudD's answer as matches: one, or none for an honest miss (pure).

    Raises :class:`AudDError` when AudD answered with an error -- above all a
    rejected token, which is a different sentence from "no match".
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError) as error:
        raise AudDError("AudD's answer could not be read.") from error
    if not isinstance(data, dict):
        raise AudDError("AudD's answer could not be read.")
    if data.get("status") != "success":
        raw = data.get("error")
        problem: dict[str, object] = raw if isinstance(raw, dict) else {}
        try:
            code = int(str(problem.get("error_code", 0) or 0))
        except ValueError:
            code = 0
        if code in _BAD_TOKEN_CODES:
            raise AudDError(
                "AudD did not accept the API token. Check it in Preferences, or "
                f"get a new one at {DASHBOARD_URL}."
            )
        if code in _LIMIT_CODES:
            raise AudDError(
                "AudD says its free limit is used up and no API token reached it. "
                "Check the AudD API token in Preferences."
            )
        if code in _TOO_SHORT_CODES:
            return []
        message = str(problem.get("error_message", "") or "").strip()
        raise AudDError(f"AudD could not recognise that{': ' + message if message else ''}.")
    result = data.get("result")
    if isinstance(result, list):
        result = result[0] if result else None
    if not isinstance(result, dict):
        return []
    title = str(result.get("title", "") or "").strip()
    if not title:
        return []
    return [
        Match(
            title=title,
            artist=str(result.get("artist", "") or "").strip(),
            score=1.0,
            album=str(result.get("album", "") or "").strip(),
        )
    ]


def identify(
    token: str,
    sample: bytes,
    *,
    safe_mode: bool = False,
    post: Callable[[bytes, str], str] | None = None,
) -> list[Match]:
    """Ask AudD what *sample* is. An empty list is an honest "no match"."""
    if safe_mode:
        raise AudDError(
            "Song recognition is disabled in Safe Mode. Restart Quill Radio normally to use it."
        )
    if not token.strip():
        raise AudDError(NO_TOKEN_SENTENCE)
    if not sample:
        raise AudDError("There was no audio to send to AudD.")
    if len(sample) > MAX_SAMPLE_BYTES:
        raise AudDError("The sample is too large for AudD. Try again in a moment.")
    body, content_type = build_body(token.strip(), sample)
    sender = post if post is not None else _post
    return parse_answer(sender(body, content_type))


__all__ = [
    "DASHBOARD_URL",
    "NO_MATCH",
    "NO_TOKEN_SENTENCE",
    "SAMPLE_SECONDS",
    "AudDError",
    "build_body",
    "identify",
    "parse_answer",
    "save_token",
    "stored_token",
]
