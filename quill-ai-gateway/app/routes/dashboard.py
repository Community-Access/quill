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

from app.config_schema import describe as describe_config_key
from app.config_schema import validate as validate_config_value
from app.costing import describe_change
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
    """Every tunable limit, grouped the way an operator thinks about them and
    priced so the consequence of a change is on the same page as the field
    that makes it (``app/config_schema.py``, ``app/costing.py``)."""
    from app.config_schema import grouped_keys
    from app.costing import load_cost_model, pricing_caveat
    from app.limits import resolve_limit

    rows = {row.key: row for row in db.session.query(GatewayConfig).all()}
    described_keys = set()
    groups = []
    for group_id, heading, blurb, entries in grouped_keys():
        members = []
        for entry in entries:
            row = rows.get(entry.key)
            if row is None:
                continue
            described_keys.add(entry.key)
            members.append({
                "meta": entry,
                "row": row,
                "display": entry.format_value(float(row.value)),
            })
        if members:
            groups.append({"id": group_id, "heading": heading, "blurb": blurb, "members": members})

    # Anything in the database this build has no description for. Shown rather
    # than hidden: a key nobody can see is a key nobody can fix, and the
    # fail-safe path in limits.py can invent one.
    undescribed = [row for key, row in sorted(rows.items()) if key not in described_keys]

    return render_template(
        "dashboard/config.html",
        groups=groups,
        undescribed=undescribed,
        cost=load_cost_model(current_app),
        budget_cap=resolve_limit(current_app, "global_monthly_budget_usd"),
        pricing_caveat=pricing_caveat(),
    )


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

    # Range check. Before this existed, 0.15 typed as 15 raised every user's
    # cost ceiling a hundredfold behind a green success message.
    problem = validate_config_value(key, new_value)
    if problem is not None:
        flash(problem, "error")
        return redirect(url_for("dashboard.config"))

    impact = describe_change(current_app, key, new_value)
    if impact is not None and impact.needs_confirmation and request.form.get("confirm") != "yes":
        flash(
            f"That change was not saved, because it more than doubles the cost. "
            f"{impact.sentence()} Tick the confirmation box beside the field and "
            f"save again if you meant it.",
            "error",
        )
        return redirect(url_for("dashboard.config"))

    described = describe_config_key(key)
    old_display = described.format_value(float(row.value)) if described else f"{float(row.value):g}"
    new_display = described.format_value(new_value) if described else f"{new_value:g}"
    name = described.name if described else key

    row.value = new_value
    row.updated_by = session["admin_device_id"]
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="set_config",
            target=key,
            reason=f"{old_display} -> {new_display}",
        )
    )
    db.session.commit()
    _redis(current_app).delete(f"gwcfg:{key}")

    message = f"{name} changed from {old_display} to {new_display}."
    if impact is not None:
        message += f" {impact.sentence()}"
    flash(message, "error" if (impact and impact.exceeds_budget) else "success")
    return redirect(url_for("dashboard.config"))


# --- Users -----------------------------------------------------------------------


