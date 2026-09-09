"""QuillLite's command table: one list the menu bar and the key list both read.

The house rule this table exists to keep is QUILL's, stated in ``CLAUDE.md``:
**every enabled menu item shows a keyboard route in its label, and no two items
in one menu bar claim the same key.** Walking a menu to discover there is no
shortcut is a cost a screen-reader user pays on every visit, and a key claimed
twice means one of the pair silently never fires.

A table rather than fifty ``menu.Append`` calls, because the table is checkable.
:mod:`tests.unit.core.lite.test_lite_commands` asserts, mechanically, that every
item carries a key, that no key is claimed twice, that no ``&`` mnemonic is
claimed twice *within one menu*, and that every key string is one
``wx.AcceleratorEntry`` can actually parse -- the last of which matters because
wx silently drops what it cannot parse, leaving the menu advertising a key that
does nothing.

The same table generates the Keyboard Shortcuts window, so the list a user reads
is the list that is bound. There is no third place for the two to disagree.

wx-free on purpose: the tests, the shortcut text and the F1 answer all import
this without a display.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.lite import APP_NAME, APP_VERSION

__all__ = [
    "COMMANDS",
    "COMMAND_AREA",
    "MENU_AREA",
    "SEPARATOR",
    "SUBMENU_SEP",
    "Command",
    "CommandRow",
    "area_for",
    "menu_titles",
    "plain_label",
    "shortcut_text",
    "split_menu",
    "visible_commands",
]

#: One row: ``(menu, label, key, handler, kind)``.
#:
#: * ``menu`` and ``label`` carry their own ``&`` mnemonic.
#: * ``key`` is the accelerator, appended after a tab so wx binds it *and*
#:   the menu advertises it. Empty only for a separator.
#: * ``handler`` is the method name on the document window.
#: * ``kind`` is ``""`` (normal), ``"check"`` (checkable) or ``"sep"``.
CommandRow = tuple[str, str, str, str, str]
Command = CommandRow  # the historical spelling, kept so callers may use either

#: Separates a parent menu from a submenu in a row's ``menu`` field:
#: ``"&Edit|Select&ion"`` is the Selection submenu of the Edit menu. Chosen
#: because it cannot occur in a wx menu label, so a title can never be mistaken
#: for a path.
SUBMENU_SEP = "|"

SEPARATOR: CommandRow = ("", "", "", "", "sep")

COMMANDS: list[CommandRow] = [
    # -- File ---------------------------------------------------------------
    # Notepad's and WordPad's File menus, key for key: Ctrl+N, Ctrl+O, Ctrl+S,
    # Ctrl+Shift+S, Ctrl+P. Notepad's Ctrl+Shift+N is "New Window" -- here every
    # New *is* a new window, so the chord names the mode instead.
    ("&File", "&New", "Ctrl+N", "cmd_new", ""),
    ("&File", "New &Rich Text Document", "Ctrl+Shift+N", "cmd_new_rich", ""),
    ("&File", "New P&lain Text Document", "Ctrl+Alt+N", "cmd_new_plain", ""),
    ("&File", "&Open...", "Ctrl+O", "cmd_open", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "&Save", "Ctrl+S", "cmd_save", ""),
    ("&File", "Save &As...", "Ctrl+Shift+S", "cmd_save_as", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "Page Set&up...", "Ctrl+Alt+U", "cmd_page_setup", ""),
    ("&File", "&Print...", "Ctrl+P", "cmd_print", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "&Close Window", "Ctrl+W", "cmd_close", ""),
    ("&File", "E&xit QuillLite", "Ctrl+Q", "cmd_exit", ""),
    # -- Edit ---------------------------------------------------------------
    ("&Edit", "&Undo", "Ctrl+Z", "cmd_undo", ""),
    ("&Edit", "&Redo", "Ctrl+Y", "cmd_redo", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "Cu&t", "Ctrl+X", "cmd_cut", ""),
    ("&Edit", "&Copy", "Ctrl+C", "cmd_copy", ""),
    ("&Edit", "&Paste", "Ctrl+V", "cmd_paste", ""),
    # Not a QUILL feature and not in WordPad either -- just the thing everybody
    # expects and nobody has in a rich text editor.
    ("&Edit", "Paste Text &Only", "Ctrl+Shift+V", "cmd_paste_plain", ""),
    # Notepad has this item, and it is worth having even though the key works
    # without it: a menu is how somebody discovers what a key does.
    ("&Edit", "De&lete", "Del", "cmd_delete", ""),
    ("&Edit", "Select &All", "Ctrl+A", "cmd_select_all", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "Insert &Date and Time", "F5", "cmd_insert_datetime", ""),
    # A screen reader says "space" for four different characters. This is the
    # only way to find out which one broke the search.
    ("&Edit", "Descri&be Character", "Ctrl+Shift+C", "cmd_describe_character", ""),
    ("&Edit", "Character Detail&s...", "Ctrl+Alt+C", "cmd_describe_character_detail", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "&Find...", "Ctrl+F", "cmd_find", ""),
    ("&Edit", "Find &Next", "F3", "cmd_find_next", ""),
    ("&Edit", "Find Pre&vious", "Shift+F3", "cmd_find_previous", ""),
    ("&Edit", "R&eplace...", "Ctrl+H", "cmd_replace", ""),
    ("&Edit", "&Go to Line...", "Ctrl+G", "cmd_goto_line", ""),
    # -- Edit > Matches ------------------------------------------------------
    # Two questions Find Next cannot answer: how many are there, and what does
    # each one sit in. Both matter most in the moment just before a Replace
    # All, and both are otherwise reachable only by pressing F3 until it wraps
    # and counting as you go -- which is a thing you can do by eye and cannot
    # do by ear.
    #
    # A submenu of two, for the reason Selection is a submenu: the Edit menu
    # has one free mnemonic letter left, and these need two. A submenu opens
    # its own namespace instead of forcing a worse letter on a neighbour.
    ("&Edit|&Matches", "&All Matches...", "Ctrl+Shift+F3", "cmd_find_all", ""),
    ("&Edit|&Matches", "&Count Occurrences", "Ctrl+Alt+Shift+F3", "cmd_count_occurrences", ""),
    # -- Edit > Selection ----------------------------------------------------
    # A submenu of Edit, which is where Word and QUILL both keep it. Nineteen
    # items is too many to pour into Edit itself, and too coherent to scatter:
    # a submenu is one Alt+E, I away and gives the group its own mnemonic
    # namespace, which is why every item below can have a sensible letter.
    #
    # A menu string of "parent|child" is how the table says "submenu".
    #
    # Selecting is not one feature, it is three, and they are worth separating:
    # *mark and extend* (press F8, then move, and the selection follows), which
    # is the only way to select an arbitrary run without holding a modifier down
    # while navigating; *structural* selection, which takes a whole word, line
    # or paragraph in one keystroke; and *marks*, which are throwaway positions
    # you can bounce back to.
    #
    # The reason this matters more here than in a mouse editor: Shift+arrow is
    # a fine way to select two letters and a terrible way to select four
    # paragraphs, and there is no drag gesture to fall back on.
    #
    # F8's family is QUILL's, key for key, so the two products feel the same
    # under the hands. Where a key was already taken here, the newcomer moved
    # rather than the resident -- an existing binding somebody's fingers know
    # outranks a new command's convention.
    ("&Edit|Select&ion", "&Start Selection", "F8", "cmd_start_selection", ""),
    ("&Edit|Select&ion", "&Complete Selection", "Shift+F8", "cmd_complete_selection", ""),
    ("&Edit|Select&ion", "&Reselect Last Selection", "Ctrl+Shift+F8", "cmd_reselect", ""),
    (
        "&Edit|Select&ion",
        "&Go to Start of Selection",
        "Alt+Shift+F8",
        "cmd_go_to_selection_start",
        "",
    ),
    (
        "&Edit|Select&ion",
        "Extend Selection &Mode",
        "Ctrl+Alt+F8",
        "cmd_toggle_extend_mode",
        "check",
    ),
    ("&Edit|Select&ion", "", "", "", "sep"),
    ("&Edit|Select&ion", "Select &Word", "Ctrl+Shift+W", "cmd_select_word", ""),
    ("&Edit|Select&ion", "Select L&ine", "Ctrl+Shift+E", "cmd_select_line", ""),
    ("&Edit|Select&ion", "Select &Paragraph", "Ctrl+Shift+H", "cmd_select_paragraph", ""),
    ("&Edit|Select&ion", "Select Se&ntence", "Ctrl+Space", "cmd_select_sentence", ""),
    ("&Edit|Select&ion", "Select &Block", "Ctrl+Alt+Shift+B", "cmd_select_block", ""),
    ("&Edit|Select&ion", "", "", "", "sep"),
    ("&Edit|Select&ion", "E&xpand Selection", "Ctrl+Shift+X", "cmd_expand_selection", ""),
    ("&Edit|Select&ion", "S&hrink Selection", "Ctrl+Alt+Shift+X", "cmd_shrink_selection", ""),
    ("&Edit|Select&ion", "&Unselect All", "Ctrl+Shift+A", "cmd_unselect_all", ""),
    ("&Edit|Select&ion", "", "", "", "sep"),
    # A mark is not a bookmark. A bookmark is a place you mean to keep; a mark
    # is where you were standing ten seconds ago, and Pop Mark is how you get
    # back after going to look something up.
    ("&Edit|Select&ion", "Set Mar&k", "Ctrl+Alt+Shift+K", "cmd_set_mark", ""),
    ("&Edit|Select&ion", "P&op Mark", "Ctrl+M", "cmd_pop_mark", ""),
    ("&Edit|Select&ion", "&List Marks", "Alt+M", "cmd_list_marks", ""),
    ("&Edit|Select&ion", "&Exchange Cursor and Mark", "Ctrl+Alt+X", "cmd_exchange_point_mark", ""),
    ("&Edit|Select&ion", "", "", "", "sep"),
    # Reading back what is selected is not a convenience here. Without sight
    # there is no glance that confirms the selection is the one you meant, and
    # the next keystroke may well replace it.
    ("&Edit|Select&ion", "Sa&y Selection", "Ctrl+Shift+Y", "cmd_say_selection", ""),
    ("&Edit|Select&ion", "&Duplicate Selection", "Ctrl+Alt+Q", "cmd_duplicate_selection", ""),
    # -- View ---------------------------------------------------------------
    # After Edit, where WordPad puts it.
    ("&View", "&Dark Mode", "Alt+Shift+D", "cmd_toggle_dark", "check"),
    ("&View", "&Word Wrap", "Alt+Z", "cmd_toggle_wrap", "check"),
    ("&View", "", "", "", "sep"),
    # Notepad's own zoom chords.
    ("&View", "&Increase Text Size", "Ctrl+=", "cmd_zoom_in", ""),
    ("&View", "D&ecrease Text Size", "Ctrl+-", "cmd_zoom_out", ""),
    ("&View", "&Reset Text Size", "Ctrl+0", "cmd_zoom_reset", ""),
    ("&View", "Editor &Font...", "Ctrl+Alt+F", "cmd_editor_font", ""),
    ("&View", "", "", "", "sep"),
    ("&View", "Document &Statistics", "Ctrl+Alt+W", "cmd_statistics", ""),
    # F6 is the region key every Windows app uses, and the one QUILL's own
    # status bar answers. The menu item exists so the key is discoverable
    # rather than folklore.
    ("&View", "Status &Bar", "F6", "cmd_focus_status_bar", ""),
    ("&View", "", "", "", "sep"),
    # The only place the two settings with no menu item of their own -- what
    # Ctrl+N creates, and how often unsaved work is copied aside -- can be
    # changed at all. Ctrl+comma is where Windows has put preferences for a
    # decade.
    ("&View", "&Preferences...", "Ctrl+,", "cmd_preferences", ""),
    # Turning a whole area off is QUILL's own idea, and it belongs here more
    # than anywhere: the way QuillLite stays small is that somebody who does not
    # want rich text can remove the Format menu entirely rather than learn to
    # ignore it.
    ("&View", "&Customize Features...", "Ctrl+Alt+Shift+F", "cmd_customize_features", ""),
    ("&View", "Command Pa&lette...", "Ctrl+Shift+P", "cmd_command_palette", ""),
    ("&View", "&Go To Anything...", "Ctrl+Alt+Shift+A", "cmd_go_to_anything", ""),
    # -- Format -------------------------------------------------------------
    # WordPad's Format menu, key for key where WordPad has a key: Ctrl+B/I/U,
    # Ctrl+L/E/R/J for alignment, Ctrl+1/2/5 for line spacing, Ctrl+Shift+L for
    # bullets, and Ctrl+Shift+> / < to grow and shrink the selection.
    ("F&ormat", "&Bold", "Ctrl+B", "cmd_bold", ""),
    ("F&ormat", "&Italic", "Ctrl+I", "cmd_italic", ""),
    ("F&ormat", "&Underline", "Ctrl+U", "cmd_underline", ""),
    ("F&ormat", "Gro&w Font", "Ctrl+Shift+.", "cmd_grow_font", ""),
    ("F&ormat", "Shrin&k Font", "Ctrl+Shift+,", "cmd_shrink_font", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Heading &1", "Ctrl+Alt+1", "cmd_heading_1", ""),
    ("F&ormat", "Heading &2", "Ctrl+Alt+2", "cmd_heading_2", ""),
    ("F&ormat", "Heading &3", "Ctrl+Alt+3", "cmd_heading_3", ""),
    ("F&ormat", "Heading &4", "Ctrl+Alt+4", "cmd_heading_4", ""),
    ("F&ormat", "Body &Text", "Ctrl+Alt+0", "cmd_heading_0", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Align &Left", "Ctrl+L", "cmd_align_left", ""),
    ("F&ormat", "&Centre", "Ctrl+E", "cmd_align_center", ""),
    ("F&ormat", "Align &Right", "Ctrl+R", "cmd_align_right", ""),
    ("F&ormat", "&Justify", "Ctrl+J", "cmd_align_justify", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Bullet&s", "Ctrl+Shift+L", "cmd_toggle_bullets", ""),
    ("F&ormat", "Sin&gle Spacing", "Ctrl+1", "cmd_spacing_single", ""),
    ("F&ormat", "One and a &Half Spacing", "Ctrl+5", "cmd_spacing_one_half", ""),
    ("F&ormat", "Double S&pacing", "Ctrl+2", "cmd_spacing_double", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "&Font for Selection...", "Ctrl+Shift+F", "cmd_selection_font", ""),
    ("F&ormat", "&Describe Formatting at Cursor", "Ctrl+Shift+D", "cmd_describe", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Switch Document &Mode", "Ctrl+Shift+M", "cmd_switch_mode", ""),
    # -- Clipboard ----------------------------------------------------------
    # The system clipboard holds one thing, which is one fewer than people need.
    # A whole menu rather than four items scattered through Edit, so the whole
    # idea can be switched off in one checkbox by anyone who does not want it.
    ("&Clipboard", "&Copy to Tray", "Ctrl+Alt+Y", "cmd_copy_to_tray", ""),
    ("&Clipboard", "&Paste from Tray...", "Ctrl+Alt+V", "cmd_paste_from_tray", ""),
    ("&Clipboard", "C&lear Copy Tray", "Ctrl+Alt+Shift+Y", "cmd_clear_copy_tray", ""),
    ("&Clipboard", "", "", "", "sep"),
    ("&Clipboard", "C&ollect Selection", "Ctrl+Alt+G", "cmd_collect_selection", ""),
    ("&Clipboard", "Paste &Everything Collected", "Ctrl+Alt+Shift+G", "cmd_paste_collected", ""),
    ("&Clipboard", "Clear the Collec&tor", "Ctrl+Alt+Shift+C", "cmd_clear_collected", ""),
    ("&Clipboard", "", "", "", "sep"),
    ("&Clipboard", "&Keep Clip", "Ctrl+Alt+M", "cmd_remember_clip", ""),
    ("&Clipboard", "&Recent Clips...", "Ctrl+Alt+Shift+M", "cmd_paste_clip", ""),
    # -- Navigate -----------------------------------------------------------
    ("&Navigate", "&Next Heading", "Ctrl+Alt+H", "cmd_next_heading", ""),
    ("&Navigate", "&Previous Heading", "Ctrl+Alt+Shift+H", "cmd_previous_heading", ""),
    ("&Navigate", "&List Headings...", "Ctrl+Alt+L", "cmd_list_headings", ""),
    ("&Navigate", "", "", "", "sep"),
    # A place you meant to come back to. There is no scrollbar thumb to remember
    # the position of and no glance that finds the place again, so a bookmark is
    # not a convenience here.
    ("&Navigate", "&Set Bookmark", "Ctrl+Shift+B", "cmd_set_bookmark", ""),
    ("&Navigate", "&Go to Bookmark...", "Alt+Shift+G", "cmd_list_bookmarks", ""),
    ("&Navigate", "Ne&xt Bookmark", "F2", "cmd_next_bookmark", ""),
    ("&Navigate", "Previo&us Bookmark", "Shift+F2", "cmd_previous_bookmark", ""),
    ("&Navigate", "&Clear All Bookmarks", "Ctrl+Alt+B", "cmd_clear_bookmarks", ""),
    ("&Navigate", "", "", "", "sep"),
    ("&Navigate", "Set Bookmark &1", "Ctrl+Shift+1", "cmd_set_bookmark_1", ""),
    ("&Navigate", "Set Bookmark &2", "Ctrl+Shift+2", "cmd_set_bookmark_2", ""),
    ("&Navigate", "Set Bookmark &3", "Ctrl+Shift+3", "cmd_set_bookmark_3", ""),
    ("&Navigate", "Set Bookmark &4", "Ctrl+Shift+4", "cmd_set_bookmark_4", ""),
    ("&Navigate", "Set Bookmark &5", "Ctrl+Shift+5", "cmd_set_bookmark_5", ""),
    ("&Navigate", "Set Bookmark &6", "Ctrl+Shift+6", "cmd_set_bookmark_6", ""),
    ("&Navigate", "Set Bookmark &7", "Ctrl+Shift+7", "cmd_set_bookmark_7", ""),
    ("&Navigate", "Set Bookmark &8", "Ctrl+Shift+8", "cmd_set_bookmark_8", ""),
    ("&Navigate", "Set Bookmark &9", "Ctrl+Shift+9", "cmd_set_bookmark_9", ""),
    # -- Tools --------------------------------------------------------------
    # The things people have to *do* to text. One keystroke here, several
    # minutes of arrow keys otherwise -- and "several minutes of arrow keys"
    # costs a screen-reader user far more than it costs anybody else.
    ("&Tools", "&Sort Lines A to Z", "Ctrl+Alt+S", "cmd_sort_lines", ""),
    ("&Tools", "Sort Lines &Z to A", "Ctrl+Alt+Shift+S", "cmd_sort_lines_descending", ""),
    ("&Tools", "", "", "", "sep"),
    ("&Tools", "Remove &Blank Lines", "Ctrl+Alt+K", "cmd_remove_blank_lines", ""),
    ("&Tools", "Remove &Duplicate Lines", "Ctrl+Alt+D", "cmd_remove_duplicate_lines", ""),
    ("&Tools", "T&rim Trailing Spaces", "Ctrl+Alt+T", "cmd_trim_trailing_space", ""),
    ("&Tools", "", "", "", "sep"),
    # Line surgery, on the caret's line rather than on a selection. Reordering
    # two lines without these costs a select, a cut, a move and a paste -- four
    # chances to lose your place in a document you cannot glance at. Same chords
    # as QUILL, which gained them in the same change (it had registered every
    # one of these commands and bound none of them).
    ("&Tools", "Move Line U&p", "Ctrl+Shift+Up", "cmd_move_line_up", ""),
    ("&Tools", "Move Line Dow&n", "Ctrl+Shift+Down", "cmd_move_line_down", ""),
    ("&Tools", "Dupl&icate Line", "Ctrl+D", "cmd_duplicate_line", ""),
    ("&Tools", "&Join Lines", "Ctrl+Alt+Shift+J", "cmd_join_lines", ""),
    ("&Tools", "", "", "", "sep"),
    ("&Tools", "Delete Lin&e", "Ctrl+Shift+Delete", "cmd_delete_line", ""),
    ("&Tools", "Delete to St&art of Line", "Ctrl+Shift+Backspace", "cmd_delete_to_line_start", ""),
    ("&Tools", "Delete t&o End of Line", "Ctrl+Alt+Shift+Delete", "cmd_delete_to_line_end", ""),
    ("&Tools", "Delete Paragrap&h", "Ctrl+Alt+Shift+Backspace", "cmd_delete_paragraph", ""),
    # Undo puts text back where it was; this puts it back where the caret is,
    # which turns a delete into a move and is the only thing here undo cannot do.
    ("&Tools", "Restore Deleted Te&xt", "Ctrl+Alt+Shift+Z", "cmd_restore_deletion", ""),
    ("&Tools", "", "", "", "sep"),
    ("&Tools", "&UPPERCASE", "Ctrl+Shift+U", "cmd_upper_case", ""),
    ("&Tools", "&lowercase", "Ctrl+Shift+K", "cmd_lower_case", ""),
    ("&Tools", "&Title Case", "Ctrl+Shift+G", "cmd_title_case", ""),
    # The two QUILL registered and never bound, so its own Change Case offered
    # five in the menu and three from the keyboard. "Invert" rather than
    # "Toggle" because the Tools menu had no free T and because a person asked
    # to describe it says "it swaps them".
    ("&Tools", "Sentence &case", "Ctrl+Alt+Shift+U", "cmd_sentence_case", ""),
    ("&Tools", "In&vert Case", "Ctrl+Alt+Shift+N", "cmd_toggle_case", ""),
    ("&Tools", "", "", "", "sep"),
    # Both are shown in the status bar and both used to be read-only: QuillLite
    # wrote back whatever it read, which is the right default and a dead end for
    # anyone who needs a UTF-8 copy of a Windows-1252 file.
    ("&Tools", "&File Encoding and Line Endings...", "Ctrl+Alt+E", "cmd_file_format", ""),
    ("&Tools", "", "", "", "sep"),
    # Type a short form and a space, get the long one. QUILL's engine, QUILL's
    # manager dialog, and QuillLite's own library unless Preferences says share.
    ("&Tools", "&Manage Abbreviations...", "Ctrl+Alt+A", "cmd_manage_abbreviations", ""),
    # -- Tools > Indenting ---------------------------------------------------
    # A submenu because the Tools menu has few free mnemonic letters left and
    # these are one idea. QUILL's own chords, unchanged.
    #
    # Deliberately NOT a Describe Indent Depth command, though leading
    # whitespace is exactly what a reader does not speak: QUILL has no such
    # command, only an announce-as-you-move toggle, and QuillLite may never be
    # ahead of the editor. It belongs in QUILL first.
    ("&Tools|Indentin&g", "&Indent", "Ctrl+]", "cmd_indent", ""),
    ("&Tools|Indentin&g", "&Outdent", "Ctrl+[", "cmd_outdent", ""),
    # -- Tools > More Line Work ----------------------------------------------
    ("&Tools|More Line &Work", "&Reverse Lines", "Alt+Shift+Z", "cmd_reverse_lines", ""),
    (
        "&Tools|More Line &Work",
        "&Tidy Whitespace",
        "Ctrl+Alt+Shift+T",
        "cmd_normalize_whitespace",
        "",
    ),
    ("&Tools|More Line &Work", "&Number Lines", "Alt+Shift+N", "cmd_number_lines", ""),
    # -- Spelling -----------------------------------------------------------
    # Its own menu rather than four items in Tools, for the reason the
    # Clipboard menu is its own: the whole idea has to be switchable in one
    # checkbox, and an area whose commands are scattered through a menu that
    # stays is an area you cannot cleanly remove.
    #
    # F7 is the spelling key in Word, in QUILL, and in every editor that has
    # one. The family around it is free, so the whole menu sits on F7 with a
    # modifier -- which means one key to remember rather than six.
    ("&Spelling", "Check &Spelling...", "F7", "cmd_spell_review", ""),
    ("&Spelling", "Spelling for &This Word", "Shift+F7", "cmd_spell_word_at_cursor", ""),
    ("&Spelling", "", "", "", "sep"),
    ("&Spelling", "&Next Misspelling", "Ctrl+F7", "cmd_next_misspelling", ""),
    ("&Spelling", "&Previous Misspelling", "Ctrl+Shift+F7", "cmd_previous_misspelling", ""),
    ("&Spelling", "", "", "", "sep"),
    ("&Spelling", "&Add Word to Dictionary", "Alt+F7", "cmd_add_word_to_dictionary", ""),
    # Notepad has this item, and it earns its place: the file-type rule means
    # the check is sometimes off for a reason nobody was told, so there has to
    # be one visible thing that says what the state is and changes it.
    ("&Spelling", "Check &While Typing", "Ctrl+Alt+F7", "cmd_toggle_live_spelling", "check"),
    # -- Window -------------------------------------------------------------
    # Ctrl+F6 is the Windows MDI convention and Ctrl+Tab is what everyone
    # actually presses; both are bound, because a key somebody expects and
    # does not get is indistinguishable from a broken app.
    ("&Window", "&Next Window", "Ctrl+Tab", "cmd_next_window", ""),
    ("&Window", "Ne&xt Window (MDI)", "Ctrl+F6", "cmd_next_window_mdi", ""),
    ("&Window", "&Previous Window", "Ctrl+Shift+Tab", "cmd_previous_window", ""),
    # -- Help ---------------------------------------------------------------
    # F1 belongs to the family's context help (quill.ui.app_context_help): it
    # answers with what *this* window is for and then what the focused control
    # does. The static key list moved to Ctrl+F1 rather than taking F1 from the
    # engine every other QuillVille app answers with.
    ("&Help", "&Help for This Window", "F1", "cmd_context_help", ""),
    ("&Help", "&Keyboard Shortcuts", "Ctrl+F1", "cmd_shortcuts", ""),
    ("&Help", "&About QuillLite", "Shift+F1", "cmd_about", ""),
]

#: Menu-bar labels, in bar order, deduplicated by first appearance.
_MENU_ORDER: list[str] = []
for _row in COMMANDS:
    if _row[0] not in _MENU_ORDER:
        _MENU_ORDER.append(_row[0])


def menu_titles() -> list[str]:
    """The menu-*bar* titles, in bar order. Submenus are not bar entries."""
    seen: list[str] = []
    for menu in _MENU_ORDER:
        top = menu.split(SUBMENU_SEP, 1)[0]
        if top not in seen:
            seen.append(top)
    return seen


def split_menu(menu: str) -> tuple[str, str]:
    """``"&Edit|Select&ion"`` -> ``("&Edit", "Select&ion")``; else ``(menu, "")``."""
    parent, _, child = menu.partition(SUBMENU_SEP)
    return parent, child


def _plain(label: str) -> str:
    """*label* with its mnemonic ampersands removed, for reading aloud."""
    return label.replace("&&", "\0").replace("&", "").replace("\0", "&")


def shortcut_text() -> str:
    """The Keyboard Shortcuts window's body, generated from the same table.

    Two things are appended that the table cannot carry: the Alt+digit window
    switches (built per window, from however many are open) and the heading
    ladder, which is the one fact about rich mode that saves a support email.
    """
    lines = [f"{APP_NAME} {APP_VERSION} keyboard shortcuts", ""]
    current = ""
    for menu, label, key, _handler, kind in COMMANDS:
        if kind == "sep":
            continue
        if menu != current:
            current = menu
            parent, child = split_menu(menu)
            lines.append("")
            lines.append(
                f"{_plain(parent)} menu, {_plain(child)} submenu"
                if child
                else f"{_plain(parent)} menu"
            )
        lines.append(f"  {key}: {_plain(label)}")
    lines += [
        "",
        "Window menu",
        "  Alt+1 to Alt+9: switch to that open window",
        "",
        "File menu, Open Recent",
        "  Alt+Shift+1 to Alt+Shift+9: reopen that recent file",
        "",
        "Status bar (F6)",
        "  Left and Right, Home and End: move between cells",
        "  Enter: act on the cell -- go to a line, switch mode, list headings, save",
        "  Escape: back to the document",
        "",
        "Headings in rich text are bold plus a point size: 20, 16, 14 and 12",
        "point for levels 1 to 4, and 11 point for body text. That is QUILL's",
        "own ladder, so a document saved here reads as headings in Word.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------- #
# Which commands belong to which switchable area
# ---------------------------------------------------------------------- #
#
# Turning an area off in View > Customize Features removes its commands from the
# menus, from the keyboard, and from the Command Palette -- not just from the
# menus. A key that still fires for a feature somebody has switched off is the
# feature not being off.
#
# Two granularities, because that is how the areas actually fall: some are a
# whole menu (Format is rich text; Tools is the tools), and some are a handful of
# items scattered through menus that stay (printing, bookmarks, clipboard).

#: Menus that belong entirely to one area.
MENU_AREA: dict[str, str] = {
    "F&ormat": "rich_text",
    "&Tools": "tools",
    "&Clipboard": "clipboard",
    "&Spelling": "spelling",
    "&Edit|Select&ion": "selection",
}

#: Individual handlers whose area is not their menu's.
COMMAND_AREA: dict[str, str] = {
    "cmd_page_setup": "printing",
    "cmd_print": "printing",
    "cmd_next_heading": "headings",
    "cmd_previous_heading": "headings",
    "cmd_list_headings": "headings",
    "cmd_set_bookmark": "bookmarks",
    "cmd_list_bookmarks": "bookmarks",
    "cmd_next_bookmark": "bookmarks",
    "cmd_previous_bookmark": "bookmarks",
    "cmd_clear_bookmarks": "bookmarks",
    "cmd_paste_from_tray": "clipboard",
    "cmd_copy_to_tray": "clipboard",
    "cmd_clear_copy_tray": "clipboard",
    "cmd_collect_selection": "clipboard",
    "cmd_paste_collected": "clipboard",
    "cmd_clear_collected": "clipboard",
    "cmd_remember_clip": "clipboard",
    "cmd_paste_clip": "clipboard",
    # In the Tools menu, but its own area: somebody can keep the tools and drop
    # expansion, or the other way round.
    "cmd_manage_abbreviations": "abbreviations",
    "cmd_go_to_anything": "go_to_anything",
}
COMMAND_AREA.update({f"cmd_set_bookmark_{n}": "bookmarks" for n in range(1, 10)})


def area_for(menu: str, handler: str) -> str:
    """The area a row belongs to, or "" when it is always present."""
    return COMMAND_AREA.get(handler) or MENU_AREA.get(menu, "")


def plain_label(label: str) -> str:
    """*label* with its mnemonic ampersands removed, for reading aloud."""
    return _plain(label)


def visible_commands(is_enabled: Callable[[str], bool]) -> list[CommandRow]:
    """The table with every switched-off area removed, and tidied afterwards.

    Tidying is the part that is easy to forget and obvious when missing: taking
    rows out leaves separators with nothing between them, separators at the top
    or bottom of a menu, and -- when a whole menu goes -- a menu with nothing in
    it at all. Each of those is a thing a screen reader dutifully reads out.
    """
    kept: list[CommandRow] = []
    for row in COMMANDS:
        menu, _label, _key, handler, kind = row
        if kind != "sep" and not is_enabled(area_for(menu, handler)) and area_for(menu, handler):
            continue
        if kind == "sep" and not is_enabled(MENU_AREA.get(menu, "")) and MENU_AREA.get(menu):
            continue
        kept.append(row)
    return _tidy(kept)


def _tidy(rows: list[CommandRow]) -> list[CommandRow]:
    """Drop empty menus, leading and trailing separators, and doubled ones."""
    by_menu: dict[str, list[CommandRow]] = {}
    for row in rows:
        by_menu.setdefault(row[0], []).append(row)
    out: list[CommandRow] = []
    for menu in _MENU_ORDER:
        items = by_menu.get(menu, [])
        cleaned: list[CommandRow] = []
        for row in items:
            if row[4] == "sep" and (not cleaned or cleaned[-1][4] == "sep"):
                continue
            cleaned.append(row)
        while cleaned and cleaned[-1][4] == "sep":
            cleaned.pop()
        if any(row[4] != "sep" for row in cleaned):
            out.extend(cleaned)
    return out
