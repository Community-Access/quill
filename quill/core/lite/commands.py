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

from quill.core.lite import APP_NAME, APP_VERSION

__all__ = [
    "COMMANDS",
    "SEPARATOR",
    "SUBMENU_SEP",
    "Command",
    "CommandRow",
    "menu_titles",
    "plain_label",
    "shortcut_text",
    "split_menu",
]
#: One row: ``(menu, label, key, handler, kind)``.
#:
#: * ``menu`` and ``label`` carry their own ``&`` mnemonic.
#: * ``key`` is the accelerator, appended after a tab so wx binds it *and*
#:   the menu advertises it. Empty for a separator or a submenu title.
#: * ``handler`` is the method name on the document window.
#: * ``kind`` is ``""`` (normal), ``"check"`` (checkable), ``"sep"`` or
#:   ``"sub"``.
#:
#: A ``"sub"`` row is a submenu's title, sitting in its parent at the position
#: the submenu should appear -- its ``label`` is the child half of the child's
#: own menu path, so ``("&Edit", "&Lines", "", "", "sub")`` names
#: ``"&Edit|&Lines"``. Written down rather than inferred, for two reasons: the
#: submenu lands where the table says instead of always at the bottom of its
#: parent, and its mnemonic is then a row like any other, so the "no letter
#: twice in one menu" check sees it. It carries no key and no handler.
CommandRow = tuple[str, str, str, str, str]
Command = CommandRow  # the historical spelling, kept so callers may use either

#: Separates a parent menu from a submenu in a row's ``menu`` field:
#: ``"&Edit|Select&ion"`` is the Selection submenu of the Edit menu. Chosen
#: because it cannot occur in a wx menu label, so a title can never be mistaken
#: for a path.
SUBMENU_SEP = "|"

SEPARATOR: CommandRow = ("", "", "", "", "sep")

