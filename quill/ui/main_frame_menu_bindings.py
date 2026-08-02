"""Menu event bindings for ``MainFrame`` (CQ-1 decomposition).

``MenuBindingsMixin`` owns ``_bind_menu_events`` -- the ~1,900 lines of
``self.frame.Bind(wx.EVT_MENU, ...)`` wiring that was the tail of
``MenuBuilderMixin._build_menu``. It runs after the menu bar is built and
set, binding every menu id to its handler. Purely mechanical: it reads
``wx`` from ``self._wx`` and reaches every id and handler through ``self``,
so it has no module-level imports. Split out so the menu module shrinks
without any behaviour change; ``_build_menu`` now ends by calling
``self._bind_menu_events()``.
"""

from __future__ import annotations

from quill.ui.batch_speech_runner import run_batch_export_to_speech
from quill.ui.pronunciation_dictionary_dialog import run_pronunciation_manager
from quill.ui.translated_speech_runner import run_translated_speech_export


class MenuBindingsMixin:
    def open_companion_app(self, key: str) -> None:
        """Tools > Companion Apps: launch Quill Radio or Quill Weather in its own
        window and process. If it is already running, it just comes forward
        (each is single-instance); if it isn't installed, offer to get it.
        Best-effort; never disrupts QUILL."""
        from quill.ui.companion_offer import try_open_or_offer

        try_open_or_offer(self, key)

    def _bind_menu_events(self) -> None:
        wx = self._wx

        self.frame.Bind(wx.EVT_MENU, lambda _e: self.new_file(), id=self._id_new)
        # #1246: Ctrl+T new document tab (reuses new_file).
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.new_file(), id=self._id_new_tab)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_file(), id=self._id_open)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_url(), id=self._id_open_url)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_from_favorite_folder(),
            id=self._id_open_from_favorite_folder,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.add_favorite_folder(),
            id=self._id_add_favorite_folder,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.remove_favorite_folder(),
            id=self._id_remove_favorite_folder,
        )
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
        self._bind_braille_menu()
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
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.restore_previous_version(),
            id=self._id_restore_previous_version,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.save_session(), id=self._id_save_session)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_session(), id=self._id_open_session)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.page_setup(), id=self._id_page_setup)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.print_document(), id=self._id_print)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.print_studio(), id=self._id_print_studio)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.edit_header_footer(), id=self._id_header_footer
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.save_as_plain_text(),
            id=self._id_save_plain_text,
        )
        # #262: Pandoc Import / Export menu bindings.
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.import_convert_document(),
            id=self._id_import_convert,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.install_local_ocr_engine(),
            id=self._id_install_local_ocr,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.review_last_ocr_result(),
            id=self._id_review_last_ocr,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ocr_service_settings(),
            id=self._id_ocr_service_settings,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.delete_ocr_temp_files(),
            id=self._id_delete_ocr_temp,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.show_ocr_services_overview(),
            id=self._id_ocr_services,
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.import_document("markdown"), id=self._id_import_markdown
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.import_document("html"), id=self._id_import_html
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.import_document("docx"), id=self._id_import_docx
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.import_document("odt"), id=self._id_import_odt)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.import_document("rtf"), id=self._id_import_rtf)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.import_document("epub"), id=self._id_import_epub
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.import_document("csv"), id=self._id_import_csv)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.import_document("latex"), id=self._id_import_latex
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.import_document_other(), id=self._id_import_other
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.export_document("markdown"), id=self._id_export_markdown
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.export_document("html"), id=self._id_export_html
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.export_document("docx"), id=self._id_export_docx
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.export_document("odt"), id=self._id_export_odt)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.export_document("rtf"), id=self._id_export_rtf)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.export_document("epub"), id=self._id_export_epub
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.export_document("pdf"), id=self._id_export_pdf)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.export_document("plain_text"),
            id=self._id_export_plain_text,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.export_daisy(), id=self._id_export_daisy)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.export_document_other(), id=self._id_export_other
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.run_batch_conversion_wizard(),
            id=self._id_batch_convert_import,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.run_batch_conversion_wizard(),
            id=self._id_batch_convert_export,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_palette(), id=self._id_palette)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_vault(), id=self._id_vault_open)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.show_vault_explorer(), id=self._id_vault_explorer
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.follow_wikilink(), id=self._id_vault_follow_link
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_backlinks(), id=self._id_vault_backlinks)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.show_neighborhood(), id=self._id_vault_neighborhood
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.show_unlinked_mentions(), id=self._id_vault_unlinked
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.insert_wikilink(), id=self._id_vault_insert_link
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.complete_at_cursor(), id=self._id_vault_complete
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.rename_current_note(), id=self._id_vault_rename
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.quick_switch_note(), id=self._id_vault_quick_switch
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.search_vault_notes(), id=self._id_vault_search)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_tags(), id=self._id_vault_tags)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.speak_embed_at_cursor(), id=self._id_vault_speak_embed
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.resolve_embed_inline(), id=self._id_vault_resolve_embed
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.insert_note_template(), id=self._id_vault_insert_template
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_todays_note(), id=self._id_vault_today)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.previous_daily_note(), id=self._id_vault_prev_daily
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.next_daily_note(), id=self._id_vault_next_daily
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.export_vault_site(), id=self._id_vault_export_site
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.sync_vault(), id=self._id_vault_sync)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.configure_vault_settings(), id=self._id_vault_settings
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.sync_folder_with_github(),
            id=self._id_git_sync_folder,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_create_repository(),
            id=self._id_github_create_repo,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_fork_repository(),
            id=self._id_github_fork_repo,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_rename_repository(),
            id=self._id_github_rename_repo,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_change_repository_visibility(),
            id=self._id_github_change_visibility,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_change_default_branch(),
            id=self._id_github_change_default_branch,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_configure_branch_protection(),
            id=self._id_github_branch_protection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_delete_branch(),
            id=self._id_github_delete_branch,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_commit_multiple_files(),
            id=self._id_github_commit_multiple,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_browse_organization(),
            id=self._id_github_browse_org,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_create_release(),
            id=self._id_github_create_release,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_dispatch_workflow(),
            id=self._id_github_dispatch_workflow,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_view_notifications(),
            id=self._id_github_notifications,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_view_security_alerts(),
            id=self._id_github_security_alerts,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_list_codespaces(),
            id=self._id_github_list_codespaces,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_create_codespace(),
            id=self._id_github_create_codespace,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_copilot_suggest(),
            id=self._id_github_copilot_suggest,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.github_copilot_explain(),
            id=self._id_github_copilot_explain,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_uncommitted_changes(),
            id=self._id_localgit_uncommitted,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_switch_branch(),
            id=self._id_localgit_switch_branch,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_stash_changes(),
            id=self._id_localgit_stash_changes,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_manage_stashes(),
            id=self._id_localgit_manage_stashes,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_blame_at_cursor(),
            id=self._id_localgit_blame,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_bisect_start(),
            id=self._id_localgit_bisect_start,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_bisect_reset(),
            id=self._id_localgit_bisect_reset,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_resolve_conflicts(),
            id=self._id_localgit_resolve_conflicts,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_interactive_rebase(),
            id=self._id_localgit_interactive_rebase,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.local_git_rebase_abort(),
            id=self._id_localgit_rebase_abort,
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_story_studio(), id=self._id_open_story_studio
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_work_personas(), id=self._id_work_personas
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_calculator(), id=self._id_calculator)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_general_preferences(), id=self._id_preferences
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_menu_editor(), id=self._id_menu_editor)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.exit_app(), id=self._id_exit)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._open_publishing_connections(),
            id=self._id_publishing_connections,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._verify_current_publishing_connection(),
            id=self._id_publishing_verify_connection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._browse_publishing_content(),
            id=self._id_publishing_browse_content,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._create_publishing_draft(),
            id=self._id_publishing_create_draft,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._publish_current_document(),
            id=self._id_publishing_publish_current,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._create_publishing_page_draft(),
            id=self._id_publishing_create_page_draft,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._publish_current_page(),
            id=self._id_publishing_publish_current_page,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._compare_publishing_remote_item(),
            id=self._id_publishing_compare_remote_item,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._update_publishing_remote_item(),
            id=self._id_publishing_update_remote_item,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._publish_open_remote_item(),
            id=self._id_publishing_publish_remote_item,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self._schedule_publishing_publish(),
            id=self._id_publishing_schedule_publish,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_about_quill(), id=self._id_about_quill)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.enable_braille_mode(),
            id=self._id_enable_braille_mode,
        )
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
            lambda _e: self.show_spoken_echo(),
            id=self._id_show_spoken_echo,
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
            lambda _e: self.open_optional_components(),
            id=self._id_download_components,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_redeem_unlock_code_dialog(),
            id=self._id_redeem_unlock_code,
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
            lambda _e: self.open_ai_library(),
            id=self._id_ai_library,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_hub(),
            id=self._id_ai_hub,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.cycle_ai_engine(),
            id=self._id_ai_switch_engine,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_copilot_onboarding(),
            id=self._id_ai_copilot_setup,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_agent_validator(),
            id=self._id_ai_validate_agents,
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
            lambda _e: self.ai_spell_check(),
            id=self._id_ai_spell_check,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_spell_check_interactive(),
            id=self._id_ai_spell_check_interactive,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_grammar_style_check(),
            id=self._id_ai_grammar_style,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_translate_selection(),
            id=self._id_ai_translate_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_translate_document(),
            id=self._id_ai_translate_document,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_transcribe_audio_file(),
            id=self._id_ai_transcribe_audio,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_tts_read_selection(),
            id=self._id_ai_tts_read_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_tts_read_document(),
            id=self._id_ai_tts_read_document,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_tts_stop(),
            id=self._id_ai_tts_stop,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ai_tts_export_mp3(),
            id=self._id_ai_tts_export_mp3,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_document_qa(),
            id=self._id_ai_document_qa,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ask_quill_chat(),
            id=self._id_ask_quill_chat,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ask_quill_conversation(),
            id=self._id_ask_quill_voice,
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
            lambda _e: self.open_speech_hub(),
            id=self._id_speech_models,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.transcribe_audio_offline(),
            id=self._id_speech_transcribe,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.generate_captions_offline(),
            id=self._id_speech_captions,
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.dictate_offline_toggle(), id=self._id_speech_dictate
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.toggle_locked_dictation(), id=self._id_dictation_lock
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.toggle_dictation_pause(), id=self._id_dictation_pause
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.speak_dictation_status(), id=self._id_dictation_status
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.stop_dictation_keep_speech(), id=self._id_dictation_stop
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.cancel_dictation_discard(), id=self._id_dictation_cancel
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_dictation_settings(), id=self._id_dictation_settings
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_dictation_history(), id=self._id_dictation_history
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.voice_command_toggle(), id=self._id_speech_voice_command
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.voice_conversation_toggle(),
            id=self._id_speech_voice_conversation,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.voice_wakeword_toggle(),
            id=self._id_speech_wakeword,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.speak_voice_status(),
            id=self._id_speech_voice_status,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_dictation_microphone(),
            id=self._id_speech_microphone,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.set_huggingface_token(),
            id=self._id_speech_hf_token,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.generate_speech_audio(),
            id=self._id_speech_export_audio,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: run_translated_speech_export(self),
            id=self._id_speech_export_translated,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: run_batch_export_to_speech(self),
            id=self._id_speech_batch_export,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: run_pronunciation_manager(self),
            id=self._id_speech_pronunciations,
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
            lambda _e: self.open_ai_expand_selection(),
            id=self._id_ai_expand_selection,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_toc(),
            id=self._id_ai_generate_toc,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_ai_thesaurus(), id=self._id_ai_thesaurus)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_ai_improve_reading_order(),
            id=self._id_ai_reading_order,
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
        for _position in range(1, 11):
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, position=_position: self.go_to_document(position),
                id=self._id_go_to_document[_position - 1],
            )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.close_other_documents(),
            id=self._id_close_other_documents,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.insert_link(), id=self._id_insert_link)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.insert_equation(), id=self._id_insert_equation)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.insert_citation(), id=self._id_insert_citation)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_snippet_gallery(), id=self._id_snippet_gallery
        )
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
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.toggle_fold(), id=self._id_toggle_fold)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.next_fold(), id=self._id_next_fold)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.previous_fold(), id=self._id_previous_fold)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.list_folds(), id=self._id_list_folds)
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
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.toggle_tab_insert_mode(), id=self._id_toggle_tab_mode
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.move_line_up(), id=self._id_move_line_up)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.move_line_down(), id=self._id_move_line_down)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.move_section_up(), id=self._id_move_section_up)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.move_section_down(), id=self._id_move_section_down
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.duplicate_line(), id=self._id_duplicate_line)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.delete_line(), id=self._id_delete_line)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.join_lines(), id=self._id_join_lines)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.quote_lines(), id=self._id_quote_lines)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.unquote_lines(), id=self._id_unquote_lines)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.switch_document_format(),
            id=self._id_switch_document_format,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_bold(), id=self._id_format_bold)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_italic(), id=self._id_format_italic)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.format_underline(), id=self._id_format_underline
        )
        self.bind_format_codes(wx)
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
        # EdSharp port: toggle variants bound to Ctrl+Alt+7/8.
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_bullet_list(),
            id=self._id_toggle_bullet_list,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_numbered_list(),
            id=self._id_toggle_numbered_list,
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
            lambda _e: self.open_list_studio(),
            id=self._id_open_list_studio,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_list_studio_settings(),
            id=self._id_list_studio_settings,
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
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_blockquote(),
            id=self._id_insert_blockquote,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.format_horizontal_rule(),
            id=self._id_insert_horizontal_rule,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.insert_emoji(),
            id=self._id_insert_emoji,
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
            lambda _e: self.open_sticky_notes_browser(),
            id=self._id_sticky_browser,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_global_hotkeys_manager(),
            id=self._id_global_hotkeys,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.create_sticky_note(),
            id=self._id_new_sticky_note,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_quill_eraser(),
            id=self._id_quill_eraser,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_quill_eraser_selection(),
            id=self._id_quill_eraser_selection,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.show_word_count(), id=self._id_word_count)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_spell_check_dialog(),
            id=self._id_spell_check,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.spell_check_ranked(),
            id=self._id_spell_check_ranked,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.spell_check_word_at_cursor(),
            id=self._id_spell_check_word,
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
            lambda _e: self.open_misspelling_list_ranked(),
            id=self._id_misspelling_list_ranked,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.choose_spell_language(),
            id=self._id_spell_language,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.add_inline_note(), id=self._id_add_inline_note)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.next_inline_note(), id=self._id_next_inline_note
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.previous_inline_note(), id=self._id_previous_inline_note
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.speak_inline_note(), id=self._id_speak_inline_note
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
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.change_display_language(),
            id=self._id_display_language,
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.ocr_image_file(), id=self._id_ocr_image)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_table_studio(), id=self._id_table_studio)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_csv_studio(), id=self._id_csv_studio)
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
        # Experimental in-browser reading. Bound unconditionally (the menu item
        # only appears when opted in, and the handler self-guards on the
        # setting), so an accidental invocation degrades gracefully.
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.read_document_in_browser(),
            id=self._id_read_aloud_edge,
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
            lambda _e: self.convert_file(),
            id=self._id_convert_file,
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
            lambda _e: self.show_whats_new(),
            id=self._id_whats_new,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_glow_updates(),
            id=self._id_check_glow_updates,
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
            lambda _e: self.reset_all_to_factory_defaults(),
            id=self._id_reset_all_defaults,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.post_to_mastodon(),
            id=self._id_post_mastodon,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.manage_mastodon_accounts(),
            id=self._id_mastodon_accounts,
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
            lambda _e: self.open_startup_logs(),
            id=self._id_view_startup_logs,
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
            lambda _e: self.toggle_reveal_codes(),
            id=self._id_reveal_codes,
        )
        # Idle tick keeps the Reveal Codes pane synced with the editor caret/text
        # without binding every per-tab editor; it early-returns when the pane is hidden.
        self.frame.Bind(wx.EVT_IDLE, self._reveal_on_idle)
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
        self.frame.Bind(wx.EVT_MENU, self._on_window_doc_menu)
        self.frame.Bind(wx.EVT_MENU, self._on_menu_command_activity)
