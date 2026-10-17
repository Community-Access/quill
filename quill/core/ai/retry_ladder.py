"""One retry ladder for every AI provider QUILL talks to.

QUILL reaches AI over four routes -- its own free hosted service
(:mod:`quill.core.ai.gateway_client`), the person's own OpenAI or compatible
key (:mod:`quill.core.assistant_ai`), their own Google Gemini key
(:mod:`quill.core.ai.own_key_gemini`) and a ChatGPT plan
(:mod:`quill.core.ai.chatgpt_http`). Before 2026-10-17 each had its own idea
of trying again: one tried twice on a 5xx, one three times on a different set
of codes with a different schedule, two never did. A busy moment at the
provider read as four different products.

This module is the one answer, and every route asks it the same question --
"this attempt failed with *status* and these headers; wait how long, or
stop?" -- through :func:`wait_before_retry`:

* **Three attempts in all** (:data:`MAX_ATTEMPTS`), on the statuses that mean
  "ask again shortly" (:data:`RETRY_STATUSES`): 408 Request Timeout, 409
  Conflict, 429 Too Many Requests, and 500, 502, 503 and 504.
* **Linear backoff**, one second then two (:data:`STEP_SECONDS`) -- unless the
  service said how long with ``Retry-After`` (seconds or an HTTP date), which
  is honoured. A service asking for longer than :data:`LONGEST_WAIT_SECONDS`
  is not waited for: somebody is listening to silence, so the failure is said
  now instead, in the service's own words.
* **Never twice when the API says no.** A response carrying
  ``x-should-retry: false`` is the provider saying that repeating this request
  is unsafe -- typically because it may already have been carried out and
  charged. That is final, whatever the status. A caller that knows more (the
  hosted service says so in its reply body) passes ``final=True``.
* **Only the last failure is heard.** Retries are silent; the caller raises or
  reports exactly once, after the ladder gives up (GATE-13: a "trying again"
  the listener cannot act on is noise).

The egress sites themselves do not move -- each route keeps its one reviewed
``urlopen`` (:mod:`quill.tools.network_egress_entries`) and loops around it.

``sleep`` is resolved when a wait happens, never captured at import, so a test
that patches :func:`time.sleep` really does skip the wait. wx-free,
strict-typed.
"""

from __future__ import annotations

import email.utils
import time
from collections.abc import Callable, Mapping
from typing import Any

__all__ = [
    "LONGEST_WAIT_SECONDS",
    "MAX_ATTEMPTS",
    "RETRY_STATUSES",
    "STEP_SECONDS",
    "api_forbids_retry",
    "pause",
    "retry_after_seconds",
    "wait_after_failure",
    "wait_before_retry",
]

#: Every route makes at most this many attempts at one request.
MAX_ATTEMPTS = 3

#: The statuses worth asking again. Every other 4xx says the request itself
#: is wrong, and a retry would only make the same answer arrive later.
RETRY_STATUSES: frozenset[int] = frozenset({408, 409, 429, 500, 502, 503, 504})

#: Linear backoff: the wait after attempt *n* is ``n * STEP_SECONDS``.
STEP_SECONDS = 1.0

#: The longest ``Retry-After`` a person is asked to sit through in silence.
LONGEST_WAIT_SECONDS = 20.0


def _header(headers: Any, name: str) -> str:
    """One header's value from a ``Message``, a dict or ``None``; "" if absent."""
    if headers is None:
        return ""
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    value = getter(name)
    if value is None and isinstance(headers, Mapping):
        lowered = name.lower()
        for key, candidate in headers.items():
            if str(key).lower() == lowered:
                value = candidate
                break
    return str(value or "").strip()


def retry_after_seconds(value: str, *, now: float | None = None) -> float | None:
    """``Retry-After`` as seconds from now, or ``None`` when absent or unreadable.

    Both forms the standard allows: a number of seconds, or an HTTP date. A
    date already past means "now" (0).
    """
    text = (value or "").strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    current = time.time() if now is None else now
    return max(0.0, when.timestamp() - current)


def api_forbids_retry(headers: Any) -> bool:
    """True when the response says repeating this request is unsafe."""
    return _header(headers, "x-should-retry").lower() == "false"


def wait_before_retry(
    status: int,
    headers: Any,
    attempt: int,
    *,
    final: bool = False,
    max_attempts: int = MAX_ATTEMPTS,
    now: float | None = None,
) -> float | None:
    """Seconds to wait before trying again after *attempt* failed, or ``None``.

    *attempt* counts from 1. ``None`` means stop and report this failure: the
    ladder has run out, the status is not one worth repeating, the API said
    not to (or *final* says the caller knows it must not), or the service
    asked for a longer pause than anyone should wait through.
    """
    if final or attempt >= max_attempts or int(status) not in RETRY_STATUSES:
        return None
    if api_forbids_retry(headers):
        return None
    asked = retry_after_seconds(_header(headers, "retry-after"), now=now)
    if asked is not None:
        return None if asked > LONGEST_WAIT_SECONDS else asked
    return STEP_SECONDS * attempt


def wait_after_failure(
    status: int | None,
    headers: Any,
    attempt: int,
    max_attempts: int = MAX_ATTEMPTS,
    *,
    lost: bool = False,
) -> float | None:
    """:func:`wait_before_retry` for a failure that may have had no answer.

    With a *status* the server answered, and the ladder decides. Without one
    the request never got an answer; *lost* says it is the kind worth asking
    again -- a timeout, or a server on this computer still starting -- and it
    climbs the same linear steps. Anything else (a refused certificate, a
    name that does not resolve) is final at once.
    """
    if status is not None:
        return wait_before_retry(status, headers, attempt, max_attempts=max_attempts)
    if lost and attempt < max_attempts:
        return STEP_SECONDS * attempt
    return None


def pause(
    seconds: float, *, cancel: Any = None, sleep: Callable[[float], None] | None = None
) -> bool:
    """Wait *seconds*; True when a set *cancel* event cut the wait short.

    A ``threading.Event`` passed as *cancel* is waited on rather than slept
    past, so Stop during a retry wait stops at once.
    """
    if seconds <= 0:
        return bool(cancel is not None and cancel.is_set())
    if cancel is not None and sleep is None:
        return bool(cancel.wait(seconds))
    (time.sleep if sleep is None else sleep)(seconds)
    return bool(cancel is not None and cancel.is_set())
