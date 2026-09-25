"""The client, and the sentences it turns failures into.

Most of this file is about error mapping, which is not an implementation detail
here. A screen-reader user hears only the sentence we wrote: "HTTP 429" tells
them nothing they can act on, and "your allowance is used up, it starts again on
the 1st" tells them everything. So the tests assert on the *class* and on the
words, because both are the product.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from quill.core.ai.gateway_client import (
    GatewayClient,
    GatewayLimits,
    GatewayQuota,
    device_flow_poster,
)
from quill.core.ai.gateway_errors import (
    GatewayAuthError,
    GatewayPausedError,
    GatewayQuotaError,
    GatewayServiceError,
    GatewayTooLargeError,
)


def _http_error(code: int, payload: dict) -> urllib.error.HTTPError:
    body = io.BytesIO(json.dumps(payload).encode())
    return urllib.error.HTTPError("https://x/", code, "", {}, body)


def _raising(error):
    def opener(*_args, **_kwargs):
        raise error

    return opener


# --- Turning failures into sentences ------------------------------------------


def test_a_revoked_token_says_how_to_fix_it():
    from quill.core.ai.gateway_client import _error_for_status

    error = _error_for_status(_http_error(401, {"message": "Invalid or revoked token."}))
    assert isinstance(error, GatewayAuthError)
    assert "Sign In" in error.user_hint


def test_an_exhausted_allowance_keeps_the_servers_own_words():
    """The server knows which limit was hit and when it lifts. Replacing its
    sentence with a generic one throws away the only useful part."""
    from quill.core.ai.gateway_client import _error_for_status

    error = _error_for_status(
        _http_error(
            429,
            {
                "message": "You've used today's free limit. It resets at midnight.",
                "scope": "daily",
                "reset_at": "2026-10-01T00:00:00+00:00",
            },
        )
    )
    assert isinstance(error, GatewayQuotaError)
    assert "resets at midnight" in str(error)
    assert error.scope == "daily"
    assert error.reset_at.startswith("2026-10-01")


def test_a_signup_throttle_is_not_reported_as_a_quota():
    """Both are 429 and they are completely different facts: one is about this
    network, the other about this person's allowance. Telling a first-time user
    they have used up an allowance they have never had is a support ticket."""
    from quill.core.ai.gateway_client import _error_for_status

    error = _error_for_status(
        _http_error(429, {"status": "throttled", "message": "Too many computers..."})
    )
    assert isinstance(error, GatewayPausedError)
    assert not isinstance(error, GatewayQuotaError)


def test_an_oversized_request_says_nothing_was_used():
    from quill.core.ai.gateway_client import _error_for_status

    error = _error_for_status(_http_error(422, {"message": "That selection is too large."}))
    assert isinstance(error, GatewayTooLargeError)
    assert "Nothing was sent and nothing was used." in error.user_hint


def test_a_paused_service_points_at_what_still_works():
    from quill.core.ai.gateway_client import _error_for_status

    error = _error_for_status(_http_error(503, {"message": "Hosted AI is paused."}))
    assert isinstance(error, GatewayPausedError)
    assert "own API key" in error.user_hint


def test_an_unreadable_error_body_still_produces_a_sentence():
    """A proxy returning HTML, a truncated response. The user still gets
    something to act on rather than a traceback."""
    from quill.core.ai.gateway_client import _error_for_status

    body = io.BytesIO(b"<html>502 Bad Gateway</html>")
    error = _error_for_status(urllib.error.HTTPError("https://x/", 502, "", {}, body))
    assert isinstance(error, GatewayServiceError)
    assert str(error).endswith(".")


@pytest.mark.parametrize(
    "error_class",
    [GatewayAuthError, GatewayQuotaError, GatewayTooLargeError, GatewayPausedError],
)
def test_every_failure_says_what_to_do_next(error_class):
    """A message that only names the problem is a dead end, and a dead end is
    where somebody stops using the feature."""
    hint = error_class("x").user_hint
    assert hint
    assert hint.endswith(".")
    assert len(hint.split()) >= 4


# --- Reading what the service allows -------------------------------------------


def test_limits_come_from_the_server_not_from_a_constant():
    client = GatewayClient(
        "https://x",
        opener=lambda *_a, **_k: {
            "max_input_tokens": 4000,
            "max_output_tokens": 900,
            "max_chunks_per_request": 5,
            "hosted_ai_enabled": True,
            "feature_flags": {"summarize": True, "alt_text": False},
        },
    )
    limits = client.fetch_limits()
    assert limits.max_input_tokens == 4000
    assert limits.max_chunks_per_request == 5


def test_an_unknown_feature_is_treated_as_off():
    """An id this build predates, or one that was removed. Offering a button for
    something that answers with an error is worse than not offering it."""
    limits = GatewayLimits(feature_flags={"summarize": True})
    assert limits.feature_available("summarize") is True
    assert limits.feature_available("alt_text") is False
    assert limits.feature_available("something_new") is False


def test_the_global_switch_turns_everything_off():
    limits = GatewayLimits(hosted_ai_enabled=False, feature_flags={"summarize": True})
    assert limits.feature_available("summarize") is False


def test_quota_reports_what_is_left_not_what_was_used():
    quota = GatewayQuota(monthly_cap=100, monthly_used=80, daily_cap=20, daily_used=3)
    assert quota.monthly_left == 20
    assert quota.daily_left == 17


def test_today_never_reports_more_than_the_month_has_left():
    """A new connection's monthly cap sat under the daily one, and the Usage
    window said 15 left this month and 20 left today (2026-09-25)."""
    quota = GatewayQuota(monthly_cap=15, monthly_used=0, daily_cap=20, daily_used=0)
    assert quota.daily_left == 15


def test_a_quota_already_over_its_cap_never_reports_a_negative():
    quota = GatewayQuota(monthly_cap=100, monthly_used=105)
    assert quota.monthly_left == 0


# --- Asking -------------------------------------------------------------------


def test_asking_sends_the_feature_and_the_prompt_and_nothing_else():
    sent = {}

    def opener(url, *, token="", body=None, method=""):
        sent.update({"url": url, "token": token, "body": body})
        return {"text": "an answer", "remaining_quota": {"monthly": 93, "daily": 17}}

    client = GatewayClient("https://x", "tok", opener=opener)
    text, quota = client.ask("summarize", "some text")

    assert text == "an answer"
    assert quota.monthly_cap == 93
    assert sent["token"] == "tok"
    assert sent["body"] == {"feature": "summarize", "prompt": "some text"}


def test_excerpts_are_sent_only_when_there_are_some():
    sent = {}

    def opener(url, *, token="", body=None, method=""):
        sent.update(body or {})
        return {"text": "an answer"}

    GatewayClient("https://x", "t", opener=opener).ask("document_qna", "q?", ["a", "b"])
    assert sent["chunks"] == ["a", "b"]


def test_an_empty_answer_is_an_error_not_an_answer():
    """The user experiences a blank reply as a broken feature. The server
    refunds it; the client has to refuse to present it as a result."""
    client = GatewayClient("https://x", "t", opener=lambda *_a, **_k: {"text": "   "})
    with pytest.raises(GatewayServiceError):
        client.ask("summarize", "text")


def test_signing_out_never_fails_the_caller():
    """The local token is deleted whatever happens here. Somebody who asks to
    sign out ends up signed out even on a train with no signal."""
    client = GatewayClient("https://x", "t", opener=_raising(GatewayServiceError("down")))
    client.revoke("device-1")  # must not raise


# --- The device-flow adapter ----------------------------------------------------


def test_the_adapter_speaks_oauth_to_the_existing_state_machine():
    """The gateway says ``status``; QUILL's already-tested RFC 8628 machine
    reads ``error``. Translating is what lets the machine be reused rather than
    rewritten -- including the polling and back-off that were already made to
    behave for a screen-reader user once."""
    import quill.core.ai.gateway_client as mod

    replies = iter([
        {"status": "pending"},
        {"status": "slow_down"},
        {"status": "authorized", "token": "tok", "device_id": "dev"},
    ])
    mod._urlopen_json = lambda *_a, **_k: next(replies)  # noqa: SLF001

    poster = device_flow_poster("https://x")
    assert poster("https://x/device/token", {"device_code": "d"}) == {
        "error": "authorization_pending"
    }
    assert poster("https://x/device/token", {"device_code": "d"}) == {"error": "slow_down"}
    assert poster("https://x/device/token", {"device_code": "d"}) == {
        "access_token": "tok",
        "device_id": "dev",
    }


def test_a_too_fast_poll_is_a_slow_down_not_a_quota_failure():
    """The poll endpoint uses 429 for "you are polling too fast". Reading that
    as an exhausted allowance would abandon a sign-in that was going fine."""
    import quill.core.ai.gateway_client as mod

    mod._urlopen_json = _raising(GatewayQuotaError("slow down"))  # noqa: SLF001
    poster = device_flow_poster("https://x")
    assert poster("https://x/device/token", {"device_code": "d"}) == {"error": "slow_down"}


def test_the_gateways_pending_and_expired_statuses_are_answers(monkeypatch):
    """The gateway says "pending" with HTTP 428 and "expired" or "denied" with
    410. Read as failures, the first poll ended every sign-in with
    "server_error" before anybody could type the code (2026-09-25). Patched at
    urlopen rather than at _urlopen_json, because that is where it broke."""
    import importlib

    mod = importlib.reload(importlib.import_module("quill.core.ai.gateway_client"))
    replies = iter([
        _http_error(428, {"status": "pending"}),
        _http_error(410, {"status": "denied"}),
        _http_error(410, {"status": "expired"}),
    ])

    def fake_urlopen(*_a, **_k):
        raise next(replies)

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    poster = mod.device_flow_poster("https://x")
    form = {"device_code": "d"}
    assert poster("https://x/device/token", form) == {"error": "authorization_pending"}
    assert poster("https://x/device/token", form) == {"error": "access_denied"}
    assert poster("https://x/device/token", form) == {"error": "expired_token"}


# --- When the connection itself fails (2026-09-25) -------------------------------
#
# Reported from a Windows 10 22H2 machine whose internet was fine: every sign-in
# ended at "QUILL could not reach the internet". The connection had been made;
# the certificate could not be verified, because the TLS context trusted only
# Windows' root store and Windows had never downloaded the root this service
# chains to. Every URLError was being reported as "no internet".


def _names_host(message):
    """Whether *message* names the service's host, as a whole word."""
    import re

    return re.search(r"(?<![\w.])ai\.example\.org(?![\w.])", message) is not None


