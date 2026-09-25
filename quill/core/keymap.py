from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from pathlib import Path

from quill.core.keymap_format import (
    format_binding_for_display,
    format_quill_key_chord,
)
from quill.core.keymap_packs import (
    KEYBOARD_PACK_CUSTOM,
    KEYBOARD_PACK_DEFAULT,
    KEYBOARD_PACKS,
    KeyboardPack,
    keyboard_pack_description,
    keyboard_pack_names,
    keyboard_pack_preview,
)
from quill.core.keymap_query import (
    canonical_binding,
    commands_for_keystroke,
    diagnose_keymap,
    duplicate_bindings,
    find_keymap_conflicts,
)
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "DEFAULT_ALIASES",
    "DEFAULT_KEYMAP",
    "KEYBOARD_PACK_CUSTOM",
    "KEYBOARD_PACK_DEFAULT",
    "KEYBOARD_PACKS",
    "KeyboardPack",
    "KQP_EXTENSION",
    "build_keymap_for_pack",
    "canonical_binding",
    "commands_for_keystroke",
    "diagnose_keymap",
    "duplicate_bindings",
    "export_keyboard_pack",
    "export_keymap",
    "find_keymap_conflict",
    "find_keymap_conflicts",
    "format_binding_for_display",
    "format_quill_key_chord",
    "import_keyboard_pack",
    "import_keymap",
    "keyboard_pack_description",
    "keyboard_pack_names",
    "keyboard_pack_preview",
    "keymap_path",
    "list_keymap_profiles",
    "load_keymap",
    "load_keymap_profile",
    "merge_keymaps",
    "reset_keymap",
    "save_keymap",
]

logger = logging.getLogger(__name__)

