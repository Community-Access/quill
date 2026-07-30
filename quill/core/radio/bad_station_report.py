"""Compose a pre-filled "this station will not play" bug report (#1218).

A user hit a station (e.g. WAAI 100.9) that would not play and asked for a way
to report bad stations from inside the app. RadioBrowser already hides stations
its own checker believes are dead (``hidebroken=true``), so a station that plays
for the directory but fails for one listener still shows up -- the listener is
the only one who can flag it.

This module turns a :class:`~quill.core.radio.models.RadioStation` into a
``(summary, body)`` pair for the existing Report a Bug flow. It is pure and
wx-free so the wording is unit-testable; the UI wiring lives in the app shell
and the Radio frame's menus. The body carries only station metadata (never the
user's name, email, or paths), so it is safe to drop straight onto the clipboard
or into a browser issue form.
"""

from __future__ import annotations

from quill.core.radio.models import RadioStation


def build_bad_station_report(station: RadioStation) -> tuple[str, str]:
    """Return ``(summary, body)`` describing *station* as a non-playing station.

    ``summary`` is a short issue title; ``body`` is a plain-text block a user can
    submit as-is. Only fields the station actually carries are included, so a
    sparse favorite doesn't produce a wall of empty labels.
    """
    name = station.name or "Unknown station"
    summary = f"Bad station: {station.display_name}"

    lines = ["This station would not play.", "", f"Station: {station.display_name}"]
    if station.source:
        lines.append(f"Source: {station.source}")
    if station.station_uuid:
        lines.append(f"Station UUID: {station.station_uuid}")
    # The stream URL is the single most useful field for triage, so include it
    # even when blank (its absence is itself a clue that resolution failed).
    lines.append(f"Stream URL: {station.stream_url or '(none resolved)'}")
    if station.codec or station.bitrate_kbps:
        fmt = " ".join(
            part
            for part in (
                station.codec,
                f"{station.bitrate_kbps} kbps" if station.bitrate_kbps else "",
            )
            if part
        )
        lines.append(f"Format: {fmt}")
    if station.homepage:
        lines.append(f"Homepage: {station.homepage}")
    lines.append("")
    lines.append(f"Please look into why {name} will not play.")
    return summary, "\n".join(lines)
