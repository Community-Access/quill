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
    src = _read("quill/ui/main_frame_radio.py")
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
    assert '("Add to &Favorites"' in src
    # The favorite button is enabled for a not-yet-resolved row (was disabled).
    assert "self._favorite_btn.Enable(True)" in src


def test_favorites_manager_offers_remove_all() -> None:
    dialog = _read("quill/ui/radio/favorites_manager_dialog.py")
    assert '"Remove A&ll..."' in dialog
    assert "def _on_remove_all(" in dialog
    actions = _read("quill/ui/radio/favorite_actions.py")
    assert "def remove_all_favorites(" in actions
    assert "store.clear()" in actions
    # Destructive: confirmation defaults to No.
    assert "wx.NO_DEFAULT" in actions


def test_transport_button_does_not_claim_alt_s_or_alt_p() -> None:
    src = _read("quill/apps/radio.py")
    # The button label carries no "&" mnemonic (would collide with the Station /
    # Playback menu-bar mnemonics, #1208); it advertises the working Ctrl+P key.
    assert 'wx.Button(panel, label="Play")' in src
    assert 'button_label = "Stop" if stopping else "Play"' in src
    assert "(Ctrl+P)" in src
    # The Playback menu item keeps its accelerator.
    assert "Ctrl+P" in src