DEFAULT_KEYMAP: dict[str, str] = {
    "file.new": "Ctrl+N",
    # #1246: Ctrl+T opens a new document tab in the current notebook window
    # (a second entry point to New; Ctrl+N stays bound to file.new).
    "window.new_document_tab": "Ctrl+T",
    # QUILL Lite's chords: a document started in the kind you meant, rather than
    # one you make and convert (bad.md P1.13, 3.7). Ctrl+Alt+N came free when
    # Numbered List folded into the Ctrl+Shift+L cycle.
    # Alt+Shift+T since 2026-09-22, because Ctrl+Shift+N is **Word's Normal
    # style** and format.clear_formatting now has it (rule 1, Microsoft's key
    # wins; rule 3, frequency breaks the tie -- Normal Text is pressed all day
    # in a rich document and this once per document).
    #
    # T for Text, and the keymap left almost no choice: four chords were free in
    # both editors and this is the only one that means anything. Ctrl+Alt+Shift+N
    # would have kept the two News a pair and is Invert Case, one of five Change
    # Case chords worth more as a family; Ctrl+Alt+R is QUILL's Trim Trailing
    # Whitespace, a divergence from QUILL Lite decided on 2026-09-16 and written
    # down. It sits beside format.switch_document_mode on Alt+Shift+F, which is
    # the neighbouring idea: that one changes what this document is, this one
    # starts a new one already being it.
    "file.new_rich_document": "Alt+Shift+T",
    "file.new_plain_text_document": "Ctrl+Alt+N",  # §edsharp-ok — QUILL Lite's chord
    "file.open": "Ctrl+O",
    "file.save": "Ctrl+S",
    "file.save_as": "Ctrl+Shift+S",
    # The leader reclaim (bad.md 5.9, P1.11): eight of its sixteen positions.
    # Nobody presses a chord to rename a repository, and what these gave up is
    # what section 3's editing-loop relocations needed. Menu and palette only.
    "file.open_from_remote": "",
    "file.save_to_remote": "",
    "file.manage_remote_sites": "",
    "file.open_github_repository": "",
    "file.open_github_file_url": "",
    "file.github_save_back": "",
    "file.github_manage_accounts": "",
    "file.open_github_items": "",
    "file.close_document": "Ctrl+W",
    "file.print": "Ctrl+P",
    # Restore points: no default key (assignable); the File menu item is the
    # primary path.
    # QUILL Lite's chord, freed by tools.ai_switch_engine vacating the AI class
    # (bad.md P1.1, P1.11). The File menu was the only way in before.
    "file.restore_previous_version": "Ctrl+Alt+Shift+E",
    # On macOS, wx's ACCEL_CTRL maps to Cmd (not the physical Control key) in
    # the accelerator table, so "Ctrl+Tab" here becomes Cmd+Tab -- macOS's own
    # reserved App Switcher shortcut, which never reaches the app. A literal
    # physical Ctrl+Tab press does not match ACCEL_CTRL on macOS either, so it
    # falls through to generic focus traversal instead of switching documents.
    # Use the conventional macOS tab-cycling chord (matching Safari/Xcode,
    # and pairing with the Cmd+[ / Cmd+] back/forward chord above) instead.
    "window.next_document": "Cmd+Shift+]" if sys.platform == "darwin" else "Ctrl+Tab",
    "window.previous_document": "Cmd+Shift+[" if sys.platform == "darwin" else "Ctrl+Shift+Tab",
    # Jump straight to the Nth open document. Alt+digit is otherwise unused and,
    # unlike Ctrl+Alt+ chords, is not screen-reader-hostile (§10.8). Alt+0 = 10th.
    "window.go_to_document_1": "Alt+1",
    "window.go_to_document_2": "Alt+2",
    "window.go_to_document_3": "Alt+3",
    "window.go_to_document_4": "Alt+4",
    "window.go_to_document_5": "Alt+5",
    "window.go_to_document_6": "Alt+6",
    "window.go_to_document_7": "Alt+7",
    "window.go_to_document_8": "Alt+8",
    "window.go_to_document_9": "Alt+9",
    "window.go_to_document_10": "Alt+0",
    "window.close_other_documents": "Ctrl+Shift+F4",
    "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
    "navigate.speak_full_path": "Ctrl+Shift+Grave, P",
    "navigate.speak_status_summary": "Ctrl+Shift+Grave, Q",
    "view.send_to_tray": "Ctrl+Shift+Grave, T",
    # support#67: bare Alt+<letter> is a macOS Option deadkey (Alt+Z would
    # steal a diacritical the user types). The pack guard
    # (_is_macos_reserved_runtime_chord) already drops bare Alt+letter on
    # darwin; apply the same policy to DEFAULT_KEYMAP -- disable on darwin
    # so Option+Z types its character. The command stays available via the
    # command palette and menu; a Mac-validated remap is the follow-up.
    "view.toggle_soft_wrap": "" if sys.platform == "darwin" else "Alt+Z",
    # Notepad's own three, and QUILL Lite's. QUILL could not change the size of
    # its own text at all before 2026-09-16 (bad.md 4.3, P0.6a).
    "view.text_size_up": "Ctrl+=",
    "view.text_size_down": "Ctrl+-",
    "view.text_size_reset": "Ctrl+0",
    "view.reveal_codes_toggle": "Alt+F3",  # WordPerfect Reveal Codes
    "view.toggle_tab_control": "Ctrl+Shift+Grave, Shift+T",
    "app.command_palette": "Ctrl+Shift+P",
    "app.preferences": "Ctrl+,",
    # #608: app.exit is bound to Ctrl+Q so it maps to Cmd+Q on macOS
    # (the conventional Quit shortcut) and Alt+F4 on Windows is also
    # wired by the wx stock accelerator on the file menu. Quote Lines
    # was moved to Ctrl+Shift+Q to free up Ctrl+Q.
    "app.exit": "Ctrl+Q",
    "navigate.go_to_line": "Ctrl+G",
    "navigate.go_to_page": "",  # the Page row of one Go To now (bad.md 5.4, P1.6)
    # Notepad's F5, and QUILL Lite's. A core command rather than the bundled
    # insert-tools Quillin's menu rows, so it has a chord and so it survives
    # Safe Mode, where Quillin contributions are off (bad.md P1.9).
    "edit.insert_date_time": "F5",
    "navigate.next_region": "F6",
    "navigate.previous_region": "Shift+F6",
    # #609: on macOS, Alt+Left / Alt+Right collide with the system-standard
    # Option+Left / Option+Right word-by-word movement (and with
    # VoiceOver's word-by-word reading). Use Cmd+[ / Cmd+] on macOS,
    # which is the conventional macOS back/forward chord.
    "navigate.back_location": "Cmd+[" if sys.platform == "darwin" else "Alt+Left",
    "navigate.forward_location": "Cmd+]" if sys.platform == "darwin" else "Alt+Right",
    "navigate.outline_navigator": "Ctrl+Shift+O",
    "navigate.match_bracket": "Ctrl+Shift+\\",
    "navigate.next_structure": "Alt+Down",
    "navigate.previous_structure": "Alt+Up",
    # Rule 6, found by the parity table (bad.md P1.15): QUILL Lite reaches the
    # heading organiser on Alt+Shift+O and QUILL had it on the leader.
    "navigate.heading_organizer": "Alt+Shift+O",
    # Word's own Bookmark key. Alt+Shift+B went to view.toggle_status_bar on
    # 2026-09-16, which is Notepad's chord for it and QUILL Lite's; this was
    # already an alias here, so the displacement cost nothing (bad.md P1.10).
    # QUILL Lite's chord as the primary, Word's as the alias below (bad.md 3.5).
    "navigate.list_bookmarks": "Alt+Shift+G",
    # Notepad's View > Status Bar, and QUILL Lite's. QUILL could hide any one
    # cell and not the bar itself (bad.md G3, P1.10).
    "view.toggle_status_bar": "Alt+Shift+B",
    # Numbered bookmarks: nine slots you address by digit, shared core
    # (quill.core.numbered_bookmarks) whose docstring says it lives there so
    # QUILL can adopt it. QUILL Lite was its only caller until 2026-09-16,
    # which is exactly the shape CLAUDE.md forbids -- the small product ahead
    # of the big one, invisibly. Same chords in both, which are the chords
    # QUILL Lite already shipped (bad.md 3.5, 5.2, P0.1).
    #
    # These are NOT navigate.set_bookmark / go_to_bookmark: those are QUILL's
    # *named* bookmark vault, which stays as the writing environment's extra.
    "navigate.set_numbered_bookmark": "Ctrl+Shift+B",
    "navigate.next_bookmark": "F2",
    "navigate.previous_bookmark": "Shift+F2",
    "navigate.clear_numbered_bookmarks": "Ctrl+Alt+B",
    "navigate.set_numbered_bookmark_1": "Ctrl+Shift+1",
    "navigate.set_numbered_bookmark_2": "Ctrl+Shift+2",
    "navigate.set_numbered_bookmark_3": "Ctrl+Shift+3",
    "navigate.set_numbered_bookmark_4": "Ctrl+Shift+4",
    "navigate.set_numbered_bookmark_5": "Ctrl+Shift+5",
    "navigate.set_numbered_bookmark_6": "Ctrl+Shift+6",
    "navigate.set_numbered_bookmark_7": "Ctrl+Shift+7",
    "navigate.set_numbered_bookmark_8": "Ctrl+Shift+8",
    "navigate.set_numbered_bookmark_9": "Ctrl+Shift+9",
    # #1317: re-registered after the historical Ctrl+Shift+K / Alt+Shift+K went
    # to Unquote Lines (#608) and Keep Unique Lines (§4.22). J = jump point.
    # Ctrl+J is Word's Justify and QUILL Lite's, so the temporary bookmark
    # takes the chord Justify vacates. Go To keeps Ctrl+Shift+J: it is the
    # pair's second half and nothing else wants it (bad.md 3.1).
    "navigate.set_temp_bookmark": "Ctrl+Alt+J",
    "navigate.go_to_temp_bookmark": "Ctrl+Shift+J",
    # support#67: bare Alt+Q is a macOS Option deadkey -- disable on darwin
    # (see view.toggle_soft_wrap above). Reachable via the command palette.
    "tools.ask_quill_chat": "" if sys.platform == "darwin" else "Alt+Q",
    # The hosted AI -- QUILL's own free service, which is what the AI menu now
    # opens with. Every chord here is **QUILL Lite's**, unchanged, because family
    # rule 2 says the command both products have keeps its chord and all five
    # were free on this side. A person who learned Ctrl+Alt+G in the small
    # editor has learned it in the big one.
    #
    # Ctrl+Alt+G for the pad and Ctrl+Alt+Z for "ask about this document" are
    # short because they are the two things people do; Usage, Sign In and the
    # agreement are rule 9 commands -- once-a-month at most, so they earn *a*
    # key rather than a good one.
    # The two Ctrl+Alt+letter chords here are the §10.8 escape hatch used the
    # same way file.new_plain_text_document and power.describe_character_detail
    # use it: **QUILL Lite's chord, adopted unchanged under family rule 2.** The
    # policy exists because Ctrl+Alt is AltGr on an international layout and
    # because JAWS and NVDA claim parts of that space, and the honest accounting
    # is that this chord pair is already shipped and already pressed -- in the
    # small editor, by the same people, for the same two commands. Giving QUILL a
    # different key would not recover the AltGr exposure; it would only add a
    # second thing to remember, which is the cost rule 2 exists to refuse.
    # Neither is a default JAWS or NVDA command: NVDA's laptop layer uses
    # NVDA+Ctrl+... rather than bare Ctrl+Alt, and JAWS's Ctrl+Alt assignments
    # are Ctrl+Alt+function-key and Ctrl+Alt+arrow (table navigation), not
    # Ctrl+Alt+G or Ctrl+Alt+Z. Both are rebindable, and the Keyboard Manager
    # says so.
    "tools.hosted_ai_assistant": "Ctrl+Alt+G",  # §edsharp-ok — QUILL Lite's chord
    "tools.hosted_ai_ask_document": "Ctrl+Alt+Z",  # §edsharp-ok — QUILL Lite's chord
    # Usage and Sign In are the two that could NOT keep QUILL Lite's chord, and
    # the reason is the same one cmd_spelling_voice_settings already carries in
    # DIVERGENCES: Ctrl+Alt+Shift+F7 through F12 are the six QuillVille sibling
    # launchers in QUILL, and QUILL Lite -- being the editor on its own -- has no
    # siblings to launch, so F9 and F10 are free over there and spoken for here.
    # A chord claimed twice means one of the pair silently never fires, which is
    # worse than a divergence somebody can read about. Same modifiers, same
    # finger shape, two keys to the left, and both are rule 9 commands anyway.
    "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
    "tools.hosted_ai_sign_in": "Ctrl+Alt+Shift+F4",
    "tools.hosted_ai_privacy": "Ctrl+Alt+Shift+K",
    # Thirteen commands that had no DEFAULT_KEYMAP entry at all and were bound
    # (or listed unbound) only in the shipped "QUILL Default" profile. That was
    # backwards: the profile is a delta over these defaults, so a command
    # absent here is a command the Keyboard Manager and the generated reference
    # cannot see, and one a profile could silently pin (bad.md P2.6).
    #
    # Three take positions the leader reclaim freed, with the mnemonic the
    # stale profile had chosen: Q for quiet, M for meeting, Z for undo. The
    # rest ship unbound, which is a decision rather than an omission now.
    "tools.ask_quill_conversation": "Alt+Shift+Q",
    "verbosity.toggle_quiet": "Ctrl+Shift+Grave, Shift+Q",
    "verbosity.toggle_meeting": "Ctrl+Shift+Grave, Shift+M",
    # NOT Ctrl+Shift+Z, which the profile pinned and which is Quick Nav here
    # since 2026-09-16 -- the collision that shipped invisibly for a year.
    "verbosity.undo": "Ctrl+Shift+Grave, Shift+Z",
    "verbosity.history": "",
    "verbosity.preferences": "",
    "verbosity.where_am_i": "",
    "verbosity.what_changed": "",
    "verbosity.speak_status": "",
    "tools.voice_command": "",
    "tools.voice_conversation": "",
    "tools.voice_wakeword": "",
    "tools.voice_status": "",
    "tools.table_studio": "",
    "tools.csv_studio": "",
    # Quiet mode. Alt+Shift+M for mute, and the same chord in QUILL Lite --
    # one key for one idea, in both editors, because "make it stop" is the
    # command somebody reaches for without wanting to think about which
    # app they are in. Free in both keymaps, which is why it is this one.
    "tools.sound_toggle": "Alt+Shift+M",
    "tools.word_count": "Ctrl+Shift+G",
    "tools.spell_check_dialog": "F7",
    # The window that decides how a misspelling is SAID (bad.md 3.6, P1.14).
    # QUILL had the twelve settings and no way to reach them except by finding
    # twelve rows among four hundred.
    #
    # One key below QUILL Lite's Ctrl+Alt+Shift+F7, and that is the whole
    # divergence: QUILL carries the QuillVille launchers on
    # Ctrl+Alt+Shift+F7..F12 and QUILL Lite, being the editor on its own, has no
    # siblings to launch. Same modifiers, one F-key down, so the habit still
    # transfers. Recorded in lite/parity.py DIVERGENCES (rule 11).
    "tools.spelling_announcements": "Ctrl+Alt+Shift+F6",
    # tools.spell_check_ranked retired 2026-09-16: ranked review is the F7
    # dialog's own checkbox, so it is one dialog with one key instead of the
    # same dialog on two (bad.md P0.3). Alt+Shift+F7 is Spelling for This
    # Word in both editors now, which is where QUILL Lite's has always been
    # in spirit and where Word puts the word-level check.
    # Alt+F7 is Add Word to Dictionary in QUILL Lite and was the word-level
    # check here, so one spelling reflex taught the dictionary and the other
    # did not, on the same key. Alt+F7 is Next Misspelling in both now -- an
    # alias, below -- which is what Word means by it, and no habit on it can
    # change anything. Spelling for This Word takes Alt+Shift+F7 in both
    # (bad.md 3.6, P0.3).
    "tools.spell_check_word_at_cursor": "Alt+Shift+F7",
    # Add Word to Dictionary was reachable in QUILL only from the context
    # menu -- a capability with no command and no key. Deliberately OFF the
    # F7 row: no spelling habit should land on the one command here that
    # changes a stored dictionary.
    "tools.add_word_to_dictionary": "Ctrl+Alt+F9",
    "tools.next_misspelling": "Ctrl+F7",
    "tools.previous_misspelling": "Ctrl+Shift+F7",
    "tools.misspelling_list": "Alt+Shift+L",
    # --- Commands QUILL had and left keyless, on QUILL Lite's chords ----------
    #
    # Rule 8 of bad.md: every registered editor command has a key or a written
    # reason not to. A capability with no key is invisible -- it is in a menu
    # somebody has to walk, and absent from the generated keyboard reference
    # entirely. Each of these was registered with binding=None while QUILL Lite
    # reached the same verb on a chord, which is the small product being ahead
    # of the big one in the way CLAUDE.md forbids.
    #
    # Every chord here was FREE in QUILL: nothing was displaced to make room,
    # which is why they could all land at once (bad.md P1.1, P1.13).
    "file.page_setup": "Ctrl+Alt+P",
    "edit.remove_duplicate_lines": "Ctrl+Alt+D",
    "edit.sort_lines_ascending": "Ctrl+Alt+S",
    # Sort Z to A, on QUILL Lite's chord, freed by tools.ai_spell_check
    # vacating the AI class (bad.md P1.1, P1.11).
    "edit.sort_lines_descending": "Ctrl+Alt+Shift+S",
    "format.upper_case": "Ctrl+Shift+U",
    "format.title_case": "Ctrl+Shift+T",
    # QUILL Lite's chord, free at last: the blockquote merge moved Duplicate
    # Selection to Ctrl+Alt+Q, which moved Unquote Lines to Ctrl+Alt+Shift+Q,
    # which let go of this one (bad.md P1.1, P1.2, P2.5 -- a four-link chain,
    # and the reason this command waited two days for a key).
    "format.lower_case": "Ctrl+Shift+K",
    "navigate.next_heading": "Ctrl+Alt+H",
    # Shift for backwards, which is the pattern every other pair in this file
    # follows. It cost tools.ai_thesaurus its H; that moved one letter over in
    # its own Ctrl+Alt+Shift class, to M for synonyMs -- the plain Thesaurus
    # keeps Word's Shift+F7, and Ctrl+Alt+Shift+F7..F12 are the QuillVille
    # launcher block, so the F-keys were not free (bad.md P1.4).
    "navigate.previous_heading": "Ctrl+Alt+Shift+H",
    # Ctrl+Alt+1..6 are the six heading levels; 0 is the way back to body
    # text, which is the same shape Word's style gallery uses and the
    # command QUILL had no key for at all (bad.md P1.4).
    "format.body_text": "Ctrl+Alt+0",
    "navigate.set_language": "Ctrl+Alt+F6",
    "power.describe_character": "Ctrl+Shift+C",
    # The detail window, on QUILL Lite's chord: Ctrl+Shift+C speaks the answer,
    # this one is for studying it (bad.md P1.13).
    "power.describe_character_detail": "Ctrl+Alt+C",  # §edsharp-ok — QUILL Lite's chord
    "view.toggle_spellcheck_as_you_type": "Ctrl+Alt+F7",
    "tools.check_updates": "Ctrl+Alt+U",
    "help.about_quill": "Shift+F1",
    # Open User Guide carried "Ctrl+F1" as a LITERAL after a tab in its menu
    # label, outside the keymap: absent from the generated reference,
    # unreachable from the Keyboard Manager, and deaf to a rebinding. It was
    # latent until 2026-09-16, when help.key_cheatsheet gained the Ctrl+F1
    # alias QUILL Lite uses -- at which point two menu items claimed one key
    # and one of them silently stopped firing. A literal accelerator is
    # invisible to every gate that would have caught it, which is the whole
    # of bad.md H4. Ctrl+Shift+F1 is free in both editors.
    "help.open_user_guide": "Ctrl+Shift+F1",
    # Same defect, found by the gate written for the row above: this had
    # "Shift+F1" as a literal, which About took as a real binding on
    # 2026-09-16 -- so two Help items claimed it and one stopped firing.
    "help.what_can_i_do_here": "Ctrl+Alt+Shift+F1",
    # F1, at last owned by the command whose docstring begins "F1: show
    # context-sensitive help for the currently focused control". Its only
    # key was a literal in a menu label -- so F1 worked, and the keyboard
    # reference said it did not, and the Keyboard Manager could not reach
    # it. That invisibility is why help.context_help was given an F1 alias
    # on 2026-09-15 "because F1 was bound to nothing at all": the premise
    # was wrong, F1 was answered, and the two then claimed one key.
    #
    # This is also QUILL Lite's F1 -- "what this window is for, then what
    # the focused control does" -- and the GATE-<APP>-HELP contract every
    # app in the family is held to (bad.md H4a, decided 2026-09-16).
    "help.help_on_control": "F1",
    # --- Once a year, and therefore on the F-keys (bad.md rule 9, P2.9) -----
    #
    # Back up your settings, restore them, choose which features exist, rebind
    # your keys. Nobody does these in the editing loop, and each was holding a
    # three-modifier LETTER chord in QUILL Lite that an editing verb wanted --
    # Ctrl+Alt+Shift+F, Q and D are Search in Files, Duplicate Selection and
    # Restore Settings' neighbours. The F-keys past F9 are empty in both
    # editors and nothing else is competing for them, so a command used twice
    # a year sits where it costs nothing to leave it.
    "tools.individual_feature_toggles": "Ctrl+Alt+F10",
    "tools.share_export": "Ctrl+Alt+F11",
    "tools.share_import": "Ctrl+Alt+F12",
    # Ranked pairs with the plain list on Alt+Shift+L -- L lists, R ranks --
    # because Ctrl+Shift+L is WordPad's Bullets key and QUILL Lite's, and a
    # list-of-misspellings variant does not outrank a formatting verb both
    # products bind (bad.md 3.1). The two list commands should become one
    # command with a sort option (bad.md P1); until then both keep a key.
    "tools.misspelling_list_ranked": "Alt+Shift+R",
    # Favourite folders to the leader, 2026-09-17 (bad.md §0.6, rule 7: media,
    # radio favourites, favourite folders, AI and remote-file commands live on
    # the leader or in a menu -- editor chords are for the editor).
    #
    # ONE of the three keeps a chord, because only one of them is something you
    # do while working: **open** from a favourite folder. Adding and removing a
    # favourite are things you do once, when you set the app up, and they keep
    # their menu rows. Rule 9 is about once-a-year commands needing *a* key, not
    # the same key, and a menu row is a key route.
    "file.open_from_favorite_folder": "Ctrl+Shift+Grave, G",
    # Two of P1.1's keyless names, each waiting on exactly one of the chords
    # the move above frees, and each taking QUILL Lite's own chord for it so the
    # two products agree. Both are once-in-a-while commands, which is where
    # three-modifier chords belong (rule 9) -- and "reachable only by walking a
    # menu" is a cost a screen-reader user pays on every visit, not once.
    "tools.keymap_editor": "Ctrl+Alt+Shift+R",
    "tools.sound_events": "Ctrl+Alt+Shift+O",
    # Open is leader G; its two managing verbs take two positions the reclaim
    # freed (bad.md 3.5). Keyless before, because the leader was full.
    "file.add_favorite_folder": "Ctrl+Shift+Grave, Shift+F",  # F = Favourite, add
    "file.remove_favorite_folder": "Ctrl+Shift+Grave, Shift+X",  # X = remove, as elsewhere
    # Folds take the Shift+bracket pair beside Ctrl+[ / Ctrl+] outdent and
    # indent, which is where every code editor puts folding. This frees
    # Ctrl+Alt+Shift+L for List Studio and Ctrl+Alt+Shift+F for Search in
    # Files (bad.md 3.1).
    "edit.toggle_fold": "Ctrl+Shift+[",
    "navigate.next_fold": "Alt+Shift+]",
    "navigate.previous_fold": "Alt+Shift+[",
    "tools.list_folds": "Ctrl+Shift+]",
    "tools.thesaurus": "Shift+F7",
    # Inline notes (sticky, content-anchored annotations).
    "notes.add_inline_note": "Alt+Shift+I",
    "notes.next_inline_note": "Alt+Shift+J",
    # Alt+Shift+K, because Alt+Shift+G is Go to Bookmark in QUILL Lite and a
    # bookmark list is a verb both products have (rule 2; bad.md 3.5, P1.15).
    # Alt+Shift+K came free when keep_unique_lines retired the same day.
    "notes.previous_inline_note": "Alt+Shift+K",
    "notes.speak_inline_note": "Alt+Shift+H",
    "tools.read_aloud_start_pause": "Ctrl+Shift+Grave, R",  # §10.8.2: P→R
    "tools.read_aloud_stop": "Ctrl+Shift+Grave, Shift+R",  # §10.8.2: Shift+P→Shift+R
    "tools.dictation_toggle": "Ctrl+Shift+Grave, D",
    "tools.speech_dictate": "Ctrl+Shift+Grave, Shift+D",
    "tools.speech_batch_export": "Ctrl+Shift+Grave, Y",  # Audio Studio
    "radio.play_pause": "Ctrl+Shift+Grave, N",  # Internet Radio (N = the last free plain letter)
    "radio.stop": "Ctrl+Shift+Grave, 0",  # Internet Radio
    "radio.mute_toggle": "Ctrl+Shift+Grave, 9",  # Internet Radio
    # Quick-play favorites have no editor chord. They held Ctrl+Alt+Shift+digit
    # until 2026-09-16, which is the only free three-modifier digit row and is
    # now numbered tray paste -- and rule 7 of bad.md says a media convenience
    # does not outrank an editing verb inside a text editor. In Quill Radio,
    # which has no editor, the ten chords survive on Alt+1..0
    # (APP_KEYMAPS["radio"]). In QUILL they are reached through one chooser,
    # radio.play_favorite, so the Favorite Stations menu still advertises a
    # keyboard route as the menu-accelerator rule requires.
    "radio.play_favorite_1": "",
    "radio.play_favorite_2": "",
    "radio.play_favorite_3": "",
    "radio.play_favorite_4": "",
    "radio.play_favorite_5": "",
    "radio.play_favorite_6": "",
    "radio.play_favorite_7": "",
    "radio.play_favorite_8": "",
    "radio.play_favorite_9": "",
    "radio.play_favorite_10": "",
    "radio.play_favorite": "Ctrl+Shift+Grave, 3",  # Play Favorite... chooser
    "podcasts.play_pause": "Ctrl+Shift+Grave, 8",  # Podcasts
    "podcasts.stop": "Ctrl+Shift+Grave, 7",  # Podcasts
    # Player Information: reviewable status for what is playing. No default
    # chord -- it is a read-only report, not a transport control -- but it is
    # registered so it reaches the Command Palette and can be bound.
    "podcasts.player_information": "",
    # Sound Enhancements: both standalone apps use Ctrl+E, so in full QUILL --
    # which has both players -- one key follows whatever is playing.
    # Was Ctrl+E until 2026-09-16, which is Centre in Word, WordPad and
    # QUILL Lite. Media lives on the leader digits (rule 7), and this joins
    # them rather than holding a plain letter an editing verb needs.
    "media.sound_enhancements": "Ctrl+Shift+Grave, 1",
    "radio.sound_enhancements": "",
    "podcasts.sound_enhancements": "",
    # My Notes in This Episode: your notes for whatever is playing. Unbound by
    # default (no free chord), but registered so it can be given one.
    "podcasts.episode_notes": "",
    # Keep This Episode: streaming -> kept. Unbound (a deliberate, occasional
    # act, not a transport control), registered so it can be given a chord.
    "podcasts.keep_episode": "",
    "radio.record_toggle": "Ctrl+Shift+Grave, 6",  # Internet Radio (Record Now / Stop Recording)
    "podcasts.skip_forward": "Ctrl+Shift+Grave, 5",  # Podcasts
    "podcasts.skip_back": "Ctrl+Shift+Grave, 4",  # Podcasts
    # Locked Dictation (offline Whisper). All remappable; the
    # these are matched in the editor key handlers rather than the accelerator
    # table (no menu accelerators) so Escape can be consumed only while recording.
    "tools.dictation_lock_toggle": "Ctrl+F9",
    "tools.dictation_pause": "Ctrl+Shift+F9",
    "tools.dictation_status": "Alt+F9",
    "tools.dictation_emergency_stop": "Escape",  # consumed only while recording
    "tools.dictation_cancel": "Shift+Escape",  # consumed only while recording
    "tools.describe_image": "Ctrl+Shift+Grave, I",
    # To the leader (bad.md 3.7): read once when a file arrives, not an
    # editing-loop verb -- and Ctrl+Shift+I is where Insert Image goes, so
    # Ctrl+Alt+I can be Insert Markdown Tag as it is in QUILL Lite.
    "tools.document_intake_report": "Ctrl+Shift+Grave, Shift+I",  # I = Intake
    # #357 keymap consolidation: AI commands move from inline F7/Shift+F7/F8/
    # Shift+F8/Ctrl+Shift+T accelerators (which collided with the selection
    # bindings at F8/Shift+F8/Ctrl+F8) to Ctrl+Alt+Shift+ chords, matching
    # the EdSharp port convention. The chord class is reserved for AI so
    # power users can find them by feel. Justifications name the screen-
    # reader binding each chord displaces (NVDA review-cursor for the
    # chord class; F7/F8 selection-start/complete for the displaced
    # inline accelerators).
    # The six AI commands vacate Ctrl+Alt+Shift+{S,I,G,T,M,E} (bad.md P1.11,
    # decided 2026-09-16). QUILL Lite spends the same six on editing verbs, and
    # rule 2 gives a chord to the command both products have. AI keeps its
    # menu, the palette and Alt+Q.
    "tools.ai_spell_check": "",
    "tools.ai_spell_check_interactive": "",
    "tools.ai_grammar_style": "",
    "tools.ai_translate_selection": "",
    "tools.ai_thesaurus": "",
    "tools.ai_switch_engine": "",
    # #357 keymap consolidation: compare commands move from inline
    # F8/Shift+F8/Ctrl+F8 accelerators (colliding with the selection
    # bindings) to the same Ctrl+Alt+Shift+ chord class as the AI
    # commands. The compare class also owns Ctrl+Alt+Shift+D for
    # "Read Current Difference"; Alt+Shift+D stays free for
    # view.toggle_dark_mode (different modifier stack).
    "tools.compare_next_difference": (
        "Ctrl+Alt+Shift+."
    ),  # §edsharp-ok — compare reserved chord class
    "tools.compare_previous_difference": (
        "Ctrl+Alt+Shift+,"
    ),  # §edsharp-ok — compare reserved chord class
    "tools.compare_announce_difference": (
        "Ctrl+Alt+Shift+D"
    ),  # §edsharp-ok — compare reserved chord class
    # view.toggle_dark_mode owns Alt+Shift+D, which does not collide with
    # the Ctrl+Alt+Shift+D compare binding above (different modifier stack).
    "view.toggle_dark_mode": "Alt+Shift+D",
    "help.switch_feature_profile": "Alt+Shift+P",
    # Ctrl+Shift+C is Describe Character in QUILL Lite -- what IS this symbol,
    # the question a listener asks constantly and a reader answers by looking.
    # Copy With Source is a citation aid used far less often (bad.md 3.7).
    "edit.copy_with_source": "Alt+Shift+C",
    "edit.copy_selection_for_email": "Ctrl+Shift+Grave, C",
    "edit.undo": "Ctrl+Z",
    "edit.redo": "Ctrl+Y",
    "edit.toggle_selection_marker": "Ctrl+Alt+F8",  # §edsharp-ok — F8 family
    # NOT Ctrl+Alt+Shift+F8, which bad.md 5.3a proposed: the whole
    # Ctrl+Alt+Shift+F7..F12 block belongs to the QuillVille launchers
    # (app_keymaps.SIBLING_APP_ACCELERATORS), and that table's own comment
    # settles who moves -- "an existing binding outranks a newcomer's
    # convention". Extend Selection Mode is the newcomer to that chord.
    # Alt+Shift+F9 is free in both editors and keeps the mode beside the F8
    # family it belongs to, whose every other combination is already spoken
    # for: F8 marks, Shift+F8 completes, Ctrl+Shift+F8 reselects,
    # Alt+Shift+F8 goes to the start, Ctrl+F8 copies all, and Ctrl+Alt+F8 is
    # now the marker toggle.
    "edit.toggle_extend_selection_mode": "Alt+Shift+F9",  # §edsharp-ok
    "edit.start_selection": "F8",
    "edit.complete_selection": "Shift+F8",
    "edit.reselect": "Ctrl+Shift+F8",
    "edit.go_to_start_of_selection": "Alt+Shift+F8",
    "edit.copy_all": "Ctrl+F8",
    "edit.unselect_all": "Ctrl+Shift+A",
    # Was reachable ONLY as a conditional Shift+Space intercept in
    # _on_editor_key_down -- no chord, no menu row that could show one, and
    # nothing in the keyboard reference. QUILL Lite has had it on Ctrl+Shift+Y
    # since it shipped (bad.md L12, P1.1).
    "edit.say_selected": "Ctrl+Shift+Y",
    "edit.read_all": "Alt+F8",
    "edit.find": "Ctrl+F",
    # macOS HIG: Find Next/Previous are Cmd+G / Cmd+Shift+G. The bare F3 /
    # Shift+F3 defaults need the Fn key held on a stock MacBook (F-keys default
    # to brightness/media), so the darwin alternates give a no-Fn path (#6).
    "edit.find_next": "Cmd+G" if sys.platform == "darwin" else "F3",
    "edit.find_previous": "Cmd+Shift+G" if sys.platform == "darwin" else "Shift+F3",
    "edit.find_all_matches": "Ctrl+Shift+F3",  # was Alt+F3 (now Reveal Codes)
    # Ctrl+H becomes Cmd+H on macOS (system Hide) -- dead by default. The darwin
    # alternate Cmd+Alt+F mirrors the Mac/VS Code Replace convention (#30).
    "edit.replace": "Cmd+Alt+F" if sys.platform == "darwin" else "Ctrl+H",
    # Ctrl+Alt+Shift+F since 2026-09-16. Ctrl+Shift+F is Word's Font key and
    # QUILL Lite's Font for Selection, and the family follows Word (bad.md 3.1,
    # 3.9): the code-editor convention loses to the one in everybody's hands.
    "tools.search_in_files": "Ctrl+Alt+Shift+F",
    "tools.replace_in_files": "Ctrl+Shift+R",
    # Bare "N" after the QUILL-key prefix is intercepted for browse mode in
    # QuillKeyMixin (before chord dispatch), so a bare-N chord here is dead.
    # Sticky-note capture uses the free Shift+N second key (not intercepted).
    "tools.sticky_note_capture": "Ctrl+Shift+Grave, Shift+N",
    # Post to Mastodon: the QUILL-key chord + Shift+P ("Post"). Bare P is taken
    # by navigate.speak_full_path; Shift+P is free and stays mnemonic.
    "tools.post_to_mastodon": "Ctrl+Shift+Grave, Shift+P",
    # #262: Batch Conversion wizard. QUILL-key chord (B is free in the
    # second-key space). The entry moved out of the Tools menu and now
    # sits in File > Import > Batch Conversion... and File > Export >
    # Batch Conversion... (one in each, both invoking the same wizard).
    "file.batch_conversion": "Ctrl+Shift+Grave, B",
    # Ctrl+Shift+H is Select Paragraph in QUILL Lite, so the same reflex that
    # selected a paragraph there ran a document-wide Replace All here --
    # rule 4 of bad.md, destructive habits first, and the reason this was
    # P0. Replace All keeps a key rather than losing one: the leader's X
    # was freed when the Copy Tray took QUILL Lite's Ctrl+Alt+V. Ctrl+H
    # still opens the Replace dialog, which is where most people start.
    "edit.replace_all": "Ctrl+Shift+Grave, X",
    # Word's Insert Hyperlink key, and the chord QUILL has ALREADY answered
    # since the char hook hard-coded it by key code (main_frame.py). That
    # binding was invisible to the keymap editor, the keyboard reference and
    # the Key Describer, and could not be rebound; this makes it real. The
    # x.md authoring chord moves by explicit authorization (2026-09-16) and
    # becomes QUILL Lite's Remove Every Blank Line (bad.md 3.1, 3.2, P0.6).
    "edit.insert_link": "Ctrl+K",
    # Off Ctrl+Shift+E (Select Line in both since 2026-09-17, bad.md 3.3) to the
    # sign it draws; an equation is a once-a-document insert.
    "edit.insert_equation": "Ctrl+Alt+=",  # #1197 — math authoring chord
    # #1304: both ship unbound. The QUILL-key namespace has no free letter left,
    # and taking one from an existing command would cost a binding people already
    # use to buy one they have never had. Both are in the command palette and
    # rebindable in the Keymap Editor, which is what the issue actually asks for.
    "app.repeat_last_announcement": "",
    "app.announcement_self_test": "",
    "app.open_media_player": "",
    "edit.follow_link": "Ctrl+Enter",
    "edit.word_prediction": "Ctrl+.",  # freed Ctrl+Space for the sentence family (§4.22)
    # Ctrl+Space means SENTENCE in both editors (bad.md 5.3a, P1.2b). It was
    # Select Chunk here and Select Sentence in QUILL Lite, which is one key
    # meaning two things across two products -- and the sentence is the one
    # people reach for, so it keeps the chord.
    #
    # Ctrl+Space becomes Cmd+Space on macOS (Spotlight) -- dead by default. The
    # darwin alternate Cmd+Alt+Space avoids the system shortcuts (#32).
    "edit.select_sentence": "Cmd+Alt+Space" if sys.platform == "darwin" else "Ctrl+Space",
    # Renamed from Select Chunk on 2026-09-17. "Chunk" named nothing a person
    # could picture, and the command duplicates Select Word on a word -- both
    # use \w -- so what it is actually FOR is the case Select Word cannot
    # answer: a run of punctuation, or a run of whitespace. "Token" is the word
    # for that. The id is unchanged deliberately: a renamed id orphans every
    # keymap override somebody has already made.
    "edit.select_chunk": "Ctrl+Alt+Space",
    # Ctrl+Shift+V is Paste Without Formatting in Word 365, Notepad, every
    # browser and QUILL Lite -- so a Lite user reaching to paste plain text
    # in QUILL opened a preview pane instead. Preview is QUILL-only and
    # moves (bad.md 3.2, P0.4).
    "view.preview": "Alt+Shift+V",
    "view.browser_preview": "Ctrl+Shift+Grave, V",  # §10.8.2: QUILL-key chord
    # Ctrl+Alt+backslash, written as itself (2026-09-09): two faults in one
    # binding, the second hidden behind the first. wx has no name for this key,
    # so it rejected "Ctrl+Shift+Backslash" outright ("Unrecognized accel key
    # 'Backslash', accel string ignored") and the View menu advertised a chord
    # that could never fire -- the only sign one line in the startup log. And
    # once written as "\" it parsed and collided: Ctrl+Shift+\ has been
    # navigate.match_bracket all along, and the two were at peace only because
    # wx was throwing this one away. Split preview keeps the backslash (it is
    # the divider you are asking for) and takes Ctrl+Alt+Shift -- not bare
    # Ctrl+Alt, which menu_lint rejects and PRD 10.8 explains: on a great
    # many keyboard layouts Ctrl+Alt is AltGr, so the chord types a
    # character instead of firing and nothing tells the user which.
    # tests/unit/ui/test_keymap_accelerators.py walks every chord for both.
    "view.split_preview": "Ctrl+Alt+Shift+\\",
    # Alt+F6, moved off Ctrl+F6 on 2026-09-17 (bad.md 5.7). Ctrl+F6 is
    # Windows' own "next document" in every MDI application, it is Word's,
    # and it is QUILL Lite's -- so QUILL was the one product in the family
    # where the key a person arrives with does something else entirely.
    #
    # Alt+F6 is the better home anyway rather than merely a free one: F6
    # walks the regions, so Alt+F6 reading as "jump straight to one of
    # them" puts Focus Preview in the family it belongs to. Free in both.
    "view.focus_preview": "Alt+F6",
    # The Document Format switcher (One Editor, Every Format): took over the
    # chord the retired Rich text lens command held.
    # QUILL Lite reaches this on a plain chord and QUILL had it on the leader,
    # which rule 6 forbids: nothing QUILL Lite reaches on a plain chord lives on
    # QUILL's leader (bad.md 3.8, P1.2). Leader K is free.
    "format.switch_document_format": "Alt+Shift+F",
    "edit.set_mark": "Ctrl+Shift+M",
    # Ctrl+M becomes Cmd+M on macOS (system Minimize) -- dead by default. The
    # darwin alternate Cmd+Alt+M avoids Minimize (#31).
    "edit.pop_mark": "Cmd+Alt+M" if sys.platform == "darwin" else "Ctrl+M",
    # QUILL Lite's three, and the last of the structural six to converge
    # (bad.md 3.3, P1.2). Exchange moves one modifier over so Expand can have
    # the chord it has in QUILL Lite, and Shrink sits beside it where every
    # other pair in this file puts the reverse of a verb.
    "edit.exchange_point_mark": "Ctrl+Alt+X",  # §edsharp-ok — QUILL Lite's chord
    # support#67: bare Alt+M is a macOS Option deadkey -- disable on darwin
    # (see view.toggle_soft_wrap above). Reachable via the command palette.
    "edit.list_marks": "" if sys.platform == "darwin" else "Alt+M",
    # §10.8's Ctrl+Alt+P avoidance is reversed; QUILL Lite binds all three.
    # QUILL Lite's chord, three keys rather than four, for a verb used in the
    # editing loop. The authoring chord moves by explicit authorization
    # (2026-09-16); Ctrl+Alt+Shift+P is now free (bad.md 3.3, P0.5).
    "edit.select_paragraph": "Ctrl+Shift+H",
    # QUILL Lite's chord, free since Document Statistics took Ctrl+Shift+G, and
    # it returns Ctrl+Alt+W to Line Statistics (bad.md 3.1, 3.3).
    "edit.select_word": "Ctrl+Shift+W",
    # QUILL Lite's chord (bad.md 3.3); the Ctrl+Alt+E it gives up is File Format
    # there and now here too.
    "edit.select_line": "Ctrl+Shift+E",
    # QUILL Lite's File Format window: the encoding and the line endings in one
    # place, which QUILL could read in the status bar and change nowhere
    # (bad.md 3.7, P1.8, F6).
    "file.file_format": "Ctrl+Alt+E",
    # Rule 9: a once-a-year command needs A key, not a short one. This undoes
    # the "do not ask me again for .docx files" checkbox in the File Changed on
    # Disk dialog, which is the only way back from it (bad.md F5).
    "file.forget_external_change_answers": "Ctrl+Shift+F11",
    # The session chooser on demand, so "Not Now" is deferrable rather than
    # lost (rule 9: a once-in-a-while command gets a key, not a short one).
    "file.reopen_last_session": "Alt+Shift+F12",
    # Once in a lifetime, so an F-key past F9 (rule 9). Reachable without
    # switching profiles, because somebody can want their QUILL Lite
    # abbreviations in QUILL without wanting QUILL Lite's menus (bad.md P2.4).
    "tools.bring_from_quilllite": "Alt+Shift+F11",
    # The magical tier (bad.md P3.7): the three things a screen reader cannot
    # say, because they are the application's own knowledge. Asked often enough
    # to deserve a real chord, and grouped so learning one teaches the others.
    "view.describe_this_document": "Alt+Shift+F1",
    "view.describe_last_change": "Alt+Shift+F2",
    "edit.undo_and_say": "Alt+Shift+F3",  # §edsharp-ok — QUILL Lite's chord
    # QUILL Lite's chord for the same command, and Ctrl+Shift+B is Set
    # Bookmark in both from 2026-09-16 (bad.md 3.3, 3.5).
    "edit.select_block": "Ctrl+Alt+Shift+B",
    # PR1 (EdSharp port): section move takes the Alt+Shift+Up/Down slot. The
    # previous expand/shrink selection pair migrates to the QUILL-key chord.
    # J and Shift+J were free in the QUILL-key second-key space (verified
    # against DEFAULT_KEYMAP and both profile JSONs); they sit adjacent to
    # the existing I/H/G group of navigate/contrast/chord-prefix neighbours.
    "edit.expand_selection": "Ctrl+Shift+X",  # was Alt+Shift+Up (§edsharp-ok)
    "edit.shrink_selection": "Ctrl+Alt+Shift+X",  # was Alt+Shift+Down (§edsharp-ok)
    "format.move_section_up": "Alt+Shift+Up",  # §edsharp-ok — markdown/html only
    "format.move_section_down": "Alt+Shift+Down",  # §edsharp-ok — markdown/html only
    # Select Section, the clipboard route out of the section family. Every
    # Alt+Shift letter is spoken for in one editor or the other, and this is a
    # rule 9 command: it earns *a* key rather than a short one. Alt+Shift+F5
    # keeps it in the Alt+Shift family the other four structure keys live in,
    # is free in both products, and carries no Word or Windows meaning to
    # fight (unlike Alt+F4, Alt+F6 and Ctrl+Shift+F5/F6/F12, which do).
    "edit.select_section": "Alt+Shift+F5",
    # Move Section To, the destination picker. Picked the same way
    # Select Section's key was: every Alt+Shift and Ctrl+Alt+Shift *letter* is
    # claimed in one editor or the other, so the choice was among function keys
    # free in both. Ctrl+Alt+Shift+F5 is the same F-key as Select Section with
    # one more modifier -- the bigger version of the same idea, which is worth
    # something to a hand that has learned the smaller one -- and carries no
    # Word or Windows meaning to fight, unlike Alt+F6 (next window within an
    # app), Alt+Shift+F10 (smart tags) and Ctrl+Shift+F5/F6/F12.
    "format.move_section_to": "Ctrl+Alt+Shift+F5",
    "edit.set_named_mark": "",
    "edit.jump_to_named_mark": "",
    "edit.open_review_buffer": "Alt+Shift+U",  # bad.md 4.2: registered, never bound
    "edit.select_to_start_of_line": "Shift+Home",
    "edit.select_to_end_of_line": "Shift+End",
    "edit.select_to_start_of_document": "Ctrl+Shift+Home",
    "edit.select_to_end_of_document": "Ctrl+Shift+End",
    # #608: Quote Lines moved from Ctrl+Q to Ctrl+Shift+Q so Ctrl+Q is
    # free for the system Quit shortcut on macOS (Cmd+Q maps to Ctrl+Q in
    # wxPython). Unquote Lines moved from Ctrl+Shift+Q to Ctrl+Shift+K
    # to keep the two commands as a near-mirror pair (Shift+Q -> Shift+K
    # to stay in the home row). The legacy_rebinding entries below
    # rewrite the prior pair on load for users who saved them to disk.
    "edit.quote_lines": "Ctrl+Shift+Q",  # §4.22 advanced-editor parity; #608
    "edit.unquote_lines": "Ctrl+Alt+Shift+Q",  # one modifier off its twin; #608
    # §edsharp-ok — QUILL Lite's chord (§4.17 avoided Ctrl+D, not this one).
    "edit.duplicate_selection": "Ctrl+Alt+Q",
    "edit.reverse_lines": "Alt+Shift+Z",  # §4.22 advanced-editor parity
    "format.toggle_line_comment": "Ctrl+/",
    # Rule 2: Alt+Shift+A is Expand Abbreviations in QUILL Lite, a verb both
    # products have, so it goes to the command both have and block comment --
    # a code-editor verb QUILL Lite does not have at all -- takes the chord
    # beside its line-comment twin (bad.md 3.4, 3.7, P1.15).
    "format.toggle_block_comment": "Ctrl+Shift+/",
    "format.indent": "Ctrl+]",
    "format.outdent": "Ctrl+[",
    # Line surgery. QUILL has registered all five of these for a long time and
    # bound none of them, so they were reachable from the palette and the menu
    # and from no keystroke at all -- the same shape of gap the QUILL Lite work
    # found in the paragraph commands (2026-09-08). Alt+Up/Down, the chords most
    # editors use for the move pair, are structure navigation here and stay that
    # way; Ctrl+Shift+Up/Down is the next-most-familiar pair and was free.
    "format.move_line_up": "Ctrl+Shift+Up",
    "format.move_line_down": "Ctrl+Shift+Down",
    "format.duplicate_line": "Ctrl+D",
    "format.delete_line": "Ctrl+Shift+Delete",
    "format.join_lines": "Ctrl+Alt+Shift+J",
    # Re-insert recently deleted text *at the cursor*, which is what makes it a
    # move rather than an undo. Not Ctrl+Shift+Z: redo is Ctrl+Y here, but
    # Ctrl+Shift+Z is what a great many hands press for redo anyway, and a key
    # that does something else entirely is worse than a key that does nothing.
    "edit.restore_deletion": "Ctrl+Alt+Shift+Z",
    # Insert/overwrite. Deliberately NOT the Insert key, which is the obvious
    # answer everywhere except here: Insert is NVDA's and JAWS's own modifier,
    # so binding it would fight the screen reader this editor is written for.
    # W for "write over", the letter being free where O was not.
    "view.toggle_overwrite_mode": "Ctrl+Alt+Shift+W",
    # Structured deletion -- the kill-to-end-of-line family, likewise registered
    # and unbound. Backspace deletes backwards and Delete deletes forwards, so
    # the pair keeps that direction and only adds modifiers. Two constraints
    # shaped the exact chords: Ctrl+Alt+Delete is never bindable by anyone
    # (Windows reserves it as the secure attention sequence), and bare Ctrl+Alt+
    # is barred by §10.8 as screen-reader-hostile, so every chord here carries
    # Shift as well.
    # The two case conversions QUILL registered and never bound, so Change Case
    # offered five in the menu and three from the keyboard.
    "format.sentence_case": "Ctrl+Alt+Shift+U",
    "format.toggle_case": "Ctrl+Alt+Shift+N",
    # How many, before you commit to a Replace All. Find All Matches already
    # had Ctrl+Shift+F3; its cheaper sibling had no key, which left "is this
    # search safe to replace?" answerable only by opening a list.
    "power.count_occurrences": "Ctrl+Alt+Shift+F3",
    "power.delete_to_line_start": "Ctrl+Shift+Backspace",
    "power.delete_to_line_end": "Ctrl+Alt+Shift+Delete",
    "power.delete_paragraph": "Ctrl+Alt+Shift+Backspace",
    # Toggle the Tab key between smart indent and literal tab insertion.
    # Bound to a QUILL-key chord: plain Ctrl+M / Ctrl+Shift+M are the mark ring,
    # and Ctrl+Alt+ chords are screen-reader-hostile (§10.8), so neither is usable.
    # The chord tools.ai_spell_check_interactive vacated, which is what it is
    # for: this is QUILL Lite's key for the same toggle (bad.md 3.4, P1.15).
    "format.toggle_tab_insert_mode": "Ctrl+Alt+Shift+I",
    # Say the caret line's indentation on demand -- the one part of a line a
    # screen reader does not read back, and until now askable in neither
    # product. Ctrl+Alt+Shift+V carries no mnemonic and is not pretending to:
    # it is the only chord free in both QUILL and QUILL Lite, and one key across
    # the two is worth more than a better letter in one of them.
    "format.describe_indent_depth": "Ctrl+Alt+Shift+V",
    # QUILL Lite's two, and Word's for the second. Ctrl+Shift+F was Search in
    # Files here, which moved: the family follows Word where Word has a key,
    # and a font is the one everybody's hands already know (bad.md 3.1, P1.7).
    "format.editor_font": "Ctrl+Alt+F",
    "format.selection_font": "Ctrl+Shift+F",
    "format.list_manager": "Ctrl+Shift+Grave, L",
    "format.bold": "Ctrl+B",
    "format.italic": "Ctrl+I",
    "format.describe_formatting": "Ctrl+Shift+D",
    "format.heading_1": "Ctrl+Alt+1",  # §edsharp-ok — overrides NVDA switch-to-synth-1
    "format.heading_2": "Ctrl+Alt+2",  # §edsharp-ok — overrides NVDA switch-to-synth-2
    "format.heading_3": "Ctrl+Alt+3",  # §edsharp-ok — overrides NVDA switch-to-synth-3
    "format.heading_4": "Ctrl+Alt+4",  # §edsharp-ok — overrides NVDA switch-to-synth-4
    "format.heading_5": "Ctrl+Alt+5",  # §edsharp-ok — overrides NVDA switch-to-synth-5
    "format.heading_6": "Ctrl+Alt+6",  # §edsharp-ok — overrides NVDA switch-to-synth-6
    "format.decrease_heading_level": "Alt+Shift+Left",
    "format.increase_heading_level": "Alt+Shift+Right",
    # WordPad's Bullets key, and QUILL Lite's. Ctrl+Alt+B goes to Clear All
    # Bookmarks, which is QUILL Lite's meaning for it (bad.md 3.1, 3.5).
    "format.toggle_bullet_list": "Ctrl+Shift+L",
    # Rich-mode paragraph formatting, arrived at through QUILL Lite and wired
    # here so the editor is never behind its own small sibling. WordPad's
    # chords, deliberately: these are the ones already in people's hands.
    # WordPad's own chord for justify is Ctrl+J, and QUILL Lite uses it. QUILL
    # cannot: Ctrl+J has been Set Temporary Bookmark here for far longer, and a
    # binding somebody's hands already know is not something a new command gets
    # to take. Ctrl+Alt+J instead, and the divergence is recorded rather than
    # hidden -- the two products differ here on purpose.
    # Word's four alignment keys, and QUILL Lite's. QUILL had Justify alone,
    # on the x.md authoring chord Ctrl+Alt+J -- so the one alignment it had
    # was on the one key no other editor uses for it, and the three it did
    # not have were on keys standing empty. The authoring chord moves by
    # explicit authorization (2026-09-16); it is now the temporary
    # bookmark's, which is what Ctrl+J used to be (bad.md 3.1, P0.2).
    "format.align_left": "Ctrl+L",
    "format.align_center": "Ctrl+E",
    "format.align_right": "Ctrl+R",
    "format.justify": "Ctrl+J",
    # Word's Ctrl+Shift+N, and the only way back out of formatting. Every other
    # command in the Format menu is a toggle or a set, so each one needs you to
    # already know what is applied; somebody who cannot glance at the page to
    # see what is still on it had no way to be sure. QUILL Lite asked for it
    # first and QUILL gets it in the same change -- the small product may never
    # be ahead of the editor.
    "format.clear_formatting": "Ctrl+Shift+N",
    "format.line_spacing_single": "Ctrl+1",
    "format.line_spacing_one_and_a_half": "Ctrl+5",
    "format.line_spacing_double": "Ctrl+2",
    "format.grow_font": "Ctrl+Shift+.",
    "format.shrink_font": "Ctrl+Shift+,",
    # Ctrl+Shift+V is Preview here, so plain paste takes Ctrl+Alt+V. Same
    # reasoning: an existing binding wins over a new command's convention.
    # The x.md authoring chord moves by explicit authorization (2026-09-16):
    # Ctrl+Alt+V is Paste from Tray in QUILL Lite, and the tray chooser takes
    # it here too.
    "edit.paste_plain_text": "Ctrl+Shift+V",
    # Ctrl+Shift+L cycles bullets, numbers and off now (bad.md 0.6, 3.4), so the
    # direct numbered verb is a once-in-a-while command and moves to a position
    # the leader reclaim freed. It stays a command because HTML has no strip
    # path and therefore no cycle. Ctrl+Alt+N goes to New Plain Text Document,
    # which is what it opens in QUILL Lite.
    "format.toggle_numbered_list": "Ctrl+Shift+Grave, Shift+L",
    "format.insert_html_tag": "Ctrl+Shift+Grave, H",
    # QUILL Lite's chord (bad.md 3.7, P1.1); Insert Image moves one modifier over.
    "format.insert_markdown_tag": "Ctrl+Alt+I",  # §edsharp-ok — authoring chord (x.md)
    # Format-aware structured inserts: direct authoring chords (x.md),
    # user-authorized; allow-listed in menu_lint, rebindable via editor.
    "format.insert_table": "Ctrl+Alt+T",  # §edsharp-ok — authorized authoring chord (x.md)
    # Ctrl+Alt+Q is Duplicate Selection now, which is what it means in QUILL Lite
    # (bad.md 3.3, 0.6). Block Quote lost its chord to the merge above it: the
    # command stays for the HTML branch and is reached from the Format menu and
    # the palette, which is what a once-a-document structural insert wants.
    "format.blockquote": "",
    # H is for Heading: Ctrl+Alt+H and Ctrl+Alt+Shift+H walk them in QUILL Lite,
    # and heading navigation is an editing-loop verb where inserting a rule is
    # a once-a-document one. The authoring chord moves to the key that draws
    # what a rule looks like (bad.md 3.5).
    "format.horizontal_rule": "Ctrl+Alt+-",
    "power.insert_image": "Ctrl+Shift+I",
    # Table cell navigation: move cell by cell inside a
    # pipe/Markdown table, hearing each cell + its position. Context-sensitive --
    # harmless outside a table. §edsharp-ok authoring/navigation chords.
    "table.next_cell": "Ctrl+Alt+Right",  # §edsharp-ok — table cell navigation
    "table.previous_cell": "Ctrl+Alt+Left",  # §edsharp-ok — table cell navigation
    "table.cell_below": "Ctrl+Alt+Down",  # §edsharp-ok — table cell navigation
    "table.cell_above": "Ctrl+Alt+Up",  # §edsharp-ok — table cell navigation
    "table.first_cell": "Ctrl+Alt+Home",  # §edsharp-ok — table cell navigation
    "table.last_cell": "Ctrl+Alt+End",  # §edsharp-ok — table cell navigation
    # Announce Headings, on the family's function-key range. Ctrl+Alt+F1 is
    # Tutorials and Ctrl+Alt+F2 is Get Help from Support; F3 joins them, and the
    # same reasoning exempts it from the Ctrl+Alt policy (menu_lint.py): the
    # policy is about AltGr on character keys and about the readers' own
    # Ctrl+Alt+letter/arrow commands, and a function key is neither.
    "view.toggle_heading_announcements": "Ctrl+Alt+F3",  # §edsharp-ok — family F-key
    # Announce Lists, on the same range and exempt for the same reason. F5 and
    # not the F4 that would have sat next to its sibling: a finger that misses
    # the Control key on a chord pressed this often finds Alt+F4, and what that
    # costs is the document. Shared with QUILL Lite, key for key.
    "view.toggle_list_announcements": "Ctrl+Alt+F5",  # §edsharp-ok — family F-key
    "table.row_start": "Alt+Home",
    "table.row_end": "Alt+End",
    "power.paste_html_as_markdown": "Ctrl+Shift+Grave, M",
    "power.non_ascii_jump_to_source": "",  # assign via Keymap Editor; use from Non-ASCII report
    "power.non_ascii_jump_to_report": "",  # assign via Keymap Editor; jump back to report
    "power.open_snippet_gallery": "Ctrl+Shift+Grave, Shift+G",
    "format.insert_snippet": "Ctrl+Shift+Grave, S",
    "format.manage_snippets": "Ctrl+Shift+Grave, Shift+S",
    "format.expand_abbreviation": "Ctrl+Shift+Grave, A",
    "format.manage_abbreviations": "Ctrl+Shift+Grave, Shift+A",
    # No default chord: the Ctrl+Shift+Grave leader space is fully allocated,
    # and taking a used one would silently break an existing habit. Registered
    # so it reaches the Command Palette and can be bound by anyone who wants it.
    "format.quick_insert": "",
    "format.new_abbreviation_from_clipboard": "",
    "format.toggle_abbreviation_expansion": "Alt+Shift+A",
    # List Studio had F2 and Insert Special Character Shift+F2. Both move:
    # F2 and Shift+F2 are Next and Previous Bookmark in QUILL Lite and in
    # every editor people arrive from, and walking bookmarks is an
    # editing-loop verb where List Studio is a dialog you visit (bad.md 3.5).
    "format.list_studio": "Ctrl+Alt+Shift+L",
    "format.list_studio_settings": "",  # no default key; assign via keymap editor
    "story.open_studio": "",  # Story Studio binder; no default key, assign via keymap editor
    "vault.open": "",  # Accessible Vault; no default keys, assign via keymap editor
    "vault.explorer": "",
    "vault.follow_link": "",
    "vault.backlinks": "",
    "vault.neighborhood": "",
    "vault.unlinked_mentions": "",
    "vault.insert_link": "",
    "vault.complete": "",
    "vault.rename": "",
    "vault.quick_switch": "",
    "vault.search": "",
    "vault.tags": "",
    "vault.speak_embed": "",
    "vault.resolve_embed": "",
    "vault.insert_template": "",
    "vault.today": "",
    "vault.prev_daily": "",
    "vault.next_daily": "",
    "vault.export_site": "",
    "vault.sync": "",
    "vault.settings": "",
    "sync.sync_folder": "",
    # GitHub repository admin (Tools > GitHub): the reclaim's other eight. Menu
    # and palette only, like the Tier 2/3 commands below that never had a chord.
    "github.create_repository": "",
    "github.fork_repository": "",
    "github.rename_repository": "",
    "github.change_repository_visibility": "",
    "github.change_default_branch": "",
    "github.configure_branch_protection": "",
    "github.delete_branch": "",
    "github.commit_multiple_files": "",
    # GitHub Tier 2 (Organizations/Releases/Actions dispatch/Notifications/
    # Security alerts). No default chords -- the leader-chord space is fully
    # claimed; reachable via the menu and the Command Palette.
    "github.browse_organization": "",
    "github.create_release": "",
    "github.dispatch_workflow": "",
    "github.view_notifications": "",
    "github.view_security_alerts": "",
    # GitHub Tier 3 (Codespaces + Copilot CLI, needs live-device
    # verification -- see quill/core/github/gh_bridge.py). No default
    # chords -- the leader-chord space is fully claimed.
    "github.list_codespaces": "",
    "github.create_codespace": "",
    "github.copilot_suggest": "",
    "github.copilot_explain": "",
    # Local git (Tools > Local Git). No default chords -- the single-letter
    # leader-chord space is fully claimed (see the github.* block above);
    # these are reachable via the menu and the Command Palette, and freely
    # assignable in Preferences > Keyboard Shortcuts like every command.
    "localgit.uncommitted_changes": "",
    "localgit.switch_branch": "",
    "localgit.stash_changes": "",
    "localgit.manage_stashes": "",
    "localgit.blame_at_cursor": "",
    "localgit.bisect_start": "",
    "localgit.bisect_reset": "",
    "localgit.resolve_conflicts": "",
    "localgit.interactive_rebase": "",
    "localgit.rebase_abort": "",
    "vault.publish_note": "",
    "power.insert_special_character": "Ctrl+Shift+F2",  # QUILL Lite's chord
    # The chord Word uses for the same thing, so nobody has to learn one (#1488).
    "power.insert_line_break": "Shift+Enter",
    "edit.insert_emoji": "Alt+.",  # Accessible Emoji Picker
    "power.number_lines": "Alt+Shift+N",  # §4.22 Number Items parity
    "power.trim_blank_lines": "Ctrl+Shift+Enter",  # §4.22 Trim Blanks parity
    # QUILL Lite's two whitespace verbs, on QUILL Lite's chords where the
    # chord was free. Remove Every Blank Line takes Ctrl+Alt+K, freed by
    # Insert Link moving to Word's Ctrl+K. Trim Trailing Spaces CANNOT take
    # QUILL Lite's Ctrl+Alt+T, which is Insert Table here -- an authorized
    # x.md authoring chord for a verb that builds structure, deliberately
    # kept over one that strips whitespace (decided 2026-09-16). That is a
    # documented divergence, the only one in bad.md 3.2 that does not
    # converge, and it is in the parity gate's exception table.
    "power.remove_blank_lines": "Ctrl+Alt+K",
    "edit.trim_trailing_whitespace": "Ctrl+Alt+R",
    # QUILL Lite's chord, freed by the AI class vacating (bad.md P1.1, P1.11).
    "edit.normalize_whitespace": "Ctrl+Alt+Shift+T",
    # Five verbs QUILL Lite gave a key on 2026-09-16 and QUILL could only reach
    # by walking a menu, on the chords QUILL Lite uses -- all four of those were
    # free here, so there was nothing to trade (bad.md P1.1, rule 8). Line
    # Statistics takes Ctrl+Alt+G rather than QUILL Lite's Ctrl+Alt+W, which is
    # edit.select_word here: it is the "how wide is this" sibling of Document
    # Statistics on Ctrl+Shift+G, so G is the letter either way.
    "edit.convert_indentation_to_spaces": "Alt+F11",
    "edit.convert_indentation_to_tabs": "Alt+F12",
    "power.delete_lines_containing": "Alt+Shift+X",
    "power.hard_wrap_lines": "Alt+Shift+W",
    # QUILL Lite's chord, reachable now Select Word has moved (bad.md 3.7).
    "power.compute_line_statistics": "Ctrl+Alt+W",
    # The collector and the clip library, on QUILL Lite's chords (P1.12).
    # Paste Collected is absent because QUILL has no such command yet;
    # Ctrl+Alt+Shift+G is held open for it (C4).
    # Alt+Shift+S, not Ctrl+Alt+G, since 2026-09-22. Google Drive for desktop
    # registers Ctrl+Alt+G **system-wide**, and a system-wide hotkey is handed
    # to its owner before a focused application sees the key at all -- so this
    # command could not be reached from the keyboard on any machine with Drive
    # installed, and nothing said why. An in-app accelerator cannot outrank
    # RegisterHotKey; the only fix that works out of the box is not to sit on
    # the chord. Ctrl+Alt+<letter> is where third-party global hotkeys live,
    # which is why Drive chose it, so this one leaves that space entirely.
    # (The detection that makes the *next* one of these say so rather than go
    # silent lives in quill/platform/windows/hotkey_owner.py.)
    "power.toggle_clipboard_collector": "Alt+Shift+S",
    "edit.keep_selection_in_clip_library": "Ctrl+Alt+M",
    "edit.open_clip_library": "Ctrl+Alt+Shift+M",
    # power.keep_unique_lines retired 2026-09-18 (bad.md 7.1, P2.5): it and
    # edit.remove_duplicate_lines called the SAME core function through two
    # command ids, two chords and two sentences -- "Kept unique lines (removed
    # duplicates)" and "Removed duplicate lines" -- which is one verb a listener
    # has to learn twice and two places for the wording to drift. QUILL Lite has
    # one, on Ctrl+Alt+D, and that is the one that survives. Alt+Shift+K is free.
    "quill.quick_nav.heading": "H",
    "quill.quick_nav.link": "A",
    "quill.quick_nav.list": "L",
    "quill.quick_nav.list_item": "I",
    "quill.quick_nav.table": "T",
    "quill.quick_nav.block_quote": "Q",
    "quill.quick_nav.bookmark": "B",
    "quill.quick_nav.code_block": "'",
    "quill.quick_nav.table_of_contents": "C",
    "quill.quick_nav.paragraph": "P",
    "quill.quick_nav.sentence": "S",
    "quill.quick_nav.block": "TAB",
    "quill.quick_nav.skip_forward": "]",
    "quill.quick_nav.skip_backward": "[",
    # §8.1 — context help for current mode and doc summary (Alt+I).
    # Alt+H is reserved for the Help menu mnemonic; Ctrl+Shift+H is edit.replace_all;
    # Ctrl+Alt+ is banned by §10.8 (screen-reader-hostile). Use the QUILL-key chord.
    "help.context_help": "Ctrl+Shift+Grave, Shift+H",
    # support#67: bare Alt+I is a macOS Option deadkey -- disable on darwin
    # (see view.toggle_soft_wrap above). Reachable via the command palette.
    "document.summary": "" if sys.platform == "darwin" else "Alt+I",
    # §8.2 — universal "Go to anything" palette (Quill+G).
    # QUILL Lite's chord, so the fuzzy jump is one key in both (bad.md P2.19).
    # The leader G it gives up is what 5.9 wants for a favourite folder.
    # Freed by the favourite-folder move above; QUILL Lite's chord for it.
    "navigate.go_to_anything": "Ctrl+Alt+Shift+A",
    # Quick Nav had no key at all. It is a landmark index rather than a
    # command palette -- a different surface answering a different
    # question -- so the two stay two commands (§0.6).
    #
    # Ctrl+Shift+Z both opens and CLOSES it, so the key is a toggle and
    # Escape still closes it too. Free in both editors, and Redo is Ctrl+Y
    # here as it is in Word, so nothing collides. Worth knowing: Ctrl+Shift+Z
    # is Redo in VS Code and in browsers, so somebody arriving from those
    # may press it expecting Redo and get a list of landmarks instead --
    # recorded rather than avoided, because the alternative is leaving a
    # surface with no key at all.
    "navigate.quick_nav": "Ctrl+Shift+Z",
    # §8.1 — QUILL-key cheatsheet overlay (Alt+?).
    "help.key_cheatsheet": "Alt+Shift+/",
    # §8.1 — live contrast check announcement.
    "view.announce_contrast": "Ctrl+Shift+Grave, Shift+C",
    # Spoken Echo — virtualise the last several announcements into a read-only
    # review dialog (E for Echo). Alt+Shift+E is free (Alt+Shift+letter chords
    # are used elsewhere, e.g. Z/N/K) and not screen-reader-hostile.
    "view.spoken_echo": "Alt+Shift+E",
    # §8.2 — explain why the focused item is unavailable ("Why don't I see…?").
    "help.why_unavailable": "Alt+F1",
    "help.tutorials": "Ctrl+Alt+F1",  # the family key: Radio, Cast, Weather too
    # One key along from Tutorials, and the family key for the same reason:
    # every app answers it with the same door to a person who can reply.
    "help.report_bug": "Ctrl+Alt+F2",
    # Long said to "move to QUILL key, V"; it never did (leader V is Browser
    # Preview), so it stayed menu-only. Leader Shift+V now (bad.md C9).
    "edit.magic_paste": "Ctrl+Shift+Grave, Shift+V",
    # §CopyTray — Copy Tray slot access (12 slots).
    # Paste: Ctrl+Shift+N for N=1-9, Ctrl+Shift+0 for slot 10,
    #        Ctrl+Shift+- for slot 11, Ctrl+Shift+= for slot 12.
    # Copy:  QUILL+Shift+N for same key positions (Shift+digit/symbol).
    # QUILL+1-6 (bare) are heading shortcuts; Shift variants are distinct.
    # Open tray dialog: QUILL+X.
    # QUILL Lite's Paste from Tray chord. It was a leader chord here, which
    # is a two-stroke route to the tray's only overview (bad.md 5.1, P0.4).
    "edit.open_copy_tray": "Ctrl+Alt+V",
    # QUILL Lite's chords for the two tray verbs that do not need a slot
    # number: put this somewhere, and empty the whole thing (bad.md 3.7).
    "edit.clear_all_tray_slots": "Ctrl+Alt+Shift+Y",
    "edit.copy_to_next_slot": "Ctrl+Alt+Y",
    # The chooser beside it, on QUILL Lite's chord: the next free slot is the
    # right default and the wrong only option (bad.md P2.1, 5.1).
    "edit.copy_to_tray_slot": "Alt+Shift+Y",
    "edit.search_tray_slots": "",
    "edit.copy_to_tray_1": "Ctrl+Shift+Grave, Shift+1",
    "edit.copy_to_tray_2": "Ctrl+Shift+Grave, Shift+2",
    "edit.copy_to_tray_3": "Ctrl+Shift+Grave, Shift+3",
    "edit.copy_to_tray_4": "Ctrl+Shift+Grave, Shift+4",
    "edit.copy_to_tray_5": "Ctrl+Shift+Grave, Shift+5",
    "edit.copy_to_tray_6": "Ctrl+Shift+Grave, Shift+6",
    "edit.copy_to_tray_7": "Ctrl+Shift+Grave, Shift+7",
    "edit.copy_to_tray_8": "Ctrl+Shift+Grave, Shift+8",
    "edit.copy_to_tray_9": "Ctrl+Shift+Grave, Shift+9",
    "edit.copy_to_tray_10": "Ctrl+Shift+Grave, Shift+0",
    "edit.copy_to_tray_11": "Ctrl+Shift+Grave, Shift+-",
    "edit.copy_to_tray_12": "Ctrl+Shift+Grave, Shift+=",
    # Ctrl+Shift+digit is Set Bookmark N in both editors from 2026-09-16:
    # QUILL Lite has meant that since it shipped, numbered bookmarks live in
    # shared core so QUILL could adopt them, and a bookmark is an
    # editing-loop verb where pasting slot 7 by number is not (bad.md 3.2,
    # P0.1). Paste keeps the same digits one modifier out; the row it moves
    # into was Quill Radio's quick-play favorites, which are now the radio
    # app's own keys plus a chooser here (app_keymaps.py, radio.play_favorite).
    "edit.paste_from_tray_1": "Ctrl+Alt+Shift+1",
    "edit.paste_from_tray_2": "Ctrl+Alt+Shift+2",
    "edit.paste_from_tray_3": "Ctrl+Alt+Shift+3",
    "edit.paste_from_tray_4": "Ctrl+Alt+Shift+4",
    "edit.paste_from_tray_5": "Ctrl+Alt+Shift+5",
    "edit.paste_from_tray_6": "Ctrl+Alt+Shift+6",
    "edit.paste_from_tray_7": "Ctrl+Alt+Shift+7",
    "edit.paste_from_tray_8": "Ctrl+Alt+Shift+8",
    "edit.paste_from_tray_9": "Ctrl+Alt+Shift+9",
    "edit.paste_from_tray_10": "Ctrl+Alt+Shift+0",
    "edit.paste_from_tray_11": "Ctrl+Alt+Shift+-",
    "edit.paste_from_tray_12": "Ctrl+Alt+Shift+=",
}