def _raise_on_open(monkeypatch, reason):
    from quill.core.ai import gateway_client as mod

    def fake_urlopen(*_a, **_k):
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    return mod


def test_a_certificate_failure_is_not_reported_as_no_internet(monkeypatch):
    import ssl

    from quill.core.ai.gateway_errors import GatewayCertificateError, GatewayOfflineError

    mod = _raise_on_open(
        monkeypatch, ssl.SSLCertVerificationError(1, "unable to get local issuer certificate")
    )
    with pytest.raises(GatewayCertificateError) as caught:
        mod._urlopen_json("https://ai.example.org/v1/device/code", body={})
    message = str(caught.value)
    assert "internet" not in message
    # Matched as a word, not with ``in``: CodeQL reads a hostname tested by
    # substring as URL sanitisation (py/incomplete-url-substring-sanitization).
    assert _names_host(message) and "certificate" in message
    assert "unable to get local issuer certificate" in message  # the reason, for support
    assert "Nothing was sent" in message
    # Still an offline error to every caller: nothing was sent.
    assert isinstance(caught.value, GatewayOfflineError)


@pytest.mark.parametrize(
    ("reason", "expected", "phrase"),
    [
        ("dns", "GatewayOfflineError", "could not look up the address"),
        (ConnectionRefusedError(10061, "refused"), "GatewayUnreachableError", "refused"),
        (TimeoutError("timed out"), "GatewayUnreachableError", "did not answer in time"),
    ],
)
def test_each_connection_failure_says_which_it_was(monkeypatch, reason, expected, phrase):
    import socket

    if reason == "dns":
        reason = socket.gaierror(11001, "getaddrinfo failed")
    mod = _raise_on_open(monkeypatch, reason)
    with pytest.raises(Exception) as caught:
        mod._urlopen_json("https://ai.example.org/v1/limits")
    assert type(caught.value).__name__ == expected
    assert phrase in str(caught.value)
    assert _names_host(str(caught.value))


def test_the_tls_context_trusts_certifi_as_well_as_the_system_store(monkeypatch):
    """The fix itself: a system store missing the root must not fail the chain."""
    import ssl

    import certifi

    from quill.core.ai import gateway_client as mod

    loaded: list[str] = []

    class Recording(ssl.SSLContext):
        def load_verify_locations(self, cafile=None, *args, **kwargs):  # noqa: ANN001
            loaded.append(str(cafile))
            return super().load_verify_locations(cafile, *args, **kwargs)

    monkeypatch.setattr(
        mod.ssl, "create_default_context", lambda *a, **k: Recording(ssl.PROTOCOL_TLS_CLIENT)
    )
    context = mod._verified_context()
    assert loaded == [certifi.where()]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("error_name", ["GatewayCertificateError", "GatewayUnreachableError"])
def test_the_new_connection_errors_say_what_to_do_next(error_name):
    from quill.core.ai import gateway_errors

    hint = getattr(gateway_errors, error_name)("x").user_hint
    assert hint.endswith(".") and len(hint.split()) >= 4