@bp.get("/users")
@dashboard_login_required
def users():
    """Find an account by the support ID the person was shown, or browse the
    most recent. Without the search, a pseudonymous account id makes "somebody
    wrote to support" an unanswerable question."""
    query = (request.args.get("q") or "").strip()
    normalized = query.replace("-", "").replace(" ", "").lower()
    rows = db.session.query(User)
    if normalized:
        rows = rows.filter(User.id.ilike(f"{normalized}%"))
    all_users = rows.order_by(User.created_at.desc()).limit(200).all()
    return render_template("dashboard/users.html", users=all_users, query=query)


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
    from app.limits import _month_key, is_new_account, remaining_quota

    return render_template(
        "dashboard/user_detail.html",
        user=user,
        summaries=summaries,
        devices=list(user.devices),
        quota=remaining_quota(current_app, user),
        is_new=is_new_account(current_app, user),
        month_key=_month_key(),
    )


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
    """The switches, in plain language, with the global one kept apart.

    Two things this page has to get right. A feature that was **never built**
    and one **paused for an hour** are completely different facts, so the
    deferred ones are listed separately rather than mixed in with switches an
    operator might reasonably flip. And when the budget cap pauses the service
    automatically, the page must say *that* -- not show a switch somebody
    appears to have thrown -- because resuming without raising the cap re-pauses
    within the hour, and an operator who does not know that will think the
    switch is broken.
    """
    from app.limits import _month_key, resolve_limit
    from app.prompts import DEFERRED_FEATURES, FEATURE_LABELS, SHIPPED_FEATURES

    shipped = []
    for feature in SHIPPED_FEATURES:
        flag = db.session.get(FeatureFlag, feature)
        shipped.append({
            "feature": feature,
            "label": FEATURE_LABELS.get(feature, feature),
            "enabled": flag.enabled if flag is not None else True,
            "disabled_reason": flag.disabled_reason if flag is not None else "",
        })

    deferred = []
    for feature, reason in DEFERRED_FEATURES.items():
        flag = db.session.get(FeatureFlag, feature)
        deferred.append({
            "feature": feature,
            "label": FEATURE_LABELS.get(feature, feature),
            "enabled": flag.enabled if flag is not None else False,
            "reason": (flag.disabled_reason if flag is not None else "") or reason,
        })

    global_flag = db.session.get(FeatureFlag, "hosted_ai")
    global_enabled = global_flag.enabled if global_flag is not None else True
    global_reason = (global_flag.disabled_reason if global_flag is not None else "") or ""
    # _auto_pause_hosted_ai writes exactly this sentence.
    auto_paused = (not global_enabled) and "budget cap reached" in global_reason.lower()

    budget_cap = resolve_limit(current_app, "global_monthly_budget_usd")
    spend = float(_redis(current_app).get(f"gwspend:{_month_key()}") or 0.0)

    return render_template(
        "dashboard/feature_flags.html",
        shipped=shipped,
        deferred=deferred,
        global_enabled=global_enabled,
        global_reason=global_reason,
        global_updated_at=global_flag.updated_at if global_flag is not None else None,
        auto_paused=auto_paused,
        budget_cap=budget_cap,
        spend=spend,
    )


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


#: What each recorded action reads as in a sentence. ``{target}`` is the user,
#: device, feature or config key it was done to.
_ACTION_SENTENCES: dict[str, str] = {
    "set_config": "changed the limit {target}",
    "set_quota": "changed the limits for {target}",
    "reset_usage": "gave {target} their allowance back",
    "set_user_status": "changed the account status of {target}",
    "delete_user": "permanently removed {target}",
    "set_device_status": "changed the status of computer {target}",
    "rotate_device_token": "issued a new token for computer {target}",
    "enable_feature": "switched {target} back on",
    "disable_feature": "switched {target} off",
    "enable_model": "enabled the model {target}",
    "disable_model": "disabled the model {target}",
    "set_default_model": "made {target} the default model",
    "test_key": "tested the provider key against {target}",
}


@bp.get("/audit-log")
@dashboard_login_required
def audit_log():
    """Every admin action, most recent first, as sentences.

    The structured columns are underneath for filtering, but the sentence is
    what is read. "18 October, 09:14 -- admin f3a8 gave A1B2-C3D4 their
    allowance back. Reason: ran out during a demo." answers the question in one
    pass; five columns of identifiers make the reader assemble it themselves,
    every row, out loud.
    """
    actions = db.session.query(AdminAction).order_by(AdminAction.created_at.desc()).limit(100).all()
    rows = []
    for action in actions:
        target = action.target
        user = db.session.get(User, target) if len(target) > 20 else None
        if user is not None:
            target = user.support_id
        template = _ACTION_SENTENCES.get(action.action, "did " + action.action + " to {target}")
        rows.append({
            "action": action,
            "sentence": template.format(target=target),
            "admin_short": action.admin_id[:8],
        })
    return render_template("dashboard/audit_log.html", rows=rows)


