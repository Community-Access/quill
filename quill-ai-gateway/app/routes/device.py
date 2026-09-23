"""Device-code auth endpoints (PRD §7, §24): ``/v1/device/code``,
``/v1/device/token``, ``/v1/device/rotate``, the user's own revoke, and the
human-facing ``/connect`` confirmation page.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, render_template_string, request

from app.auth import (
    client_ip,
    confirm_device_code,
    poll_device_token,
    require_auth,
    rotate_device_token,
    start_device_flow,
)
from app.limits import (
    RegistrationThrottled,
    check_device_budget,
    check_registration_allowed,
    note_device_registered,
    note_registration_blocked,
    release_device_slot,
)
from app.models import Device, db

bp = Blueprint("device", __name__)

_CONNECT_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Connect QUILL</title>
</head>
<body>
  <main>
    <h1>Connect QUILL's free AI</h1>
    {% if error %}
      <p role="alert">{{ error }}</p>
    {% elif confirmed %}
      <p role="status">Connected. Go back to QUILL &mdash; it will pick this up
        automatically. You can close this page.</p>
    {% else %}
      <p>QUILL is showing you an eight-character code. Type it here to connect
        that computer. There is no account and no password.</p>
      <form method="post">
        <label for="code">Enter the code shown in QUILL</label>
        <input id="code" name="code" value="{{ prefill }}" autocomplete="off"
               autocapitalize="characters" spellcheck="false" autofocus>
        <button type="submit">Confirm</button>
      </form>
      <p>When you use AI in QUILL, the passage you selected is sent to QUILL and
        on to OpenAI, which writes the answer. QUILL records how many requests
        you make and how big they were. QUILL does not record what you wrote or
        what came back.</p>
    {% endif %}
  </main>
</body>
</html>
"""
"""Deliberately minimal, semantic HTML: one labelled input, one button, no
JavaScript required to function, and the privacy summary on the page rather
than behind a link. This page is reached over a plain browser link from
anywhere -- a phone, a library computer, somebody else's laptop -- so it must
not assume any particular assistive technology setup beyond a standards-
compliant browser, and it must not assume the reader has seen QUILL's own
sign-in window."""


@bp.post("/v1/device/code")
def device_code():
    """Start a sign-up. Throttled per internet address before anything is
    minted (see :func:`app.limits.check_registration_allowed` for why an
    unauthenticated, account-free registration endpoint has to be)."""
    try:
        check_registration_allowed(current_app, client_ip())
        # How fast, and how many at once. The second is what stops somebody
        # connecting one more machine every few days -- each of which is a
        # whole new account with a whole new allowance.
        check_device_budget(current_app, client_ip())
    except RegistrationThrottled as exc:
        note_registration_blocked(current_app)
        return (
            jsonify({"status": "throttled", "message": exc.message}),
            429,
            {"Retry-After": str(exc.retry_after_seconds)},
        )
    return jsonify(start_device_flow(current_app)), 200


@bp.post("/v1/device/token")
def device_token():
    body = request.get_json(silent=True) or {}
    device_code_value = body.get("device_code", "")
    status, payload = poll_device_token(current_app, device_code_value)
    return jsonify(payload), status


@bp.post("/v1/device/rotate")
@require_auth
def rotate_token():
    """Swap this device's bearer token for a fresh one.

    The client calls this on a token older than 180 days, and an admin can
    trigger it from the console for a token that may have leaked. It is
    authenticated by the *current* token, so a rotation is proof of possession:
    somebody who has already lost the token cannot use this to lock the real
    owner out, they can only do what revocation would do anyway.
    """
    token = rotate_device_token(g.device)
    return jsonify({"status": "ok", "token": token, "device_id": g.device.id}), 200


@bp.route("/connect", methods=["GET", "POST"])
def connect():
    prefill = request.args.get("code", "")
    if request.method == "GET":
        return render_template_string(_CONNECT_PAGE, prefill=prefill, error=None, confirmed=False)

    code = request.form.get("code", "").strip().upper()
    if confirm_device_code(current_app, code):
        # Counted here rather than at /v1/device/code: a code that is minted and
        # never confirmed has cost nobody a slot.
        note_device_registered(current_app, client_ip())
        return render_template_string(_CONNECT_PAGE, prefill="", error=None, confirmed=True)
    return render_template_string(
        _CONNECT_PAGE,
        prefill=code,
        # One message for unknown, used and expired alike: telling them apart
        # would let somebody probe which codes exist.
        error="That code wasn't recognized, or has expired. Check QUILL for a fresh code.",
        confirmed=False,
    )


@bp.delete("/v1/devices/<device_id>")
@require_auth
def revoke_device(device_id: str):
    """PRD §7's "compromised device" flow, and the client's "sign out this
    computer" button. A user may only revoke their own devices here; revoking
    *another* user's device is an admin-only action (``app/routes/admin.py``)."""
    device = db.session.get(Device, device_id)
    if device is None or device.user_id != g.user.id:
        return jsonify({"status": "not_found"}), 404
    device.status = "revoked"
    db.session.commit()
    # Give the slot back, so somebody who signs an old laptop out before
    # connecting a new one is not refused for doing exactly the right thing.
    release_device_slot(current_app, client_ip())
    return "", 204
