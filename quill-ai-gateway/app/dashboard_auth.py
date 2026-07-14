"""Browser-session auth for the admin dashboard (``app/routes/dashboard.py``).

Deliberately reuses the **existing** admin credential -- a device's bearer
token, checked against ``GATEWAY_ADMIN_ALLOWLIST`` (``app/auth.py``) --
rather than inventing a second login system. The dashboard's "log in"
form is just "paste the admin device token you already have"; on success
it's remembered in Flask's signed, httponly session cookie so an admin
doesn't paste it on every page.

This is the simple v1. The PRD's dashboard section (docs/planning/
openai.md) documents a stronger upgrade path -- OIDC login via the
Keycloak instance GLOW already runs on this same server -- for later,
once a nicer login screen is worth the added complexity. No CAPTCHA
anywhere in this flow, matching the rest of the Gateway's accessibility
posture.
"""

from __future__ import annotations

from functools import wraps

from flask import current_app, redirect, request, session, url_for

from app.auth import hash_token
from app.models import Device


def verify_admin_token(app, token: str) -> Device | None:
    """Return the :class:`Device` if *token* is a valid, active,
    allowlisted admin credential; ``None`` otherwise. Used only by the
    dashboard login form -- the JSON admin API (``app/routes/admin.py``)
    authenticates every request independently via ``require_auth`` +
    ``require_admin`` and never touches the session.
    """
    from app.models import db

    device = db.session.query(Device).filter_by(token_hash=hash_token(token)).one_or_none()
    if device is None or device.status != "active":
        return None
    if device.id not in app.config["ADMIN_ALLOWLIST"]:
        return None
    return device


def dashboard_login_required(view):
    """Decorator for dashboard pages: redirects to the login form if the
    session doesn't hold a still-valid admin token. Re-checks validity on
    every request (not just at login time) so a revoked device is logged
    out of the dashboard immediately, exactly like the JSON API."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        token = session.get("admin_token")
        if not token or verify_admin_token(current_app, token) is None:
            session.pop("admin_token", None)
            return redirect(url_for("dashboard.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped
