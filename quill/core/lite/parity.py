"""Where the two editors' vocabularies are written down, once.

The same concept is spelled two ways in several settings, the same verb has two
command ids, and the same announcement had two shapes. None of those is a bug on
its own; together they are **the mechanism by which the two editors drift**,
because there was no place where a name got decided once (bad.md 7.7).

This module is that place. Today it holds the **settings** half:
:data:`SETTINGS_ALIASES` maps QuillLite's field name to QUILL's, for every
concept both products store under different names (bad.md G1). It is what
"Bring my QuillLite settings" reads when somebody grows up into QUILL (5.8),
and what the settings-vocabulary gate checks a new field against.

The **command** half belongs here too and is not written yet: the family parity
gate (§9 item 1, bad.md P1.15) needs a QuillLite-handler-to-QUILL-command-id
table so the two can be asserted to resolve to the same chord. The mapping
exists today inside ``tests/unit/core/lite/test_lite_selection.py``, covering
the selection family only; moving it here and completing it is P1.15's job, and
:data:`DIVERGENCES` is waiting for it.

**Why a mapping and not a rename.** Both tables could be emptied by renaming
one side, and both sides' names are already on disk in people's settings files
and keymap overrides. A rename is a migration for every existing user, in
exchange for a tidiness nobody can see. The mapping costs one row and is
checkable, which is the thing the rename was supposed to buy.

**The table is the review.** A new shared concept that lands under a second
name fails the gate until somebody either picks the existing name or writes the
row -- and writing the row is where they have to say, in words, why two names
are right.
"""

from __future__ import annotations

__all__ = [
    "COMMAND_EQUIVALENTS",
    "DIVERGENCES",
    "LITE_ONLY",
    "NATIVE_IN_BOTH",
    "SETTINGS_ALIASES",
    "quill_setting_for",
]

#: QuillLite's field name -> QUILL's, for one concept stored under two names.
#:
#: Five rows, and each one is a concept a person would describe with the same
#: sentence in either product (bad.md G1). Three more pairs the audit named have
#: since converged on one name and are deliberately absent: ``font_name``,
#: ``font_size`` and ``show_status_bar`` are spelled identically in both.
SETTINGS_ALIASES: dict[str, str] = {
    # "How often it saves a copy of unsaved work." QuillLite's name is the
    # shorter and the clearer of the two; QUILL's says "interval" twice.
    "autosave_seconds": "autosave_interval_seconds",
    # "Whether long lines wrap to the window." Notepad, WordPad and Word all
    # call this Word Wrap, which is QuillLite's name and the one the menus in
    # both products show -- QUILL's field is the outlier, not its label.
    "word_wrap": "soft_wrap",
    # "Whether it checks spelling as you type."
    "spell_check_while_typing": "spellcheck_as_you_type",
    # "What kind of document a new one is." Not quite the same shape -- Lite's
    # is plain/rich, QUILL's names a format -- which is why 5.8's importer has
    # to translate rather than copy, and why this row exists.
    "default_mode": "default_new_document_format",
    # "Whether it looks for a new version by itself." A fifth pair the G1 audit
    # missed, found by this table's own gate on 2026-09-17: neither name
    # contains a word the other does, so no amount of eyeballing the two field
    # lists finds it. That is the argument for the gate.
    "check_updates_on_launch": "auto_check_updates",
}

#: Pairs that look like the same concept and are not, recorded so nobody adds
#: them to the table above by pattern-matching on the name.
#:
#: ``recent_files`` / ``recent_files_limit`` is the one that catches people:
#: QuillLite's is **the list of files** and QUILL's is **how many to keep**. A
#: mapping between them would hand an importer a list where it expected a
#: number.
NOT_ALIASES: dict[str, str] = {
    "recent_files": "recent_files_limit",
}

