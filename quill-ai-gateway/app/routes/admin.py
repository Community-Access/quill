"""Admin console API (PRD §10, §24): everything an operator needs to run
the Gateway day to day without touching code or redeploying.

Every route here requires **both** decorators, in this exact order
(``require_auth`` above ``require_admin`` — see ``app/auth.py``'s
docstring for why the order matters), and every state-changing action
writes an :class:`~app.models.AdminAction` row so "who did what and when"
is always answerable later (PRD §10's last bullet).

Covers, per the admin capabilities requested for this service: turning a
model on or off, choosing which model is the active default, editing any
tunable limit live, viewing a user's usage, disabling a user's hosted-AI
access (a soft, reversible block), and permanently removing a user
(a hard delete, for a user who asks to be forgotten or for cleaning up
clearly-abusive accounts) as a distinct action from disabling.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from app.auth import require_admin, require_auth
from app.model_registry import list_models, set_default_model, set_model_enabled
from app.models import (
    AdminAction,
    Device,
    FeatureFlag,
    GatewayConfig,
    MonthlyUsageSummary,
    User,
    db,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


# --- Models: enable/disable, choose the active one --------------------------


@bp.get("/models")
@require_auth
@require_admin
def get_models():
    """Every configured model (enabled and disabled), for the admin
    console's model picker."""
    models = list_models(include_disabled=True)
    return jsonify([
        {
            "model_id": m.model_id,
            "label": m.label,
            "enabled": m.enabled,
            "is_default": m.is_default,
            "input_cost_per_million_usd": float(m.input_cost_per_million_usd),
            "output_cost_per_million_usd": float(m.output_cost_per_million_usd),
        }
        for m in models
    ])


@bp.put("/models/<model_id>/enabled")
@require_auth
@require_admin
def put_model_enabled(model_id: str):
    """Turn one model on or off. Body: ``{"enabled": true|false}``."""
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled", True))
    try:
        set_model_enabled(model_id, enabled, admin_id=g.device.id)
    except ValueError as exc:
        return jsonify({"status": "not_found", "message": str(exc)}), 404
    return jsonify({"status": "ok"})


@bp.put("/models/<model_id>/default")
@require_auth
@require_admin
def put_model_default(model_id: str):
    """Choose which enabled model is the active default (PRD §10's
    "select different models" requirement)."""
    try:
        set_default_model(model_id, admin_id=g.device.id)
    except ValueError as exc:
        return jsonify({"status": "not_found", "message": str(exc)}), 404
    return jsonify({"status": "ok"})


# --- Config: every tunable limit, live -------------------------------------


