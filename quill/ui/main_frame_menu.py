"""Menu-bar construction for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``MenuBuilderMixin`` and ``_build_menu`` resolves identically through the MRO.
The method is fully self-contained: it reads ``wx`` from ``self._wx`` and
reaches every menu id, submenu, label helper, and refresh routine through
``self``, so no module-level imports are required here.
"""

from __future__ import annotations


class MenuBuilderMixin:
    def _build_menu(self) -> None:
        wx = self._wx
        menu_bar = wx.MenuBar()

        self._id_new = wx.ID_NEW
        self._id_open = wx.ID_OPEN
        self._id_save = wx.ID_SAVE
        self._id_save_as = wx.ID_SAVEAS
        self._id_exit = wx.ID_EXIT
        self._id_palette = wx.NewIdRef()
        self._id_preferences = wx.NewIdRef()
        self._id_menu_editor = wx.NewIdRef()
        self._id_open_url = wx.NewIdRef()
        self._id_open_remote = wx.NewIdRef()
        self._id_save_to_remote = wx.NewIdRef()
        self._id_save_copy_to_remote = wx.NewIdRef()
        self._id_manage_remote_sites = wx.NewIdRef()
        self._id_github_repository = wx.NewIdRef()
        self._id_github_file_url = wx.NewIdRef()
        self._id_github_save_back = wx.NewIdRef()
        self._id_github_manage_accounts = wx.NewIdRef()
        self._id_ssh_quick_connect = wx.NewIdRef()
        self._id_ssh_site_manager = wx.NewIdRef()
        self._id_close_document = wx.NewIdRef()
        self._id_save_all = wx.NewIdRef()
        self._id_reload_from_disk = wx.NewIdRef()
        self._id_check_external_changes = wx.NewIdRef()
        self._id_restore_backup = wx.NewIdRef()
        self._id_save_session = wx.NewIdRef()
        self._id_open_session = wx.NewIdRef()
        self._id_clear_recent_sessions = wx.NewIdRef()
        self._id_page_setup = wx.NewIdRef()
        self._id_print = wx.NewIdRef()
        self._id_save_plain_text = wx.NewIdRef()
        self._id_clear_recent = wx.NewIdRef()
        self._sessions_menu = wx.Menu()
        self._open_documents_menu = wx.Menu()
        self._recent_sessions_menu = wx.Menu()
        self._id_new_notebook = wx.NewIdRef()
        self._id_new_notebook_from_folder = wx.NewIdRef()
        self._id_open_notebook = wx.NewIdRef()
        self._id_notebook_save_snapshot = wx.NewIdRef()
        self._id_notebook_restore_snapshot = wx.NewIdRef()
        self._id_manage_notebook_snapshots = wx.NewIdRef()
        self._id_toggle_entries_panel = wx.NewIdRef()
        self._id_go_to_entry_in_notebook = wx.NewIdRef()
        self._id_go_to_heading_in_notebook = wx.NewIdRef()
        self._id_go_to_bookmark_in_notebook = wx.NewIdRef()
        self._id_go_to_sticky_note_in_notebook = wx.NewIdRef()

        file_menu = wx.Menu()
        # --- Create / open ---
        file_menu.Append(self._id_new, self._menu_label("&New", "file.new"))
        file_menu.Append(self._id_open, self._menu_label("&Open...", "file.open"))
        self._recent_menu = wx.Menu()
        file_menu.AppendSubMenu(self._recent_menu, "Open &Recent")
        self._refresh_recent_menu()
        file_menu.Append(self._id_open_url, "Open from &URL...")
        ssh_menu = wx.Menu()
        ssh_menu.Append(self._id_ssh_quick_connect, "&Quick Connect...")
        ssh_menu.Append(self._id_ssh_site_manager, "&Site Manager...")
        file_menu.AppendSubMenu(ssh_menu, "Open over SS&H")
        remote_menu = wx.Menu()
        remote_menu.Append(
            self._id_open_remote,
            self._menu_label("&Open from Remote...", "file.open_from_remote"),
        )
        remote_menu.Append(
            self._id_save_to_remote,
            self._menu_label("&Save to Remote", "file.save_to_remote"),
        )
        remote_menu.Append(
            self._id_save_copy_to_remote,
            self._menu_label("Save &Copy to Remote...", "file.save_copy_to_remote"),
        )
        remote_menu.AppendSeparator()
        remote_menu.Append(
            self._id_github_repository,
            self._menu_label("&GitHub Repository...", "file.open_github_repository"),
        )
        remote_menu.Append(
            self._id_github_file_url,
            self._menu_label("GitHub File &URL...", "file.open_github_file_url"),
        )
        remote_menu.Append(
            self._id_github_save_back,
            self._menu_label("&Save to GitHub...", "file.github_save_back"),
        )
        remote_menu.AppendSeparator()
        remote_menu.Append(
            self._id_manage_remote_sites,
            self._menu_label("&Manage Remote Sites...", "file.manage_remote_sites"),
        )
        remote_menu.Append(
            self._id_github_manage_accounts,
            self._menu_label("Manage &GitHub Accounts...", "file.github_manage_accounts"),
        )
        file_menu.AppendSubMenu(remote_menu, "Open from &Remote")
        file_menu.AppendSubMenu(self._sessions_menu, "&Snapshots")
        file_menu.AppendSeparator()
        # --- Save ---
        file_menu.Append(self._id_save, self._menu_label("&Save", "file.save"))
        file_menu.Append(self._id_save_as, self._menu_label("Save &As...", "file.save_as"))
        file_menu.Append(self._id_save_all, "Save A&ll")
        file_menu.Append(self._id_save_plain_text, "Save As Plain &Text...")
        file_menu.AppendSeparator()
        # --- Restore / reload ---
        file_menu.Append(self._id_reload_from_disk, "&Reload from Disk")
        file_menu.Append(self._id_check_external_changes, "Check for E&xternal Changes...")
        file_menu.Append(self._id_restore_backup, "Restore &Backup...")
        file_menu.AppendSeparator()
        # --- Current-file operations (Power Tools recirculation, menus.md Phase 4) ---
        self._append_power_tools_file_ops_items(file_menu)
        file_menu.AppendSeparator()
        # --- Notebook ---
        notebook_menu = wx.Menu()
        notebook_menu.Append(
            self._id_new_notebook,
            self._menu_label("&New Notebook...", "file.new_notebook"),
        )
        notebook_menu.Append(
            self._id_new_notebook_from_folder,
            self._menu_label("New from &Folder...", "file.new_notebook_from_folder"),
        )
        notebook_menu.Append(
            self._id_open_notebook,
            self._menu_label("&Open Notebook...", "file.open_notebook"),
        )
        notebook_menu.AppendSeparator()
        notebook_menu.Append(
            self._id_notebook_save_snapshot,
            self._menu_label("&Save Snapshot...", "file.save_snapshot"),
        )
        notebook_menu.Append(
            self._id_notebook_restore_snapshot,
            self._menu_label("Restore &Snapshot...", "file.manage_snapshots"),
        )
        notebook_menu.Append(
            self._id_manage_notebook_snapshots,
            self._menu_label("&Manage Snapshots...", "file.manage_snapshots"),
        )
        file_menu.AppendSubMenu(notebook_menu, "&Notebook")
        file_menu.AppendSeparator()
        # --- Print ---
        file_menu.Append(self._id_page_setup, "Pa&ge Setup...")
        file_menu.Append(self._id_print, self._menu_label("&Print...", "file.print"))
        file_menu.AppendSeparator()
        # --- Close ---
        file_menu.Append(
            self._id_close_document,
            self._menu_label("&Close Document", "file.close_document"),
        )
        file_menu.Append(self._id_exit, self._menu_label("E&xit", "app.exit"))

        self._id_find = wx.NewIdRef()
        self._id_undo = wx.NewIdRef()
        self._id_redo = wx.NewIdRef()
        self._id_copy_with_source = wx.NewIdRef()
        self._id_toggle_extend_selection_mode = wx.NewIdRef()
        self._id_start_selection = wx.NewIdRef()
        self._id_complete_selection = wx.NewIdRef()
        self._id_reselect = wx.NewIdRef()
        self._id_go_to_start_of_selection = wx.NewIdRef()
        self._id_copy_all = wx.NewIdRef()
        self._id_unselect_all = wx.NewIdRef()
        self._id_say_selected = wx.NewIdRef()
        self._id_read_all = wx.NewIdRef()
        self._id_replace = wx.NewIdRef()
        self._id_replace_all = wx.NewIdRef()
        self._id_find_next = wx.NewIdRef()
        self._id_find_previous = wx.NewIdRef()
        self._id_find_all_matches = wx.NewIdRef()
        self._id_search_in_files = wx.NewIdRef()
        self._id_replace_in_files = wx.NewIdRef()
        self._id_insert_link = wx.NewIdRef()
        self._id_follow_link = wx.NewIdRef()
        self._id_word_prediction = wx.NewIdRef()
        self._id_select_line = wx.NewIdRef()
        self._id_select_paragraph = wx.NewIdRef()
        self._id_select_block = wx.NewIdRef()
        self._id_select_to_start_of_line = wx.NewIdRef()
        self._id_select_to_end_of_line = wx.NewIdRef()
        self._id_select_to_start_of_document = wx.NewIdRef()
        self._id_select_to_end_of_document = wx.NewIdRef()
        self._id_expand_selection = wx.NewIdRef()
        self._id_shrink_selection = wx.NewIdRef()
        self._id_set_mark = wx.NewIdRef()
        self._id_pop_mark = wx.NewIdRef()
        self._id_exchange_point_mark = wx.NewIdRef()
        self._id_list_marks = wx.NewIdRef()
        self._id_set_named_mark = wx.NewIdRef()
        self._id_jump_to_named_mark = wx.NewIdRef()
        self._id_open_review_buffer = wx.NewIdRef()
        self._id_sort_lines_ascending = wx.NewIdRef()
        self._id_sort_lines_descending = wx.NewIdRef()
        self._id_reverse_lines = wx.NewIdRef()
        self._id_remove_duplicate_lines = wx.NewIdRef()
        self._id_trim_trailing_whitespace = wx.NewIdRef()
        self._id_normalize_whitespace = wx.NewIdRef()
        self._id_convert_indentation_to_spaces = wx.NewIdRef()
        self._id_convert_indentation_to_tabs = wx.NewIdRef()
        # Copy Tray slot IDs (Edit > Copy Tray submenu)
        self._id_copy_tray_slots: list[wx.WindowIDRef] = [wx.NewIdRef() for _ in range(12)]
        self._id_paste_tray_slots: list[wx.WindowIDRef] = [wx.NewIdRef() for _ in range(12)]
        self._id_open_copy_tray = wx.NewIdRef()
        self._id_clear_all_tray_slots = wx.NewIdRef()
        self._id_copy_to_next_slot = wx.NewIdRef()
        self._id_search_tray_slots = wx.NewIdRef()
        edit_menu = wx.Menu()
        edit_menu.Append(self._id_undo, self._menu_label("&Undo", "edit.undo"))
        edit_menu.Append(self._id_redo, self._menu_label("&Redo", "edit.redo"))
        edit_menu.AppendSeparator()
        # Standard clipboard items. wxTextCtrl routes these IDs natively, so
        # we don't need to bind handlers; the active editor handles them.
        edit_menu.Append(wx.ID_CUT, "Cu&t\tCtrl+X")
        edit_menu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
        edit_menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V")
        # Paste variants and New Document from Clipboard (power tools)
        self._append_power_tools_edit_items(edit_menu)
        # Copy Tray submenu — per-slot items use explicit IDs for direct bindings;
        # open/clear dialog commands are recirculated from the manifest via the
        # helper (menus.md Phase 4 pattern).
        tray_menu = wx.Menu()
        for _n in range(1, 13):
            tray_menu.Append(
                self._id_copy_tray_slots[_n - 1],
                self._menu_label(f"Copy to Slot &{_n}", f"edit.copy_to_tray_{_n}"),
            )
        tray_menu.AppendSeparator()
        for _n in range(1, 13):
            tray_menu.Append(
                self._id_paste_tray_slots[_n - 1],
                self._menu_label(f"Paste from Slot &{_n}", f"edit.paste_from_tray_{_n}"),
            )
        tray_menu.AppendSeparator()
        tray_menu.Append(
            self._id_copy_to_next_slot,
            self._menu_label("Copy to &Next Empty Slot", "edit.copy_to_next_slot"),
        )
        tray_menu.Append(
            self._id_search_tray_slots,
            self._menu_label("&Search Tray Slots...", "edit.search_tray_slots"),
        )
        tray_menu.AppendSeparator()
        self._append_power_tools_copy_tray_items(tray_menu)
        edit_menu.AppendSubMenu(tray_menu, "Copy &Tray")
        edit_menu.Append(
            self._id_copy_with_source,
            self._menu_label("Copy With &Attribution", "edit.copy_with_source"),
        )
        edit_menu.AppendSeparator()
        edit_menu.Append(wx.ID_SELECTALL, "Select &All\tCtrl+A")
        edit_menu.AppendSeparator()
        # Find / Replace and the find-navigation commands live in Edit (their
        # conventional home and their edit.* command ids); the Search menu is
        # reserved for cross-file search (menus.md Phase 3).
        edit_menu.Append(self._id_find, self._menu_label("Fin&d...", "edit.find"))
        edit_menu.Append(
            self._id_replace,
            self._menu_label("Rep&lace...", "edit.replace"),
        )
        edit_menu.Append(
            self._id_find_next,
            self._menu_label("Find &Next", "edit.find_next"),
        )
        edit_menu.Append(
            self._id_find_previous,
            self._menu_label("Find Pre&vious", "edit.find_previous"),
        )
        edit_menu.Append(
            self._id_find_all_matches,
            self._menu_label("Find All &Matches", "edit.find_all_matches"),
        )
        edit_menu.AppendSeparator()
        edit_menu.Append(
            self._id_word_prediction,
            self._menu_label("&Word Prediction...", "edit.word_prediction"),
        )
        edit_menu.AppendSeparator()
        selection_menu = wx.Menu()
        selection_menu.AppendCheckItem(
            self._id_toggle_extend_selection_mode,
            self._menu_label(
                "E&xtend Selection Mode",
                "edit.toggle_extend_selection_mode",
            ),
        )
        selection_menu.Check(self._id_toggle_extend_selection_mode, self._extend_selection_mode)
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_start_selection,
            self._menu_label("&Start Selection", "edit.start_selection"),
        )
        selection_menu.Append(
            self._id_complete_selection,
            self._menu_label("&Complete Selection", "edit.complete_selection"),
        )
        selection_menu.Append(
            self._id_reselect,
            self._menu_label("&Reselect", "edit.reselect"),
        )
        selection_menu.Append(
            self._id_go_to_start_of_selection,
            self._menu_label("&Go to Start of Selection", "edit.go_to_start_of_selection"),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_select_line,
            self._menu_label("Select &Line", "edit.select_line"),
        )
        selection_menu.Append(
            self._id_select_paragraph,
            self._menu_label("Select &Paragraph", "edit.select_paragraph"),
        )
        selection_menu.Append(
            self._id_select_block,
            self._menu_label("Select &Block", "edit.select_block"),
        )
        selection_menu.Append(
            self._id_expand_selection,
            self._menu_label("E&xpand Selection", "edit.expand_selection"),
        )
        selection_menu.Append(
            self._id_shrink_selection,
            self._menu_label("S&hrink Selection", "edit.shrink_selection"),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_select_to_end_of_line,
            self._menu_label("Select to End of &Line", "edit.select_to_end_of_line"),
        )
        selection_menu.Append(
            self._id_select_to_start_of_line,
            self._menu_label(
                "Select to Start of Li&ne",
                "edit.select_to_start_of_line",
            ),
        )
        selection_menu.Append(
            self._id_select_to_end_of_document,
            self._menu_label(
                "Select to End of &Document",
                "edit.select_to_end_of_document",
            ),
        )
        selection_menu.Append(
            self._id_select_to_start_of_document,
            self._menu_label(
                "Select to Start of D&ocument",
                "edit.select_to_start_of_document",
            ),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_set_mark,
            self._menu_label("&Set Temporary Mark", "edit.set_mark"),
        )
        selection_menu.Append(
            self._id_pop_mark,
            self._menu_label("&Jump to Previous Mark", "edit.pop_mark"),
        )
        selection_menu.Append(
            self._id_exchange_point_mark,
            self._menu_label(
                "&Swap Cursor and Mark",
                "edit.exchange_point_mark",
            ),
        )
        selection_menu.Append(
            self._id_list_marks,
            self._menu_label("&List Recent Marks", "edit.list_marks"),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_set_named_mark,
            self._menu_label("&Set Named Mark...", "edit.set_named_mark"),
        )
        selection_menu.Append(
            self._id_jump_to_named_mark,
            self._menu_label("&Jump to Named Mark...", "edit.jump_to_named_mark"),
        )
        selection_menu.Append(
            self._id_open_review_buffer,
            self._menu_label("&Review Buffer", "edit.open_review_buffer"),
        )
        edit_menu.AppendSubMenu(selection_menu, "&Selection")
        insert_menu = wx.Menu()

        search_menu = wx.Menu()
        # Search is the cross-file search hub; in-document Find/Replace lives in
        # the Edit menu (menus.md Phase 3).
        search_menu.Append(
            self._id_search_in_files,
            self._menu_label("Search in &Files...", "tools.search_in_files"),
        )
        search_menu.Append(
            self._id_replace_in_files,
            self._menu_label("&Replace Across Files...", "tools.replace_in_files"),
        )
        # Regular Expression match count/extract and block set-ops make Search the single
        # find / filter / extract-lines hub (Power Tools recirculation, menus.md
        # Phase 4).
        self._append_power_tools_search_items(search_menu)
        self._append_quillin_menu_items(search_menu, "Search")
        self._id_send_to_tray = wx.NewIdRef()
        self._id_toggle_tray_mode = wx.NewIdRef()
        self._id_toggle_soft_wrap = wx.NewIdRef()
        self._id_toggle_tab_control = wx.NewIdRef()
        self._id_toggle_find_wrap = wx.NewIdRef()
        self._id_toggle_title_full_path = wx.NewIdRef()
        self._id_toggle_auto_check_updates = wx.NewIdRef()
        self._id_toggle_dark_mode = wx.NewIdRef()
        self._id_toggle_persistent_undo = wx.NewIdRef()
        self._id_toggle_spellcheck_as_you_type = wx.NewIdRef()
        self._id_toggle_intellisense_as_you_type = wx.NewIdRef()
        self._id_browser_preview = wx.NewIdRef()
        self._id_preview = wx.NewIdRef()
        self._id_split_preview = wx.NewIdRef()
        self._id_focus_preview = wx.NewIdRef()
        self._id_toggle_auto_side_preview = wx.NewIdRef()
        self._id_start_with_no_document_open = wx.NewIdRef()
        self._id_dirty_title_text = wx.NewIdRef()
        self._id_dirty_title_asterisk = wx.NewIdRef()
        self._id_dirty_title_asterisk_text = wx.NewIdRef()
        view_menu = wx.Menu()
        # View keeps genuine view actions and view-state toggles. Preference
        # toggles (theme/dark mode, system-tray mode, title-bar path, dirty-title
        # style, persistent undo, spell-check-as-you-type, and word-prediction-as-
        # you-type) now live in the registry-driven Settings dialog (menus.md
        # Phase 3), where they are persisted; they are no longer duplicated here.
        view_menu.AppendCheckItem(
            self._id_toggle_soft_wrap,
            self._menu_label("Toggle Soft &Wrap", "view.toggle_soft_wrap"),
        )
        view_menu.Check(self._id_toggle_soft_wrap, self.settings.soft_wrap)
        view_menu.AppendCheckItem(self._id_toggle_tab_control, "Show &Tab Control")
        view_menu.Check(self._id_toggle_tab_control, self.settings.show_tab_control)
        view_menu.AppendSeparator()
        view_menu.Append(
            self._id_preview,
            self._menu_label("&Preview...", "view.preview"),
        )
        view_menu.Append(
            self._id_split_preview,
            self._menu_label("Preview &Side by Side", "view.split_preview"),
        )
        view_menu.Append(
            self._id_focus_preview,
            self._menu_label("&Focus Preview", "view.focus_preview"),
        )
        view_menu.Append(
            self._id_browser_preview,
            self._menu_label("&Browser Preview...", "view.browser_preview"),
        )
        view_menu.AppendCheckItem(self._id_toggle_auto_side_preview, "&Auto Side-by-Side Preview")
        view_menu.Check(self._id_toggle_auto_side_preview, self.settings.auto_side_preview)
        view_menu.AppendSeparator()
        view_menu.AppendCheckItem(
            self._id_toggle_entries_panel,
            self._menu_label("Show &Entries Panel", "view.toggle_entries_panel"),
        )
        navigate_menu = wx.Menu()
        self._id_go_to_line = wx.NewIdRef()
        self._id_set_bookmark = wx.NewIdRef()
        self._id_go_to_bookmark = wx.NewIdRef()
        self._id_list_bookmarks = wx.NewIdRef()
        self._id_go_to_page = wx.NewIdRef()
        self._id_back_location = wx.NewIdRef()
        self._id_forward_location = wx.NewIdRef()
        self._id_next_heading = wx.NewIdRef()
        self._id_previous_heading = wx.NewIdRef()
        self._id_next_block = wx.NewIdRef()
        self._id_previous_block = wx.NewIdRef()
        self._id_outline_navigator = wx.NewIdRef()
        self._id_heading_organizer = wx.NewIdRef()
        self._id_match_bracket = wx.NewIdRef()
        self._id_next_token = wx.NewIdRef()
        self._id_previous_token = wx.NewIdRef()
        self._id_set_language = wx.NewIdRef()
        self._id_speak_window_title = wx.NewIdRef()
        self._id_speak_full_path = wx.NewIdRef()
        self._id_speak_status_summary = wx.NewIdRef()
        self._id_compare_start_with_file = wx.NewIdRef()
        self._id_compare_next = wx.NewIdRef()
        self._id_compare_previous = wx.NewIdRef()
        self._id_compare_current = wx.NewIdRef()
        self._id_compare_toggle_whitespace = wx.NewIdRef()
        self._id_compare_generate_report = wx.NewIdRef()
        self._id_next_structure = wx.NewIdRef()
        self._id_previous_structure = wx.NewIdRef()
        self._id_next_region = wx.NewIdRef()
        self._id_previous_region = wx.NewIdRef()
        navigate_menu.Append(
            self._id_back_location,
            self._menu_label("&Back Location", "navigate.back_location"),
        )
        navigate_menu.Append(
            self._id_forward_location,
            self._menu_label("&Forward Location", "navigate.forward_location"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_go_to_line,
            self._menu_label("&Go To Line...", "navigate.go_to_line"),
        )
        navigate_menu.Append(
            self._id_go_to_page,
            self._menu_label("Go To &Page...", "navigate.go_to_page"),
        )
        # Go to Percent, First/Last Non-Blank, Open Target at Cursor (power tools navigate group)
        self._append_power_tools_navigate_items(navigate_menu)
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_next_heading,
            self._menu_label("Next &Heading", "navigate.next_heading"),
        )
        navigate_menu.Append(
            self._id_previous_heading,
            self._menu_label("Pre&vious Heading", "navigate.previous_heading"),
        )
        navigate_menu.Append(
            self._id_next_block,
            self._menu_label("Next &Block", "navigate.next_block"),
        )
        navigate_menu.Append(
            self._id_previous_block,
            self._menu_label("Previous Bl&ock", "navigate.previous_block"),
        )
        navigate_menu.Append(
            self._id_next_structure,
            self._menu_label("Next Str&ucture", "navigate.next_structure"),
        )
        navigate_menu.Append(
            self._id_previous_structure,
            self._menu_label("Previous Structu&re", "navigate.previous_structure"),
        )
        navigate_menu.Append(
            self._id_next_region,
            self._menu_label("Next Re&gion", "navigate.next_region"),
        )
        navigate_menu.Append(
            self._id_previous_region,
            self._menu_label("Previous Regio&n", "navigate.previous_region"),
        )
        navigate_menu.Append(
            self._id_match_bracket,
            self._menu_label("Match &Bracket", "navigate.match_bracket"),
        )
        navigate_menu.Append(
            self._id_next_token,
            self._menu_label("Next &Token", "navigate.next_token"),
        )
        navigate_menu.Append(
            self._id_previous_token,
            self._menu_label("P&revious Token", "navigate.previous_token"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_set_language,
            self._menu_label("Set Document &Language...", "navigate.set_language"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_speak_window_title,
            self._menu_label("Speak &Window Title", "navigate.speak_window_title"),
        )
        navigate_menu.Append(
            self._id_speak_full_path,
            self._menu_label("Speak &Full Path", "navigate.speak_full_path"),
        )
        navigate_menu.Append(
            self._id_speak_status_summary,
            self._menu_label("Speak &Status Summary", "navigate.speak_status_summary"),
        )
        navigate_menu.AppendSeparator()
        compare_menu = wx.Menu()
        compare_menu.Append(
            self._id_compare_start_with_file,
            self._menu_label("&Compare with File...", "compare.start_with_file"),
        )
        compare_menu.AppendSeparator()
        compare_menu.Append(
            self._id_compare_next,
            self._menu_label("&Next Difference\tF8", "compare.next_difference"),
        )
        compare_menu.Append(
            self._id_compare_previous,
            self._menu_label("&Previous Difference\tShift+F8", "compare.previous_difference"),
        )
        compare_menu.Append(
            self._id_compare_current,
            self._menu_label(
                "Read &Current Difference\tCtrl+F8",
                "compare.current_difference_summary",
            ),
        )
        compare_menu.AppendSeparator()
        compare_menu.Append(
            self._id_compare_toggle_whitespace,
            self._menu_label("Toggle &Ignore Whitespace", "compare.toggle_ignore_whitespace"),
        )
        compare_menu.Append(
            self._id_compare_generate_report,
            self._menu_label("&Generate Accessible Report", "compare.generate_accessible_report"),
        )
        navigate_menu.AppendSubMenu(compare_menu, "&Compare")
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_outline_navigator,
            self._menu_label("Outline &Navigator...", "navigate.outline_navigator"),
        )
        navigate_menu.Append(
            self._id_heading_organizer,
            self._menu_label("&Heading Organizer...", "navigate.heading_organizer"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_follow_link,
            self._menu_label("&Follow Link", "edit.follow_link"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_set_bookmark,
            self._menu_label("Set &Bookmark...", "navigate.set_bookmark"),
        )
        navigate_menu.Append(
            self._id_go_to_bookmark,
            self._menu_label("Go To &Bookmark...", "navigate.go_to_bookmark"),
        )
        navigate_menu.Append(
            self._id_list_bookmarks,
            self._menu_label("List B&ookmarks...", "navigate.list_bookmarks"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_go_to_entry_in_notebook,
            self._menu_label("Go to &Entry in Notebook...", "navigate.go_to_entry_in_notebook"),
        )
        navigate_menu.Append(
            self._id_go_to_heading_in_notebook,
            self._menu_label("Go to &Heading in Notebook...", "navigate.go_to_heading_in_notebook"),
        )
        navigate_menu.Append(
            self._id_go_to_bookmark_in_notebook,
            self._menu_label(
                "Go to &Bookmark in Notebook...", "navigate.go_to_bookmark_in_notebook"
            ),
        )
        navigate_menu.Append(
            self._id_go_to_sticky_note_in_notebook,
            self._menu_label(
                "Go to Sticky &Note in Notebook...", "navigate.go_to_sticky_note_in_notebook"
            ),
        )
        self._id_insert_html_tag = wx.NewIdRef()
        self._id_insert_markdown_tag = wx.NewIdRef()
        self._id_insert_snippet = wx.NewIdRef()
        self._id_manage_snippets = wx.NewIdRef()
        self._id_expand_abbreviation = wx.NewIdRef()
        self._id_manage_abbreviations = wx.NewIdRef()
        self._id_toggle_abbreviation_expansion = wx.NewIdRef()
        self._id_format_bold = wx.NewIdRef()
        self._id_format_italic = wx.NewIdRef()
        self._id_heading_1 = wx.NewIdRef()
        self._id_heading_2 = wx.NewIdRef()
        self._id_heading_3 = wx.NewIdRef()
        self._id_heading_4 = wx.NewIdRef()
        self._id_heading_5 = wx.NewIdRef()
        self._id_heading_6 = wx.NewIdRef()
        self._id_decrease_heading_level = wx.NewIdRef()
        self._id_increase_heading_level = wx.NewIdRef()
        self._id_style_headings = wx.NewIdRef()
        self._id_upper_case = wx.NewIdRef()
        self._id_lower_case = wx.NewIdRef()
        self._id_title_case = wx.NewIdRef()
        self._id_sentence_case = wx.NewIdRef()
        self._id_toggle_case = wx.NewIdRef()
        self._id_toggle_line_comment = wx.NewIdRef()
        self._id_toggle_block_comment = wx.NewIdRef()
        self._id_indent = wx.NewIdRef()
        self._id_outdent = wx.NewIdRef()
        self._id_move_line_up = wx.NewIdRef()
        self._id_move_line_down = wx.NewIdRef()
        self._id_duplicate_line = wx.NewIdRef()
        self._id_delete_line = wx.NewIdRef()
        self._id_join_lines = wx.NewIdRef()
        self._id_quote_lines = wx.NewIdRef()
        self._id_unquote_lines = wx.NewIdRef()
        self._id_insert_bullet_list = wx.NewIdRef()
        self._id_insert_numbered_list = wx.NewIdRef()
        self._id_insert_task_list = wx.NewIdRef()
        self._id_open_list_manager = wx.NewIdRef()
        self._id_insert_code_block = wx.NewIdRef()
        self._id_insert_footnote = wx.NewIdRef()
        self._id_insert_table = wx.NewIdRef()
        format_menu = wx.Menu()

        # --- Character formatting (most common) ---
        format_menu.Append(self._id_format_bold, self._menu_label("&Bold", "format.bold"))
        format_menu.Append(self._id_format_italic, self._menu_label("&Italic", "format.italic"))
        format_menu.AppendSeparator()

        # --- Structural formatting ---
        format_menu.Append(
            self._id_indent,
            self._menu_label("&Indent", "format.indent"),
        )
        format_menu.Append(
            self._id_outdent,
            self._menu_label("O&utdent", "format.outdent"),
        )
        format_menu.AppendSeparator()

        # --- Case ---
        case_menu = wx.Menu()
        case_menu.Append(
            self._id_upper_case,
            self._menu_label("&Upper Case", "format.upper_case"),
        )
        case_menu.Append(
            self._id_lower_case,
            self._menu_label("&Lower Case", "format.lower_case"),
        )
        case_menu.Append(
            self._id_title_case,
            self._menu_label("&Title Case", "format.title_case"),
        )
        case_menu.Append(
            self._id_sentence_case,
            self._menu_label("&Sentence Case", "format.sentence_case"),
        )
        case_menu.Append(
            self._id_toggle_case,
            self._menu_label("To&ggle Case", "format.toggle_case"),
        )
        format_menu.AppendSubMenu(case_menu, "Change &Case")

        # --- Comments ---
        format_menu.Append(
            self._id_toggle_line_comment,
            self._menu_label(
                "Toggle Line &Comment",
                "format.toggle_line_comment",
            ),
        )
        format_menu.Append(
            self._id_toggle_block_comment,
            self._menu_label(
                "Toggle &Block Comment",
                "format.toggle_block_comment",
            ),
        )
        format_menu.AppendSeparator()

        # --- Line submenu ---
        line_menu = wx.Menu()
        line_menu.Append(
            self._id_move_line_up,
            self._menu_label("Move Line &Up", "format.move_line_up"),
        )
        line_menu.Append(
            self._id_move_line_down,
            self._menu_label("Move Line &Down", "format.move_line_down"),
        )
        line_menu.AppendSeparator()
        line_menu.Append(
            self._id_duplicate_line,
            self._menu_label("D&uplicate Line", "format.duplicate_line"),
        )
        line_menu.Append(
            self._id_delete_line,
            self._menu_label("De&lete Line", "format.delete_line"),
        )
        line_menu.AppendSeparator()
        line_menu.Append(
            self._id_join_lines,
            self._menu_label("&Join Lines", "format.join_lines"),
        )
        # Number Lines, Hard-Wrap Lines and delete operations (power tools format_line group)
        self._append_power_tools_format_line_items(line_menu)
        line_menu.AppendSeparator()
        line_menu.Append(self._id_quote_lines, self._menu_label("&Quote Lines", "edit.quote_lines"))
        line_menu.Append(
            self._id_unquote_lines, self._menu_label("&Unquote Lines", "edit.unquote_lines")
        )
        format_menu.AppendSubMenu(line_menu, "&Line")

        # --- Sort & Filter submenu ---
        sort_menu = wx.Menu()
        sort_menu.Append(
            self._id_sort_lines_ascending,
            self._menu_label("Sort Lines &A to Z", "edit.sort_lines_ascending"),
        )
        sort_menu.Append(
            self._id_sort_lines_descending,
            self._menu_label("Sort Lines &Z to A", "edit.sort_lines_descending"),
        )
        # Numeric, by length, shuffle, keep unique, delete-containing (power tools)
        self._append_power_tools_sort_filter_items(sort_menu)
        sort_menu.AppendSeparator()
        sort_menu.Append(
            self._id_reverse_lines,
            self._menu_label("&Reverse Lines", "edit.reverse_lines"),
        )
        sort_menu.AppendSeparator()
        sort_menu.Append(
            self._id_remove_duplicate_lines,
            self._menu_label("Remove &Duplicate Lines", "edit.remove_duplicate_lines"),
        )
        format_menu.AppendSubMenu(sort_menu, "Sort && &Filter")

        # --- Whitespace submenu ---
        ws_menu = wx.Menu()
        ws_menu.Append(
            self._id_trim_trailing_whitespace,
            self._menu_label("Trim Trailing &Whitespace", "edit.trim_trailing_whitespace"),
        )
        # Trim Blank Lines (power tools trim_blank group)
        self._append_power_tools_trim_blank_items(ws_menu)
        ws_menu.Append(
            self._id_normalize_whitespace,
            self._menu_label("&Normalize Whitespace", "edit.normalize_whitespace"),
        )
        ws_menu.AppendSeparator()
        ws_menu.Append(
            self._id_convert_indentation_to_spaces,
            self._menu_label(
                "Convert Indentation to &Spaces",
                "edit.convert_indentation_to_spaces",
            ),
        )
        ws_menu.Append(
            self._id_convert_indentation_to_tabs,
            self._menu_label(
                "Convert Indentation to &Tabs",
                "edit.convert_indentation_to_tabs",
            ),
        )
        format_menu.AppendSubMenu(ws_menu, "&Whitespace")

        # --- HTML & Encoding submenu ---
        html_menu = wx.Menu()
        self._append_power_tools_html_encoding_items(html_menu)
        format_menu.AppendSubMenu(html_menu, "&HTML && Encoding")

        # Quillin-contributed Format items
        self._append_quillin_menu_items(format_menu, "Format")

        heading_menu = wx.Menu()
        heading_menu.Append(self._id_heading_1, self._menu_label("Heading &1", "format.heading_1"))
        heading_menu.Append(self._id_heading_2, self._menu_label("Heading &2", "format.heading_2"))
        heading_menu.Append(self._id_heading_3, self._menu_label("Heading &3", "format.heading_3"))
        heading_menu.Append(self._id_heading_4, self._menu_label("Heading &4", "format.heading_4"))
        heading_menu.Append(self._id_heading_5, self._menu_label("Heading &5", "format.heading_5"))
        heading_menu.Append(self._id_heading_6, self._menu_label("Heading &6", "format.heading_6"))
        heading_menu.AppendSeparator()
        heading_menu.Append(
            self._id_decrease_heading_level,
            self._menu_label(
                "Decrease Level",
                "format.decrease_heading_level",
            ),
        )
        heading_menu.Append(
            self._id_increase_heading_level,
            self._menu_label(
                "Increase Level",
                "format.increase_heading_level",
            ),
        )
        heading_menu.AppendSeparator()
        heading_menu.Append(
            self._id_style_headings,
            self._menu_label("&Style Headings...", "format.style_headings"),
        )
        insert_menu.Append(
            self._id_insert_link,
            self._menu_label("Insert &Link...", "edit.insert_link"),
        )
        insert_menu.AppendSeparator()
        insert_menu.AppendSubMenu(heading_menu, "&Heading")
        list_menu = wx.Menu()
        list_menu.Append(
            self._id_insert_bullet_list,
            self._menu_label("B&ullet", "format.insert_bullet_list"),
        )
        list_menu.Append(
            self._id_insert_numbered_list,
            self._menu_label("&Numbered", "format.insert_numbered_list"),
        )
        list_menu.Append(
            self._id_insert_task_list,
            self._menu_label("&Task", "format.insert_task_list"),
        )
        list_menu.AppendSeparator()
        list_menu.Append(
            self._id_open_list_manager,
            self._menu_label("List &Manager...", "format.list_manager"),
        )
        insert_menu.AppendSubMenu(list_menu, "&List")
        insert_menu.Append(
            self._id_insert_code_block,
            self._menu_label("Insert Code &Block", "format.insert_code_block"),
        )
        insert_menu.Append(
            self._id_insert_footnote,
            self._menu_label("Insert &Footnote", "format.insert_footnote"),
        )
        insert_menu.Append(
            self._id_insert_table,
            self._menu_label("Insert &Table...", "format.insert_table"),
        )
        insert_menu.AppendSeparator()
        insert_menu.Append(
            self._id_insert_html_tag,
            self._menu_label("Insert &HTML Tag...", "format.insert_html_tag"),
        )
        insert_menu.Append(
            self._id_insert_markdown_tag,
            self._menu_label("Insert &Markdown Tag...", "format.insert_markdown_tag"),
        )
        insert_menu.Append(
            self._id_insert_snippet,
            self._menu_label("Insert S&nippet...", "format.insert_snippet"),
        )
        insert_menu.Append(
            self._id_manage_snippets,
            self._menu_label("Manage Snippets...", "format.manage_snippets"),
        )
        insert_menu.AppendSeparator()
        insert_menu.Append(
            self._id_expand_abbreviation,
            self._menu_label("E&xpand Abbreviation", "format.expand_abbreviation"),
        )
        insert_menu.Append(
            self._id_manage_abbreviations,
            self._menu_label("Manage Abbrevi&ations...", "format.manage_abbreviations"),
        )
        insert_menu.Append(
            self._id_toggle_abbreviation_expansion,
            self._menu_label(
                "&Toggle Abbreviation Expansion", "format.toggle_abbreviation_expansion"
            ),
        )
        # Special character / date-time / calculated date / file content (Power Tools
        # recirculation, menus.md Phase 4).
        self._append_power_tools_insert_items(insert_menu)
        self._append_quillin_menu_items(insert_menu, "Insert")
        self._id_next_document = wx.NewIdRef()
        self._id_previous_document = wx.NewIdRef()
        window_menu = wx.Menu()
        window_menu.Append(
            self._id_next_document,
            self._menu_label("&Next Document", "window.next_document"),
        )
        window_menu.Append(
            self._id_previous_document,
            self._menu_label("&Previous Document", "window.previous_document"),
        )
        window_menu.AppendSeparator()
        window_menu.Append(
            self._id_send_to_tray,
            self._menu_label("Send to S&ystem Tray", "view.send_to_tray"),
        )

        self._id_word_count = wx.NewIdRef()
        self._id_sticky_notes = wx.NewIdRef()
        self._id_new_sticky_note = wx.NewIdRef()
        self._id_spell_check = wx.NewIdRef()
        self._id_previous_misspelling = wx.NewIdRef()
        self._id_next_misspelling = wx.NewIdRef()
        self._id_misspelling_list = wx.NewIdRef()
        self._id_dictionary_status = wx.NewIdRef()
        self._id_ocr_image = wx.NewIdRef()
        self._id_ocr_clipboard = wx.NewIdRef()
        self._id_ocr_screen = wx.NewIdRef()
        self._id_describe_image = wx.NewIdRef()
        self._id_regex_helper = wx.NewIdRef()
        self._id_pandoc_wizard = wx.NewIdRef()
        self._id_external_tools = wx.NewIdRef()
        self._id_read_aloud = wx.NewIdRef()
        self._id_read_aloud_stop = wx.NewIdRef()
        self._id_read_aloud_voice = wx.NewIdRef()
        self._id_read_aloud_settings = wx.NewIdRef()
        self._id_read_aloud_generate_audio = wx.NewIdRef()
        self._id_announcement_backend = wx.NewIdRef()
        self._id_announcement_backend_auto = wx.NewIdRef()
        self._id_announcement_backend_prism = wx.NewIdRef()
        self._id_announcement_backend_status_only = wx.NewIdRef()
        self._id_toggle_announcement_trace = wx.NewIdRef()
        self._id_toggle_sound = wx.NewIdRef()
        self._id_sound_events = wx.NewIdRef()
        self._id_dictation = wx.NewIdRef()
        self._id_dictation_voice_commands = wx.NewIdRef()
        self._id_bw_model_manager = wx.NewIdRef()
        self._id_bw_model_status = wx.NewIdRef()
        self._id_bw_model_recommend = wx.NewIdRef()
        self._id_bw_toggle_parakeet = wx.NewIdRef()
        self._id_bw_check_faster_whisper = wx.NewIdRef()
        self._id_bw_provider_center = wx.NewIdRef()
        self._id_bw_provider_status = wx.NewIdRef()
        self._id_bw_provider_recommend = wx.NewIdRef()
        self._id_bw_provider_select = wx.NewIdRef()
        self._id_bw_readiness_check = wx.NewIdRef()
        self._id_bw_capability_matrix = wx.NewIdRef()
        self._id_bw_download_queue = wx.NewIdRef()
        self._id_watch_folder_toggle = wx.NewIdRef()
        self._id_watch_folder_settings = wx.NewIdRef()
        self._id_watch_folder_status = wx.NewIdRef()
        self._id_document_intake_report = wx.NewIdRef()
        self._id_review_extraction_quality = wx.NewIdRef()
        self._id_report_bad_extraction = wx.NewIdRef()
        self._id_shell_install = wx.NewIdRef()
        self._id_shell_remove = wx.NewIdRef()
        self._id_notifications = wx.NewIdRef()
        self._id_check_updates = wx.NewIdRef()
        self._id_check_glow_updates = wx.NewIdRef()
        self._id_validate_contrast = wx.NewIdRef()
        self._id_status_bar_settings = wx.NewIdRef()
        self._id_share_export = wx.NewIdRef()
        self._id_share_import = wx.NewIdRef()
        self._id_keymap_editor = wx.NewIdRef()
        self._id_export_keymap = wx.NewIdRef()
        self._id_import_keymap = wx.NewIdRef()
        self._id_reset_keymap = wx.NewIdRef()
        self._id_profiles_and_features = wx.NewIdRef()
        self._id_glow_audit_document = wx.NewIdRef()
        self._id_glow_audit_selection = wx.NewIdRef()
        self._id_glow_fix_document = wx.NewIdRef()
        self._id_glow_fix_selection = wx.NewIdRef()
        self._id_link_inventory = wx.NewIdRef()
        self._id_ai_hub = wx.NewIdRef()
        self._id_ai_assistant = wx.NewIdRef()
        self._id_ai_prompt_studio = wx.NewIdRef()
        self._id_ai_agent_center = wx.NewIdRef()
        self._id_ai_accessibility_agent = wx.NewIdRef()
        self._id_ask_quill_chat = wx.NewIdRef()
        self._id_prompt_library = wx.NewIdRef()
        self._id_skill_library = wx.NewIdRef()
        self._id_check_grammar_ai = wx.NewIdRef()
        self._id_ai_enabled = wx.NewIdRef()
        self._id_ai_status_badge = wx.NewIdRef()
        self._id_ai_status_detail = wx.NewIdRef()
        self._id_ai_model = wx.NewIdRef()
        self._id_ai_session_browser = wx.NewIdRef()
        self._id_ai_connection = wx.NewIdRef()
        self._id_ai_forget_key = wx.NewIdRef()
        self._id_ai_rewrite_selection = wx.NewIdRef()
        self._id_ai_summarize_selection = wx.NewIdRef()
        self._id_ai_continue_writing = wx.NewIdRef()
        self._id_ai_fix_grammar = wx.NewIdRef()
        self._id_ai_speech_start_pause = wx.NewIdRef()
        self._id_ai_speech_stop = wx.NewIdRef()
        self._id_ai_speech_voice = wx.NewIdRef()
        self._id_ai_speech_settings = wx.NewIdRef()
        self._id_ai_speech_generate_audio = wx.NewIdRef()
        self._id_train_style = wx.NewIdRef()
        self._id_writing_instructions = wx.NewIdRef()
        self._id_compare_with_file = wx.NewIdRef()
        self._id_compare_open_documents = wx.NewIdRef()
        self._id_compare_next_difference = wx.NewIdRef()
        self._id_compare_previous_difference = wx.NewIdRef()
        self._id_compare_announce_difference = wx.NewIdRef()
        self._id_compare_difference_list = wx.NewIdRef()
        self._id_compare_toggle_sync = wx.NewIdRef()
        self._id_compare_options = wx.NewIdRef()
        self._id_compare_create_summary = wx.NewIdRef()
        self._id_compare_copy_current = wx.NewIdRef()
        self._id_compare_copy_all = wx.NewIdRef()
        self._id_start_macro_recording = wx.NewIdRef()
        self._id_stop_macro_recording = wx.NewIdRef()
        self._id_play_last_macro = wx.NewIdRef()
        self._id_manage_macros = wx.NewIdRef()
        self._id_open_welcome_guide = wx.NewIdRef()
        self._id_open_keyboard_reference = wx.NewIdRef()
        self._id_about_quill = wx.NewIdRef()
        self._id_save_diagnostics = wx.NewIdRef()
        self._id_report_bug = wx.NewIdRef()
        self._id_open_logs_folder = wx.NewIdRef()
        self._id_open_diagnostics_folder = wx.NewIdRef()
        self._id_help_on_control = wx.NewIdRef()
        self._id_context_help = wx.NewIdRef()
        self._id_announce_context_shortcuts = wx.NewIdRef()
        self._id_help_status_page = wx.NewIdRef()
        self._id_why_dont_i_see_feature = wx.NewIdRef()
        self._id_switch_feature_profile = wx.NewIdRef()
        self._id_feature_profile_health_check = wx.NewIdRef()
        self._id_individual_feature_toggles = wx.NewIdRef()
        self._id_undo_profile_change = wx.NewIdRef()
        self._id_reset_feature_profile = wx.NewIdRef()
        self._id_profile_onboarding = wx.NewIdRef()
        self._id_keyboard_trap_snapshot = wx.NewIdRef()
        self._id_accessibility_audit = wx.NewIdRef()
        self._id_yaml_structure_editor = wx.NewIdRef()
        self._id_whisperer_about = wx.NewIdRef()
        self._id_dev_console_python = wx.NewIdRef()
        self._id_dev_console_ts = wx.NewIdRef()
        self._id_dev_copy_diagnostic = wx.NewIdRef()
        self._id_dev_restart_ts_worker = wx.NewIdRef()
        tools_menu = wx.Menu()
        tools_menu.Append(
            self._id_palette,
            self._menu_label("&Command Palette...", "app.command_palette"),
        )
        tools_menu.AppendSeparator()

        # Writing & Language -----------------------------------------------
        writing_menu = wx.Menu()
        writing_menu.Append(
            self._id_word_count,
            self._menu_label("&Word Count...", "tools.word_count"),
        )
        writing_menu.Append(
            self._id_spell_check,
            self._menu_label("&Spell Check...", "tools.spell_check_dialog"),
        )
        writing_menu.Append(
            self._id_previous_misspelling,
            self._menu_label("Previous Mi&sspelling", "tools.previous_misspelling"),
        )
        writing_menu.Append(
            self._id_next_misspelling,
            self._menu_label("Next &Misspelling", "tools.next_misspelling"),
        )
        writing_menu.Append(
            self._id_misspelling_list,
            self._menu_label("&Misspelling List...", "tools.misspelling_list"),
        )
        self._id_thesaurus = wx.NewIdRef()
        writing_menu.Append(
            self._id_thesaurus,
            self._menu_label("&Thesaurus...", "tools.thesaurus"),
        )
        writing_menu.Append(
            self._id_dictionary_status,
            self._menu_label("Dictionary &Status...", "tools.dictionary_status"),
        )
        # GLOW is hidden for now (core.glow is locked off pending completion).
        # When re-enabled, these audit/fix items reappear automatically.
        if self._feature_enabled("core.glow"):
            writing_menu.AppendSeparator()
            writing_menu.Append(
                self._id_glow_audit_document,
                self._menu_label("GLOW &Audit Document", "tools.glow_audit_document"),
            )
            writing_menu.Append(
                self._id_glow_audit_selection,
                self._menu_label("GLOW Audit &Selection", "tools.glow_audit_selection"),
            )
            writing_menu.AppendSeparator()
            writing_menu.Append(
                self._id_glow_fix_document,
                self._menu_label("GLOW &Fix Document", "tools.glow_fix_document"),
            )
            writing_menu.Append(
                self._id_glow_fix_selection,
                self._menu_label("GLOW Fix &Selection", "tools.glow_fix_selection"),
            )
        tools_menu.AppendSubMenu(writing_menu, "&Writing && Language")

        # Reading & Dictation (merges Read Aloud, Dictation, OCR) ------------
        read_aloud_menu = wx.Menu()
        read_aloud_menu.Append(
            self._id_read_aloud,
            self._menu_label("&Start / Pause", "tools.read_aloud_start_pause"),
        )
        read_aloud_menu.Append(
            self._id_read_aloud_voice,
            self._menu_label("&Voice...", "tools.read_aloud_voice"),
        )
        read_aloud_menu.Append(
            self._id_read_aloud_settings,
            self._menu_label("Se&ttings...", "tools.read_aloud_settings"),
        )
        read_aloud_menu.Append(
            self._id_read_aloud_generate_audio,
            self._menu_label("Generate &Audio...", "tools.read_aloud_generate_audio"),
        )
        read_aloud_menu.Append(
            self._id_announcement_backend,
            self._menu_label("Announcement &Backend...", "tools.announcement_backend"),
        )
        read_aloud_menu.Append(
            self._id_toggle_announcement_trace,
            "Announcement &Trace (in Settings)...",
        )
        reading_menu = wx.Menu()
        reading_menu.AppendSubMenu(read_aloud_menu, "Read &Aloud")
        reading_menu.Append(
            self._id_read_aloud_stop,
            self._menu_label("&Stop Reading", "tools.read_aloud_stop"),
        )
        reading_menu.Append(
            self._id_say_selected,
            self._menu_label("&Say Selected", "edit.say_selected"),
        )
        reading_menu.Append(
            self._id_read_all,
            self._menu_label("&Read All", "edit.read_all"),
        )
        reading_menu.AppendSeparator()
        dictation_submenu = wx.Menu()
        dictation_submenu.Append(
            self._id_dictation,
            self._menu_label("&Dictation", "tools.dictation_toggle"),
            "Press to start dictation, press again to stop and insert",
        )
        dictation_submenu.Append(
            self._id_dictation_voice_commands,
            "Hey QUILL &Commands (in Settings)...",
        )
        reading_menu.AppendSubMenu(dictation_submenu, "&Dictation")
        reading_menu.AppendSeparator()
        reading_menu.Append(
            self._id_toggle_sound,
            self._menu_label("Toggle &Sound Notifications", "tools.sound_toggle"),
        )
        reading_menu.Append(
            self._id_sound_events,
            self._menu_label("&Manage Sound Events...", "tools.sound_events"),
        )
        reading_menu.AppendSeparator()
        reading_menu.Append(
            self._id_ocr_image,
            self._menu_label("OCR &Image...", "tools.ocr_image"),
        )
        reading_menu.Append(
            self._id_ocr_clipboard,
            self._menu_label("OCR &Clipboard Image", "tools.ocr_clipboard"),
        )
        reading_menu.Append(
            self._id_ocr_screen,
            self._menu_label("OCR &Screen Capture...", "tools.ocr_screen"),
        )
        reading_menu.Append(
            self._id_describe_image,
            self._menu_label("&Describe Image...", "tools.describe_image"),
        )
        tools_menu.AppendSubMenu(reading_menu, "R&eading && Dictation")

        # Comparison (was Compare Documents) ----------------------------------
        compare_menu = wx.Menu()
        compare_menu.Append(self._id_compare_with_file, "Compare with &File...")
        compare_menu.Append(self._id_compare_open_documents, "Compare &Open Documents...")
        compare_menu.AppendSeparator()
        compare_menu.Append(self._id_compare_next_difference, "&Next Difference")
        compare_menu.Append(self._id_compare_previous_difference, "&Previous Difference")
        compare_menu.Append(self._id_compare_announce_difference, "&Announce Current Difference")
        compare_menu.Append(self._id_compare_difference_list, "Difference &List...")
        compare_menu.Append(self._id_compare_toggle_sync, "Toggle &Synchronized Navigation")
        compare_menu.Append(self._id_compare_options, "Compare O&ptions...")
        compare_menu.AppendSeparator()
        compare_menu.Append(self._id_compare_create_summary, "Create Difference &Summary")
        compare_menu.Append(self._id_compare_copy_current, "Copy &Current Difference")
        compare_menu.Append(self._id_compare_copy_all, "Copy A&ll Differences")
        tools_menu.AppendSubMenu(compare_menu, "C&omparison")

        # Watch Folder (extracted from former Dictation submenu) --------------
        watch_folder_menu = wx.Menu()
        watch_folder_menu.Append(
            self._id_watch_folder_toggle,
            "Watch Folder &Monitoring (in Settings)...",
        )
        watch_folder_menu.Append(
            self._id_watch_folder_settings,
            self._menu_label("Watch Folder &Profiles...", "tools.watch_folder_settings"),
        )
        watch_folder_menu.Append(
            self._id_watch_folder_status,
            self._menu_label("Watch Folder &Queue...", "tools.watch_folder_status"),
        )
        tools_menu.AppendSubMenu(watch_folder_menu, "&Watch Folder")

        # AI Assistant (Speech submenu removed; read aloud is in Reading & Dictation)
        ai_menu = wx.Menu()
        from quill.core.ai.model_manager import load_ai_enabled

        ai_menu.AppendCheckItem(self._id_ai_enabled, "Use Artificial &Intelligence")
        ai_menu.Check(self._id_ai_enabled, load_ai_enabled())
        ai_menu.AppendSeparator()
        ai_menu.Append(
            self._id_ask_quill_chat,
            self._menu_label("&Ask Quill...", "tools.ask_quill_chat"),
        )
        ai_menu.Append(
            self._id_prompt_library,
            self._menu_label("&Prompt Library...", "tools.prompt_library"),
        )
        ai_menu.Append(
            self._id_skill_library,
            self._menu_label("S&kill Library...", "tools.skill_library"),
        )
        ai_menu.AppendSeparator()
        ai_menu.Append(
            self._id_ai_hub,
            self._menu_label("AI &Hub...", "tools.ai_hub"),
        )
        # AI Model and Connection were merged into the AI Hub (one place to
        # configure every provider, its key, model, and run Test Chat).
        ai_menu.Append(
            self._id_ai_session_browser,
            self._menu_label("Session &Branches...", "tools.ai_session_browser"),
        )
        ai_menu.AppendSeparator()
        ai_menu.Append(
            self._id_ai_assistant,
            self._menu_label("&Writing Assistant...", "tools.ai_assistant"),
        )
        ai_menu.Append(
            self._id_ai_prompt_studio,
            self._menu_label("Prompt &Studio...", "tools.ai_prompt_studio"),
        )
        ai_menu.Append(
            self._id_ai_agent_center,
            self._menu_label("Agent &Center...", "tools.ai_agent_center"),
        )
        ai_menu.Append(
            self._id_ai_accessibility_agent,
            self._menu_label("Accessibility &Tune-Up...", "tools.ai_accessibility_agent"),
        )
        ai_menu.AppendSeparator()
        ai_menu.Append(
            self._id_ai_rewrite_selection,
            self._menu_label("&Rewrite Selection", "tools.ai_rewrite_selection"),
        )
        ai_menu.Append(
            self._id_ai_summarize_selection,
            self._menu_label("&Summarize Selection", "tools.ai_summarize_selection"),
        )
        ai_menu.Append(
            self._id_ai_continue_writing,
            self._menu_label("&Continue Writing", "tools.ai_continue_writing"),
        )
        ai_menu.Append(
            self._id_ai_fix_grammar,
            self._menu_label("Fix &Grammar", "tools.ai_fix_grammar"),
        )
        ai_menu.Append(
            self._id_check_grammar_ai,
            self._menu_label("Check Grammar with &AI...", "tools.check_grammar_ai"),
        )
        ai_menu.Append(
            self._id_train_style,
            self._menu_label("&Train Writing Style...", "tools.train_writing_style"),
        )
        ai_menu.Append(
            self._id_writing_instructions,
            self._menu_label("&Writing Instructions...", "tools.writing_instructions"),
        )
        # "Forget API Key" moved into the AI Hub as a per-provider action
        # ("Forget this provider's key"), since a single global forget is
        # ambiguous once each provider keeps its own key.
        tools_menu.AppendSubMenu(ai_menu, "AI &Assistant")

        # BITS Whisperer (conditional, deferred to QUILL 2.0) ----------------
        # "About Whisperer" was folded into the single About Quill dialog.
        whisperer_menu = wx.Menu()
        whisperer_menu.Append(
            self._id_profile_onboarding,
            self._menu_label("&Startup Wizard...", "help.startup_wizard"),
        )
        bw_dictation_menu = wx.Menu()
        bw_dictation_menu.Append(
            self._id_dictation,
            self._menu_label("&Dictation", "tools.dictation_toggle"),
            "Press to start dictation, press again to stop and insert",
        )
        bw_dictation_menu.Append(
            self._id_dictation_voice_commands,
            "Hey QUILL &Commands (in Settings)...",
        )
        bw_dictation_menu.AppendSeparator()
        bw_dictation_menu.Append(
            self._id_watch_folder_toggle,
            "Watch Folder &Monitoring (in Settings)...",
        )
        bw_dictation_menu.Append(
            self._id_watch_folder_settings,
            self._menu_label("Watch Folder &Profiles...", "tools.watch_folder_settings"),
        )
        bw_dictation_menu.Append(
            self._id_watch_folder_status,
            self._menu_label("Watch Folder &Queue...", "tools.watch_folder_status"),
        )
        whisperer_menu.AppendSubMenu(bw_dictation_menu, "&Dictation and Watch Folder")
        bw_models_menu = wx.Menu()
        self._append_bw_safe_mode_badge(bw_models_menu)
        bw_models_menu.Append(
            self._id_bw_model_manager,
            self._menu_label("&Model Manager...", "whisperer.model_manager"),
        )
        bw_models_menu.Append(
            self._id_bw_model_status,
            self._menu_label("Model &Status", "whisperer.model_status"),
        )
        bw_models_menu.Append(
            self._id_bw_model_recommend,
            self._menu_label("Use &Recommended Model", "whisperer.model_recommend"),
        )
        bw_models_menu.AppendCheckItem(
            self._id_bw_toggle_parakeet,
            self._menu_label("Show &Parakeet Models", "whisperer.toggle_parakeet"),
        )
        bw_models_menu.Check(
            self._id_bw_toggle_parakeet,
            bool(getattr(self.settings, "bw_enable_parakeet_models", False)),
        )
        bw_models_menu.AppendSeparator()
        bw_models_menu.Append(
            self._id_bw_check_faster_whisper,
            self._menu_label("Check &faster-whisper Engine", "whisperer.check_faster_whisper"),
        )
        bw_models_menu.Append(
            self._id_bw_download_queue,
            self._menu_label("Download &Queue...", "whisperer.download_queue"),
        )
        whisperer_menu.AppendSubMenu(bw_models_menu, "Speech &Models")
        bw_providers_menu = wx.Menu()
        self._append_bw_safe_mode_badge(bw_providers_menu)
        bw_providers_menu.Append(
            self._id_bw_provider_center,
            self._menu_label("&Provider Center...", "whisperer.provider_center"),
        )
        bw_providers_menu.Append(
            self._id_bw_provider_status,
            self._menu_label("Provider &Status", "whisperer.provider_status"),
        )
        bw_providers_menu.Append(
            self._id_bw_provider_recommend,
            self._menu_label("Use Re&commended Provider", "whisperer.provider_recommend"),
        )
        bw_providers_menu.Append(
            self._id_bw_provider_select,
            self._menu_label("&Select Provider...", "whisperer.provider_select"),
        )
        whisperer_menu.AppendSubMenu(bw_providers_menu, "&Providers")
        bw_rollout_menu = wx.Menu()
        self._append_bw_safe_mode_badge(bw_rollout_menu)
        bw_rollout_menu.Append(
            self._id_bw_readiness_check,
            self._menu_label("&Readiness Check", "whisperer.readiness_check"),
        )
        bw_rollout_menu.Append(
            self._id_bw_capability_matrix,
            self._menu_label("&Capability Matrix", "whisperer.capability_matrix"),
        )
        whisperer_menu.AppendSubMenu(bw_rollout_menu, "&Rollout")
        if self._feature_enabled("core.bw_whisperer"):
            tools_menu.AppendSubMenu(whisperer_menu, "&BITS Whisperer")

        # Sticky Notes -------------------------------------------------------
        tools_menu.AppendSeparator()
        tools_menu.Append(
            self._id_sticky_notes,
            self._menu_label("Sticky &Notes...", "tools.sticky_notes"),
        )
        tools_menu.Append(
            self._id_new_sticky_note,
            self._menu_label("New Sticky &Note...", "tools.sticky_note_capture"),
        )

        # Advanced (expanded: power-tool utilities + Macros + Authoring +
        # Document Intake + Shell Integration, per menus.md §10.3) ----------
        power_tools_menu = wx.Menu()
        self._append_power_tools_group(power_tools_menu, "power_tools")
        power_tools_menu.AppendSeparator()
        macro_menu = wx.Menu()
        macro_menu.Append(
            self._id_start_macro_recording,
            self._menu_label("&Start Recording", "tools.start_macro_recording"),
        )
        macro_menu.Append(
            self._id_stop_macro_recording,
            self._menu_label("S&top Recording", "tools.stop_macro_recording"),
        )
        macro_menu.Append(
            self._id_play_last_macro,
            self._menu_label("&Play Last Macro", "tools.play_last_macro"),
        )
        macro_menu.Append(
            self._id_manage_macros,
            self._menu_label("&Manage Macros...", "tools.manage_macros"),
        )
        power_tools_menu.AppendSubMenu(macro_menu, "&Macros")
        power_tools_menu.AppendSeparator()
        dev_console_menu = wx.Menu()
        dev_console_menu.Append(
            self._id_dev_console_python,
            self._menu_label("Open &Python Console...", "tools.open_python_console"),
        )
        dev_console_menu.Append(
            self._id_dev_console_ts,
            self._menu_label("Open &TypeScript Console...", "tools.open_typescript_console"),
        )
        dev_console_menu.AppendSeparator()
        dev_console_menu.Append(
            self._id_dev_copy_diagnostic,
            self._menu_label("&Copy Diagnostic Summary", "tools.copy_diagnostic_summary"),
        )
        dev_console_menu.Append(
            self._id_dev_restart_ts_worker,
            self._menu_label("&Restart TypeScript Worker", "tools.restart_typescript_worker"),
        )
        power_tools_menu.AppendSubMenu(dev_console_menu, "&Developer Console")
        power_tools_menu.AppendSeparator()
        power_tools_menu.Append(
            self._id_regex_helper,
            self._menu_label("Regular Expression &Helper...", "tools.regex_helper"),
        )
        power_tools_menu.Append(
            self._id_pandoc_wizard,
            self._menu_label("Pandoc Conversion &Wizard...", "tools.pandoc_wizard"),
        )
        power_tools_menu.Append(
            self._id_external_tools,
            self._menu_label(
                "External Tools and Format &Support...",
                "tools.external_tools",
            ),
        )
        power_tools_menu.Append(
            self._id_yaml_structure_editor,
            self._menu_label("&YAML Structure Editor...", "tools.yaml_structure_editor"),
        )
        power_tools_menu.AppendSeparator()
        intake_menu = wx.Menu()
        intake_menu.Append(
            self._id_document_intake_report,
            self._menu_label("&Document Intake Report...", "tools.document_intake_report"),
        )
        intake_menu.Append(
            self._id_review_extraction_quality,
            self._menu_label("&Review Extraction Quality...", "tools.review_extraction_quality"),
        )
        intake_menu.Append(
            self._id_report_bad_extraction,
            self._menu_label("R&eport Bad Extraction...", "tools.report_bad_extraction"),
        )
        power_tools_menu.AppendSubMenu(intake_menu, "Document &Intake")
        power_tools_menu.AppendSeparator()
        power_tools_menu.Append(
            self._id_shell_install,
            self._menu_label("&Install Shell Integration...", "tools.shell_install"),
        )
        power_tools_menu.Append(
            self._id_shell_remove,
            self._menu_label("&Remove Shell Integration", "tools.shell_remove"),
        )
        tools_menu.AppendSubMenu(power_tools_menu, "&Advanced")

        # Quillins ------------------------------------------------------------
        tools_menu.AppendSubMenu(self._build_quillins_menu(), "&Quillins")

        # Accessibility -------------------------------------------------------
        accessibility_menu = wx.Menu()
        accessibility_menu.Append(self._id_accessibility_audit, "Accessibility A&udit...")
        accessibility_menu.Append(
            self._id_keyboard_trap_snapshot,
            "&Keyboard Trap && Tab-Order Snapshot...",
        )
        accessibility_menu.Append(self._id_validate_contrast, "&Validate Contrast...")
        accessibility_menu.Append(self._id_link_inventory, "Link Inventory && Alt-Text Catalo&g...")
        self._append_power_tools_accessibility_items(accessibility_menu)
        tools_menu.AppendSubMenu(accessibility_menu, "A&ccessibility")

        # Customize & Support (Support + Customize merged per §10.3) ----------
        customize_support_menu = wx.Menu()
        customize_support_menu.Append(
            self._id_preferences,
            self._menu_label("Pre&ferences...", "app.preferences"),
        )
        customize_support_menu.Append(
            self._id_menu_editor,
            self._menu_label("Customize &Menus...", "app.menu_editor"),
        )
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(
            self._id_profiles_and_features,
            self._menu_label("&Profiles and Features...", "tools.profiles_and_features_settings"),
        )
        customize_support_menu.Append(self._id_status_bar_settings, "&Status Bar Layout...")
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(self._id_share_export, "&Export and Back Up...")
        customize_support_menu.Append(self._id_share_import, "&Import or Restore...")
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(self._id_keymap_editor, "&Keymap Editor...")
        customize_support_menu.Append(self._id_export_keymap, "&Export Keymap...")
        customize_support_menu.Append(self._id_import_keymap, "&Import Keymap...")
        customize_support_menu.Append(self._id_reset_keymap, "&Reset Keymap")
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(self._id_notifications, "Show &Notifications")
        customize_support_menu.Append(self._id_save_diagnostics, "Save &Diagnostics...")
        customize_support_menu.Append(self._id_open_logs_folder, "Open &Logs Folder")
        customize_support_menu.Append(
            self._id_open_diagnostics_folder,
            "Open &Diagnostics Folder",
        )
        customize_support_menu.Append(self._id_check_updates, "Check for &Updates")
        tools_menu.AppendSubMenu(customize_support_menu, "&Customize && Support")

        # The former top-level "Settings" menu is gone. All configuration now
        # lives together under Tools > Customize (Preferences, Customize Menus,
        # profiles/features, export/import, and keymap), which is the
        # Windows/Tools convention. Nothing references settings_menu after
        # this point; do not append it to the menu bar.

        help_menu = wx.Menu()
        help_menu.Append(
            self._id_help_on_control,
            self._menu_label("Help on This &Control\tF1", "help.help_on_control"),
        )
        help_menu.Append(
            self._id_context_help,
            self._menu_label("&What Can I Do Here?\tShift+F1", "help.what_can_i_do_here"),
        )
        help_menu.Append(
            self._id_announce_context_shortcuts,
            self._menu_label("Announce Mode &Shortcuts", "help.context_help"),
        )
        help_menu.Append(
            self._id_help_status_page,
            self._menu_label("Status &Page", "help.status_page"),
        )
        help_menu.Append(
            self._id_why_dont_i_see_feature,
            self._menu_label("&Why Don't I See a Feature?", "help.why_dont_i_see_feature"),
        )
        help_menu.AppendSeparator()
        self._id_open_user_guide = wx.NewIdRef()
        self._id_open_third_party_notices = wx.NewIdRef()
        help_menu.Append(self._id_open_user_guide, "Open User &Guide\tCtrl+F1")
        help_menu.Append(
            self._id_open_third_party_notices,
            "Open &Third-Party Notices",
        )
        help_menu.Append(self._id_open_welcome_guide, "Open &Welcome Guide")
        help_menu.Append(self._id_open_keyboard_reference, "Open Keyboard &Reference")
        help_menu.Append(
            self._id_profile_onboarding,
            self._menu_label("&Personalise QUILL...", "help.startup_wizard"),
        )
        help_menu.AppendSeparator()
        help_menu.Append(
            self._id_save_diagnostics,
            self._menu_label("Save &Diagnostics...", "help.save_diagnostics"),
        )
        help_menu.Append(
            self._id_report_bug,
            self._menu_label("Report a &Bug...", "help.report_bug"),
        )
        help_menu.AppendSeparator()
        profiles_menu = wx.Menu()
        profiles_menu.Append(
            self._id_switch_feature_profile,
            self._menu_label("&Switch Profile...", "help.switch_feature_profile"),
        )
        profiles_menu.Append(
            self._id_feature_profile_health_check,
            self._menu_label(
                "Profile &Health Check...",
                "help.feature_profile_health_check",
            ),
        )
        profiles_menu.Append(
            self._id_individual_feature_toggles,
            self._menu_label(
                "Manage &Individual Features...",
                "tools.individual_feature_toggles",
            ),
        )
        profiles_menu.AppendSeparator()
        profiles_menu.Append(
            self._id_undo_profile_change,
            self._menu_label("&Undo Last Profile Change", "help.undo_last_profile_change"),
        )
        profiles_menu.Append(
            self._id_reset_feature_profile,
            self._menu_label("Reset to &Essential Profile", "help.reset_feature_profile"),
        )
        help_menu.AppendSubMenu(profiles_menu, "Feature &Profiles")
        # "Check for Updates on Startup" lives in Settings now (removed the
        # duplicate Help-menu toggle).
        help_menu.Append(self._id_check_updates, "Check for &Updates...")
        if self._feature_enabled("core.glow"):
            help_menu.Append(self._id_check_glow_updates, "Check for &GLOW Updates...")
        help_menu.Append(self._id_about_quill, "&About Quill")

        # MENU-REORDER (menus.md Phase 1): every top-level menu is attached to the
        # bar here, in one place, in the conventional Windows order. Menu *content*
        # is built above in arbitrary order; wx lets bar order be set independently
        # of construction order. Keep this list in sync with ``_TOP_MENU_DEFS``.
        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(edit_menu, "&Edit")
        menu_bar.Append(view_menu, "&View")
        menu_bar.Append(insert_menu, "&Insert")
        menu_bar.Append(format_menu, "F&ormat")
        menu_bar.Append(navigate_menu, "&Navigate")
        menu_bar.Append(search_menu, "&Search")
        menu_bar.Append(tools_menu, "&Tools")
        menu_bar.Append(window_menu, "&Window")
        menu_bar.Append(help_menu, "&Help")

        self._apply_menu_customization(menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._refresh_contextual_menu_items()
        self._apply_ai_menu_enabled()

        self.frame.Bind(wx.EVT_MENU, lambda _e: self.new_file(), id=self._id_new)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_file(), id=self._id_open)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_url(), id=self._id_open_url)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_from_remote(),
            id=self._id_open_remote,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.save_to_remote(),
            id=self._id_save_to_remote,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.save_copy_to_remote(),
            id=self._id_save_copy_to_remote,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_remote_sites(),
            id=self._id_manage_remote_sites,
        )
        self._bind_ssh_file_menu()
        self._bind_github_menu()
        self._dt_bind_devtools_menu()
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.save_file(), id=self._id_save)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.save_file_as(), id=self._id_save_as)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.close_current_document(),
            id=self._id_close_document,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.save_all_files(), id=self._id_save_all)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.reload_from_disk(),
            id=self._id_reload_from_disk,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_external_changes_now(),
            id=self._id_check_external_changes,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.restore_backup(),
            id=self._id_restore_backup,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.save_session(), id=self._id_save_session)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_session(), id=self._id_open_session)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.page_setup(), id=self._id_page_setup)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.print_document(), id=self._id_print)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.save_as_plain_text(),
            id=self._id_save_plain_text,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_palette(), id=self._id_palette)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_preferences(), id=self._id_preferences)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_menu_editor(), id=self._id_menu_editor)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.exit_app(), id=self._id_exit)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_about_quill(), id=self._id_about_quill)
        # macOS routes the application-menu "About" to wx.ID_ABOUT — wire it to
        # the same custom dialog so the Apple-menu About shows the links too.
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_about_quill(), id=wx.ID_ABOUT)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_help_on_control(),
            id=self._id_help_on_control,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_context_help(),
            id=self._id_context_help,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.announce_context_mode_shortcuts(),
            id=self._id_announce_context_shortcuts,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_help_status_page(),
            id=self._id_help_status_page,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_feature_explanation(),
            id=self._id_why_dont_i_see_feature,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.switch_feature_profile(),
            id=self._id_switch_feature_profile,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_feature_profile_health_check(),
            id=self._id_feature_profile_health_check,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_individual_feature_toggles(),
            id=self._id_individual_feature_toggles,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.undo_last_profile_change(),
            id=self._id_undo_profile_change,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.reset_feature_profile_to_essential(),
            id=self._id_reset_feature_profile,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.run_startup_wizard(),
            id=self._id_profile_onboarding,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_whisperer_about_page(),
            id=self._id_whisperer_about,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_hub(),
            id=self._id_ai_hub,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_writing_assistant(),
            id=self._id_ai_assistant,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_prompt_studio(),
            id=self._id_ai_prompt_studio,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_agent_center(),
            id=self._id_ai_agent_center,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.make_document_accessible(),
            id=self._id_ai_accessibility_agent,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_prompt_library(),
            id=self._id_prompt_library,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_skill_library(),
            id=self._id_skill_library,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_grammar_with_ai(),
            id=self._id_check_grammar_ai,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ask_quill_chat(),
            id=self._id_ask_quill_chat,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._refresh_ai_status(),
            id=self._id_ai_status_badge,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._refresh_ai_status(),
            id=self._id_ai_status_detail,
        )
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_ai_enabled, id=self._id_ai_enabled)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_model_settings(),
            id=self._id_ai_model,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._forget_assistant_api_key(),
            id=self._id_ai_forget_key,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_session_browser(),
            id=self._id_ai_session_browser,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_preferences(),
            id=self._id_ai_connection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_rewrite_selection(),
            id=self._id_ai_rewrite_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_summarize_selection(),
            id=self._id_ai_summarize_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_continue_writing(),
            id=self._id_ai_continue_writing,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_fix_grammar(),
            id=self._id_ai_fix_grammar,
        )
        self._refresh_ai_status()
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.send_to_tray(), id=self._id_send_to_tray)
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_tray_mode,
            id=self._id_toggle_tray_mode,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_soft_wrap,
            id=self._id_toggle_soft_wrap,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_auto_side_preview,
            id=self._id_toggle_auto_side_preview,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_tab_control,
            id=self._id_toggle_tab_control,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_find_wrap,
            id=self._id_toggle_find_wrap,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_title_full_path,
            id=self._id_toggle_title_full_path,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_auto_check_updates,
            id=self._id_toggle_auto_check_updates,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_dirty_title_style("text"),
            id=self._id_dirty_title_text,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_dirty_title_style("asterisk"),
            id=self._id_dirty_title_asterisk,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_dirty_title_style("asterisk_text"),
            id=self._id_dirty_title_asterisk_text,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_dark_mode,
            id=self._id_toggle_dark_mode,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_persistent_undo,
            id=self._id_toggle_persistent_undo,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_spellcheck_as_you_type,
            id=self._id_toggle_spellcheck_as_you_type,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_intellisense_as_you_type,
            id=self._id_toggle_intellisense_as_you_type,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.preview_in_app(),
            id=self._id_preview,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_side_preview(),
            id=self._id_split_preview,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.focus_preview(),
            id=self._id_focus_preview,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.preview_in_browser(),
            id=self._id_browser_preview,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_writing_assistant(),
            id=self._id_ai_assistant,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_train_writing_style(),
            id=self._id_train_style,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_writing_instructions(),
            id=self._id_writing_instructions,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_start_with_no_document_open,
            id=self._id_start_with_no_document_open,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.next_document(), id=self._id_next_document)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.previous_document(),
            id=self._id_previous_document,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.insert_link(), id=self._id_insert_link)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.follow_link(), id=self._id_follow_link)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.start_selection(), id=self._id_start_selection)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.complete_selection(), id=self._id_complete_selection
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.reselect(), id=self._id_reselect)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.go_to_start_of_selection(),
            id=self._id_go_to_start_of_selection,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.copy_all(), id=self._id_copy_all)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.unselect_all(), id=self._id_unselect_all)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.say_selected(), id=self._id_say_selected)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.read_all(), id=self._id_read_all)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.select_line(), id=self._id_select_line)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.select_paragraph(),
            id=self._id_select_paragraph,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.select_block(), id=self._id_select_block)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.expand_selection(), id=self._id_expand_selection
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.shrink_selection(), id=self._id_shrink_selection
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.set_named_mark(), id=self._id_set_named_mark)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.jump_to_named_mark(), id=self._id_jump_to_named_mark
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_review_buffer(), id=self._id_open_review_buffer
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.select_to_start_of_line(),
            id=self._id_select_to_start_of_line,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.select_to_end_of_line(),
            id=self._id_select_to_end_of_line,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.select_to_start_of_document(),
            id=self._id_select_to_start_of_document,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.select_to_end_of_document(),
            id=self._id_select_to_end_of_document,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.sort_lines_ascending(),
            id=self._id_sort_lines_ascending,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.sort_lines_descending(),
            id=self._id_sort_lines_descending,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.reverse_lines(), id=self._id_reverse_lines)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.remove_duplicate_lines(),
            id=self._id_remove_duplicate_lines,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.trim_trailing_whitespace(),
            id=self._id_trim_trailing_whitespace,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.normalize_whitespace(),
            id=self._id_normalize_whitespace,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.convert_indentation_to_spaces(),
            id=self._id_convert_indentation_to_spaces,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.convert_indentation_to_tabs(),
            id=self._id_convert_indentation_to_tabs,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.set_mark(), id=self._id_set_mark)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.pop_mark(), id=self._id_pop_mark)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.exchange_point_and_mark(),
            id=self._id_exchange_point_mark,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.list_marks(), id=self._id_list_marks)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.undo(), id=self._id_undo)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.redo(), id=self._id_redo)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.copy_with_source(),
            id=self._id_copy_with_source,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            self._on_toggle_extend_selection_mode,
            id=self._id_toggle_extend_selection_mode,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.find_text(), id=self._id_find)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.replace_text(), id=self._id_replace)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.replace_all_text(), id=self._id_replace_all)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.go_to_line(), id=self._id_go_to_line)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.go_to_page(), id=self._id_go_to_page)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_back_location(),
            id=self._id_back_location,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_forward_location(),
            id=self._id_forward_location,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_next_heading(),
            id=self._id_next_heading,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_previous_heading(),
            id=self._id_previous_heading,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_next_block(),
            id=self._id_next_block,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_previous_block(),
            id=self._id_previous_block,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_outline_navigator(),
            id=self._id_outline_navigator,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_heading_organizer(),
            id=self._id_heading_organizer,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.match_bracket(),
            id=self._id_match_bracket,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_next_token(),
            id=self._id_next_token,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_previous_token(),
            id=self._id_previous_token,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_document_language(),
            id=self._id_set_language,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.speak_window_title(),
            id=self._id_speak_window_title,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.speak_full_path(),
            id=self._id_speak_full_path,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.speak_status_summary(),
            id=self._id_speak_status_summary,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_start_with_file(),
            id=self._id_compare_start_with_file,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_dialog_next(),
            id=self._id_compare_next,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_dialog_previous(),
            id=self._id_compare_previous,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_current_summary(),
            id=self._id_compare_current,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_toggle_ignore_whitespace(),
            id=self._id_compare_toggle_whitespace,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_generate_report(),
            id=self._id_compare_generate_report,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_next_structure(),
            id=self._id_next_structure,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_previous_structure(),
            id=self._id_previous_structure,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_next_region(),
            id=self._id_next_region,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.navigate_previous_region(),
            id=self._id_previous_region,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.set_bookmark(), id=self._id_set_bookmark)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.go_to_bookmark(), id=self._id_go_to_bookmark)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.list_bookmarks(),
            id=self._id_list_bookmarks,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.find_next(), id=self._id_find_next)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.find_previous(), id=self._id_find_previous)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.find_all_matches(),
            id=self._id_find_all_matches,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.search_in_files(),
            id=self._id_search_in_files,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.replace_in_files(),
            id=self._id_replace_in_files,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_upper_case(), id=self._id_upper_case)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_lower_case(), id=self._id_lower_case)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_title_case(), id=self._id_title_case)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_sentence_case(),
            id=self._id_sentence_case,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_toggle_case(), id=self._id_toggle_case)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_toggle_line_comment(),
            id=self._id_toggle_line_comment,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_toggle_block_comment(),
            id=self._id_toggle_block_comment,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_indent(), id=self._id_indent)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_outdent(), id=self._id_outdent)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.move_line_up(), id=self._id_move_line_up)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.move_line_down(), id=self._id_move_line_down)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.duplicate_line(), id=self._id_duplicate_line)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.delete_line(), id=self._id_delete_line)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.join_lines(), id=self._id_join_lines)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.quote_lines(), id=self._id_quote_lines)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.unquote_lines(), id=self._id_unquote_lines)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_bold(), id=self._id_format_bold)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_italic(), id=self._id_format_italic)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_heading(1), id=self._id_heading_1)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_heading(2), id=self._id_heading_2)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_heading(3), id=self._id_heading_3)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_heading(4), id=self._id_heading_4)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_heading(5), id=self._id_heading_5)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_heading(6), id=self._id_heading_6)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.decrease_heading_level(),
            id=self._id_decrease_heading_level,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.increase_heading_level(),
            id=self._id_increase_heading_level,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.style_headings(), id=self._id_style_headings)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_insert_bullet_list(),
            id=self._id_insert_bullet_list,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_insert_numbered_list(),
            id=self._id_insert_numbered_list,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_insert_task_list(),
            id=self._id_insert_task_list,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_list_manager(),
            id=self._id_open_list_manager,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_insert_code_block(),
            id=self._id_insert_code_block,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_insert_footnote(),
            id=self._id_insert_footnote,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_insert_table(),
            id=self._id_insert_table,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.insert_html_tag(), id=self._id_insert_html_tag)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.insert_markdown_tag(),
            id=self._id_insert_markdown_tag,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.insert_snippet(),
            id=self._id_insert_snippet,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_snippets(),
            id=self._id_manage_snippets,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.expand_abbreviation_at_cursor(),
            id=self._id_expand_abbreviation,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_abbreviation_manager(),
            id=self._id_manage_abbreviations,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_abbreviation_expansion(),
            id=self._id_toggle_abbreviation_expansion,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_word_prediction(),
            id=self._id_word_prediction,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_sticky_notes(),
            id=self._id_sticky_notes,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.create_sticky_note(),
            id=self._id_new_sticky_note,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_word_count(), id=self._id_word_count)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_spell_check_dialog(),
            id=self._id_spell_check,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.previous_misspelling(),
            id=self._id_previous_misspelling,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.next_misspelling(),
            id=self._id_next_misspelling,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_misspelling_list(),
            id=self._id_misspelling_list,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_thesaurus(),
            id=self._id_thesaurus,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_dictionary_status(),
            id=self._id_dictionary_status,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.ocr_image_file(), id=self._id_ocr_image)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.ocr_clipboard_image(), id=self._id_ocr_clipboard
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.ocr_screen_capture(), id=self._id_ocr_screen)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.describe_image_with_ai(), id=self._id_describe_image
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_regex_helper(), id=self._id_regex_helper)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.toggle_read_aloud(), id=self._id_read_aloud)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.stop_read_aloud(),
            id=self._id_read_aloud_stop,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_read_aloud_voice(),
            id=self._id_read_aloud_voice,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_read_aloud_settings(),
            id=self._id_read_aloud_settings,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.generate_speech_audio(),
            id=self._id_read_aloud_generate_audio,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_read_aloud(),
            id=self._id_ai_speech_start_pause,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.stop_read_aloud(),
            id=self._id_ai_speech_stop,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_read_aloud_voice(),
            id=self._id_ai_speech_voice,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_read_aloud_settings(),
            id=self._id_ai_speech_settings,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.generate_speech_audio(),
            id=self._id_ai_speech_generate_audio,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_announcement_backend(),
            id=self._id_announcement_backend,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_announcement_backend("auto"),
            id=self._id_announcement_backend_auto,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_announcement_backend("prism"),
            id=self._id_announcement_backend_prism,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_announcement_backend("status_only"),
            id=self._id_announcement_backend_status_only,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_announcement_trace_capture(),
            id=self._id_toggle_announcement_trace,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_sound(),
            id=self._id_toggle_sound,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_sound_events_dialog(),
            id=self._id_sound_events,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_dictation(),
            id=self._id_dictation,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_dictation_voice_commands(),
            id=self._id_dictation_voice_commands,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_bw_model_manager(),
            id=self._id_bw_model_manager,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_bw_model_status(),
            id=self._id_bw_model_status,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.apply_bw_recommended_model(),
            id=self._id_bw_model_recommend,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_bw_parakeet_visibility(),
            id=self._id_bw_toggle_parakeet,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_bw_faster_whisper_engine(),
            id=self._id_bw_check_faster_whisper,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_bw_provider_center(),
            id=self._id_bw_provider_center,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_bw_provider_status(),
            id=self._id_bw_provider_status,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.apply_bw_recommended_provider(),
            id=self._id_bw_provider_recommend,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.select_bw_provider(),
            id=self._id_bw_provider_select,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_bw_readiness_check(),
            id=self._id_bw_readiness_check,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_bw_capability_matrix_page(),
            id=self._id_bw_capability_matrix,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_bw_download_queue(),
            id=self._id_bw_download_queue,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_watch_folder_monitoring(),
            id=self._id_watch_folder_toggle,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_watch_folder_settings(),
            id=self._id_watch_folder_settings,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_watch_folder_status(),
            id=self._id_watch_folder_status,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_document_intake_report(),
            id=self._id_document_intake_report,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.review_extraction_quality(),
            id=self._id_review_extraction_quality,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_bad_extraction(),
            id=self._id_report_bad_extraction,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_pandoc_wizard(),
            id=self._id_pandoc_wizard,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_external_tools_dialog(),
            id=self._id_external_tools,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.install_shell_integration(),
            id=self._id_shell_install,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.remove_shell_integration(),
            id=self._id_shell_remove,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_notifications(),
            id=self._id_notifications,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_updates(),
            id=self._id_check_updates,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_glow_updates(),
            id=self._id_check_glow_updates,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.validate_contrast(),
            id=self._id_validate_contrast,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_status_bar_settings(),
            id=self._id_status_bar_settings,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_share_export_dialog(),
            id=self._id_share_export,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_share_import_dialog(),
            id=self._id_share_import,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_keymap_editor(),
            id=self._id_keymap_editor,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_profiles_and_features_settings(),
            id=self._id_profiles_and_features,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_link_inventory(),
            id=self._id_link_inventory,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_with_file(),
            id=self._id_compare_with_file,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_open_documents(),
            id=self._id_compare_open_documents,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_next_difference(),
            id=self._id_compare_next_difference,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_previous_difference(),
            id=self._id_compare_previous_difference,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.compare_announce_difference(),
            id=self._id_compare_announce_difference,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_compare_difference_list(),
            id=self._id_compare_difference_list,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_compare_synchronization(),
            id=self._id_compare_toggle_sync,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_compare_options(),
            id=self._id_compare_options,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.create_compare_summary_document(),
            id=self._id_compare_create_summary,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.copy_current_difference(),
            id=self._id_compare_copy_current,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.copy_all_differences(),
            id=self._id_compare_copy_all,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.start_macro_recording(),
            id=self._id_start_macro_recording,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.stop_macro_recording(),
            id=self._id_stop_macro_recording,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.play_last_macro(),
            id=self._id_play_last_macro,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_macros(),
            id=self._id_manage_macros,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.export_keymap_file(),
            id=self._id_export_keymap,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.import_keymap_file(),
            id=self._id_import_keymap,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.reset_keymap_defaults(),
            id=self._id_reset_keymap,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_welcome_guide(),
            id=self._id_open_welcome_guide,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_keyboard_reference(),
            id=self._id_open_keyboard_reference,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_user_guide(),
            id=self._id_open_user_guide,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_third_party_notices(),
            id=self._id_open_third_party_notices,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.save_diagnostics_bundle(),
            id=self._id_save_diagnostics,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.report_bug(),
            id=self._id_report_bug,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_logs_folder(),
            id=self._id_open_logs_folder,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_diagnostics_folder(),
            id=self._id_open_diagnostics_folder,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_yaml_structure_editor(),
            id=self._id_yaml_structure_editor,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_accessibility_audit(),
            id=self._id_accessibility_audit,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_audit_document(),
            id=self._id_glow_audit_document,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_audit_selection(),
            id=self._id_glow_audit_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_fix_document(),
            id=self._id_glow_fix_document,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.glow_fix_selection(),
            id=self._id_glow_fix_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_keyboard_trap_snapshot(),
            id=self._id_keyboard_trap_snapshot,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.new_notebook(),
            id=self._id_new_notebook,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.new_notebook_from_folder(),
            id=self._id_new_notebook_from_folder,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_notebook(),
            id=self._id_open_notebook,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.notebook_save_snapshot(),
            id=self._id_notebook_save_snapshot,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_notebook_snapshots(),
            id=self._id_notebook_restore_snapshot,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_notebook_snapshots(),
            id=self._id_manage_notebook_snapshots,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_entries_panel(),
            id=self._id_toggle_entries_panel,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.go_to_entry_in_notebook(),
            id=self._id_go_to_entry_in_notebook,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.go_to_heading_in_notebook(),
            id=self._id_go_to_heading_in_notebook,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.go_to_bookmark_in_notebook(),
            id=self._id_go_to_bookmark_in_notebook,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.go_to_sticky_note_in_notebook(),
            id=self._id_go_to_sticky_note_in_notebook,
        )
        # Copy Tray per-slot bindings (slots 1-12)
        for _n in range(1, 13):
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, _slot=_n: self.copy_to_tray_slot(_slot),
                id=self._id_copy_tray_slots[_n - 1],
            )
        for _n in range(1, 13):
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, _slot=_n: self.paste_from_tray_slot(_slot),
                id=self._id_paste_tray_slots[_n - 1],
            )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.copy_to_next_slot(),
            id=self._id_copy_to_next_slot,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.search_tray_slots(),
            id=self._id_search_tray_slots,
        )
        self.frame.Bind(wx.EVT_MENU, self._on_open_recent)
        self.frame.Bind(wx.EVT_MENU, self._on_session_menu)
        self.frame.Bind(wx.EVT_MENU, self._on_recent_session_menu)
        self.frame.Bind(wx.EVT_MENU, self._on_menu_command_activity)
