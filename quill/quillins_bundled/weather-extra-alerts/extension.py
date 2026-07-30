"""Weather Extra Alerts -- a bundled sample ``weather.alerts`` source.

Demonstrates the alert-source capability for Quill Weather: the handler returns
extra active alerts the host merges into the alert watch alongside the built-in
NWS feed. It makes **no** network call -- the sample advisory is read from the
Quillin's own storage (falling back to a demo advisory) -- so it needs no ``net``
capability (least privilege).

The out-of-process worker discards a handler's return value, so the result is
handed back by writing a JSON array to storage under ``_RESULT_KEY`` (kept in
lock-step with ``quill.core.quillins.app_host.ALERTS_RESULT_KEY``); the host
reads it from the shared storage dict, decodes it, and builds WeatherAlert rows.
"""

from __future__ import annotations

import json

# Must match quill.core.quillins.app_host.ALERTS_RESULT_KEY.
_RESULT_KEY = "__quill_weather_alerts_result__"


def extra_alerts(api, event: dict) -> None:  # noqa: ARG001 - event is unused for this source
    """Return this source's active alerts.

    A real source would read a regional feed the user configured; the sample
    returns a single demo advisory (from storage under ``advisory``, falling back
    to a built-in one) so it works out of the box.
    """

    stored = api.get_storage("advisory")
    if stored:
        try:
            alerts = json.loads(stored)
        except (ValueError, TypeError):
            alerts = []
    else:
        alerts = [
            {
                "id": "ext-weatherextraalerts-demo-1",
                "event": "Community Advisory",
                "severity": "Minor",
                "urgency": "Expected",
                "headline": "Sample community weather advisory from a Quillin source.",
                "area_description": "Demo area",
            }
        ]
    api.set_storage(_RESULT_KEY, json.dumps(alerts))


def register(api) -> None:
    api.register_command("extra_alerts", extra_alerts)
    api.log("Weather Extra Alerts loaded")
