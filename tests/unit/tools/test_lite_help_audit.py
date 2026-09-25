"""GATE-LITE-HELP: F1 help ships with every QUILL Lite surface and control.

The mirror of the seven sibling gates, judged against QUILL Lite's own catalogue
(:mod:`quill.core.lite_surface_help`) and its own inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in QUILL Lite whose title has no entry fails here, so a window
   cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until a
   human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** QUILL Lite activates the shared
   engine with its own resolver at startup, which is also what installs the
   ``wx.HelpProvider`` -- without that call every ``SetHelpText`` in the app
   stores nothing at all, and the whole catalogue is dead.

QUILL Lite's own wrinkle is the fourth test: its main window is titled after the
document rather than after the app, so the catalogue has to answer titles like
``"*Notes.txt - QUILL Lite (rich text)"`` that no fixed key could ever match.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import lite_surface_help
from quill.core.lite import APP_NAME
from quill.tools import lite_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_lite_window_title_has_an_authored_purpose() -> None:
    _sites, violations = lite_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = lite_help_audit.scan()
    committed = lite_help_audit.load_snapshot()
    live = lite_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.lite_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= lite_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    """The one call that makes every SetHelpText in the app live."""
    source = (REPO / "quill" / "apps" / "lite.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(lite_surface_help.purpose_for_title)" in source
    window = (REPO / "quill" / "apps" / "lite_window.py").read_text(encoding="utf-8")
    # A main window is wrapped by no show path, so F1 is bound on it directly.
    assert "app_context_help.install(self, wx=wx)" in window


def test_the_document_window_is_answered_however_it_is_titled() -> None:
    """The title carries the file name and the mode, and still resolves."""
    for title in (
        f"Untitled - {APP_NAME} (plain text)",
        f"*Notes.txt - {APP_NAME} (rich text)",
        f"report.rtf - {APP_NAME} (rich text)",
    ):
        assert lite_surface_help.is_known_title(title), title
        assert lite_surface_help.purpose_for_title(title) == lite_surface_help.PURPOSES[APP_NAME]


def test_every_fixed_window_quilllite_opens_is_answered() -> None:
    """Each literal title the app passes to a surface has a purpose."""
    for title in (
        APP_NAME,
        "Find",
        "Replace",
        "Go to line",
        "Headings",
        "Keyboard shortcuts",
        f"About {APP_NAME}",
    ):
        assert lite_surface_help.is_known_title(title), title


def test_the_generic_purpose_is_the_fallback_and_not_an_answer() -> None:
    """An unknown window still says something true -- and is never a real one."""
    generic = lite_surface_help.purpose_for_title("Some Window Nobody Wrote")
    assert generic == lite_surface_help.GENERIC_PURPOSE
    assert generic not in lite_surface_help.PURPOSES.values()
