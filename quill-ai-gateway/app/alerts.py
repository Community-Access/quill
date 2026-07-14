"""Budget-threshold and operational alerting (PRD §13's 50/75/90/100%
notifications).

A minimal, dependency-free webhook poster -- any Slack/Discord-style
incoming webhook that accepts ``{"text": "..."}`` works. If
``GATEWAY_ALERT_WEBHOOK_URL`` isn't configured (e.g. local development),
alerts are logged instead of posted, so nothing about this module ever
blocks a request on an unconfigured or unreachable webhook.
"""

from __future__ import annotations

import logging

import requests

_log = logging.getLogger("gateway.alerts")


def send_alert(app, message: str) -> None:
    """Best-effort: a failed alert must never fail the request that
    triggered it (this is called from inside :func:`app.limits.record_usage`,
    deep in the success path of an already-completed, already-billed
    OpenAI call -- raising here would be strictly worse than logging and
    moving on)."""
    from app.redaction import scrub

    safe_message = scrub(message)
    webhook_url = app.config.get("ALERT_WEBHOOK_URL", "")
    if not webhook_url:
        _log.warning("ALERT (no webhook configured): %s", safe_message)
        return
    try:
        requests.post(webhook_url, json={"text": safe_message}, timeout=5.0)
    except requests.RequestException:
        _log.exception("Failed to deliver alert webhook: %s", safe_message)
