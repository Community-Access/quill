"""Retry a *transient* network failure; give up on a permanent one at once.

Earshot's #386, translated. A podcast feed that answers 503 because its host
is briefly overloaded, a connection dropped mid-read, a request that timed out
-- all three usually succeed on the second or third try a couple of seconds
later. A 404 and an unresolvable hostname never do, and retrying them only
makes the failure take five seconds longer to report.

So the distinction this module draws is not "did it fail" but **"is failing
again the likely outcome"**, and it is the whole value here: a blanket retry
would be worse than none, because the surfaces that use it feed a *pruning*
decision. ``opml_import.probe_feed`` decides which subscriptions a listener is
offered the chance to delete; a false "dead feed" verdict from one flaky
moment is the most expensive wrong answer in the podcast stack.

Three call sites, one policy: feed refresh (``feed_reader``), directory search
(``itunes_search``), and the OPML reachability sweep (``opml_import``).
Downloads deliberately do **not** use it -- they already have their own
resumable reconnect with a Range header (``download_queue``), which is a
different and better answer for a partially-transferred file.

``sleep`` is injected so the tests prove the backoff schedule without waiting
three seconds to do it.

wx-free, strict-typed.
"""

from __future__ import annotations

import socket
import ssl
import time
import urllib.error
from collections.abc import Callable, Sequence

#: The waits between attempts, in seconds: two retries, 1s then 2s (#386).
#: A tuple of waits rather than a count-plus-multiplier so the schedule is
#: something a test can state literally and a reader can see at a glance.
DEFAULT_BACKOFF: tuple[float, ...] = (1.0, 2.0)

#: 4xx codes that mean "ask again shortly" rather than "this is wrong".
#: 408 Request Timeout and 429 Too Many Requests say so outright; 425 Too
#: Early is the same shape. Every other 4xx is the server telling us the
#: request itself is the problem, which a retry cannot fix.
_RETRYABLE_STATUS: frozenset[int] = frozenset({408, 425, 429})


def is_transient(error: BaseException) -> bool:
    """Whether *error* is worth trying again in a second or two.

    Deliberately a short allowlist rather than "anything that is not a 404".
    An unrecognized failure is treated as permanent, so a new failure mode
    surfaces immediately instead of being silently retried three times --
    the wrong default here costs a listener's subscription list.
    """
    # HTTPError subclasses URLError, which subclasses OSError, so it has to
    # be tested first or every HTTP status would fall through to the
    # connection-level branches below.
    if isinstance(error, urllib.error.HTTPError):
        status = int(getattr(error, "code", 0) or 0)
        return status >= 500 or status in _RETRYABLE_STATUS

    # A name that does not resolve is "bad address": the permanent case #386
    # names explicitly. It is reached through URLError.reason, so unwrap.
    if isinstance(error, urllib.error.URLError):
        reason = getattr(error, "reason", None)
        if isinstance(reason, socket.gaierror):
            return False
        if isinstance(reason, BaseException):
            return is_transient(reason)
        return True

    if isinstance(error, socket.gaierror):
        return False

    # A certificate that does not verify will not verify two seconds later,
    # and retrying a TLS failure reads as flakiness papering over a real
    # trust problem. Other SSL errors (a truncated handshake, a reset during
    # negotiation) are ordinary connection noise.
    if isinstance(error, ssl.SSLCertVerificationError):
        return False
    if isinstance(error, ssl.SSLError):
        return True

    if isinstance(error, (TimeoutError, socket.timeout, ConnectionError)):
        return True

    return False


def retry_transient[T](
    operation: Callable[[], T],
    *,
    backoff: Sequence[float] = DEFAULT_BACKOFF,
    sleep: Callable[[float], None] | None = None,
    transient: Callable[[BaseException], bool] = is_transient,
) -> T:
    """Call *operation*, retrying it while it fails transiently.

    ``backoff`` is the wait before each **retry**, so the default of
    ``(1.0, 2.0)`` means up to three attempts in total: the first, then one a
    second later, then one two seconds after that.

    A permanent failure is re-raised from the first attempt without waiting,
    and the last transient failure is re-raised once the schedule runs out --
    either way the caller sees the original exception, with its original
    traceback and message, so error text never becomes "retried 3 times" when
    what the listener needs to read is "404 Not Found".

    ``transient`` is a parameter so a call site with its own idea of what is
    worth retrying can say so without a second retry loop existing.

    ``sleep`` defaults to :func:`time.sleep`, but is resolved **when the
    function runs** rather than captured as a default argument at import.
    A captured default cannot be monkeypatched, which would quietly make
    every wiring test that thinks it has disabled the waiting actually sit
    through the whole schedule -- passing, but three seconds slower each,
    and proving less than it appears to.
    """
    wait = time.sleep if sleep is None else sleep
    attempts = len(backoff) + 1
    for index in range(attempts):
        try:
            return operation()
        except Exception as error:  # noqa: BLE001 - re-raised below; see docstring
            if index >= len(backoff) or not transient(error):
                raise
            wait(backoff[index])
    # Unreachable: the loop either returns or raises on its final pass. Kept
    # so the function has no implicit ``None`` return for the type checker.
    raise AssertionError("retry_transient exhausted its schedule without returning")


__all__ = ["DEFAULT_BACKOFF", "is_transient", "retry_transient"]
