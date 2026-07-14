"""Tests for the accessible admin web dashboard (app/routes/dashboard.py):
the session-based login bridge, and that each page/action reaches the same
underlying effect as its JSON admin-API counterpart."""

from __future__ import annotations

from app.auth import hash_token

from tests.conftest import make_user_and_device, seed_default_model


def _admin_session_client(app, client):
    """A test client that has already logged into the dashboard as an
    admin device (mirrors test_admin.py's _admin_client, but drives the
    session-cookie login form instead of a bearer header)."""
    from app.models import Device, User, db

    user = User()
    db.session.add(user)
    db.session.flush()
    device = Device(user_id=user.id, token_hash=hash_token("admin-token"), label="admin device")
    db.session.add(device)
    db.session.commit()
    app.config["ADMIN_ALLOWLIST"] = frozenset({device.id})

    response = client.post("/dashboard/login", data={"token": "admin-token", "next": ""})
    assert response.status_code == 302
    return client, user, device


def test_dashboard_redirects_to_login_when_not_authenticated(client):
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert "/dashboard/login" in response.headers["Location"]


def test_login_rejects_an_unknown_token(client):
    response = client.post("/dashboard/login", data={"token": "not-a-real-token", "next": ""})
    assert response.status_code == 401


def test_login_rejects_a_non_admin_devices_token(app, client, db):
    make_user_and_device(db.session, token="regular-token")
    response = client.post("/dashboard/login", data={"token": "regular-token", "next": ""})
    assert response.status_code == 401


def test_login_succeeds_for_an_allowlisted_admin_device(app, client, db):
    client, _user, _device = _admin_session_client(app, client)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Overview" in response.data


def test_logout_ends_the_session(app, client, db):
    client, _user, _device = _admin_session_client(app, client)
    client.post("/dashboard/logout")
    response = client.get("/dashboard/")
    assert response.status_code == 302


def test_overview_renders_budget_and_trend(app, client, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="global_monthly_budget_usd", value=25, description="test"))
    db.session.commit()
    client, _user, _device = _admin_session_client(app, client)

    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"budget" in response.data.lower()


def test_dashboard_can_toggle_a_model(app, client, db):
    seed_default_model(db.session)
    client, _user, _device = _admin_session_client(app, client)

    response = client.post("/dashboard/models/gpt-5-nano/toggle", data={"enabled": "0"})
    assert response.status_code == 302

    from app.models import GatewayModel

    assert db.session.get(GatewayModel, "gpt-5-nano").enabled is False


def test_dashboard_can_edit_a_config_value(app, client, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="monthly_request_cap", value=100, description="test"))
    db.session.commit()
    client, _user, _device = _admin_session_client(app, client)

    response = client.post("/dashboard/config/monthly_request_cap", data={"value": "250"})
    assert response.status_code == 302
    assert db.session.get(GatewayConfig, "monthly_request_cap").value == 250


def test_dashboard_user_status_and_delete_flow(app, client, db):
    from app.models import Device, User

    target_user, target_device = make_user_and_device(db.session, token="target-token")
    target_user_id = target_user.id
    target_device_id = target_device.id
    client, _admin_user, _admin_device = _admin_session_client(app, client)

    response = client.post(f"/dashboard/users/{target_user_id}/status", data={"status": "blocked"})
    assert response.status_code == 302
    assert db.session.get(User, target_user_id).status == "blocked"

    # Deleting without the confirmation checkbox is a no-op.
    client.post(f"/dashboard/users/{target_user_id}/delete", data={})
    assert db.session.get(User, target_user_id) is not None

    response = client.post(f"/dashboard/users/{target_user_id}/delete", data={"confirm": "yes"})
    assert response.status_code == 302
    assert db.session.get(User, target_user_id) is None
    assert db.session.get(Device, target_device_id) is None


def test_dashboard_can_toggle_a_feature_flag(app, client, db):
    client, _user, _device = _admin_session_client(app, client)

    response = client.post(
        "/dashboard/feature-flags/alt_text", data={"enabled": "0", "reason": "testing"}
    )
    assert response.status_code == 302

    from app.models import FeatureFlag

    flag = db.session.get(FeatureFlag, "alt_text")
    assert flag.enabled is False
    assert flag.disabled_reason == "testing"


def test_audit_log_records_dashboard_actions(app, client, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="monthly_request_cap", value=100, description="test"))
    db.session.commit()
    client, _user, _device = _admin_session_client(app, client)
    client.post("/dashboard/config/monthly_request_cap", data={"value": "200"})

    response = client.get("/dashboard/audit-log")
    assert response.status_code == 200
    assert b"set_config" in response.data