COMMANDS: list[CommandRow] = [
    # The bar is Notepad's and WordPad's, in that order and with those names:
    # **File, Edit, View, Insert, Format, Navigate, Tools, Window, Help**. Nine,
    # where there were ten -- Clipboard and Spelling were top-level menus of
    # their own, which is two more things to walk past on every Alt press for two
    # features neither Notepad nor WordPad puts on the bar at all. They are
    # submenus now (Edit > Clipboard, Tools > Spelling), which costs one
    # keystroke to reach and saves one on every visit to everything else.
    #
    # **Insert is the ninth, and it is where the things you put *into* a document
    # go.** It was a submenu of Edit holding three rows, which was the right
    # answer while there were three; adding the emoji picker and the two tag
    # pickers made six, and six is a menu. It sits before Format for the reason
    # Word and every other editor puts it there: you insert a thing and then you
    # format it, so the menus are in the order the work happens. Nothing moved
    # key: Alt+E, I still reaches nothing, but F5, Ctrl+Shift+F2 and Shift+Enter
    # are unchanged, which is what fingers actually remember.
    #
    # Navigate is the one menu neither of them has, and it earns its place: a
    # sighted user navigates a document by scrolling and glancing, and a
    # listener navigates it by heading, bookmark and line number. That is not a
    # tool, it is how the document is read.
    # -- File ---------------------------------------------------------------
    # Notepad's and WordPad's File menus, key for key: Ctrl+N, Ctrl+O, Ctrl+S,
    # Ctrl+Shift+S, Ctrl+P. Notepad's Ctrl+Shift+N is "New Window" -- here every
    # New *is* a new window, so the chord names the mode instead.
    ("&File", "&New", "Ctrl+N", "cmd_new", ""),
    # Alt+Shift+T, not Ctrl+Shift+N, since 2026-09-22. Ctrl+Shift+N is
    # **Word's Normal style** and a rich document is where somebody reaches for
    # it -- family rule 1, Microsoft's key wins for a function both editors
    # have, and rule 3, frequency breaks the tie: Normal Text is pressed all
    # day in an RTF document and New Rich Document once per document.
    #
    # T for Text, and the keymap left almost no choice: four chords were free in
    # both editors and this is the only one that means anything. Ctrl+Alt+Shift+N
    # would have kept the two News a pair and is Invert Case, one of five Change
    # Case chords worth more as a family; Ctrl+Alt+R is QUILL's Trim Trailing
    # Whitespace, a divergence decided on 2026-09-16 and written down, and taking
    # it would have left that row with no keyboard route at all.
    ("&File", "New &Rich Text Document", "Alt+Shift+T", "cmd_new_rich", ""),
    ("&File", "New P&lain Text Document", "Ctrl+Alt+N", "cmd_new_plain", ""),
    ("&File", "&Open...", "Ctrl+O", "cmd_open", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "&Save", "Ctrl+S", "cmd_save", ""),
    ("&File", "Save &As...", "Ctrl+Shift+S", "cmd_save_as", ""),
    # The dated copies kept on every save. QuillLite has written these since
    # backups shipped and offered no way to read one back: the files were
    # correct, correctly named, and reachable only by knowing which hashed
    # folder under the backups directory was yours. A safety net nobody can
    # reach is not a safety net.
    #
    # In File because that is where a version of *this file* belongs, and where
    # QUILL keeps its own Restore Previous Version. Its own area rather than the
    # File menu's, since backups are switchable and the rest of File is not.
    ("&File", "Earlier &Versions...", "Ctrl+Alt+Shift+E", "cmd_browse_backups", ""),
    # The session chooser on demand. Same key and same window as QUILL, so
    # "Not Now" at launch is deferrable rather than lost (rule 9: the F-keys
    # past F9 are where a once-in-a-while command goes).
    ("&File", "Reopen Last S&ession...", "Alt+Shift+F12", "cmd_reopen_last_session", ""),
    ("&File", "", "", "", "sep"),
    # Ctrl+Alt+P, not the Ctrl+Alt+U it used to hold: that key is Check
    # for Updates in the eight other QuillVille apps, and P suits Page Setup.
    ("&File", "Page Set&up...", "Ctrl+Alt+P", "cmd_page_setup", ""),
    # An accessible preview rather than a picture of a page (bad.md PR2,
    # P3.6). WordPad and Word both show a scaled image of the sheet, which
    # answers nothing for somebody who listens; this says how many pages, on
    # what paper, with what margins, and what is at the top of each one.
    # Not &V: Earlier &Versions has it in this menu, and Windows cycles
    # focus between duplicates instead of pressing, so one of the pair
    # silently cannot be reached (GATE-14).
    ("&File", "Print Previe&w...", "Ctrl+Alt+Shift+P", "cmd_print_preview", ""),
    ("&File", "&Print...", "Ctrl+P", "cmd_print", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "&Close Window", "Ctrl+W", "cmd_close", ""),
    # The same move on the key Windows has used for an MDI child since Windows
    # 3.1. Nothing bound it, so somebody arriving from any MDI application
    # pressed it and got nothing -- and the two comments that mentioned Alt+F4
    # disagreed about what *that* did (bad.md H7). Alt+F4 closes the shell and
    # takes the documents with it, which is the window manager's key and not
    # ours to rebind; Ctrl+F4 closes this document, and now says so. Bound as
    # its own row rather than an alias because the table gives one key to one
    # handler -- the same arrangement Ctrl+Tab and Ctrl+F6 already have.
    ("&File", "Close Window (&MDI)", "Ctrl+F4", "cmd_close_mdi", ""),
    ("&File", "E&xit QuillLite", "Ctrl+Q", "cmd_exit", ""),
    # -- Edit ---------------------------------------------------------------
    # Notepad's Edit menu is the top of this one, in Notepad's order, and then
    # four submenus for the things Notepad has no answer to at all: the
    # clipboard that holds more than one thing, the selection family, the match
    # list, and line work.
    #
    # Four submenus rather than four more groups of items, and the reason is
    # mnemonic arithmetic rather than taste: Edit claims twenty-two Alt letters
    # as it stands and there are twenty-six. A submenu opens its own namespace,
    # which is what lets every row below have a sensible letter.
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
    ("&Edit", "&Delete", "Del", "cmd_delete", ""),
    ("&Edit", "Select &All", "Ctrl+A", "cmd_select_all", ""),
    # Beside Select All because it is the thing people use Select All *for*, and
    # it is the better answer: Select All then Copy leaves the whole document
    # selected, and the next character typed replaces it. QUILL's own key
    # (bad.md 4.2, Tier 1).
    ("&Edit", "Cop&y All", "Ctrl+F8", "cmd_copy_all", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "&Find...", "Ctrl+F", "cmd_find", ""),
    ("&Edit", "Find Ne&xt", "F3", "cmd_find_next", ""),
    ("&Edit", "Find Pre&vious", "Shift+F3", "cmd_find_previous", ""),
    ("&Edit", "R&eplace...", "Ctrl+H", "cmd_replace", ""),
    # Two questions Find Next cannot answer: how many are there, and what does
    # each one sit in. Both matter most in the moment just before a Replace
    # All, and both are otherwise reachable only by pressing F3 until it wraps
    # and counting as you go -- which is a thing you can do by eye and cannot
    # do by ear. Directly under Find, where the question gets asked.
    ("&Edit", "&Matches", "", "", "sub"),
    ("&Edit", "", "", "", "sep"),
    # Go To is in Edit because that is where Notepad has always kept it, and
    # because it answers the question Find asks: the line number the status bar
    # just read out is typed in here.
    # Word's Go To, not Notepad's Go to Line: one window with a target kind --
    # Line, Bookmark or Heading -- rather than three surfaces for one verb
    # (bad.md 5.4). Alt+Shift+G and Ctrl+Alt+L still go straight to their own
    # list, which is the faster route when you already know which kind you want.
    ("&Edit", "&Go To...", "Ctrl+G", "cmd_goto_line", ""),
    ("&Edit", "", "", "", "sep"),
    # A screen reader says "space" for four different characters. This is the
    # only way to find out which one broke the search.
    ("&Edit", "Describe C&haracter", "Ctrl+Shift+C", "cmd_describe_character", ""),
    ("&Edit", "Character Detail&s...", "Ctrl+Alt+C", "cmd_describe_character_detail", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "&Lines", "", "", "sub"),
    ("&Edit", "Selectio&n", "", "", "sub"),
    ("&Edit", "Clip&board", "", "", "sub"),
    # -- Edit > Matches ------------------------------------------------------
    ("&Edit|&Matches", "&All Matches...", "Ctrl+Shift+F3", "cmd_find_all", ""),
    ("&Edit|&Matches", "&Count Occurrences", "Ctrl+Alt+Shift+F3", "cmd_count_occurrences", ""),
    # -- Edit > Lines --------------------------------------------------------
    # Everything that happens to whole lines, in one place, in the order the
    # work is actually done: move them, delete them, order them, tidy them.
    #
    # These were the top two thirds of a top-level Tools menu, which put line
    # surgery three menus away from the text it operates on and left Edit
    # looking like Notepad's. Line work *is* editing: it belongs next to Cut and
    # Paste, not next to the encoding dialog. Every chord is unchanged, so
    # nothing anybody's fingers already know has moved -- only the menu has.
    #
    # One keystroke here, several minutes of arrow keys otherwise -- and
    # "several minutes of arrow keys" costs a screen-reader user far more than
    # it costs anybody else.
    #
    # Line surgery is on the caret's line rather than on a selection.
    # Reordering two lines without these costs a select, a cut, a move and a
    # paste -- four chances to lose your place in a document you cannot glance
    # at. Same chords as QUILL, which gained them in the same change (it had
    # registered every one of these commands and bound none of them).
    ("&Edit|&Lines", "Move Line &Up", "Ctrl+Shift+Up", "cmd_move_line_up", ""),
    ("&Edit|&Lines", "Move Line Do&wn", "Ctrl+Shift+Down", "cmd_move_line_down", ""),
    ("&Edit|&Lines", "&Duplicate Line", "Ctrl+D", "cmd_duplicate_line", ""),
    ("&Edit|&Lines", "&Join Lines", "Ctrl+Alt+Shift+J", "cmd_join_lines", ""),
    ("&Edit|&Lines", "", "", "", "sep"),
    ("&Edit|&Lines", "Delete Lin&e", "Ctrl+Shift+Delete", "cmd_delete_line", ""),
    (
        "&Edit|&Lines",
        "Delete to &Start of Line",
        "Ctrl+Shift+Backspace",
        "cmd_delete_to_line_start",
        "",
    ),
    (
        "&Edit|&Lines",
        "Delete t&o End of Line",
        "Ctrl+Alt+Shift+Delete",
        "cmd_delete_to_line_end",
        "",
    ),
    ("&Edit|&Lines", "Delete &Paragraph", "Ctrl+Alt+Shift+Backspace", "cmd_delete_paragraph", ""),
    # Undo puts text back where it was; this puts it back where the caret is,
    # which turns a delete into a move and is the only thing here undo cannot do.
    ("&Edit|&Lines", "&Restore Deleted Text", "Ctrl+Alt+Shift+Z", "cmd_restore_deletion", ""),
    ("&Edit|&Lines", "", "", "", "sep"),
    ("&Edit|&Lines", "Sort Lines &A to Z", "Ctrl+Alt+S", "cmd_sort_lines", ""),
    ("&Edit|&Lines", "Sort Lines &Z to A", "Ctrl+Alt+Shift+S", "cmd_sort_lines_descending", ""),
    ("&Edit|&Lines", "Re&verse Lines", "Alt+Shift+Z", "cmd_reverse_lines", ""),
    ("&Edit|&Lines", "&Number Lines", "Alt+Shift+N", "cmd_number_lines", ""),
    ("&Edit|&Lines", "", "", "", "sep"),
    ("&Edit|&Lines", "Remove Every &Blank Line", "Ctrl+Alt+K", "cmd_remove_blank_lines", ""),
    ("&Edit|&Lines", "Remove Dup&licate Lines", "Ctrl+Alt+D", "cmd_remove_duplicate_lines", ""),
    ("&Edit|&Lines", "&Trim Trailing Spaces", "Ctrl+Alt+T", "cmd_trim_trailing_space", ""),
    ("&Edit|&Lines", "", "", "", "sep"),
    # QuillLite's PRD accepts that people edit .py, .json and .conf here -- it
    # silences the spell checker in them for exactly that reason -- and a
    # comment toggle is the second half of that concession (bad.md 4.2). The
    # prefix comes from the file name, through the same shared helper QUILL
    # uses, so a .py gets "# " and a .sql gets "-- " in both editors.
    ("&Edit|&Lines", "Toggle Line &Comment", "Ctrl+/", "cmd_toggle_line_comment", ""),
    ("&Edit|&Lines", "", "", "", "sep"),
    # Replying to an email and quoting a log excerpt are Notepad-scale tasks,
    # and the engine was shared already: QuillLite had every other line tool
    # and not these two (bad.md 4.2, Tier 2). Ctrl+Shift+Q is QUILL's own.
    #
    # "Remove Quote Marks" rather than "Unquote Lines", which is QUILL's label:
    # a listener hears "unquote" as the start of a quotation, and Edit > Lines
    # had no free mnemonic in the word anyway. The divergence is a label, not a
    # verb -- both editors run the same `unquote_lines`.
    ("&Edit|&Lines", "&Quote Lines", "Ctrl+Shift+Q", "cmd_quote_lines", ""),
    ("&Edit|&Lines", "Remove Quote &Marks", "Ctrl+Alt+Shift+Q", "cmd_unquote_lines", ""),
    ("&Edit|&Lines", "", "", "", "sep"),
    # Log triage and formatting for a narrow display, which are two of the
    # reasons somebody opens a plain-text editor at all (bad.md 4.2, Tier 2).
    (
        "&Edit|&Lines",
        "Delete Lines Containin&g...",
        "Alt+Shift+X",
        "cmd_delete_lines_containing",
        "",
    ),
    ("&Edit|&Lines", "&Hard Wrap Lines...", "Alt+Shift+W", "cmd_hard_wrap", ""),
    ("&Edit|&Lines", "Tid&y Whitespace", "Ctrl+Alt+Shift+T", "cmd_normalize_whitespace", ""),
    # -- Edit > Selection ----------------------------------------------------
    # A submenu of Edit, which is where Word and QUILL both keep it. Nineteen
    # items is too many to pour into Edit itself, and too coherent to scatter:
    # a submenu is one Alt+E, N away and gives the group its own mnemonic
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
    ("&Edit|Selectio&n", "&Start Selection", "F8", "cmd_start_selection", ""),
    ("&Edit|Selectio&n", "&Complete Selection", "Shift+F8", "cmd_complete_selection", ""),
    ("&Edit|Selectio&n", "&Reselect Last Selection", "Ctrl+Shift+F8", "cmd_reselect", ""),
    (
        "&Edit|Selectio&n",
        "&Go to Start of Selection",
        "Alt+Shift+F8",
        "cmd_go_to_selection_start",
        "",
    ),
    (
        # Named for what it does since 2026-09-17. It was called "Extend
        # Selection Mode", which is a different thing that QUILL has on
        # Alt+Shift+F9 and QuillLite now has too -- and calling the marker
        # toggle by the mode's name is how somebody presses it expecting a
        # sticky Shift and gets a pin (bad.md 5.3a).
        "&Edit|Selectio&n",
        "&Toggle Selection Marker",
        "Ctrl+Alt+F8",
        "cmd_toggle_extend_mode",
        "check",
    ),
    (
        "&Edit|Selectio&n",
        "Extend Selection &Mode",
        "Alt+Shift+F9",
        "cmd_toggle_extend_selection_mode",
        "check",
    ),
    ("&Edit|Selectio&n", "", "", "", "sep"),
    ("&Edit|Selectio&n", "Select &Word", "Ctrl+Shift+W", "cmd_select_word", ""),
    ("&Edit|Selectio&n", "Select L&ine", "Ctrl+Shift+E", "cmd_select_line", ""),
    ("&Edit|Selectio&n", "Select &Paragraph", "Ctrl+Shift+H", "cmd_select_paragraph", ""),
    ("&Edit|Selectio&n", "Select Se&ntence", "Ctrl+Space", "cmd_select_sentence", ""),
    ("&Edit|Selectio&n", "Select &Block", "Ctrl+Alt+Shift+B", "cmd_select_block", ""),
    ("&Edit|Selectio&n", "", "", "", "sep"),
    ("&Edit|Selectio&n", "E&xpand Selection", "Ctrl+Shift+X", "cmd_expand_selection", ""),
    ("&Edit|Selectio&n", "S&hrink Selection", "Ctrl+Alt+Shift+X", "cmd_shrink_selection", ""),
    ("&Edit|Selectio&n", "&Unselect All", "Ctrl+Shift+A", "cmd_unselect_all", ""),
    ("&Edit|Selectio&n", "", "", "", "sep"),
    # A mark is not a bookmark. A bookmark is a place you mean to keep; a mark
    # is where you were standing ten seconds ago, and Pop Mark is how you get
    # back after going to look something up.
    # Ctrl+Shift+M since 2026-09-16, which is QUILL's own chord for it and the
    # family's (bad.md 3.3). Set Mark is an editing-loop verb and was on a
    # four-key chord while Switch Document Mode -- which a person presses a
    # handful of times a year -- held the three-key one. Frequency breaks the
    # tie; Switch Document Mode moved to Alt+Shift+F, free in both editors.
    ("&Edit|Selectio&n", "Set Mar&k", "Ctrl+Shift+M", "cmd_set_mark", ""),
    ("&Edit|Selectio&n", "P&op Mark", "Ctrl+M", "cmd_pop_mark", ""),
    ("&Edit|Selectio&n", "&List Marks", "Alt+M", "cmd_list_marks", ""),
    ("&Edit|Selectio&n", "&Exchange Cursor and Mark", "Ctrl+Alt+X", "cmd_exchange_point_mark", ""),
    ("&Edit|Selectio&n", "", "", "", "sep"),
    # Reading back what is selected is not a convenience here. Without sight
    # there is no glance that confirms the selection is the one you meant, and
    # the next keystroke may well replace it.
    ("&Edit|Selectio&n", "Sa&y Selection", "Ctrl+Shift+Y", "cmd_say_selection", ""),
    # A read-only copy of the selection, in a window of its own. The point is
    # what you cannot do in it: arrowing through your own document with a
    # selection live means the next character you type replaces all of it, so
    # the safe way to read a selection back is a copy that refuses to be edited
    # (bad.md 4.2, Tier 2). QUILL has had the command since SEL-4 and never
    # bound a key to it.
    # Alt+Shift+U, not the V that "Review" asks for: V is Preview in QUILL and
    # a chord free in both is adopted in both (rule 5). QUILL gained the key on
    # the same day -- it had had the command since SEL-4 and nothing bound to it.
    ("&Edit|Selectio&n", "Re&view Buffer...", "Alt+Shift+U", "cmd_open_review_buffer", ""),
    ("&Edit|Selectio&n", "&Duplicate Selection", "Ctrl+Alt+Q", "cmd_duplicate_selection", ""),
    # -- Edit > Clipboard ----------------------------------------------------
    # The system clipboard holds one thing, which is one fewer than people need.
    # A submenu of Edit rather than a menu of its own on the bar: it is the
    # clipboard, and the clipboard has lived in Edit in every Windows
    # application ever written. It was top-level so that the whole idea could be
    # switched off in one checkbox -- which a submenu does just as well, because
    # a submenu with nothing left in it is removed along with its title.
    ("&Edit|Clip&board", "&Copy to Tray", "Ctrl+Alt+Y", "cmd_copy_to_tray", ""),
    # The next free slot is the right default and the wrong only option: a tray
    # filled in order is a tray whose numbers mean nothing, and the value of a
    # numbered slot is that you chose the number. Each row says what it holds,
    # so nothing is overwritten unheard (bad.md 5.1, P2.1).
    ("&Edit|Clip&board", "Copy to Tray &Slot...", "Alt+Shift+Y", "cmd_copy_to_tray_slot", ""),
    ("&Edit|Clip&board", "&Paste from Tray...", "Ctrl+Alt+V", "cmd_paste_from_tray", ""),
    ("&Edit|Clip&board", "C&lear Copy Tray", "Ctrl+Alt+Shift+Y", "cmd_clear_copy_tray", ""),
    ("&Edit|Clip&board", "", "", "", "sep"),
    # Alt+Shift+S, not Ctrl+Alt+G: Google Drive for desktop owns Ctrl+Alt+G
    # system-wide, and Windows hands a system-wide hotkey to its owner before a
    # focused application sees the key -- so this was unreachable from the
    # keyboard on any machine with Drive installed, and went silent rather than
    # saying so. The two Shift variants below keep the G, because only the base
    # chord is claimed.
    ("&Edit|Clip&board", "C&ollect Selection", "Alt+Shift+S", "cmd_collect_selection", ""),
    (
        "&Edit|Clip&board",
        "Paste &Everything Collected",
        "Ctrl+Alt+Shift+G",
        "cmd_paste_collected",
        "",
    ),
    ("&Edit|Clip&board", "Clear the Collec&tor", "Ctrl+Alt+Shift+C", "cmd_clear_collected", ""),
    ("&Edit|Clip&board", "", "", "", "sep"),
    ("&Edit|Clip&board", "&Keep Clip", "Ctrl+Alt+M", "cmd_remember_clip", ""),
    ("&Edit|Clip&board", "&Recent Clips...", "Ctrl+Alt+Shift+M", "cmd_paste_clip", ""),
    # -- View ---------------------------------------------------------------
    # After Edit, where WordPad puts it. Notepad's View menu is Zoom and a
    # Status Bar checkbox; this one is that, plus the four modes that are
    # invisible until you ask -- and every one of those is a *state* rather than
    # an action, which is what View is for.
    ("&View", "&Dark Mode", "Alt+Shift+D", "cmd_toggle_dark", "check"),
    ("&View", "&Word Wrap", "Alt+Z", "cmd_toggle_wrap", "check"),
    # Say "Heading 2" on arrival, or do not. A toggle rather than a buried
    # preference because it is a per-document decision: you want it in a report
    # and not in a file you are reading as text. Ctrl+Alt+F3 joins Ctrl+Alt+F1
    # (tutorials) and Ctrl+Alt+F2 (support) in the family's function-key range,
    # which is outside what the Ctrl+Alt policy is about -- F-keys are neither
    # AltGr characters nor claimed by any default JAWS or NVDA command.
    ("&View", "Announce &Headings", "Ctrl+Alt+F3", "cmd_toggle_heading_announcements", "check"),
    # And the same for lists -- "Bulleted list, 5 items" going in, "Level 2, 3
    # items" a rung down, "Out of list" coming out. Its own switch rather than a
    # share of the heading one, because the two answer different questions and
    # people want different answers to them: reorganising an outline the list
    # level is the work, and proof-reading the same file it is a phrase between
    # you and every item.
    #
    # Ctrl+Alt+F5, not the F4 that would have sat next to its sibling. A finger
    # that misses the Control key on a chord pressed this often finds Alt+F4,
    # and what that costs is the document.
    ("&View", "&Announce Lists", "Ctrl+Alt+F5", "cmd_toggle_list_announcements", "check"),
    # Overtype, on QUILL's own chord. **Not** the Insert key, which is NVDA's
    # and JAWS's modifier -- binding it would fight the reader. The native
    # control answers Insert itself whatever we do, so QuillLite mirrors that
    # into the Typing Mode cell rather than claiming the key: a reader that is
    # not using Insert as its modifier still gets the Windows behaviour, and
    # the status cell stays true either way.
    ("&View", "&Overwrite Mode", "Ctrl+Alt+Shift+W", "cmd_toggle_overwrite", "check"),
    # What the Tab key does. Checked means Tab types a tab character, which is
    # Notepad's behaviour and QuillLite's default; unchecked runs the smart line
    # indent, which is QUILL's. The default differs on purpose -- a file opened
    # here is as likely to be a configuration file where a tab is data -- and
    # the key differs because it has to: QUILL binds this to the leader chord
    # Ctrl+Shift+Grave, U and QuillLite has no leader key at all.
    (
        "&View",
        "&Tab Key Inserts a Tab Character",
        "Ctrl+Alt+Shift+I",
        "cmd_toggle_tab_mode",
        "check",
    ),
    # Notepad's View menu has carried this checkbox since Windows 95, and it was
    # the one thing QuillLite's status bar could not do: it was always there and
    # there was no way to say otherwise. Hiding it gives the document four more
    # lines and takes nothing away, because everything the bar says is also
    # available on demand -- Document Statistics speaks the counts, and the
    # Position cell's numbers are what Go to Line asks for.
    #
    # Going *to* the bar is F6 and lives in Navigate, because that is a move
    # rather than a setting. F6 with the bar hidden says so rather than failing
    # silently (see cmd_focus_status_bar).
    ("&View", "&Status Bar", "Alt+Shift+B", "cmd_toggle_status_bar", "check"),
    ("&View", "", "", "", "sep"),
    # Notepad's own zoom chords.
    ("&View", "&Increase Text Size", "Ctrl+=", "cmd_zoom_in", ""),
    ("&View", "D&ecrease Text Size", "Ctrl+-", "cmd_zoom_out", ""),
    ("&View", "&Reset Text Size", "Ctrl+0", "cmd_zoom_reset", ""),
    ("&View", "", "", "", "sep"),
    # Ctrl+Shift+G, which is Word's Word Count key and therefore the family's
    # (bad.md 3.1). It was Ctrl+Alt+W here and Ctrl+Shift+W in QUILL -- two
    # editors, two chords, neither of them the one anybody's hands knew.
    ("&View", "Do&cument Statistics", "Ctrl+Shift+G", "cmd_statistics", ""),
    # How *wide* the document is, which is the question somebody formatting for
    # a braille display or a narrow window has -- Document Statistics answers
    # how big it is (bad.md 4.2, Tier 2). On Ctrl+Alt+W, which is the chord its
    # sibling vacated on the same day: one letter, two scopes.
    ("&View", "Li&ne Statistics", "Ctrl+Alt+W", "cmd_line_statistics", ""),
    # A menu bar answers "what is under Format?"; a palette answers "how do I
    # sort lines?", which is the question somebody actually has.
    ("&View", "Command Pa&lette...", "Ctrl+Shift+P", "cmd_command_palette", ""),
    # -- Insert -------------------------------------------------------------
    # Everything that puts something into the document that is not typing. The
    # top three were Edit > Insert and keep their keys exactly; the bottom three
    # are new and are why this is a menu now.
    #
    # Ctrl+Shift+F2 rather than QUILL's Shift+F2: that is Previous Bookmark here.
    ("&Insert", "&Date and Time", "F5", "cmd_insert_datetime", ""),
    ("&Insert", "&Special Character...", "Ctrl+Shift+F2", "cmd_insert_special_character", ""),
    # QUILL's own key, unchanged: Alt+. is the emoji picker in both editors, and
    # a listener who learned it in one should not have to learn it twice. The
    # picker itself is QUILL's too -- a searchable list with a written
    # description of every glyph, which is the only shape of this feature that
    # works at all without sight. It is offered in every document, rich ones
    # included: an emoji is a character rather than markup.
    ("&Insert", "&Emoji...", "Alt+.", "cmd_insert_emoji", ""),
    # Shift+Enter is the chord Word uses for a hard return, so the fingers that
    # need this already know it (#1488). A hard break ends the line without
    # starting a paragraph, which is the distinction a blank line cannot make.
    ("&Insert", "&Line Break", "Shift+Enter", "cmd_insert_line_break", ""),
    # Word's key, and everybody's. A link is the one tag every person who has
    # ever written anything has inserted, and QuillLite had the Markdown and
    # HTML kinds, a tag picker for each, and no way to make it (bad.md 4.2).
    ("&Insert", "Lin&k...", "Ctrl+K", "cmd_insert_link", ""),
    ("&Insert", "", "", "", "sep"),
    # The two tag pickers. Exactly one of them is ever enabled -- whichever the
    # document's language is -- and the other is *dimmed rather than hidden*,
    # because a row that is present and greyed announces itself as unavailable
    # the moment a reader touches it, while a row that has vanished leaves
    # somebody hunting a menu for a feature they know exists. See
    # DocumentMarkupMixin and MARKUP_COMMANDS.
    #
    # The keys are two free neighbours rather than mnemonics, and that is an
    # admission rather than a design: M, H, T and G were all bound years ago, and
    # two adjacent letters under one finger are easier to hold onto as a pair
    # than two unrelated ones. The route worth remembering is the menu's --
    # Alt+I, M and Alt+I, H -- which does spell the thing.
    ("&Insert", "&Markdown Tag...", "Ctrl+Alt+I", "cmd_insert_markdown_tag", ""),
    ("&Insert", "&HTML Tag...", "Ctrl+Alt+O", "cmd_insert_html_tag", ""),
    # -- Format -------------------------------------------------------------
    # WordPad's Format menu, key for key where WordPad has a key: Ctrl+B/I/U,
    # Ctrl+L/E/R/J for alignment, Ctrl+1/2/5 for line spacing, Ctrl+Shift+L for
    # bullets, and Ctrl+Shift+> / < to grow and shrink the selection.
    ("F&ormat", "&Bold", "Ctrl+B", "cmd_bold", ""),
    ("F&ormat", "&Italic", "Ctrl+I", "cmd_italic", ""),
    ("F&ormat", "&Underline", "Ctrl+U", "cmd_underline", ""),
    ("F&ormat", "Gro&w Font", "Ctrl+Shift+.", "cmd_grow_font", ""),
    ("F&ormat", "Shrin&k Font", "Ctrl+Shift+,", "cmd_shrink_font", ""),
    # Word's Ctrl+Shift+N, and the only way back. Every other command here is a
    # toggle or a set, so each one needs you to already know what is applied --
    # bold off needs bold to be on, a twenty-point run needs the ladder walked
    # back down, and a colour, a highlight or a list had no "none" at all.
    # Somebody who cannot glance at the page to see what is still on it had no
    # way to be sure, which is the whole problem this editor exists to solve.
    ("F&ormat", "Normal &Text", "Ctrl+Shift+N", "cmd_normal_text", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "&Headings", "", "", "sub"),
    ("F&ormat", "Structur&e", "", "", "sub"),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Align &Left", "Ctrl+L", "cmd_align_left", ""),
    ("F&ormat", "&Centre", "Ctrl+E", "cmd_align_center", ""),
    ("F&ormat", "Align &Right", "Ctrl+R", "cmd_align_right", ""),
    ("F&ormat", "&Justify", "Ctrl+J", "cmd_align_justify", ""),
    ("F&ormat", "", "", "", "sep"),
    # A ring, not a toggle: bulleted list, numbered list, no list, round again,
    # which is what WordPad's own button on this chord does. As a toggle it
    # meant QuillLite could not make a numbered list in any kind of document
    # (bad.md P1.5). The label says "Lists" because the row is now about all
    # three answers rather than about bullets.
    ("F&ormat", "List&s", "Ctrl+Shift+L", "cmd_cycle_list_style", ""),
    # The three spacings are one decision with three answers, so they are one
    # row that opens rather than three rows to arrow past -- and between them
    # they were holding G, H and P, three of the four letters Headings and
    # Line Spacing needed. A submenu opens its own namespace and hands them back.
    ("F&ormat", "Line Spacin&g", "", "", "sub"),
    ("F&ormat", "", "", "", "sep"),
    # Notepad's Format menu is Word Wrap and Font, and this is the Font half. It
    # was in View, which is where the *size* controls are, and it is the only
    # item in this menu that is not about rich text: it sets the face the whole
    # editor draws in, plain text included. So it keeps an always-on area of its
    # own (see COMMAND_AREA) -- with rich text switched off the Format menu is
    # left holding exactly this one item, which is Notepad's Format menu, which
    # is the right answer for a plain text editor rather than an accident.
    ("F&ormat", "Editor Fo&nt...", "Ctrl+Alt+F", "cmd_editor_font", ""),
    ("F&ormat", "&Font for Selection...", "Ctrl+Shift+F", "cmd_selection_font", ""),
    ("F&ormat", "&Describe Formatting at Cursor", "Ctrl+Shift+D", "cmd_describe", ""),
    ("F&ormat", "", "", "", "sep"),
    # Alt+Shift+F rings: plain text, Markdown, HTML, rich text, round again.
    # It used to toggle between two of those, from before a plain document had a
    # language -- and a key that means "make this the other kind" should reach
    # every kind there is rather than three quarters of them. Each stop
    # announces itself, so you press it until you hear the one you meant.
    #
    # It held Ctrl+Shift+M until 2026-09-16 and gave it up to Set Mark, which is
    # QUILL's chord for that and an editing-loop verb besides (bad.md 3.3).
    # Alt+Shift+F is free in both editors and F is for Format, which is the menu
    # this row lives in.
    ("F&ormat", "Switch Document &Mode", "Alt+Shift+F", "cmd_switch_document_kind", ""),
    # Which markup a *plain* document is written in -- Markdown, HTML, or none.
    # Next to Switch Document Mode because they are the same kind of decision one
    # size down: that one chooses between plain and rich, this one chooses what
    # plain means. It decides four things at once (what Ctrl+B writes, what the
    # heading keys write, which tag picker is offered, and whether the caret can
    # say "Bulleted list, 5 items"), which is exactly why it needs somewhere to
    # be asked rather than being inferred and never mentioned.
    #
    # Also on the status bar's Language cell, where Enter opens this same
    # chooser: the bar is where somebody notices the answer is wrong, and making
    # them leave it to fix it would be a menu hunt for a one-word change.
    ("F&ormat", "D&ocument Language...", "Ctrl+Alt+F6", "cmd_set_language", ""),
    # -- Format > Line Spacing -----------------------------------------------
    # WordPad's own chords, unchanged: Ctrl+1, Ctrl+5, Ctrl+2.
    ("F&ormat|Line Spacin&g", "&Single Spacing", "Ctrl+1", "cmd_spacing_single", ""),
    ("F&ormat|Line Spacin&g", "&One and a Half Spacing", "Ctrl+5", "cmd_spacing_one_half", ""),
    ("F&ormat|Line Spacin&g", "&Double Spacing", "Ctrl+2", "cmd_spacing_double", ""),
    # -- Format > Headings ---------------------------------------------------
    # Six levels, each on its own digit, in a submenu of their own. Seven rows
    # (six headings and the way back to body text) is half of what the Format
    # menu was and none of it is formatting in the Bold-and-Italic sense: a
    # heading is *structure*, which is why it earns a group rather than a place
    # in the middle of the alignment and spacing rows.
    #
    # Five and six are new. The ladder gave them both the 11-point body size, so
    # the editor could set a Heading 5 and then could not tell it from an
    # ordinary paragraph -- heading navigation and the headings list both walked
    # straight past it. They now have sizes of their own
    # (HEADING_POINT_SIZES in quill/ui/richedit_rtf_surface.py), which is what
    # made offering them honest. QUILL gained the same two levels in the same
    # change, because the small product may never be ahead of the editor.
    #
    # The mnemonic is the digit and so is the chord: Alt+O, H, 3 and Ctrl+Alt+3
    # are the same three, which is one thing to remember rather than two.
    ("F&ormat|&Headings", "Heading &1", "Ctrl+Alt+1", "cmd_heading_1", ""),
    ("F&ormat|&Headings", "Heading &2", "Ctrl+Alt+2", "cmd_heading_2", ""),
    ("F&ormat|&Headings", "Heading &3", "Ctrl+Alt+3", "cmd_heading_3", ""),
    ("F&ormat|&Headings", "Heading &4", "Ctrl+Alt+4", "cmd_heading_4", ""),
    ("F&ormat|&Headings", "Heading &5", "Ctrl+Alt+5", "cmd_heading_5", ""),
    ("F&ormat|&Headings", "Heading &6", "Ctrl+Alt+6", "cmd_heading_6", ""),
    ("F&ormat|&Headings", "", "", "", "sep"),
    ("F&ormat|&Headings", "Body &Text", "Ctrl+Alt+0", "cmd_heading_0", ""),
    # -- Format > Structure --------------------------------------------------
    # Restructuring, on QUILL's own four keys. Until now QuillLite could create
    # and navigate headings but never rearrange them, so reorganising a
    # document fell back to cut and paste -- which means selecting from one
    # heading to the start of the next, a boundary you cannot see and have to
    # find by ear, and which loses your place when you get it wrong.
    #
    # A submenu because the Format menu is out of letters: Promote Heading
    # wanted H (taken by One and a Half Spacing), Move Section Up wanted U
    # (Underline) and Move Section Down wanted W (Grow Font). A submenu opens
    # its own mnemonic namespace instead of forcing a worse letter on three
    # neighbours -- the same answer Edit's Matches and Selection submenus are.
    # Its own title takes E, which the Format menu itself does not use.
    ("F&ormat|Structur&e", "Promote &Heading", "Alt+Shift+Left", "cmd_promote_heading", ""),
    ("F&ormat|Structur&e", "D&emote Heading", "Alt+Shift+Right", "cmd_demote_heading", ""),
    ("F&ormat|Structur&e", "Move Section &Up", "Alt+Shift+Up", "cmd_move_section_up", ""),
    ("F&ormat|Structur&e", "Move Section Do&wn", "Alt+Shift+Down", "cmd_move_section_down", ""),
    ("F&ormat|Structur&e", "", "", "", "sep"),
    # The four rows above, in one window. QUILL has had this since #303 and
    # QuillLite already had both halves of it -- a headings list and section
    # moves -- so what was missing was only the surface that puts them
    # together (bad.md P2.13, Tier 2). QUILL's own chord is Ctrl+Alt+Shift+H,
    # which is Previous Heading here, and Ctrl+Alt+Shift+O is Sound Scheme --
    # the letter it is named after is taken twice over. Alt+Shift+O keeps the O
    # and is free in both.
    (
        "F&ormat|Structur&e",
        "Heading &Organizer...",
        "Alt+Shift+O",
        "cmd_heading_organizer",
        "",
    ),
    # -- Navigate -----------------------------------------------------------
    # Where you are, and how to get somewhere else. The one menu Notepad and
    # WordPad do not have, because a sighted reader navigates by scrolling and
    # glancing and a listener cannot.
    # Back and Forward, on the pair every browser and file window has used for
    # thirty years, and the pair QUILL binds. The undo for navigation: without
    # it every jump is one-way, and somebody who followed a heading or landed on
    # a search hit has no way back to the paragraph they were writing except to
    # remember a line number they were never told.
    #
    # At the top because they are the most used rows here, and always present:
    # they belong to neither the headings area nor the bookmarks one, which is
    # also what keeps this menu from emptying when both are switched off.
    #
    # QuillLite is Windows-only, so the macOS Cmd+[ / Cmd+] fallback QUILL
    # carries for #609 has nothing to answer here.
    ("&Navigate", "Go Bac&k", "Alt+Left", "cmd_back_location", ""),
    ("&Navigate", "Go For&ward", "Alt+Right", "cmd_forward_location", ""),
    ("&Navigate", "", "", "", "sep"),
    ("&Navigate", "&Next Heading", "Ctrl+Alt+H", "cmd_next_heading", ""),
    ("&Navigate", "&Previous Heading", "Ctrl+Alt+Shift+H", "cmd_previous_heading", ""),
    ("&Navigate", "&List Headings...", "Ctrl+Alt+L", "cmd_list_headings", ""),
    ("&Navigate", "", "", "", "sep"),
    # Folding. A reading aid rather than a change to the document: nothing
    # is hidden from the caret and a folded section reads exactly as it
    # reads unfolded, which is QUILL's decision too -- a fold that really
    # hid text would be a document whose contents depend on a view state,
    # and the first thing it would break is Find (bad.md P3.6).
    # Function keys rather than Minus and Equal. Those two are unparseable to
    # wx.AcceleratorEntry, which does not complain -- it rejects the whole
    # string, leaving the menu advertising a key that can never fire. Subtract
    # and Add parse in wx and not in QuillLite's own reader, which is the same
    # failure from the other end. F9 and F10 are read by both, and a fold is a
    # once-in-a-while verb rather than an editing-loop one, which is where the
    # F-keys past F8 belong (bad.md rule 9).
    ("&Navigate", "&Fold or Unfold Section", "Ctrl+Shift+F9", "cmd_toggle_fold", ""),
    ("&Navigate", "Ne&xt Section", "Ctrl+Alt+Shift+Down", "cmd_next_fold", ""),
    ("&Navigate", "Previo&us Section", "Ctrl+Alt+Shift+Up", "cmd_previous_fold", ""),
    ("&Navigate", "Unfold &Everything", "Ctrl+Shift+F10", "cmd_unfold_all", ""),
    ("&Navigate", "", "", "", "sep"),
    ("&Navigate", "&Bookmarks", "", "", "sub"),
    ("&Navigate", "", "", "", "sep"),
    # F6 is the region key every Windows app uses, and the one QUILL's own
    # status bar answers. The menu item exists so the key is discoverable
    # rather than folklore -- and it is here rather than in View because going
    # to the status bar is a move, not a setting. Whether the bar is there at
    # all is View's checkbox, one menu to the left.
    ("&Navigate", "&Status Bar", "F6", "cmd_focus_status_bar", ""),
    ("&Navigate", "&Go To Anything...", "Ctrl+Alt+Shift+A", "cmd_go_to_anything", ""),
    # -- Navigate > Bookmarks ------------------------------------------------
    # A place you meant to come back to. There is no scrollbar thumb to remember
    # the position of and no glance that finds the place again, so a bookmark is
    # not a convenience here.
    #
    # A submenu because of the nine numbered rows: Set Bookmark 1 to 9 is most
    # of the menu by row count and almost none of it by use, and a listener
    # arrowing down Navigate had to walk past all nine to reach anything else.
    # In a submenu they are one Right arrow away, and out of the way.
    ("&Navigate|&Bookmarks", "&Set Bookmark", "Ctrl+Shift+B", "cmd_set_bookmark", ""),
    ("&Navigate|&Bookmarks", "&Go to Bookmark...", "Alt+Shift+G", "cmd_list_bookmarks", ""),
    ("&Navigate|&Bookmarks", "&Next Bookmark", "F2", "cmd_next_bookmark", ""),
    ("&Navigate|&Bookmarks", "&Previous Bookmark", "Shift+F2", "cmd_previous_bookmark", ""),
    ("&Navigate|&Bookmarks", "&Clear All Bookmarks", "Ctrl+Alt+B", "cmd_clear_bookmarks", ""),
    ("&Navigate|&Bookmarks", "", "", "", "sep"),
    # The one with no number. QUILL has had it for years and QuillLite had
    # nothing like it, which is backwards for two editors whose keys are meant
    # to agree -- so it crosses on QUILL's own two chords (bad.md P2.20).
    # A pin you drop before going to look something up: no dialog, no label, no
    # list, and gone when the document closes. Its own group between the five
    # that manage the nine and the nine themselves, because it is neither.
    ("&Navigate|&Bookmarks", "Set &Temporary Bookmark", "Ctrl+Alt+J", "cmd_set_temp_bookmark", ""),
    (
        "&Navigate|&Bookmarks",
        "Go to Temporar&y Bookmark",
        "Ctrl+Shift+J",
        "cmd_go_to_temp_bookmark",
        "",
    ),
    ("&Navigate|&Bookmarks", "", "", "", "sep"),
    ("&Navigate|&Bookmarks", "Set Bookmark &1", "Ctrl+Shift+1", "cmd_set_bookmark_1", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &2", "Ctrl+Shift+2", "cmd_set_bookmark_2", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &3", "Ctrl+Shift+3", "cmd_set_bookmark_3", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &4", "Ctrl+Shift+4", "cmd_set_bookmark_4", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &5", "Ctrl+Shift+5", "cmd_set_bookmark_5", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &6", "Ctrl+Shift+6", "cmd_set_bookmark_6", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &7", "Ctrl+Shift+7", "cmd_set_bookmark_7", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &8", "Ctrl+Shift+8", "cmd_set_bookmark_8", ""),
    ("&Navigate|&Bookmarks", "Set Bookmark &9", "Ctrl+Shift+9", "cmd_set_bookmark_9", ""),
    # -- Tools --------------------------------------------------------------
    # What is left once line work has gone to Edit where it belongs: the things
    # that are genuinely *tools* rather than editing -- the spell checker, case
    # conversion, indenting, the files-and-formats dialog, abbreviations, and
    # the two ways to change what QuillLite itself is. Tools > Options is where
    # Windows applications have kept their settings since Word 6, which is why
    # Preferences and Customize Features are here rather than in View.
    ("&Tools", "&Spelling", "", "", "sub"),
    ("&Tools", "&Change Case", "", "", "sub"),
    ("&Tools", "Indentin&g", "", "", "sub"),
    ("&Tools", "", "", "", "sep"),
    # Both are shown in the status bar and both used to be read-only: QuillLite
    # wrote back whatever it read, which is the right default and a dead end for
    # anyone who needs a UTF-8 copy of a Windows-1252 file.
    ("&Tools", "&File Encoding and Line Endings...", "Ctrl+Alt+E", "cmd_file_format", ""),
    ("&Tools", "", "", "", "sep"),
    # Type a short form and a space, get the long one. QUILL's engine, QUILL's
    # manager dialog, and QuillLite's own library unless Preferences says share.
    # The gallery, and the manager beside it. Abbreviations expand when you
    # type the trigger, which is perfect for the six you use daily and useless
    # for the fortieth, whose trigger you cannot remember. QUILL has had a
    # snippet gallery since its snippets shipped (bad.md 4.2 Tier 3).
    # Not Insert: QuillLite reserves it, because it is the screen reader's
    # own modifier and a binding on it is a binding the reader eats. Not
    # &S either -- Spelling has it in this menu (GATE-14).
    ("&Tools", "Snippe&ts...", "Alt+Shift+I", "cmd_snippet_gallery", ""),
    ("&Tools", "&Manage Abbreviations...", "Ctrl+Alt+A", "cmd_manage_abbreviations", ""),
    # The switch beside the manager, and not the same thing as the Customize
    # Features checkbox even though it moves it: expansion is the one feature
    # here that fires *while you type*, so the moment you need it off is the
    # moment it has just expanded something you meant to keep -- and a dialog
    # three keystrokes away is three keystrokes too many. Alt+Shift+A from the
    # document, and the check mark says which way it is now.
    #
    # No area of its own, deliberately: the switch has to still be there when
    # the thing it switches is off, or it can only ever be turned one way.
    ("&Tools", "&Expand Abbreviations", "Alt+Shift+A", "cmd_toggle_abbreviations", "check"),
    ("&Tools", "", "", "", "sep"),
    # The only place the two settings with no menu item of their own -- what
    # Ctrl+N creates, and how often unsaved work is copied aside -- can be
    # changed at all. Ctrl+comma is where Windows has put preferences for a
    # decade.
    ("&Tools", "&Preferences...", "Ctrl+,", "cmd_preferences", ""),
    # Back up the configuration, and put it back on the next machine (#1501).
    # Beside Preferences because that is what it is a copy of. Neither carries
    # anything that describes *this* computer -- no recent files, no window
    # size, no update timestamp -- so the file is a configuration rather than a
    # snapshot of one desk.
    ("&Tools", "&Back Up Settings...", "Ctrl+Alt+F11", "cmd_backup_settings", ""),
    ("&Tools", "Restore Sett&ings...", "Ctrl+Alt+F12", "cmd_restore_settings", ""),
    # Turning a whole area off is QUILL's own idea, and it belongs here more
    # than anywhere: the way QuillLite stays small is that somebody who does not
    # want rich text can remove the Format menu entirely rather than learn to
    # ignore it.
    # Once a year, and therefore on the F-keys. These three held
    # Ctrl+Alt+Shift+F, Q and D -- three-modifier LETTER chords that editing
    # verbs want in QUILL (Search in Files, Duplicate Selection) -- for
    # commands nobody runs in the editing loop. The F-keys past F9 are empty
    # in both editors (bad.md rule 9, P2.9).
    ("&Tools", "C&ustomize Features...", "Ctrl+Alt+F10", "cmd_customize_features", ""),
    # Which keys do what, beside which features exist. Never switchable, for
    # the same reason as its two neighbours: the surface that repairs a key
    # somebody broke cannot be behind a key.
    #
    # Ctrl+Alt+Shift+R rather than anything spelling "keyboard": K is Set
    # Mark, lowercase and Remove Blank Lines three times over, and moving a
    # real command out of the way to make room for the dialog that moves
    # commands would be a poor trade. R is for rebind. The mnemonic is the
    # K the menu still has free.
    ("&Tools", "&Keyboard Manager...", "Ctrl+Alt+Shift+R", "cmd_keyboard_manager", ""),
    # -- Tools > Spelling ----------------------------------------------------
    # A submenu rather than a menu on the bar: neither Notepad nor WordPad has a
    # Spelling menu, and Word keeps spelling under Tools. The whole area still
    # switches off in one checkbox, because a submenu with nothing left in it is
    # removed along with its title.
    #
    # F7 is the spelling key in Word, in QUILL, and in every editor that has
    # one. The family around it is free, so the whole submenu sits on F7 with a
    # modifier -- which means one key to remember rather than six.
    ("&Tools|&Spelling", "Check &Spelling...", "F7", "cmd_spell_review", ""),
    # Alt+Shift+F7 rather than Shift+F7 since 2026-09-16: Shift+F7 is the
    # Thesaurus in Word and in QUILL, so a habit from either landed here on
    # something else. QuillLite has no thesaurus (it needs an asset
    # download), and the right answer for a key it cannot honour is to leave
    # it unbound rather than to give it a different meaning (bad.md 3.6).
    (
        "&Tools|&Spelling",
        "Spelling for &This Word",
        "Alt+Shift+F7",
        "cmd_spell_word_at_cursor",
        "",
    ),
    ("&Tools|&Spelling", "", "", "", "sep"),
    # Every misspelling at once, with the line each is on. Ctrl+F7 N times is
    # the alternative and answers a different question -- it moves you to the
    # next one, and this says how many there are (bad.md 4.2, Tier 2). QUILL's
    # own chord; the one row of this submenu that is not on an F7 chord,
    # because it is a list rather than a step.
    ("&Tools|&Spelling", "&List Misspellings...", "Alt+Shift+L", "cmd_misspelling_list", ""),
    ("&Tools|&Spelling", "&Next Misspelling", "Ctrl+F7", "cmd_next_misspelling", ""),
    ("&Tools|&Spelling", "&Previous Misspelling", "Ctrl+Shift+F7", "cmd_previous_misspelling", ""),
    ("&Tools|&Spelling", "", "", "", "sep"),
    # Off the F7 row entirely, and deliberately. Alt+F7 was this, and Alt+F7
    # is Next Misspelling in Word -- so the one command in the family that
    # writes to a stored dictionary sat where a navigation habit lands. It is
    # Ctrl+Alt+F9 in both editors now (bad.md 3.6, P0.3).
    (
        "&Tools|&Spelling",
        "&Add Word to Dictionary",
        "Ctrl+Alt+F9",
        "cmd_add_word_to_dictionary",
        "",
    ),
    # Notepad has this item, and it earns its place: the file-type rule means
    # the check is sometimes off for a reason nobody was told, so there has to
    # be one visible thing that says what the state is and changes it.
    ("&Tools|&Spelling", "Check &While Typing", "Ctrl+Alt+F7", "cmd_toggle_live_spelling", "check"),
    ("&Tools|&Spelling", "", "", "", "sep"),
    # The twelve answers to "how is a misspelling *said*", in one window. On the
    # last free F7 chord, which keeps the whole submenu on one key: F7 and a
    # modifier, six times over, rather than six unrelated keys to remember.
    (
        "&Tools|&Spelling",
        "Ann&ouncements...",
        "Ctrl+Alt+Shift+F7",
        "cmd_spelling_voice_settings",
        "",
    ),
    # Sound belongs in Tools beside Preferences, not in View: it is a setting
    # about the app rather than a way of looking at the document. Not
    # switchable by Customize Features for the same reason Preferences is not --
    # switching off the menu that holds the switch is a door that locks from
    # the inside, and somebody who has silenced every sound needs a way back.
    # Quiet mode, on the same chord QUILL uses. A checkable row rather than
    # two commands: the state is the question ('am I muted?') and a check
    # mark is the only thing that answers it without pressing anything.
    ("&Tools", "&Quiet Mode", "Alt+Shift+M", "cmd_toggle_quiet_mode", "check"),
    ("&Tools", "S&ound Scheme...", "Ctrl+Alt+Shift+O", "cmd_sound_scheme", ""),
    # -- Tools > Change Case -------------------------------------------------
    ("&Tools|&Change Case", "&UPPERCASE", "Ctrl+Shift+U", "cmd_upper_case", ""),
    ("&Tools|&Change Case", "&lowercase", "Ctrl+Shift+K", "cmd_lower_case", ""),
    # Ctrl+Shift+T since 2026-09-16: Ctrl+Shift+G is Word Count in Word, and
    # both editors put Document Statistics there (bad.md 3.4).
    ("&Tools|&Change Case", "&Title Case", "Ctrl+Shift+T", "cmd_title_case", ""),
    # The two QUILL registered and never bound, so its own Change Case offered
    # five in the menu and three from the keyboard. "Invert" rather than
    # "Toggle" because a person asked to describe it says "it swaps them".
    ("&Tools|&Change Case", "Sentence &case", "Ctrl+Alt+Shift+U", "cmd_sentence_case", ""),
    ("&Tools|&Change Case", "In&vert Case", "Ctrl+Alt+Shift+N", "cmd_toggle_case", ""),
    # -- Tools > Indenting ---------------------------------------------------
    # QUILL's own chords, unchanged. Not part of the line-tools area and
    # deliberately so: indenting a line is basic editing, and an editor that
    # cannot indent because somebody switched off the line tools is broken
    # rather than small.
    ("&Tools|Indentin&g", "&Indent", "Ctrl+]", "cmd_indent", ""),
    ("&Tools|Indentin&g", "&Outdent", "Ctrl+[", "cmd_outdent", ""),
    # Describe Indent Depth landed in QUILL first (2026-09-09,
    # ``format.describe_indent_depth``, the same chord), which is the order the
    # house rule requires: QuillLite may never be ahead of the editor. Leading
    # whitespace is the one part of a line a screen reader does not read back,
    # so this is the only way to ask what shape the document is in -- and QUILL
    # had the phrasing for two years with nothing bound to it, only an
    # announce-as-you-move toggle that speaks while you move and goes quiet the
    # moment you stop to wonder.
    ("&Tools|Indentin&g", "&Describe Indent Depth", "Ctrl+Alt+Shift+V", "cmd_describe_indent", ""),
    ("&Tools|Indentin&g", "", "", "", "sep"),
    # The single most common fix a person makes to somebody else's file, and
    # the other half of the concession that QuillLite is where a .py gets
    # opened (bad.md 4.2, Tier 2). On F-keys past F9 by rule 9: they are real
    # commands and they are not run in the editing loop.
    ("&Tools|Indentin&g", "Convert to &Spaces", "Alt+F11", "cmd_indentation_to_spaces", ""),
    ("&Tools|Indentin&g", "Convert to &Tabs", "Alt+F12", "cmd_indentation_to_tabs", ""),
    # -- Window -------------------------------------------------------------
    # Ctrl+F6 is the Windows MDI convention and Ctrl+Tab is what everyone
    # actually presses; both are bound, because a key somebody expects and
    # does not get is indistinguishable from a broken app.
    ("&Window", "&Next Window", "Ctrl+Tab", "cmd_next_window", ""),
    ("&Window", "Ne&xt Window (MDI)", "Ctrl+F6", "cmd_next_window_mdi", ""),
    ("&Window", "&Previous Window", "Ctrl+Shift+Tab", "cmd_previous_window", ""),
    ("&Window", "", "", "", "sep"),
    # QUILL's command, on QUILL's key (family rule 2). Reported by somebody who
    # opened QuillLite to sixty-nine restored windows and found that the only
    # route back to one document was Ctrl+W sixty-eight times, with a save
    # prompt on each. Ctrl+F4 closes this one; Ctrl+Shift+F4 closes the others.
    ("&Window", "&Close Other Documents", "Ctrl+Shift+F4", "cmd_close_other_windows", ""),
    # -- Help ---------------------------------------------------------------
    # F1 belongs to the family's context help (quill.ui.app_context_help): it
    # answers with what *this* window is for and then what the focused control
    # does. The static key list moved to Ctrl+F1 rather than taking F1 from the
    # engine every other QuillVille app answers with.
    ("&Help", "&Help for This Window", "F1", "cmd_context_help", ""),
    # The family key for lessons, and the family window. Ctrl+Alt+F1 is what
    # Radio, Cast, Weather and QUILL answer with (bad.md P3.2).
    ("&Help", "&Tutorials...", "Ctrl+Alt+F1", "cmd_tutorials", ""),
    ("&Help", "&Keyboard Shortcuts", "Ctrl+F1", "cmd_shortcuts", ""),
    # The family item, on the family key: QuillLite is the app whose users
    # are least likely to know where else to write.
    ("&Help", "&Get Help from Support...", "Ctrl+Alt+F2", "cmd_get_help_from_support", ""),
    # The family key. Before this QuillLite had no way at all to learn that a
    # newer version existed -- see quill.apps.lite_updates.
    ("&Help", "Check for &Updates...", "Ctrl+Alt+U", "cmd_check_updates", ""),
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


def shortcut_text(keymap: dict[str, str] | None = None) -> str:
    """The Keyboard Shortcuts window's body, generated from the same table.

    *keymap* is the resolved binding per handler
    (:func:`quill.core.lite.keymap.load_keymap`). Passing None gives the shipped
    keys, which is what a test that predates rebinding is asking for -- but the
    app always passes its own, because a shortcut list that shows the key a
    command *used* to have is the one surface where a wrong key gets learned.

    Two things are appended that the table cannot carry: the Alt+digit window
    switches (built per window, from however many are open) and the heading
    ladder, which is the one fact about rich mode that saves a support email.
    """
    lines = [f"{APP_NAME} {APP_VERSION} keyboard shortcuts", ""]
    current = ""
    for menu, label, default_key, handler, kind in COMMANDS:
        key = (keymap or {}).get(handler, default_key)
        # A submenu's title row is not a shortcut; the submenu gets its own
        # heading below, from the rows that carry the keys.
        if kind in {"sep", "sub"}:
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
        "Headings in rich text are bold plus a point size: 20, 16, 14, 12, 11.5",
        "and 10.5 point for levels 1 to 6, and 11 point for body text. That is",
        "QUILL's own ladder, so a document saved here reads as headings in Word.",
    ]
    return "\n".join(lines)


def plain_label(label: str) -> str:
    """*label* with its mnemonic ampersands removed, for reading aloud."""
    return _plain(label)