#: A **second** chord for a command that already has one, command id to chord.
#:
#: Kept out of :data:`DEFAULT_KEYMAP` because that dict is the *rebindable*
#: keymap -- it round-trips through the Keyboard Manager, the keyboard packs and
#: the saved-delta file, all of which assume one chord per command. An alias
#: stands alongside whatever the user chose, so moving F8 keeps it.
#:
#: F8 stays: it is Word's own Extend Selection key. The home-row pair is added
#: beside it because a function key means taking a hand off the home row, which
#: costs somebody who is not looking at the keyboard. Both chords were free in
#: QUILL and QUILL Lite alike -- the two editors must not disagree this close to
#: the fingers. The full reasoning, including why not Ctrl+, (Preferences in
#: both) or Ctrl+. (Word Prediction here), is in quill/core/lite/keymap.py.
DEFAULT_ALIASES: dict[str, str] = {
    # Windows' MDI pair, and QUILL Lite's. Ctrl+Tab stays the primary in both
    # -- it is what people actually press -- and these are the keys the
    # platform documents, so both work rather than one (rule 5: a chord free
    # in both is adopted as an alias and nothing moves). Ctrl+F6 was
    # view.focus_preview here until 2026-09-17, which made QUILL the only
    # product in the family where it did not walk documents (bad.md 5.7).
    "window.next_document": "Ctrl+F6",
    "window.previous_document": "Ctrl+Shift+F6",
    "edit.start_selection": "Ctrl+;",
    "edit.complete_selection": "Ctrl+'",
    # F1 is THE help key on Windows and QUILL left it unbound, context help on a
    # leader chord. QUILL Lite has answered F1 since it shipped. An alias, not a
    # move: the leader chord keeps working (2026-09-15).
    # help.context_help had F1 here from 2026-09-15 to 2026-09-16. It keeps
    # its leader chord; F1 went to help.help_on_control, which is what F1
    # already did through a literal nobody could see. See that row.
    # Word's key for the same thing, in both editors. The primary Ctrl+F7
    # keeps working; this is the chord a person arrives with (bad.md 3.6).
    "tools.next_misspelling": "Alt+F7",
    # Word's function-key trio. Free in both editors, so they cost nothing and
    # they are what a hand trained on Word reaches for. Aliases, not moves:
    # Ctrl+S, Ctrl+O and Ctrl+P remain the primaries (bad.md rule 5, P2.7).
    "file.save_as": "F12",
    "file.open": "Ctrl+F12",
    "file.print": "Ctrl+Shift+F12",
    # Word's own Bookmark key, kept as a second route when QUILL Lite's
    # Alt+Shift+G became the primary (bad.md 3.5, P1.15). It was the primary
    # itself between 2026-09-16 and 2026-09-18, so legacy_rebindings carries
    # the hop; anyone who learned it in that window still lands here.
    "navigate.list_bookmarks": "Ctrl+Shift+F5",
    "navigate.outline_navigator": "Ctrl+Alt+L",
    # QUILL Lite reaches the shortcut list on Ctrl+F1; QUILL had it on
    # Alt+Shift+/, which is a chord you have to be told about.
    "help.key_cheatsheet": "Ctrl+F1",
    # Three more QUILL Lite reaches on a plain chord and QUILL buried on the
    # leader chord. Same argument as F1: the small product found the obvious
    # key first, and a person who uses both should not have to learn two.
    # Go To Anything is NOT here -- QUILL Lite's Ctrl+Alt+Shift+A is
    # file.add_favorite_folder in QUILL, so aligning it needs a decision about
    # which one moves rather than an alias (bad.md 3c).
    "format.insert_html_tag": "Ctrl+Alt+O",
    "format.manage_abbreviations": "Ctrl+Alt+A",
}


