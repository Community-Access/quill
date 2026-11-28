"""Quill Radio menu accelerators, extracted from app_keymaps under GATE-11."""

from __future__ import annotations

from quill.core.radio.dial_tuning import DIAL_KEYS
from quill.core.radio.song_marks import SONG_MARK_KEYS
from quill.core.radio.streamsift_keys import STREAMSIFT_KEYS

RADIO_KEYMAPS: dict[str, str] = {
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
    # Edit > Dictate Here (dict.md D-16): Ctrl+F11, the editors' Start Dictation key (rule 2).
    "app.dictate_here": "Ctrl+F11",
    # Video > Full Screen keeps F11 (decision 2); beside it, never a dictation key.
    "app.command_key": "Alt+F11",
    # QUILL Lineups (2026-10-13): Ctrl+U, "lineUp". Ctrl+Alt+U was the first
    # choice and is Help > Check for Updates here; Ctrl+U was one of the few
    # chords free on both this bar and Cast's, where the same command keeps
    # the same chord (family rule 2). Add to Lineup is Ctrl+Shift+U.
    "radio.lineups": "Ctrl+U",
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
    **SONG_MARK_KEYS,  # song marks and per-station length: song_marks.py
    **STREAMSIFT_KEYS,  # Play Random and the StreamSift ideas: streamsift_keys.py
    # Identify This Song (AcoustID, 2026-10-15). Not Ctrl+Alt+Shift+R,
    # which looks free on this bar only because it is Radio's own
    # system-wide show/hide key. Ctrl+K is one of the few plain Ctrl
    # letters left that no clipboard or undo habit owns.
    "radio.identify_song": "Ctrl+K",
    "radio.whats_playing_details": "Ctrl+T",
    "radio.song_history": "Ctrl+Shift+H",
    "radio.station_playlist": "Alt+Shift+H",  # the station's own list, same H
    **DIAL_KEYS,  # dial tuning on and off, and Go to Playing Station: dial_tuning.py
    # Lyrics (LRCLIB, on request only). Not the planned Ctrl+Alt+L, which is
    # Resume Last Station on Launch; B is the one Ctrl+Alt letter left.
    "radio.lyrics": "Ctrl+Alt+B",
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
    # main window those keys are Rewind / Forward, above.)
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
    # What's New (todo P3 Radio extras 8): what arrived while you were
    # away, the companion of What Is On Now (Ctrl+Alt+H). Alt+Shift+N for
    # New, the same shape as Alt+Shift+F for Play Favorite: the Ctrl+Alt
    # and Ctrl+Alt+Shift rows have no letter left on this bar.
    "radio.whats_new": "Alt+Shift+N",
    # A second output device (xradio2 4.6, 4.7): B for Background, D for
    # Device. The Alt+Shift row is where this bar still has letters.
    "radio.background_station": "Alt+Shift+B",
    "radio.mirror_output": "Alt+Shift+D",
    # Station Details (todo P2 #33, the station pack): I for information,
    # on the Alt+Shift row for the same reason as the two above.
    "radio.station_details": "Alt+Shift+I",
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
    # The family's AI (codex.md Phase 3, 2026-11-01). Ask QUILL Radio became
    # Ask, the family's one conversation window, and keeps its id and
    # Ctrl+Shift+8 (rule 5: nothing moves). The editors' Ctrl+4, Ctrl+6 and
    # Ctrl+8 cannot follow it here: Ctrl+1 to Ctrl+9 are Quill Radio's
    # Window menu keys on every window (quill/ui/window_menu.py), and a key
    # claimed twice means one of the pair silently never fires. So Which AI
    # Am I Using is Ctrl+F8 -- the 8 of the editors' key, moved to the
    # function row -- and Choose Your AI is Ctrl+Shift+F8, the same key with
    # Shift for "and open the window" (Ctrl+F8 pressed twice opens it too).
    # Both were free on this bar and on Cast's, where the same two commands
    # take the same two keys (rule 2). The divergence from the editors is
    # this comment and its row in app_ai_keys.APP_AI_DIVERGENCES (rule 11).
    "tools.hosted_ai_which": "Ctrl+F8",
    "tools.hosted_ai_choose": "Ctrl+Shift+F8",
    # The family's Usage and own-key keys, free here. Privacy Agreement
    # takes Cast's Alt+Shift+F2: the editors' Ctrl+Alt+Shift+K is this bar's
    # Keyboard Shortcuts Sheet.
    "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
    "tools.hosted_ai_own_key": "Alt+F2",
    "tools.hosted_ai_privacy": "Alt+Shift+F2",
    # Describe the Video (codex.md 10B.5): the family's Describe key, the
    # editors' Ask About an Image chord, free on this bar.
    "radio.describe_video": "Ctrl+F5",
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
}
