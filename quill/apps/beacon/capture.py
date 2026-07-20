"""Capture: turn things in the world into Beacons (PRD section 14).

Canonicalizes URLs, recognizes file/folder/URI/podcast/radio inputs, and
builds a Resource + Location (ULD) + Beacon ready for the store. The UI layer
calls :func:`capture` with whatever context it has; this module is wx-free.

Capture is deliberately permissive: it never throws on a weird input, it
returns a Beacon with a ``health`` hint so the user can review and fix.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from quill.apps.beacon import uld
from quill.apps.beacon.model import (
    HEALTH_BROKEN,
    TYPE_FILE,
    TYPE_FOLDER,
    TYPE_PODCAST_EPISODE,
    TYPE_PODCAST_SHOW,
    TYPE_RADIO_STATION,
    TYPE_RADIO_STREAM,
    TYPE_URI,
    TYPE_WEB,
    TYPE_WEB_HEADING,
    TYPE_WEB_PASSAGE,
    Beacon,
    Resource,
)

_TRACK = re.compile(r"^(utm_|gclid|fbclid|mc_|ref|igshid|ref_src|ref_url)")


def canonicalize_url(url: str) -> str:
    """Normalize a URL: lowercase host, drop tracking params, strip fragment."""
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        # bare domain -> https
        if "." in url and " " not in url:
            url = "https://" + url
    try:
        p = urlparse(url)
    except ValueError:
        return url
    if not p.scheme or not p.netloc:
        return url
    scheme = p.scheme.lower()
    netloc = p.netloc.lower()
    # drop default ports
    if (scheme, netloc.endswith(":80")) == ("http", True):
        netloc = netloc[:-3]
    if (scheme, netloc.endswith(":443")) == ("https", True):
        netloc = netloc[:-4]
    # filter tracking params
    qs = parse_qs(p.query, keep_blank_values=True)
    cleaned = {k: v for k, v in qs.items() if not _TRACK.match(k)}
    query = urlencode(cleaned, doseq=True)
    return urlunparse((scheme, netloc, p.path or "/", "", query, ""))


def detect_type(value: str) -> str:
    """Guess a resource type from a raw string (URL, path, feed, stream)."""
    v = (value or "").strip()
    if not v:
        return TYPE_URI
    if re.match(r"^[a-z][a-z0-9+.-]*://", v, re.I):
        path = urlparse(v).path.lower()
        if v.lower().endswith(".mp3") or v.lower().endswith(".m4a") or v.lower().endswith(".opus"):
            if "feed" in v or "episode" in path:
                return TYPE_PODCAST_EPISODE
            return TYPE_PODCAST_EPISODE
        if re.search(r"\.(m3u|pls|asx|ram)(\?|$)", v, re.I):
            return TYPE_RADIO_STREAM
        if re.search(r"/(rss|feed|xml)(\?|$)", v, re.I):
            return TYPE_PODCAST_SHOW
        if ":/" in v and not v.startswith("http"):
            return TYPE_URI
        return TYPE_WEB
    # filesystem path
    if re.match(r"^[A-Za-z]:[\\/]|^[/\\]|^\.\.?[/\\]", v):
        if os.path.isdir(v):
            return TYPE_FOLDER
        if os.path.isfile(v):
            return TYPE_FILE
        return TYPE_FILE if "." in os.path.basename(v) else TYPE_FOLDER
    return TYPE_URI


def _title_from(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    path = urlparse(url).path.rstrip("/")
    name = os.path.basename(path) if path else host
    return name or host or url


def capture(
    value: str,
    *,
    title: str = "",
    note: str = "",
    tags: list[str] | None = None,
    collections: list[str] | None = None,
    favorite: bool = False,
    inbox: bool = True,
    selected_text: str = "",
    heading_path: list[str] | None = None,
    media_start_ms: int | None = None,
    media_end_ms: int | None = None,
    capture_source: str = "manual",
) -> tuple[Beacon, Resource]:
    """Build a Beacon + Resource from a raw input string and optional context.

    Returns the pair without persisting; the caller (UI or importer) hands
    them to ``BeaconStore.put_beacon``. This keeps capture testable and lets
    the importer reuse the same canonicalization.
    """
    tags = list(tags or [])
    collections = list(collections or [])
    rtype = detect_type(value)

    if rtype in (TYPE_FILE, TYPE_FOLDER):
        p = Path(value)
        res = Resource(
            type=rtype,
            canonical_id=str(p.resolve()) if p.exists() else str(p),
            title=title or p.name,
            primary_uri=value,
        )
        loc = uld.build_uld(
            resource_id=res.resource_id,
            location_type="positional",
            positional={"path": str(p)},
            display_summary=str(p),
        )
        if not p.exists():
            res.availability = HEALTH_BROKEN
        beacon = Beacon(
            title=title or p.name,
            note=note,
            favorite=favorite,
            in_inbox=inbox,
            tags=tags,
            collections=collections,
            capture_source=capture_source,
        )
        beacon.locations = [loc]
        return beacon, res

    if rtype in (TYPE_PODCAST_EPISODE, TYPE_PODCAST_SHOW, TYPE_RADIO_STATION, TYPE_RADIO_STREAM):
        canon = canonicalize_url(value) if value.startswith("http") else value
        res = Resource(
            type=rtype,
            canonical_id=canon,
            title=title or _title_from(value),
            primary_uri=value,
        )
        loc = uld.build_uld(
            resource_id=res.resource_id,
            location_type="media" if media_start_ms is not None else "native",
            media_start_ms=media_start_ms,
            media_end_ms=media_end_ms,
            text_quote=selected_text,
            display_summary=title or _title_from(value),
        )
        beacon = Beacon(
            title=title or _title_from(value),
            note=note,
            favorite=favorite,
            in_inbox=inbox,
            tags=tags,
            collections=collections,
            capture_source=capture_source,
        )
        beacon.locations = [loc]
        return beacon, res

    # Web / generic URI
    canon = canonicalize_url(value)
    res = Resource(
        type=TYPE_WEB if value.startswith("http") else TYPE_URI,
        canonical_id=canon,
        title=title or _title_from(value),
        primary_uri=value,
    )
    loc_type = "textQuote" if selected_text else ("structural" if heading_path else "native")
    loc = uld.build_uld(
        resource_id=res.resource_id,
        location_type=loc_type,
        text_quote=selected_text,
        heading_path=heading_path,
        display_summary=" > ".join(heading_path)
        if heading_path
        else (selected_text[:80] if selected_text else res.title),
    )
    if selected_text:
        res.type = TYPE_WEB_PASSAGE
    elif heading_path:
        res.type = TYPE_WEB_HEADING
    beacon = Beacon(
        title=title or res.title,
        note=note,
        favorite=favorite,
        in_inbox=inbox,
        tags=tags,
        collections=collections,
        capture_source=capture_source,
    )
    beacon.locations = [loc]
    return beacon, res


def capture_from_clipboard(text: str) -> tuple[Beacon, Resource] | None:
    """Convenience: capture the first URL or path found in clipboard text."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^(https?://|[A-Za-z]:[\\/])", line):
            return capture(line, capture_source="clipboard")
    return None
