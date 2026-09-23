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
    quota = GatewayQuota(monthly_cap=100, monthly_used=94, daily_cap=20, daily_used=3)
    assert quota.monthly_left == 6
    assert quota.daily_left == 17


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
