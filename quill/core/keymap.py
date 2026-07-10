from __future__ import annotations

import logging
import sys
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
    "file.open": "Ctrl+O",
    "file.save": "Ctrl+S",
    "file.save_as": "Ctrl+Shift+S",
    "file.open_from_remote": "Ctrl+Shift+Grave, Shift+O",  # QUILL-key chord (R taken by read-aloud)
    "file.save_to_remote": "Ctrl+Shift+Grave, W",  # QUILL-key chord
    "file.manage_remote_sites": "Ctrl+Shift+Grave, Shift+M",  # QUILL-key chord
    "file.close_document": "Ctrl+W",
    "file.print": "Ctrl+P",
    # Restore points: no default key (assignable); the File menu item is the
    # primary path.
    "file.restore_previous_version": "",
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
    "view.toggle_soft_wrap": "Alt+Z",
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
    "navigate.go_to_page": "Ctrl+Shift+G",
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
    "navigate.heading_organizer": "Ctrl+Shift+Grave, O",
    "navigate.list_bookmarks": "Alt+Shift+B",
    "tools.ask_quill_chat": "Alt+Q",
    "tools.word_count": "Ctrl+Shift+W",
    "tools.spell_check_dialog": "F7",
    "tools.next_misspelling": "Ctrl+F7",
    "tools.previous_misspelling": "Ctrl+Shift+F7",
    "tools.misspelling_list": "Alt+Shift+L",
    "tools.thesaurus": "Shift+F7",
    # Inline notes (sticky, content-anchored annotations).
    "notes.add_inline_note": "Alt+Shift+I",
    "notes.next_inline_note": "Alt+Shift+J",
    "notes.previous_inline_note": "Alt+Shift+G",
    "notes.speak_inline_note": "Alt+Shift+H",
    "tools.read_aloud_start_pause": "Ctrl+Shift+Grave, R",  # §10.8.2: P→R
    "tools.read_aloud_stop": "Ctrl+Shift+Grave, Shift+R",  # §10.8.2: Shift+P→Shift+R
    "tools.dictation_toggle": "Ctrl+Shift+Grave, D",
    "tools.speech_dictate": "Ctrl+Shift+Grave, Shift+D",
    "tools.speech_batch_export": "Ctrl+Shift+Grave, Y",  # Audio Studio
    # Locked Dictation (offline Whisper). All remappable; the
    # these are matched in the editor key handlers rather than the accelerator
    # table (no menu accelerators) so Escape can be consumed only while recording.
    "tools.dictation_lock_toggle": "Ctrl+F9",
    "tools.dictation_pause": "Ctrl+Shift+F9",
    "tools.dictation_status": "Alt+F9",
    "tools.dictation_emergency_stop": "Escape",  # consumed only while recording
    "tools.dictation_cancel": "Shift+Escape",  # consumed only while recording
    "tools.describe_image": "Ctrl+Shift+Grave, I",
    "tools.document_intake_report": "Ctrl+Shift+I",
    # #357 keymap consolidation: AI commands move from inline F7/Shift+F7/F8/
    # Shift+F8/Ctrl+Shift+T accelerators (which collided with the selection
    # bindings at F8/Shift+F8/Ctrl+F8) to Ctrl+Alt+Shift+ chords, matching
    # the EdSharp port convention. The chord class is reserved for AI so
    # power users can find them by feel. Justifications name the screen-
    # reader binding each chord displaces (NVDA review-cursor for the
    # chord class; F7/F8 selection-start/complete for the displaced
    # inline accelerators).
    "tools.ai_spell_check": "Ctrl+Alt+Shift+S",  # §edsharp-ok — AI reserved chord class
    "tools.ai_spell_check_interactive": "Ctrl+Alt+Shift+I",  # §edsharp-ok — AI reserved chord class
    "tools.ai_grammar_style": "Ctrl+Alt+Shift+G",  # §edsharp-ok — AI reserved chord class
    "tools.ai_translate_selection": "Ctrl+Alt+Shift+T",  # §edsharp-ok — AI reserved chord class
    "tools.ai_thesaurus": "Ctrl+Alt+Shift+H",  # §edsharp-ok — AI reserved chord class
    "tools.ai_switch_engine": "Ctrl+Alt+Shift+E",  # §edsharp-ok — AI reserved chord class
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
    "edit.copy_with_source": "Ctrl+Shift+C",
    "edit.copy_selection_for_email": "Ctrl+Shift+Grave, C",
    "edit.undo": "Ctrl+Z",
    "edit.redo": "Ctrl+Y",
    "edit.toggle_extend_selection_mode": "",  # no default binding; assign via keymap editor
    "edit.start_selection": "F8",
    "edit.complete_selection": "Shift+F8",
    "edit.reselect": "Ctrl+Shift+F8",
    "edit.go_to_start_of_selection": "Alt+Shift+F8",
    "edit.copy_all": "Ctrl+F8",
    "edit.unselect_all": "Ctrl+Shift+A",
    "edit.say_selected": "",  # Shift+Space — conditional intercept in _on_editor_key_down
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
    "tools.search_in_files": "Ctrl+Shift+F",
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
    "edit.replace_all": "Ctrl+Shift+H",
    "edit.insert_link": "Ctrl+K",
    "edit.follow_link": "Ctrl+Enter",
    "edit.word_prediction": "Ctrl+.",  # freed Ctrl+Space for select_chunk (§4.22)
    # Ctrl+Space becomes Cmd+Space on macOS (Spotlight) -- dead by default. The
    # darwin alternate Cmd+Alt+Space avoids the system shortcuts (#32).
    "edit.select_chunk": "Cmd+Alt+Space"
    if sys.platform == "darwin"
    else "Ctrl+Space",  # §4.22 advanced-editor parity
    "view.preview": "Ctrl+Shift+V",
    "view.browser_preview": "Ctrl+Shift+Grave, V",  # §10.8.2: QUILL-key chord
    "view.split_preview": "Ctrl+Shift+Backslash",
    "view.focus_preview": "Ctrl+F6",
    "view.switch_editing_lens": "Ctrl+Shift+Grave, K",
    "edit.set_mark": "Ctrl+Shift+M",
    # Ctrl+M becomes Cmd+M on macOS (system Minimize) -- dead by default. The
    # darwin alternate Cmd+Alt+M avoids Minimize (#31).
    "edit.pop_mark": "Cmd+Alt+M" if sys.platform == "darwin" else "Ctrl+M",
    "edit.exchange_point_mark": "Ctrl+Shift+X",
    "edit.list_marks": "Alt+M",
    "edit.select_paragraph": "",  # Ctrl+Alt+P removed (§10.8 screen-reader-hostile)
    "edit.select_block": "Ctrl+Shift+B",
    # PR1 (EdSharp port): section move takes the Alt+Shift+Up/Down slot. The
    # previous expand/shrink selection pair migrates to the QUILL-key chord.
    # J and Shift+J were free in the QUILL-key second-key space (verified
    # against DEFAULT_KEYMAP and both profile JSONs); they sit adjacent to
    # the existing I/H/G group of navigate/contrast/chord-prefix neighbours.
    "edit.expand_selection": "Ctrl+Shift+Grave, J",  # was Alt+Shift+Up (§edsharp-ok)
    "edit.shrink_selection": "Ctrl+Shift+Grave, Shift+J",  # was Alt+Shift+Down (§edsharp-ok)
    "format.move_section_up": "Alt+Shift+Up",  # §edsharp-ok — markdown/html only
    "format.move_section_down": "Alt+Shift+Down",  # §edsharp-ok — markdown/html only
    "edit.set_named_mark": "",
    "edit.jump_to_named_mark": "",
    "edit.open_review_buffer": "",
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
    "edit.unquote_lines": "Ctrl+Shift+K",  # §4.22 advanced-editor parity; #608
    "edit.duplicate_selection": "",  # §4.17; no default key to avoid Ctrl+D clash
    "edit.reverse_lines": "Alt+Shift+Z",  # §4.22 advanced-editor parity
    "format.toggle_line_comment": "Ctrl+/",
    "format.toggle_block_comment": "Shift+Alt+A",
    "format.indent": "Ctrl+]",
    "format.outdent": "Ctrl+[",
    # Toggle the Tab key between smart indent and literal tab insertion.
    # Bound to a QUILL-key chord: plain Ctrl+M / Ctrl+Shift+M are the mark ring,
    # and Ctrl+Alt+ chords are screen-reader-hostile (§10.8), so neither is usable.
    "format.toggle_tab_insert_mode": "Ctrl+Shift+Grave, U",
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
    "format.toggle_bullet_list": "Ctrl+Alt+7",  # §edsharp-ok — overrides NVDA review-cursor
    "format.toggle_numbered_list": "Ctrl+Alt+8",  # §edsharp-ok — overrides NVDA review-cursor
    "format.insert_html_tag": "Ctrl+Shift+Grave, H",
    "format.insert_markdown_tag": "",  # M is reserved for paste-HTML-as-Markdown
    "power.paste_html_as_markdown": "Ctrl+Shift+Grave, M",
    "power.non_ascii_jump_to_source": "",  # assign via Keymap Editor; use from Non-ASCII report
    "power.non_ascii_jump_to_report": "",  # assign via Keymap Editor; jump back to report
    "power.open_snippet_gallery": "Ctrl+Shift+Grave, Shift+G",
    "format.insert_snippet": "Ctrl+Shift+Grave, S",
    "format.manage_snippets": "Ctrl+Shift+Grave, Shift+S",
    "format.expand_abbreviation": "Ctrl+Shift+Grave, A",
    "format.manage_abbreviations": "Ctrl+Shift+Grave, Shift+A",
    "format.toggle_abbreviation_expansion": "Ctrl+Shift+Grave, E",
    # Structured List Studio takes the primary F2 slot (its PRD names F2 the
    # primary command); Insert Special Character moves to the adjacent Shift+F2.
    "format.list_studio": "F2",
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
    "vault.publish_note": "",
    "power.insert_special_character": "Shift+F2",  # §4.22 parity; F2 -> List Studio
    "power.number_lines": "Alt+Shift+N",  # §4.22 Number Items parity
    "power.trim_blank_lines": "Ctrl+Shift+Enter",  # §4.22 Trim Blanks parity
    "power.keep_unique_lines": "Alt+Shift+K",  # §4.22 Keep Unique parity
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
    "document.summary": "Alt+I",
    # §8.2 — universal "Go to anything" palette (Quill+G).
    "navigate.go_to_anything": "Ctrl+Shift+Grave, G",
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
    # §10.8 — magic paste moves to QUILL key, V (handled in QuillKeyMixin prefix
    # state machine).  Ctrl+Alt+V removed — screen readers eat Ctrl+Alt+ chords.
    "edit.magic_paste": "",
    # §CopyTray — Copy Tray slot access (12 slots).
    # Paste: Ctrl+Shift+N for N=1-9, Ctrl+Shift+0 for slot 10,
    #        Ctrl+Shift+- for slot 11, Ctrl+Shift+= for slot 12.
    # Copy:  QUILL+Shift+N for same key positions (Shift+digit/symbol).
    # QUILL+1-6 (bare) are heading shortcuts; Shift variants are distinct.
    # Open tray dialog: QUILL+X.
    "edit.open_copy_tray": "Ctrl+Shift+Grave, X",
    "edit.clear_all_tray_slots": "",
    "edit.copy_to_next_slot": "",
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
    "edit.paste_from_tray_1": "Ctrl+Shift+1",
    "edit.paste_from_tray_2": "Ctrl+Shift+2",
    "edit.paste_from_tray_3": "Ctrl+Shift+3",
    "edit.paste_from_tray_4": "Ctrl+Shift+4",
    "edit.paste_from_tray_5": "Ctrl+Shift+5",
    "edit.paste_from_tray_6": "Ctrl+Shift+6",
    "edit.paste_from_tray_7": "Ctrl+Shift+7",
    "edit.paste_from_tray_8": "Ctrl+Shift+8",
    "edit.paste_from_tray_9": "Ctrl+Shift+9",
    "edit.paste_from_tray_10": "Ctrl+Shift+0",
    "edit.paste_from_tray_11": "Ctrl+Shift+-",
    "edit.paste_from_tray_12": "Ctrl+Shift+=",
}


