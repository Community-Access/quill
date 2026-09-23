"""The four operator actions that did not exist: find a person, give their
allowance back, change their limits, and replace a token without signing them
out.
"""

from __future__ import annotations

from tests.conftest import (
    make_admin_client,
    make_user_and_device,
    seed_config_rows,
    seed_default_model,
    seed_feature_flags,
)


def _spend_some(app, user, device, count=3):
    from app.limits import check_request_allowed, record_usage

    with app.app_context():
        for _ in range(count):
            check_request_allowed(app, user, device, "summarize")
            record_usage(app, user, device, "summarize", "gpt-6-luna", 100, 20, 0.0004, "allowed")


# --- Finding somebody ------------------------------------------------------------


def test_a_person_can_be_found_by_the_support_id_they_were_shown(app, client, db):
    """Accounts are pseudonymous UUIDs. Without this, "somebody wrote to
    support and I cannot find them" has no answer at all."""
    user, _device = make_user_and_device(db.session, token="user-token")
    c, headers, _admin, _admin_device = make_admin_client(app, client)

    support_id = user.support_id
    response = c.get(f"/admin/users?q={support_id}", headers=headers)
    assert response.status_code == 200
    found = [row["user_id"] for row in response.json["users"]]
    assert user.id in found


def test_the_support_id_is_short_enough_to_read_aloud(app, db):
    user, _device = make_user_and_device(db.session, token="t")
    assert len(user.support_id) == 9  # AAAA-BBBB
    assert user.support_id[4] == "-"
    assert user.support_id.upper() == user.support_id


def test_searching_with_the_dashes_typed_still_finds_them(app, client, db):
    """A person reading a code aloud says the dash. An operator types what they
    hear."""
    user, _device = make_user_and_device(db.session, token="user-token")
    c, headers, _admin, _ad = make_admin_client(app, client)

    response = c.get(f"/admin/users?q={user.support_id}", headers=headers)
    assert user.id in [row["user_id"] for row in response.json["users"]]


# --- Giving an allowance back ------------------------------------------------------


def test_reset_clears_the_counters_and_the_cost_together(app, client, db):
    """Either half on its own produces a reset that appears to have silently
    failed: counters alone leaves the cost ceiling still refusing them, cost
    alone leaves them still out of requests."""
    from app.limits import _month_key, remaining_quota
    from app.models import MonthlyUsageSummary

    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    user, device = make_user_and_device(db.session, token="user-token")
    _spend_some(app, user, device, count=3)

    with app.app_context():
        assert remaining_quota(app, user).monthly_used == 3
    summary = db.session.get(MonthlyUsageSummary, {"user_id": user.id, "year_month": _month_key()})
    assert summary.request_count == 3
    assert float(summary.total_cost_usd) > 0

    c, headers, _admin, _ad = make_admin_client(app, client)
    response = c.post(
        f"/admin/users/{user.id}/usage/reset",
        json={"reason": "ran out during a demo"},
        headers=headers,
    )
    assert response.status_code == 200

    with app.app_context():
        assert remaining_quota(app, user).monthly_used == 0
    db.session.refresh(summary)
    assert summary.request_count == 0
    assert float(summary.total_cost_usd) == 0


def test_reset_does_not_touch_the_global_spend(app, client, db):
    """That money was really spent. A per-person courtesy must never quietly
    edit the number the budget cap protects everybody with."""
    from app.limits import _month_key, _redis

    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    user, device = make_user_and_device(db.session, token="user-token")
    _spend_some(app, user, device, count=2)

    with app.app_context():
        before = float(_redis(app).get(f"gwspend:{_month_key()}") or 0)
    assert before > 0

    c, headers, _admin, _ad = make_admin_client(app, client)
    c.post(f"/admin/users/{user.id}/usage/reset", json={"reason": "x"}, headers=headers)

    with app.app_context():
        after = float(_redis(app).get(f"gwspend:{_month_key()}") or 0)
    assert after == before


def test_reset_is_written_to_the_audit_log(app, client, db):
    from app.models import AdminAction

    seed_config_rows(db.session)
    user, _device = make_user_and_device(db.session, token="user-token")
    c, headers, _admin, _ad = make_admin_client(app, client)
    c.post(
        f"/admin/users/{user.id}/usage/reset",
        json={"reason": "goodwill after an outage"},
        headers=headers,
    )

    action = db.session.query(AdminAction).filter_by(action="reset_usage").one()
    assert action.target == user.id
    assert action.reason == "goodwill after an outage"


