"""GATE-DOCMENU for Quill Radio: what the changelog and guide promise is in the menus.

Quill Radio is released, so its documents are read by people with the running
app open beside them. Every menu path the user-facing changelog and the user
guide write (``Playback > Lineups...``) and every command they name beside a
chord (``**Chapters...** (Ctrl+Shift+C)``) must be on a menu bar a new install
actually shows. The reader is shared (``menu_claims.py``); this file supplies
Radio's menus.

**Which menus.** The main window's bar, plus the two peer windows the guide
teaches menu by menu -- Local Media (Ctrl+O) and Lineups (Ctrl+U) -- each built
in memory and never shown, on a fresh profile, as a public build (no
``QUILL_DEV_BUILD``) would build them. Their items are pooled: a path written
for the Local Media window resolves against Local Media's ``Edit`` menu, and a
claim is a finding only when no window has it. That pooling is the one
weakness to know about: ``Edit > Cut`` written about the main window would pass,
because Local Media has it.

**Not machine-global.** Building ``RadioAppFrame`` registers its system-wide
hotkeys, so ``RegisterHotKey`` is replaced on ``wx.Frame`` for the build: this
test never touches the desktop's hotkey table, and so never takes a key from a
copy of Quill Radio the developer is running.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from tests.unit.docs.menu_claims import (  # noqa: E402
    ROOT,
    MenuItem,
    OptIn,
    check_documents,
    items_from_wx_menu_bar,
)

DOCS = ROOT / "standalone" / "radio" / "docs"
DOCUMENTS = [DOCS / "CHANGELOG.md", DOCS / "userguide.md"]

#: A finding allowed, and why. Each must still match something (asserted below).
ALLOW: dict[str, str] = {
    # History: the changelog records what a release shipped under the name it
    # had then. 3.0.1's "Get became Repair" entry is the record of the rename.
    "path:help > get ffmpeg": "3.0.1 records the rename to Help > Repair FFmpeg...",
    "path:station > update youtube": (
        "the same 3.0.1 rename entry; the old title wraps onto the next line there"
    ),
    "path:station > update youtube support": (
        "the 3.0.0 name of Station > Repair YouTube Support..., renamed in 3.0.1"
    ),
}

#: The documents spell some punctuation keys out ("Ctrl+Shift+period"); the
#: menus show the character ("Ctrl+Shift+."). Same key, same command.
SPELLED_KEYS: dict[str, str] = {
    "Ctrl+Shift+period": "Next Chapter",
    "Ctrl+Shift+comma": "Previous Chapter",
    "Ctrl+comma": "Preferences",
}


@pytest.fixture
def radio_menus(quill_data_dir, monkeypatch) -> Iterator[tuple[list[MenuItem], OptIn]]:
    """Every menu row a new install shows in the three windows the guide teaches,
    and the main bar once there are favorites (Play Favorite Station... is
    appended only then, and the guide says "once you have favorites")."""
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    monkeypatch.setattr(wx.Frame, "RegisterHotKey", lambda _self, *_a: False, raising=False)
    monkeypatch.setattr(wx.Frame, "UnregisterHotKey", lambda _self, *_a: True, raising=False)
    app = wx.App()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy
    from quill.ui.lineups.window import LineupsWindow
    from quill.ui.radio.lineups_host import RadioLineupsHost
    from quill.ui.radio.local_media_window import LocalMediaWindow

    frame = RadioAppFrame()
    windows = []
    try:
        items = items_from_wx_menu_bar(frame.frame.GetMenuBar())
        local_media = LocalMediaWindow(None, host=frame, windows=frame._windows)
        windows.append(local_media._win)
        items += items_from_wx_menu_bar(local_media._win.GetMenuBar())
        lineups = LineupsWindow(RadioLineupsHost(frame))
        windows.append(lineups._win)
        items += items_from_wx_menu_bar(lineups._win.GetMenuBar())
        from quill.core.radio.models import RadioStation

        station = RadioStation(name="Gate Station", stream_url="http://example.invalid/1")
        frame._radio_favorites.add(station, folder="")
        frame._build_menu_bar()
        with_favorites = OptIn(
            items_from_wx_menu_bar(frame.frame.GetMenuBar()),
            ("once you have favorites",),
        )
        yield items, with_favorites
    finally:
        for window in windows:
            window.Destroy()
        frame._radio_shutdown()
        set_transition_announcement_policy(None)
        del app


def test_every_documented_menu_claim_is_on_a_new_install_menu(radio_menus) -> None:
    items, with_favorites = radio_menus
    findings, used = check_documents(
        DOCUMENTS, items, ALLOW, extra_keys=SPELLED_KEYS, opt_in=[with_favorites]
    )
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"allowlist entries that match nothing: {set(ALLOW) - used}"


def test_the_gate_catches_a_path_that_is_not_there(radio_menus, tmp_path: Path) -> None:
    fake = tmp_path / "fake.md"
    fake.write_text(
        "Press **Ctrl+L** (**Station > Play Last Station**).\n"
        "Choose **Station > Frobnicate Everything...** to begin.\n"
        "- **Polish the Antenna...** (Ctrl+Alt+Shift+F12): not a command.\n",
        encoding="utf-8",
    )
    findings, _used = check_documents([fake], radio_menus[0], {})
    assert len(findings) == 2, findings
    assert "station > frobnicate everything" in findings[0]
    assert "Polish the Antenna" in findings[1]
