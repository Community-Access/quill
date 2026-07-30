"""Process-wide registry of Quillin-supplied weather alert sources.

A Quillin running in Quill Weather may contribute a ``weather.alerts`` source
that returns extra active alerts (a regional feed, a bundled community advisory).
:class:`~quill.core.quillins.app_host.QuillinAppHost` populates this registry
from every enabled source contribution, and
:func:`quill.core.weather.headless_check.run_check` (and the live in-app watch)
merges the contributed alerts with the built-in NWS feed.

The registry is deliberately tiny and wx-free: a source is a callable
``() -> list[dict]`` returning alert rows (``{"id", "event", ...}``). The handler
makes no network call of its own -- it returns rows from its own storage or a
static list -- so consulting the registry never introduces a new egress site.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.weather.models import WeatherAlert

#: A source callable returning alert rows. Each row is a mapping with at least
#: ``id`` and ``event``; other :class:`WeatherAlert` fields are optional.
AlertSource = Callable[[], list[dict[str, str]]]


@dataclass(frozen=True, slots=True)
class AlertSourceEntry:
    """A registered alert source and its suggested poll cadence."""

    source_id: str
    handler: AlertSource
    interval_seconds: int = 300


_sources: list[AlertSourceEntry] = []

#: The :class:`WeatherAlert` fields a contributed row may populate (id/event are
#: required; the rest default to "").
_ALERT_STR_FIELDS = (
    "severity",
    "urgency",
    "certainty",
    "headline",
    "description",
    "instruction",
    "area_description",
    "effective",
    "onset",
    "expires",
    "ends",
    "sender_name",
)


def register_source(source_id: str, handler: AlertSource, interval_seconds: int = 300) -> None:
    """Register (or replace, by id) an alert source."""

    clear_source(source_id)
    _sources.append(AlertSourceEntry(source_id, handler, interval_seconds))


def clear_source(source_id: str) -> None:
    """Remove the source with ``source_id`` if present."""

    _sources[:] = [s for s in _sources if s.source_id != source_id]


def clear_sources() -> None:
    """Forget every registered source (a full host reload starts here)."""

    _sources.clear()


def registered_source_ids() -> tuple[str, ...]:
    """The ids of every currently registered source (for tests / diagnostics)."""

    return tuple(s.source_id for s in _sources)


def _row_to_alert(row: dict[str, str]) -> WeatherAlert | None:
    """Build a :class:`WeatherAlert` from a contributed row, or None when invalid."""

    if not isinstance(row, dict):
        return None
    alert_id = str(row.get("id", "")).strip()
    event = str(row.get("event", "")).strip()
    if not alert_id or not event:
        return None
    extra = {field: str(row.get(field, "")) for field in _ALERT_STR_FIELDS}
    return WeatherAlert(id=alert_id, event=event, **extra)


def alerts_from_sources() -> list[WeatherAlert]:
    """Return the active alerts every registered source supplies.

    Sources are consulted in registration order; a handler that raises is skipped
    so one faulty source never blocks the watch. Rows missing an ``id`` or
    ``event`` are dropped.
    """

    alerts: list[WeatherAlert] = []
    for source in _sources:
        try:
            rows = source.handler()
        except Exception:  # noqa: BLE001 - a faulty source must never break the watch
            continue
        for row in rows or ():
            alert = _row_to_alert(row)
            if alert is not None:
                alerts.append(alert)
    return alerts
