"""Beacon Transit Resolver -- a bundled sample ``beacon.resolver`` provider.

Demonstrates the location-resolver capability for Quill Beacon: the handler is
consulted as a fallback locator layer when the built-in native / structural /
text-quote / fuzzy / positional locators all fail to place a Universal Location
Descriptor. It makes **no** network call -- it searches the supplied content --
so it needs no ``net`` capability (least privilege).

The out-of-process worker discards a handler's return value, so the resolution is
handed back by writing a JSON object to storage under ``_RESULT_KEY`` (kept in
lock-step with ``quill.core.quillins.app_host.RESOLVER_RESULT_KEY``); the host
reads it from the shared storage dict and turns it into a Resolution.
"""

from __future__ import annotations

import json

# Must match quill.core.quillins.app_host.RESOLVER_RESULT_KEY.
_RESULT_KEY = "__quill_beacon_resolver_result__"


def resolve_location(api, event: dict) -> None:
    """Resolve a ULD against ``content`` with a case-insensitive quote search.

    ``event`` carries ``{"loc": {...}, "content": ...}``. The sample lower-cases
    both the saved exact quote and the content and reports the first offset it
    finds, at a deliberately low confidence so Beacon treats it as "needs review"
    (never a silent replacement of an exact bookmark).
    """

    loc = event.get("loc") or {}
    content = str(event.get("content", ""))
    quote = ""
    text_quote = loc.get("text_quote") if isinstance(loc, dict) else None
    if isinstance(text_quote, dict):
        quote = str(text_quote.get("exact", "")).strip()
    if not quote or not content:
        api.set_storage(_RESULT_KEY, "")
        return
    offset = content.lower().find(quote.lower())
    if offset < 0:
        api.set_storage(_RESULT_KEY, "")
        return
    resolution = {
        "matched": True,
        "confidence": 0.7,
        "layer": "quillin",
        "position": {"offset": offset},
        "message": "Matched by the Transit Resolver (case-insensitive quote). Review recommended.",
    }
    api.set_storage(_RESULT_KEY, json.dumps(resolution))


def register(api) -> None:
    api.register_command("resolve_location", resolve_location)
    api.log("Beacon Transit Resolver loaded")