@bp.get("/config")
@require_auth
@require_admin
def get_all_config():
    rows = db.session.query(GatewayConfig).order_by(GatewayConfig.key).all()
    return jsonify([
        {
            "key": row.key,
            "value": float(row.value),
            "description": row.description,
            "updated_by": row.updated_by,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ])


@bp.put("/config/<key>")
@require_auth
@require_admin
def put_config(key: str):
    """Edit one tunable limit. Body: ``{"value": <number>}``. The Redis
    cache for this key is invalidated immediately below, so the new value
    is live on the very next request -- never a redeploy, never even a
    cache-TTL wait."""
    from app.limits import _redis

    body = request.get_json(silent=True) or {}
    if "value" not in body:
        return jsonify({"status": "rejected", "message": "'value' is required."}), 400
    try:
        new_value = float(body["value"])
    except (TypeError, ValueError):
        return jsonify({"status": "rejected", "message": "'value' must be a number."}), 400

    row = db.session.get(GatewayConfig, key)
    if row is None:
        return jsonify({"status": "not_found", "message": f"Unknown config key: {key!r}"}), 404
    row.value = new_value
    row.updated_by = g.device.id
    db.session.add(
        AdminAction(admin_id=g.device.id, action="set_config", target=key, reason=str(new_value))
    )
    db.session.commit()

    # Invalidate the Redis cache immediately rather than waiting out the
    # TTL (see app/limits.py's resolve_limit), so an admin sees their own
    # change take effect on the very next request, not after a delay.
    _redis(current_app).delete(f"gwcfg:{key}")
    return jsonify({"status": "ok"})


# --- Users: view usage, disable, remove -------------------------------------


@bp.get("/users/<user_id>/usage")
@require_auth
@require_admin
def get_user_usage(user_id: str):
    """A usage summary — request counts and cost, never prompt content
    (PRD §4/§10: there is no prompt data anywhere in this schema to
    view)."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "not_found"}), 404
    summaries = (
        db.session
        .query(MonthlyUsageSummary)
        .filter_by(user_id=user_id)
        .order_by(MonthlyUsageSummary.year_month.desc())
        .limit(13)
        .all()
    )
    return jsonify({
        "user_id": user.id,
        "status": user.status,
        "created_at": user.created_at.isoformat(),
        "monthly_request_cap_override": user.monthly_request_cap,
        "monthly_usage": [
            {
                "year_month": s.year_month,
                "request_count": s.request_count,
                "total_cost_usd": float(s.total_cost_usd),
            }
            for s in summaries
        ],
    })


@bp.put("/users/<user_id>/status")
@require_auth
@require_admin
def put_user_status(user_id: str):
    """Set a user's status: ``active`` | ``reduced`` | ``review`` |
    ``blocked``. This is the **reversible, soft** way to turn off a
    user's hosted-AI usage — ``blocked`` stops every request immediately
    (checked first, in :func:`app.limits.check_request_allowed`) without
    deleting anything; flipping back to ``active`` restores access
    exactly as it was. For permanent removal, see
    :func:`delete_user` below instead."""
    body = request.get_json(silent=True) or {}
    new_status = body.get("status", "")
    if new_status not in ("active", "reduced", "review", "blocked"):
        return (
            jsonify({
                "status": "rejected",
                "message": "status must be one of active/reduced/review/blocked.",
            }),
            400,
        )
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "not_found"}), 404
    user.status = new_status
    db.session.add(
        AdminAction(
            admin_id=g.device.id,
            action="set_user_status",
            target=user_id,
            reason=body.get("reason", new_status),
        )
    )
    db.session.commit()
    return jsonify({"status": "ok"})


@bp.delete("/users/<user_id>")
@require_auth
@require_admin
def delete_user(user_id: str):
    """**Permanently remove** a user and their devices — a distinct,
    harder action than :func:`put_user_status`'s ``blocked``. Usage
    events keep their ``user_id`` foreign key for aggregate reporting
    integrity (metadata only, never content — PRD §4 — so retaining them
    after a user is removed carries no meaningful privacy cost); if a
    literal right-to-be-forgotten request requires erasing even that
    linkage, that's a follow-up anonymization step (reassign the row's
    ``user_id`` to a shared "deleted-user" placeholder), not part of this
    endpoint's default behavior."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "not_found"}), 404
    reason = (request.get_json(silent=True) or {}).get("reason", "")
    db.session.query(Device).filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.add(
        AdminAction(admin_id=g.device.id, action="delete_user", target=user_id, reason=reason)
    )
    db.session.commit()
    return "", 204


# --- Devices: revoke on behalf of a user ------------------------------------


@bp.put("/devices/<device_id>/status")
@require_auth
@require_admin
def put_device_status(device_id: str):
    body = request.get_json(silent=True) or {}
    new_status = body.get("status", "")
    if new_status not in ("active", "revoked"):
        return jsonify({"status": "rejected", "message": "status must be active or revoked."}), 400
    device = db.session.get(Device, device_id)
    if device is None:
        return jsonify({"status": "not_found"}), 404
    device.status = new_status
    db.session.add(
        AdminAction(
            admin_id=g.device.id, action="set_device_status", target=device_id, reason=new_status
        )
    )
    db.session.commit()
    return jsonify({"status": "ok"})


# --- Feature flags -----------------------------------------------------------


@bp.put("/feature-flags/<feature>")
@require_auth
@require_admin
def put_feature_flag(feature: str):
    """Enable/disable one feature, or the global ``hosted_ai`` switch
    (PRD §10's emergency kill switch)."""
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled", True))
    reason = body.get("reason", "")
    flag = db.session.get(FeatureFlag, feature)
    if flag is None:
        flag = FeatureFlag(feature=feature)
        db.session.add(flag)
    flag.enabled = enabled
    flag.disabled_reason = None if enabled else reason
    db.session.add(
        AdminAction(
            admin_id=g.device.id,
            action="enable_feature" if enabled else "disable_feature",
            target=feature,
            reason=reason,
        )
    )
    db.session.commit()
    return jsonify({"status": "ok"})


# --- Spend --------------------------------------------------------------------


@bp.get("/spend")
@require_auth
@require_admin
def get_spend():
    """Current-month total spend vs. the global budget cap (PRD §13)."""
    from app.limits import _month_key, _redis, resolve_limit

    month_key = _month_key()
    spend = float(_redis(current_app).get(f"gwspend:{month_key}") or 0.0)
    cap = resolve_limit(current_app, "global_monthly_budget_usd")
    return jsonify({"year_month": month_key, "spend_usd": spend, "budget_cap_usd": cap})
