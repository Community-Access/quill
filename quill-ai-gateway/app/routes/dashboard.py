"""The accessible admin web dashboard: every knob in ``app/routes/admin.py``'s
JSON API, as server-rendered HTML pages an admin can operate from a
browser without editing a file or crafting a `curl` command.

No JavaScript is used anywhere in this blueprint -- every page is a plain
HTML document; every interactive action is a native ``<form>`` POST or an
``<a>`` link, including destructive actions (a required confirmation
checkbox, enforced server-side, stands in for a JS ``confirm()`` dialog --
see ``delete_user`` below). This is a deliberate accessibility and
simplicity choice
(see ``docs/planning/openai.md``'s dashboard section): a screen reader or
keyboard-only user gets the exact same, fully-supported experience as
anyone else, and there's no client-side build step to maintain.

Auth: ``app/dashboard_auth.py``'s session bridge over the existing admin
bearer-token credential -- see that module's docstring.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.dashboard_auth import dashboard_login_required, verify_admin_token
from app.limits import _month_key, _redis, resolve_limit
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

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard", template_folder="../templates")

_FEATURES = ("document_qna", "summarize", "rewrite", "alt_text", "chat")


# --- Auth ---------------------------------------------------------------------


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("dashboard/login.html", next=request.args.get("next", ""))

    token = request.form.get("token", "").strip()
    next_path = request.form.get("next", "") or url_for("dashboard.overview")
    device = verify_admin_token(current_app, token)
    if device is None:
        flash("That token isn't a valid, active admin device token.", "error")
        return render_template("dashboard/login.html", next=next_path), 401
    session["admin_token"] = token
    session["admin_device_id"] = device.id
    flash("Signed in.", "success")
    return redirect(next_path)


@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_token", None)
    session.pop("admin_device_id", None)
    flash("Signed out.", "success")
    return redirect(url_for("dashboard.login"))


# --- Overview: budget, spend, usage trend --------------------------------------


def _budget_status(fraction: float) -> str:
    """Maps a spend fraction to one of the dataviz skill's reserved status
    roles (good/warning/serious/critical) -- never used as a categorical
    series color, and always paired with a text label wherever it's shown
    (see the templates: the status word is always in the markup, never
    color-only)."""
    if fraction >= 1.0:
        return "critical"
    if fraction >= 0.9:
        return "serious"
    if fraction >= 0.75:
        return "warning"
    return "good"


@bp.get("/")
@dashboard_login_required
def overview():
    month_key = _month_key()
    spend = float(_redis(current_app).get(f"gwspend:{month_key}") or 0.0)
    budget_cap = resolve_limit(current_app, "global_monthly_budget_usd")
    fraction = (spend / budget_cap) if budget_cap > 0 else 0.0
    status = _budget_status(fraction)

    summaries = (
        db.session
        .query(MonthlyUsageSummary.year_month)
        .distinct()
        .order_by(MonthlyUsageSummary.year_month.desc())
        .limit(6)
        .all()
    )
    trend = []
    for (ym,) in reversed(summaries):
        total = (
            db.session
            .query(db.func.sum(MonthlyUsageSummary.request_count))
            .filter(MonthlyUsageSummary.year_month == ym)
            .scalar()
            or 0
        )
        trend.append({"year_month": ym, "requests": int(total)})
    max_requests = max((row["requests"] for row in trend), default=0) or 1
    for row in trend:
        row["bar_percent"] = round(row["requests"] / max_requests * 100)

    user_count = db.session.query(db.func.count(User.id)).scalar() or 0
    active_devices = (
        db.session.query(db.func.count(Device.id)).filter(Device.status == "active").scalar() or 0
    )

    return render_template(
        "dashboard/overview.html",
        spend=spend,
        budget_cap=budget_cap,
        fraction=min(fraction, 1.0),
        fraction_percent=round(min(fraction, 1.0) * 100),
        status=status,
        month_key=month_key,
        trend=trend,
        user_count=user_count,
        active_devices=active_devices,
    )


# --- Models ---------------------------------------------------------------------


@bp.get("/models")
@dashboard_login_required
def models():
    all_models = list_models(include_disabled=True)
    return render_template("dashboard/models.html", models=all_models)


@bp.post("/models/<model_id>/toggle")
@dashboard_login_required
def toggle_model(model_id: str):
    enabled = request.form.get("enabled") == "1"
    try:
        set_model_enabled(model_id, enabled, admin_id=session["admin_device_id"])
        flash(f"{model_id} {'enabled' if enabled else 'disabled'}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.models"))


@bp.post("/models/<model_id>/make-default")
@dashboard_login_required
def make_default_model(model_id: str):
    try:
        set_default_model(model_id, admin_id=session["admin_device_id"])
        flash(f"{model_id} is now the default model.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.models"))


# --- Config: every tunable limit ------------------------------------------------


@bp.get("/config")
@dashboard_login_required
def config():
    rows = db.session.query(GatewayConfig).order_by(GatewayConfig.key).all()
    return render_template("dashboard/config.html", rows=rows)


@bp.post("/config/<key>")
@dashboard_login_required
def update_config(key: str):
    raw_value = request.form.get("value", "")
    row = db.session.get(GatewayConfig, key)
    if row is None:
        flash(f"Unknown config key: {key}", "error")
        return redirect(url_for("dashboard.config"))
    try:
        new_value = float(raw_value)
    except ValueError:
        flash("Value must be a number.", "error")
        return redirect(url_for("dashboard.config"))

    row.value = new_value
    row.updated_by = session["admin_device_id"]
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="set_config",
            target=key,
            reason=str(new_value),
        )
    )
    db.session.commit()
    _redis(current_app).delete(f"gwcfg:{key}")
    flash(f"{key} updated to {new_value:g}.", "success")
    return redirect(url_for("dashboard.config"))


# --- Users -----------------------------------------------------------------------


@bp.get("/users")
@dashboard_login_required
def users():
    all_users = db.session.query(User).order_by(User.created_at.desc()).limit(200).all()
    return render_template("dashboard/users.html", users=all_users)


@bp.get("/users/<user_id>")
@dashboard_login_required
def user_detail(user_id: str):
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("dashboard.users"))
    summaries = (
        db.session
        .query(MonthlyUsageSummary)
        .filter_by(user_id=user_id)
        .order_by(MonthlyUsageSummary.year_month.desc())
        .limit(13)
        .all()
    )
    return render_template("dashboard/user_detail.html", user=user, summaries=summaries)


@bp.post("/users/<user_id>/status")
@dashboard_login_required
def set_user_status(user_id: str):
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("dashboard.users"))
    new_status = request.form.get("status", "")
    if new_status not in ("active", "reduced", "review", "blocked"):
        flash("Invalid status.", "error")
        return redirect(url_for("dashboard.user_detail", user_id=user_id))
    user.status = new_status
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="set_user_status",
            target=user_id,
            reason=new_status,
        )
    )
    db.session.commit()
    flash(f"User status set to {new_status}.", "success")
    return redirect(url_for("dashboard.user_detail", user_id=user_id))


@bp.post("/users/<user_id>/delete")
@dashboard_login_required
def delete_user(user_id: str):
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("dashboard.users"))
    if request.form.get("confirm") != "yes":
        # Server-side enforcement of the confirmation checkbox -- the
        # client's `required` attribute is a UX nicety only, never trusted
        # (same principle as every quota check in this codebase).
        flash("Confirmation checkbox was not checked; nothing was deleted.", "error")
        return redirect(url_for("dashboard.user_detail", user_id=user_id))
    db.session.query(Device).filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="delete_user",
            target=user_id,
            reason="dashboard",
        )
    )
    db.session.commit()
    flash("User permanently removed.", "success")
    return redirect(url_for("dashboard.users"))


# --- Feature flags ------------------------------------------------------------


@bp.get("/feature-flags")
@dashboard_login_required
def feature_flags():
    flags = []
    for feature in ("hosted_ai", *_FEATURES):
        flag = db.session.get(FeatureFlag, feature)
        flags.append({
            "feature": feature,
            "enabled": flag.enabled if flag is not None else True,
            "disabled_reason": flag.disabled_reason if flag is not None else "",
            "is_global": feature == "hosted_ai",
        })
    return render_template("dashboard/feature_flags.html", flags=flags)


@bp.post("/feature-flags/<feature>")
@dashboard_login_required
def toggle_feature_flag(feature: str):
    enabled = request.form.get("enabled") == "1"
    reason = request.form.get("reason", "")
    flag = db.session.get(FeatureFlag, feature)
    if flag is None:
        flag = FeatureFlag(feature=feature)
        db.session.add(flag)
    flag.enabled = enabled
    flag.disabled_reason = None if enabled else reason
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="enable_feature" if enabled else "disable_feature",
            target=feature,
            reason=reason,
        )
    )
    db.session.commit()
    flash(f"{feature} {'enabled' if enabled else 'disabled'}.", "success")
    return redirect(url_for("dashboard.feature_flags"))


# --- Admin action log -----------------------------------------------------------


@bp.get("/audit-log")
@dashboard_login_required
def audit_log():
    actions = db.session.query(AdminAction).order_by(AdminAction.created_at.desc()).limit(100).all()
    return render_template("dashboard/audit_log.html", actions=actions)
