"""The one real inference endpoint: ``POST /v1/chat`` (PRD §24).

Every feature (document Q&A, summarize, rewrite, chat) is the same route
with a different ``feature`` value -- the fixed server-side prompt
template for that feature (``app/prompts.py``) is what actually varies,
never a client-supplied system prompt.

This module is deliberately thin: it's the glue between
``app/limits.py`` (quota + size enforcement), ``app/model_registry.py``
(which model to use), ``app/prompts.py`` (what to actually ask), and
``app/openai_client.py`` (the one real network call) -- read those
modules to understand *why* each step exists; this file is just the
order they run in.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from app.auth import require_auth
from app.limits import (
    FeatureUnavailable,
    QuotaExceeded,
    RequestTooLarge,
    check_request_allowed,
    record_usage,
    reject_if_too_large,
    remaining_quota,
    resolve_limit,
)
from app.model_registry import NoDefaultModel, resolve_default_model
from app.openai_client import OpenAICallError, complete
from app.prompts import FEATURES, build_prompt

bp = Blueprint("chat", __name__)


@bp.post("/v1/chat")
@require_auth
def chat():
    body = request.get_json(silent=True) or {}
    feature = body.get("feature", "")
    prompt = body.get("prompt", "")
    chunks = body.get("chunks") or []

    if feature not in FEATURES:
        return (
            jsonify({
                "status": "rejected",
                "reason": "unknown_feature",
                "message": f"Unknown feature: {feature!r}.",
            }),
            400,
        )
    if not prompt or not isinstance(prompt, str):
        return (
            jsonify({
                "status": "rejected",
                "reason": "empty_prompt",
                "message": "No prompt was provided.",
            }),
            400,
        )

    # 1. Quota / feature-flag / status gate (PRD §8) -- cheapest checks
    #    first, entirely before any tokenizing or model call.
    try:
        check_request_allowed(current_app, g.user, g.device, feature)
    except FeatureUnavailable as exc:
        return jsonify({"status": "unavailable", "scope": exc.scope, "message": exc.message}), 503
    except QuotaExceeded as exc:
        return (
            jsonify({
                "status": "quota_exceeded",
                "scope": exc.scope,
                "reset_at": exc.reset_at.isoformat() if exc.reset_at else None,
                "message": exc.message,
            }),
            429,
        )

    # 2. Large-document safeguards (PRD §14.1, layers 2 and 3) -- real,
    #    server-side, tokenized size check, independent of any client-side
    #    pre-check the caller may or may not have done.
    try:
        reject_if_too_large(current_app, prompt, chunks)
    except RequestTooLarge as exc:
        return (
            jsonify({
                "status": "rejected",
                "reason": exc.reason,
                "message": exc.message,
                "max_input_tokens": exc.max_value,
                "tokens_counted": exc.actual_value,
            }),
            422,
        )

    # 3. Resolve the active model (admin-configured, never client-chosen).
    try:
        model = resolve_default_model()
    except NoDefaultModel:
        return (
            jsonify({
                "status": "unavailable",
                "scope": "global",
                "message": "Hosted AI is paused for everyone right now while we look "
                "into something — check quillforall.org/status, or use your own "
                "API key in the meantime.",
            }),
            503,
        )

    # 4. Build the fixed-template prompt and make the one real call.
    full_prompt = build_prompt(feature, prompt, chunks)
    max_output_tokens = int(resolve_limit(current_app, "max_output_tokens"))

    try:
        text, tokens_in, tokens_out = complete(
            current_app, model.model_id, full_prompt, max_output_tokens
        )
    except OpenAICallError:
        current_app.logger.exception("OpenAI call failed for feature=%s", feature)
        return (
            jsonify({
                "status": "error",
                "message": "The AI service is having trouble right now — please try "
                "again in a moment, or use your own API key.",
            }),
            502,
        )

    # 5. Record usage (this is what makes the quota checks above mean
    #    anything on the *next* request) and return the result plus a
    #    fresh quota snapshot for the client's status display.
    cost = model.estimate_cost_usd(tokens_in, tokens_out)
    record_usage(
        current_app,
        g.user,
        g.device,
        feature,
        model.model_id,
        tokens_in,
        tokens_out,
        cost,
        status="allowed",
    )
    quota = remaining_quota(current_app, g.user)

    return (
        jsonify({
            "status": "allowed",
            "text": text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "remaining_quota": {
                "monthly": max(0, quota.monthly_cap - quota.monthly_used),
                "daily": max(0, quota.daily_cap - quota.daily_used),
                "hourly": max(0, quota.hourly_cap - quota.hourly_used),
            },
        }),
        200,
    )
