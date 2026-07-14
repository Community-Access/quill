"""Device-code auth endpoints (PRD §7, §24): ``/v1/device/code``,
``/v1/device/token``, and the human-facing ``/connect`` confirmation page.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, render_template_string, request

from app.auth import confirm_device_code, poll_device_token, require_auth, start_device_flow
from app.models import Device, db

bp = Blueprint("device", __name__)

_CONNECT_PAGE = """
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Connect QUILL</title></head>
<body>
  <main>
    <h1>Connect QUILL's free AI</h1>
    {% if error %}
      <p role="alert">{{ error }}</p>
    {% elif confirmed %}
      <p>Connected! Go back to QUILL — it will pick this up automatically.</p>
    {% else %}
      <form method="post">
        <label for="code">Enter the code shown in QUILL:</label>
        <input id="code" name="code" value="{{ prefill }}" autofocus>
        <button type="submit">Confirm</button>
      </form>
    {% endif %}
  </main>
</body>
</html>
"""
"""Deliberately minimal, semantic HTML: one labelled input, one button, no
JavaScript required to function. This page is reached over a plain
browser link from anywhere (phone, another computer), so it must not
assume any particular assistive technology setup beyond a standards-
compliant browser."""


@bp.post("/v1/device/code")
def device_code():
    return jsonify(start_device_flow(current_app)), 200


@bp.post("/v1/device/token")
def device_token():
    body = request.get_json(silent=True) or {}
    device_code_value = body.get("device_code", "")
    status, payload = poll_device_token(device_code_value)
    return jsonify(payload), status


@bp.route("/connect", methods=["GET", "POST"])
def connect():
    prefill = request.args.get("code", "")
    if request.method == "GET":
        return render_template_string(_CONNECT_PAGE, prefill=prefill, error=None, confirmed=False)

    code = request.form.get("code", "").strip().upper()
    ok = confirm_device_code(code)
    if not ok:
        return render_template_string(
            _CONNECT_PAGE,
            prefill=code,
            error="That code wasn't recognized, or has expired. Check QUILL for a fresh code.",
            confirmed=False,
        )
    return render_template_string(_CONNECT_PAGE, prefill="", error=None, confirmed=True)


@bp.delete("/v1/devices/<device_id>")
@require_auth
def revoke_device(device_id: str):
    """PRD §7's "compromised device" flow / the client's "This isn't my
    computer anymore" button. A user may only revoke their own devices
    here; revoking *another* user's device is an admin-only action (see
    ``app/routes/admin.py``)."""
    device = db.session.get(Device, device_id)
    if device is None or device.user_id != g.user.id:
        return jsonify({"status": "not_found"}), 404
    device.status = "revoked"
    db.session.commit()
    return "", 204
