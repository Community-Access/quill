"""``GET /v1/config`` and ``GET /v1/quota`` (PRD §24): the two read-only
endpoints that power the client's "magical" usage display -- the status
bar indicator, the AI Hub panel, and the About dialog's usage line all
read from ``/v1/quota``, and the client's own large-document pre-check
(PRD §14.1 layer 1) reads its thresholds from ``/v1/config`` once per
session so it always reflects whatever an admin has most recently set.

**Web search** (2026-10-15) appears in both. ``/v1/config`` carries a
``web_search`` entry -- whether it is on and the monthly number of searches --
and, while it is on, a catalogue row so the client's pad offers it with no
release; ``/v1/quota`` carries how many of this month's searches are used.
Older clients ignore every key they do not know.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify

from app.auth import require_auth
from app.limits import (
    _effective_feature_cap,
    remaining_quota,
    resolve_feature_cap,
    resolve_limit,
    starter_allowance_ends_at,
    web_searches_used,
)
from app.models import FeatureFlag, db
from app.prompts import CATALOGUE, DEFERRED_FEATURES, OPT_IN_FEATURES, SHIPPED_FEATURES

bp = Blueprint("client_config", __name__)


@bp.get("/v1/config")
def get_config():
    """No auth required -- these are limits, not anything user-specific,
    and the client needs them before it even offers to sign in (to decide
    whether to show "hosted AI" as an option at all)."""
    hosted_flag = db.session.get(FeatureFlag, "hosted_ai")
    hosted_enabled = hosted_flag.enabled if hosted_flag is not None else True

    # Driven from the feature table rather than a list written out here. A
    # hardcoded tuple went stale the moment Proofread and Explain were added:
    # the client asked what was available, was told about five features, and
    # two of them were ones it could no longer reach while two it *could* reach
    # went unmentioned.
    feature_flags = {}
    for feature in (*SHIPPED_FEATURES, *DEFERRED_FEATURES, *OPT_IN_FEATURES):
        flag = db.session.get(FeatureFlag, feature)
        # A deferred feature defaults to off when no row exists; a shipped one
        # defaults to on. Erring the other way would have the client offering a
        # button for something that was never built.
        default = feature in SHIPPED_FEATURES
        feature_flags[feature] = flag.enabled if flag is not None else default

    max_input_tokens = int(resolve_limit(current_app, "max_input_tokens"))
    return jsonify({
        "max_input_tokens": max_input_tokens,
        "max_output_tokens": int(resolve_limit(current_app, "max_output_tokens")),
        "max_chunks_per_request": int(resolve_limit(current_app, "max_chunks_per_request")),
        "max_image_bytes": int(resolve_limit(current_app, "max_image_bytes")),
        "max_image_edge_px": int(resolve_limit(current_app, "max_image_edge_px")),
        "hosted_ai_enabled": hosted_enabled,
        "feature_flags": feature_flags,
        # Added 2026-10. Older clients read only the keys above and ignore
        # this one; newer ones offer whatever entry they do not already have
        # built in, so a new text tool needs no client release.
        "features": _catalogue(feature_flags, hosted_enabled, max_input_tokens),
        # Added 2026-10-15: whether web search is offered, and how many
        # searches a month each account gets. Off unless an operator turned
        # the flag on (app/prompts.py::OPT_IN_FEATURES).
        "web_search": {
            "enabled": bool(hosted_enabled and feature_flags.get("web_search", False)),
            "monthly_cap": int(resolve_feature_cap(current_app, "web_search")),
        },
    })


def _catalogue(
    feature_flags: dict[str, bool], hosted_enabled: bool, max_input_tokens: int
) -> list[dict]:
    """The feature catalogue: one entry per shipped feature that is on now.

    A feature switched off in the console leaves the catalogue as well as
    turning its flag false, so a client never builds a row for something that
    would only answer with a refusal; with the whole service paused the list
    is empty. ``id`` is the value to send as ``feature`` to ``/v1/chat`` and
    names the fixed template here; the client never supplies one.
    ``max_input_tokens`` is this feature's input ceiling -- the global one
    today, carried per entry so a future feature can have a smaller one
    without a new key.
    """
    if not hosted_enabled:
        return []
    entries = []
    for feature in (*SHIPPED_FEATURES, *OPT_IN_FEATURES):
        meta = CATALOGUE.get(feature)
        if meta is None or not feature_flags.get(feature, False):
            continue
        entries.append({
            "id": feature,
            "label": meta["label"],
            "help": meta["help"],
            "input": meta["input"],
            "max_input_tokens": max_input_tokens,
        })
    return entries


@bp.get("/v1/quota")
@require_auth
def get_quota():
    """Powers the client's status-bar / AI Hub / About-dialog usage
    display (see ``docs/planning/openai.md`` §17.2 and §24) — purely
    informational; the client never uses this to enforce anything, only
    to show it, exactly like every number in this response is re-checked
    authoritatively server-side on the next real ``/v1/chat`` call."""
    quota = remaining_quota(current_app, g.user)
    starter_until = starter_allowance_ends_at(current_app, g.user)
    return jsonify({
        # Both absent-safe for older clients, which ignore unknown keys. The
        # standard cap is the live setting, not a constant: an operator can
        # move it, and the client says whatever the server says.
        "starter_until": starter_until.isoformat() if starter_until else None,
        "standard_monthly_request_cap": int(resolve_limit(current_app, "monthly_request_cap")),
        "monthly_request_cap": quota.monthly_cap,
        "monthly_requests_used": quota.monthly_used,
        "daily_request_cap": quota.daily_cap,
        "daily_requests_used": quota.daily_used,
        "reset_at": quota.reset_at.isoformat(),
        "status": g.user.status,
        # Added 2026-10-15, display only like the rest: this account's web
        # searches this month (its own cap, which an admin may have set).
        "web_search_monthly_cap": _effective_feature_cap(current_app, g.user.id, "web_search"),
        "web_searches_used": web_searches_used(current_app, g.user),
    })
