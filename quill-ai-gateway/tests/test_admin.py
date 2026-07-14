"""Tests for app/routes/admin.py: the admin-console API surface covering
model on/off, config edits, and user disable/remove."""

from __future__ import annotations

from app.auth import hash_token

from tests.conftest import make_user_and_device, seed_default_model


def _admin_client(app, client):
    """An authenticated request as a device on the admin allowlist."""
    from app.models import Device, User, db

    user = User()
    db.session.add(user)
    db.session.flush()
    device = Device(user_id=user.id, token_hash=hash_token("admin-token"), label="admin device")
    db.session.add(device)
    db.session.commit()
    app.config["ADMIN_ALLOWLIST"] = frozenset({device.id})
    return client, {"Authorization": "Bearer admin-token"}, user, device


def test_non_admin_device_is_forbidden(app, client, db):
    user, device = make_user_and_device(db.session, token="regular-token")
    response = client.get("/admin/config", headers={"Authorization": "Bearer regular-token"})
    assert response.status_code == 403


def test_admin_can_list_and_toggle_models(app, client, db):
    seed_default_model(db.session)
    c, headers, _user, _device = _admin_client(app, client)

    response = c.get("/admin/models", headers=headers)
    assert response.status_code == 200
    assert response.json[0]["model_id"] == "gpt-5-nano"
    assert response.json[0]["enabled"] is True

    response = c.put("/admin/models/gpt-5-nano/enabled", json={"enabled": False}, headers=headers)
    assert response.status_code == 200
    response = c.get("/admin/models", headers=headers)
    assert response.json[0]["enabled"] is False


def test_admin_can_edit_a_config_value(app, client, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="monthly_request_cap", value=100, description="test"))
    db.session.commit()
    c, headers, _user, _device = _admin_client(app, client)

    response = c.put("/admin/config/monthly_request_cap", json={"value": 250}, headers=headers)
    assert response.status_code == 200

    from app.limits import resolve_limit

    assert resolve_limit(app, "monthly_request_cap") == 250


def test_admin_can_disable_a_user(app, client, db):
    c, headers, _admin_user, _admin_device = _admin_client(app, client)
    target_user, _target_device = make_user_and_device(db.session, token="target-token")

    response = c.put(
        f"/admin/users/{target_user.id}/status",
        json={"status": "blocked", "reason": "test"},
        headers=headers,
    )
    assert response.status_code == 200
    db.session.refresh(target_user)
    assert target_user.status == "blocked"


def test_admin_can_permanently_delete_a_user(app, client, db):
    from app.models import Device, User

    c, headers, _admin_user, _admin_device = _admin_client(app, client)
    target_user, target_device = make_user_and_device(db.session, token="target-token-2")
    target_user_id = target_user.id
    target_device_id = target_device.id

    response = c.delete(f"/admin/users/{target_user_id}", headers=headers)
    assert response.status_code == 204
    assert db.session.get(User, target_user_id) is None
    assert db.session.get(Device, target_device_id) is None


def test_delete_unknown_user_is_404(app, client, db):
    c, headers, _admin_user, _admin_device = _admin_client(app, client)
    response = c.delete("/admin/users/does-not-exist", headers=headers)
    assert response.status_code == 404
