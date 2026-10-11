"""Per-station website overrides and URL validation.

Directory results are read-only provider records. A listener's correction is
stored separately and joined back by a stable local key, so it never changes
what a provider returned or contacts a site merely to validate its address.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping
from urllib.parse import urlsplit, urlunsplit

from quill.core.radio.catalog.keys import normalize_stream_url


def station_key(station: object) -> str:
    """Stable key for a station website correction, or empty without identity."""
    source = str(getattr(station, "source", "") or "radio-browser").strip().casefold()
    station_uuid = str(getattr(station, "station_uuid", "") or "").strip().casefold()
    if station_uuid:
        identity = ["uuid", source, station_uuid]
    else:
        stream_url = normalize_stream_url(str(getattr(station, "stream_url", "") or ""))
        if not stream_url:
            return ""
        name = " ".join(str(getattr(station, "name", "") or "").split()).casefold()
        identity = ["stream", source, name, stream_url]
    encoded = json.dumps(identity, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_website(value: str) -> str | None:
    """Validate and normalize a user-entered HTTP(S) website address.

    A missing scheme defaults to HTTPS. This is syntax validation only; the
    address is not fetched or probed.
    """
    candidate = value.strip()
    if not candidate or any(character.isspace() for character in candidate):
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        _ = parsed.port  # Access validates the port syntax and range.
        host = parsed.hostname
        try:
            ipaddress.ip_address(host)
        except ValueError:
            ascii_host = host.encode("idna").decode("ascii")
            labels = ascii_host.rstrip(".").split(".")
            if any(
                not label
                or len(label) > 63
                or re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?", label) is None
                for label in labels
            ):
                return None
    except ValueError:
        return None
    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc,
        parsed.path,
        parsed.query,
        parsed.fragment,
    ))


def website_for(station: object, overrides: Mapping[str, str]) -> str:
    """Return a local correction when present, otherwise the provider website."""
    key = station_key(station)
    value = (
        overrides[key]
        if key and key in overrides
        else str(getattr(station, "homepage", "") or "").strip()
    )
    if not value:
        return ""
    return normalize_website(value) or ""


def clean_overrides(raw: object) -> dict[str, str]:
    """Read only well-formed persisted overrides; an empty value clears a site."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key or not isinstance(value, str):
            continue
        if value == "":
            result[key] = ""
            continue
        normalized = normalize_website(value)
        if normalized is not None:
            result[key] = normalized
    return result


__all__ = ["clean_overrides", "normalize_website", "station_key", "website_for"]
