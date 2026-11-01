"""The two outbound calls a ChatGPT subscription needs, and nothing else.

One module, two egress sites (both recorded in
:mod:`quill.tools.network_egress_entries`): a JSON request that answers at
once, and a streaming POST that answers line by line. OpenAI's plan-sharing
preview *requires* ``stream=true`` on the Responses API, so the second is not an
optimisation -- it is the only shape the service accepts.

Everything here raises the coded errors in :mod:`quill.core.ai.chatgpt_errors`
rather than a bare ``URLError``, so every surface above hears a sentence written
for a person. The ``opener`` is injectable, which is how the parsing is tested
without a socket.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

from quill.core.ai.chatgpt_errors import (
    ChatGptBusyError,
    ChatGptError,
    ChatGptLimitError,
    ChatGptSignedOutError,
    ChatGptUnsupportedError,
    ChatGptUsageUnavailableError,
)
from quill.core.ai.retry_ladder import pause, wait_before_retry

__all__ = ["Opener", "StreamOpener", "get_json", "post_json", "stream_sse"]

#: Performs one prepared request and returns ``(status, body)`` -- or
#: ``(status, body, headers)``, which lets a ``Retry-After`` be honoured.
#: Injected for tests.
Opener = Callable[[urllib.request.Request], "tuple[int, bytes] | tuple[int, bytes, Any]"]
#: Performs one prepared request and yields the raw response lines. Injected for tests.
StreamOpener = Callable[[urllib.request.Request], Iterator[bytes]]

_USER_AGENT = "QUILL"
_TIMEOUT_SECONDS = 30.0
#: A long answer on a busy model can take a while; the read timeout is per
#: chunk, not per response, so a stream that is still arriving never trips it.
_STREAM_TIMEOUT_SECONDS = 300.0


def _request(
    url: str, *, token: str, body: dict[str, Any] | None, method: str
) -> urllib.request.Request:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", _USER_AGENT)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    return request


def _context(url: str) -> ssl.SSLContext | None:
    from quill.core.net import verified_ssl_context

    return verified_ssl_context() if url.lower().startswith("https") else None


def _real_opener(request: urllib.request.Request) -> tuple[int, bytes, Any]:
    try:
        with urllib.request.urlopen(  # noqa: S310 - https enforced by _context
            request, timeout=_TIMEOUT_SECONDS, context=_context(request.full_url)
        ) as response:
            return int(response.status or 200), response.read(), response.headers
    except urllib.error.HTTPError as error:
        return int(error.code), error.read(), error.headers


def _real_stream_opener(request: urllib.request.Request) -> Iterator[bytes]:
    try:
        response = urllib.request.urlopen(  # noqa: S310 - https enforced by _context
            request, timeout=_STREAM_TIMEOUT_SECONDS, context=_context(request.full_url)
        )
    except urllib.error.HTTPError as error:
        raise _http_failure(
            int(error.code), error.read(), request.full_url, error.headers
        ) from error
    with response:
        yield from response


def _unreachable(url: str, error: BaseException) -> ChatGptError:
    host = urllib.parse.urlsplit(url).hostname or "OpenAI"
    reason = getattr(error, "reason", error)
    detail = str(reason).strip() or type(reason).__name__
    if isinstance(reason, ssl.SSLError):
        return ChatGptError(
            f"QUILL reached {host} but could not make a secure connection ({detail}). "
            "Nothing was sent."
        )
    if isinstance(reason, socket.gaierror):
        return ChatGptError(
            f"QUILL could not look up the address {host}, which usually means this "
            f"computer is offline ({detail}). Nothing was sent."
        )
    if isinstance(reason, TimeoutError):
        return ChatGptError(f"{host} did not answer in time ({detail}).")
    return ChatGptError(f"QUILL could not connect to {host} ({detail}). Nothing was sent.")


def _error_for_status(status: int, raw: bytes, url: str) -> ChatGptError:
    """The right coded error for an HTTP failure, keeping OpenAI's own words."""
    text = raw.decode("utf-8", errors="replace").strip()
    message = ""
    try:
        payload = json.loads(text) if text else {}
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip()
            code = str(error.get("code", "")).strip()
            if code == "subscription_sharing_usage_limit_exceeded":
                return ChatGptLimitError(message or "Your ChatGPT plan's usage limit was reached.")
            if code == "subscription_sharing_usage_unavailable":
                return ChatGptUsageUnavailableError(
                    message or "ChatGPT plan usage is not available right now."
                )
            if code == "subscription_sharing_unsupported_capability":
                return ChatGptUnsupportedError(
                    message or "Your ChatGPT plan does not take this request."
                )
        elif isinstance(error, str):
            message = error.strip()
    except ValueError:
        message = text[:200]
    host = urllib.parse.urlsplit(url).hostname or "OpenAI"
    if status == 401:
        return ChatGptSignedOutError(
            message or "OpenAI no longer accepts this computer's ChatGPT sign-in."
        )
    if status == 429:
        return ChatGptBusyError(message or "OpenAI is asking QUILL to slow down for a moment.")
    return ChatGptError(f"{host} answered {status}. {message}".strip())