# --- Users: give an allowance back, change one person's limits ----------------


@bp.post("/users/<user_id>/reset-usage")
@dashboard_login_required
def reset_usage(user_id: str):
    """Put one person's month back to zero.

    Clears the request counters and the running cost total together. Doing
    either alone produces a reset that looks as though it silently failed --
    see :func:`app.limits.reset_user_usage`.
    """
    from app.limits import reset_user_usage

    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("dashboard.users"))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Give a reason for the reset — it goes in the audit log.", "error")
        return redirect(url_for("dashboard.user_detail", user_id=user_id))

    cleared = reset_user_usage(current_app, user)
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="reset_usage",
            target=user_id,
            reason=reason,
        )
    )
    db.session.commit()
    flash(
        f"Allowance reset. Cleared {cleared['requests_cleared']} request(s) and "
        f"${cleared['cost_cleared_usd']:.4f} of recorded cost for this month. "
        "They can use the service again immediately.",
        "success",
    )
    return redirect(url_for("dashboard.user_detail", user_id=user_id))


@bp.post("/users/<user_id>/caps")
@dashboard_login_required
def set_user_caps(user_id: str):
    """Override one person's limits, or clear the overrides.

    An empty field means "no override" and returns them to the live global
    default, which is what makes every change here reversible.
    """
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("dashboard.users"))

    raw_requests = (request.form.get("monthly_request_cap") or "").strip()
    raw_cost = (request.form.get("monthly_cost_cap_usd") or "").strip()

    if raw_requests == "":
        user.monthly_request_cap = None
    else:
        try:
            parsed = int(raw_requests)
        except ValueError:
            flash("Requests per month must be a whole number, or blank.", "error")
            return redirect(url_for("dashboard.user_detail", user_id=user_id))
        if parsed < 0 or parsed > 10_000:
            flash("Requests per month must be between 0 and 10,000.", "error")
            return redirect(url_for("dashboard.user_detail", user_id=user_id))
        user.monthly_request_cap = parsed

    if raw_cost == "":
        user.monthly_cost_cap_usd = None
    else:
        try:
            parsed_cost = float(raw_cost)
        except ValueError:
            flash("The cost ceiling must be a number, or blank.", "error")
            return redirect(url_for("dashboard.user_detail", user_id=user_id))
        if parsed_cost < 0 or parsed_cost > 1000:
            flash("The cost ceiling must be between $0 and $1,000.", "error")
            return redirect(url_for("dashboard.user_detail", user_id=user_id))
        user.monthly_cost_cap_usd = parsed_cost

    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="set_quota",
            target=user_id,
            reason=(request.form.get("reason") or "").strip() or "no reason given",
        )
    )
    db.session.commit()
    flash("This person's limits were updated.", "success")
    return redirect(url_for("dashboard.user_detail", user_id=user_id))


@bp.post("/devices/<device_id>/revoke")
@dashboard_login_required
def revoke_device(device_id: str):
    device = db.session.get(Device, device_id)
    if device is None:
        flash("Computer not found.", "error")
        return redirect(url_for("dashboard.users"))
    device.status = "revoked"
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="set_device_status",
            target=device_id,
            reason="revoked",
        )
    )
    db.session.commit()
    flash(
        "That computer is signed out. It stops working on its very next request; "
        "the person can connect it again from QUILL whenever they like.",
        "success",
    )
    return redirect(url_for("dashboard.user_detail", user_id=device.user_id))


@bp.post("/devices/<device_id>/rotate")
@dashboard_login_required
def rotate_device(device_id: str):
    """Issue a new token without signing the computer out.

    The answer to "this may have leaked but I am not certain". The new token is
    shown once, here, and never again -- only its hash is stored.
    """
    from app.auth import rotate_device_token

    device = db.session.get(Device, device_id)
    if device is None:
        flash("Computer not found.", "error")
        return redirect(url_for("dashboard.users"))
    token = rotate_device_token(device)
    db.session.add(
        AdminAction(
            admin_id=session["admin_device_id"],
            action="rotate_device_token",
            target=device_id,
            reason=(request.form.get("reason") or "").strip() or "no reason given",
        )
    )
    db.session.commit()
    flash(
        f"New token issued. It is shown once and never again: {token} — the old "
        "one stopped working the moment this was saved.",
        "success",
    )
    return redirect(url_for("dashboard.user_detail", user_id=device.user_id))


