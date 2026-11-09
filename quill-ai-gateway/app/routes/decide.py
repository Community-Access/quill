"""``POST /v1/decide``: Jev picks one of this window's commands (command-key.md 7.6).

Thin, like ``chat.py``: the order things run in, with the reasons in
``app/jev.py``. The request body is checked and rebuilt before anything is
counted; the caps are counted before TypeSafe is asked; nothing the person typed
is logged.

Answers:

* 200: ``{"answers", "model", "usage"}``, TypeSafe's answer with only those fields.
* 400: the body was not one QUILL builds (``unknown_catalogue``, ``unknown_app``,
  ``bad_candidates``, ``unknown_command``, ``bad_request``).
* 429 ``limit_reached``, 402 ``no_credit``, 503 ``disabled``: the app says one
  line once and stops asking until tomorrow.
* 502 or 504 ``failed``: the app matches this one on the computer.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from app.auth import client_ip, require_auth
from app.jev import DecideError, ask_typesafe, build_body, check_caps, count, note_spend

bp = Blueprint("decide", __name__)


def _refuse(error: DecideError):
    count(current_app.extensions["gateway_redis"], f"refused:{error.error}")
    return jsonify({"error": error.error, "message": error.message}), error.status


def _jev_enabled() -> bool:
    from app.models import FeatureFlag, db

    if not current_app.config.get("JEV_ENABLED", True) or not current_app.config.get(
        "TYPESAFE_API_KEY"
    ):
        return False
    flag = db.session.get(FeatureFlag, "command_decide")
    return flag is None or bool(flag.enabled)


@bp.post("/v1/decide")
@require_auth
def decide():
    redis_client = current_app.extensions["gateway_redis"]
    count(redis_client, "requests")
    if not _jev_enabled():
        return _refuse(DecideError(503, "disabled", "Jev is turned off on this service."))
    try:
        built = build_body(request.get_json(silent=True))
        check_caps(current_app.config, redis_client, g.device.id, client_ip())
        answer = ask_typesafe(current_app.config, built.body, built.offered)
    except DecideError as error:
        if error.error == "disabled":
            current_app.logger.error("TypeSafe refused the service's key: check TYPESAFE_API_KEY.")
        return _refuse(error)
    tokens = answer["usage"]["input_tokens"]
    note_spend(redis_client, tokens)
    count(redis_client, "answered")
    count(redis_client, "input_tokens", tokens)
    count(redis_client, "latency_ms", answer.pop("latency_ms"))
    return jsonify(answer), 200
