"""Saving and loading the alert choices (``weather_alert_choices.json``). Split
from ``alert_rules`` (GATE-11); wx-free. Tolerant on read: anything unreadable
falls back to the safe default for that part (everything, Extreme always told),
and a damaged file is kept aside."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from quill.core.weather.alert_rules import (
    CATEGORIES,
    KINDS,
    PRESETS,
    SEVERITIES,
    AlertChoices,
    Clause,
    Delivery,
    QuietHours,
    RuleSet,
    Selection,
    valid_clock,
)

logger = logging.getLogger(__name__)

_STORE_NAME = "weather_alert_choices.json"
_SCHEMA = 1


def _clause_to_json(c: Clause) -> dict[str, Any]:
    return {
        "categories": c.categories,
        "events": c.events,
        "skip_events": c.skip_events,
        "kinds": c.kinds,
        "severities": c.severities,
    }


def _clause_from_json(raw: Any) -> Clause:
    if not isinstance(raw, dict):
        return Clause()

    def names(key: str, allowed: tuple[str, ...] | None = None) -> list[str]:
        value = raw.get(key)
        if not isinstance(value, list):
            return []
        out = [str(x)[:80] for x in value if isinstance(x, str)][:200]
        return [x for x in out if allowed is None or x in allowed]

    return Clause(
        categories=names("categories", CATEGORIES),
        events=names("events"),
        skip_events=names("skip_events"),
        kinds=names("kinds", KINDS),
        severities=names("severities", SEVERITIES),
    )


def _ruleset_to_json(r: RuleSet) -> dict[str, Any]:
    return {
        "preset": r.selection.preset,
        "custom": _clause_to_json(r.selection.custom),
        "delivery": r.delivery.value,
    }


def _ruleset_from_json(raw: Any) -> RuleSet:
    if not isinstance(raw, dict):
        return RuleSet()
    preset = raw.get("preset")
    try:
        delivery = Delivery(raw.get("delivery", "auto"))
    except ValueError:
        delivery = Delivery.AUTO
    return RuleSet(
        Selection(
            preset if preset in PRESETS else "everything", _clause_from_json(raw.get("custom"))
        ),
        delivery,
    )


def to_json(choices: AlertChoices) -> dict[str, Any]:
    return {
        "version": _SCHEMA,
        "general": _ruleset_to_json(choices.general),
        "places": {pid: _ruleset_to_json(r) for pid, r in list(choices.places.items())[:100]},
        "quiet": {
            "enabled": choices.quiet.enabled,
            "start": choices.quiet.start,
            "end": choices.quiet.end,
            "extreme_breaks_through": choices.quiet.extreme_breaks_through,
        },
        "extreme_always": choices.extreme_always,
        "sounds": {s: p for s, p in choices.sounds.items() if s in SEVERITIES and p},
    }


def from_json(raw: Any) -> AlertChoices:
    """Tolerant: anything unreadable falls back to the default for that part,
    and the defaults are the safe ones (everything, Extreme always told)."""
    if not isinstance(raw, dict):
        raise ValueError("alert choices file is not an object")
    choices = AlertChoices(general=_ruleset_from_json(raw.get("general")))
    places = raw.get("places")
    if isinstance(places, dict):
        for pid, value in list(places.items())[:100]:
            if isinstance(pid, str):
                choices.places[pid] = _ruleset_from_json(value)
    quiet = raw.get("quiet")
    if isinstance(quiet, dict):
        start, end = str(quiet.get("start", "22:00")), str(quiet.get("end", "07:00"))
        choices.quiet = QuietHours(
            enabled=quiet.get("enabled") is True,
            start=start if valid_clock(start) else "22:00",
            end=end if valid_clock(end) else "07:00",
            extreme_breaks_through=quiet.get("extreme_breaks_through") is not False,
        )
    choices.extreme_always = raw.get("extreme_always") is not False
    sounds = raw.get("sounds")
    if isinstance(sounds, dict):
        choices.sounds = {
            s: str(p)[:520] for s, p in sounds.items() if s in SEVERITIES and isinstance(p, str)
        }
    return choices


def store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def load_choices(data_dir: Path) -> AlertChoices:
    """Read the saved choices; missing is the default (everything, as before). A
    damaged file is kept aside and reads as the default."""
    import json

    path = store_path(data_dir)
    if not path.exists():
        return AlertChoices()
    try:
        return from_json(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("weather alert choices are unreadable (%s); using the defaults", exc)
        try:
            from quill.core.migration_backup import backup_corrupt_file

            backup_corrupt_file("weather_alert_choices", path)
        except Exception:  # noqa: BLE001 - keeping a copy is best effort
            pass
        return AlertChoices()


def save_choices(data_dir: Path, choices: AlertChoices) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(store_path(data_dir), to_json(choices))
