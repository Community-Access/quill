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

from quill.core.app_keymaps_ai import SMALL_APP_AI_KEYMAPS, with_agent_tasks
from quill.core.app_keymaps_radio import RADIO_KEYMAPS
from quill.core.app_keymaps_weather import WEATHER_KEYMAPS
from quill.core.family_chords import SHOW_HIDE_DEFAULTS
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.wordpress.workbench_keymaps import WORKBENCH_KEYMAPS

#: app id -> {command id: binding}.
APP_KEYMAPS: dict[str, dict[str, str]] = with_agent_tasks({
    "studio": {
        "studio.capture": "Ctrl+Alt+Shift+S",
        "studio.inspect_capture": "Ctrl+Alt+Shift+I",
        "studio.cancel_capture": "Ctrl+Alt+Shift+X",
        "studio.capture_hotkeys": "Ctrl+Alt+Shift+H",
        "studio.capture_active": "Ctrl+Alt+Shift+F5",
        "studio.capture_desktop": "Ctrl+Alt+Shift+F6",
        "studio.capture_selected": "Ctrl+Alt+Shift+F4",
        "studio.open_capture": "Ctrl+Alt+Shift+O",
        # Record a Demonstration (Studio PRD 7A.3). Not Ctrl+Alt+Shift+R, the
        # first proposal: that is Quill Radio's system-wide show/hide
        # (family_chords.SHOW_HIDE_DEFAULTS), which wins while Radio runs.
        # V for video. The rest are the PRD's proposals, free on this bar.
        "studio.record_demo": "Ctrl+Alt+Shift+V",
        "studio.record_pause": "Ctrl+Alt+Shift+P",
        "studio.record_marker": "Ctrl+Alt+Shift+B",
        "studio.record_mute": "Ctrl+Alt+Shift+U",
        "studio.record_status": "Ctrl+Alt+Shift+T",
        "studio.record_window": "Ctrl+Alt+Shift+W",
        # A second Stop and save: a screen reader's keyboard hook can swallow
        # one chord invisibly (TRAY-007).
        "studio.record_emergency_stop": "Ctrl+Alt+Shift+End",
        # Rare and destructive (family rule 9): a key, not a short one, and it
        # asks before deleting anything.
        # Not F7 to F11: those are the QuillVille launcher keys, and a launcher
        # always wins, so a command there would never fire.
        "studio.record_discard": "Ctrl+Alt+Shift+Delete",
        "studio.record_recover": "Ctrl+Alt+Shift+N",  # rule 9; L is Narrate (Studio menu)
        "studio.camera_check": "Ctrl+Alt+Shift+C",
        # MX-150 proposes Ctrl+Alt+M for the mixer; the three-modifier form
        # keeps Studio's capture keys one family.
        "studio.mixer": "Ctrl+Alt+Shift+M",
        # Y for YouTube: a picture and a sound made into one video (roadmap V3).
        "studio.picture_video": "Ctrl+Alt+Shift+Y",
        # K for asK: AI about the whole video or a stretch (roadmap A1). Not Q,
        # which is QUILL's system-wide show/hide (family_chords.SHOW_HIDE_DEFAULTS).
        "studio.ask_ai_video": "Ctrl+Alt+Shift+K",
        # J: the one letter left on this bar; a picture made by talking (roadmap V1).
        "studio.make_picture": "Ctrl+Alt+Shift+J",
        # Broadcasting (roadmap section 6): G for go live, Z for the emergency
        # mute of everything public (MX-178), E for end.
        "studio.broadcast": "Ctrl+Alt+Shift+G",
        "studio.broadcast_mute": "Ctrl+Alt+Shift+Z",
        "studio.broadcast_stop": "Ctrl+Alt+Shift+E",
        # The family's AI (codex.md Phase 3). No Window menu here, so the
        # editors' Ctrl+8, Ctrl+4 and Ctrl+6 hold, from DEFAULT_KEYMAP
        # (decision 14). Use My ChatGPT Subscription keeps its id, once keyless
        # on the Capture menu, and takes the family's Alt+F5 (rule 2). Privacy
        # Agreement takes Radio's Alt+Shift+F2: Ctrl+Alt+Shift+K is Ask AI
        # About a Video above (rule 11; app_ai_keys.APP_AI_DIVERGENCES).
        # Describe a Picture: the family's Describe key (codex.md 10B.6).
        "studio.chatgpt_account": "Alt+F5",
        "tools.hosted_ai_privacy": "Alt+Shift+F2",
        "studio.describe_picture": "Ctrl+F5",
    },
    # QUILL Transcribe's AI rows (codex.md Phase 3); its other keys are in
    # transcribe_menus.py. Ctrl+1 to Ctrl+9 are its Window menu keys, so the
    # editors' Ctrl+4, Ctrl+6 and Ctrl+8 would each be claimed twice: it takes
    # Radio's and Cast's set -- Ask Ctrl+Shift+8, Which AI Ctrl+F8, Choose
    # Your AI Ctrl+Shift+F8 (rule 2) -- and their Alt+Shift+F2 for Privacy
    # Agreement, Ctrl+Alt+Shift+K being its Command Key. Each divergence is
    # this comment and an app_ai_keys row (rule 11); the rest are the editors'.
    "transcribe": {
        "tools.hosted_ai_chat_key": "Ctrl+Shift+8",
        "tools.hosted_ai_which": "Ctrl+F8",
        "tools.hosted_ai_choose": "Ctrl+Shift+F8",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_privacy": "Alt+Shift+F2",
    },
    "radio": RADIO_KEYMAPS,
    # QUILL Cast had no app keymap at all until undo needed one: every other
    # Cast accelerator is either a shared default or baked into a menu label.
    "cast": {
        "podcasts.refresh_feed": "F5",
        "media.refresh_podcasts": "Ctrl+F5",
        "podcasts.move_to_folder": "Ctrl+Shift+V",
        "podcasts.copy_to_folder": "Ctrl+Shift+Y",
        "podcasts.new_folder": "Ctrl+Shift+E",
        "podcasts.mark_all_played": "Alt+Shift+E",
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
        # QUILL Lineups: the same window and the same chord as in Quill Radio.
        "podcasts.lineups": "Ctrl+U",
        # Edit > Dictate Here (dict.md D-16): QUILL Transcribe dictating into
        # the field you are in. The editors' Start Dictation key, for the same
        # verb (family rule 2), and free here and in Quill Radio.
        "app.dictate_here": "Ctrl+F11",
        # The Now Playing line's key: what is playing, how far in, the speed.
        "podcasts.say_now_playing": "Ctrl+T",
        # Quill Radio's Skip Silence key, for the same verb (family rule 2).
        "podcasts.skip_silence": "Ctrl+Shift+9",
        # Player Information, which had no key or menu row in Cast (qc.md C2-03).
        "podcasts.player_information": "Ctrl+I",
        # qc.md section 18 item 3: how much is left, on one key.
        "podcasts.time_remaining": "Ctrl+Shift+T",
        # Where Am I? (2026-11-27): Quill Radio's chord for the same verb (rule 2);
        # New Episodes, which had it, moved to the free Ctrl+Shift+F.
        "podcasts.where_am_i": "Ctrl+Shift+W",
        # Bookmarks for one episode (qc.md 18.1): J beside Help > Bookmarks' Ctrl+Alt+Shift+J.
        "podcasts.bookmark_note": "Ctrl+Shift+D",
        "podcasts.episode_bookmarks": "Ctrl+Shift+J",
        # The shared hosted AI (ear.md A1): the family's chords, all free in
        # Cast except Privacy Agreement's Ctrl+Alt+Shift+K (Keyboard Shortcuts
        # Sheet), which takes Alt+Shift+F2, beside the own key on Alt+F2.
        "tools.hosted_ai_assistant": "Ctrl+Alt+G",
        "tools.hosted_ai_ask_document": "Ctrl+Alt+Z",
        # Refresh All owns Ctrl+F5 in Cast; image generation is less frequent.
        "tools.hosted_ai_image": "Ctrl+Alt+F5",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_sign_in": "Ctrl+Alt+Shift+F4",
        "tools.hosted_ai_privacy": "Alt+Shift+F2",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        # Ask, Which AI Am I Using and Choose Your AI (codex.md Phase 3): Quill
        # Radio's three keys, for Radio's reason -- Ctrl+1 to Ctrl+9 are this
        # app's Window menu keys, and inside an episode list Ctrl+1 to Ctrl+9
        # also run its Quick Actions -- so the editors' Ctrl+6, Ctrl+8 and Ctrl+4
        # would each be a key one of two things silently loses. Ctrl+Shift+8 is
        # Radio's Ask key, free here (rule 2). See app_ai_keys.py (rule 11).
        "tools.hosted_ai_chat_key": "Ctrl+Shift+8",
        "tools.hosted_ai_which": "Ctrl+F8",
        "tools.hosted_ai_choose": "Ctrl+Shift+F8",
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
        # Carry My Place Between Machines... (todo 50), the row beside Back Up
        # and Restore, had no key. Set up once per computer, so rule 9: an
        # F-key past F9, two along from Restore's Ctrl+Alt+F12. Free in Cast and
        # system-wide nowhere; Radio's and Studio's own Ctrl+Alt+F10 rows live
        # in other windows, and QUILL Lite's is QUILL Lite's.
        "media.sync_places": "Ctrl+Alt+F10",
        # The guided lessons, on the family key: Ctrl+Alt+F1 opens the tutorials
        # in Quill Radio, Quill Weather and QUILL too. This bar had no F-key
        # accelerator of any kind, so the whole family could be given one chord.
        "podcasts.tutorials": "Ctrl+Alt+F1",
    },
    "weather": WEATHER_KEYMAPS,  # the rows and their reasons: app_keymaps_weather.py
    **{app: rows for app, rows in SMALL_APP_AI_KEYMAPS.items() if app != "weather"},
    **WORKBENCH_KEYMAPS,  # the GitHub and WordPress Workbench windows (PRD Part C)
})

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
#:
#: **Five keys, and no sixth (Jeff, 2026-10-16).** QUILL Transcribe joins the
#: menu on 2026-11-01, last in ``QUILLVILLE_APP_ORDER``, and that makes the
#: developer-build menus one row longer than this tuple: QUILL's lists six
#: positional siblings, the Media Player's seven. The decision is not to invent
#: a sixth launcher key. In a public build every menu shows at most five rows,
#: on Ctrl+Alt+Shift+F7 to F11 (Cast and Audio Studio are gated, and Quill Radio
#: leaves Inkwell off its own menu), so no row a listener can meet is ever
#: without a key. Only a developer build shows rows past the fifth, with no key
#: -- exactly as the Media Player's developer menu already did -- and they are
#: still reached with Alt+Q and their access letter, or a key bound to
#: ``quillville.open_<app>`` in Keyboard Shortcuts. The rest of the
#: Ctrl+Alt+Shift F-row is spoken for (F1 What Can I Do Here, F2 hosted AI
#: usage, F3 Count Occurrences, F4-F6 Radio's Sort Favorites, F12 Cast), so a
#: sixth key would be a fight somebody loses silently, for rows no public build
#: shows.
#: ``test_keymap_accelerators.py`` holds both halves: five rows at most in a
#: public build, and the keyless overflow only where a developer build lists
#: unreleased apps.
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