#: QuillLite handlers whose chord is allowed to differ, each with its reason.
#:
#: A row here is a promise that somebody thought about it, not a place to park
#: a collision -- and the gate prints the reason when it reports the pair, so
#: the next person reads the argument rather than re-having it.
DIVERGENCES: dict[str, str] = {
    "cmd_trim_trailing_space": (
        "Ctrl+Alt+T is Insert Table in QUILL, an authorized x.md authoring "
        "chord for a verb that builds structure, deliberately kept over one "
        "that strips whitespace (decided 2026-09-16). QUILL's trim is "
        "Ctrl+Alt+R. The one row in bad.md 3.2 that does not converge."
    ),
    "cmd_toggle_fold": (
        "QUILL's folds are Ctrl+Shift+[ and ] beside its indent pair, which is "
        "where every code editor puts folding, and that freed Ctrl+Shift+F for "
        "Word's Font (bad.md 3.1). QuillLite uses the F9 row and has no font "
        "dialog to make room for."
    ),
    "cmd_next_fold": (
        "As cmd_toggle_fold: the whole fold family sits on the bracket row in "
        "QUILL, beside indent and outdent, and on the F9 row in QuillLite."
    ),
    "cmd_previous_fold": (
        "As cmd_toggle_fold: the whole fold family sits on the bracket row in "
        "QUILL, beside indent and outdent, and on the F9 row in QuillLite."
    ),
    "cmd_spelling_voice_settings": (
        "Ctrl+Alt+Shift+F7 is a QuillVille launcher in QUILL -- the six "
        "siblings sit on Ctrl+Alt+Shift+F7 through F12, and QuillLite, being "
        "the editor on its own, has none to launch. QUILL's Announcements "
        "window is one key down on Ctrl+Alt+Shift+F6: same modifiers, same "
        "finger shape, so the habit transfers even though the key cannot "
        "(bad.md P1.14)."
    ),
    "cmd_snippet_gallery": (
        "Alt+Shift+I is Add Inline Note in QUILL -- one of four note chords "
        "QuillLite does not have (bad.md 3.9) -- and a snippet gallery is a "
        "once-a-session window, so the note keeps the shorter chord (rule 3)."
    ),
    "cmd_context_help": (
        "F1 in QUILL is help.help_on_control, the same idea under another id: "
        "the command that answers 'what is this control?' owns F1 in both, and "
        "help.context_help is QUILL's second, chord-reached help window."
    ),
    "cmd_customize_features": (
        "Not the same verb: QuillLite's Customize Features toggles individual "
        "features, QUILL's Alt+Shift+P switches whole feature PROFILES. The "
        "closest QUILL command to Lite's is tools.individual_feature_toggles, "
        "which is on Ctrl+Alt+F10 -- QuillLite's chord -- and the mapping "
        "points at the profile switcher because that is the row the menus "
        "share. Reviewed 2026-09-18; left as a divergence rather than forcing "
        "two different verbs onto one key."
    ),
    # Five pairs that looked like divergences and are not: QuillLite's chord is
    # a QUILL *alias*, which is rule 5 working -- both keys reach the command
    # here. The gate said so on its first run and they were deleted from this
    # table (cmd_list_headings, cmd_insert_html_tag, cmd_manage_abbreviations,
    # cmd_shortcuts, cmd_next_window_mdi).
}


