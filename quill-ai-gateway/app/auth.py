"""OAuth 2.0 Device Authorization Grant (RFC 8628) for QUILL AI Gateway
sign-in, and the bearer-token verification every other route depends on.

This mirrors the QUILL desktop client's existing, already-tested
``device_login.py``/``copilot_auth.py`` state machine (see
``docs/planning/openai.md`` §7) -- the server side of the same flow. The client
polls ``POST /v1/device/token`` using exactly the
pending/slow_down/authorized/denied/expired status vocabulary that existing
client code already knows how to drive.

**Anonymous registration** (PRD §7): confirming a device code creates a
brand-new pseudonymous :class:`~app.models.User` with no email required. This
keeps onboarding to "read a code, open a browser, click Confirm" with no
account, no password and no CAPTCHA -- which is the whole accessibility premise
of the product, and also the reason sign-ups have to be throttled somewhere
else (:func:`app.limits.check_registration_allowed`).

**Pending grants live in Redis, not in this process.** They used to live in a
module-level dict, which works perfectly on one worker and not at all on two:
Gunicorn is configured with ``-w 2``, so the worker that answered
``/v1/device/code`` is only ever a coin flip away from being a different worker
than the one that answers ``/connect`` or the client's next poll. The symptom
would have been an intermittent "that code wasn't recognized" on roughly half of
all sign-ins, which is the worst kind of bug to meet on your first contact with
a product. Redis already backs every rate-limit counter here, so this adds no
new dependency.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import string
from datetime import UTC, datetime, timedelta
from functools import wraps

from flask import current_app, g, jsonify, request

from app.models import Device, User, db

__all__ = [
    "client_ip",
    "confirm_device_code",
    "hash_token",
    "poll_device_token",
    "require_admin",
    "require_auth",
    "rotate_device_token",
    "start_device_flow",
]

_USER_CODE_ALPHABET = "".join(sorted(set(string.ascii_uppercase) - set("ILOU0158")))
"""Excludes visually and phonetically ambiguous characters (I/L/O/0/1/5/8-ish
confusions) -- the user code is read aloud by a screen reader and typed back by
a person, so ambiguity here is a real usability bug, not a cosmetic one."""


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


def client_ip(req=None) -> str:
    """The caller's address, honouring one layer of reverse proxy.

    Used only for sign-up throttling. ``X-Forwarded-For`` is trusted because
    this service is only ever reached through the Caddy instance that
    terminates TLS for it (see ``Caddyfile.example``) -- the leftmost entry is
    the real client. If it is ever exposed directly, that header becomes
    attacker-controlled and the throttle becomes decorative, which is called out
    in the deployment notes.
    """
    req = req or request
    forwarded = (req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (req.remote_addr or "")


# --- Pending grants (Redis) ---------------------------------------------------


def _redis(app):
    return app.extensions["gateway_redis"]


def _grant_key(device_code: str) -> str:
    return f"devgrant:{device_code}"


def _user_code_key(user_code: str) -> str:
    return f"devusercode:{user_code}"


def _load_grant(app, device_code: str) -> dict | None:
    raw = _redis(app).get(_grant_key(device_code))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:  # pragma: no cover - only reachable via manual corruption
        return None


def _save_grant(app, grant: dict, ttl_seconds: int) -> None:
    _redis(app).set(_grant_key(grant["device_code"]), json.dumps(grant), ex=max(1, ttl_seconds))


def _drop_grant(app, grant: dict) -> None:
    client = _redis(app)
    client.delete(_grant_key(grant["device_code"]))
    client.delete(_user_code_key(grant["user_code"]))


def _seconds_left(grant: dict, now: datetime) -> int:
    expires_at = datetime.fromisoformat(grant["expires_at"])
    return int((expires_at - now).total_seconds())


def start_device_flow(app) -> dict:
    """``POST /v1/device/code``: mint a new device/user code pair.

    The caller is responsible for having passed
    :func:`app.limits.check_registration_allowed` first -- this function does
    the minting, not the gatekeeping, so that the throttle's refusal can be
    shaped by the route that knows how to say it.
    """
    expires_seconds = app.config["DEVICE_CODE_EXPIRES_SECONDS"]
    interval = app.config["DEVICE_CODE_POLL_INTERVAL_SECONDS"]
    device_code = secrets.token_urlsafe(24)
    user_code = _generate_user_code()
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_seconds)

    grant = {
        "device_code": device_code,
        "user_code": user_code,
        "expires_at": expires_at.isoformat(),
        "interval": interval,
        "status": "pending",
        "device_id": None,
        "token": None,
        "last_poll_at": None,
    }
    _save_grant(app, grant, expires_seconds)
    # The reverse index is what lets /connect find a grant from the eight
    # characters a person typed, without scanning every key in Redis.
    _redis(app).set(_user_code_key(user_code), device_code, ex=expires_seconds)

    base_url = app.config["PUBLIC_BASE_URL"]
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": f"{base_url}/connect",
        "verification_uri_complete": f"{base_url}/connect?code={user_code}",
        "interval": interval,
        "expires_in": expires_seconds,
    }


def confirm_device_code(app, user_code: str) -> bool:
    """Called by the Gateway-hosted confirmation page when a human clicks
    Confirm after typing or reading their code.

    Creates a fresh pseudonymous user and device row. Returns ``False`` if the
    code is unknown, already used, or expired -- the page says the same thing
    for all three on purpose, since distinguishing them would let somebody probe
    which codes exist.
    """
    device_code = _redis(app).get(_user_code_key(user_code))
    if device_code is None:
        return False
    grant = _load_grant(app, device_code)
    if grant is None or grant["status"] != "pending":
        return False

    now = datetime.now(UTC)
    if _seconds_left(grant, now) <= 0:
        _drop_grant(app, grant)
        return False

    token = _generate_opaque_token()
    user = User()
    db.session.add(user)
    db.session.flush()  # populate user.id before creating the device row
    device = Device(user_id=user.id, token_hash=hash_token(token), label="QUILL desktop")
    db.session.add(device)
    db.session.commit()

    grant["status"] = "authorized"
    grant["device_id"] = device.id
    grant["token"] = token
    _save_grant(app, grant, max(1, _seconds_left(grant, now)))
    return True


def poll_device_token(app, device_code: str) -> tuple[int, dict]:
    """``POST /v1/device/token``: the client's poll. Returns
    ``(http_status, body)`` in exactly the shape PRD §24 documents."""
    grant = _load_grant(app, device_code)
    if grant is None:
        return 410, {"status": "expired"}

    now = datetime.now(UTC)
    remaining = _seconds_left(grant, now)
    if remaining <= 0:
        _drop_grant(app, grant)
        return 410, {"status": "expired"}

    last_poll = grant.get("last_poll_at")
    if last_poll is not None:
        since = (now - datetime.fromisoformat(last_poll)).total_seconds()
        if since < grant["interval"]:
            return 429, {"status": "slow_down"}
    grant["last_poll_at"] = now.isoformat()
    _save_grant(app, grant, remaining)

    if grant["status"] == "authorized":
        result = {
            "status": "authorized",
            "token": grant["token"],
            "device_id": grant["device_id"],
        }
        _drop_grant(app, grant)  # single-use: the code cannot be replayed
        return 200, result
    if grant["status"] == "denied":
        _drop_grant(app, grant)
        return 410, {"status": "denied"}
    return 428, {"status": "pending"}


# --- Token rotation ------------------------------------------------------------


def rotate_device_token(device: Device) -> str:
    """Issue a fresh bearer token for *device* and return it, once.

    The answer to "a token may have leaked but I am not certain". Revoking is
    the answer when you *are* certain, and it costs the user a re-registration;
    rotating costs them nothing they will notice, because the client stores the
    new token and carries on. The old hash is replaced in the same transaction,
    so there is never a moment when both tokens work.

    The raw token is returned here and never again -- only its hash is stored,
    exactly as at registration.
    """
    token = _generate_opaque_token()
    device.token_hash = hash_token(token)
    db.session.commit()
    return token


# --- Request authentication -----------------------------------------------------


def require_auth(view):
    """Decorator: resolves ``Authorization: Bearer <token>`` to a
    (:class:`User`, :class:`Device`) pair, stored on ``g.user``/``g.device``
    for the route to use. Returns ``401`` for a missing, unknown or revoked
    token -- this is the one place every authenticated route depends on, so it
    is the one place a token's validity is actually decided.
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
    """Decorator for ``/admin/*`` routes: requires ``g.device`` to already be
    set by :func:`require_auth`, so **``require_auth`` must be the decorator
    listed above this one** (Python applies decorators bottom-up, so the
    topmost-listed one runs first at request time):

    .. code-block:: python

        @bp.route("/admin/config")
        @require_auth
        @require_admin
        def view(): ...

    Checks the authenticated device's id against ``GATEWAY_ADMIN_ALLOWLIST``
    (PRD §10: "gated to an admin allowlist," deliberately a deployment-time
    config value, never something the admin console can grant to itself).
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        allowlist = current_app.config["ADMIN_ALLOWLIST"]
        if g.device.id not in allowlist:
            return jsonify({"status": "forbidden", "message": "Admin access required."}), 403
        return view(*args, **kwargs)

    return wrapped
