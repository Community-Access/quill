"""Podcast and radio metadata normalization (PRD sections 11, 12).

Normalizes chapters from Podcasting 2.0 JSON and embedded ID3 CHAP/CTOC
frames into one ``MediaChapter`` model, retaining provenance (publisher,
provider, suggested, personal). Radio stream metadata is captured as a
resource metadata blob. Pure logic, wx-free, unit-testable.
"""

from __future__ import annotations

import json
from typing import Any

from quill.apps.beacon.model import MediaChapter


def parse_podcasting2_chapters(data: dict[str, Any] | str, resource_id: str) -> list[MediaChapter]:
    """Parse Podcasting 2.0 JSON chapters (PRD 11.2, ref 42.1).

    The spec format is ``{"version": "1.2", "chapters": [{"startTime": 0,
    "title": "...", "url": "...", "img": "..."}]}``.
    """
    if isinstance(data, str):
        data = json.loads(data)
    chapters = data.get("chapters") or []
    out: list[MediaChapter] = []
    for i, c in enumerate(chapters):
        start = _to_ms(c.get("startTime", 0))
        end = _to_ms(c.get("endTime")) if c.get("endTime") is not None else None
        out.append(
            MediaChapter(
                resource_id=resource_id,
                source_type="publisher",
                title=c.get("title", f"Chapter {i + 1}"),
                start_ms=start,
                end_ms=end,
                url=c.get("url", ""),
                image_ref=c.get("img", ""),
                publisher_id=str(c.get("startTime", "")),
            )
        )
    return out


def parse_id3_chapters(frames: list[dict[str, Any]], resource_id: str) -> list[MediaChapter]:
    """Parse ID3v2 CHAP/CTOC frames (PRD 11.2, ref 42.3).

    ``frames`` is a list of dicts with keys ``element_id``, ``start_ms``,
    ``end_ms``, ``title`` (from a TIT2 sub-frame, already flattened by the
    tag reader). CTOC frames define ordering; CHAP frames define the
    segments. We keep CHAP frames and order by start time.
    """
    chap = [f for f in frames if f.get("kind") == "CHAP" or "start_ms" in f]
    out: list[MediaChapter] = []
    for i, f in enumerate(chap):
        out.append(
            MediaChapter(
                resource_id=resource_id,
                source_type="publisher",
                title=f.get("title") or f.get("element_id") or f"Chapter {i + 1}",
                start_ms=int(f.get("start_ms", 0)),
                end_ms=int(f["end_ms"]) if f.get("end_ms") is not None else None,
                url=f.get("url", ""),
                publisher_id=f.get("element_id", ""),
            )
        )
    out.sort(key=lambda c: c.start_ms)
    return out


def merge_chapters(*sources: list[MediaChapter]) -> list[MediaChapter]:
    """Merge multiple chapter sources, publisher first, then personal/suggested.

    Publisher chapters win on overlap; personal chapters are kept and labeled
    so they never alter the publisher's original media (PRD 11.3).
    """
    by_start: dict[int, MediaChapter] = {}
    for src in sources:
        for ch in src:
            key = ch.start_ms
            existing = by_start.get(key)
            if existing is None:
                by_start[key] = ch
            elif _priority(ch) < _priority(existing):
                by_start[key] = ch
    return sorted(by_start.values(), key=lambda c: c.start_ms)


def _priority(ch: MediaChapter) -> int:
    order = {"publisher": 0, "provider": 1, "shared": 2, "suggested": 3, "personal": 4}
    return order.get(ch.source_type, 5)


def _to_ms(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value * 1000)
    if isinstance(value, str):
        return _parse_ts(value)
    return 0


def _parse_ts(ts: str) -> int:
    """Parse ``HH:MM:SS`` or ``MM:SS`` or seconds into milliseconds."""
    ts = ts.strip()
    if ":" in ts:
        parts = ts.split(":")
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            h, m, s = parts
        else:
            h, m, s = 0, parts[0], parts[1]
        return int((h * 3600 + m * 60 + s) * 1000)
    return int(float(ts) * 1000)


def fmt_time(ms: int) -> str:
    """Human-friendly ``H:MM:SS`` or ``M:SS`` for screen-reader announcement."""
    s = ms // 1000
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def normalize_radio_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Pull a stable radio metadata blob from ICY/StreamInfo-style data (PRD 12.2)."""
    return {
        "station_name": raw.get("station_name") or raw.get("icy-name") or "",
        "stream_url": raw.get("stream_url") or raw.get("url") or "",
        "homepage": raw.get("homepage") or "",
        "format": raw.get("format") or raw.get("content_type") or "",
        "bitrate": raw.get("bitrate") or "",
        "now_playing": raw.get("now_playing") or raw.get("icy-title") or "",
        "language": raw.get("language") or "",
        "country": raw.get("country") or "",
        "logo": raw.get("logo") or "",
        "last_validated": raw.get("last_validated") or 0,
    }
