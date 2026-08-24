"""The sheet, and the media-tools answer, are actually reachable (5.1, 5.3).

Source assertions rather than a live frame, matching the house pattern for
Cast's app-level tests: constructing the real frame needs a podcast library on
disk, and what is at stake here is wiring -- a method that exists, a menu item
that calls it, an id that survives the frame's lifetime.

That last one is not pedantry. wx frees an unreferenced ``NewIdRef``, and a
freed id is a menu item that fires nothing: the item is there, it is enabled,
it reads correctly to a screen reader, and pressing it does nothing at all.
Cast pins every menu id for exactly that reason, and a new item that forgets
to join the list is the quietest possible bug.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FRAME = (REPO / "quill" / "apps" / "podcasts.py").read_text(encoding="utf-8")
MENU = (REPO / "quill" / "apps" / "podcasts_menu.py").read_text(encoding="utf-8")
MIXIN = (REPO / "quill" / "apps" / "podcasts_help_surfaces.py").read_text(encoding="utf-8")


def test_the_frame_mixes_the_help_surfaces_in() -> None:
    assert "CastHelpSurfacesMixin" in FRAME
    assert "from quill.apps.podcasts_help_surfaces import CastHelpSurfacesMixin" in FRAME


def test_the_shortcut_sheet_has_a_menu_item_that_calls_it() -> None:
    assert "podcast_keyboard_cheat_sheet" in MENU
    assert "def podcast_keyboard_cheat_sheet" in MIXIN


def test_the_media_tools_answer_has_a_menu_item_that_calls_it() -> None:
    assert "podcast_media_tools_status" in MENU
    assert "def podcast_media_tools_status" in MIXIN


def test_both_new_items_show_the_key_they_answer_to() -> None:
    """The house rule: walking a menu to discover there is no shortcut is a
    cost a screen-reader user pays on every visit. ``_menu_label`` renders
    whatever is actually bound, so the label follows a rebinding."""
    assert '_menu_label("Keyboard Shortcuts S&heet...", "app.shortcut_sheet")' in MENU
    assert '_menu_label("&Media Tools", "app.media_tools")' in MENU


def test_the_keys_are_declared_where_the_app_keys_live() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS

    cast = APP_KEYMAPS["cast"]

    assert cast["app.shortcut_sheet"] == "Ctrl+Alt+Shift+K"
    assert cast["app.media_tools"] == "Ctrl+Alt+Shift+M"


def test_the_sheet_uses_the_same_key_in_both_apps() -> None:
    """Two sheets, one window over a different menu bar. Somebody who learned
    the key in one app has learned it in the other."""
    from quill.core.app_keymaps import APP_KEYMAPS

    radio_source = (REPO / "quill" / "apps" / "radio.py").read_text(encoding="utf-8")

    assert r"Keyboard Shortcuts S&heet...\tCtrl+Alt+Shift+K" in radio_source
    assert APP_KEYMAPS["cast"]["app.shortcut_sheet"] == "Ctrl+Alt+Shift+K"


def test_the_new_menu_ids_are_pinned_for_the_frames_lifetime() -> None:
    """wx frees an unreferenced NewIdRef, and a freed id is an accelerator and
    a menu item that fire nothing."""
    pinned = MENU[MENU.index("self._keep_menu_ids(") :]

    assert "sheet_id," in pinned
    assert "media_tools_id," in pinned


def test_the_sheet_is_radios_implementation_rather_than_a_second_one() -> None:
    """A copy is how two apps come to disagree about what a key does. The
    sheet walks the live menu bar, so it is already app-neutral."""
    assert "from quill.ui.radio.cheat_sheet_dialog import show_cheat_sheet" in MIXIN


def test_the_launch_notice_is_deferred_rather_than_run_inline() -> None:
    """A modal or an announcement at construction fights a screen reader for
    focus the app has not settled yet (#259)."""
    assert "wx.CallAfter(self.surface_cast_media_health)" in FRAME


# --- Go To (list.md 5.2) ---


def test_go_to_has_a_menu_item_that_calls_it() -> None:
    assert "open_cast_go_to" in MENU
    assert "go_to_id," in MENU[MENU.index("self._keep_menu_ids(") :]


def test_go_to_shows_its_key_and_it_is_the_one_radio_uses() -> None:
    """Ctrl+G opens the same kind of list in both apps. It was free in Cast --
    the only thing called "Go To" here jumped to a time inside an episode."""
    from quill.core.app_keymaps import APP_KEYMAPS

    assert '_menu_label("&Go To...", "app.go_to")' in MENU
    assert APP_KEYMAPS["cast"]["app.go_to"] == "Ctrl+G"


def test_every_place_in_the_catalogue_has_a_door_on_the_frame() -> None:
    """The catalogue names host methods by string -- which is what lets the
    pool grow with no migration, and also what lets a rename go unnoticed
    until somebody presses the number."""
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.apps.podcasts_go_to import unreachable_destinations

    assert unreachable_destinations(PodcastsAppFrame) == []
