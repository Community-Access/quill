"""GATE-WEATHER-HELP: F1 help ships with every Weather surface and control.

The mirror of ``test_radio_help_audit`` and ``test_cast_help_audit`` -- same
three facts, judged against Quill Weather's own catalogue
(:mod:`quill.core.weather.surface_help`, authored 2026-08-27) and its own
inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in the weather UI whose title has no entry fails here, so a
   window cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** Weather re-activates the shared
   engine with its own resolver at startup, after the app shell's generic
   activation.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.weather import surface_help
from quill.tools import weather_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_weather_window_title_has_an_authored_purpose() -> None:
    _sites, violations = weather_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = weather_help_audit.scan()
    committed = weather_help_audit.load_snapshot()
    live = weather_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.weather_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= weather_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    weather_app = (REPO / "quill" / "apps" / "weather.py").read_text(encoding="utf-8")
    assert "context_help.activate()" in weather_app
    shim = (REPO / "quill" / "ui" / "weather" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in shim


def test_the_gated_titles_are_answered_by_the_catalogue() -> None:
    """Every window the weather UI constructs resolves to its authored entry."""
    for title in ("Quill Weather", "Weather Center", "Add Weather Location", "Weather Settings"):
        assert surface_help.is_known_title(title), title
        assert surface_help.purpose_for_title(title) != surface_help.GENERIC_PURPOSE, title
    assert surface_help.is_known_title("Help: Weather Center")


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert surface_help.purpose_for_title("Some Quillin Window") == surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Weather Center") != surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Help: Weather Settings").startswith(
        "This is the help window itself"
    )
