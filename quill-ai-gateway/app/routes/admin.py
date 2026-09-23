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

from app.auth import require_admin, require_auth, rotate_device_token
from app.config_schema import describe as describe_config_key
from app.config_schema import validate as validate_config_value
from app.costing import describe_change
from app.model_registry import list_models, set_default_model, set_model_enabled
from app.models import (
    AdminAction,
    Device,
    FeatureFlag,
    GatewayConfig,
    MonthlyUsageSummary,
    User,
    UserFeatureCap,
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
    """Every tunable limit, with the plain-language description and the range
    it may be set to (``app/config_schema.py``). A caller that knows the bounds
    before it writes is a caller that does not need to be told no."""
    rows = db.session.query(GatewayConfig).order_by(GatewayConfig.key).all()
    payload = []
    for row in rows:
        entry = {
            "key": row.key,
            "value": float(row.value),
            "description": row.description,
            "updated_by": row.updated_by,
            "updated_at": row.updated_at.isoformat(),
        }
        described = describe_config_key(row.key)
        if described is not None:
            entry.update({
                "name": described.name,
                "group": described.group,
                "unit": described.unit,
                "minimum": described.minimum,
                "maximum": described.maximum,
                "explanation": described.sentence,
                "consequence": described.consequence,
                "cost_relevant": described.cost_relevant,
            })
        payload.append(entry)
    return jsonify(payload)


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

    # Range check. This route used to accept any float that parsed, which meant
    # 0.15 typed as 15 raised every user's cost ceiling a hundredfold and
    # answered 200 OK. See app/config_schema.py.
    problem = validate_config_value(key, new_value)
    if problem is not None:
        return jsonify({"status": "rejected", "reason": "out_of_range", "message": problem}), 400

    # A change that more than doubles the modelled bill needs to be meant. The
    # API's equivalent of the console's typed confirmation is an explicit
    # ``"confirm": true`` -- a script that really wants it says so, and a
    # mistyped decimal point does not.
    impact = describe_change(current_app, key, new_value)
    if impact is not None and impact.needs_confirmation and not body.get("confirm"):
        return (
            jsonify({
                "status": "rejected",
                "reason": "needs_confirmation",
                "message": (
                    f"This more than doubles the modelled cost. {impact.sentence()} "
                    'Send the same request with "confirm": true if that is intended.'
                ),
                "before_usd": round(impact.before_usd, 2),
                "after_usd": round(impact.after_usd, 2),
            }),
            409,
        )

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


# --- Users: find one, give their allowance back, change their limits --------


@bp.get("/users")
@require_auth
@require_admin
def search_users():
    """Find an account by support-ID prefix, or list the most recent.

    Accounts are pseudonymous UUIDs, which is the right privacy default and
    also means that without this route, "somebody wrote to support and I cannot
    find them" has no answer. The client shows every user their support ID --
    the first eight characters of their account id, grouped -- precisely so
    they have something to quote, and this is what turns that back into an
    account.
    """
    query = (request.args.get("q") or "").strip().replace("-", "").lower()
    rows = db.session.query(User)
    if query:
        rows = rows.filter(User.id.ilike(f"{query}%"))
    rows = rows.order_by(User.created_at.desc()).limit(50).all()
    return jsonify({
        "users": [
            {
                "user_id": user.id,
                "support_id": user.support_id,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            }
            for user in rows
        ]
    })


@bp.post("/users/<user_id>/usage/reset")
@require_auth
@require_admin
def reset_usage(user_id: str):
    """Put one person's month back to zero.

    Clears the Redis request counters **and** the running cost total together
    -- see :func:`app.limits.reset_user_usage` for why doing either on its own
    produces a reset that appears to have silently failed.
    """
    from app.limits import reset_user_usage

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "not_found"}), 404
    reason = (request.get_json(silent=True) or {}).get("reason", "")
    cleared = reset_user_usage(current_app, user)
    db.session.add(
        AdminAction(
            admin_id=g.device.id,
            action="reset_usage",
            target=user_id,
            reason=reason or "no reason given",
        )
    )
    db.session.commit()
    return jsonify({"status": "ok", "cleared": cleared})


