"""GATE-STUDIO-HELP: F1 help ships with every Audio Studio surface and control.

The mirror of ``test_radio_help_audit`` and ``test_cast_help_audit`` -- the
same three facts, judged against QUILL Audio Studio's own catalogue
(:mod:`quill.core.audio_studio.surface_help`, authored 2026-08-27) and its own
inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in the Studio UI whose title has no entry fails here, so a
   window cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** The Studio re-activates the
   shared engine with its own resolver at startup, after the app shell's
   generic activation.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.audio_studio import surface_help
from quill.tools import studio_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_studio_window_title_has_an_authored_purpose() -> None:
    _sites, violations = studio_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = studio_help_audit.scan()
    committed = studio_help_audit.load_snapshot()
    live = studio_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.studio_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= studio_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    studio_app = (REPO / "quill" / "apps" / "studio.py").read_text(encoding="utf-8")
    assert "context_help.activate()" in studio_app
    shim = (REPO / "quill" / "ui" / "audio_studio" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in shim


def test_the_subclassed_dialog_titles_are_answered_by_the_catalogue() -> None:
    """The scan only sees direct ``wx.Dialog(...)`` constructions; most Studio
    dialogs are subclasses whose title lives in ``super().__init__``, invisible
    to it. Pin their runtime titles here so a rename cannot silently orphan a
    purpose the gate never checked."""
    for title in (
        "QUILL Audio Studio",
        "QUILL Audio Studio (Safe Mode)",
        "QUILL Audio Studio Preferences",
        "Sleep Timer",
        "Play Queue",
        "Chapter Workbench",
        "Propose chapters from silences",
        "ACX check",
        "Folder Podcast Feed",
        "Publish Audiobook",
        "Convert Audio",
        "Export a Document to Translated Speech",
        "Copy Sections -- interview.mp3",
        "Help: Chapters",
    ):
        assert surface_help.is_known_title(title), title


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert surface_help.purpose_for_title("Some Quillin Window") == surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Chapter Workbench") != surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Copy Sections -- take2.mp3").startswith("Mark pieces")
