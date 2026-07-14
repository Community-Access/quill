"""Tests for app/auth.py: the device-code flow and bearer-token auth."""

from __future__ import annotations

from app.auth import (
    _pending_grants,
    confirm_device_code,
    hash_token,
    poll_device_token,
    start_device_flow,
)


def test_start_device_flow_returns_rfc8628_shape(app):
    with app.app_context():
        result = start_device_flow(app)
    assert set(result) == {
        "device_code",
        "user_code",
        "verification_uri",
        "verification_uri_complete",
        "interval",
        "expires_in",
    }
    assert "-" in result["user_code"]  # ABCD-1234 shape
    assert result["user_code"] in result["verification_uri_complete"]


def test_user_code_alphabet_excludes_ambiguous_characters(app):
    with app.app_context():
        for _ in range(20):
            result = start_device_flow(app)
            code = result["user_code"].replace("-", "")
            assert not any(c in code for c in "ILOU0158")


def test_poll_before_confirmation_is_pending(app, db):
    with app.app_context():
        result = start_device_flow(app)
        status, body = poll_device_token(result["device_code"])
    assert status == 428
    assert body == {"status": "pending"}


def test_confirm_then_poll_returns_a_real_token(app, db):
    with app.app_context():
        result = start_device_flow(app)
        ok = confirm_device_code(result["user_code"])
        assert ok is True
        # bypass the poll interval for this test
        _pending_grants[result["device_code"]].last_poll_at = None
        status, body = poll_device_token(result["device_code"])
    assert status == 200
    assert body["status"] == "authorized"
    assert body["token"]
    assert body["device_id"]


def test_confirm_unknown_code_fails(app, db):
    with app.app_context():
        ok = confirm_device_code("ZZZZ-9999")
    assert ok is False


def test_device_code_is_single_use(app, db):
    with app.app_context():
        result = start_device_flow(app)
        confirm_device_code(result["user_code"])
        _pending_grants[result["device_code"]].last_poll_at = None
        status1, _ = poll_device_token(result["device_code"])
        status2, body2 = poll_device_token(result["device_code"])
    assert status1 == 200
    assert status2 == 410
    assert body2["status"] == "expired"


def test_hash_token_is_stable_and_not_reversible_shaped(app):
    a = hash_token("my-secret-token")
    b = hash_token("my-secret-token")
    c = hash_token("a-different-token")
    assert a == b
    assert a != c
    assert len(a) == 64  # sha256 hex digest length
    assert "my-secret-token" not in a


def test_require_auth_rejects_missing_bearer_header(app, client):
    response = client.post("/v1/chat", json={"feature": "chat", "prompt": "hi"})
    assert response.status_code == 401


def test_require_auth_rejects_unknown_token(app, client):
    response = client.post(
        "/v1/chat",
        json={"feature": "chat", "prompt": "hi"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
