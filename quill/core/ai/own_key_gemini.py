"""AI help on the user's own Google Gemini key: one streamed request, stoppable.

The Gemini half of :mod:`quill.core.ai.own_key` (qc.md X-07). A request goes to
``/v1beta/models/{model}:streamGenerateContent?alt=sse`` on Google's host, with
the key in the ``x-goog-api-key`` header -- never in the URL, where it would end
up in a proxy's log -- and the instructions in ``systemInstruction``, the same
words the free service and the OpenAI route use. The URL, the headers, the body
and the reading of each Server-Sent Event are QUILL's existing pure builders
(:mod:`quill.core.ai.endpoints`, :func:`~quill.core.assistant_ai.build_chat_body`,
:func:`~quill.core.assistant_ai.iter_stream_text`); what is here is only what the
own-key route needs on top of them:

* **Stopping.** The answer arrives in pieces, and a set ``cancel`` event is
  checked before every line is read, so Stop closes the connection part way
  rather than waiting for the whole answer to be generated and discarded.
* **Sentences, not status codes.** Gemini answers a wrong key with HTTP 400 and
  ``API_KEY_INVALID`` -- not 401 -- so "check your key" has to be recognised
  from the body. Every failure becomes one plain sentence that says what to do,
  and none of them ever repeats the key (:func:`quill.core.ai.own_key.scrub`).
* **HTTPS only**, certificate-checked. Plain HTTP is refused unless the host is
  this computer's loopback address, which only the tests use.

One egress site, :func:`_open_stream`, reviewed in
``quill/tools/network_egress_entries.py``. wx-free.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from quill.core.ai.own_key import (
    GEMINI,
    OwnKeyCancelled,
    OwnKeyError,
    OwnKeyRejected,
    scrub,
)

__all__ = ["GEMINI_HOST", "KEY_PAGE_URL", "USAGE_URL", "stream_answer"]

GEMINI_HOST = "https://generativelanguage.googleapis.com"

#: Where a person creates a Gemini key, and where its usage is.
KEY_PAGE_URL = "https://aistudio.google.com/apikey"
USAGE_URL = "https://aistudio.google.com/usage"

_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})

#: Server errors worth one more try, if nothing has arrived yet.
_TRY_AGAIN = frozenset({500, 502, 503, 504})


class _Busy(OwnKeyError):
    """Gemini was busy before it sent anything; one more try is allowed."""

    code = "QUILL-AI-OWN-KEY-GEMINI-BUSY"


def _stop_if_cancelled(cancel: Any) -> None:
    if cancel is not None and cancel.is_set():
        raise OwnKeyCancelled("Stopped. Nothing more will arrive from this request.")


def _secure(host: str) -> None:
    parsed = urlparse(host)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and (parsed.hostname or "") in _LOOPBACK:
        return
    raise OwnKeyError("Google Gemini can only be reached over HTTPS. Nothing was sent.")


def _detail(error: HTTPError, key: str) -> str:
    """Gemini's own message from an error body, without the key, or ""."""
    try:
        parsed = json.loads(error.read().decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 - best effort: the status still speaks
        return ""
    body = parsed.get("error") if isinstance(parsed, dict) else None
    if not isinstance(body, dict):
        return ""
    parts = [str(body.get("message", "") or ""), str(body.get("status", "") or "")]
    for detail in body.get("details") or []:
        if isinstance(detail, dict):
            parts.append(str(detail.get("reason", "") or ""))
    return scrub(" ".join(part for part in parts if part).strip(), key)[:300]


def _failure(error: HTTPError, model: str, key: str) -> OwnKeyError:
    """One sentence for what an HTTP failure means, and what to do about it."""
    status = error.code
    detail = _detail(error, key)
    lowered = detail.lower()
    if status in (401, 403) or "api_key_invalid" in lowered or "api key" in lowered:
        return OwnKeyRejected(
            "Google Gemini did not accept the saved key. It may be mistyped, revoked, "
            "or not allowed to use the Gemini API."
        )
    if status == 404:
        return OwnKeyError(
            f"Google Gemini does not offer the model {model} to this key. Choose "
            "another model in Use My Own API Key."
        )
    if status == 429:
        return OwnKeyError(
            "Google Gemini says this key has reached its rate limit or quota. Wait a "
            "minute and try again, or check the key's plan in Google AI Studio."
        )
    if status in _TRY_AGAIN or status >= 500:
        return _Busy("Google Gemini is busy or not answering right now. Try again in a moment.")
    said = f" Google said: {detail}" if detail else ""
    return OwnKeyError(f"Google Gemini refused the request (HTTP {status}).{said}")


def _watched(lines: Iterable[bytes], cancel: Any) -> Iterator[bytes]:
    """Each raw line, checking for Stop *before* each read, not after it."""
    iterator = iter(lines)
    while True:
        _stop_if_cancelled(cancel)
        try:
            line = next(iterator)
        except StopIteration:
            return
        yield line


def _open_stream(
    endpoint: str,
    headers: dict[str, str],
    body: bytes,
    *,
    timeout: float,
    cancel: Any,
    on_delta: Callable[[str], None] | None,
) -> str:
    """POST once and read the streamed answer. The one egress site."""
    from quill.core.assistant_ai import iter_stream_text
    from quill.core.net import verified_ssl_context

    context = verified_ssl_context() if endpoint.startswith("https:") else None
    request = Request(endpoint, data=body, headers=headers, method="POST")
    pieces: list[str] = []
    with urlopen(request, timeout=timeout, context=context) as response:
        for delta in iter_stream_text(GEMINI, _watched(response, cancel)):
            pieces.append(delta)
            if on_delta is not None:
                on_delta(delta)
    return "".join(pieces)


def stream_answer(
    key: str,
    model: str,
    system: str,
    user: str,
    *,
    cancel: Any = None,
    host: str = "",
    timeout: float = 120.0,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Ask Gemini *model* with *key*, and return the whole answer. Blocking.

    Raises :class:`OwnKeyCancelled` once *cancel* is set, :class:`OwnKeyRejected`
    for a key Gemini refuses, and :class:`OwnKeyError` for anything else -- each
    with a sentence for a person and never the key. *host* is for tests; empty
    means :data:`GEMINI_HOST`, read at call time.
    """
    from quill.core.ai.endpoints import stream_chat_endpoint
    from quill.core.assistant_ai import build_chat_body, build_chat_headers

    if not (key or "").strip():
        raise OwnKeyError("No Google Gemini key is saved on this computer. Nothing was sent.")
    if _safe_mode():
        raise OwnKeyError("AI help is switched off in Safe Mode. Nothing was sent.")
    host = host or GEMINI_HOST
    _secure(host)
    _stop_if_cancelled(cancel)
    endpoint = stream_chat_endpoint(GEMINI, host, model)
    headers = build_chat_headers(GEMINI, host, key)
    payload = build_chat_body(GEMINI, model, user, max_tokens=None, system_prompt=system)
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(2):
        try:
            text = _open_stream(
                endpoint, headers, body, timeout=timeout, cancel=cancel, on_delta=on_delta
            )
        except HTTPError as error:
            failure = _failure(error, model, key)
            if isinstance(failure, _Busy) and attempt == 0:
                _pause(cancel, 1.0)
                continue
            raise failure from None
        except (URLError, TimeoutError, OSError):
            _stop_if_cancelled(cancel)
            raise OwnKeyError(
                "Google Gemini could not be reached. Check the internet connection and try again."
            ) from None
        _stop_if_cancelled(cancel)
        if not text.strip():
            raise OwnKeyError(
                "Google Gemini sent back no answer. It may have declined the request; "
                "try rewording it, or choose another model."
            )
        return text.strip()
    raise OwnKeyError("Google Gemini is busy or not answering right now. Try again in a moment.")


def _pause(cancel: Any, seconds: float) -> None:
    """Wait before the one retry, but not past a Stop."""
    if cancel is not None:
        if cancel.wait(seconds):
            _stop_if_cancelled(cancel)
        return
    time.sleep(seconds)


def _safe_mode() -> bool:
    from quill.core.assistant_ai import _safe_mode_active

    return bool(_safe_mode_active())
