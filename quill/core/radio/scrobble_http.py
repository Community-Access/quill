"""The one HTTPS POST behind scrobbling: ListenBrainz, last.fm and Libre.fm.

Every scrobbling request goes through :func:`post`, the reviewed egress site
(``network_egress_entries_radio_listening``). It is reached only after the
listener has turned a service on in Preferences and signed in or pasted their
own token, and it is refused in Safe Mode. HTTPS only, over a verified TLS
context, with a bounded timeout and answer size.

An HTTP error is not an exception here: both services explain a refusal in the
body (a bad token, a rate limit), and the caller decides what that means for
the songs waiting. Only "could not reach the server" raises. Credit for the
idea of scrobbling from a radio player: BlindRadio by serrebidev (MIT).
wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

_TIMEOUT_SECONDS = 20.0
_MAX_BYTES = 1_000_000


class ScrobbleNetworkError(CodedError):
    """A scrobbling service could not be reached, or Safe Mode refused it."""

    code = "QUILL-RADIO-SCROBBLE-NETWORK"


@dataclass(frozen=True, slots=True)
class Reply:
    status: int
    text: str


def post(
    url: str,
    body: bytes,
    *,
    content_type: str,
    headers: dict[str, str] | None = None,
    safe_mode: bool = False,
) -> Reply:
    """POST *body* to *url* and return the status and text, whatever the status."""
    if safe_mode:
        raise ScrobbleNetworkError("Scrobbling is turned off in Safe Mode.")
    if not url.startswith("https://"):
        raise ScrobbleNetworkError("Scrobbling only talks to secure (https) addresses.")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": http_client.user_agent(),
            "Accept": "application/json",
            "Content-Type": content_type,
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return Reply(
                int(getattr(resp, "status", 200) or 200), payload.decode("utf-8", "replace")
            )
    except urllib.error.HTTPError as error:
        try:
            text = error.read(_MAX_BYTES).decode("utf-8", errors="replace")
        except OSError:
            text = ""
        return Reply(int(error.code), text)
    except (
        urllib.error.URLError,
        TimeoutError,
        ssl.SSLError,
        OSError,
        http.client.HTTPException,
    ) as error:
        raise ScrobbleNetworkError("The scrobbling service could not be reached.") from error


__all__ = ["Reply", "ScrobbleNetworkError", "post"]
