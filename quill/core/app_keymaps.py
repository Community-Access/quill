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

from quill.core.family_chords import SHOW_HIDE_DEFAULTS
from quill.core.keymap import DEFAULT_KEYMAP

#: app id -> {command id: binding}.
APP_KEYMAPS: dict[str, dict[str, str]] = {
    "radio": {
        # Quick-play favorites. These were Ctrl+Alt+Shift+1..0 in
        # DEFAULT_KEYMAP until 2026-09-16, when numbered tray paste took that
        # row -- the only free three-modifier digit row in the editor, and an
        # editing verb outranks a media convenience inside a text editor
        # (bad.md rule 3, P0.1). Quill Radio has no document tabs, so the plain
        # Alt+digit row the editor spends on window.go_to_document_N is free
        # here, and it is the row the old comment in keymap.py told people to
        # rebind to anyway. QUILL reaches the same favorites through one
        # chooser, radio.play_favorite.
        "radio.play_favorite_1": "Alt+1",
        "radio.play_favorite_2": "Alt+2",
        "radio.play_favorite_3": "Alt+3",
        "radio.play_favorite_4": "Alt+4",
        "radio.play_favorite_5": "Alt+5",
        "radio.play_favorite_6": "Alt+6",
        "radio.play_favorite_7": "Alt+7",
        "radio.play_favorite_8": "Alt+8",
        "radio.play_favorite_9": "Alt+9",
        "radio.play_favorite_10": "Alt+0",
        # ...and the chooser QUILL reaches them through needs a key here too:
        # its shared default is a QUILL-key chord, which a menu label cannot
        # carry (#612), so without this the Station menu would advertise no
        # route for the row.
        "radio.play_favorite": "Alt+Shift+F",
        "radio.browse": "Ctrl+B",
        # Local Media (2026-10-03): your own music, audiobooks and video, in
        # playlists. Ctrl+O because "open a file of mine" is what Ctrl+O has
        # meant in every program, and it was free on this bar -- and inside the
        # window the same key is Add Media Files, so Ctrl+O twice gets you from
        # anywhere to the file picker.
        "radio.local_media": "Ctrl+O",
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
        # Ctrl+P toggles play/stop; this is the unconditional stop, for when you
        # want silence and do not want to think about what state the player is
        # in. Ctrl+. since 2026-09-25 -- the transport table's Stop, which every
        # other window of the app already answered to. It was Ctrl+Alt+P, which
        # no accelerator ever carried on the main window and which Station >
        # Connect to Spotify also claimed; radio_main_keys now carries it.
        "radio.stop": "Ctrl+.",
        # The keys Radio's own menus already bind, named so the Command Palette
        # and Keyboard Shortcuts show them (2026-09-25). Without these the
        # palette listed Play/Pause and Mute on QUILL leader chords
        # (Ctrl+Shift+Grave, N) that do nothing here, and the rest with no key.
        "radio.play_pause": "Ctrl+P",
        "radio.mute_toggle": "Ctrl+M",
        "radio.volume_up": "Ctrl+Up",
        "radio.volume_down": "Ctrl+Down",
        "radio.volume_boost": "Ctrl+Shift+B",
        "radio.play_last": "Ctrl+L",
        "radio.rewind": "Ctrl+Shift+Left",
        "radio.forward": "Ctrl+Shift+Right",
        "radio.jump_to_live": "Ctrl+Shift+L",
        "radio.whats_playing_details": "Ctrl+T",
        "radio.song_history": "Ctrl+Shift+H",
        "radio.statistics": "Ctrl+Shift+Q",
        "radio.sound_enhancements": "Ctrl+E",
        # A QUILL leader chord Radio cannot dispatch; the Radio entry above is
        # the same window on a real key.
        "media.sound_enhancements": "",
        "media.sleep_timer": "Ctrl+Shift+Z",
        "radio.update_catalog": "Ctrl+Alt+Shift+G",
        "radio.catalog_status": "Ctrl+Alt+Shift+S",
        "radio.browse_sources": "Ctrl+Alt+Shift+O",
        "radio.download_preferences": "Ctrl+Alt+Shift+D",
        # The transport verbs the palette lists as "Radio: ...": the keys the
        # transport table gives every window, which the main window's Playback
        # menu also carries. (Skip Back / Skip Forward are left out: on the
        # main window those keys are Rewind / Forward 30 Seconds, above.)
        "radio.transport.speed_up": "Ctrl+Shift+Up",
        "radio.transport.speed_down": "Ctrl+Shift+Down",
        "radio.transport.speed_reset": "Ctrl+Shift+0",
        "radio.transport.skip_silence": "Ctrl+Shift+9",
        "radio.transport.next_chapter": "Ctrl+Shift+.",
        "radio.transport.previous_chapter": "Ctrl+Shift+,",
        "radio.transport.chapter_list": "Ctrl+Shift+C",
        "radio.transport.announce_position": "Ctrl+Shift+W",
        "radio.transport.go_to_player": "Ctrl+Shift+G",
        # One step of undo for the destructive verbs (11.3). Radio has no
        # editor, so Ctrl+Z is free here in exactly the way it is not in QUILL.
        "app.undo_last": "Ctrl+Z",
        # Undo History (qc.md 18.12); Ctrl+Shift+Z is the Sleep Timer here.
        "app.undo_history": "Ctrl+Alt+Shift+A",
        # Recent Problems: the list a transient announcement goes into. On
        # Help, beside the other "what is going on here" surfaces.
        "app.recent_problems": "Ctrl+Alt+Shift+P",
        # qc.md F-10: the family's two result keys, the same everywhere.
        "app.repeat_last_result": "F9",
        "app.activity": "Shift+F9",
        # Notifications: what the apps have told you, kept so a toast you
        # missed is still recoverable. A function key rather than a letter
        # because every Ctrl+Alt+Shift letter is already claimed somewhere in
        # the family -- U (unread) is Search Sources and W is Restore from
        # Backup, both of which the accelerator gate named rather than
        # letting one of the pair silently never fire. Rule 9: a window you
        # visit occasionally gets *a* key, not a short one.
        "app.notifications": "Ctrl+Alt+Shift+F3",
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
        # Ask QUILL Radio and Use My ChatGPT Subscription (2026-09-29): the
        # assistant on the listener's own ChatGPT plan, with what is playing
        # attached to every question. Ctrl+Shift+8 is one of the three gaps
        # the 2026-08-25 note above left (Ctrl+Shift+6, 7, 8); the digit
        # carries no mnemonic, and Alt+C then R is how most people will reach
        # it. Alt+F5 is the account window, the same key the editors give the
        # same window, so a person who set it up in QUILL Lite finds it here.
        "radio.ask_quill_radio": "Ctrl+Shift+8",
        "radio.chatgpt_account": "Alt+F5",
        # Search YouTube... (Station) and Read Comments... (Video), 2026-10-03:
        # the last two of the three Ctrl+Shift digit gaps named above. Digits,
        # so no mnemonic is pretended; Alt+S then H and Alt+D then M are the
        # one-key-at-a-time routes.
        "radio.search_youtube": "Ctrl+Shift+6",
        "radio.youtube_comments": "Ctrl+Shift+7",
        # Video > YouTube (2026-10-03): Live Chat, YouTube Video, Skip Sponsor
        # Segments and Search YouTube with Filters. The Ctrl+Shift digit row is
        # spent, so these take the Ctrl+Alt+Shift digit row, which was wholly
        # free on this bar; 7 sits beside Read Comments' Ctrl+Shift+7 on
        # purpose -- the chat and the comments are the two conversations.
        "radio.youtube_live_chat": "Ctrl+Alt+Shift+7",
        "radio.youtube_video": "Ctrl+Alt+Shift+8",
        "radio.youtube_sponsorblock": "Ctrl+Alt+Shift+9",
        "radio.youtube_search_filters": "Ctrl+Alt+Shift+0",
    },
    # QUILL Cast had no app keymap at all until undo needed one: every other
    # Cast accelerator is either a shared default or baked into a menu label.
    "cast": {
        "app.undo_last": "Ctrl+Z",
        # Undo History (qc.md 18.12). Not Radio's chord: Ctrl+Alt+Shift+H is Cast's
        # Global Hotkeys, and Ctrl+Shift+Z is Radio's Sleep Timer.
        "app.undo_history": "Ctrl+Shift+Z",
        # The same key Quill Radio's Go to Position uses, so "jump to the bit
        # forty minutes in" is one keystroke in both players (11.8).
        "podcasts.go_to_position": "Ctrl+Alt+J",
        # Mark as Played and Next (ear.md R3): Next in Queue's Ctrl+Alt+Down with
        # Shift added, so the two "and on to the next" keys sit together. It was
        # Ctrl+Alt+Shift+Q until 2026-10-04, which is QUILL's system-wide
        # show/hide key, so it never fired while QUILL ran. A Cast command, so
        # its key lives here and not in the editor's table (family rule 7);
        # QUILL Lite's Next Section on the same chord is no clash, because
        # neither key is system-wide and the two never share a window.
        "podcasts.mark_played_and_next": "Ctrl+Alt+Shift+Down",
        # Now Playing (qc.md 5): window 2, so Ctrl+2 reaches it through the
        # Window menu; this is the Episode menu row's own chord.
        "podcasts.now_playing": "Ctrl+Alt+2",
        # The Now Playing line's key: what is playing, how far in, the speed.
        "podcasts.say_now_playing": "Ctrl+T",
        # Quill Radio's Skip Silence key, for the same verb (family rule 2).
        "podcasts.skip_silence": "Ctrl+Shift+9",
        # Player Information, which had no key or menu row in Cast (qc.md C2-03).
        "podcasts.player_information": "Ctrl+I",
        # qc.md section 18 item 3: how much is left, on one key.
        "podcasts.time_remaining": "Ctrl+Shift+T",
        # Bookmarks for one episode (qc.md 18.1): J beside Help > Bookmarks' Ctrl+Alt+Shift+J.
        "podcasts.bookmark_note": "Ctrl+Shift+D",
        "podcasts.episode_bookmarks": "Ctrl+Shift+J",
        # The shared hosted AI (ear.md A1): the family's chords, all free in
        # Cast except Privacy Agreement's Ctrl+Alt+Shift+K (Keyboard Shortcuts
        # Sheet), which takes Alt+Shift+F2, beside the own key on Alt+F2.
        "tools.hosted_ai_assistant": "Ctrl+Alt+G",
        "tools.hosted_ai_ask_document": "Ctrl+Alt+Z",
        "tools.hosted_ai_image": "Ctrl+F5",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_sign_in": "Ctrl+Alt+Shift+F4",
        "tools.hosted_ai_privacy": "Alt+Shift+F2",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "app.recent_problems": "Ctrl+Alt+Shift+P",
        # qc.md F-10: the family's two result keys, the same everywhere.
        "app.repeat_last_result": "F9",
        "app.activity": "Shift+F9",
        # Notifications: what the apps have told you, kept so a toast you
        # missed is still recoverable. A function key rather than a letter
        # because every Ctrl+Alt+Shift letter is already claimed somewhere in
        # the family -- U (unread) is Search Sources and W is Restore from
        # Backup, both of which the accelerator gate named rather than
        # letting one of the pair silently never fire. Rule 9: a window you
        # visit occasionally gets *a* key, not a short one.
        "app.notifications": "Ctrl+Alt+Shift+F3",
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
        #
        # Restore was Ctrl+Alt+Shift+R until 2026-10-05: Quill Radio's
        # system-wide show/hide key, so with Radio running it never reached
        # Cast. Ctrl+Alt+F12 is Restore Settings in both editors -- the same
        # verb on the same key across the family (rule 2) -- and a once-a-year
        # command belongs on an F-key past F9 (rule 9).
        "app.backup": "Ctrl+Alt+Shift+B",
        "app.restore": "Ctrl+Alt+F12",
        # The guided lessons, on the family key: Ctrl+Alt+F1 opens the tutorials
        # in Quill Radio, Quill Weather and QUILL too. This bar had no F-key
        # accelerator of any kind, so the whole family could be given one chord.
        "podcasts.tutorials": "Ctrl+Alt+F1",
    },
    "weather": {
        # Quill Weather drove its whole Weather menu from bound menu items and
        # had no command ids at all, so the Command Palette could not reach a
        # single weather verb and a tutorial step could not name one. These are
        # the ids, and their bindings are the keys those menu labels already
        # advertise -- the menu is unchanged; it simply has names now.
        "weather.now": "Ctrl+Shift+W",
        "weather.quick": "Ctrl+Shift+Q",
        "weather.alerts": "Ctrl+Shift+Alt+A",
        "weather.add_location": "Ctrl+Alt+Shift+L",
        "weather.settings": "Ctrl+Alt+Shift+F",
        "weather.test_alert": "Ctrl+Alt+Shift+T",
        "weather.monitor_toggle": "Ctrl+Alt+Shift+M",
        "weather.monitor_pause": "Ctrl+Alt+Shift+P",
        "weather.noaa_listen": "Ctrl+Alt+N",
        "weather.noaa_update": "Ctrl+Alt+Shift+N",
        # The guided lessons. Ctrl+Alt+F1 is the family key for them -- the same
        # chord opens the lessons in Quill Radio, QUILL Cast and QUILL -- and it
        # sits in the F1 family, which is where help lives everywhere.
        "weather.tutorials": "Ctrl+Alt+F1",
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
#:
#: **F7-F12, not F1-F3 (2026-09-09), and one per sibling.** The move to F-keys
#: landed the third launcher on top of ``power.count_occurrences``
#: (Ctrl+Alt+Shift+F3), so in QUILL the Search menu's Count Occurrences and the
#: QuillVille menu's Open Quill Inkwell claimed one key and one of them never
#: fired. The launchers move rather than Count Occurrences: an existing binding
#: outranks a newcomer's convention, and that chord is QUILL Lite's too
#: (``core/lite/commands.py``), so moving it would split a key across the two
#: products for no reason. F4-F6 were already Quill Radio's Sort Favorites
#: items, which is why the block starts at F7 -- and F7-F12 is exactly six, one
#: for every row this menu can show (``QUILLVILLE_APP_ORDER`` is seven apps and
#: an app never lists itself). Before this the tuple held three, so a QuillVille
#: menu quietly shipped rows with no key at all while the builder's comment
#: claimed the house rule was met.
#:
#: **F7-F11, and Quill Cast on F12 (2026-10-05).** F12 was the sixth positional
#: key, and Ctrl+Alt+Shift+F12 is Quill Cast's system-wide show/hide key -- so
#: in a developer build, where all six siblings are listed, the sixth row
#: (Inkwell in QUILL, Converter in Inkwell) never fired while Cast ran. Cast's
#: key stays: its users are taught it, and the sixth row only ever existed in
#: developer builds, where nobody has learned it (rule 2: the key people use
#: keeps it). Instead Cast's own row takes F12 wherever it appears
#: (:data:`SIBLING_APP_FIXED_ACCELERATORS`), which makes the key mean "Quill
#: Cast" everywhere -- it opens Cast when Cast is closed and brings it up when
#: it is running -- and the other rows count through F7-F11 without it. No
#: menu loses a key: an app never lists itself, so the longest menu without
#: Cast is five rows. (Quill Media Player is not in ``QUILLVILLE_APP_ORDER``,
#: so its developer-build menu lists all seven and its last row had no key
#: before this change as well as after.)
SIBLING_APP_ACCELERATORS: tuple[str, ...] = (
    "Ctrl+Alt+Shift+F7",
    "Ctrl+Alt+Shift+F8",
    "Ctrl+Alt+Shift+F9",
    "Ctrl+Alt+Shift+F10",
    "Ctrl+Alt+Shift+F11",
)

#: Siblings whose QuillVille row keeps one key wherever it appears instead of
#: the next positional one: the app's own system-wide show/hide key, so the
#: launcher and the hotkey are one key, not two that fight.
SIBLING_APP_FIXED_ACCELERATORS: dict[str, str] = {
    "cast": SHOW_HIDE_DEFAULTS["cast"],
}


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
