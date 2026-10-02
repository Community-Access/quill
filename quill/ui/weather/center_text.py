"""What the Weather Center says about an alert or a forecast period.

Moved out of ``weather_center_dialog.py`` under GATE-11 (2026-10-01) when that
module gained its task-lifetime wrapper (qc.md F-02). Pure text: no wx, no
window, so every sentence is testable on its own. ``weather_center_dialog``
re-exports these names, which is how its tests reach them.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "_alert_detail_text",
    "_alert_list_label",
    "_period_detail_text",
    "_spell_out",
    "_temp_words",
]


def _alert_list_label(alert: Any) -> str:
    """One-line list entry: event, area, tier, and when it expires."""
    bits = [alert.event]
    if alert.area_description:
        bits.append(alert.area_description.split(";")[0].strip())
    bits.append(alert.tier)
    return " -- ".join(b for b in bits if b)


def _spell_out(text: str) -> str:
    """Expand the abbreviations the National Weather Service leaves in its own
    forecast prose, so a screen reader or voice speaks them in full. Only widens
    abbreviations -- it never changes the official wording's meaning."""
    import re

    text = re.sub(r"\bmph\b", "miles per hour", text)
    text = re.sub(r"\bkm/h\b", "kilometers per hour", text)
    return text


def _temp_words(period: Any) -> str:
    scale = "Fahrenheit" if period.temperature_unit == "F" else "Celsius"
    return f"{period.temperature} degrees {scale}"


def _period_detail_text(period: Any) -> str:
    """A forecast period as a self-contained, copyable, fully spoken block: the
    day name and temperature at the top, then the full detailed forecast."""
    head = f"{period.name}: {_temp_words(period)}"
    body = _spell_out(period.detailed_forecast or period.short_forecast)
    return f"{head}\n{body}" if body else head


def _alert_detail_text(alert: Any) -> str:
    """The full official alert: headline, instructions, description, timing."""
    lines = [alert.headline or alert.event]
    lines.append(
        f"Severity {alert.severity or 'Unknown'}, urgency {alert.urgency or 'Unknown'}, "
        f"certainty {alert.certainty or 'Unknown'}."
    )
    if alert.area_description:
        lines.append(f"Area: {alert.area_description}")
    if alert.effective or alert.expires:
        lines.append(f"In effect {alert.effective or '?'} to {alert.expires or '?'}.")
    if alert.instruction:
        lines.append("")
        lines.append("Instructions: " + alert.instruction)
    if alert.description:
        lines.append("")
        lines.append(alert.description)
    if alert.sender_name:
        lines.append("")
        lines.append(f"Issued by {alert.sender_name}.")
    return "\n".join(lines)
