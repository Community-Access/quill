"""GATE-CONVERTER-HELP: F1 help ships with every Converter surface and control.

The mirror of ``test_radio_help_audit`` and ``test_cast_help_audit`` -- same
three facts, judged against Quill Converter's own catalogue
(:mod:`quill.core.converter_surface_help`, authored 2026-08-27) and its own
inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in the Converter whose title has no entry fails here, so a
   window cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** The Converter re-activates the
   shared engine with its own resolver at startup, after the app shell's
   generic activation -- directly, since this single-file app has no
   ``quill/ui`` subpackage to hold a context_help shim.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import converter_surface_help
from quill.tools import converter_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_converter_window_title_has_an_authored_purpose() -> None:
    _sites, violations = converter_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = converter_help_audit.scan()
    committed = converter_help_audit.load_snapshot()
    live = converter_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.converter_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= converter_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    converter_app = (REPO / "quill" / "apps" / "converter.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(converter_surface_help.purpose_for_title)" in converter_app


def test_the_main_window_and_shared_surfaces_are_answered() -> None:
    """The titles the Converter actually raises resolve to authored purposes."""
    for title in ("Quill Converter", "Convert Audio", "Convert from URL"):
        assert converter_surface_help.is_known_title(title), title
    assert converter_surface_help.is_known_title("Help: Quill Converter")


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    generic = converter_surface_help.GENERIC_PURPOSE
    assert converter_surface_help.purpose_for_title("Some Quillin Window") == generic
    assert converter_surface_help.purpose_for_title("Quill Converter") != generic
    assert converter_surface_help.purpose_for_title("Convert from URL").startswith("Paste a web")