_PROFILES_DIR = Path(__file__).resolve().parent / "keymap"

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
    """Return only the entries of *merged* that differ from DEFAULT_KEYMAP.

    This is the delta persisted to disk: omitting defaults is what lets a
    later DEFAULT_KEYMAP change reach the user automatically (see
    ``KEYMAP_DEFAULTS_EPOCH``).
    """
    return {
        command_id: chord
        for command_id, chord in merged.items()
        if command_id in DEFAULT_KEYMAP and chord != DEFAULT_KEYMAP[command_id]
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


def load_keymap_profile(name: str) -> dict[str, str]:
    """Return the merged keymap for a named JSON profile in quill/core/keymap/.

    Falls back to DEFAULT_KEYMAP if the profile file is not found.
    Profile names map to ``profile_<name>.json``; spaces are replaced with
    underscores and the string is lower-cased.  Example: ``"Minimal"``
    loads ``profile_minimal.json``.
    """
    slug = name.lower().replace(" ", "_")
    profile_path = _PROFILES_DIR / f"profile_{slug}.json"
    data = read_json(profile_path, default={})
    if not isinstance(data, dict):
        return DEFAULT_KEYMAP.copy()
    bindings = data.get("bindings", {})
    if not isinstance(bindings, dict):
        return DEFAULT_KEYMAP.copy()
    merged = DEFAULT_KEYMAP.copy()
    merged.update({k: v for k, v in bindings.items() if isinstance(v, str)})
    return merged


def list_keymap_profiles() -> list[str]:
    """Return the display names of available JSON profiles."""
    profiles: list[str] = []
    if not _PROFILES_DIR.is_dir():
        return profiles
    for path in sorted(_PROFILES_DIR.glob("profile_*.json")):
        data = read_json(path, default={})
        if isinstance(data, dict) and "_name" in data:
            profiles.append(str(data["_name"]))
        else:
            logger.debug("Dropping malformed keymap profile: %s", path.name)
    return profiles


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
    merged.update(pack.bindings)
    return merged


def merge_keymaps(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return DEFAULT_KEYMAP.copy()
    merged = DEFAULT_KEYMAP.copy()
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
        "edit.unquote_lines": ("Ctrl+Shift+Q", "Ctrl+Shift+K"),
        # window.next_document / previous_document: Ctrl+Tab restored as default
        # in #190; no cross-platform legacy rebinding needed (the macOS-only
        # rewrite lives in the darwin block below).
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
            # A binding for a command id that no longer ships in DEFAULT_KEYMAP
            # is no longer valid; drop it so the default (which is to omit it)
            # takes effect.
            if command_id not in DEFAULT_KEYMAP:
                logger.debug("Dropping keymap entry for unknown command: %r", command_id)
                continue
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
            # An empty binding means "use the default" — drop it so the
            # default in DEFAULT_KEYMAP takes effect (do not store "" on top).
            if not normalized.strip():
                continue
            conflict = find_keymap_conflict(merged, command_id, normalized)
            if conflict is None:
                merged[command_id] = normalized
            else:
                logger.debug(
                    "Dropping keymap entry for %r: chord %r already taken by %r",
                    command_id,
                    normalized,
                    conflict,
                )
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