# --- Reference pages ----------------------------------------------------------


@bp.get("/locked")
@dashboard_login_required
def locked():
    """Everything that affects cost or safety and is deliberately in code.

    A protection the operator cannot see is one they will assume is missing --
    or, worse, assume is a dial they have already checked.
    """
    from app.openai_client import ALLOWED_BODY_KEYS
    from app.prompts import (
        DEFERRED_FEATURES,
        FEATURE_LABELS,
        REASONING_EFFORT,
        SHIPPED_FEATURES,
        TEMPLATES,
    )

    return render_template(
        "dashboard/locked.html",
        shipped=[
            {
                "feature": f,
                "label": FEATURE_LABELS.get(f, f),
                "effort": REASONING_EFFORT.get(f, "none"),
                "template": TEMPLATES[f],
            }
            for f in SHIPPED_FEATURES
        ],
        deferred=[
            {"feature": f, "label": FEATURE_LABELS.get(f, f), "reason": reason}
            for f, reason in DEFERRED_FEATURES.items()
        ],
        allowed_keys=sorted(ALLOWED_BODY_KEYS),
    )


@bp.get("/safety")
@dashboard_login_required
def safety():
    """The checks that hold this service together, and whether they are holding.

    Two rows have a live state rather than a fixed one -- whether alerts reach a
    human, and when the scheduled jobs last ran -- and both are the kind of
    thing that rots silently. An alert webhook that was never configured is not
    a missing nicety: it is the difference between noticing at 50% of budget and
    noticing when the service switches itself off.
    """
    from app.costing import load_cost_model
    from app.limits import _month_key, registrations_blocked_today, resolve_limit
    from app.model_registry import NoDefaultModel, resolve_default_model
    from app.models import DiagnosticRecord, UsageEvent

    try:
        resolve_default_model()
        model_ok = True
    except NoDefaultModel:
        model_ok = False

    cost = load_cost_model(current_app)
    budget_cap = resolve_limit(current_app, "global_monthly_budget_usd")
    spend = float(_redis(current_app).get(f"gwspend:{_month_key()}") or 0.0)

    # "No column can hold document text" is an invariant worth checking against
    # the live mapping rather than trusting a docstring: a migration that added
    # one would be the single worst regression this service could ship.
    content_columns = [
        c.name
        for c in UsageEvent.__table__.columns
        if c.name in {"prompt", "response", "text", "content", "document"}
    ]

    return render_template(
        "dashboard/safety.html",
        allowed_keys_count=4,
        blocked_today=registrations_blocked_today(current_app),
        new_account_hours=int(resolve_limit(current_app, "new_account_hours")),
        new_account_cap=int(resolve_limit(current_app, "new_account_request_cap")),
        reg_hourly=int(resolve_limit(current_app, "registration_hourly_cap_per_ip")),
        reg_daily=int(resolve_limit(current_app, "registration_daily_cap_per_ip")),
        budget_cap=budget_cap,
        spend=spend,
        budget_percent=round((spend / budget_cap * 100) if budget_cap else 0),
        alerts_configured=bool(current_app.config.get("ALERT_WEBHOOK_URL")),
        model_ok=model_ok,
        cost=cost,
        content_columns=content_columns,
        pending_diagnostics=db.session.query(DiagnosticRecord).count(),
    )


@bp.get("/glossary")
@dashboard_login_required
def glossary():
    """Plain definitions. The console is operated by whoever is awake, not
    only by whoever built it."""
    return render_template("dashboard/glossary.html")