def alias_for(command_id: str) -> str:
    """The second chord *command_id* also answers to, or ``""``."""
    return DEFAULT_ALIASES.get(command_id, "")


# Uppercased prefix of the QUILL-key leader chord, used by the 0.8.0 beta
# Find force in ``merge_keymaps`` to recognize any saved Find binding that
# still lives on the leader chord (e.g. "Ctrl+Shift+Grave, Z").
_QUILL_LEADER_PREFIX = "CTRL+SHIFT+GRAVE"

# Keymap defaults epoch (GATE-keymap-fwdcompat). The on-disk keymap.json is a
# *delta* of the user's overrides relative to DEFAULT_KEYMAP plus this stamp.
# Because non-overridden commands are absent from the file, any new or changed
# default in DEFAULT_KEYMAP automatically reaches every existing user on the
# next launch -- without a per-binding migration entry. That is the whole point
# of the delta format: it removes the fragile "remember to add an old->new
# rebinding for every default change" tax.
#
# The epoch is only needed for the one-time conversion of *legacy* keymap.json
# files, which were full snapshots that pinned every command to its value at
# save time (so a changed default never reached the user). A file whose stamp
# is below ``KEYMAP_DEFAULTS_EPOCH`` -- including the unstamped legacy files --
# gets the curated ``legacy_rebindings`` clean-up and the Find force applied,
# then is rewritten as a stamped delta so it never needs that treatment again.
#
# Bump this ONLY to re-run the legacy-style clean-up against files already on
# the current epoch (rare). Normal default changes need no bump and no
# migration entry; just change DEFAULT_KEYMAP.
KEYMAP_DEFAULTS_EPOCH = 1
_DEFAULTS_EPOCH_KEY = "_defaults_epoch"


