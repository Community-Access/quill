"""Source-contract tests for a batch of Quill Radio favorites/UX fixes:

- #1205: adding a custom station refreshes the favorites tree immediately.
- #1210: TuneIn stations can be added to Favorites from Browse Stations
  (resolve-then-add), via context menu and the favorite button.
- #1201: the Favorites manager offers "Remove All..." with confirmation.
- #1208: the transport button no longer claims Alt+S/Alt+P mnemonics.

These wx surfaces are asserted at the source level (the house pattern) rather
than by driving real widgets."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_add_custom_station_refreshes_favorites_view() -> None:
    # Add Custom Station moved to quill/ui/radio/add_custom_station.py under
    # GATE-11 on 2026-08-24, when duplicate detection (11.6) grew it past the
    # frame's budget. The refresh it pins is unchanged.
    src = _read("quill/ui/radio/add_custom_station.py")
    # After add + save, both the tree and the toggle are refreshed (guarded for
    # embedded QUILL which has no favorites tree).
    assert '_reload_favorites_tree", None)' in src
    assert '_refresh_favorite_toggle", None)' in src


def test_a_lazily_resolved_station_can_be_favorited_from_browse() -> None:
    src = _read("quill/ui/radio/browse_tree_dialog.py")
    # One resolve-then-act path now serves both Play and Add to Favorites, for
    # every source that needs it -- this used to be two TuneIn-specific methods.
    assert "def _resolve_then(" in src
    assert "self._resolve_then(data, self._add_favorite_station)" in src
    assert "self._resolve_then(data, self._play_station)" in src
    # The button's label and enabled state moved to browse_details.py when the
    # browse window lost its duplicate player (2026-08-18); the behaviour they
    # pin -- a not-yet-resolved row can still be favorited -- did not.
    details = _read("quill/ui/radio/browse_details.py")
    assert '("Add to &Favorites"' in details
    assert "dialog._favorite_btn.Enable(True)" in details


def test_favorites_manager_offers_remove_all() -> None:
    dialog = _read("quill/ui/radio/favorites_manager_dialog.py")
    assert '"Remove A&ll..."' in dialog
    assert "def _on_remove_all(" in dialog
    actions = _read("quill/ui/radio/favorite_actions.py")
    assert "def remove_all_favorites(" in actions
    assert "store.clear()" in actions
    # Destructive: confirmation defaults to No.
    assert "wx.NO_DEFAULT" in actions


def test_no_control_on_the_main_window_claims_a_menu_bar_mnemonic() -> None:
    """#1208, outlived by the button it was written about.

    The transport button used to read "&Stop"/"&Play", claiming Alt+S and
    Alt+P -- which the Station and Playback menu-bar entries answer first, so
    pressing them opened a menu instead of stopping the radio. It was fixed by
    moving to free letters (Alt+L, Alt+T), and on 2026-08-21 the button left the
    main window entirely: the transport is Enter on a row, Ctrl+P, or the
    Playback menu.

    The rule the fix established outlives the button, so this guards the rule:
    no control built on the main panel may claim a letter the menu bar answers
    first. Menu ITEMS are unaffected -- a submenu mnemonic does not compete with
    the menu bar, only a control's does.
    """
    src = _read("quill/apps/radio.py")
    panel = src[
        src.index("root = wx.BoxSizer(wx.VERTICAL)") : src.index("def _focus_initial_control")
    ]
    for claimed in ("&S", "&P", "&V", "&R", "&A", "&H", "&Q"):
        forbidden = f'label="{claimed}'
        assert forbidden not in panel, f"a main-window control claims a menu-bar key: {claimed}"
    # The transport keeps its route, in the menu where it now lives -- which
    # since 2026-08-25 is radio_transport_menu, extracted so the Playback menu
    # could grow a Pause row without radio.py going over its GATE-11 ceiling.
    # The rule under test is "&Stop"/"&Play" stay MENU labels rather than
    # becoming control labels again, so it is checked wherever they are built.
    menu_src = _read("quill/apps/radio_transport_menu.py")
    assert 'f"&{primary.plain}' in menu_src
    assert "Ctrl+P" in menu_src
