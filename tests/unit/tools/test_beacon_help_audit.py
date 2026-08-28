"""GATE-BEACON-HELP: F1 help ships with every Beacon surface and control.

The mirror of ``test_radio_help_audit`` and ``test_cast_help_audit`` -- the
same facts, judged against QuillBeacon's own catalogue
(:mod:`quill.apps.beacon.surface_help`, authored 2026-08-27) and its own
inventory:

1. **Every window title resolves to a purpose.** Beacon's windows subclass
   ``wx.Frame``/``wx.Dialog`` and pass titles through ``super().__init__``,
   which the shared scanner does not resolve -- so beyond the scan (which
   guards any future direct construction), every ``title="..."`` literal in
   the Beacon UI modules is harvested here and pinned against the catalogue,
   along with the frame and f-string titles by hand.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human authors help or classifies it deliberately -- and ``missing``
   fails.
3. **The wiring cannot silently disappear.** The main frame activates the
   shared engine with Beacon's resolver and binds F1 on itself; every dialog
   binds F1 in its ``__init__`` (Beacon shows dialogs with a bare
   ``ShowModal()``, which no contract show path wraps), and so do the
   palette and the player frame.
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.apps.beacon import surface_help
from quill.tools import beacon_help_audit

REPO = Path(__file__).resolve().parents[3]
BEACON = REPO / "quill" / "apps" / "beacon"

#: The modules that construct Beacon's windows (frames and dialogs).
_WINDOW_MODULES = ("app.py", "dialogs.py", "commands.py", "player.py")


def test_every_beacon_window_title_has_an_authored_purpose() -> None:
    _sites, violations = beacon_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_every_literal_title_in_the_beacon_ui_is_in_the_catalogue() -> None:
    """The subclass-style titles the scanner cannot see, pinned by harvest.

    Every ``title="..."`` literal in the window-building modules is a window
    title (Beacon passes titles only to ``super().__init__``), so each must
    resolve to an authored purpose. A new dialog with an uncatalogued title
    fails here.
    """
    unknown: list[str] = []
    for name in _WINDOW_MODULES:
        text = (BEACON / name).read_text(encoding="utf-8")
        for title in re.findall(r'title="([^"]+)"', text):
            if not surface_help.is_known_title(title):
                unknown.append(f"{name}: {title!r}")
    assert unknown == [], "titles with no purpose in surface_help.py: " + ", ".join(unknown)


def test_the_dynamic_titles_are_answered_by_the_catalogue() -> None:
    """The frame constant and the two f-string titles resolve by hand."""
    assert surface_help.is_known_title("QuillBeacon")
    assert surface_help.is_known_title("QuillBeacon Player")
    assert surface_help.is_known_title("Trail -- Learning wx")
    assert surface_help.is_known_title("Attachments -- Some Bookmark")
    assert surface_help.is_known_title("Help: Search bookmarks")


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = beacon_help_audit.scan()
    committed = beacon_help_audit.load_snapshot()
    live = beacon_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.beacon_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= beacon_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    app = (BEACON / "app.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in app
    assert "app_context_help.install(self)" in app

    dialogs = (BEACON / "dialogs.py").read_text(encoding="utf-8")
    dialog_classes = len(re.findall(r"^class \w+\(wx\.Dialog\):", dialogs, flags=re.MULTILINE))
    bound = dialogs.count("_context_help(self)")
    assert dialog_classes > 0
    assert bound == dialog_classes, (
        f"{dialog_classes} wx.Dialog classes but {bound} _context_help(self) bindings -- "
        "a Beacon dialog is shown with a bare ShowModal(), so each __init__ "
        "must bind F1 itself"
    )

    palette = (BEACON / "commands.py").read_text(encoding="utf-8")
    assert "_install_f1(self)" in palette
    player = (BEACON / "player.py").read_text(encoding="utf-8")
    assert "_install_f1(self)" in player


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert surface_help.purpose_for_title("Some Future Window") == surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("QuillBeacon") != surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Trail -- Episode 4").startswith("Step through")