@bp.put("/users/<user_id>/caps")
@require_auth
@require_admin
def put_user_caps(user_id: str):
    """Override this person's limits, or clear the overrides.

    Body keys, all optional: ``monthly_request_cap``, ``monthly_cost_cap_usd``,
    ``feature_caps`` (a ``{feature: cap}`` mapping). ``null`` clears an
    override and returns that person to the live global default -- which is
    what makes this reversible, and why the columns are nullable rather than
    always populated.
    """
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"status": "not_found"}), 404
    body = request.get_json(silent=True) or {}

    if "monthly_request_cap" in body:
        value = body["monthly_request_cap"]
        if value is None:
            user.monthly_request_cap = None
        else:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                return (
                    jsonify({
                        "status": "rejected",
                        "message": "Cap must be a whole number.",
                    }),
                    400,
                )
            if parsed < 0 or parsed > 10_000:
                return (
                    jsonify({
                        "status": "rejected",
                        "message": "Requests per month must be between 0 and 10,000.",
                    }),
                    400,
                )
            user.monthly_request_cap = parsed

    if "monthly_cost_cap_usd" in body:
        value = body["monthly_cost_cap_usd"]
        if value is None:
            user.monthly_cost_cap_usd = None
        else:
            try:
                parsed_cost = float(value)
            except (TypeError, ValueError):
                return jsonify({"status": "rejected", "message": "Ceiling must be a number."}), 400
            if parsed_cost < 0 or parsed_cost > 1000:
                return (
                    jsonify({
                        "status": "rejected",
                        "message": "Cost ceiling must be between $0 and $1,000.",
                    }),
                    400,
                )
            user.monthly_cost_cap_usd = parsed_cost

    feature_caps = body.get("feature_caps")
    if isinstance(feature_caps, dict):
        for feature, cap in feature_caps.items():
            existing = db.session.get(UserFeatureCap, {"user_id": user_id, "feature": feature})
            if cap is None:
                if existing is not None:
                    db.session.delete(existing)
                continue
            try:
                parsed_cap = int(cap)
            except (TypeError, ValueError):
                return (
                    jsonify({
                        "status": "rejected",
                        "message": f"Cap for {feature} must be a whole number.",
                    }),
                    400,
                )
            if existing is None:
                db.session.add(
                    UserFeatureCap(user_id=user_id, feature=feature, monthly_cap=parsed_cap)
                )
            else:
                existing.monthly_cap = parsed_cap

    db.session.add(
        AdminAction(
            admin_id=g.device.id,
            action="set_quota",
            target=user_id,
            reason=body.get("reason", ""),
        )
    )
    db.session.commit()
    return jsonify({"status": "ok"})


@bp.post("/devices/<device_id>/rotate")
@require_auth
@require_admin
def rotate_device(device_id: str):
    """Issue a new token for one device without signing it out.

    The answer to "this token may have leaked but I am not certain". Revoking
    is the answer when you are certain, and it costs the user a
    re-registration; rotating costs them nothing they will notice. The new
    token is returned once and never again.
    """
    device = db.session.get(Device, device_id)
    if device is None:
        return jsonify({"status": "not_found"}), 404
    reason = (request.get_json(silent=True) or {}).get("reason", "")
    token = rotate_device_token(device)
    db.session.add(
        AdminAction(
            admin_id=g.device.id, action="rotate_device_token", target=device_id, reason=reason
        )
    )
    db.session.commit()
    return jsonify({"status": "ok", "token": token})


# --- Is the provider key actually working? ------------------------------------


@bp.post("/test-key")
@require_auth
@require_admin
def test_key():
    """Make one tiny real call and report whether the provider key works.

    The key is set in the server's environment and read in exactly one place
    (``app/openai_client.py``). That is the right design -- it keeps the secret
    out of the database, out of backups, out of ``pg_dump`` output and out of
    anything with read access to Postgres -- but it has one operational cost:
    there is no way to *look* at it to check it is right, and a wrong key
    produces a 502 on somebody's first ever request rather than an error at
    deploy time.

    This closes that. It sends the shortest possible completion to the default
    model and reports ok or not-ok. It costs a fraction of a cent, never echoes
    the key, and never includes it in an error message.
    """
    from app.model_registry import NoDefaultModel, resolve_default_model
    from app.openai_client import OpenAICallError, complete

    if not current_app.config.get("OPENAI_API_KEY"):
        return (
            jsonify({
                "status": "not_configured",
                "message": "No provider key is set. Put OPENAI_API_KEY in the "
                "server's environment file and restart the service.",
            }),
            503,
        )

    try:
        model = resolve_default_model()
    except NoDefaultModel:
        return (
            jsonify({
                "status": "no_model",
                "message": "No enabled model is marked default, so there is nothing "
                "to test against. Set one on the Models page.",
            }),
            503,
        )

    try:
        completion = complete(current_app, model.model_id, "Reply with the word: ok", 16, "none")
    except OpenAICallError as exc:
        return (
            jsonify({
                "status": "failed",
                "model": model.model_id,
                # exc carries only the exception *type* name by construction --
                # see openai_client.complete -- so this can never echo the key.
                "message": f"The provider refused the call ({exc}). Check the key and "
                "the model id.",
            }),
            502,
        )

    db.session.add(
        AdminAction(admin_id=g.device.id, action="test_key", target=model.model_id, reason="ok")
    )
    db.session.commit()
    return jsonify({
        "status": "ok",
        "model": model.model_id,
        "message": f"The key works and {model.model_id} answered.",
        "tokens_used": completion.tokens_in + completion.tokens_out,
    })


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
