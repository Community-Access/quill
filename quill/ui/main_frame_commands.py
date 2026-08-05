"""Command registry construction for MainFrame (CQ-1 decomposition).

``CommandRegistryMixin`` owns ``_build_commands`` -- the single place every
QUILL command id is registered with its title, category, default keybinding,
and handler -- and ``_command_to_menu_id_map``, which pairs command ids with
their menu item ids for accelerator and menu-state work. Both were extracted
verbatim from ``main_frame.py``; they run on ``MainFrame`` (``self``) and rely
on handler methods provided by ``MainFrame`` and its other mixins.
"""

from __future__ import annotations


class CommandRegistryMixin:
    def _build_commands(self) -> None:
        self.commands.register(
            "file.new",
            "New File",
            self.new_file,
            self._binding_for("file.new"),
        )
        # #1246: Ctrl+T = new document tab in the current notebook. Reuses new_file
        # (which already opens a new tab); this is a second, tab-oriented entry point.
        self.commands.register(
            "window.new_document_tab",
            "New Tab",
            self.new_file,
            self._binding_for("window.new_document_tab"),
        )
        self.commands.register(
            "file.open",
            "Open File...",
            self.open_file,
            self._binding_for("file.open"),
        )
        self.commands.register(
            "file.ssh_quick_connect",
            "Open over SSH: Quick Connect...",
            self.open_ssh_quick_connect,
            self._binding_for("file.ssh_quick_connect"),
        )
        self.commands.register(
            "file.ssh_site_manager",
            "Open over SSH: Site Manager...",
            self.open_ssh_site_manager,
            self._binding_for("file.ssh_site_manager"),
        )
        self.commands.register(
            "file.open_github_repository",
            "Open Remote GitHub Repository...",
            self.open_github_repository,
            None,
        )
        self.commands.register(
            "file.open_github_file_url",
            "Open Remote GitHub File URL...",
            self.open_github_file_url,
            None,
        )
        self.commands.register(
            "file.github_save_back",
            "Save to GitHub...",
            self.github_save_back,
            None,
        )
        self.commands.register(
            "file.github_manage_accounts",
            "Manage GitHub Accounts...",
            self.manage_github_accounts,
            None,
        )
        self.commands.register(
            "file.open_github_items",
            "Open GitHub Items...",
            self.open_github_items_viewer,
            None,
        )
        self.commands.register(
            "tools.open_python_console",
            "Open Python Console...",
            self.open_python_console,
            None,
        )
        self.commands.register(
            "tools.open_typescript_console",
            "Open TypeScript Console...",
            self.open_typescript_console,
            None,
        )
        self.commands.register(
            "tools.copy_diagnostic_summary",
            "Copy Diagnostic Summary",
            self.copy_diagnostic_summary,
            None,
        )
        self.commands.register(
            "tools.restart_typescript_worker",
            "Restart TypeScript Worker",
            self.restart_typescript_worker,
            None,
        )
        self.commands.register(
            "file.save",
            "Save",
            self.save_file,
            self._binding_for("file.save"),
        )
        self.commands.register(
            "file.save_as",
            "Save As...",
            self.save_file_as,
            self._binding_for("file.save_as"),
        )
        self.commands.register(
            "file.close_document",
            "Close Document",
            self.close_current_document,
            self._binding_for("file.close_document"),
        )
        self.commands.register(
            "file.save_all",
            "Save All",
            self.save_all_files,
            None,
        )
        self.commands.register(
            "file.reload_from_disk",
            "Reload from Disk",
            self.reload_from_disk,
            None,
        )
        self.commands.register(
            "file.restore_backup",
            "Restore Backup...",
            self.restore_backup,
            None,
        )
        self.commands.register(
            "file.page_setup",
            "Page Setup...",
            self.page_setup,
            None,
        )
        self.commands.register(
            "file.print",
            "Print...",
            self.print_document,
            self._binding_for("file.print"),
        )
        self.commands.register(
            "file.print_studio",
            "Print Studio...",
            self.print_studio,
            self._binding_for("file.print_studio"),
        )
        self.commands.register(
            "file.header_footer",
            "Header and Footer...",
            self.edit_header_footer,
            self._binding_for("file.header_footer"),
        )
        self.commands.register(
            "file.save_as_plain_text",
            "Save As Plain Text...",
            self.save_as_plain_text,
            None,
        )
        self.commands.register(
            "file.choose_encoding",
            "Choose Encoding...",
            self.choose_document_encoding,
            None,
        )
        self.commands.register(
            "file.toggle_line_endings",
            "Toggle Line Endings",
            self.toggle_line_endings,
            None,
        )
        self.commands.register(
            "file.open_containing_folder",
            "Open Containing Folder",
            self.open_containing_folder,
            None,
        )
        self.commands.register(
            "file.open_url",
            "Open from URL...",
            self.open_url,
            None,
        )
        self.commands.register(
            "file.save_session",
            "Save Session...",
            self.save_session,
            None,
        )
        self.commands.register(
            "file.open_session",
            "Open Session...",
            self.open_session,
            None,
        )
        self.commands.register(
            "app.command_palette",
            "Command Palette...",
            self.open_palette,
            self._binding_for("app.command_palette"),
        )
        self.commands.register(
            "app.preferences",
            "Preferences...",
            self.open_general_preferences,
            self._binding_for("app.preferences"),
        )
        self.commands.register(
            "app.exit",
            "Exit",
            self.exit_app,
            self._binding_for("app.exit"),
        )
        self.commands.register(
            "window.next_document",
            "Next Document",
            self.next_document,
            self._binding_for("window.next_document"),
        )
        self.commands.register(
            "window.previous_document",
            "Previous Document",
            self.previous_document,
            self._binding_for("window.previous_document"),
        )
        # Jump straight to the Nth open document (Alt+1..Alt+9, Alt+0 = 10th).
        for _position in range(1, 11):
            command_id = f"window.go_to_document_{_position}"
            self.commands.register(
                command_id,
                f"Go to Document {_position}",
                (lambda position=_position: self.go_to_document(position)),
                self._binding_for(command_id),
            )
        self.commands.register(
            "window.close_other_documents",
            "Close Other Documents",
            self.close_other_documents,
            self._binding_for("window.close_other_documents"),
        )
        self.commands.register(
            "navigate.speak_window_title",
            "Speak Window Title",
            self.speak_window_title,
            self._binding_for("navigate.speak_window_title"),
        )
        self.commands.register(
            "navigate.speak_full_path",
            "Speak Full Path",
            self.speak_full_path,
            self._binding_for("navigate.speak_full_path"),
        )
        self.commands.register(
            "navigate.speak_status_summary",
            "Speak Status Summary",
            self.speak_status_summary,
            self._binding_for("navigate.speak_status_summary"),
        )
        self.commands.register(
            "view.send_to_tray",
            "Send to Tray",
            self.send_to_tray,
            self._binding_for("view.send_to_tray"),
        )
        # Verbosity system (sub-PR 1.5).
        self.commands.register(
            "verbosity.toggle_quiet",
            "Toggle Quiet Mode",
            self.toggle_quiet_mode,
            self._binding_for("verbosity.toggle_quiet"),
        )
        self.commands.register(
            "verbosity.toggle_meeting",
            "Toggle Meeting Mode",
            self.toggle_meeting_mode,
            self._binding_for("verbosity.toggle_meeting"),
        )
        self.commands.register(
            "verbosity.undo",
            "Undo Verbosity Change",
            self.verbosity_undo,
            self._binding_for("verbosity.undo"),
        )
        self.commands.register(
            "verbosity.history",
            "Announcement History",
            self.open_verbosity_preferences,
            self._binding_for("verbosity.history"),
        )
        self.commands.register(
            "verbosity.preferences",
            "Verbosity Preferences",
            self.open_verbosity_preferences,
            self._binding_for("verbosity.preferences"),
        )
        self.commands.register(
            "verbosity.where_am_i",
            "Where Am I",
            self.verbosity_where_am_i,
            self._binding_for("verbosity.where_am_i"),
        )
        self.commands.register(
            "verbosity.what_changed",
            "What Changed",
            self.verbosity_what_changed,
            self._binding_for("verbosity.what_changed"),
        )
        self.commands.register(
            "verbosity.speak_status",
            "Speak Status Bar",
            self.verbosity_speak_status,
            self._binding_for("verbosity.speak_status"),
        )
        self.commands.register(
            "view.toggle_soft_wrap",
            "Toggle Soft Wrap",
            self.toggle_soft_wrap,
            self._binding_for("view.toggle_soft_wrap"),
        )
        self.commands.register(
            "view.toggle_tab_control",
            "Toggle Tab Control",
            self.toggle_tab_control,
            self._binding_for("view.toggle_tab_control"),
        )
        self.commands.register(
            "view.toggle_find_wrap",
            "Toggle Find Wrap",
            self.toggle_find_wrap,
            None,
        )
        self.commands.register(
            "view.toggle_dark_mode",
            "Toggle Dark Mode",
            self.toggle_dark_mode,
            self._binding_for("view.toggle_dark_mode"),
        )
        self.commands.register(
            "view.toggle_persistent_undo",
            "Toggle Persistent Undo",
            self.toggle_persistent_undo,
            None,
        )
        self.commands.register(
            "view.toggle_spellcheck_as_you_type",
            "Toggle Spell Check As You Type",
            self.toggle_spellcheck_as_you_type,
            None,
        )
        self.commands.register(
            "view.toggle_intellisense_as_you_type",
            "Toggle Word Prediction As You Type",
            self.toggle_intellisense_as_you_type,
            None,
        )
        self.commands.register(
            "view.preview",
            "Preview",
            self.preview_in_app,
            self._binding_for("view.preview"),
        )
        self.commands.register(
            "view.split_preview",
            "Preview Side by Side",
            self.toggle_side_preview,
            self._binding_for("view.split_preview"),
        )
        self.commands.register(
            "view.focus_preview",
            "Focus Preview",
            self.focus_preview,
            self._binding_for("view.focus_preview"),
        )
        self.commands.register(
            "view.browser_preview",
            "Browser Preview",
            self.preview_in_browser,
            self._binding_for("view.browser_preview"),
        )
        self.commands.register(
            "tools.ai_hub",
            "AI Hub",
            self.open_ai_hub,
            None,
        )
        self.commands.register(
            "tools.ai_assistant",
            "Writing Assistant",
            self.open_writing_assistant,
            None,
        )
        self.commands.register(
            "tools.ai_prompt_studio",
            "Prompt Studio",
            self.open_prompt_studio,
            None,
        )
        self.commands.register(
            "tools.ai_agent_center",
            "Agent Center",
            self.open_agent_center,
            None,
        )
        self.commands.register(
            "tools.ai_accessibility_agent",
            "Accessibility Tune-Up",
            self.make_document_accessible,
            None,
        )
        self.commands.register(
            "tools.ai_library",
            "AI Library",
            self.open_ai_library,
            None,
        )
        self.commands.register(
            "tools.prompt_library",
            "Prompt Library",
            self.open_prompt_library,
            None,
        )
        self.commands.register(
            "tools.skill_library",
            "Skill Library",
            self.open_skill_library,
            None,
        )
        self.commands.register(
            "tools.check_grammar_ai",
            "Check Grammar with AI",
            self.check_grammar_with_ai,
            None,
        )
        self.commands.register(
            "tools.ask_quill_chat",
            "Ask Quill Chat",
            self.open_ask_quill_chat,
            self._binding_for("tools.ask_quill_chat"),
        )
        self.commands.register(
            "tools.ask_quill_conversation",
            "Ask Quill: Voice Conversation",
            self.open_ask_quill_conversation,
            self._binding_for("tools.ask_quill_conversation"),
        )
        self.commands.register(
            "tools.ai_model",
            "AI Model",
            self.open_ai_model_settings,
            None,
        )
        self.commands.register(
            "tools.ai_session_browser",
            "AI Session Branches",
            self.open_ai_session_browser,
            None,
        )
        self.commands.register(
            "tools.ai_connection",
            "AI Connection",
            self.open_ai_preferences,
            None,
        )
        self.commands.register(
            "publishing.connections",
            "Publishing Connections...",
            self._open_publishing_connections,
            None,
        )
        self.commands.register(
            "publishing.verify_connection",
            "Verify Current Publishing Connection",
            self._verify_current_publishing_connection,
            None,
        )
        self.commands.register(
            "publishing.browse_content",
            "Browse Publishing Content...",
            self._browse_publishing_content,
            None,
        )
        self.commands.register(
            "publishing.create_draft",
            "Create Post Draft...",
            self._create_publishing_draft,
            None,
        )
        self.commands.register(
            "publishing.publish_current",
            "Publish Post Now...",
            self._publish_current_document,
            None,
        )
        self.commands.register(
            "publishing.create_page_draft",
            "Create Page Draft...",
            self._create_publishing_page_draft,
            None,
        )
        self.commands.register(
            "publishing.publish_current_page",
            "Publish Page Now...",
            self._publish_current_page,
            None,
        )
        self.commands.register(
            "publishing.compare_remote_item",
            "Compare With Remote...",
            self._compare_publishing_remote_item,
            None,
        )
        self.commands.register(
            "publishing.update_remote_item",
            "Update Remote Content...",
            self._update_publishing_remote_item,
            None,
        )
        self.commands.register(
            "publishing.publish_remote_item",
            "Publish Open Remote Content...",
            self._publish_open_remote_item,
            None,
        )
        self.commands.register(
            "publishing.schedule_publish",
            "Schedule Publish...",
            self._schedule_publishing_publish,
            None,
        )
        self.commands.register(
            "tools.ai_rewrite_selection",
            "Rewrite Selection",
            self.open_ai_rewrite_selection,
            None,
        )
        self.commands.register(
            "tools.ai_summarize_selection",
            "Summarize Selection",
            self.open_ai_summarize_selection,
            None,
        )
        self.commands.register(
            "tools.ai_expand_selection",
            "Expand Selection",
            self.open_ai_expand_selection,
            None,
        )
        self.commands.register(
            "tools.ai_generate_toc",
            "Generate Table of Contents",
            self.open_ai_toc,
            None,
        )
        self.commands.register(
            "tools.ai_switch_engine",
            "Switch AI Engine",
            self.cycle_ai_engine,
            self._binding_for("tools.ai_switch_engine"),
        )
        self.commands.register(
            "tools.ai_spell_check",
            "AI Spell Check...",
            self.ai_spell_check,
            self._binding_for("tools.ai_spell_check"),
        )
        self.commands.register(
            "tools.ai_spell_check_interactive",
            "AI Spell Check Interactive...",
            self.ai_spell_check_interactive,
            self._binding_for("tools.ai_spell_check_interactive"),
        )
        self.commands.register(
            "tools.ai_grammar_style",
            "AI Grammar and Style Check...",
            self.ai_grammar_style_check,
            self._binding_for("tools.ai_grammar_style"),
        )
        self.commands.register(
            "tools.ai_translate_selection",
            "Translate Selection...",
            self.ai_translate_selection,
            self._binding_for("tools.ai_translate_selection"),
        )
        self.commands.register(
            "tools.ai_thesaurus",
            "AI Thesaurus",
            self.open_ai_thesaurus,
            self._binding_for("tools.ai_thesaurus"),
        )
        self.commands.register(
            "tools.ai_reading_order",
            "Improve Reading Order",
            self.open_ai_improve_reading_order,
            self._binding_for("tools.ai_reading_order"),
        )
        from quill.ui.agent_editor_host import register_agent_commands

        register_agent_commands(self)  # Run Agent palette entries (one per catalog agent)
        self.commands.register(
            "tools.ai_continue_writing",
            "Continue Writing",
            self.open_ai_continue_writing,
            None,
        )
        self.commands.register(
            "tools.ai_fix_grammar",
            "Fix Grammar",
            self.open_ai_fix_grammar,
            None,
        )
        self.commands.register(
            "tools.train_writing_style",
            "Train Writing Style",
            self.open_train_writing_style,
            None,
        )
        self.commands.register(
            "tools.writing_instructions",
            "Open Writing Instructions",
            self.open_writing_instructions,
            None,
        )
        self.commands.register(
            "view.toggle_overwrite_mode",
            "Toggle Overwrite Mode",
            self.toggle_overwrite_mode,
            None,
        )
        self.commands.register(
            "navigate.go_to_line",
            "Go To Line...",
            self.go_to_line,
            self._binding_for("navigate.go_to_line"),
        )
        self.commands.register(
            "navigate.go_to_page",
            "Go To Page...",
            self.go_to_page,
            self._binding_for("navigate.go_to_page"),
        )
        self.commands.register(
            "navigate.back_location",
            "Back Location",
            self.navigate_back_location,
            self._binding_for("navigate.back_location"),
        )
        self.commands.register(
            "navigate.forward_location",
            "Forward Location",
            self.navigate_forward_location,
            self._binding_for("navigate.forward_location"),
        )
        self.commands.register(
            "navigate.next_heading",
            "Next Heading",
            self.navigate_next_heading,
            None,
        )
        self.commands.register(
            "navigate.previous_heading",
            "Previous Heading",
            self.navigate_previous_heading,
            None,
        )
        self.commands.register(
            "navigate.next_block",
            "Next Block",
            self.navigate_next_block,
            None,
        )
        self.commands.register(
            "navigate.previous_block",
            "Previous Block",
            self.navigate_previous_block,
            None,
        )
        self.commands.register(
            "navigate.outline_navigator",
            "Outline Navigator...",
            self.open_outline_navigator,
            self._binding_for("navigate.outline_navigator"),
        )
        self.commands.register(
            "navigate.heading_organizer",
            "Heading Organizer...",
            self.open_heading_organizer,
            self._binding_for("navigate.heading_organizer"),
        )
        self.commands.register(
            "navigate.next_token",
            "Next Token",
            self.navigate_next_token,
            self._binding_for("navigate.next_token"),
        )
        self.commands.register(
            "navigate.previous_token",
            "Previous Token",
            self.navigate_previous_token,
            self._binding_for("navigate.previous_token"),
        )
        self.commands.register(
            "navigate.set_language",
            "Set Document Language...",
            self.set_document_language,
            self._binding_for("navigate.set_language"),
        )
        self.commands.register(
            "app.display_language",
            "Change Display Language...",
            self.change_display_language,
            self._binding_for("app.display_language"),
        )
        self.commands.register(
            "navigate.match_bracket",
            "Match Bracket",
            self.match_bracket,
            self._binding_for("navigate.match_bracket"),
        )
        self.commands.register(
            "navigate.next_structure",
            "Next Structure",
            self.navigate_next_structure,
            self._binding_for("navigate.next_structure"),
        )
        self.commands.register(
            "navigate.previous_structure",
            "Previous Structure",
            self.navigate_previous_structure,
            self._binding_for("navigate.previous_structure"),
        )
        self.commands.register(
            "navigate.next_region",
            "Next Region",
            self.navigate_next_region,
            self._binding_for("navigate.next_region"),
        )
        self.commands.register(
            "navigate.previous_region",
            "Previous Region",
            self.navigate_previous_region,
            self._binding_for("navigate.previous_region"),
        )
        for command_id, label, handler in (
            ("table.next_cell", "Table: Next Cell", self.table_next_cell),
            ("table.previous_cell", "Table: Previous Cell", self.table_previous_cell),
            ("table.cell_below", "Table: Cell Below", self.table_cell_below),
            ("table.cell_above", "Table: Cell Above", self.table_cell_above),
            ("table.row_start", "Table: First Cell in Row", self.table_row_start),
            ("table.row_end", "Table: Last Cell in Row", self.table_row_end),
            ("table.first_cell", "Table: First Cell", self.table_first_cell),
            ("table.last_cell", "Table: Last Cell", self.table_last_cell),
        ):
            self.commands.register(command_id, label, handler, self._binding_for(command_id))
        self.commands.register(
            "navigate.set_bookmark",
            "Set Bookmark...",
            self.set_bookmark,
            None,
        )
        self.commands.register(
            "navigate.go_to_bookmark",
            "Go To Bookmark...",
            self.go_to_bookmark,
            None,
        )
        self.commands.register(
            "navigate.list_bookmarks",
            "List Bookmarks...",
            self.list_bookmarks,
            self._binding_for("navigate.list_bookmarks"),
        )
        self.commands.register(
            "tools.word_count",
            "Word Count...",
            self.show_word_count,
            self._binding_for("tools.word_count"),
        )
        self.commands.register(
            "tools.sticky_notes",
            "Sticky Notes...",
            self.manage_sticky_notes,
            None,
        )
        self.commands.register(
            "tools.sticky_note_capture",
            "New Sticky Note...",
            self.create_sticky_note,
            self._binding_for("tools.sticky_note_capture"),
        )
        self._register_global_hotkey_commands()
        self._register_adp_commands()
        self.commands.register(
            "tools.spell_check_dialog",
            "Spell Check...",
            self.open_spell_check_dialog,
            self._binding_for("tools.spell_check_dialog"),
        )
        self.commands.register(
            "tools.next_misspelling",
            "Next Misspelling",
            self.next_misspelling,
            self._binding_for("tools.next_misspelling"),
        )
        self.commands.register(
            "tools.previous_misspelling",
            "Previous Misspelling",
            self.previous_misspelling,
            self._binding_for("tools.previous_misspelling"),
        )
        self.commands.register(
            "tools.misspelling_list",
            "Misspelling List...",
            self.open_misspelling_list,
            self._binding_for("tools.misspelling_list"),
        )
        self.commands.register(
            "tools.thesaurus",
            "Thesaurus...",
            self.show_thesaurus,
            self._binding_for("tools.thesaurus"),
        )
        self.commands.register(
            "tools.dictionary_status",
            "Dictionary Status...",
            self.show_dictionary_status,
            None,
        )
        self.commands.register(
            "tools.ocr_image",
            "OCR Image...",
            self.ocr_image_file,
            None,
        )
        self.commands.register(
            "file.import_convert",
            "Import / Convert Document (OCR)",
            self.import_convert_document,
            None,
        )
        self.commands.register(
            "tools.install_local_ocr",
            "Install Local OCR Engine (Tesseract)",
            self.install_local_ocr_engine,
            None,
        )
        self.commands.register(
            "tools.ocr_services",
            "OCR and Conversion Services",
            self.show_ocr_services_overview,
            None,
        )
        self.commands.register(
            "tools.review_last_ocr",
            "Review Last OCR Result",
            self.review_last_ocr_result,
            None,
        )
        self.commands.register(
            "tools.ocr_service_settings",
            "OCR Service Settings",
            self.open_ocr_service_settings,
            None,
        )
        self.commands.register(
            "tools.delete_ocr_temp",
            "Delete OCR Temporary Files",
            self.delete_ocr_temp_files,
            None,
        )
        self.commands.register(
            "tools.ocr_clipboard",
            "OCR Clipboard Image",
            self.ocr_clipboard_image,
            self._binding_for("tools.ocr_clipboard"),
        )
        self.commands.register(
            "tools.ocr_screen",
            "OCR Screen Capture...",
            self.ocr_screen_capture,
            self._binding_for("tools.ocr_screen"),
        )
        self.commands.register(
            "tools.describe_image",
            "Describe Image...",
            self.describe_image_with_ai,
            None,
        )
        self.commands.register(
            "tools.read_aloud_start_pause",
            "Read Aloud Start/Pause",
            self.toggle_read_aloud,
            self._binding_for("tools.read_aloud_start_pause"),
        )
        self.commands.register(
            "tools.read_aloud_stop",
            "Read Aloud Stop",
            self.stop_read_aloud,
            self._binding_for("tools.read_aloud_stop"),
        )
        self.commands.register(
            "tools.read_aloud_voice",
            "Read Aloud Voice...",
            self.choose_read_aloud_voice,
            None,
        )
        self.commands.register(
            "tools.read_aloud_settings",
            "Read Aloud Settings...",
            self.choose_read_aloud_settings,
            None,
        )
        self.commands.register(
            "tools.read_aloud_generate_audio",
            "Generate Speech Audio...",
            self.generate_speech_audio,
            None,
        )
        # Experimental: read the document aloud in the user's real browser (where
        # the full/online voices are available). Registered unconditionally so the
        # command palette has it the moment the setting is toggled — no restart.
        # The handler self-guards (read_document_in_browser shows a "turn it on
        # under Experimental" message when disabled), and the *menu* entry stays
        # gated on the setting (rebuilt live by _build_menu on settings-apply), so
        # nothing appears in the menu until opted in. See quill/core/browser_reader.py.
        self.commands.register(
            "tools.read_aloud_edge",
            "Read Document in Browser (Experimental)",
            self.read_document_in_browser,
            None,
        )
        self.commands.register(
            "tools.announcement_backend",
            "Announcement Backend...",
            self.choose_announcement_backend,
            None,
        )
        self.commands.register(
            "tools.announcement_trace_toggle",
            "Toggle Announcement Trace Capture",
            self.toggle_announcement_trace_capture,
            None,
        )
        self.commands.register(
            "tools.sound_toggle",
            "Toggle Sound Notifications",
            self.toggle_sound,
            self._binding_for("tools.sound_toggle"),
        )
        self.commands.register(
            "tools.sound_events",
            "Manage Sound Events",
            self.open_sound_events_dialog,
            self._binding_for("tools.sound_events"),
        )
        self.commands.register(
            "tools.dictation_toggle",
            "Dictation",
            self.toggle_dictation,
            self._binding_for("tools.dictation_toggle"),
            feature_id="core.dictation",
        )
        self.commands.register(
            "tools.voice_command",
            "Voice Command (Offline)",
            self.voice_command_toggle,
            self._binding_for("tools.voice_command"),
            # Hey QUILL Phase 1: push-to-talk over the offline speech stack,
            # bounded by the agent safe-tool allowlist. See
            # docs/planning/quill-hey-quill-voice-interaction-plan.md.
            feature_id="core.voice_commands",
        )
        self.commands.register(
            "tools.voice_conversation",
            "Voice Conversation Mode",
            self.voice_conversation_toggle,
            self._binding_for("tools.voice_conversation"),
            # Hey QUILL Phase 2: the same on-device capture wrapped in the
            # conversation state machine (warm cues, cancel window, follow-up).
            feature_id="core.voice_commands",
        )
        self.commands.register(
            "tools.voice_wakeword",
            "Listen for Hey QUILL (Wake Word)",
            self.voice_wakeword_toggle,
            self._binding_for("tools.voice_wakeword"),
            # Hey QUILL Phase 3: always-listening on-device for the wake phrase.
            feature_id="core.voice_commands",
        )
        self.commands.register(
            "tools.voice_status",
            "Speak Voice Status",
            self.speak_voice_status,
            self._binding_for("tools.voice_status"),
            # Hey QUILL refinement: say what voice is doing (mic-live check).
            feature_id="core.voice_commands",
        )
        self.commands.register(
            "whisperer.model_manager",
            "BITS Whisperer Speech Model Manager...",
            self.open_bw_model_manager,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.model_status",
            "BITS Whisperer Speech Model Status",
            self.show_bw_model_status,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.model_recommend",
            "BITS Whisperer Use Recommended Speech Model",
            self.apply_bw_recommended_model,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.check_faster_whisper",
            "BITS Whisperer Check faster-whisper Engine",
            self.check_bw_faster_whisper_engine,
            None,
            feature_id="core.bw_transcription",
        )
        self.commands.register(
            "whisperer.provider_center",
            "BITS Whisperer Provider Center...",
            self.open_bw_provider_center,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.provider_status",
            "BITS Whisperer Provider Status",
            self.show_bw_provider_status,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.provider_recommend",
            "BITS Whisperer Use Recommended Provider",
            self.apply_bw_recommended_provider,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.provider_select",
            "BITS Whisperer Select Provider...",
            self.select_bw_provider,
            None,
            feature_id="core.bw_providers",
        )
        self.commands.register(
            "whisperer.readiness_check",
            "BITS Whisperer Readiness Check",
            self.show_bw_readiness_check,
            None,
            feature_id="core.bw_insights",
        )
        self.commands.register(
            "whisperer.capability_matrix",
            "BITS Whisperer Capability Matrix",
            self.show_bw_capability_matrix_page,
            None,
            feature_id="core.bw_insights",
        )
        self.commands.register(
            "whisperer.download_queue",
            "BITS Whisperer Download Queue...",
            self.manage_bw_download_queue,
            None,
            feature_id="core.bw_insights",
        )
        self.commands.register(
            "tools.watch_folder_toggle",
            "Watch Folder Monitoring",
            self.toggle_watch_folder_monitoring,
            None,
            feature_id="core.watch_folder",
        )
        self.commands.register(
            "tools.watch_folder_settings",
            "Watch Folder Settings...",
            self.open_watch_folder_settings,
            None,
            feature_id="core.watch_folder",
        )
        self.commands.register(
            "tools.watch_folder_status",
            "Watch Folder Status...",
            self.show_watch_folder_status,
            None,
            feature_id="core.watch_folder",
        )
        self.commands.register(
            "tools.document_intake_report",
            "Document Intake Report...",
            self.show_document_intake_report,
            self._binding_for("tools.document_intake_report"),
        )
        self.commands.register(
            "tools.review_extraction_quality",
            "Review Extraction Quality...",
            self.review_extraction_quality,
            None,
        )
        self.commands.register(
            "tools.regex_helper",
            "Regular Expression Helper...",
            self.show_regex_helper,
            None,
        )
        self.commands.register(
            "file.convert_file",
            "Convert File...",
            self.convert_file,
            None,
        )
        self.commands.register(
            "tools.external_tools",
            "External Tools and Format Support...",
            self.show_external_tools_dialog,
            None,
        )
        self.commands.register(
            "tools.report_bad_extraction",
            "Report Bad Extraction...",
            self.report_bad_extraction,
            None,
        )
        self.commands.register(
            "tools.shell_install",
            "Install Shell Integration...",
            self.install_shell_integration,
            None,
        )
        self.commands.register(
            "tools.shell_remove",
            "Remove Shell Integration",
            self.remove_shell_integration,
            None,
        )
        self.commands.register(
            "tools.notifications",
            "Open Notifications...",
            self.open_notifications,
            None,
        )
        self.commands.register(
            "tools.check_updates",
            "Check for Updates...",
            self.check_for_updates,
            None,
        )
        self.commands.register(
            "tools.check_glow_updates",
            "Check for GLOW Updates...",
            self.check_for_glow_updates,
            None,
        )
        self.commands.register(
            "tools.compare_with_file",
            "Compare with File...",
            self.compare_with_file,
            None,
        )
        self.commands.register(
            "tools.compare_open_documents",
            "Compare Open Documents...",
            self.compare_open_documents,
            None,
        )
        self.commands.register(
            "tools.compare_next_difference",
            "Next Difference",
            self.compare_next_difference,
            self._binding_for("tools.compare_next_difference"),
        )
        self.commands.register(
            "tools.compare_previous_difference",
            "Previous Difference",
            self.compare_previous_difference,
            self._binding_for("tools.compare_previous_difference"),
        )
        self.commands.register(
            "tools.compare_announce_difference",
            "Announce Current Difference",
            self.compare_announce_difference,
            self._binding_for("tools.compare_announce_difference"),
        )
        self.commands.register(
            "tools.compare_difference_list",
            "Open Difference List...",
            self.open_compare_difference_list,
            None,
        )
        self.commands.register(
            "tools.compare_toggle_sync",
            "Toggle Compare Synchronization",
            self.toggle_compare_synchronization,
            None,
        )
        self.commands.register(
            "tools.compare_options",
            "Compare Options...",
            self.open_compare_options,
            None,
        )
        self.commands.register(
            "tools.compare_create_summary",
            "Create Difference Summary",
            self.create_compare_summary_document,
            None,
        )
        self.commands.register(
            "tools.compare_copy_current_difference",
            "Copy Current Difference",
            self.copy_current_difference,
            None,
        )
        self.commands.register(
            "tools.compare_copy_all_differences",
            "Copy All Differences",
            self.copy_all_differences,
            None,
        )
        self.commands.register(
            "tools.export_keymap",
            "Export Keymap...",
            self.export_keymap_file,
            None,
        )
        self.commands.register(
            "tools.keymap_editor",
            "Keymap Editor...",
            self.open_keymap_editor,
            None,
        )
        self.commands.register(
            "tools.status_bar_settings",
            "Status Bar Layout...",
            self.open_status_bar_settings,
            None,
        )
        self.commands.register(
            "tools.share_export",
            "Export and Back Up...",
            self.open_share_export_dialog,
            None,
        )
        self.commands.register(
            "tools.share_import",
            "Import or Restore...",
            self.open_share_import_dialog,
            None,
        )
        self.commands.register(
            "tools.import_keymap",
            "Import Keymap...",
            self.import_keymap_file,
            None,
        )
        self.commands.register(
            "tools.export_keyboard_pack",
            "Export Keyboard Pack (.kqp)...",
            self.export_keyboard_pack_file,
            None,
        )
        self.commands.register(
            "tools.import_keyboard_pack",
            "Import Keyboard Pack (.kqp)...",
            self.import_keyboard_pack_file,
            None,
        )
        self.commands.register(
            "tools.reset_keymap",
            "Reset Keymap",
            self.reset_keymap_defaults,
            None,
        )
        self.commands.register(
            "tools.reset_all_defaults",
            "Reset Everything to Factory Defaults...",
            self.reset_all_to_factory_defaults,
            None,
        )
        self.commands.register(
            "tools.undo_recommended_updates",
            "Undo Recent Shortcut Change",
            self.undo_recommended_keymap_updates,
            None,
        )
        self.commands.register(
            "tools.post_to_mastodon",
            "Post to Mastodon...",
            self.post_to_mastodon,
            self._binding_for("tools.post_to_mastodon"),
        )
        self.commands.register(
            "tools.manage_mastodon_accounts",
            "Mastodon Accounts...",
            self.manage_mastodon_accounts,
            None,
        )
        self.commands.register(
            "tools.view_mastodon_profile",
            "View Mastodon Profile...",
            self.view_mastodon_profile,
            None,
        )
        self.commands.register(
            "tools.mastodon_add_user_to_list",
            "Add a User to a Mastodon List...",
            self.mastodon_add_user_to_list,
            None,
        )
        self.commands.register(
            "tools.open_welcome_guide",
            "Open Welcome Guide",
            self.open_welcome_guide,
            None,
        )
        self.commands.register(
            "tools.open_keyboard_reference",
            "Open Keyboard Reference",
            self.open_keyboard_reference,
            None,
        )
        self.commands.register(
            "help.open_user_guide",
            "Open User Guide",
            self.open_user_guide,
            None,
        )
        self.commands.register(
            "help.open_third_party_notices",
            "Open Third-Party Notices",
            self.open_third_party_notices,
            None,
        )
        self.commands.register(
            "help.why_dont_i_see_feature",
            "Why Don't I See a Feature?",
            self.show_feature_explanation,
            None,
        )
        self.commands.register(
            "help.switch_feature_profile",
            "Switch Feature Profile...",
            self.switch_feature_profile,
            None,
        )
        self.commands.register(
            "help.feature_profile_health_check",
            "Feature Profile Health Check...",
            self.show_feature_profile_health_check,
            None,
        )
        self.commands.register(
            "tools.individual_feature_toggles",
            "Manage Individual Features...",
            self.open_individual_feature_toggles,
            None,
        )
        self.commands.register(
            "tools.profiles_and_features_settings",
            "Profiles and Features...",
            self.open_profiles_and_features_settings,
            self._binding_for("tools.profiles_and_features_settings"),
        )
        self.commands.register(
            "help.undo_last_profile_change",
            "Undo Last Profile Change",
            self.undo_last_profile_change,
            None,
        )
        self.commands.register(
            "help.reset_feature_profile",
            "Reset to Essential Profile",
            self.reset_feature_profile_to_essential,
            None,
        )
        self.commands.register(
            "help.startup_wizard",
            "Startup Wizard...",
            self.run_startup_wizard,
            None,
        )
        self.commands.register(
            "help.enable_braille_mode",
            "Enable Braille Mode...",
            self.enable_braille_mode,
            None,
        )
        self.commands.register(
            "help.run_profile_onboarding",
            "Startup Wizard...",
            self.run_startup_wizard,
            None,
        )
        self.commands.register(
            "tools.start_macro_recording",
            "Start Macro Recording",
            self.start_macro_recording,
            None,
        )
        self.commands.register(
            "tools.stop_macro_recording",
            "Stop Macro Recording",
            self.stop_macro_recording,
            None,
        )
        self.commands.register(
            "tools.play_last_macro",
            "Play Last Macro",
            self.play_last_macro,
            None,
        )
        self.commands.register(
            "tools.manage_macros",
            "Manage Macros...",
            self.manage_macros,
            None,
        )
        self.commands.register(
            "tools.cycle_autosave_interval",
            "Cycle Autosave Interval",
            self.cycle_autosave_interval,
            None,
        )
        self.commands.register(
            "help.about_quill",
            "About Quill",
            self.show_about_quill,
            None,
        )
        self.commands.register(
            "help.save_diagnostics",
            "Save Diagnostics...",
            self.save_diagnostics_bundle,
            None,
        )
        self.commands.register(
            "help.report_bug",
            "Report a Bug...",
            self.report_bug,
            None,
        )
        self.commands.register(
            "help.open_logs_folder",
            "Open Logs Folder",
            self.open_logs_folder,
            None,
        )
        self.commands.register(
            "help.open_diagnostics_folder",
            "Open Diagnostics Folder",
            self.open_diagnostics_folder,
            None,
        )
        self.commands.register(
            "help.what_can_i_do_here",
            "What Can I Do Here?",
            self.show_context_help,
            None,
        )
        self.commands.register(
            "whisperer.about",
            "About BITS Whisperer",
            self.show_whisperer_about_page,
            None,
            feature_id="core.bw_whisperer",
        )
        self.commands.register(
            "help.status_page",
            "Status Page",
            self.show_help_status_page,
            None,
        )
        self.commands.register(
            "tools.glow_audit_document",
            "GLOW Audit Current Document",
            self.glow_audit_document,
            None,
        )
        self.commands.register(
            "tools.glow_audit_selection",
            "GLOW Audit Selection",
            self.glow_audit_selection,
            None,
        )
        self.commands.register(
            "tools.glow_fix_document",
            "GLOW Fix Current Document",
            self.glow_fix_document,
            None,
        )
        self.commands.register(
            "tools.glow_fix_selection",
            "GLOW Fix Selection",
            self.glow_fix_selection,
            None,
        )
        self.commands.register(
            "tools.glow_audit_file",
            "GLOW Audit File",
            self.glow_audit_file,
            None,
        )
        self.commands.register(
            "tools.glow_fix_file",
            "GLOW Fix File",
            self.glow_fix_file,
            None,
        )
        self.commands.register(
            "edit.undo",
            "Undo",
            self.undo,
            self._binding_for("edit.undo"),
        )
        self.commands.register(
            "edit.redo",
            "Redo",
            self.redo,
            self._binding_for("edit.redo"),
        )
        self.commands.register(
            "edit.copy_with_source",
            "Copy With Source",
            self.copy_with_source,
            self._binding_for("edit.copy_with_source"),
        )
        self.commands.register(
            "edit.toggle_extend_selection_mode",
            "Toggle Extend Selection Mode",
            self.toggle_extend_selection_mode,
            self._binding_for("edit.toggle_extend_selection_mode"),
        )
        self.commands.register(
            "edit.start_selection",
            "Start Selection",
            self.start_selection,
            self._binding_for("edit.start_selection"),
        )
        self.commands.register(
            "edit.complete_selection",
            "Complete Selection",
            self.complete_selection,
            self._binding_for("edit.complete_selection"),
        )
        self.commands.register(
            "edit.reselect",
            "Reselect",
            self.reselect,
            self._binding_for("edit.reselect"),
        )
        self.commands.register(
            "edit.go_to_start_of_selection",
            "Go to Start of Selection",
            self.go_to_start_of_selection,
            self._binding_for("edit.go_to_start_of_selection"),
        )
        self.commands.register(
            "edit.copy_all",
            "Copy All",
            self.copy_all,
            self._binding_for("edit.copy_all"),
        )
        self.commands.register(
            "edit.unselect_all",
            "Unselect All",
            self.unselect_all,
            self._binding_for("edit.unselect_all"),
        )
        self.commands.register(
            "edit.say_selected",
            "Say Selected",
            self.say_selected,
            self._binding_for("edit.say_selected"),
        )
        self.commands.register(
            "edit.read_all",
            "Read All",
            self.read_all,
            self._binding_for("edit.read_all"),
        )
        self.commands.register(
            "edit.find",
            "Find...",
            self.find_text,
            self._binding_for("edit.find"),
        )
        self.commands.register(
            "edit.find_next",
            "Find Next",
            self.find_next,
            self._binding_for("edit.find_next"),
        )
        self.commands.register(
            "edit.find_previous",
            "Find Previous",
            self.find_previous,
            self._binding_for("edit.find_previous"),
        )
        self.commands.register(
            "edit.replace",
            "Replace...",
            self.replace_text,
            self._binding_for("edit.replace"),
        )
        self.commands.register(
            "edit.find_all_matches",
            "Find All Matches",
            self.find_all_matches,
            self._binding_for("edit.find_all_matches"),
        )
        self.commands.register(
            "tools.search_in_files",
            "Search in Files...",
            self.search_in_files,
            self._binding_for("tools.search_in_files"),
        )
        self.commands.register(
            "tools.replace_in_files",
            "Replace Across Files...",
            self.replace_in_files,
            self._binding_for("tools.replace_in_files"),
        )
        self.commands.register(
            "edit.replace_all",
            "Replace All...",
            self.replace_all_text,
            self._binding_for("edit.replace_all"),
        )
        self.commands.register(
            "edit.insert_link",
            "Insert Link...",
            self.insert_link,
            self._binding_for("edit.insert_link"),
        )
        self.commands.register(
            "app.repeat_last_announcement",
            "Repeat Last Announcement",
            self.repeat_last_announcement,
            self._binding_for("app.repeat_last_announcement"),
        )
        self.commands.register(
            "app.announcement_self_test",
            "Announcement Self-Test...",
            self.run_announcement_self_test,
            self._binding_for("app.announcement_self_test"),
        )
        self.commands.register(
            "app.report_editor_surface",
            "Report Editor Surface",
            self.report_editor_surface,
            self._binding_for("app.report_editor_surface"),
        )
        self.commands.register(
            "ai.suggest_metadata",
            "Suggest Document Metadata...",
            self.suggest_document_metadata,
            self._binding_for("ai.suggest_metadata"),
        )
        self.commands.register(
            "edit.insert_equation",
            "Insert Equation...",
            self.insert_equation,
            self._binding_for("edit.insert_equation"),
        )
        self.commands.register(
            "edit.insert_citation",
            "Insert Citation...",
            self.insert_citation,
            self._binding_for("edit.insert_citation"),
        )
        self.commands.register(
            "power.open_snippet_gallery",
            "Snippet Gallery...",
            self.open_snippet_gallery,
            self._binding_for("power.open_snippet_gallery"),
        )
        self.commands.register(
            "edit.follow_link",
            "Follow Link",
            self.follow_link,
            self._binding_for("edit.follow_link"),
        )
        self.commands.register(
            "edit.word_prediction",
            "Word Prediction...",
            self.show_word_prediction,
            self._binding_for("edit.word_prediction"),
        )
        self.commands.register(
            "edit.select_line",
            "Select Line",
            self.select_line,
            self._binding_for("edit.select_line"),
        )
        self.commands.register(
            "edit.select_paragraph",
            "Select Paragraph",
            self.select_paragraph,
            None,
        )
        self.commands.register(
            "edit.set_mark",
            "Set Mark",
            self.set_mark,
            self._binding_for("edit.set_mark"),
        )
        self.commands.register(
            "edit.pop_mark",
            "Pop Mark",
            self.pop_mark,
            self._binding_for("edit.pop_mark"),
        )
        self.commands.register(
            "edit.exchange_point_mark",
            "Exchange Point and Mark",
            self.exchange_point_and_mark,
            self._binding_for("edit.exchange_point_mark"),
        )
        self.commands.register(
            "edit.list_marks",
            "List Marks",
            self.list_marks,
            self._binding_for("edit.list_marks"),
        )
        self.commands.register(
            "edit.select_block",
            "Select Block",
            self.select_block,
            None,
        )
        self.commands.register(
            "edit.expand_selection",
            "Expand Selection",
            self.expand_selection,
            self._binding_for("edit.expand_selection"),
        )
        self.commands.register(
            "edit.shrink_selection",
            "Shrink Selection",
            self.shrink_selection,
            self._binding_for("edit.shrink_selection"),
        )
        self.commands.register(
            "edit.set_named_mark",
            "Set Named Mark",
            self.set_named_mark,
            self._binding_for("edit.set_named_mark"),
        )
        self.commands.register(
            "edit.jump_to_named_mark",
            "Jump to Named Mark",
            self.jump_to_named_mark,
            self._binding_for("edit.jump_to_named_mark"),
        )
        self.commands.register(
            "edit.open_review_buffer",
            "Open Review Buffer",
            self.open_review_buffer,
            self._binding_for("edit.open_review_buffer"),
        )
        self.commands.register(
            "edit.selection_actions",
            "Selection Actions",
            self.quill_key_selection_actions,
            self._binding_for("edit.selection_actions"),
        )
        self.commands.register(
            "navigate.quick_nav",
            "Quick Nav (Go to Anything)",
            self.open_quick_nav,
            self._binding_for("navigate.quick_nav"),
        )
        self.commands.register(
            "edit.select_to_start_of_line",
            "Select to Start of Line",
            self.select_to_start_of_line,
            self._binding_for("edit.select_to_start_of_line"),
        )
        self.commands.register(
            "edit.select_to_end_of_line",
            "Select to End of Line",
            self.select_to_end_of_line,
            self._binding_for("edit.select_to_end_of_line"),
        )
        self.commands.register(
            "edit.select_to_start_of_document",
            "Select to Start of Document",
            self.select_to_start_of_document,
            self._binding_for("edit.select_to_start_of_document"),
        )
        self.commands.register(
            "edit.select_to_end_of_document",
            "Select to End of Document",
            self.select_to_end_of_document,
            self._binding_for("edit.select_to_end_of_document"),
        )
        self.commands.register(
            "format.insert_html_tag",
            "Insert HTML Tag...",
            self.insert_html_tag,
            self._binding_for("format.insert_html_tag"),
        )
        self.commands.register(
            "format.toggle_line_comment",
            "Toggle Line Comment",
            self.format_toggle_line_comment,
            self._binding_for("format.toggle_line_comment"),
        )
        self.commands.register(
            "format.toggle_block_comment",
            "Toggle Block Comment",
            self.format_toggle_block_comment,
            self._binding_for("format.toggle_block_comment"),
        )
        self.commands.register(
            "format.auto_indent_newline",
            "Auto-Indent Newline",
            self.format_auto_indent_newline,
            self._binding_for("format.auto_indent_newline"),
        )
        self.commands.register(
            "format.indent",
            "Indent",
            self.format_indent,
            self._binding_for("format.indent"),
        )
        self.commands.register(
            "format.outdent",
            "Outdent",
            self.format_outdent,
            self._binding_for("format.outdent"),
        )
        self.commands.register(
            "format.toggle_tab_insert_mode",
            "Toggle Tab Key Mode (Indent / Tab Character)",
            self.toggle_tab_insert_mode,
            self._binding_for("format.toggle_tab_insert_mode"),
        )
        self.commands.register(
            "format.insert_markdown_tag",
            "Insert Markdown Tag...",
            self.insert_markdown_tag,
            self._binding_for("format.insert_markdown_tag"),
        )
        self.commands.register(
            "format.insert_snippet",
            "Insert Snippet...",
            self.insert_snippet,
            self._binding_for("format.insert_snippet"),
        )
        self.commands.register(
            "format.manage_snippets",
            "Manage Snippets...",
            self.manage_snippets,
            self._binding_for("format.manage_snippets"),
        )
        self.commands.register(
            "format.expand_abbreviation",
            "Expand Abbreviation",
            self.expand_abbreviation_at_cursor,
            self._binding_for("format.expand_abbreviation"),
        )
        self.commands.register(
            "format.manage_abbreviations",
            "Manage Abbreviations...",
            self.open_abbreviation_manager,
            self._binding_for("format.manage_abbreviations"),
        )
        self.commands.register(
            "format.toggle_abbreviation_expansion",
            "Toggle Abbreviation Expansion",
            self.toggle_abbreviation_expansion,
            self._binding_for("format.toggle_abbreviation_expansion"),
        )
        self.commands.register(
            "format.switch_document_format",
            "Switch Document Format",
            self.switch_document_format,
            self._binding_for("format.switch_document_format"),
        )
        self.commands.register(
            "format.bold",
            "Bold",
            self.format_bold,
            self._binding_for("format.bold"),
        )
        self.commands.register(
            "format.italic",
            "Italic",
            self.format_italic,
            self._binding_for("format.italic"),
        )
        self.commands.register(
            "format.underline",
            "Underline",
            self.format_underline,
            self._binding_for("format.underline"),
        )
        self.register_format_codes_commands()
        self.register_reveal_codes_commands()
        self.register_inline_note_commands()
        self.register_restore_point_commands()
        self.commands.register(
            "format.heading_1",
            "Insert Heading 1",
            lambda: self.format_heading(1),
            self._binding_for("format.heading_1"),
        )
        self.commands.register(
            "format.heading_2",
            "Insert Heading 2",
            lambda: self.format_heading(2),
            self._binding_for("format.heading_2"),
        )
        self.commands.register(
            "format.heading_3",
            "Insert Heading 3",
            lambda: self.format_heading(3),
            self._binding_for("format.heading_3"),
        )
        self.commands.register(
            "format.heading_4",
            "Insert Heading 4",
            lambda: self.format_heading(4),
            self._binding_for("format.heading_4"),
        )
        self.commands.register(
            "format.heading_5",
            "Insert Heading 5",
            lambda: self.format_heading(5),
            self._binding_for("format.heading_5"),
        )
        self.commands.register(
            "format.heading_6",
            "Insert Heading 6",
            lambda: self.format_heading(6),
            self._binding_for("format.heading_6"),
        )
        self.commands.register(
            "format.decrease_heading_level",
            "Decrease Heading Level",
            self.decrease_heading_level,
            self._binding_for("format.decrease_heading_level"),
        )
        self.commands.register(
            "format.increase_heading_level",
            "Increase Heading Level",
            self.increase_heading_level,
            self._binding_for("format.increase_heading_level"),
        )
        self.commands.register(
            "format.style_headings",
            "Style Headings...",
            self.style_headings,
            self._binding_for("format.style_headings"),
        )
        self.commands.register(
            "format.upper_case",
            "Upper Case",
            self.format_upper_case,
            self._binding_for("format.upper_case"),
        )
        self.commands.register(
            "format.lower_case",
            "Lower Case",
            self.format_lower_case,
            self._binding_for("format.lower_case"),
        )
        self.commands.register(
            "format.title_case",
            "Title Case",
            self.format_title_case,
            None,
        )
        self.commands.register(
            "format.sentence_case",
            "Sentence Case",
            self.format_sentence_case,
            None,
        )
        self.commands.register(
            "format.toggle_case",
            "Toggle Case",
            self.format_toggle_case,
            None,
        )
        self.commands.register(
            "format.move_line_up",
            "Move Line Up",
            self.move_line_up,
            self._binding_for("format.move_line_up"),
        )
        self.commands.register(
            "format.move_line_down",
            "Move Line Down",
            self.move_line_down,
            self._binding_for("format.move_line_down"),
        )
        # PR1 (EdSharp port): section-move pair. Bound to Alt+Shift+Up/Down.
        # See docs/keybinding-standard.md for the §edsharp-ok justification.
        self.commands.register(
            "format.move_section_up",
            "Move Section Up",
            self.move_section_up,
            self._binding_for("format.move_section_up"),
        )
        self.commands.register(
            "format.move_section_down",
            "Move Section Down",
            self.move_section_down,
            self._binding_for("format.move_section_down"),
        )
        self.commands.register(
            "format.duplicate_line",
            "Duplicate Line",
            self.duplicate_line,
            self._binding_for("format.duplicate_line"),
        )
        self.commands.register(
            "format.delete_line",
            "Delete Line",
            self.delete_line,
            self._binding_for("format.delete_line"),
        )
        self.commands.register(
            "format.join_lines",
            "Join Lines",
            self.join_lines,
            None,
        )
        self.commands.register(
            "format.insert_bullet_list",
            "Insert Bullet List",
            self.format_insert_bullet_list,
            None,
        )
        self.commands.register(
            "format.insert_numbered_list",
            "Insert Numbered List",
            self.format_insert_numbered_list,
            None,
        )
        # EdSharp port: list-toggle variants strip an existing list or insert
        # a new one based on the caret context.  See _toggle_list in this
        # module for the insert-vs-strip decision.
        self.commands.register(
            "format.toggle_bullet_list",
            "Toggle Bullet List",
            self.toggle_bullet_list,
            self._binding_for("format.toggle_bullet_list"),
        )
        self.commands.register(
            "format.toggle_numbered_list",
            "Toggle Numbered List",
            self.toggle_numbered_list,
            self._binding_for("format.toggle_numbered_list"),
        )
        self.commands.register(
            "format.insert_task_list",
            "Insert Task List",
            self.format_insert_task_list,
            None,
        )
        self.commands.register(
            "format.list_manager",
            "List Manager",
            self.open_list_manager,
            self._binding_for("format.list_manager"),
        )
        self.commands.register(
            "format.insert_code_block",
            "Insert Code Block",
            self.format_insert_code_block,
            None,
        )
        self.commands.register(
            "format.insert_footnote",
            "Insert Footnote",
            self.format_insert_footnote,
            None,
        )
        self.commands.register(
            "format.insert_table",
            "Insert Table",
            self.format_insert_table,
            self._binding_for("format.insert_table"),
        )
        # Format-aware structured inserts with direct Ctrl+Alt authoring chords
        # (Ctrl+Alt+T table, Ctrl+Alt+Q quote, Ctrl+Alt+H rule);
        # still rebindable in the Keymap Editor.
        self.commands.register(
            "format.blockquote",
            "Insert Block Quote",
            self.format_blockquote,
            self._binding_for("format.blockquote"),
        )
        self.commands.register(
            "format.horizontal_rule",
            "Insert Horizontal Rule",
            self.format_horizontal_rule,
            self._binding_for("format.horizontal_rule"),
        )
        self.commands.register(
            "tools.table_studio",
            "Table Studio (Experimental)",
            self.open_table_studio,
            self._binding_for("tools.table_studio"),
        )
        self.commands.register(
            "tools.work_personas",
            "Work Personas...",
            self.open_work_personas,
            self._binding_for("tools.work_personas"),
        )
        self.commands.register(
            "tools.calculator",
            "Calculator...",
            self.open_calculator,
            self._binding_for("tools.calculator"),
        )
        self.commands.register(
            "app.open_radio",
            "Open Quill Radio",
            lambda: self.open_companion_app("radio"),
            self._binding_for("app.open_radio"),
        )
        self.commands.register(
            "app.open_weather",
            "Open Quill Weather",
            lambda: self.open_companion_app("weather"),
            self._binding_for("app.open_weather"),
        )
        self.commands.register(
            "tools.csv_studio",
            "Open CSV in Table Studio (Experimental)",
            self.open_csv_studio,
            self._binding_for("tools.csv_studio"),
        )
        self.commands.register(
            "edit.sort_lines_ascending",
            "Sort Lines Ascending",
            self.sort_lines_ascending,
            None,
        )
        self.commands.register(
            "edit.sort_lines_descending",
            "Sort Lines Descending",
            self.sort_lines_descending,
            None,
        )
        self.commands.register(
            "edit.reverse_lines",
            "Reverse Lines",
            self.reverse_lines,
            self._binding_for("edit.reverse_lines"),
        )
        self.commands.register(
            "edit.remove_duplicate_lines",
            "Remove Duplicate Lines",
            self.remove_duplicate_lines,
            None,
        )
        self.commands.register(
            "edit.quote_lines",
            "Quote Lines",
            self.quote_lines,
            self._binding_for("edit.quote_lines"),
        )
        self.commands.register(
            "edit.unquote_lines",
            "Unquote Lines",
            self.unquote_lines,
            self._binding_for("edit.unquote_lines"),
        )
        self.commands.register(
            "edit.duplicate_selection",
            "Duplicate Selection",
            self.duplicate_selection,
            None,
        )
        self.commands.register(
            "edit.select_chunk",
            "Select Chunk",
            self.select_chunk,
            self._binding_for("edit.select_chunk"),
        )
        self.commands.register(
            "edit.trim_trailing_whitespace",
            "Trim Trailing Whitespace",
            self.trim_trailing_whitespace,
            None,
        )
        self.commands.register(
            "edit.normalize_whitespace",
            "Normalize Whitespace",
            self.normalize_whitespace,
            None,
        )
        self.commands.register(
            "edit.convert_indentation_to_spaces",
            "Convert Indentation to Spaces",
            self.convert_indentation_to_spaces,
            None,
        )
        self.commands.register(
            "edit.convert_indentation_to_tabs",
            "Convert Indentation to Tabs",
            self.convert_indentation_to_tabs,
            None,
        )
        self.commands.register(
            "help.context_help",
            "Context Help: Current Mode Keys",
            self.announce_context_mode_shortcuts,
            None,
        )
        self.commands.register(
            "document.summary",
            "Document Summary",
            self.show_document_summary,
            None,
        )
        self.commands.register(
            "navigate.go_to_anything",
            "Go to Anything",
            self.open_go_to_anything,
            None,
        )
        self.commands.register(
            "help.key_cheatsheet",
            "Key Cheatsheet",
            self.open_key_cheatsheet,
            None,
        )
        self.commands.register(
            "view.announce_contrast",
            "Announce Contrast Ratio",
            self.announce_contrast_ratio,
            None,
        )
        self.commands.register(
            "view.spoken_echo",
            "Show Spoken Echo",
            self.show_spoken_echo,
            self._binding_for("view.spoken_echo"),
        )
        self.commands.register(
            "help.why_unavailable",
            "Why Is This Unavailable?",
            self.explain_unavailable_feature,
            None,
        )
        self.commands.register(
            "edit.magic_paste",
            "Magic Paste",
            self.magic_paste,
            None,
        )
        # Copy Tray per-slot commands — registered here (not through the power-tools
        # manifest) so they share the explicit menu-ID arrays and avoid duplicate entries.
        for _ct_n in range(1, 13):
            self.commands.register(
                f"edit.copy_to_tray_{_ct_n}",
                f"Copy to Tray Slot {_ct_n}",
                (lambda _n=_ct_n: lambda: self.copy_to_tray_slot(_n))(),
                self._binding_for(f"edit.copy_to_tray_{_ct_n}"),
            )
            self.commands.register(
                f"edit.paste_from_tray_{_ct_n}",
                f"Paste from Tray Slot {_ct_n}",
                (lambda _n=_ct_n: lambda: self.paste_from_tray_slot(_n))(),
                self._binding_for(f"edit.paste_from_tray_{_ct_n}"),
            )
        self.commands.register(
            "edit.copy_to_next_slot",
            "Copy to Next Empty Tray Slot",
            self.copy_to_next_slot,
            self._binding_for("edit.copy_to_next_slot"),
        )
        self.commands.register(
            "edit.search_tray_slots",
            "Search Copy Tray Slots",
            self.search_tray_slots,
            self._binding_for("edit.search_tray_slots"),
        )
        self._register_power_tools_commands()
        self._register_quillins_commands()
        self._register_braille_commands()
        self._register_braille_repair_commands()
        self._register_speech_commands()
        self._register_list_studio_commands()
        self._register_story_studio_commands()
        self._register_vault_commands()
        self._register_git_sync_commands()
        self._register_github_admin_commands()
        self._register_github_extras_commands()
        self._register_gh_bridge_commands()
        self._register_local_git_commands()
        self._register_worktree_commands()
        self._register_media_player_commands()
        self._register_dictation_hotkey_commands()
        self._register_emoji_picker_commands()
        self._register_radio_commands()
        self._register_podcasts_commands()
        self._register_unlock_code_commands()
        self._register_media_sleep_timer_commands()

    def _command_to_menu_id_map(self) -> dict[str, int]:
        return {
            "file.new": self._id_new,
            "window.new_document_tab": self._id_new_tab,
            "file.open": self._id_open,
            "file.open_from_favorite_folder": self._id_open_from_favorite_folder,
            "file.add_favorite_folder": self._id_add_favorite_folder,
            "file.remove_favorite_folder": self._id_remove_favorite_folder,
            "file.save": self._id_save,
            "file.save_as": self._id_save_as,
            "file.close_document": self._id_close_document,
            "file.save_all": self._id_save_all,
            "file.reload_from_disk": self._id_reload_from_disk,
            "file.restore_backup": self._id_restore_backup,
            "file.page_setup": self._id_page_setup,
            "file.print": self._id_print,
            "file.print_studio": self._id_print_studio,
            "file.header_footer": self._id_header_footer,
            "window.next_document": self._id_next_document,
            "window.previous_document": self._id_previous_document,
            "window.go_to_document_1": self._id_go_to_document[0],
            "window.go_to_document_2": self._id_go_to_document[1],
            "window.go_to_document_3": self._id_go_to_document[2],
            "window.go_to_document_4": self._id_go_to_document[3],
            "window.go_to_document_5": self._id_go_to_document[4],
            "window.go_to_document_6": self._id_go_to_document[5],
            "window.go_to_document_7": self._id_go_to_document[6],
            "window.go_to_document_8": self._id_go_to_document[7],
            "window.go_to_document_9": self._id_go_to_document[8],
            "window.go_to_document_10": self._id_go_to_document[9],
            "window.close_other_documents": self._id_close_other_documents,
            "view.send_to_tray": self._id_send_to_tray,
            "view.toggle_soft_wrap": self._id_toggle_soft_wrap,
            "view.toggle_find_wrap": self._id_toggle_find_wrap,
            "view.preview": self._id_preview,
            "view.split_preview": self._id_split_preview,
            "view.focus_preview": self._id_focus_preview,
            "view.browser_preview": self._id_browser_preview,
            "tools.read_aloud_generate_audio": self._id_read_aloud_generate_audio,
            "tools.read_aloud_edge": self._id_read_aloud_edge,
            "tools.ai_hub": self._id_ai_hub,
            "tools.ai_assistant": self._id_ai_assistant,
            "tools.ai_prompt_studio": self._id_ai_prompt_studio,
            "tools.ai_agent_center": self._id_ai_agent_center,
            "tools.ai_accessibility_agent": self._id_ai_accessibility_agent,
            "tools.ai_library": self._id_ai_library,
            "tools.prompt_library": self._id_prompt_library,
            "tools.skill_library": self._id_skill_library,
            "tools.check_grammar_ai": self._id_check_grammar_ai,
            "tools.ask_quill_chat": self._id_ask_quill_chat,
            "tools.ask_quill_conversation": self._id_ask_quill_voice,
            "tools.ai_model": self._id_ai_model,
            "tools.ai_switch_engine": self._id_ai_switch_engine,
            "tools.ai_spell_check": self._id_ai_spell_check,
            "tools.ai_spell_check_interactive": self._id_ai_spell_check_interactive,
            "tools.ai_grammar_style": self._id_ai_grammar_style,
            "tools.ai_translate_selection": self._id_ai_translate_selection,
            "tools.ai_thesaurus": self._id_ai_thesaurus,
            "tools.ai_reading_order": self._id_ai_reading_order,
            "tools.copilot_onboarding": self._id_ai_copilot_setup,
            "tools.validate_agents": self._id_ai_validate_agents,
            "tools.ai_session_browser": self._id_ai_session_browser,
            "tools.ai_connection": self._id_ai_connection,
            "tools.ai_rewrite_selection": self._id_ai_rewrite_selection,
            "tools.ai_summarize_selection": self._id_ai_summarize_selection,
            "tools.ai_continue_writing": self._id_ai_continue_writing,
            "tools.ai_fix_grammar": self._id_ai_fix_grammar,
            "tools.train_writing_style": self._id_train_style,
            "tools.writing_instructions": self._id_writing_instructions,
            "app.exit": self._id_exit,
            "app.command_palette": self._id_palette,
            "app.preferences": self._id_preferences,
            "app.menu_editor": self._id_menu_editor,
            "edit.undo": self._id_undo,
            "edit.redo": self._id_redo,
            "edit.toggle_extend_selection_mode": self._id_toggle_extend_selection_mode,
            "edit.start_selection": self._id_start_selection,
            "edit.complete_selection": self._id_complete_selection,
            "edit.reselect": self._id_reselect,
            "edit.go_to_start_of_selection": self._id_go_to_start_of_selection,
            "edit.copy_all": self._id_copy_all,
            "edit.unselect_all": self._id_unselect_all,
            "edit.say_selected": self._id_say_selected,
            "edit.read_all": self._id_read_all,
            "edit.insert_link": self._id_insert_link,
            "edit.insert_equation": self._id_insert_equation,
            "edit.insert_citation": self._id_insert_citation,
            "power.open_snippet_gallery": self._id_snippet_gallery,
            "edit.follow_link": self._id_follow_link,
            "edit.find": self._id_find,
            "edit.find_next": self._id_find_next,
            "edit.find_previous": self._id_find_previous,
            "edit.find_all_matches": self._id_find_all_matches,
            "edit.replace": self._id_replace,
            "edit.replace_all": self._id_replace_all,
            "edit.select_to_start_of_line": self._id_select_to_start_of_line,
            "edit.select_to_end_of_line": self._id_select_to_end_of_line,
            "edit.select_to_start_of_document": self._id_select_to_start_of_document,
            "edit.select_to_end_of_document": self._id_select_to_end_of_document,
            "edit.set_mark": self._id_set_mark,
            "edit.pop_mark": self._id_pop_mark,
            "edit.exchange_point_mark": self._id_exchange_point_mark,
            "edit.list_marks": self._id_list_marks,
            "edit.set_named_mark": self._id_set_named_mark,
            "edit.jump_to_named_mark": self._id_jump_to_named_mark,
            "edit.open_review_buffer": self._id_open_review_buffer,
            "navigate.go_to_line": self._id_go_to_line,
            "navigate.go_to_page": self._id_go_to_page,
            "navigate.list_bookmarks": self._id_list_bookmarks,
            "navigate.back_location": self._id_back_location,
            "navigate.forward_location": self._id_forward_location,
            "navigate.outline_navigator": self._id_outline_navigator,
            "edit.toggle_fold": self._id_toggle_fold,
            "navigate.next_fold": self._id_next_fold,
            "navigate.previous_fold": self._id_previous_fold,
            "tools.list_folds": self._id_list_folds,
            "navigate.heading_organizer": self._id_heading_organizer,
            "navigate.match_bracket": self._id_match_bracket,
            "navigate.next_token": self._id_next_token,
            "navigate.previous_token": self._id_previous_token,
            "navigate.set_language": self._id_set_language,
            "navigate.next_structure": self._id_next_structure,
            "navigate.previous_structure": self._id_previous_structure,
            "navigate.next_region": self._id_next_region,
            "navigate.previous_region": self._id_previous_region,
            "tools.word_count": self._id_word_count,
            "tools.sticky_notes": self._id_sticky_notes,
            "tools.sticky_note_capture": self._id_new_sticky_note,
            "tools.spell_check_dialog": self._id_spell_check,
            "tools.spell_check_ranked": self._id_spell_check_ranked,
            "tools.spell_check_word_at_cursor": self._id_spell_check_word,
            "tools.previous_misspelling": self._id_previous_misspelling,
            "tools.next_misspelling": self._id_next_misspelling,
            "tools.misspelling_list": self._id_misspelling_list,
            "tools.misspelling_list_ranked": self._id_misspelling_list_ranked,
            "tools.thesaurus": self._id_thesaurus,
            "tools.dictionary_status": self._id_dictionary_status,
            "tools.announcement_backend": self._id_announcement_backend,
            "tools.announcement_trace_toggle": self._id_toggle_announcement_trace,
            "tools.sound_toggle": self._id_toggle_sound,
            "tools.sound_events": self._id_sound_events,
            "tools.watch_folder_toggle": self._id_watch_folder_toggle,
            "tools.watch_folder_settings": self._id_watch_folder_settings,
            "tools.watch_folder_status": self._id_watch_folder_status,
            "tools.document_intake_report": self._id_document_intake_report,
            "tools.review_extraction_quality": self._id_review_extraction_quality,
            "tools.report_bad_extraction": self._id_report_bad_extraction,
            "file.convert_file": self._id_convert_file,
            "tools.external_tools": self._id_external_tools,
            "tools.compare_with_file": self._id_compare_with_file,
            "tools.compare_open_documents": self._id_compare_open_documents,
            "tools.compare_next_difference": self._id_compare_next_difference,
            "tools.compare_previous_difference": self._id_compare_previous_difference,
            "tools.compare_announce_difference": self._id_compare_announce_difference,
            "tools.compare_difference_list": self._id_compare_difference_list,
            "tools.compare_toggle_sync": self._id_compare_toggle_sync,
            "tools.compare_options": self._id_compare_options,
            "tools.compare_create_summary": self._id_compare_create_summary,
            "tools.compare_copy_current_difference": self._id_compare_copy_current,
            "tools.compare_copy_all_differences": self._id_compare_copy_all,
            "tools.start_macro_recording": self._id_start_macro_recording,
            "tools.stop_macro_recording": self._id_stop_macro_recording,
            "tools.play_last_macro": self._id_play_last_macro,
            "tools.manage_macros": self._id_manage_macros,
            "tools.glow_audit_document": self._id_glow_audit_document,
            "tools.glow_audit_selection": self._id_glow_audit_selection,
            "tools.glow_fix_document": self._id_glow_fix_document,
            "tools.glow_fix_selection": self._id_glow_fix_selection,
            "help.save_diagnostics": self._id_save_diagnostics,
            "help.report_bug": self._id_report_bug,
            "help.view_startup_logs": self._id_view_startup_logs,
            "help.open_logs_folder": self._id_open_logs_folder,
            "help.open_diagnostics_folder": self._id_open_diagnostics_folder,
            "help.status_page": self._id_help_status_page,
            "help.startup_wizard": self._id_profile_onboarding,
            "help.context_help": self._id_announce_context_shortcuts,
            "view.spoken_echo": self._id_show_spoken_echo,
            "whisperer.model_manager": self._id_bw_model_manager,
            "whisperer.model_status": self._id_bw_model_status,
            "whisperer.model_recommend": self._id_bw_model_recommend,
            "whisperer.check_faster_whisper": self._id_bw_check_faster_whisper,
            "whisperer.provider_center": self._id_bw_provider_center,
            "whisperer.provider_status": self._id_bw_provider_status,
            "whisperer.provider_recommend": self._id_bw_provider_recommend,
            "whisperer.provider_select": self._id_bw_provider_select,
            "whisperer.readiness_check": self._id_bw_readiness_check,
            "whisperer.capability_matrix": self._id_bw_capability_matrix,
            "whisperer.download_queue": self._id_bw_download_queue,
            "tools.yaml_structure_editor": self._id_yaml_structure_editor,
            "edit.copy_with_source": self._id_copy_with_source,
            "edit.select_line": self._id_select_line,
            "format.decrease_heading_level": self._id_decrease_heading_level,
            "format.increase_heading_level": self._id_increase_heading_level,
            "format.style_headings": self._id_style_headings,
            "format.bold": self._id_format_bold,
            "format.italic": self._id_format_italic,
            "format.underline": self._id_format_underline,
            "format.upper_case": self._id_upper_case,
            "format.lower_case": self._id_lower_case,
            "format.heading_1": self._id_heading_1,
            "format.heading_2": self._id_heading_2,
            "format.heading_3": self._id_heading_3,
            "format.heading_4": self._id_heading_4,
            "format.heading_5": self._id_heading_5,
            "format.heading_6": self._id_heading_6,
            "format.toggle_line_comment": self._id_toggle_line_comment,
            "format.toggle_block_comment": self._id_toggle_block_comment,
            "format.indent": self._id_indent,
            "format.outdent": self._id_outdent,
            "format.toggle_tab_insert_mode": self._id_toggle_tab_mode,
            "format.move_line_up": self._id_move_line_up,
            "format.move_line_down": self._id_move_line_down,
            # PR1 (EdSharp port): section-move command ids.
            "format.move_section_up": self._id_move_section_up,
            "format.move_section_down": self._id_move_section_down,
            "format.duplicate_line": self._id_duplicate_line,
            "format.delete_line": self._id_delete_line,
            "format.insert_html_tag": self._id_insert_html_tag,
            "format.insert_markdown_tag": self._id_insert_markdown_tag,
            "format.insert_snippet": self._id_insert_snippet,
            "format.manage_snippets": self._id_manage_snippets,
            "format.expand_abbreviation": self._id_expand_abbreviation,
            "format.manage_abbreviations": self._id_manage_abbreviations,
            "format.toggle_abbreviation_expansion": self._id_toggle_abbreviation_expansion,
            "edit.word_prediction": self._id_word_prediction,
            # Copy Tray
            "edit.open_copy_tray": self._id_open_copy_tray,
            "edit.clear_all_tray_slots": self._id_clear_all_tray_slots,
            "edit.copy_to_next_slot": self._id_copy_to_next_slot,
            "edit.search_tray_slots": self._id_search_tray_slots,
            **{f"edit.copy_to_tray_{i}": self._id_copy_tray_slots[i - 1] for i in range(1, 13)},
            **{f"edit.paste_from_tray_{i}": self._id_paste_tray_slots[i - 1] for i in range(1, 13)},
        }