#: QuillLite handler -> the QUILL command id that means the same thing.
#:
#: 186 rows, and the table IS the review (bad.md P1.15): a new QuillLite command
#: fails the family parity gate until somebody writes its row, and writing the
#: row is where they have to decide whether QUILL has that verb at all. Three
#: things fell out of building it -- five chords that had drifted (the heading
#: organiser, the tab-mode toggle, Expand Abbreviations, the bookmark list and
#: block comment), and four QuillLite verbs QUILL simply does not have.
COMMAND_EQUIVALENTS: dict[str, str] = {
    "cmd_about": "help.about_quill",
    "cmd_add_word_to_dictionary": "tools.add_word_to_dictionary",
    "cmd_align_center": "format.align_center",
    "cmd_align_justify": "format.justify",
    "cmd_align_left": "format.align_left",
    "cmd_align_right": "format.align_right",
    "cmd_back_location": "navigate.back_location",
    "cmd_backup_settings": "tools.share_export",
    "cmd_bold": "format.bold",
    "cmd_browse_backups": "file.restore_previous_version",
    "cmd_check_updates": "tools.check_updates",
    "cmd_clear_bookmarks": "navigate.clear_numbered_bookmarks",
    "cmd_clear_copy_tray": "edit.clear_all_tray_slots",
    "cmd_close": "file.close_document",
    "cmd_collect_selection": "power.toggle_clipboard_collector",
    "cmd_command_palette": "app.command_palette",
    "cmd_complete_selection": "edit.complete_selection",
    "cmd_context_help": "help.context_help",
    "cmd_copy_all": "edit.copy_all",
    "cmd_copy_to_tray": "edit.copy_to_next_slot",
    "cmd_copy_to_tray_slot": "edit.copy_to_tray_slot",
    "cmd_count_occurrences": "power.count_occurrences",
    "cmd_customize_features": "help.switch_feature_profile",
    "cmd_cycle_list_style": "format.toggle_bullet_list",
    "cmd_delete_line": "format.delete_line",
    "cmd_delete_lines_containing": "power.delete_lines_containing",
    "cmd_delete_paragraph": "power.delete_paragraph",
    "cmd_delete_to_line_end": "power.delete_to_line_end",
    "cmd_delete_to_line_start": "power.delete_to_line_start",
    "cmd_demote_heading": "format.increase_heading_level",
    "cmd_describe": "format.describe_formatting",
    "cmd_describe_character": "power.describe_character",
    "cmd_describe_character_detail": "power.describe_character_detail",
    "cmd_describe_indent": "format.describe_indent_depth",
    "cmd_duplicate_line": "format.duplicate_line",
    "cmd_duplicate_selection": "edit.duplicate_selection",
    "cmd_editor_font": "format.editor_font",
    "cmd_exchange_point_mark": "edit.exchange_point_mark",
    "cmd_exit": "app.exit",
    "cmd_expand_selection": "edit.expand_selection",
    "cmd_file_format": "file.file_format",
    "cmd_find": "edit.find",
    "cmd_find_all": "edit.find_all_matches",
    "cmd_find_next": "edit.find_next",
    "cmd_find_previous": "edit.find_previous",
    "cmd_focus_status_bar": "navigate.next_region",
    "cmd_forward_location": "navigate.forward_location",
    "cmd_get_help_from_support": "help.report_bug",
    "cmd_go_to_anything": "navigate.go_to_anything",
    "cmd_go_to_selection_start": "edit.go_to_start_of_selection",
    "cmd_go_to_temp_bookmark": "navigate.go_to_temp_bookmark",
    "cmd_goto_line": "navigate.go_to_line",
    "cmd_grow_font": "format.grow_font",
    "cmd_hard_wrap": "power.hard_wrap_lines",
    "cmd_heading_0": "format.body_text",
    "cmd_heading_1": "format.heading_1",
    "cmd_heading_2": "format.heading_2",
    "cmd_heading_3": "format.heading_3",
    "cmd_heading_4": "format.heading_4",
    "cmd_heading_5": "format.heading_5",
    "cmd_heading_6": "format.heading_6",
    "cmd_heading_organizer": "navigate.heading_organizer",
    "cmd_indent": "format.indent",
    "cmd_indentation_to_spaces": "edit.convert_indentation_to_spaces",
    "cmd_indentation_to_tabs": "edit.convert_indentation_to_tabs",
    "cmd_insert_datetime": "edit.insert_date_time",
    "cmd_insert_emoji": "edit.insert_emoji",
    "cmd_insert_html_tag": "format.insert_html_tag",
    "cmd_insert_line_break": "power.insert_line_break",
    "cmd_insert_link": "edit.insert_link",
    "cmd_insert_markdown_tag": "format.insert_markdown_tag",
    "cmd_insert_special_character": "power.insert_special_character",
    "cmd_italic": "format.italic",
    "cmd_join_lines": "format.join_lines",
    "cmd_keyboard_manager": "tools.keymap_editor",
    "cmd_line_statistics": "power.compute_line_statistics",
    "cmd_list_bookmarks": "navigate.list_bookmarks",
    "cmd_list_headings": "navigate.outline_navigator",
    "cmd_list_marks": "edit.list_marks",
    "cmd_lower_case": "format.lower_case",
    "cmd_manage_abbreviations": "format.manage_abbreviations",
    "cmd_misspelling_list": "tools.misspelling_list",
    "cmd_move_line_down": "format.move_line_down",
    "cmd_move_line_up": "format.move_line_up",
    "cmd_move_section_down": "format.move_section_down",
    "cmd_move_section_up": "format.move_section_up",
    "cmd_new": "file.new",
    "cmd_new_plain": "file.new_plain_text_document",
    "cmd_new_rich": "file.new_rich_document",
    "cmd_next_bookmark": "navigate.next_bookmark",
    "cmd_next_fold": "navigate.next_fold",
    "cmd_next_heading": "navigate.next_heading",
    "cmd_next_misspelling": "tools.next_misspelling",
    "cmd_next_window": "window.next_document",
    "cmd_next_window_mdi": "window.next_document",
    "cmd_normalize_whitespace": "edit.normalize_whitespace",
    "cmd_number_lines": "power.number_lines",
    "cmd_open": "file.open",
    "cmd_open_review_buffer": "edit.open_review_buffer",
    "cmd_outdent": "format.outdent",
    "cmd_page_setup": "file.page_setup",
    "cmd_paste_clip": "edit.open_clip_library",
    "cmd_paste_from_tray": "edit.open_copy_tray",
    "cmd_paste_plain": "edit.paste_plain_text",
    "cmd_pop_mark": "edit.pop_mark",
    "cmd_preferences": "app.preferences",
    "cmd_previous_bookmark": "navigate.previous_bookmark",
    "cmd_previous_fold": "navigate.previous_fold",
    "cmd_previous_heading": "navigate.previous_heading",
    "cmd_previous_misspelling": "tools.previous_misspelling",
    "cmd_previous_window": "window.previous_document",
    "cmd_print": "file.print",
    "cmd_promote_heading": "format.decrease_heading_level",
    "cmd_quote_lines": "edit.quote_lines",
    "cmd_redo": "edit.redo",
    "cmd_remember_clip": "edit.keep_selection_in_clip_library",
    "cmd_remove_blank_lines": "power.remove_blank_lines",
    "cmd_remove_duplicate_lines": "edit.remove_duplicate_lines",
    "cmd_replace": "edit.replace",
    "cmd_reselect": "edit.reselect",
    "cmd_restore_deletion": "edit.restore_deletion",
    "cmd_restore_settings": "tools.share_import",
    "cmd_reverse_lines": "edit.reverse_lines",
    "cmd_save": "file.save",
    "cmd_save_as": "file.save_as",
    "cmd_say_selection": "edit.say_selected",
    "cmd_select_block": "edit.select_block",
    "cmd_select_line": "edit.select_line",
    "cmd_select_paragraph": "edit.select_paragraph",
    "cmd_select_sentence": "edit.select_sentence",
    "cmd_select_word": "edit.select_word",
    "cmd_selection_font": "format.selection_font",
    "cmd_sentence_case": "format.sentence_case",
    "cmd_set_bookmark": "navigate.set_numbered_bookmark",
    "cmd_set_bookmark_1": "navigate.set_numbered_bookmark_1",
    "cmd_set_bookmark_2": "navigate.set_numbered_bookmark_2",
    "cmd_set_bookmark_3": "navigate.set_numbered_bookmark_3",
    "cmd_set_bookmark_4": "navigate.set_numbered_bookmark_4",
    "cmd_set_bookmark_5": "navigate.set_numbered_bookmark_5",
    "cmd_set_bookmark_6": "navigate.set_numbered_bookmark_6",
    "cmd_set_bookmark_7": "navigate.set_numbered_bookmark_7",
    "cmd_set_bookmark_8": "navigate.set_numbered_bookmark_8",
    "cmd_set_bookmark_9": "navigate.set_numbered_bookmark_9",
    "cmd_set_language": "navigate.set_language",
    "cmd_set_mark": "edit.set_mark",
    "cmd_set_temp_bookmark": "navigate.set_temp_bookmark",
    "cmd_shortcuts": "help.key_cheatsheet",
    "cmd_shrink_font": "format.shrink_font",
    "cmd_shrink_selection": "edit.shrink_selection",
    "cmd_snippet_gallery": "power.open_snippet_gallery",
    "cmd_sort_lines": "edit.sort_lines_ascending",
    "cmd_sort_lines_descending": "edit.sort_lines_descending",
    "cmd_sound_scheme": "tools.sound_events",
    "cmd_spacing_double": "format.line_spacing_double",
    "cmd_spacing_one_half": "format.line_spacing_one_and_a_half",
    "cmd_spacing_single": "format.line_spacing_single",
    "cmd_spell_review": "tools.spell_check_dialog",
    "cmd_spell_word_at_cursor": "tools.spell_check_word_at_cursor",
    "cmd_spelling_voice_settings": "tools.spelling_announcements",
    "cmd_start_selection": "edit.start_selection",
    "cmd_statistics": "tools.word_count",
    "cmd_switch_document_kind": "format.switch_document_format",
    "cmd_title_case": "format.title_case",
    "cmd_toggle_abbreviations": "format.toggle_abbreviation_expansion",
    "cmd_toggle_case": "format.toggle_case",
    "cmd_toggle_dark": "view.toggle_dark_mode",
    "cmd_toggle_extend_mode": "edit.toggle_selection_marker",
    "cmd_toggle_extend_selection_mode": "edit.toggle_extend_selection_mode",
    "cmd_toggle_fold": "edit.toggle_fold",
    "cmd_toggle_heading_announcements": "view.toggle_heading_announcements",
    "cmd_toggle_line_comment": "format.toggle_line_comment",
    "cmd_toggle_list_announcements": "view.toggle_list_announcements",
    "cmd_toggle_live_spelling": "view.toggle_spellcheck_as_you_type",
    "cmd_toggle_overwrite": "view.toggle_overwrite_mode",
    "cmd_toggle_quiet_mode": "tools.sound_toggle",
    "cmd_toggle_status_bar": "view.toggle_status_bar",
    "cmd_toggle_tab_mode": "format.toggle_tab_insert_mode",
    "cmd_toggle_wrap": "view.toggle_soft_wrap",
    "cmd_trim_trailing_space": "edit.trim_trailing_whitespace",
    "cmd_tutorials": "help.tutorials",
    "cmd_undo": "edit.undo",
    "cmd_unquote_lines": "edit.unquote_lines",
    "cmd_unselect_all": "edit.unselect_all",
    "cmd_upper_case": "format.upper_case",
    "cmd_zoom_in": "view.text_size_up",
    "cmd_zoom_out": "view.text_size_down",
    "cmd_zoom_reset": "view.text_size_reset",
}

