"""The Radio main window's controls, pinned so they cannot drift back.

The window is a favorites list you play from, not a player. `player_panel.py`
already argues the position -- "an always-open player is mostly furniture" --
and the main window was the always-open player it was arguing about.

Pinned as source rather than by building the frame: constructing the real one
needs a controller, a recorder, a scheduler and a task manager, and what is
being defended here is the *shape of the surface*, which source states exactly.
"""

from __future__ import annotations

from pathlib import Path

_APPS = Path(__file__).resolve().parents[3] / "quill" / "apps"
_RADIO = _APPS / "radio.py"
_READOUT = _APPS / "radio_now_playing.py"


def _source() -> str:
    return _RADIO.read_text(encoding="utf-8")


def _compose_body() -> str:
    """The body of ``radio_now_playing.compose``, docstring stripped.

    The docstring explains *why* elapsed time is absent, so a naive substring
    search over the whole function would find the word it is asserting against.
    """
    source = _READOUT.read_text(encoding="utf-8")
    fn = source[source.index("def compose(host: Any) -> str:") :]
    fn = fn[: fn.index("\ndef refresh")]
    after_open = fn.index('"""') + 3
    return fn[fn.index('"""', after_open) + 3 :]


# -- Mute ----------------------------------------------------------------------


def test_the_main_window_has_a_mute_toggle_like_the_browse_window() -> None:
    """Browse has had one since it was built; the main window never did.

    So the same listener met two different answers to "how do I mute this?"
    depending on which window they happened to be standing in.
    """
    source = _source()
    assert "self._mute_btn = wx.ToggleButton(" in source
    assert '"&Mute"' in source


def test_the_mute_toggle_follows_the_state_rather_than_only_setting_it() -> None:
    """Ctrl+M and the Audio menu mute too. A toggle that only ever sends and
    never receives ends up showing the opposite of the truth."""
    assert "mute_btn.SetValue(muted)" in _source()


# -- The now-playing readout ---------------------------------------------------


def test_the_now_playing_line_is_readable_not_static_text() -> None:
    """A wx.StaticText cannot take focus.

    So it cannot be arrowed through, reviewed word by word, or copied -- and it
    carries exactly the text somebody most wants to go back over slowly: the
    station, the track, and what the player is doing.
    """
    source = _source()
    assert "self._now_playing_text = wx.TextCtrl(" in source
    assert "wx.TE_READONLY" in source
    assert "wx.TE_MULTILINE" in source


def test_the_now_playing_field_never_captures_tab() -> None:
    """A multiline TextCtrl with TE_PROCESS_TAB is a trap: Tab types into it
    instead of moving on, and the only way out is a mouse."""
    assert "wx.TE_PROCESS_TAB" not in _source()


def test_the_field_is_not_rewritten_while_it_has_focus() -> None:
    """Rewriting a field somebody is reading moves the text out from under them.

    A read-only field re-set on a timer also re-announces itself under a screen
    reader. Two guards: an equality check, and a pending slot applied on blur.
    """
    readout = _READOUT.read_text(encoding="utf-8")
    assert "_pending_now_playing" in readout
    assert "FindFocus()" in readout


def test_the_readout_omits_lines_rather_than_filling_them_with_placeholders() -> None:
    """A station with no track metadata shows two lines, not a line reading
    "no track information". An absent fact is quieter than a stated absence."""
    body = _compose_body()
    assert "if track" in body, "the track line must be guarded by having a track"
    assert "no track information" not in body
    assert "not available" not in body
    assert "unknown" not in body.lower()


def test_elapsed_time_is_deliberately_absent_from_the_readout() -> None:
    """It changes every second, so it would either re-announce constantly or
    have to be exempted from the change check that makes the rest of this safe.
    Ctrl+Shift+W answers it on demand."""
    body = _compose_body()
    for forbidden in ("position", "elapsed", "duration"):
        assert forbidden not in body.lower(), f"{forbidden} must not be in the readout"


# -- saving the station that is playing -----------------------------------------


def test_saving_the_playing_station_has_a_menu_home_and_a_key() -> None:
    """It lived only on a button, so removing the button would have removed the
    capability entirely -- there was no menu item and no key.

    It also cannot simply move into the favorites tree's context menu: the
    station it acts on is very often one you found in Browse, which is exactly
    the station that is *not* in the tree.
    """
    from quill.core.app_keymaps import APP_KEYMAPS

    assert APP_KEYMAPS["radio"]["radio.toggle_playing_favorite"] == "Ctrl+Shift+F"
    source = _source()
    assert "Add Playing Station to &Favorites" in source
    assert "_fav_toggle_menu_id" in source


def test_the_menu_item_flips_its_label_and_refuses_with_nothing_playing() -> None:
    toggle = (_APPS / "radio_favorite_toggle.py").read_text(encoding="utf-8")
    assert '("Remove", "from") if saved else ("Add", "to")' in toggle
    assert "item.Enable(playing)" in toggle


def test_every_door_onto_saving_a_station_reads_the_same_two_facts() -> None:
    """Three surfaces, one rule: they say the same thing at the same time,
    because they all read ``state_of`` rather than asking separately."""
    toggle = (_APPS / "radio_favorite_toggle.py").read_text(encoding="utf-8")
    assert "def state_of(host: Any) -> tuple[bool, bool]:" in toggle
    assert "playing, saved = state_of(host)" in toggle


def test_the_main_window_is_a_list_you_play_from() -> None:
    """The five buttons are gone; every handler behind them stays, because the
    menus, the keys and the player panel still call them."""
    source = _source()
    assert "self._play_stop_btn" not in source
    assert "self._favorite_toggle_btn = wx.Button" not in source
    assert "self._record_btn" not in source
    assert "radio_chapter_buttons.build(" not in source
    assert 'wx.Button(panel, label="&Browse Stations...")' not in source
    # The handlers survive: menus, keys and the panel still reach them.
    assert "def _on_play_stop_button" in source
    assert "def _on_favorite_toggle" in source
    assert "def _on_capture_button" in source
    # What the window keeps.
    assert "self._now_playing_text = wx.TextCtrl(" in source
    assert "self._favorites_tree = wx.TreeCtrl(" in source
    assert "self._mute_btn = wx.ToggleButton(" in source
    assert "self._volume_slider = wx.Slider(" in source


def test_the_player_panel_offers_the_same_action_through_one_handler() -> None:
    """Two doors, one handler -- the panel must not grow its own opinion about
    what saving a station means."""
    panel = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio" / "player_panel.py"
    ).read_text(encoding="utf-8")
    assert "_on_favorite_toggle" in panel
    assert "def _refresh_favorite_button" in panel
    assert "button.Enable(station is not None)" in panel