def keymap_path() -> Path:
    return app_data_dir() / "keymap.json"


def _keymap_overrides(merged: dict[str, str]) -> dict[str, str]:
    """Return only the entries of *merged* that must be persisted as a delta.

    Two kinds of entry are written: a known command whose chord differs from its
    ``DEFAULT_KEYMAP`` value (omitting equal-to-default is what lets a later
    ``DEFAULT_KEYMAP`` change reach the user automatically -- see
    ``KEYMAP_DEFAULTS_EPOCH``); and a binding for a command this build does not
    ship, carried forward verbatim so a newer sibling app's binding survives
    this build's rewrite (see the multi-vintage note in ``merge_keymaps``).
    """
    return {
        command_id: chord
        for command_id, chord in merged.items()
        if command_id not in DEFAULT_KEYMAP or chord != DEFAULT_KEYMAP[command_id]
    }


def _persisted_keymap_document(merged: dict[str, str]) -> dict[str, object]:
    """The on-disk shape: the override delta plus the current epoch stamp."""
    document: dict[str, object] = dict(_keymap_overrides(merged))
    document[_DEFAULTS_EPOCH_KEY] = KEYMAP_DEFAULTS_EPOCH
    return document


def load_keymap() -> dict[str, str]:
    """Load the user's keymap from disk and return the cleaned merged map.

    The on-disk file is a *delta* of the user's overrides relative to
    ``DEFAULT_KEYMAP`` plus a ``_defaults_epoch`` stamp. ``merge_keymaps``
    starts from ``DEFAULT_KEYMAP`` and applies only the saved overrides that
    are still valid, so any command the user never customized always tracks
    the current default.

    When the on-disk file does not already match the canonical delta+epoch
    shape -- a legacy full snapshot, an unstamped or older-epoch file, or one
    that still carries entries equal to the default -- it is rewritten to the
    canonical shape. That converts legacy snapshots to deltas once and stamps
    the epoch so the one-time clean-up never runs again.
    """
    path = keymap_path()
    if not path.exists():
        return DEFAULT_KEYMAP.copy()
    try:
        raw = read_json(path, default=None)
    except (ValueError, OSError):
        raw = None
    if not isinstance(raw, dict):
        # A file that exists but does not parse is corrupt: quarantine it before
        # falling back to defaults, so the user's bindings are recoverable and a
        # bad file never crashes startup.
        from quill.core.migration_backup import backup_corrupt_file

        backup_corrupt_file("keymap", path)
        return DEFAULT_KEYMAP.copy()
    cleaned = merge_keymaps(raw)
    saved_epoch = raw.get(_DEFAULTS_EPOCH_KEY)
    if isinstance(saved_epoch, int) and saved_epoch > KEYMAP_DEFAULTS_EPOCH:
        # The file was stamped with a HIGHER epoch than this build knows: a newer
        # sibling app applied curated rebindings this build has no record of. Use
        # the merged map in memory, but never rewrite the file -- downgrading it
        # to this build's epoch would strip the newer app's migration stamp (so
        # this build's own older one-time rebindings would wrongly re-run against
        # it on the next launch). Mirrors the settings store's future-file guard.
        return cleaned
    desired = _persisted_keymap_document(cleaned)
    if raw != desired:
        try:
            write_json_atomic(path, desired)
        except OSError as exc:
            # Persistence is best-effort: a read-only install or a locked
            # file should not stop QUILL from launching with the cleaned
            # map in memory. The cleanup will retry on the next launch.
            logger.debug("Could not persist cleaned keymap to %s: %s", path, exc)
    return cleaned


