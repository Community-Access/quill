"""GATE-CAST-HELP: F1 help ships with every Cast surface and control.

The mirror of ``test_radio_help_audit`` -- same three facts, judged against
QUILL Cast's own catalogue (:mod:`quill.core.podcasts.surface_help`, authored
2026-08-24) and its own inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in the podcast UI whose title has no entry fails here, so a
   window cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** Cast re-activates the shared
   engine with its own resolver at startup, after the app shell's generic
   activation.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts import onboarding, surface_help
from quill.tools import cast_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_cast_window_title_has_an_authored_purpose() -> None:
    _sites, violations = cast_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = cast_help_audit.scan()
    committed = cast_help_audit.load_snapshot()
    live = cast_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.cast_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= cast_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    cast_app = (REPO / "quill" / "apps" / "podcasts.py").read_text(encoding="utf-8")
    assert "context_help.activate()" in cast_app
    shim = (REPO / "quill" / "ui" / "podcasts" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in shim


def test_the_exempt_titles_are_answered_by_the_catalogue() -> None:
    """Every TITLE_EXEMPT entry claims the catalogue answers it. Prove it."""
    for title in onboarding.SCREEN_TITLES.values():
        assert surface_help.is_known_title(title), title
    assert surface_help.is_known_title("About This Episode")
    assert surface_help.is_known_title("About This Episode -- Episode 12")
    assert surface_help.is_known_title("Folder Settings")
    assert surface_help.is_known_title("Folder Settings -- News")


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert surface_help.purpose_for_title("Some Quillin Window") == surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Podcasts") != surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("My Notes -- Episode 412").startswith("Your own notes")
