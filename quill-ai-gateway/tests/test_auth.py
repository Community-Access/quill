"""Tests for app/auth.py: the device-code flow and bearer-token auth."""

from __future__ import annotations

from app.auth import (
    _load_grant,
    _save_grant,
    confirm_device_code,
    hash_token,
    poll_device_token,
    rotate_device_token,
    start_device_flow,
)


def allow_immediate_poll(app, device_code: str) -> None:
    """Clear the poll-interval stamp so a test can poll again at once.

    The old version of this reached into a module-level dict. Grants live in
    Redis now (so two Gunicorn workers can complete each other's sign-ins), so
    the equivalent is a load-edit-save -- still reaching into internals, and
    still preferable to making the test sleep for the real interval.
    """
    grant = _load_grant(app, device_code)
    grant["last_poll_at"] = None
    _save_grant(app, grant, 600)


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
        status, body = poll_device_token(app, result["device_code"])
    assert status == 428
    assert body == {"status": "pending"}


def test_confirm_then_poll_returns_a_real_token(app, db):
    with app.app_context():
        result = start_device_flow(app)
        ok = confirm_device_code(app, result["user_code"])
        assert ok is True
        allow_immediate_poll(app, result["device_code"])
        status, body = poll_device_token(app, result["device_code"])
    assert status == 200
    assert body["status"] == "authorized"
    assert body["token"]
    assert body["device_id"]


def test_confirm_unknown_code_fails(app, db):
    with app.app_context():
        ok = confirm_device_code(app, "ZZZZ-9999")
    assert ok is False


def test_device_code_is_single_use(app, db):
    with app.app_context():
        result = start_device_flow(app)
        confirm_device_code(app, result["user_code"])
        allow_immediate_poll(app, result["device_code"])
        status1, _ = poll_device_token(app, result["device_code"])
        status2, body2 = poll_device_token(app, result["device_code"])
    assert status1 == 200
    assert status2 == 410
    assert body2["status"] == "expired"


def test_a_grant_survives_leaving_this_process(app, db):
    """The reason grants moved to Redis.

    Gunicorn runs two workers, so the worker that minted a code is only ever a
    coin flip away from being a different worker than the one that confirms it
    or answers the client's poll. Nothing in this flow may depend on
    process-local state; this test asserts that by reading the grant back out
    of the shared store rather than out of any Python object the minting call
    returned.
    """
    with app.app_context():
        result = start_device_flow(app)
        stored = _load_grant(app, result["device_code"])
        assert stored is not None
        assert stored["user_code"] == result["user_code"]
        assert stored["status"] == "pending"


def test_polling_faster_than_the_interval_says_slow_down(app, db):
    with app.app_context():
        result = start_device_flow(app)
        first = poll_device_token(app, result["device_code"])
        second = poll_device_token(app, result["device_code"])
    assert first[0] == 428
    assert second[0] == 429
    assert second[1] == {"status": "slow_down"}


def test_hash_token_is_stable_and_not_reversible_shaped(app):
    a = hash_token("my-secret-token")
    b = hash_token("my-secret-token")
    c = hash_token("a-different-token")
    assert a == b
    assert a != c
    assert len(a) == 64  # sha256 hex digest length
    assert "my-secret-token" not in a


def test_rotating_a_token_invalidates_the_old_one(app, db, client):
    from tests.conftest import make_user_and_device

    with app.app_context():
        _user, device = make_user_and_device(db.session, token="original-token")
        new_token = rotate_device_token(device)

    assert new_token != "original-token"

    # The old token no longer authenticates anything...
    old = client.get("/v1/quota", headers={"Authorization": "Bearer original-token"})
    assert old.status_code == 401
    # ...and the new one does, without the user having to re-register.
    fresh = client.get("/v1/quota", headers={"Authorization": f"Bearer {new_token}"})
    assert fresh.status_code == 200


def test_require_auth_rejects_missing_bearer_header(app, client):
    response = client.post("/v1/chat", json={"feature": "summarize", "prompt": "hi"})
    assert response.status_code == 401


def test_require_auth_rejects_unknown_token(app, client):
    response = client.post(
        "/v1/chat",
        json={"feature": "summarize", "prompt": "hi"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
