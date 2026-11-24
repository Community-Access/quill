"""Beacon's HH:MM times of day, as milliseconds since midnight.

Moved out of :mod:`quill.apps.beacon.dialogs` (GATE-11) unchanged.
"""

from __future__ import annotations


def parse_hhmm(value: str) -> int | None:
    """Parse HH:MM (24h) to epoch-ms-of-day. Returns None if blank/invalid."""
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return (h * 3600 + m * 60) * 1000
