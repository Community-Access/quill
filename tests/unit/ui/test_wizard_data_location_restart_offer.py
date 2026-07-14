"""Source-contract test: the setup wizard offers an immediate restart when a
data-location move is queued, mirroring Preferences' existing offer.

A first-run choice to store data next to the app (or any other new location)
is deferred to the next launch the same way Preferences already handles it
(moving a data directory out from under a running process is not safe) --
but unlike Preferences, the wizard never told the user this, so the choice
looked silently ignored until a second launch. This asserts the wiring
without constructing a real wx.Dialog, matching this repo's convention for
hard-to-construct MainFrame UI paths.
"""

from __future__ import annotations

from pathlib import Path

_MAIN_FRAME = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py"


def _read_source() -> str:
    return _MAIN_FRAME.read_text(encoding="utf-8")


def test_run_startup_wizard_offers_a_restart_when_a_move_is_queued() -> None:
    src = _read_source()
    assert "from quill.core.data_location import pending_data_location_target" in src
    assert "target = pending_data_location_target()" in src
    assert "if target is not None:" in src
    assert "self._confirm_restart_for_data_location(target)" in src