#: Handlers with no QUILL command id because the *control* answers the key.
#: Copy, Cut, Paste, Select All and Delete are native in both editors; a
#: command id for them would be a second implementation of a key that already
#: works.
NATIVE_IN_BOTH: frozenset[str] = frozenset({
    "cmd_copy",
    "cmd_cut",
    "cmd_delete",
    "cmd_paste",
    "cmd_select_all",
})

#: QuillLite verbs QUILL does not have, each a real gap or a real difference:
#:
#: * ``cmd_close_mdi`` / MDI child windows -- QUILL has tabs (bad.md 5.7).
#: * ``cmd_print_preview`` -- QUILL prints but has no preview window.
#: * ``cmd_unfold_all`` -- QUILL folds and lists folds, but cannot unfold all.
#: * ``cmd_underline`` -- QUILL's Ctrl+U is hard-coded in the char hook and has
#:   no keymap entry at all, which is why it cannot be compared (bad.md 3.1).
#: * ``cmd_paste_collected`` / ``cmd_clear_collected`` -- QUILL's collector is
#:   a mode that writes into the document, so it has neither verb (C4).
#:
#: This set is the P1 backlog, restated as data: every entry is QuillLite ahead
#: of QUILL, which rule 10 does not allow to stand.
LITE_ONLY: frozenset[str] = frozenset({
    "cmd_clear_collected",
    "cmd_close_mdi",
    "cmd_paste_collected",
    "cmd_print_preview",
    "cmd_underline",
    "cmd_unfold_all",
})


def quill_setting_for(lite_field: str) -> str:
    """QUILL's name for *lite_field*, or *lite_field* when they agree.

    Never raises, and never guesses: a field this table has never heard of is
    returned unchanged, which is correct for the thirty-odd names the two
    products already spell identically.
    """
    if lite_field in NOT_ALIASES:
        # Same-looking, different thing. Returning QUILL's name here would be
        # the one wrong answer that looks right.
        return lite_field
    return SETTINGS_ALIASES.get(lite_field, lite_field)
