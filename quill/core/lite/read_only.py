"""Which QUILL Lite commands change the document's text, for the Read-Only Guard.

QUILL Lite gained the guard on 2026-10-16 (Tools > Read-Only Guard,
Ctrl+Alt+Backspace), the same command QUILL has had since EDS-8 and on the same
key (rule 2). Making the control read-only stops typing, but a command writes
through the control's own methods, which a read-only control still obeys -- so
the window refuses these commands by name while the guard is on and says
"Document is read-only" instead.

Kept as a list rather than worked out from the menus, because the menus do not
answer the question: Format holds Describe Formatting and Editor Font, which
read, beside Bold, which writes; Edit holds Copy beside Cut. A command that is
not here keeps working, which is the safe direction for reading, moving and
looking things up. Commands that write only *sometimes* -- the word tools'
Replace, an inline note written into the file -- check the guard at the moment
they would write (``quill.ui.word_tools_commands``, the inline-note commands'
``_host_read_only``), so their reading half stays available.
"""

from __future__ import annotations

__all__ = ["TEXT_CHANGING_HANDLERS"]

TEXT_CHANGING_HANDLERS: frozenset[str] = frozenset({
    # Edit
    "cmd_undo",
    "cmd_redo",
    "cmd_cut",
    "cmd_paste",
    "cmd_paste_plain",
    "cmd_delete",
    "cmd_replace",
    "cmd_duplicate_selection",
    "cmd_paste_from_tray",
    "cmd_paste_clip",
    # Edit > Lines, every row
    "cmd_move_line_up",
    "cmd_move_line_down",
    "cmd_duplicate_line",
    "cmd_join_lines",
    "cmd_delete_line",
    "cmd_delete_paragraph",
    "cmd_restore_deletion",
    "cmd_sort_lines",
    "cmd_sort_lines_descending",
    "cmd_reverse_lines",
    "cmd_number_lines",
    "cmd_remove_blank_lines",
    "cmd_remove_duplicate_lines",
    "cmd_trim_trailing_space",
    "cmd_toggle_line_comment",
    "cmd_quote_lines",
    "cmd_unquote_lines",
    "cmd_hard_wrap",
    "cmd_normalize_whitespace",
    # Insert, every row
    "cmd_insert_datetime",
    "cmd_insert_special_character",
    "cmd_insert_emoji",
    "cmd_insert_line_break",
    "cmd_insert_link",
    "cmd_insert_table",
    # Navigate > Table's editing rows
    "cmd_table_insert_row_below",
    "cmd_table_insert_column_right",
    "cmd_table_delete_row",
    "cmd_table_delete_column",
    "cmd_table_tidy",
    "cmd_insert_markdown_tag",
    "cmd_insert_html_tag",
    # Format: the rows that write, not Describe, Editor Font or Language
    "cmd_bold",
    "cmd_italic",
    "cmd_underline",
    "cmd_grow_font",
    "cmd_shrink_font",
    "cmd_normal_text",
    "cmd_align_left",
    "cmd_align_center",
    "cmd_align_right",
    "cmd_align_justify",
    "cmd_cycle_list_style",
    "cmd_selection_font",
    "cmd_switch_document_kind",
    "cmd_spacing_single",
    "cmd_spacing_one_half",
    "cmd_spacing_double",
    "cmd_heading_0",
    "cmd_heading_1",
    "cmd_heading_2",
    "cmd_heading_3",
    "cmd_heading_4",
    "cmd_heading_5",
    "cmd_heading_6",
    "cmd_promote_heading",
    "cmd_demote_heading",
    "cmd_move_section_up",
    "cmd_move_section_down",
    "cmd_toggle_task_done",
    # Tools
    "cmd_snippet_gallery",
    "cmd_upper_case",
    "cmd_lower_case",
    "cmd_title_case",
    "cmd_sentence_case",
    "cmd_toggle_case",
    "cmd_indent",
    "cmd_outdent",
    "cmd_indentation_to_spaces",
    "cmd_indentation_to_tabs",
    "cmd_dictation_tidy",
})
