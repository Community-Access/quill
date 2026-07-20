"""Universal Location Descriptor (ULD) -- PRD section 10.

A ULD stores several ways to return to the same place and does not trust a
single fragile coordinate. This module builds descriptors from capture context
and resolves them against current content, falling through the six locator
layers in the order PRD 10.2 specifies. It never silently replaces an exact
bookmark with a guessed location; a low-confidence match returns a recovery
decision for the user to approve (PRD 17.4).

Pure logic, wx-free, unit-testable.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from quill.apps.beacon.model import Location


def fingerprint_text(text: str) -> str:
    """Normalized content fingerprint for reattachment after formatting changes."""
    norm = re.sub(r"\s+", " ", text or "").strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def normalize_quote(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def build_uld(
    *,
    resource_id: str,
    location_type: str = "native",
    native: dict[str, Any] | None = None,
    structural: dict[str, Any] | None = None,
    text_quote: str = "",
    quote_prefix: str = "",
    quote_suffix: str = "",
    positional: dict[str, Any] | None = None,
    media_start_ms: int | None = None,
    media_end_ms: int | None = None,
    heading_path: list[str] | None = None,
    display_summary: str = "",
) -> Location:
    """Construct a Location populated across every applicable locator layer."""
    quote = {
        "exact": normalize_quote(text_quote),
        "prefix": normalize_quote(quote_prefix),
        "suffix": normalize_quote(quote_suffix),
        "fingerprint": fingerprint_text(text_quote) if text_quote else "",
    }
    loc = Location(
        resource_id=resource_id,
        type=location_type,
        native_locator=native or {},
        structural_locator=structural or {},
        text_quote=quote if text_quote else {},
        positional_locator=positional or {},
        recovery_hints={},
        media_start_ms=media_start_ms,
        media_end_ms=media_end_ms,
        heading_path=list(heading_path or []),
        display_summary=display_summary
        or _derive_summary(heading_path, text_quote, media_start_ms),
        confidence=1.0,
    )
    return loc


def _derive_summary(heading_path: list[str] | None, quote: str, media_ms: int | None) -> str:
    parts = []
    if heading_path:
        parts.append(" > ".join(heading_path))
    if quote:
        parts.append(f'"{quote[:80]}{"..." if len(quote) > 80 else ""}"')
    if media_ms is not None:
        parts.append(_fmt_time(media_ms))
    return " | ".join(parts)


def _fmt_time(ms: int) -> str:
    s = ms // 1000
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


@dataclass
class Resolution:
    """Outcome of resolving a ULD against current content (PRD 10.2)."""

    matched: bool
    confidence: float
    layer: str  # native|structural|textQuote|fuzzy|positional|none
    position: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    nearest: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_review(self) -> bool:
        return self.matched and self.confidence < 0.9


def resolve(loc: Location, content: str | None = None) -> Resolution:
    """Fall through locator layers and return the best resolution.

    ``content`` is the current text of the containing resource (web page body,
    document text, transcript). When None, only native/positional/media
    locators can be trusted.
    """
    # 1. Native locator (anchor, CFI, bookmark id, chapter start) -- strongest.
    if loc.native_locator:
        return Resolution(True, 1.0, "native", loc.native_locator, "Native locator present.")

    # 2. Structural locator (heading path / landmark).
    if loc.structural_locator and content:
        pos = _find_structural(loc, content)
        if pos is not None:
            return Resolution(True, 0.95, "structural", pos, "Matched heading path.")
    elif loc.heading_path and content:
        pos = _find_heading_path(loc.heading_path, content)
        if pos is not None:
            return Resolution(True, 0.9, "structural", {"offset": pos}, "Matched heading path.")

    # 3. Exact text-quote match.
    if loc.text_quote and loc.text_quote.get("exact") and content:
        exact = loc.text_quote["exact"]
        offset = content.find(exact)
        if offset >= 0:
            return Resolution(True, 0.95, "textQuote", {"offset": offset}, "Exact text match.")

    # 4. Fuzzy text + surrounding-context match.
    if loc.text_quote and loc.text_quote.get("exact") and content:
        near = _fuzzy_match(loc.text_quote, content)
        if near is not None:
            return Resolution(
                True,
                near["confidence"],
                "fuzzy",
                {"offset": near["offset"]},
                "Near match; review recommended.",
                near,
            )

    # 5. Positional locator (line/column, page, timestamp) -- last known.
    if loc.positional_locator:
        return Resolution(
            True,
            0.6,
            "positional",
            loc.positional_locator,
            "Using last known position; exact location unconfirmed.",
        )

    # 6. Open containing resource; announce the exact location could not be confirmed.
    return Resolution(False, 0.0, "none", {}, "Exact location not found. Nearest match available.")


def _find_structural(loc: Location, content: str) -> dict[str, Any] | None:
    # structural_locator may carry a heading path or landmark + accessible name.
    path = loc.structural_locator.get("headingPath") or loc.structural_locator.get("path")
    if isinstance(path, list) and path:
        off = _find_heading_path(path, content)
        if off is not None:
            return {"offset": off}
    landmark = loc.structural_locator.get("landmark")
    name = loc.structural_locator.get("accessibleName")
    if landmark and name and name in content:
        return {"landmark": landmark, "name": name}
    return None


def _find_heading_path(path: list[str], content: str) -> int | None:
    """Find the offset of the last heading in the path appearing in order."""
    cursor = 0
    for heading in path:
        idx = content.find(heading, cursor)
        if idx < 0:
            return None
        cursor = idx + len(heading)
    return cursor


def _fuzzy_match(quote: dict[str, Any], content: str) -> dict[str, Any] | None:
    """Approximate match using a token-overlap score with prefix/suffix help.

    Returns the best window offset and a confidence between 0.5 and 0.89 so it
    always triggers review (PRD 10.2: never silently replace).
    """
    exact = normalize_quote(quote.get("exact", ""))
    if not exact:
        return None
    tokens = [t for t in re.split(r"\W+", exact.lower()) if len(t) > 2]
    if not tokens:
        return None
    window = len(exact) + 40
    best = (-1, 0.0)
    step = max(1, window // 4)
    for start in range(0, max(1, len(content) - window), step):
        blob = content[start : start + window].lower()
        hits = sum(1 for t in tokens if t in blob)
        score = hits / len(tokens)
        if score > best[1]:
            best = (start, score)
    offset, score = best
    if score < 0.5:
        return None
    # Prefix/suffix corroboration nudges confidence up but stays under 0.9.
    if quote.get("prefix") and quote["prefix"][:20] in content[max(0, offset - 50) : offset + 10]:
        score = min(0.88, score + 0.1)
    confidence = max(0.5, min(0.88, score))
    return {"offset": offset, "confidence": confidence}


def repair_suggestion(loc: Location, content: str) -> dict[str, Any]:
    """Propose a repair when a location fails (PRD 17.4 broken-location assistant)."""
    res = resolve(loc, content)
    return {
        "matched": res.matched,
        "layer": res.layer,
        "confidence": res.confidence,
        "position": res.position,
        "message": res.message,
        "previous_summary": loc.display_summary,
        "previous_heading_path": list(loc.heading_path),
        "previous_quote": loc.text_quote.get("exact", ""),
    }
