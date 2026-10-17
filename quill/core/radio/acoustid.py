"""AcoustID: which recording a Chromaprint fingerprint belongs to.

The open, licensed-for-this route to "what song is this?" (xradio2.md 4.1),
chosen over the private Shazam endpoint FreeRadio talks to: AcoustID publishes
its lookup service for exactly this, and its answers are MusicBrainz recording
ids, which Quill Radio already knows how to use.

**It needs an application key, and there is none by default.** AcoustID asks
every application to register (free) for a client key. Until one is entered,
recognition is a command that says plainly what it needs and where to put it --
never a hidden menu item, never an error. The key lives in the Windows
credential store like every other key QUILL holds, never in a settings file.

**Only on request.** Nothing here runs unless the listener presses Identify
This Song, and what is sent is the key, a fingerprint and its length -- a
summary of a few seconds of sound that cannot be played back -- and nothing
about the listener or the station.

One reviewed egress site (:func:`_post`), HTTPS-only over a verified TLS
context with a bounded timeout and size; refused in Safe Mode. wx-free,
strict-typed.
"""

from __future__ import annotations

import gzip
import http.client
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

_ENDPOINT = "https://api.acoustid.org/v2/lookup"
_TIMEOUT_SECONDS = 20.0
_MAX_BYTES = 1_000_000

#: Where an application key is registered, free.
REGISTER_URL = "https://acoustid.org/new-application"

#: Where the key lives in the platform credential store.
CREDENTIAL_KEY = "quill:radio:acoustid:key"

#: What Identify This Song says when no key has been entered.
NO_KEY_SENTENCE = (
    "Song recognition needs a free AcoustID application key, and none has been "
    f"entered. Register one at {REGISTER_URL}, then paste it into Preferences, "
    "in the AcoustID key box."
)

#: AcoustID's error code for a client key it does not recognise.
_INVALID_KEY_CODE = 4


class AcoustIdError(CodedError):
    """An AcoustID lookup failed, or was refused."""

    code = "QUILL-RADIO-ACOUSTID-LOOKUP"
    listener_facing = True


@dataclass(frozen=True, slots=True)
class Match:
    """One recording AcoustID thinks the fingerprint belongs to."""

    title: str
    artist: str
    #: AcoustID's confidence, 0.0 to 1.0.
    score: float
    recording_id: str = ""

    def spoken(self) -> str:
        """``"Song by Artist"``, or just the title when no artist was given."""
        return f"{self.title} by {self.artist}" if self.artist else self.title


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`AcoustIdError` when Safe Mode is active."""
    if safe_mode:
        raise AcoustIdError(
            "Song recognition is disabled in Safe Mode. Restart Quill Radio normally to use it."
        )


def stored_key() -> str:
    """The AcoustID key from the platform credential store, or ``""``."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential
    except ImportError:
        return ""
    try:
        found = load_generic_credential(CREDENTIAL_KEY)
    except OSError:  # pragma: no cover - platform dependent
        return ""
    return str(getattr(found, "secret", "") or "").strip() if found is not None else ""


def save_key(value: str) -> bool:
    """Store *value* as the key, or remove the key when it is blank.

    True when the store accepted the change. A computer with no credential
    store keeps no key rather than writing one somewhere less safe.
    """
    try:
        from quill.platform.windows.credential_manager import (
            delete_generic_credential,
            save_generic_credential,
        )
    except ImportError:
        return False
    try:
        if value.strip():
            save_generic_credential(CREDENTIAL_KEY, value.strip())
        else:
            delete_generic_credential(CREDENTIAL_KEY)
    except OSError:  # pragma: no cover - platform dependent
        return False
    return True


def build_lookup_body(key: str, fingerprint: str, duration: int) -> bytes:
    """The form body of one lookup (pure). POSTed, because fingerprints are long."""
    return urllib.parse.urlencode({
        "client": key,
        "format": "json",
        "meta": "recordings",
        "duration": str(int(duration)),
        "fingerprint": fingerprint,
    }).encode("ascii")


def _post(body: bytes) -> str:
    """One HTTPS POST to AcoustID's lookup endpoint -- the reviewed egress site."""
    request = urllib.request.Request(
        _ENDPOINT,
        data=body,
        method="POST",
        headers={
            "User-Agent": http_client.user_agent(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            encoding = str(resp.headers.get("Content-Encoding", "") or "").lower()
    except urllib.error.HTTPError as error:
        # AcoustID answers a rejected key with a 400 *and* a JSON body that says
        # why; read it so the listener hears "key not accepted" rather than a
        # status code.
        try:
            return error.read(_MAX_BYTES).decode("utf-8", errors="replace")
        except OSError:
            raise AcoustIdError(f"AcoustID refused the request ({error.code}).") from error
    except (
        urllib.error.URLError,
        TimeoutError,
        ssl.SSLError,
        OSError,
        http.client.HTTPException,
    ) as error:
        raise AcoustIdError("Could not reach AcoustID. Check the internet connection.") from error
    if encoding == "gzip":
        try:
            payload = gzip.decompress(payload)
        except OSError as error:
            raise AcoustIdError("AcoustID's answer could not be read.") from error
    return payload.decode("utf-8", errors="replace")


def parse_lookup(json_text: str) -> list[Match]:
    """Every recording in a lookup answer, best first (pure).

    Raises :class:`AcoustIdError` when AcoustID answered with an error -- above
    all a rejected key, which is a different sentence from "no match".
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError) as error:
        raise AcoustIdError("AcoustID's answer could not be read.") from error
    if not isinstance(data, dict):
        raise AcoustIdError("AcoustID's answer could not be read.")
    if data.get("status") != "ok":
        raw_problem = data.get("error")
        problem: dict[str, object] = raw_problem if isinstance(raw_problem, dict) else {}
        if problem.get("code") == _INVALID_KEY_CODE:
            raise AcoustIdError(
                "AcoustID did not accept the application key. Check it in Preferences, "
                f"or register a new one at {REGISTER_URL}."
            )
        message = str(problem.get("message", "") or "").strip()
        raise AcoustIdError(f"AcoustID could not look that up{': ' + message if message else ''}.")
    matches: list[Match] = []
    for result in data.get("results", []) or []:
        if not isinstance(result, dict):
            continue
        try:
            score = float(result.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        for recording in result.get("recordings", []) or []:
            if not isinstance(recording, dict):
                continue
            title = str(recording.get("title", "") or "").strip()
            if not title:
                continue
            artists = [
                str(artist.get("name", "") or "").strip()
                for artist in recording.get("artists", []) or []
                if isinstance(artist, dict)
            ]
            matches.append(
                Match(
                    title=title,
                    artist=", ".join(name for name in artists if name),
                    score=max(0.0, min(1.0, score)),
                    recording_id=str(recording.get("id", "") or ""),
                )
            )
    matches.sort(key=lambda match: match.score, reverse=True)
    return matches


def lookup(
    key: str,
    fingerprint: str,
    duration: int,
    *,
    safe_mode: bool = False,
    post: Callable[[bytes], str] | None = None,
) -> list[Match]:
    """Ask AcoustID which recordings *fingerprint* matches. Best first.

    An empty list is an honest "no match". Raises :class:`AcoustIdError` for a
    missing or rejected key, Safe Mode, or a network failure.
    """
    refuse_in_safe_mode(safe_mode)
    if not key.strip():
        raise AcoustIdError(NO_KEY_SENTENCE)
    sender = post if post is not None else _post
    return parse_lookup(sender(build_lookup_body(key.strip(), fingerprint, duration)))