def test_after_a_reset_the_person_can_use_the_service_again(app, client, db, monkeypatch):
    """The point of the whole feature, asserted end to end."""
    from app.models import GatewayConfig
    from app.openai_client import Completion

    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    db.session.get(GatewayConfig, "monthly_request_cap").value = 2
    db.session.commit()

    user, device = make_user_and_device(db.session, token="user-token")
    user.monthly_request_cap = 2
    db.session.commit()
    monkeypatch.setattr(
        "app.routes.chat.complete",
        lambda *a, **k: Completion(text="ok", tokens_in=10, tokens_out=5),
    )
    headers = {"Authorization": "Bearer user-token"}

    for _ in range(2):
        assert (
            client.post(
                "/v1/chat", json={"feature": "summarize", "prompt": "t"}, headers=headers
            ).status_code
            == 200
        )
    blocked = client.post("/v1/chat", json={"feature": "summarize", "prompt": "t"}, headers=headers)
    assert blocked.status_code == 429

    c, admin_headers, _admin, _ad = make_admin_client(app, client)
    c.post(f"/admin/users/{user.id}/usage/reset", json={"reason": "x"}, headers=admin_headers)

    again = client.post("/v1/chat", json={"feature": "summarize", "prompt": "t"}, headers=headers)
    assert again.status_code == 200


# --- Changing one person's limits ---------------------------------------------------


def test_an_admin_can_give_one_person_a_different_allowance(app, client, db):
    seed_config_rows(db.session)
    user, _device = make_user_and_device(db.session, token="user-token")
    c, headers, _admin, _ad = make_admin_client(app, client)

    response = c.put(
        f"/admin/users/{user.id}/caps",
        json={"monthly_request_cap": 400, "monthly_cost_cap_usd": 0.5, "reason": "beta tester"},
        headers=headers,
    )
    assert response.status_code == 200
    db.session.refresh(user)
    assert user.monthly_request_cap == 400
    assert float(user.monthly_cost_cap_usd) == 0.5


def test_clearing_an_override_returns_them_to_the_global_default(app, client, db):
    """Null means "no override", which is what makes every change here
    reversible."""
    from datetime import UTC, datetime, timedelta

    from app.limits import _effective_user_cap

    seed_config_rows(db.session)
    user, _device = make_user_and_device(db.session, token="user-token")
    # Established, not brand new -- otherwise the new-account ramp is the
    # correct answer and this would be testing the wrong thing.
    user.created_at = datetime.now(UTC) - timedelta(days=30)
    user.monthly_request_cap = 400
    db.session.commit()

    c, headers, _admin, _ad = make_admin_client(app, client)
    c.put(f"/admin/users/{user.id}/caps", json={"monthly_request_cap": None}, headers=headers)

    db.session.refresh(user)
    assert user.monthly_request_cap is None
    with app.app_context():
        assert _effective_user_cap(app, user) == 100


def test_an_absurd_per_user_cap_is_refused(app, client, db):
    seed_config_rows(db.session)
    user, _device = make_user_and_device(db.session, token="user-token")
    c, headers, _admin, _ad = make_admin_client(app, client)

    response = c.put(
        f"/admin/users/{user.id}/caps", json={"monthly_request_cap": 999_999}, headers=headers
    )
    assert response.status_code == 400
    db.session.refresh(user)
    assert user.monthly_request_cap is None


# --- Tokens --------------------------------------------------------------------------


def test_an_admin_can_rotate_a_token_without_signing_the_person_out(app, client, db):
    """The answer to "this may have leaked but I am not certain". Revoking is
    the answer when you are certain, and it costs the person a
    re-registration."""
    user, device = make_user_and_device(db.session, token="maybe-leaked")
    c, headers, _admin, _ad = make_admin_client(app, client)

    response = c.post(f"/admin/devices/{device.id}/rotate", json={"reason": "?"}, headers=headers)
    assert response.status_code == 200
    new_token = response.json["token"]
    assert new_token != "maybe-leaked"

    assert (
        client.get("/v1/quota", headers={"Authorization": "Bearer maybe-leaked"}).status_code == 401
    )
    assert (
        client.get("/v1/quota", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200
    )
    db.session.refresh(device)
    assert device.status == "active"


def test_a_client_can_rotate_its_own_token(app, client, db):
    """What the desktop client calls on a token older than 180 days. It is
    authenticated by the *current* token, so rotation is proof of possession --
    somebody who already lost the token cannot use this to lock the owner
    out."""
    _user, _device = make_user_and_device(db.session, token="old-token")
    response = client.post("/v1/device/rotate", headers={"Authorization": "Bearer old-token"})
    assert response.status_code == 200
    assert response.json["token"] != "old-token"