def save_keymap(keymap: dict[str, str]) -> None:
    # Persist only the override delta plus the epoch stamp, never the full
    # map, so future DEFAULT_KEYMAP changes flow through to the user. Callers
    # pass the full merged map; the delta is computed here so every save site
    # (editor, reset, import, share) gets the forward-compatible shape.
    write_json_atomic(keymap_path(), _persisted_keymap_document(keymap))


def build_keymap_for_pack(name: str) -> dict[str, str]:
    pack = KEYBOARD_PACKS.get(name)
    merged = DEFAULT_KEYMAP.copy()
    if pack is None:
        return merged
    if sys.platform == "darwin":
        # #4: packs are written Windows-flavored (Ctrl+.../Alt+...) and applied
        # verbatim on Windows, but on macOS wx maps ACCEL_CTRL to Cmd, so a pack's
        # literal chord can land on a macOS system-reserved shortcut or collide
        # with a darwin-aware DEFAULT_KEYMAP binding the curated defaults chose.
        # DEFAULT_KEYMAP was hand-audited for Mac; the packs were not. Apply the
        # pack on macOS through the collision guard so a system-reserved or
        # colliding override is dropped (the darwin default wins) rather than
        # silently clobbering another command.
        _apply_darwin_pack_overrides(merged, pack.bindings)
    else:
        merged.update(pack.bindings)
    return merged


