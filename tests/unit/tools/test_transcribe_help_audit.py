"""GATE-TRANSCRIBE-HELP: F1 help ships with every QUILL Transcribe surface and control.

The mirror of ``test_inkwell_help_audit`` -- the same three facts, judged
against QUILL Transcribe's catalogue (:mod:`quill.core.transcribe.surface_help`)
and its own inventory: every window title resolves to a purpose, every
helpable control is accounted for, and the wiring cannot silently disappear.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.transcribe import surface_help
from quill.tools import transcribe_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_transcribe_window_title_has_an_authored_purpose() -> None:
    _sites, violations = transcribe_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = transcribe_help_audit.scan()
    committed = transcribe_help_audit.load_snapshot()
    live = transcribe_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.transcribe_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately)."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], "These controls have no help: " + ", ".join(missing)
    assert set(committed.values()) <= transcribe_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    app = (REPO / "quill" / "apps" / "transcribe.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in app


def test_the_windows_transcribe_opens_are_answered_by_the_catalogue() -> None:
    """Shared windows live under quill/ui, outside the scan; pin their titles."""
    for title in (
        "QUILL Transcribe",
        "Set Up QUILL Transcribe",
        "Choose Model",
        "Choose Microphone",
        "Review Transcript",
        "Start and Stop Key",
        "Show and Hide Key",
        "Dictation Settings",
        "Speech Models",
        "Dictation Commands",
        "Transcribe a Recording",
        "Notifications",
        "Use OpenAI",
        "Exit QUILL Transcribe",
        "Update downloaded",
    ):
        assert surface_help.is_known_title(title), title
    assert surface_help.is_known_title("Help: Choose Model")


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert surface_help.purpose_for_title("Some Brand-New Window") == surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("QUILL Transcribe") != surface_help.GENERIC_PURPOSE
