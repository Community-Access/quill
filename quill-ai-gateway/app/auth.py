"""OAuth 2.0 Device Authorization Grant (RFC 8628) for QUILL AI Gateway
sign-in, and the bearer-token verification every other route depends on.

This mirrors the QUILL desktop client's existing, already-tested
``device_login.py``/``copilot_auth.py`` state machine (see
``docs/planning/openai.md`` §7) -- the server side of the same flow. The
client polls ``POST /v1/device/token`` using exactly the
pending/slow_down/authorized/denied/expired status vocabulary that
existing client code already knows how to drive.

**Anonymous registration** (PRD §7): confirming a device code creates a
brand-new pseudonymous :class:`~app.models.User` with no email required.
This keeps the initial rollout's onboarding to "read a code, open a
browser, click Confirm" with no account, no password, no CAPTCHA.
"""

from __future__ import annotations

import hashlib
import secrets
import string
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps

from flask import current_app, g, jsonify, request

from app.models import Device, User, db

_USER_CODE_ALPHABET = "".join(sorted(set(string.ascii_uppercase) - set("ILOU0158")))
"""Excludes visually/phonetically ambiguous characters (I/L/O/0/1/5/8-ish
confusions) -- the user code is read aloud by a screen reader and typed
back by a person, so ambiguity here is a real usability bug, not a
cosmetic one."""


def _generate_user_code() -> str:
    """An 8-character code formatted as ``ABCD-1234``-style groups, read
    naturally by a screen reader (``announce_device_code()``'s client-side
    counterpart expects exactly this shape)."""
    chars = [secrets.choice(_USER_CODE_ALPHABET) for _ in range(8)]
    return "".join(chars[:4]) + "-" + "".join(chars[4:])


def _generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 of a bearer token -- the only form ever stored (PRD §7:
    "never stores the raw token")."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class _PendingGrant:
    device_code: str
    user_code: str
    expires_at: datetime
    interval: int
    status: str = "pending"  # pending | authorized | denied
    device_id: str | None = None
    token: str | None = None
    last_poll_at: datetime | None = None


# In-memory store for pending (not-yet-authorized) grants only -- once
# authorized, the *result* (the device/token) lives durably in Postgres;
# this dict only ever holds transient, short-lived, pre-auth state, so
# losing it on a restart just means an in-flight device-code login has to
# start over, never a security or durability issue. A Redis-backed store
# is a natural upgrade if this ever needs to survive a restart mid-flow,
# but isn't necessary for correctness at this scale.
_pending_grants: dict[str, _PendingGrant] = {}


def start_device_flow(app) -> dict:
    """``POST /v1/device/code``: mint a new device/user code pair."""
    expires_seconds = app.config["DEVICE_CODE_EXPIRES_SECONDS"]
    interval = app.config["DEVICE_CODE_POLL_INTERVAL_SECONDS"]
    device_code = secrets.token_urlsafe(24)
    user_code = _generate_user_code()
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_seconds)

    _pending_grants[device_code] = _PendingGrant(
        device_code=device_code, user_code=user_code, expires_at=expires_at, interval=interval
    )

    base_url = app.config["PUBLIC_BASE_URL"]
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": f"{base_url}/connect",
        "verification_uri_complete": f"{base_url}/connect?code={user_code}",
        "interval": interval,
        "expires_in": expires_seconds,
    }


def confirm_device_code(user_code: str) -> bool:
    """Called by the (Gateway-hosted, not client-side) confirmation web
    page when a human clicks "Confirm" after typing/reading their code.
    Creates a fresh pseudonymous user + device row. Returns False if the
    code is unknown or already used/expired."""
    grant = next((g for g in _pending_grants.values() if g.user_code == user_code), None)
    if grant is None or grant.status != "pending":
        return False
    if datetime.now(UTC) > grant.expires_at:
        grant.status = "denied"
        return False

    token = _generate_opaque_token()
    user = User()
    db.session.add(user)
    db.session.flush()  # populate user.id before creating the device row
    device = Device(user_id=user.id, token_hash=hash_token(token), label="QUILL desktop")
    db.session.add(device)
    db.session.commit()

    grant.status = "authorized"
    grant.device_id = device.id
    grant.token = token
    return True


def poll_device_token(device_code: str) -> tuple[int, dict]:
    """``POST /v1/device/token``: the client's poll. Returns
    ``(http_status, body)`` in exactly the shape PRD §24 documents."""
    grant = _pending_grants.get(device_code)
    if grant is None:
        return 410, {"status": "expired"}

    now = datetime.now(UTC)
    if now > grant.expires_at:
        return 410, {"status": "expired"}

    if (
        grant.last_poll_at is not None
        and (now - grant.last_poll_at).total_seconds() < grant.interval
    ):
        return 429, {"status": "slow_down"}
    grant.last_poll_at = now

    if grant.status == "authorized":
        result = {"status": "authorized", "token": grant.token, "device_id": grant.device_id}
        del _pending_grants[device_code]  # single-use: the code cannot be replayed
        return 200, result
    if grant.status == "denied":
        del _pending_grants[device_code]
        return 410, {"status": "denied"}
    return 428, {"status": "pending"}


def require_auth(view):
    """Decorator: resolves ``Authorization: Bearer <token>`` to a
    (:class:`User`, :class:`Device`) pair, stored on ``g.user``/``g.device``
    for the route to use. Returns ``401`` for a missing/unknown/revoked
    token -- this is the one place every authenticated route depends on,
    so it's the one place a token's validity is actually decided.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"status": "unauthorized", "message": "Missing bearer token."}), 401
        token = header[len("Bearer ") :].strip()
        token_hash = hash_token(token)
        device = db.session.query(Device).filter_by(token_hash=token_hash).one_or_none()
        if device is None or device.status != "active":
            return jsonify({"status": "unauthorized", "message": "Invalid or revoked token."}), 401
        user = db.session.get(User, device.user_id)
        if user is None:
            return jsonify({"status": "unauthorized", "message": "Invalid or revoked token."}), 401
        g.user = user
        g.device = device
        return view(*args, **kwargs)

    return wrapped


def require_admin(view):
    """Decorator for ``/admin/*`` routes: requires ``g.device`` to already
    be set by :func:`require_auth`, so **``require_auth`` must be the
    decorator listed above this one** (Python applies decorators
    bottom-up, so the topmost-listed one runs first at request time):

    .. code-block:: python

        @bp.route("/admin/config")
        @require_auth
        @require_admin
        def view(): ...

    Checks the authenticated device's id against
    ``GATEWAY_ADMIN_ALLOWLIST`` (PRD §10: "gated to an admin allowlist,"
    deliberately a deployment-time config value, never something the
    admin console can grant to itself)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        allowlist = current_app.config["ADMIN_ALLOWLIST"]
        if g.device.id not in allowlist:
            return jsonify({"status": "forbidden", "message": "Admin access required."}), 403
        return view(*args, **kwargs)

    return wrapped
