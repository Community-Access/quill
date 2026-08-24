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
        "radio.add_youtube_link": "Ctrl+Alt+N",
        "radio.import_youtube_subscriptions": "Ctrl+Alt+Shift+Y",
        "radio.find_streams": "Ctrl+Alt+S",
        "radio.manage_favorites": "Ctrl+Shift+M",
        # Saving whatever is playing. It lived only on a button until
        # 2026-08-21, so it had no key and no menu home at all. Beside
        # Ctrl+Shift+M so the favorites pair is one thing to remember;
        # Ctrl+D is Show Station Details and Ctrl+F is Search Stations, so
        # neither of the obvious mnemonics was free.
        "radio.toggle_playing_favorite": "Ctrl+Shift+F",
        "radio.toggle_global_volume": "Ctrl+Alt+V",
        "radio.forget_station_volumes": "Ctrl+Alt+Shift+V",
        "radio.toggle_title_announcements": "Ctrl+Alt+T",
        "radio.wake_timer": "Ctrl+Alt+Z",
        "radio.record_station": "Ctrl+Alt+R",
        "radio.stop_all_recordings": "Ctrl+Alt+X",
        "radio.schedule_recording": "Ctrl+Shift+S",
        # Recordings gave up Ctrl+G to Go To on 2026-08-21. It is a *place*,
        # and places are what Ctrl+G is for -- it is still on the Record menu
        # and sits in the Go To list at whatever position you put it. Ctrl+R
        # stays Record Now, which is the more frequent action and the more
        # natural mnemonic; taking it for the list would have been a downgrade.
        "radio.go_to": "Ctrl+G",
        # ...and Recordings takes Ctrl+Shift+R from Restore from Backup, a
        # once-in-a-crisis action. "Reached only through Go To" was never
        # available: every enabled menu item must advertise a keyboard route,
        # and that gate is a rule rather than a preference. It decided this.
        "radio.recordings": "Ctrl+Shift+R",
        "radio.recording_settings": "Ctrl+Alt+Shift+I",
        # Record Now's shared binding is a QUILL-key chord, which a menu label
        # cannot carry (#612); the app gets a plain key of its own.
        "radio.record_toggle": "Ctrl+R",
        # Ctrl+P toggles play/stop; this is the unconditional stop, one modifier
        # away from it, for when you want silence and do not want to think about
        # what state the player is in.
        "radio.stop": "Ctrl+Alt+P",
        "adp.ask": "Ctrl+Alt+Shift+Q",
        # One step of undo for the destructive verbs (11.3). Radio has no
        # editor, so Ctrl+Z is free here in exactly the way it is not in QUILL.
        "app.undo_last": "Ctrl+Z",
        # Recent Problems: the list a transient announcement goes into. On
        # Help, beside the other "what is going on here" surfaces.
        "app.recent_problems": "Ctrl+Alt+Shift+P",
        # Quiet Hours: the window in which the app stops speaking on its own.
        "app.quiet_hours": "Ctrl+Alt+Shift+Z",
        # Move my setup to another machine: one file out, one file in.
        "app.export_setup": "Ctrl+Alt+Shift+X",
        "app.import_setup": "Ctrl+Alt+Shift+N",
    },
    # QUILL Cast had no app keymap at all until undo needed one: every other
    # Cast accelerator is either a shared default or baked into a menu label.
    "cast": {
        "app.undo_last": "Ctrl+Z",
        # The same key Quill Radio's Go to Position uses, so "jump to the bit
        # forty minutes in" is one keystroke in both players (11.8).
        "podcasts.go_to_position": "Ctrl+Alt+J",
        "app.recent_problems": "Ctrl+Alt+Shift+P",
        "app.quiet_hours": "Ctrl+Alt+Shift+Z",
        # Move my setup to another machine: one file out, one file in.
        "app.export_setup": "Ctrl+Alt+Shift+X",
        "app.import_setup": "Ctrl+Alt+Shift+N",
    },
}

#: The QuillVille menu's sibling launchers, numbered in menu order. Kept here
#: with the rest of the app-key data rather than inline in the menu builder.
#:
#: F-keys, not digits (2026-08-17): Ctrl+Alt+Shift+1..0 belong to Quill Radio's
#: quick-play favorites (``radio.play_favorite_1..10``), and these launcher
#: rows claimed 1-3 on top of them — so in the radio app one of each pair
#: silently never fired. The conflict was invisible until the Favorites
#: submenu began advertising its real bindings and the menu-accelerator gate
#: (now walking a profile WITH favorites) caught the double claim.
SIBLING_APP_ACCELERATORS: tuple[str, ...] = (
    "Ctrl+Alt+Shift+F1",
    "Ctrl+Alt+Shift+F2",
    "Ctrl+Alt+Shift+F3",
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