# macOS system-reserved chords a Quill binding must never steal on the Mac side
# of the Ctrl->Cmd accelerator mapping (#4). F9-F12 are the stock Mission
# Control / Spaces / Dashboard defaults; the Cmd+ chords are app-level ones
# (hide / minimize / quit / close / Spotlight / app switcher / window cycle).
_MACOS_RESERVED_RUNTIME_CHORDS: frozenset[str] = frozenset({
    "Cmd+H",
    "Cmd+M",
    "Cmd+Q",
    "Cmd+W",
    "Cmd+Space",
    "Cmd+Tab",
    "Cmd+Grave",
    "F9",
    "F10",
    "F11",
    "F12",
})


def _darwin_runtime_chord(chord: str) -> str | None:
    """The chord as it fires on macOS, where wx maps ACCEL_CTRL to Cmd (#4).

    A pack stores ``"Ctrl+G"``; on macOS that fires as Cmd+G. To detect
    collisions against DEFAULT_KEYMAP's darwin ``"Cmd+G"`` entries, fold a
    leading Ctrl token to Cmd for comparison only. Storage is unchanged -- this
    is a comparison-time view, not a rewrite of the binding.
    """
    canonical = canonical_binding(chord, quill_key_prefix=_QUILL_LEADER_PREFIX)
    if canonical is None:
        return None
    if canonical.startswith("Ctrl+"):
        return "Cmd+" + canonical[len("Ctrl+") :]
    return canonical


def _is_macos_reserved_runtime_chord(runtime_chord: str) -> bool:
    """True when *runtime_chord* (already Ctrl->Cmd folded) is macOS-reserved.

    Also flags ``Option+<single letter>`` (Alt with no other modifier): on macOS
    that is a dead-key / diacritical (Alt+A = å, Alt+E = acute accent, ...), so a
    pack binding there would steal a character the user types (support#67).
    """
    if runtime_chord in _MACOS_RESERVED_RUNTIME_CHORDS:
        return True
    if runtime_chord.startswith("Alt+") and runtime_chord.count("+") == 1:
        key = runtime_chord[len("Alt+") :]
        if len(key) == 1 and key.isalpha():
            return True
    return False


def _apply_darwin_pack_overrides(merged: dict[str, str], pack_bindings: Mapping[str, str]) -> None:
    """Apply a keyboard pack's bindings on macOS with collision review (#4).

    Drops a pack override (keeping the darwin-aware DEFAULT_KEYMAP value for that
    command) when it would land on a macOS system-reserved chord or collide with a
    binding already present in *merged* once both are viewed at Mac runtime
    (Ctrl->Cmd). A user who wants the Windows app's exact chord can still rebind it
    explicitly via the keymap editor, which runs the full conflict review in
    :func:`merge_keymaps`.
    """
    runtime_merged: dict[str, str | None] = {
        command: _darwin_runtime_chord(chord) for command, chord in merged.items()
    }
    for command_id, raw_chord in pack_bindings.items():
        chord = raw_chord.strip()
        if not chord:
            # Empty pack binding means "use the default"; keep DEFAULT_KEYMAP.
            continue
        runtime = _darwin_runtime_chord(chord)
        if runtime is None:
            logger.debug(
                "Pack override %r -> %r dropped on macOS: unparseable chord (#4).",
                command_id,
                raw_chord,
            )
            continue
        if _is_macos_reserved_runtime_chord(runtime):
            logger.debug(
                "Pack override %r -> %r dropped on macOS: system-reserved chord (#4).",
                command_id,
                raw_chord,
            )
            continue
        collides = any(
            other != command_id and other_runtime == runtime
            for other, other_runtime in runtime_merged.items()
            if other_runtime is not None
        )
        if collides:
            logger.debug(
                "Pack override %r -> %r dropped on macOS: collides with a "
                "darwin-aware default (#4).",
                command_id,
                raw_chord,
            )
            continue
        merged[command_id] = chord
        runtime_merged[command_id] = runtime


