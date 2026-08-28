"""GATE-INKWELL-HELP: F1 help ships with every Inkwell surface and control.

The mirror of ``test_radio_help_audit`` and ``test_cast_help_audit`` -- the
same three facts, judged against Quill Inkwell's own catalogue
(:mod:`quill.core.inkwell_surface_help`, authored 2026-08-27) and its own
inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in ``quill/apps/inkwell.py`` whose title has no entry fails
   here, so a window cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** Inkwell has no ``quill/ui``
   subpackage, so there is no shim: the app module re-activates the shared
   engine with the catalogue's resolver directly, after the app shell's
   generic activation.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import inkwell_surface_help
from quill.tools import inkwell_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_inkwell_window_title_has_an_authored_purpose() -> None:
    _sites, violations = inkwell_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = inkwell_help_audit.scan()
    committed = inkwell_help_audit.load_snapshot()
    live = inkwell_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.inkwell_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= inkwell_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    inkwell_app = (REPO / "quill" / "apps" / "inkwell.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(inkwell_surface_help.purpose_for_title)" in inkwell_app


def test_the_dialogs_inkwell_opens_are_answered_by_the_catalogue() -> None:
    """Inkwell's dialogs live under quill/ui (shared with QUILL), outside the
    scan; pin their titles here so a rename cannot silently orphan them."""
    for title in (
        "Quill Inkwell",
        "Manage Abbreviations",
        "New Abbreviation",
        "Edit Abbreviation",
        "Quick Insert",
        "Excluded Applications",
        "Update downloaded",
    ):
        assert inkwell_surface_help.is_known_title(title), title
    assert inkwell_surface_help.is_known_title("Help: Quick Insert")


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert (
        inkwell_surface_help.purpose_for_title("Some Brand-New Window")
        == inkwell_surface_help.GENERIC_PURPOSE
    )
    assert (
        inkwell_surface_help.purpose_for_title("Quill Inkwell")
        != inkwell_surface_help.GENERIC_PURPOSE
    )
    assert inkwell_surface_help.purpose_for_title("Quick Insert").startswith("Pick an abbreviation")
