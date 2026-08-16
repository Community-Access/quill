"""Per-app menu accelerators: the keys an app owns, apart from the editor's.

**Every menu item must show a way to reach it from the keyboard** -- the house
rule (CLAUDE.md; radio PRD A-11). Walking a menu to discover there is no
shortcut is a cost a screen-reader user pays in full, on every visit, and a
key claimed by two items means one of the pair silently never fires.

These live apart from :data:`quill.core.keymap.DEFAULT_KEYMAP` because they are
*app* keys. Quill Radio has no editor, so Ctrl+B belongs to Browse Stations
there, while in QUILL it is Bold and always will be. One shared command table
could not hold both; two tables, applied per app, can.

Applied as defaults only -- see :func:`app_keymap_overrides` -- and never
persisted: ``save_keymap`` still writes the listener's real customisations and
nothing else. wx-free, so the rule is testable without a UI.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP

#: app id -> {command id: binding}.
APP_KEYMAPS: dict[str, dict[str, str]] = {
    "radio": {
        "radio.browse": "Ctrl+B",
        "radio.add_custom_station": "Ctrl+N",
        "radio.add_youtube_playlist": "Ctrl+Shift+Y",
        "radio.find_streams": "Ctrl+Alt+S",
        "radio.manage_favorites": "Ctrl+Shift+M",
        "radio.toggle_global_volume": "Ctrl+Alt+V",
        "radio.forget_station_volumes": "Ctrl+Alt+Shift+V",
        "radio.toggle_title_announcements": "Ctrl+Alt+T",
        "radio.wake_timer": "Ctrl+Alt+Z",
        "radio.record_station": "Ctrl+Alt+R",
        "radio.stop_all_recordings": "Ctrl+Alt+X",
        "radio.schedule_recording": "Ctrl+Shift+S",
        "radio.recordings": "Ctrl+G",
        "radio.recording_settings": "Ctrl+Alt+Shift+I",
        # Record Now's shared binding is a QUILL-key chord, which a menu label
        # cannot carry (#612); the app gets a plain key of its own.
        "radio.record_toggle": "Ctrl+R",
        # Ctrl+P toggles play/stop; this is the unconditional stop, one modifier
        # away from it, for when you want silence and do not want to think about
        # what state the player is in.
        "radio.stop": "Ctrl+Alt+P",
        "adp.ask": "Ctrl+Alt+Shift+Q",
    },
}

#: The QuillVille menu's sibling launchers, numbered in menu order. Kept here
#: with the rest of the app-key data rather than inline in the menu builder.
SIBLING_APP_ACCELERATORS: tuple[str, ...] = (
    "Ctrl+Alt+Shift+1",
    "Ctrl+Alt+Shift+2",
    "Ctrl+Alt+Shift+3",
)


def app_keymap_overrides(app_id: str, keymap: dict[str, str]) -> dict[str, str]:
    """The :data:`APP_KEYMAPS` entries *app_id* should apply over *keymap*.

    An app default applies when the listener has not chosen anything (no
    binding at all) or is still on the shipped default. It never overwrites a
    real customisation.

    The shipped-default case is the one that matters: several radio commands
    default to a QUILL-key *chord*, which is right in the editor and unusable
    as a menu accelerator (wx misparses the text after the tab, #612), so
    without this the command would show no key at all in the app that owns it.
    """
    overrides: dict[str, str] = {}
    for command_id, binding in APP_KEYMAPS.get(app_id, {}).items():
        current = keymap.get(command_id)
        if not current or current == DEFAULT_KEYMAP.get(command_id):
            overrides[command_id] = binding
    return overrides
