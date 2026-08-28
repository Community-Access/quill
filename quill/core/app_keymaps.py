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
        # Bookmark This Moment is the one verb here you press *while doing
        # something else*, so it gets the shorter chord of the pair; the list
        # you go and look for takes the longer one. And the longer one is
        # Shift plus Go to Position's key on purpose: Ctrl+Alt+J goes to a
        # place you name, Ctrl+Alt+Shift+J opens the places you saved.
        "app.bookmark_moment": "Ctrl+Alt+A",
        "app.bookmarks": "Ctrl+Alt+Shift+J",
        # Pause / Resume on the Playback menu (2026-08-25). Ctrl+P is Play/Stop
        # and stays that way -- moving it would change what the key does for
        # somebody who has pressed it since 1.0 -- so pause needed a chord of
        # its own, and this bar had almost none left: Ctrl+Shift is exhausted
        # and Ctrl+Alt has one letter free. Ctrl+Space is what a media player
        # has meant by pause for as long as there have been media players, and
        # wx parses it (unlike, say, Ctrl+Shift+Plus, which it silently drops).
        "radio.pause": "Ctrl+Space",
        # The ACB Media schedule (section 6). Three keys, not one window with
        # tabs: browsing a week, asking what is on *without leaving what you
        # are doing*, and reading what you have planned are three questions.
        "radio.acb_calendar": "Ctrl+Shift+N",
        "radio.on_now": "Ctrl+Alt+H",
        "radio.upcoming": "Ctrl+Alt+Shift+F",
        # Community > ACB Media Podcasts... (2026-08-25). NOT in the
        # Ctrl+Alt+Shift family the other Community items use, because that
        # space is now completely exhausted -- no letter and no digit is free.
        # This bar claims 146 accelerators; compared canonically (wx ignores
        # modifier order) the only gaps left anywhere are a handful under Ctrl,
        # Ctrl+Shift+{O,6,7,8} and Ctrl+Alt+{I,0,8,9}. Ctrl+Shift+O is out: it
        # is the transport table's Mute, so it would mean one thing here and
        # another in every other window -- the exact split fixed on this same
        # day for Ctrl+P. The letter carries no mnemonic and pretending
        # otherwise would be worse; Alt+C then P is how anybody reaches this.
        "radio.acb_podcasts": "Ctrl+Alt+I",
        # The last two gaps on this bar (see the note above): after these,
        # Ctrl+Alt has only digits left and a new menu item will need a
        # rethink rather than a chord hunt.
        "radio.community_picks": "Ctrl+Alt+0",
        "radio.suggest_pick": "Ctrl+Alt+9",
        # ...and a fourth: go and re-read ACB's feed, now.
        #
        # F5, and F5 is not a compromise. Every Ctrl+Alt+Shift letter on this
        # menu bar is claimed (Ctrl+Alt+Shift+C is Choose Columns, which is how
        # the accelerator gate caught the first attempt at this), and the two
        # letters left anywhere -- Ctrl+Alt+I, Ctrl+Shift+O -- mean nothing.
        # F5 has meant "fetch that again" for thirty years, it was completely
        # unused in Quill Radio, and it is one key rather than four: the whole
        # complaint was that re-reading the schedule took too much finding.
        "radio.refresh_calendar": "F5",
        # The guided tutorials, in the F1 family: F1 answers about the control
        # you are on, Ctrl+F1 opens the book, and this opens the lessons. It
        # took Ctrl+Alt+F1 from Product Requirements (now Alt+Shift+F1) on the
        # family's own rule -- the doors are ordered by how often somebody
        # reaches for them, and a new listener reaches for a tutorial far more
        # often than anybody reaches for the PRD.
        "radio.tutorials": "Ctrl+Alt+F1",
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
        # Bookmark This Moment is the one verb here you press *while doing
        # something else*, so it gets the shorter chord of the pair; the list
        # you go and look for takes the longer one. And the longer one is
        # Shift plus Go to Position's key on purpose: Ctrl+Alt+J goes to a
        # place you name, Ctrl+Alt+Shift+J opens the places you saved.
        "app.bookmark_moment": "Ctrl+Alt+A",
        "app.bookmarks": "Ctrl+Alt+Shift+J",
        # The sheet, on the key Quill Radio's sheet uses. Deliberately the same
        # in both apps: somebody who learned it in one has learned it in both,
        # and the two sheets are the same window over a different menu bar.
        "app.shortcut_sheet": "Ctrl+Alt+Shift+K",
        # What FFmpeg's absence costs, asked rather than waited for. Beside
        # the sheet because both are "tell me about this installation".
        "app.media_tools": "Ctrl+Alt+Shift+M",
        # One key to every place in the app -- Radio's Ctrl+G, and free in
        # Cast (Ctrl+G was nothing here).
        "app.go_to": "Ctrl+G",
        # A library out and a library back in. Deliberately long chords: these
        # are deliberate, once-in-a-while verbs, and Restore replaces
        # everything -- a short key beside a common one is how somebody
        # restores a six-month-old backup by accident.
        "app.backup": "Ctrl+Alt+Shift+B",
        "app.restore": "Ctrl+Alt+Shift+R",
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