def _http_failure(status: int, raw: bytes, url: str, headers: Any) -> ChatGptError:
    """:func:`_error_for_status`, remembering what the retry ladder needs.

    The status and headers ride on the error so :func:`stream_sse` can ask
    :func:`~quill.core.ai.retry_ladder.wait_before_retry` about a refusal that
    arrived before any of the answer did. A plan whose usage is used up is
    final: asking again cannot help until the plan resets. Plan usage that is
    only *unavailable* (503 ``subscription_sharing_usage_unavailable``) gets
    the bounded retry OpenAI's errors-and-recovery page asks for (10A.5).
    """
    error = _error_for_status(status, raw, url)
    error.http_status = status  # type: ignore[attr-defined]
    error.http_headers = headers  # type: ignore[attr-defined]
    error.retry_final = (  # type: ignore[attr-defined]
        b"subscription_sharing_usage_limit_exceeded" in raw
        or b"subscription_sharing_unsupported_capability" in raw
    )
    return error


def get_json(url: str, *, token: str = "", opener: Opener | None = None) -> dict[str, Any]:
    """GET *url* and return the parsed JSON object."""
    return _exchange(_request(url, token=token, body=None, method="GET"), opener)


def post_json(
    url: str, body: dict[str, Any], *, token: str = "", opener: Opener | None = None
) -> dict[str, Any]:
    """POST *body* as JSON to *url* and return the parsed JSON object."""
    return _exchange(_request(url, token=token, body=body, method="POST"), opener)


def _exchange(request: urllib.request.Request, opener: Opener | None) -> dict[str, Any]:
    """One request, asked again on a busy answer when it is a GET.

    Only a GET climbs the retry ladder (:mod:`quill.core.ai.retry_ladder`):
    reading the model list twice costs nothing, while a POST here is a
    sign-in exchange whose one-time code a second attempt would only spend.
    """
    run = opener or _real_opener
    attempt = 0
    while True:
        attempt += 1
        try:
            result = run(request)
        except urllib.error.URLError as error:
            raise _unreachable(request.full_url, error) from error
        except (TimeoutError, OSError) as error:
            raise _unreachable(request.full_url, error) from error
        status, raw = int(result[0]), result[1]
        headers = result[2] if len(result) > 2 else None
        if status < 400:
            break
        failure = _http_failure(status, raw, request.full_url, headers)
        wait = (
            wait_before_retry(status, headers, attempt, final=failure.retry_final)  # type: ignore[attr-defined]
            if request.get_method() == "GET"
            else None
        )
        if wait is None:
            raise failure
        pause(wait)
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except ValueError as error:
        raise ChatGptError("OpenAI sent back something QUILL could not read.") from error
    return parsed if isinstance(parsed, dict) else {}


def stream_sse(
    url: str,
    body: dict[str, Any],
    *,
    token: str,
    on_event: Callable[[str, dict[str, Any]], None],
    stop: Callable[[], bool] | None = None,
    opener: StreamOpener | None = None,
) -> None:
    """POST *body* and hand every server-sent event to *on_event* as it arrives.

    *on_event* receives ``(type, payload)``; *type* is the payload's own
    ``type`` field, or the SSE ``event:`` line when the payload has none. *stop*
    is polled between lines: when it answers True the connection is closed and
    :class:`ChatGptError` says the generation was stopped, which is the caller's
    own doing and reported as such.
    """
    request = _request(url, token=token, body=body, method="POST")
    run = opener or _real_stream_opener
    attempt = 0
    while True:
        attempt += 1
        try:
            _read_stream(run, request, url, on_event, stop)
            return
        except ChatGptError as error:
            # A refusal before anything arrived climbs the shared ladder; once
            # an event has been handed on, the answer is under way and a
            # second request could be charged twice, so never then.
            status = getattr(error, "http_status", None)
            if status is None:
                raise
            wait = wait_before_retry(
                int(status),
                getattr(error, "http_headers", None),
                attempt,
                final=bool(getattr(error, "retry_final", False)),
            )
            if wait is None or (stop is not None and stop()):
                raise
            pause(wait)


def _read_stream(
    run: StreamOpener,
    request: urllib.request.Request,
    url: str,
    on_event: Callable[[str, dict[str, Any]], None],
    stop: Callable[[], bool] | None,
) -> None:
    """One streamed attempt: every event to *on_event* as it arrives."""
    event = ""
    data: list[str] = []

    def emit() -> None:
        if not data:
            return
        raw = "\n".join(data)
        if raw == "[DONE]":
            return
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"raw": raw}
        if not isinstance(payload, dict):
            payload = {"raw": raw}
        on_event(str(payload.get("type") or event or "unknown"), payload)

    try:
        for raw_line in run(request):
            if stop is not None and stop():
                raise ChatGptError("Generation stopped.")
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                emit()
                event = ""
                data = []
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        emit()
    except urllib.error.URLError as error:
        raise _unreachable(url, error) from error
    except (TimeoutError, OSError) as error:
        raise _unreachable(url, error) from error