def merge_keymaps(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return DEFAULT_KEYMAP.copy()
    merged = DEFAULT_KEYMAP.copy()
    #: Commands this user has explicitly bound, as they are read. What makes the
    #: conflict rule below able to tell "your choice against a default" from
    #: "your choice against your other choice" -- two situations with different
    #: right answers and, until 2026-09-10, one behaviour.
    chosen: set[str] = set()
    # A file stamped below the current epoch (or unstamped -- a legacy full
    # snapshot) gets the one-time clean-up: the curated old->new rebindings and
    # the leader-chord Find force. Files already on the current epoch are pure
    # deltas of deliberate overrides, so we apply them as-is and never second-
    # guess a binding the user chose after upgrading.
    saved_epoch = raw.get(_DEFAULTS_EPOCH_KEY)
    is_pre_epoch = not (isinstance(saved_epoch, int) and saved_epoch >= KEYMAP_DEFAULTS_EPOCH)
    legacy_rebindings = {
        # NOTE: edit.find is handled separately by the 0.8.0 beta force below,
        # which overwrites *any* stale QUILL-key-leader Find binding with Ctrl+F
        # (several pre-release builds defaulted it to different leader chords).
        # #608: Quote Lines moves from Ctrl+Q to Ctrl+Shift+Q so Cmd+Q
        # can quit on macOS. Unquote Lines moves from Ctrl+Shift+Q to
        # Ctrl+Shift+K to stay in the home row and free Ctrl+Q entirely.
        # Rewrite the prior pair on load for users who saved them.
        "edit.quote_lines": ("Ctrl+Q", "Ctrl+Shift+Q"),
        # Two hops now (#608, then the 2026-09-18 blockquote merge): a saved
        # Ctrl+Shift+Q or Ctrl+Shift+K both mean "wherever Unquote Lines lives",
        # and it lives on Ctrl+Alt+Shift+Q since Duplicate Selection took
        # Ctrl+Alt+Q and lowercase took Ctrl+Shift+K (bad.md P2.5, P1.1).
        "edit.unquote_lines": ("Ctrl+Shift+K", "Ctrl+Alt+Shift+Q"),
        # window.next_document / previous_document: Ctrl+Tab restored as default
        # in #190; no cross-platform legacy rebinding needed (the macOS-only
        # rewrite lives in the darwin block below).
        # Three chords in three days (bad.md P1.10 then P1.15): Alt+Shift+B
        # went to the status-bar switch, Word's Ctrl+Shift+F5 was promoted in
        # its place, and QUILL Lite's Alt+Shift+G became the primary two days
        # later. A saved Alt+Shift+B follows the command rather than colliding
        # with the switch that now owns it; Ctrl+Shift+F5 needs no hop because
        # it is still a live alias.
        "navigate.list_bookmarks": ("ALT+SHIFT+B", "Alt+Shift+G"),
        "view.send_to_tray": ("CTRL+ALT+T", "Ctrl+Shift+Grave, T"),
        "view.toggle_tab_control": ("CTRL+ALT+SHIFT+T", "Ctrl+Shift+Grave, Shift+T"),
        "navigate.heading_organizer": ("CTRL+ALT+SHIFT+H", "Ctrl+Shift+Grave, O"),
        "tools.read_aloud_start_pause": ("CTRL+ALT+P", "Ctrl+Shift+Grave, R"),
        "tools.read_aloud_stop": ("CTRL+ALT+S", "Ctrl+Shift+Grave, Shift+R"),
        "tools.dictation_toggle": ("CTRL+ALT+V", "Ctrl+Shift+Grave, D"),
        "edit.toggle_extend_selection_mode": ("F8", ""),
        "edit.copy_selection_for_email": ("CTRL+ALT+C", "Ctrl+Shift+Grave, C"),
        "tools.sticky_note_capture": ("CTRL+ALT+SHIFT+N", "Ctrl+Shift+Grave, Shift+N"),
        "view.browser_preview": ("CTRL+ALT+SHIFT+V", "Ctrl+Shift+Grave, V"),
        "format.list_manager": ("CTRL+ALT+L", "Ctrl+Shift+Grave, L"),
        "format.heading_1": ("CTRL+SHIFT+GRAVE, 1", "Ctrl+Alt+1"),
        "format.heading_2": ("CTRL+SHIFT+GRAVE, 2", "Ctrl+Alt+2"),
        "format.heading_3": ("CTRL+SHIFT+GRAVE, 3", "Ctrl+Alt+3"),
        "format.heading_4": ("CTRL+SHIFT+GRAVE, 4", "Ctrl+Alt+4"),
        "format.heading_5": ("CTRL+SHIFT+GRAVE, 5", "Ctrl+Alt+5"),
        "format.heading_6": ("CTRL+SHIFT+GRAVE, 6", "Ctrl+Alt+6"),
        "format.insert_html_tag": ("CTRL+ALT+H", "Ctrl+Shift+Grave, H"),
        "format.insert_markdown_tag": ("CTRL+ALT+M", "Ctrl+Shift+Grave, M"),
        "format.insert_snippet": ("CTRL+ALT+SPACE", "Ctrl+Shift+Grave, S"),
        "format.manage_snippets": ("CTRL+ALT+SHIFT+SPACE", "Ctrl+Shift+Grave, Shift+S"),
        "format.expand_abbreviation": ("", "Ctrl+Shift+Grave, A"),
        "format.manage_abbreviations": ("", "Ctrl+Shift+Grave, Shift+A"),
        "format.quick_insert": ("", ""),
        "format.new_abbreviation_from_clipboard": ("", ""),
        "format.toggle_abbreviation_expansion": ("", "Ctrl+Shift+Grave, E"),
        # PR1 (EdSharp port): users from any pre-0.7.0 build who had the old
        # Alt+Shift+Up/Down expand/shrink selection bindings saved in their
        # keymap are migrated to the new QUILL-key chord home for those
        # commands.  The new format.move_section_up/down defaults take the
        # Alt+Shift+Up/Down slot.
        "edit.expand_selection": ("ALT+SHIFT+UP", "Ctrl+Shift+Grave, J"),
        "edit.shrink_selection": ("ALT+SHIFT+DOWN", "Ctrl+Shift+Grave, Shift+J"),
        # Structured List Studio claims F2; migrate a saved F2 special-character
        # binding to its new Shift+F2 home so the muscle-memory pair stays intact.
        "power.insert_special_character": ("F2", "Shift+F2"),
    }
    # #609: on macOS, a user who saved Alt+Left / Alt+Right for
    # back/forward location on a pre-#609 build has a saved entry that
    # now collides with the system word-by-word shortcut. Rewrite it to
    # the new macOS chord (Cmd+[ / Cmd+]) on first load.
    if sys.platform == "darwin":
        legacy_rebindings["navigate.back_location"] = ("Alt+Left", "Cmd+[")
        legacy_rebindings["navigate.forward_location"] = ("Alt+Right", "Cmd+]")
        # A macOS user who saved the pre-Mac-fix Ctrl+Tab / Ctrl+Shift+Tab
        # document-switch bindings has an entry that can never fire (Ctrl+Tab
        # maps to Cmd+Tab, the reserved App Switcher shortcut). Rewrite it to
        # the new macOS chord on first load.
        legacy_rebindings["window.next_document"] = ("Ctrl+Tab", "Cmd+Shift+]")
        legacy_rebindings["window.previous_document"] = ("Ctrl+Shift+Tab", "Cmd+Shift+[")
    for command_id, binding in raw.items():
        if isinstance(command_id, str) and isinstance(binding, str):
            # Reserved metadata keys (e.g. the epoch stamp) are not bindings.
            if command_id.startswith("_"):
                continue
            # A binding for a command id this build does not ship is PRESERVED,
            # not dropped. The shared %APPDATA%\Quill\keymap.json is read and
            # rewritten by several apps of possibly different vintages (QUILL,
            # Quill Radio, QUILL Cast, Audio Studio); a command absent from this
            # build's DEFAULT_KEYMAP may be one a newer sibling app added, so
            # dropping it would silently discard that sibling's binding on this
            # build's next rewrite (the same multi-vintage hazard the settings
            # store guards against). A binding for a genuinely-retired command is
            # inert -- nothing in this build can trigger it -- so carrying it
            # forward is harmless. It still passes the empty-binding and chord-
            # conflict checks below like any other entry, and _keymap_overrides
            # carries it into the saved delta so the rewrite keeps it.
            normalized = binding
            if is_pre_epoch:
                legacy_binding = legacy_rebindings.get(command_id)
                if (
                    legacy_binding is not None
                    and normalized.strip().upper() == legacy_binding[0].upper()
                ):  # noqa: E501
                    normalized = legacy_binding[1]
                # Find must be the conventional Ctrl+F. Several pre-release
                # builds defaulted edit.find to a QUILL-key leader chord
                # ("Ctrl+Shift+Grave, <key>"); overwrite any such legacy
                # binding so upgraders are not stranded with Find unreachable.
                if command_id == "edit.find" and normalized.strip().upper().startswith(
                    _QUILL_LEADER_PREFIX
                ):
                    normalized = DEFAULT_KEYMAP["edit.find"]
            # An empty binding needs care: in a current-epoch delta it is a
            # deliberately CLEARED binding, not an absent one. The file is a
            # delta, so a command the user never touched is simply absent (it
            # keeps its DEFAULT_KEYMAP value copied into ``merged`` above); a
            # command that appears with "" was explicitly unbound in the editor
            # and must STAY unbound, or the next launch silently restores the
            # default chord and drops the user's reassignment. Persist the
            # unbind only when the command actually has a non-empty default to
            # override; a pre-epoch (legacy full-snapshot) file is still treated
            # as "use default" so a newly-added default can reach upgraders.
            if not normalized.strip():
                if not is_pre_epoch and DEFAULT_KEYMAP.get(command_id, "").strip():
                    merged[command_id] = ""
                    chosen.add(command_id)
                continue
            conflict = find_keymap_conflict(merged, command_id, normalized)
            if conflict is None:
                merged[command_id] = normalized
                chosen.add(command_id)
                continue
            # A conflict, and who wins depends on what the other side is.
            #
            # **A default loses to an explicit choice.** Bind Ctrl+Alt+Shift+J
            # yourself, upgrade to a build where that chord became some other
            # command's *default*, and the old behaviour dropped your binding
            # on the floor -- silently, at a debug log level nobody reads, so
            # the key you deliberately chose simply stopped working and the
            # reason was invisible. An explicit choice is the more recent and
            # the more specific of the two; the new default is the app's
            # suggestion, and a suggestion does not outrank an instruction. The
            # default holder is left *unbound* rather than given something else:
            # inventing a replacement chord is how a second surprise happens,
            # and the Keyboard Manager's audit reports an unbound command.
            #
            # **Only for a current-epoch file**, and that qualifier is the whole
            # of the rule's safety. A pre-epoch file is a full *snapshot*, not a
            # delta: every command in it is present whether or not the user ever
            # touched it, so "they chose this" is false for almost all of it.
            # Applying the rule there would let yesterday's default beat today's
            # -- which is exactly the migration this loop exists to perform, run
            # backwards. (Caught by
            # test_legacy_preview_conflict_migrates_to_in_app_preview, where a
            # legacy snapshot's stale Ctrl+Shift+P for view.preview would
            # otherwise have taken the Command Palette's key.)
            #
            # **Two explicit choices are left as they are.** If the other side
            # is also something this user set, there is nothing to choose
            # between them from here, so the first one read keeps the chord and
            # the second is dropped -- the older behaviour, now the only case it
            # still applies to.
            if is_pre_epoch or conflict in chosen:
                logger.warning(
                    "Dropping keymap entry for %r: %r is already %r's",
                    command_id,
                    normalized,
                    conflict,
                )
                continue
            logger.info(
                "Keeping your %r binding for %r; %r had it as a default and is now unbound",
                normalized,
                command_id,
                conflict,
            )
            merged[conflict] = ""
            merged[command_id] = normalized
            chosen.add(command_id)
    return merged


def export_keymap(target: Path, keymap: dict[str, str]) -> None:
    write_json_atomic(target, keymap)


def import_keymap(source: Path) -> dict[str, str]:
    raw = read_json(source, default={})
    merged = merge_keymaps(raw)
    save_keymap(merged)
    return merged


KQP_EXTENSION = ".kqp"
_KQP_VERSION = 1


def export_keyboard_pack(
    target: Path,
    keymap: dict[str, str],
    name: str,
    description: str,
    author: str = "",
    version: str = "1.0",
) -> None:
    """Write a .kqp (Keyboard Quill Pack) file.

    Only bindings that differ from DEFAULT_KEYMAP are stored so the file
    captures intent rather than a snapshot of defaults that may change.
    """
    delta: dict[str, str] = {k: v for k, v in keymap.items() if v != DEFAULT_KEYMAP.get(k)}
    payload: dict[str, object] = {
        "kqp_version": _KQP_VERSION,
        "name": name.strip(),
        "description": description.strip(),
        "author": author.strip(),
        "version": version.strip(),
        "bindings": delta,
    }
    write_json_atomic(target, payload)


def import_keyboard_pack(source: Path) -> tuple[str, str, dict[str, str]]:
    """Read a .kqp file. Return (name, description, merged_keymap).

    Raises ValueError if the file is missing, malformed, uses an unsupported
    kqp_version, or fails the kqp validator.  The merged keymap is persisted
    via save_keymap *only* after validation succeeds (finding #42: a bad
    pack must never silently overwrite the user's bindings).
    """
    raw = read_json(source, default=None)
    if not isinstance(raw, dict):
        raise ValueError(f"{source.name} is not a valid Keyboard Quill Pack (expected JSON object)")
    file_version = raw.get("kqp_version")
    if file_version != _KQP_VERSION:
        raise ValueError(
            f"{source.name}: unsupported kqp_version {file_version!r} "
            f"(this build supports version {_KQP_VERSION})"
        )
    name = str(raw.get("name", source.stem)) or source.stem
    description = str(raw.get("description", ""))
    bindings = raw.get("bindings", {})
    if not isinstance(bindings, dict):
        raise ValueError(f"{source.name}: 'bindings' must be a JSON object")
    # Re-write the parsed payload to a temp buffer and run the same validator
    # the standalone ``quill.tools.kqp_validator`` runs, so the import path
    # uses the same rules as the CLI.
    from quill.tools.kqp_validator import validate_file  # local import: avoid cycles

    issues = validate_file(source, strict=False)
    if issues:
        joined = "; ".join(issues)
        raise ValueError(f"{source.name} failed keyboard pack validation: {joined}")
    merged = merge_keymaps(bindings)
    save_keymap(merged)
    return name, description, merged


def reset_keymap() -> dict[str, str]:
    defaults = DEFAULT_KEYMAP.copy()
    save_keymap(defaults)
    return defaults


def find_keymap_conflict(
    keymap: dict[str, str],
    command_id: str,
    binding: str,
    *,
    quill_key_prefix: str | None = None,
) -> str | None:
    """Return the first other command bound to ``binding``, or None.

    Delegates to :func:`quill.core.keymap_query.find_keymap_conflicts`, so the
    comparison is canonical: a re-ordered or alias spelling ("Shift+Ctrl+K",
    "control+shift+k") conflicts with a stored "Ctrl+Shift+K". Kept as a
    first-match convenience wrapper for the editor's existing call site.
    """
    conflicts = find_keymap_conflicts(
        keymap, command_id, binding, quill_key_prefix=quill_key_prefix
    )
    return conflicts[0] if conflicts else None


# The profile loader lives in keymap_profiles -- a separate concern, extracted
# rather than grown (GATE-11). At the bottom: it reads DEFAULT_KEYMAP.
from quill.core.keymap_profiles import (  # noqa: E402
    list_keymap_profiles,
    load_keymap_profile,
)
