"""The transient/permanent split and the backoff schedule (x.md item 10).

The classification matters more than the loop: these surfaces feed a pruning
decision, so a permanent failure retried three times merely wastes five
seconds, but a transient failure reported as permanent can talk a listener
into deleting a live subscription.
"""

from __future__ import annotations

import socket
import ssl
import urllib.error

import pytest

from quill.core.net_retry import DEFAULT_BACKOFF, is_transient, retry_transient


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example.com/feed.xml", code, "reason", {}, None)  # type: ignore[arg-type]


# -- classification ----------------------------------------------------------


@pytest.mark.parametrize("code", [500, 502, 503, 504, 599])
def test_server_errors_are_transient(code: int) -> None:
    assert is_transient(_http_error(code)) is True


@pytest.mark.parametrize("code", [408, 425, 429])
def test_the_three_retryable_4xx_codes_are_transient(code: int) -> None:
    assert is_transient(_http_error(code)) is True


@pytest.mark.parametrize("code", [400, 401, 403, 404, 410, 451])
def test_ordinary_client_errors_are_permanent(code: int) -> None:
    """404 is the case #386 names: retrying it cannot change the answer."""
    assert is_transient(_http_error(code)) is False


def test_a_name_that_does_not_resolve_is_permanent() -> None:
    """ "Bad address" -- the other permanent case #386 names. It arrives
    wrapped in a URLError, so the reason has to be unwrapped to see it."""
    error = urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))
    assert is_transient(error) is False
    assert is_transient(socket.gaierror(-2, "Name or service not known")) is False


def test_dropped_connections_and_timeouts_are_transient() -> None:
    assert is_transient(TimeoutError("timed out")) is True
    assert is_transient(ConnectionResetError("reset by peer")) is True
    assert is_transient(urllib.error.URLError(TimeoutError("timed out"))) is True


def test_a_bare_urlerror_is_transient() -> None:
    """No reason to unwrap: a connection-level failure with no detail is the
    ordinary shape of a flaky network, so it gets its retries."""
    assert is_transient(urllib.error.URLError("connection failed")) is True


def test_a_certificate_that_does_not_verify_is_permanent() -> None:
    """A trust failure will not fix itself in two seconds, and retrying it
    would paper over a real problem."""
    assert is_transient(ssl.SSLCertVerificationError("certificate verify failed")) is False


def test_other_ssl_errors_are_transient() -> None:
    assert is_transient(ssl.SSLError("handshake truncated")) is True


def test_an_unrecognized_failure_is_treated_as_permanent() -> None:
    """The safe default: a new failure mode surfaces at once rather than
    being silently retried three times."""
    assert is_transient(ValueError("something else entirely")) is False


# -- the loop ----------------------------------------------------------------


def test_a_call_that_succeeds_never_sleeps() -> None:
    waits: list[float] = []
    assert retry_transient(lambda: "ok", sleep=waits.append) == "ok"
    assert waits == []


def test_a_transient_failure_is_retried_on_the_documented_schedule() -> None:
    waits: list[float] = []
    attempts: list[int] = []

    def operation() -> str:
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise TimeoutError("timed out")
        return "ok"

    assert retry_transient(operation, sleep=waits.append) == "ok"
    assert len(attempts) == 3
    assert waits == [1.0, 2.0]
    assert tuple(waits) == DEFAULT_BACKOFF


def test_a_permanent_failure_raises_immediately_without_waiting() -> None:
    waits: list[float] = []
    attempts: list[int] = []

    def operation() -> str:
        attempts.append(len(attempts))
        raise _http_error(404)

    with pytest.raises(urllib.error.HTTPError) as caught:
        retry_transient(operation, sleep=waits.append)
    assert caught.value.code == 404
    assert len(attempts) == 1, "a 404 must cost exactly one round trip"
    assert waits == []


def test_the_original_exception_survives_the_last_retry() -> None:
    """The caller announces this error text, so it must stay the server's own
    words rather than becoming "retried 3 times"."""
    waits: list[float] = []

    def operation() -> str:
        raise _http_error(503)

    with pytest.raises(urllib.error.HTTPError) as caught:
        retry_transient(operation, sleep=waits.append)
    assert caught.value.code == 503
    assert waits == [1.0, 2.0], "every scheduled wait is used before giving up"


def test_the_schedule_length_decides_the_attempt_count() -> None:
    attempts: list[int] = []

    def operation() -> str:
        attempts.append(len(attempts))
        raise TimeoutError("timed out")

    with pytest.raises(TimeoutError):
        retry_transient(operation, backoff=(0.1,), sleep=lambda _s: None)
    assert len(attempts) == 2, "one wait means two attempts"

    attempts.clear()
    with pytest.raises(TimeoutError):
        retry_transient(operation, backoff=(), sleep=lambda _s: None)
    assert len(attempts) == 1, "an empty schedule means no retry at all"


def test_a_caller_can_supply_its_own_idea_of_transient() -> None:
    attempts: list[int] = []

    def operation() -> str:
        attempts.append(len(attempts))
        raise ValueError("normally permanent")

    with pytest.raises(ValueError):
        retry_transient(operation, sleep=lambda _s: None, transient=lambda _e: True)
    assert len(attempts) == 3
