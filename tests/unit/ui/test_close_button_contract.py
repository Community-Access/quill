"""A Close button must actually close its window, in either shape.

``wx.Dialog`` answers ``ID_CANCEL`` for free, so a Close button wired to
nothing still worked -- and every surface the radio window model converted to
a modeless ``wx.Frame`` silently lost that. Browse Stations, Find Stations,
Manage Favorites and Schedule Recording all shipped a Close button that did
nothing; only Escape closed them (reported 2026-08-16).

Source-level, because constructing these surfaces needs a display and a live
host. What is pinned is the seam: any surface that builds an ``ID_CANCEL``
button and can run modeless must route it through ``bind_close_button``.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RADIO_UI = REPO / "quill" / "ui" / "radio"


def _surfaces_with_a_cancel_button() -> list[Path]:
    found = []
    for path in sorted(RADIO_UI.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "wx.ID_CANCEL, " in source and "_modeless" in source:
            found.append(path)
    return found


def test_the_seam_exists() -> None:
    from quill.ui.dialog_contract import bind_close_button

    assert callable(bind_close_button)


def test_every_modeless_capable_surface_binds_its_close_button() -> None:
    surfaces = _surfaces_with_a_cancel_button()
    assert surfaces, "expected to find the radio surfaces that carry a Close button"
    unbound = [
        path.name
        for path in surfaces
        if "bind_close_button(" not in path.read_text(encoding="utf-8")
    ]
    assert unbound == [], (
        "these surfaces build a Close button that does nothing when modeless: " + ", ".join(unbound)
    )
