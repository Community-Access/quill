"""The one real inference endpoint: ``POST /v1/chat`` (PRD §24).

Every feature (summarize, rewrite, proofread, explain, document Q&A) is the same
route with a different ``feature`` value -- the fixed server-side prompt template
for that feature (``app/prompts.py``) is what actually varies, never a
client-supplied system prompt.

This module is deliberately thin: it is the glue between ``app/limits.py``
(quota, size and refunds), ``app/model_registry.py`` (which model),
``app/prompts.py`` (what to ask, and how hard the model may think) and
``app/openai_client.py`` (the one real network call). Read those modules for
*why* each step exists; this file is the order they run in.

One rule is worth stating before the code, because it shapes every failure path
below. **Nobody is charged for a request that did not happen.** The rate-limit
counters are incremented by the gate in step 1, before the size check, before a
model is resolved and before anything is sent -- that ordering is deliberate
(see :func:`app.limits.refund_request`) and it means every later failure has
already taken one of the user's hundred requests. So every one of them refunds
it, and only then says so. The user cannot see the counter, so the claim and the
refund have to be the same commit.
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
    refund_request,
    reject_if_too_large,
    remaining_quota,
    resolve_limit,
)
from app.model_registry import NoDefaultModel, resolve_default_model
from app.openai_client import OpenAICallError, complete
from app.prompts import FEATURES, build_prompt, reasoning_effort_for

bp = Blueprint("chat", __name__)

_NOTHING_USED = "Nothing was sent and nothing was used."


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

    # 1. Quota / feature-flag / status gate (PRD §8) -- cheapest checks first,
    #    entirely before any tokenizing or model call. This is the step that
    #    charges; everything after it may have to give the charge back.
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

    # 2. Large-document safeguards (PRD §14.1, layers 2 and 3) -- a real,
    #    server-side, tokenized size check, independent of any client-side
    #    pre-check the caller may or may not have done. Nothing has been sent
    #    upstream yet, so this costs no money -- but it has already cost the
    #    user a counted request, which is what the refund undoes.
    try:
        reject_if_too_large(current_app, prompt, chunks)
    except RequestTooLarge as exc:
        refund_request(current_app, g.user, g.device, feature)
        return (
            jsonify({
                "status": "rejected",
                "reason": exc.reason,
                "message": f"{exc.message} {_NOTHING_USED}",
                "max_input_tokens": exc.max_value,
                "tokens_counted": exc.actual_value,
            }),
            422,
        )

    # 3. Resolve the active model (admin-configured, never client-chosen).
    try:
        model = resolve_default_model()
    except NoDefaultModel:
        refund_request(current_app, g.user, g.device, feature)
        current_app.logger.error(
            "No enabled model is marked default -- every /v1/chat request is failing. "
            "Set one on the Models page."
        )
        return (
            jsonify({
                "status": "unavailable",
                "scope": "global",
                "message": "Hosted AI is paused for everyone right now while we look "
                "into something — check quillforall.org/status, or use your own "
                f"API key in the meantime. {_NOTHING_USED}",
            }),
            503,
        )

    # 4. Build the fixed-template prompt and make the one real call.
    full_prompt = build_prompt(feature, prompt, chunks)
    max_output_tokens = int(resolve_limit(current_app, "max_output_tokens"))

    try:
        completion = complete(
            current_app,
            model.model_id,
            full_prompt,
            max_output_tokens,
            reasoning_effort_for(feature),
        )
    except OpenAICallError:
        refund_request(current_app, g.user, g.device, feature)
        current_app.logger.exception("OpenAI call failed for feature=%s", feature)
        return (
            jsonify({
                "status": "error",
                "message": "The AI service is having trouble right now — please try "
                "again in a moment, or use your own API key. Nothing was used.",
            }),
            502,
        )

    # 4a. An answer that is not an answer.
    #
    #     Reasoning tokens are drawn from the same budget as the reply and are
    #     billed at the output rate, so a model left thinking too hard can spend
    #     the whole allowance and return an empty string. The user experiences
    #     that as "QUILL's AI is broken"; charging them for it as well is the
    #     shape of bug nobody files and everybody abandons the feature over.
    #
    #     The provider still billed *us* for those tokens, so the usage event is
    #     written with the real cost -- the global budget must see money that was
    #     really spent. Only the user's own counters are given back.
    if completion.is_empty:
        refund_request(current_app, g.user, g.device, feature)
        record_usage(
            current_app,
            g.user,
            g.device,
            feature,
            model.model_id,
            completion.tokens_in,
            completion.tokens_out,
            model.estimate_cost_usd(completion.tokens_in, completion.tokens_out),
            status="throttled",
            abuse_flag=None,
            reasoning_tokens=completion.reasoning_tokens,
        )
        if completion.spent_everything_thinking:
            current_app.logger.error(
                "Model %s returned an empty answer after %d reasoning tokens for "
                "feature=%s. Lower the effort in app/prompts.py::REASONING_EFFORT, "
                "or raise max_output_tokens.",
                model.model_id,
                completion.reasoning_tokens,
                feature,
            )
        return (
            jsonify({
                "status": "error",
                "message": "The AI service returned an empty answer — please try "
                "again. Nothing was used.",
            }),
            502,
        )

    # 5. Record usage (this is what makes the quota checks above mean anything
    #    on the *next* request) and return the result plus a fresh quota
    #    snapshot for the client's status display.
    cost = model.estimate_cost_usd(completion.tokens_in, completion.tokens_out)
    record_usage(
        current_app,
        g.user,
        g.device,
        feature,
        model.model_id,
        completion.tokens_in,
        completion.tokens_out,
        cost,
        status="allowed",
        abuse_flag=None,
        reasoning_tokens=completion.reasoning_tokens,
    )
    quota = remaining_quota(current_app, g.user)

    return (
        jsonify({
            "status": "allowed",
            "text": completion.text,
            "tokens_in": completion.tokens_in,
            "tokens_out": completion.tokens_out,
            "remaining_quota": {
                "monthly": max(0, quota.monthly_cap - quota.monthly_used),
                "daily": max(0, quota.daily_cap - quota.daily_used),
                "hourly": max(0, quota.hourly_cap - quota.hourly_used),
            },
        }),
        200,
    )
