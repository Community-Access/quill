"""Menu-bar construction for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``MenuBuilderMixin`` and ``_build_menu`` resolves identically through the MRO.
The method is fully self-contained: it reads ``wx`` from ``self._wx`` and
reaches every menu id, submenu, label helper, and refresh routine through
``self``, so no module-level imports are required here.
"""

from __future__ import annotations

import sys

from quill.core.app_launcher import is_app_released, is_dev_build
from quill.core.i18n import _


def _tray_slot_accel(n: int) -> str:
    """Menu-mnemonic form of a copy-tray slot number.

    ``&1``-``&9`` for the first nine, ``1&0`` for slot ten, plain ``11``/``12``
    beyond that -- ``&10`` would collide with slot 1 on the "1" mnemonic.
    """
    if n <= 9:
        return f"&{n}"
    if n == 10:
        return "1&0"
    return str(n)


class MenuBuilderMixin:
    def _prune_menu_separators(self, menu: object) -> None:
        """Remove dangling separators from a built menu (#15).

        A separator the screen reader announces but cannot focus appears when a
        menu opens or ends with one, or has two in a row -- usually because an
        optional section above/below was feature-gated out, leaving a section
        divider with nothing on one side. Strip leading and trailing separators
        and collapse consecutive runs to one. Safe to call on any menu."""
        positions_to_remove: list[int] = []
        count = menu.GetMenuItemCount()
        prev_was_separator = True  # leading separators have nothing before them
        for position in range(count):
            item = menu.FindItemByPosition(position)
            is_separator = item is not None and item.IsSeparator()
            if is_separator and prev_was_separator:
                positions_to_remove.append(position)
            else:
                prev_was_separator = is_separator
        # A trailing separator (last kept item is a separator) is also dangling.
        for position in range(count - 1, -1, -1):
            if position in positions_to_remove:
                continue
            item = menu.FindItemByPosition(position)
            if item is not None and item.IsSeparator():
                positions_to_remove.append(position)
            break
        for position in sorted(set(positions_to_remove), reverse=True):
            item = menu.FindItemByPosition(position)
            if item is not None:
                menu.DestroyItem(item)

    def _build_menu(self) -> None:
        wx = self._wx
        menu_bar = wx.MenuBar()

        self._id_new = wx.ID_NEW
        self._id_open = wx.ID_OPEN
        self._id_save = wx.ID_SAVE
        self._id_save_as = wx.ID_SAVEAS
        self._id_exit = wx.ID_EXIT
        self._id_palette = wx.NewIdRef()
        self._id_preferences = wx.ID_PREFERENCES
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
        self._id_github_items = wx.NewIdRef()
        self._id_ssh_quick_connect = wx.NewIdRef()
        self._id_ssh_site_manager = wx.NewIdRef()
        self._id_close_document = wx.NewIdRef()
        self._id_save_all = wx.NewIdRef()
        self._id_reload_from_disk = wx.NewIdRef()
        self._id_check_external_changes = wx.NewIdRef()
        self._id_restore_backup = wx.NewIdRef()
        self._id_restore_previous_version = wx.NewIdRef()
        self._id_save_session = wx.NewIdRef()
        self._id_open_session = wx.NewIdRef()
        self._id_clear_recent_sessions = wx.NewIdRef()
        self._id_page_setup = wx.NewIdRef()
        self._id_print = wx.NewIdRef()
        self._id_print_studio = wx.NewIdRef()
        self._id_header_footer = wx.NewIdRef()
        self._id_save_plain_text = wx.NewIdRef()
        self._id_clear_recent = wx.NewIdRef()
        # #262: Pandoc Import / Export menu ids (one per Tier-1 format).
        # Each id binds through the command registry in main_frame.py.
        self._id_import_markdown = wx.NewIdRef()
        self._id_import_html = wx.NewIdRef()
        self._id_import_docx = wx.NewIdRef()
        self._id_import_odt = wx.NewIdRef()
        self._id_import_rtf = wx.NewIdRef()
        self._id_import_epub = wx.NewIdRef()
        self._id_import_csv = wx.NewIdRef()
        self._id_import_latex = wx.NewIdRef()
        self._id_import_other = wx.NewIdRef()  # "Other Pandoc Format..."
        # Free-first Import / Convert Document tool (MarkItDown -> local OCR
        # -> consent-gated cloud OCR) and its OCR and Document Conversion
        # submenu (review, service settings, temp cleanup).
        self._id_import_convert = wx.NewIdRef()
        self._id_install_local_ocr = wx.NewIdRef()
        self._id_ocr_services = wx.NewIdRef()
        self._id_review_last_ocr = wx.NewIdRef()
        self._id_ocr_service_settings = wx.NewIdRef()
        self._id_delete_ocr_temp = wx.NewIdRef()
        self._id_export_markdown = wx.NewIdRef()
        self._id_export_html = wx.NewIdRef()
        self._id_export_docx = wx.NewIdRef()
        self._id_export_odt = wx.NewIdRef()
        self._id_export_rtf = wx.NewIdRef()
        self._id_export_epub = wx.NewIdRef()
        self._id_export_pdf = wx.NewIdRef()
        self._id_export_plain_text = wx.NewIdRef()
        self._id_export_daisy = wx.NewIdRef()  # DAISY 2.02 text-only talking book (#251)
        self._id_export_other = wx.NewIdRef()  # "Other Pandoc Format..."
        self._id_batch_convert_import = wx.NewIdRef()
        self._id_batch_convert_export = wx.NewIdRef()
        # File > Convert File... is appended to the File menu below (~line 362),
        # so its id must be created here, before that use, not in the later
        # tools-id block (regression from b28416b caused a launch-time
        # AttributeError building the File menu).
        self._id_convert_file = wx.NewIdRef()
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
        file_menu.Append(self._id_new, self._menu_label(_("&New"), "file.new"))
        file_menu.Append(self._id_open, self._menu_label(_("&Open..."), "file.open"))
        self._recent_menu = wx.Menu()
        file_menu.AppendSubMenu(self._recent_menu, _("Open &Recent"))
        self._refresh_recent_menu()
        self._id_open_from_favorite_folder = wx.NewIdRef()
        self._id_add_favorite_folder = wx.NewIdRef()
        self._id_remove_favorite_folder = wx.NewIdRef()
        favorites_menu = wx.Menu()
        favorites_menu.Append(
            self._id_open_from_favorite_folder,
            self._menu_label(_("&Open From Favorite Folder..."), "file.open_from_favorite_folder"),
        )
        favorites_menu.Append(
            self._id_add_favorite_folder,
            self._menu_label(_("&Add Current Folder to Favorites"), "file.add_favorite_folder"),
        )
        favorites_menu.Append(
            self._id_remove_favorite_folder,
            self._menu_label(_("&Remove Favorite Folder..."), "file.remove_favorite_folder"),
        )
        file_menu.AppendSubMenu(favorites_menu, _("Favorite &Folders"))
        file_menu.Append(self._id_open_url, _("Open from &URL..."))
        ssh_menu = wx.Menu()
        ssh_menu.Append(self._id_ssh_quick_connect, _("&Quick Connect..."))
        ssh_menu.Append(self._id_ssh_site_manager, _("&Site Manager..."))
        file_menu.AppendSubMenu(ssh_menu, _("Open over SS&H"))
        remote_menu = wx.Menu()
        remote_menu.Append(
            self._id_open_remote,
            self._menu_label(_("&Open from Remote..."), "file.open_from_remote"),
        )
        remote_menu.Append(
            self._id_save_to_remote,
            self._menu_label(_("&Save to Remote"), "file.save_to_remote"),
        )
        remote_menu.Append(
            self._id_save_copy_to_remote,
            self._menu_label(_("Save &Copy to Remote..."), "file.save_copy_to_remote"),
        )
        remote_menu.AppendSeparator()
        remote_menu.Append(
            self._id_github_repository,
            self._menu_label(_("&GitHub Repository..."), "file.open_github_repository"),
        )
        remote_menu.Append(
            self._id_github_file_url,
            self._menu_label(_("GitHub File &URL..."), "file.open_github_file_url"),
        )
        remote_menu.Append(
            self._id_github_save_back,
            self._menu_label(_("&Save to GitHub..."), "file.github_save_back"),
        )
        remote_menu.Append(
            self._id_github_items,
            self._menu_label(_("GitHub &Items..."), "file.open_github_items"),
        )
        remote_menu.AppendSeparator()
        remote_menu.Append(
            self._id_manage_remote_sites,
            self._menu_label(_("&Manage Remote Sites..."), "file.manage_remote_sites"),
        )
        remote_menu.Append(
            self._id_github_manage_accounts,
            self._menu_label(_("Manage &GitHub Accounts..."), "file.github_manage_accounts"),
        )
        file_menu.AppendSubMenu(remote_menu, _("Open from &Remote"))
        file_menu.AppendSubMenu(self._sessions_menu, _("&Snapshots"))
        self._id_publishing_connections = wx.NewIdRef()
        self._id_publishing_verify_connection = wx.NewIdRef()
        self._id_publishing_browse_content = wx.NewIdRef()
        self._id_publishing_create_draft = wx.NewIdRef()
        self._id_publishing_publish_current = wx.NewIdRef()
        self._id_publishing_create_page_draft = wx.NewIdRef()
        self._id_publishing_publish_current_page = wx.NewIdRef()
        self._id_publishing_compare_remote_item = wx.NewIdRef()
        self._id_publishing_update_remote_item = wx.NewIdRef()
        self._id_publishing_publish_remote_item = wx.NewIdRef()
        self._id_publishing_schedule_publish = wx.NewIdRef()
        # The Publish submenu is split into two independently gated halves:
        # future.publishing_read (not locked) for the read-only inbound tools,
        # and future.publishing (locked off) for the create/update/publish/
        # schedule send commands. IDs above stay unconditional (core.glow
        # precedent) so binding them below is harmless when the menu is unbuilt.
        publishing_read_enabled = self._feature_enabled("future.publishing_read")
        publishing_send_enabled = self._feature_enabled("future.publishing")
        if publishing_read_enabled or publishing_send_enabled:
            self._publishing_file_menu = wx.Menu()
        if publishing_read_enabled:
            self._publishing_file_menu.Append(
                self._id_publishing_connections,
                self._menu_label("Publishing &Connections...", "publishing.connections"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_verify_connection,
                self._menu_label(
                    "&Verify Current Publishing Connection",
                    "publishing.verify_connection",
                ),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_browse_content,
                self._menu_label("&Browse Publishing Content...", "publishing.browse_content"),
            )
        if publishing_send_enabled:
            self._publishing_file_menu.Append(
                self._id_publishing_create_draft,
                self._menu_label("Create Post &Draft...", "publishing.create_draft"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_publish_current,
                self._menu_label("&Publish Post Now...", "publishing.publish_current"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_create_page_draft,
                self._menu_label("Create Page Draft...", "publishing.create_page_draft"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_publish_current_page,
                self._menu_label("Publish Page Now...", "publishing.publish_current_page"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_compare_remote_item,
                self._menu_label("Compare With Remote...", "publishing.compare_remote_item"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_update_remote_item,
                self._menu_label("&Update Remote Content...", "publishing.update_remote_item"),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_publish_remote_item,
                self._menu_label(
                    "Publish Open Remote Content...",
                    "publishing.publish_remote_item",
                ),
            )
            self._publishing_file_menu.Append(
                self._id_publishing_schedule_publish,
                self._menu_label("&Schedule Publish...", "publishing.schedule_publish"),
            )
        if publishing_read_enabled or publishing_send_enabled:
            file_menu.AppendSeparator()
            file_menu.AppendSubMenu(self._publishing_file_menu, _("P&ublish"))
        # New document from clipboard sits beside New (Power Tools recirculation,
        # menus.md Phase 4).
        self._append_power_tools_file_create_items(file_menu)
        file_menu.AppendSeparator()
        # --- Save ---
        file_menu.Append(self._id_save, self._menu_label(_("&Save"), "file.save"))
        file_menu.Append(self._id_save_as, self._menu_label(_("Save &As..."), "file.save_as"))
        file_menu.Append(self._id_save_all, _("Save A&ll"))
        file_menu.Append(self._id_save_plain_text, _("Save As Plain &Text..."))
        file_menu.AppendSeparator()
        # --- Import / Export (issue #262) -----------------------------------
        import_menu = wx.Menu()
        # The free-first conversion tool leads the submenu: it routes any
        # supported document (including scanned PDFs and images) through the
        # local no-upload tiers, prompting before OCR ever runs.
        import_menu.Append(
            self._id_import_convert,
            self._menu_label(_("Import / Convert &Document (OCR)..."), "file.import_convert"),
        )
        import_menu.AppendSeparator()
        import_menu.Append(
            self._id_import_markdown,
            self._menu_label(_("&Markdown..."), "file.import_markdown"),
        )
        import_menu.Append(
            self._id_import_html,
            self._menu_label(_("&HTML..."), "file.import_html"),
        )
        import_menu.Append(
            self._id_import_docx,
            self._menu_label(_("&Word Document..."), "file.import_docx"),
        )
        import_menu.Append(
            self._id_import_odt,
            self._menu_label(_("&OpenDocument Text..."), "file.import_odt"),
        )
        import_menu.Append(
            self._id_import_rtf,
            self._menu_label(_("&Rich Text Format..."), "file.import_rtf"),
        )
        import_menu.Append(
            self._id_import_epub,
            self._menu_label(_("&EPUB Book..."), "file.import_epub"),
        )
        import_menu.Append(
            self._id_import_csv,
            self._menu_label(_("CSV / &TSV Table..."), "file.import_csv"),
        )
        import_menu.Append(
            self._id_import_latex,
            self._menu_label(_("&LaTeX / TeX..."), "file.import_latex"),
        )
        import_menu.AppendSeparator()
        import_menu.Append(
            self._id_batch_convert_import,
            self._menu_label(_("&Batch Conversion..."), "file.batch_conversion_import"),
        )
        import_menu.AppendSeparator()
        import_menu.Append(
            self._id_import_other,
            self._menu_label(_("Other Pandoc Format..."), "file.import_other_pandoc"),
        )
        file_menu.AppendSubMenu(import_menu, _("&Import"))

        export_menu = wx.Menu()
        export_menu.Append(
            self._id_export_markdown,
            self._menu_label(_("&Markdown..."), "file.export_markdown"),
        )
        export_menu.Append(
            self._id_export_html,
            self._menu_label(_("&HTML..."), "file.export_html"),
        )
        export_menu.Append(
            self._id_export_docx,
            self._menu_label(_("&Word Document..."), "file.export_docx"),
        )
        export_menu.Append(
            self._id_export_odt,
            self._menu_label(_("&OpenDocument Text..."), "file.export_odt"),
        )
        export_menu.Append(
            self._id_export_rtf,
            self._menu_label(_("&Rich Text Format..."), "file.export_rtf"),
        )
        export_menu.Append(
            self._id_export_epub,
            self._menu_label(_("&EPUB Book..."), "file.export_epub"),
        )
        export_menu.Append(
            self._id_export_pdf,
            self._menu_label(_("&PDF Document..."), "file.export_pdf"),
        )
        export_menu.Append(
            self._id_export_plain_text,
            self._menu_label(_("Plain &Text..."), "file.export_plain_text"),
        )
        export_menu.Append(
            self._id_export_daisy,
            self._menu_label(_("&DAISY Talking Book..."), "file.export_daisy"),
        )
        export_menu.AppendSeparator()
        export_menu.Append(
            self._id_batch_convert_export,
            self._menu_label(_("&Batch Conversion..."), "file.batch_conversion_export"),
        )
        export_menu.AppendSeparator()
        export_menu.Append(
            self._id_export_other,
            self._menu_label(_("Other Pandoc Format..."), "file.export_other_pandoc"),
        )
        file_menu.AppendSubMenu(export_menu, _("&Export"))

        file_menu.Append(
            self._id_convert_file,
            self._menu_label(_("Con&vert File..."), "file.convert_file"),
        )

        file_menu.AppendSeparator()
        # --- Restore / reload ---
        file_menu.Append(self._id_reload_from_disk, _("&Reload from Disk"))
        file_menu.Append(self._id_check_external_changes, _("Check for E&xternal Changes..."))
        file_menu.Append(self._id_restore_backup, _("Restore &Backup..."))
        file_menu.Append(
            self._id_restore_previous_version,
            self._menu_label(_("Restore Previous &Version..."), "file.restore_previous_version"),
        )
        file_menu.AppendSeparator()
        # --- Current-file operations (Power Tools recirculation, menus.md Phase 4) ---
        self._append_power_tools_file_ops_items(file_menu)
        file_menu.AppendSeparator()
        # --- Notebook ---
        notebook_menu = wx.Menu()
        notebook_menu.Append(
            self._id_new_notebook,
            self._menu_label(_("&New Notebook..."), "file.new_notebook"),
        )
        notebook_menu.Append(
            self._id_new_notebook_from_folder,
            self._menu_label(_("New from &Folder..."), "file.new_notebook_from_folder"),
        )
        notebook_menu.Append(
            self._id_open_notebook,
            self._menu_label(_("&Open Notebook..."), "file.open_notebook"),
        )
        notebook_menu.AppendSeparator()
        notebook_menu.Append(
            self._id_notebook_save_snapshot,
            self._menu_label(_("&Save Version..."), "file.save_snapshot"),
        )
        notebook_menu.Append(
            self._id_notebook_restore_snapshot,
            self._menu_label(_("Restore &Version..."), "file.manage_snapshots"),
        )
        notebook_menu.Append(
            self._id_manage_notebook_snapshots,
            self._menu_label(_("&Manage Versions..."), "file.manage_snapshots"),
        )
        file_menu.AppendSubMenu(notebook_menu, _("&Notebook"))
        file_menu.AppendSeparator()
        # --- Print ---
        file_menu.Append(self._id_page_setup, _("Pa&ge Setup..."))
        file_menu.Append(self._id_print, self._menu_label(_("&Print..."), "file.print"))
        file_menu.Append(
            self._id_print_studio,
            self._menu_label(_("Print &Studio..."), "file.print_studio"),
        )
        file_menu.Append(
            self._id_header_footer,
            self._menu_label(_("&Header and Footer..."), "file.header_footer"),
        )
        file_menu.AppendSeparator()
        # --- Close ---
        file_menu.Append(
            self._id_close_document,
            self._menu_label(_("&Close Document"), "file.close_document"),
        )
        file_menu.Append(self._id_exit, self._menu_label(_("E&xit"), "app.exit"))

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
        self._id_insert_equation = wx.NewIdRef()
        self._id_insert_citation = wx.NewIdRef()
        self._id_snippet_gallery = wx.NewIdRef()
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
        edit_menu.Append(self._id_undo, self._menu_label(_("&Undo"), "edit.undo"))
        edit_menu.Append(self._id_redo, self._menu_label(_("&Redo"), "edit.redo"))
        edit_menu.AppendSeparator()
        # Standard clipboard items. wxTextCtrl routes these IDs natively, so
        # we don't need to bind handlers; the active editor handles them.
        edit_menu.Append(wx.ID_CUT, _("Cu&t\tCtrl+X"))
        edit_menu.Append(wx.ID_COPY, _("&Copy\tCtrl+C"))
        edit_menu.Append(wx.ID_PASTE, _("&Paste\tCtrl+V"))
        # Paste variants and New Document from Clipboard (power tools)
        self._append_power_tools_edit_items(edit_menu)
        # Copy Tray submenu — per-slot items use explicit IDs for direct bindings;
        # open/clear dialog commands are recirculated from the manifest via the
        # helper (menus.md Phase 4 pattern).
        tray_menu = wx.Menu()
        # Slot accelerators: &1-&9 for the first nine, 1&0 for slot ten (the
        # standard recent-files convention), plain numbers for 11-12 -- "&10"
        # would collide with slot 1 on the "1" mnemonic.
        for _n in range(1, 13):
            tray_menu.Append(
                self._id_copy_tray_slots[_n - 1],
                self._menu_label(
                    _("Copy to Slot {n}").format(n=_tray_slot_accel(_n)),
                    f"edit.copy_to_tray_{_n}",
                ),
            )
        tray_menu.AppendSeparator()
        for _n in range(1, 13):
            tray_menu.Append(
                self._id_paste_tray_slots[_n - 1],
                self._menu_label(
                    _("Paste from Slot {n}").format(n=_tray_slot_accel(_n)),
                    f"edit.paste_from_tray_{_n}",
                ),
            )
        tray_menu.AppendSeparator()
        tray_menu.Append(
            self._id_copy_to_next_slot,
            self._menu_label(_("Copy to &Next Empty Slot"), "edit.copy_to_next_slot"),
        )
        tray_menu.Append(
            self._id_search_tray_slots,
            self._menu_label(_("&Search Tray Slots..."), "edit.search_tray_slots"),
        )
        tray_menu.AppendSeparator()
        self._append_power_tools_copy_tray_items(tray_menu)
        edit_menu.AppendSubMenu(tray_menu, _("Copy &Tray"))
        edit_menu.Append(
            self._id_copy_with_source,
            self._menu_label(_("Copy With &Attribution"), "edit.copy_with_source"),
        )
        edit_menu.AppendSeparator()
        edit_menu.Append(wx.ID_SELECTALL, _("Select &All\tCtrl+A"))
        edit_menu.AppendSeparator()
        # Find / Replace and the find-navigation commands live in Edit (their
        # conventional home and their edit.* command ids); the Search menu is
        # reserved for cross-file search (menus.md Phase 3).
        edit_menu.Append(self._id_find, self._menu_label(_("Fin&d..."), "edit.find"))
        edit_menu.Append(
            self._id_replace,
            self._menu_label(_("Rep&lace..."), "edit.replace"),
        )
        edit_menu.Append(
            self._id_find_next,
            self._menu_label(_("Find &Next"), "edit.find_next"),
        )
        edit_menu.Append(
            self._id_find_previous,
            self._menu_label(_("Find Pre&vious"), "edit.find_previous"),
        )
        edit_menu.Append(
            self._id_find_all_matches,
            self._menu_label(_("Find All &Matches"), "edit.find_all_matches"),
        )
        edit_menu.AppendSeparator()
        edit_menu.Append(
            self._id_word_prediction,
            self._menu_label(_("&Word Prediction..."), "edit.word_prediction"),
        )
        edit_menu.AppendSeparator()
        selection_menu = wx.Menu()
        selection_menu.AppendCheckItem(
            self._id_toggle_extend_selection_mode,
            self._menu_label(
                _("E&xtend Selection Mode"),
                "edit.toggle_extend_selection_mode",
            ),
        )
        selection_menu.Check(self._id_toggle_extend_selection_mode, self._extend_selection_mode)
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_start_selection,
            self._menu_label(_("&Start Selection"), "edit.start_selection"),
        )
        selection_menu.Append(
            self._id_complete_selection,
            self._menu_label(_("&Complete Selection"), "edit.complete_selection"),
        )
        selection_menu.Append(
            self._id_reselect,
            self._menu_label(_("&Reselect"), "edit.reselect"),
        )
        selection_menu.Append(
            self._id_go_to_start_of_selection,
            self._menu_label(_("&Go to Start of Selection"), "edit.go_to_start_of_selection"),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_select_line,
            self._menu_label(_("Select &Line"), "edit.select_line"),
        )
        selection_menu.Append(
            self._id_select_paragraph,
            self._menu_label(_("Select &Paragraph"), "edit.select_paragraph"),
        )
        selection_menu.Append(
            self._id_select_block,
            self._menu_label(_("Select &Block"), "edit.select_block"),
        )
        selection_menu.Append(
            self._id_expand_selection,
            self._menu_label(_("E&xpand Selection"), "edit.expand_selection"),
        )
        selection_menu.Append(
            self._id_shrink_selection,
            self._menu_label(_("S&hrink Selection"), "edit.shrink_selection"),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_select_to_end_of_line,
            self._menu_label(_("Select to End of &Line"), "edit.select_to_end_of_line"),
        )
        selection_menu.Append(
            self._id_select_to_start_of_line,
            self._menu_label(
                _("Select to Start of Li&ne"),
                "edit.select_to_start_of_line",
            ),
        )
        selection_menu.Append(
            self._id_select_to_end_of_document,
            self._menu_label(
                _("Select to End of &Document"),
                "edit.select_to_end_of_document",
            ),
        )
        selection_menu.Append(
            self._id_select_to_start_of_document,
            self._menu_label(
                _("Select to Start of D&ocument"),
                "edit.select_to_start_of_document",
            ),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_set_mark,
            self._menu_label(_("&Set Temporary Mark"), "edit.set_mark"),
        )
        selection_menu.Append(
            self._id_pop_mark,
            self._menu_label(_("&Jump to Previous Mark"), "edit.pop_mark"),
        )
        selection_menu.Append(
            self._id_exchange_point_mark,
            self._menu_label(
                _("&Swap Cursor and Mark"),
                "edit.exchange_point_mark",
            ),
        )
        selection_menu.Append(
            self._id_list_marks,
            self._menu_label(_("&List Recent Marks"), "edit.list_marks"),
        )
        selection_menu.AppendSeparator()
        selection_menu.Append(
            self._id_set_named_mark,
            self._menu_label(_("&Set Named Mark..."), "edit.set_named_mark"),
        )
        selection_menu.Append(
            self._id_jump_to_named_mark,
            self._menu_label(_("&Jump to Named Mark..."), "edit.jump_to_named_mark"),
        )
        selection_menu.Append(
            self._id_open_review_buffer,
            self._menu_label(_("&Review Buffer"), "edit.open_review_buffer"),
        )
        edit_menu.AppendSubMenu(selection_menu, _("&Selection"))
        insert_menu = wx.Menu()

        search_menu = wx.Menu()
        # Cross-file search is a regex-level feature; basic profiles only have
        # in-document Find/Replace (Edit menu). Show Search in Files and Replace
        # Across Files only when core.search.regex is enabled.
        if self._feature_enabled("core.search.regex"):
            search_menu.Append(
                self._id_search_in_files,
                self._menu_label(_("Search in &Files..."), "tools.search_in_files"),
            )
            search_menu.Append(
                self._id_replace_in_files,
                self._menu_label(_("&Replace Across Files..."), "tools.replace_in_files"),
            )
        # Regular Expression match count/extract and block set-ops make Search the single
        # find / filter / extract-lines hub (Power Tools recirculation, menus.md
        # Phase 4).
        self._append_power_tools_search_items(search_menu)
        self._append_quillin_menu_items(search_menu, "Search")
        # #15: the power-tools group's first item declares a separator_before, so
        # when the regex Find/Replace items above are feature-gated off (basic
        # profiles) the menu opens with a leading separator the screen reader
        # reads but can't arrow to. Prune leading/trailing/doubled separators.
        self._prune_menu_separators(search_menu)
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
            self._menu_label(_("Toggle Soft &Wrap"), "view.toggle_soft_wrap"),
        )
        view_menu.Check(self._id_toggle_soft_wrap, self.settings.soft_wrap)
        view_menu.AppendCheckItem(self._id_toggle_tab_control, _("Show &Tab Control"))
        view_menu.Check(self._id_toggle_tab_control, self.settings.show_tab_control)
        view_menu.AppendSeparator()
        view_menu.Append(
            self._id_preview,
            self._menu_label(_("&Preview..."), "view.preview"),
        )
        view_menu.Append(
            self._id_split_preview,
            self._menu_label(_("Preview &Side by Side"), "view.split_preview"),
        )
        view_menu.Append(
            self._id_focus_preview,
            self._menu_label(_("&Focus Preview"), "view.focus_preview"),
        )
        view_menu.Append(
            self._id_browser_preview,
            self._menu_label(_("&Browser Preview..."), "view.browser_preview"),
        )
        view_menu.AppendCheckItem(
            self._id_toggle_auto_side_preview, _("&Auto Side-by-Side Preview")
        )
        view_menu.Check(self._id_toggle_auto_side_preview, self.settings.auto_side_preview)
        view_menu.AppendSeparator()
        view_menu.AppendCheckItem(
            self._id_toggle_entries_panel,
            self._menu_label(_("Show &Entries Panel"), "view.toggle_entries_panel"),
        )
        self._id_reveal_codes = wx.NewIdRef()
        view_menu.AppendCheckItem(
            self._id_reveal_codes,
            self._menu_label(_("Reveal &Codes"), "view.reveal_codes_toggle"),
        )
        view_menu.Check(
            self._id_reveal_codes, bool(getattr(self.settings, "reveal_codes_visible", False))
        )
        navigate_menu = wx.Menu()
        self._id_go_to_line = wx.NewIdRef()
        self._id_set_bookmark = wx.NewIdRef()
        self._id_go_to_bookmark = wx.NewIdRef()
        self._id_list_bookmarks = wx.NewIdRef()
        self._id_set_temp_bookmark = wx.NewIdRef()
        self._id_go_to_temp_bookmark = wx.NewIdRef()
        self._id_go_to_page = wx.NewIdRef()
        self._id_back_location = wx.NewIdRef()
        self._id_forward_location = wx.NewIdRef()
        self._id_next_heading = wx.NewIdRef()
        self._id_previous_heading = wx.NewIdRef()
        self._id_next_block = wx.NewIdRef()
        self._id_previous_block = wx.NewIdRef()
        self._id_outline_navigator = wx.NewIdRef()
        self._id_toggle_fold = wx.NewIdRef()
        self._id_next_fold = wx.NewIdRef()
        self._id_previous_fold = wx.NewIdRef()
        self._id_list_folds = wx.NewIdRef()
        self._id_heading_organizer = wx.NewIdRef()
        self._id_match_bracket = wx.NewIdRef()
        self._id_next_token = wx.NewIdRef()
        self._id_previous_token = wx.NewIdRef()
        self._id_set_language = wx.NewIdRef()
        self._id_speak_window_title = wx.NewIdRef()
        self._id_speak_full_path = wx.NewIdRef()
        self._id_speak_status_summary = wx.NewIdRef()
        self._id_compare_toggle_whitespace = wx.NewIdRef()
        self._id_compare_generate_report = wx.NewIdRef()
        self._id_next_structure = wx.NewIdRef()
        self._id_previous_structure = wx.NewIdRef()
        self._id_next_region = wx.NewIdRef()
        self._id_previous_region = wx.NewIdRef()
        navigate_menu.Append(
            self._id_back_location,
            self._menu_label(_("&Back Location"), "navigate.back_location"),
        )
        navigate_menu.Append(
            self._id_forward_location,
            self._menu_label(_("&Forward Location"), "navigate.forward_location"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_go_to_line,
            self._menu_label(_("&Go To Line..."), "navigate.go_to_line"),
        )
        navigate_menu.Append(
            self._id_go_to_page,
            self._menu_label(_("Go To &Page..."), "navigate.go_to_page"),
        )
        # Go to Percent, First/Last Non-Blank, Open Target at Cursor (power tools navigate group)
        self._append_power_tools_navigate_items(navigate_menu)
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_next_heading,
            self._menu_label(_("Next &Heading"), "navigate.next_heading"),
        )
        navigate_menu.Append(
            self._id_previous_heading,
            self._menu_label(_("Pre&vious Heading"), "navigate.previous_heading"),
        )
        navigate_menu.Append(
            self._id_next_block,
            self._menu_label(_("Next &Block"), "navigate.next_block"),
        )
        navigate_menu.Append(
            self._id_previous_block,
            self._menu_label(_("Previous Bl&ock"), "navigate.previous_block"),
        )
        navigate_menu.Append(
            self._id_next_structure,
            self._menu_label(_("Next Str&ucture"), "navigate.next_structure"),
        )
        navigate_menu.Append(
            self._id_previous_structure,
            self._menu_label(_("Previous Structu&re"), "navigate.previous_structure"),
        )
        navigate_menu.Append(
            self._id_next_region,
            self._menu_label(_("Next Re&gion"), "navigate.next_region"),
        )
        navigate_menu.Append(
            self._id_previous_region,
            self._menu_label(_("Previous Regio&n"), "navigate.previous_region"),
        )
        navigate_menu.Append(
            self._id_match_bracket,
            self._menu_label(_("Match &Bracket"), "navigate.match_bracket"),
        )
        navigate_menu.Append(
            self._id_next_token,
            self._menu_label(_("Next &Token"), "navigate.next_token"),
        )
        navigate_menu.Append(
            self._id_previous_token,
            self._menu_label(_("P&revious Token"), "navigate.previous_token"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_set_language,
            self._menu_label(_("Set Document &Language..."), "navigate.set_language"),
        )
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_speak_window_title,
            self._menu_label(_("Speak &Window Title"), "navigate.speak_window_title"),
        )
        navigate_menu.Append(
            self._id_speak_full_path,
            self._menu_label(_("Speak &Full Path"), "navigate.speak_full_path"),
        )
        navigate_menu.Append(
            self._id_speak_status_summary,
            self._menu_label(_("Speak &Status Summary"), "navigate.speak_status_summary"),
        )
        navigate_menu.AppendSeparator()
        # Compare lives only under Tools > Comparison (the canonical, complete
        # submenu); the old Navigate > Compare duplicate is gone.
        navigate_menu.Append(
            self._id_outline_navigator,
            self._menu_label(_("Outline &Navigator..."), "navigate.outline_navigator"),
        )
        navigate_menu.Append(
            self._id_heading_organizer,
            self._menu_label(_("&Heading Organizer..."), "navigate.heading_organizer"),
        )
        navigate_menu.AppendSeparator()
        folding_menu = wx.Menu()
        folding_menu.Append(
            self._id_toggle_fold,
            self._menu_label(_("Toggle &Fold"), "edit.toggle_fold"),
        )
        folding_menu.Append(
            self._id_next_fold,
            self._menu_label(_("Ne&xt Fold"), "navigate.next_fold"),
        )
        folding_menu.Append(
            self._id_previous_fold,
            self._menu_label(_("Pre&vious Fold"), "navigate.previous_fold"),
        )
        folding_menu.Append(
            self._id_list_folds,
            self._menu_label(_("&List Folds..."), "tools.list_folds"),
        )
        navigate_menu.AppendSubMenu(folding_menu, _("Fol&ding"))
        # Sticky Notes are position-anchored annotations, so they live with the
        # navigation surfaces rather than under Tools.
        self._id_sticky_notes = wx.NewIdRef()
        self._id_new_sticky_note = wx.NewIdRef()
        sticky_menu = wx.Menu()
        sticky_menu.Append(
            self._id_sticky_notes,
            self._menu_label(_("&Sticky Notes..."), "tools.sticky_notes"),
        )
        sticky_menu.Append(
            self._id_new_sticky_note,
            self._menu_label(_("&New Sticky Note..."), "tools.sticky_note_capture"),
        )
        self._id_sticky_browser = wx.NewIdRef()
        sticky_menu.Append(
            self._id_sticky_browser,
            self._menu_label(_("Sticky Notes &Browser..."), "notes.sticky_browser"),
        )
        navigate_menu.AppendSubMenu(sticky_menu, _("Stick&y Notes"))
        navigate_menu.AppendSeparator()
        navigate_menu.Append(
            self._id_follow_link,
            self._menu_label(_("&Follow Link"), "edit.follow_link"),
        )
        navigate_menu.AppendSeparator()
        bookmarks_menu = wx.Menu()
        bookmarks_menu.Append(
            self._id_set_bookmark,
            self._menu_label(_("&Set Bookmark..."), "navigate.set_bookmark"),
        )
        bookmarks_menu.Append(
            self._id_go_to_bookmark,
            self._menu_label(_("&Go To Bookmark..."), "navigate.go_to_bookmark"),
        )
        bookmarks_menu.Append(
            self._id_list_bookmarks,
            self._menu_label(_("&List Bookmarks..."), "navigate.list_bookmarks"),
        )
        bookmarks_menu.AppendSeparator()
        bookmarks_menu.Append(
            self._id_set_temp_bookmark,
            self._menu_label(_("Set &Temporary Bookmark"), "navigate.set_temp_bookmark"),
        )
        bookmarks_menu.Append(
            self._id_go_to_temp_bookmark,
            self._menu_label(_("Go to Temporar&y Bookmark"), "navigate.go_to_temp_bookmark"),
        )
        navigate_menu.AppendSubMenu(bookmarks_menu, _("Book&marks"))
        navigate_menu.AppendSeparator()
        notebook_nav_menu = wx.Menu()
        notebook_nav_menu.Append(
            self._id_go_to_entry_in_notebook,
            self._menu_label(_("Go to &Entry..."), "navigate.go_to_entry_in_notebook"),
        )
        notebook_nav_menu.Append(
            self._id_go_to_heading_in_notebook,
            self._menu_label(_("Go to &Heading..."), "navigate.go_to_heading_in_notebook"),
        )
        notebook_nav_menu.Append(
            self._id_go_to_bookmark_in_notebook,
            self._menu_label(_("Go to &Bookmark..."), "navigate.go_to_bookmark_in_notebook"),
        )
        notebook_nav_menu.Append(
            self._id_go_to_sticky_note_in_notebook,
            self._menu_label(_("Go to Sticky &Note..."), "navigate.go_to_sticky_note_in_notebook"),
        )
        navigate_menu.AppendSubMenu(notebook_nav_menu, _("Noteboo&k"))
        self._id_insert_html_tag = wx.NewIdRef()
        self._id_insert_markdown_tag = wx.NewIdRef()
        self._id_insert_snippet = wx.NewIdRef()
        self._id_manage_snippets = wx.NewIdRef()
        self._id_expand_abbreviation = wx.NewIdRef()
        self._id_manage_abbreviations = wx.NewIdRef()
        self._id_toggle_abbreviation_expansion = wx.NewIdRef()
        self._id_format_bold = wx.NewIdRef()
        self._id_format_italic = wx.NewIdRef()
        self._id_format_underline = wx.NewIdRef()
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
        self._id_toggle_tab_mode = wx.NewIdRef()
        self._id_move_line_up = wx.NewIdRef()
        self._id_move_line_down = wx.NewIdRef()
        # PR1 (EdSharp port): section-move ids, distinct from move-line.
        self._id_move_section_up = wx.NewIdRef()
        self._id_move_section_down = wx.NewIdRef()
        self._id_duplicate_line = wx.NewIdRef()
        self._id_delete_line = wx.NewIdRef()
        self._id_join_lines = wx.NewIdRef()
        self._id_quote_lines = wx.NewIdRef()
        self._id_unquote_lines = wx.NewIdRef()
        self._id_insert_bullet_list = wx.NewIdRef()
        self._id_insert_numbered_list = wx.NewIdRef()
        # EdSharp port: toggle variants that strip or insert based on caret context.
        self._id_toggle_bullet_list = wx.NewIdRef()
        self._id_toggle_numbered_list = wx.NewIdRef()
        self._id_insert_task_list = wx.NewIdRef()
        self._id_open_list_manager = wx.NewIdRef()
        self._id_open_list_studio = wx.NewIdRef()
        self._id_list_studio_settings = wx.NewIdRef()
        self._id_insert_code_block = wx.NewIdRef()
        self._id_insert_footnote = wx.NewIdRef()
        self._id_insert_table = wx.NewIdRef()
        self._id_insert_blockquote = wx.NewIdRef()
        self._id_insert_horizontal_rule = wx.NewIdRef()
        self._id_insert_emoji = wx.NewIdRef()
        format_menu = wx.Menu()

        # --- Document Format (One Editor, Every Format) ---
        # The switcher leads the menu: it decides what every command below
        # *means* (rich mode applies real formatting; markup modes insert
        # tags). Also reachable from the palette, the Ctrl+Shift+Grave, K
        # chord, and the status bar Format cell — one handler behind all four.
        self._id_switch_document_format = wx.NewIdRef()
        format_menu.Append(
            self._id_switch_document_format,
            self._menu_label(_("&Document Format..."), "format.switch_document_format"),
        )
        format_menu.AppendSeparator()

        # --- Character formatting (most common) ---
        format_menu.Append(self._id_format_bold, self._menu_label(_("&Bold"), "format.bold"))
        format_menu.Append(self._id_format_italic, self._menu_label(_("&Italic"), "format.italic"))
        format_menu.Append(
            self._id_format_underline,
            self._menu_label(_("&Underline"), "format.underline"),
        )

        # Hidden-codes run/paragraph formatting (font, size, align, color,
        # highlight) plus the describe-formatting interrogation item. Built by
        # FormatCodesMixin so the bulk stays out of this monolith (GATE-11).
        self.build_format_codes_submenus(format_menu, wx)
        format_menu.AppendSeparator()

        # --- Structural formatting ---
        format_menu.Append(
            self._id_indent,
            self._menu_label(_("&Indent"), "format.indent"),
        )
        format_menu.Append(
            self._id_outdent,
            self._menu_label(_("O&utdent"), "format.outdent"),
        )
        format_menu.AppendCheckItem(
            self._id_toggle_tab_mode,
            self._menu_label(_("Tab Key Inserts Tab &Character"), "format.toggle_tab_insert_mode"),
        )
        format_menu.Check(self._id_toggle_tab_mode, getattr(self, "_tab_inserts_literal", False))
        format_menu.AppendSeparator()

        # --- Case ---
        case_menu = wx.Menu()
        case_menu.Append(
            self._id_upper_case,
            self._menu_label(_("&Upper Case"), "format.upper_case"),
        )
        case_menu.Append(
            self._id_lower_case,
            self._menu_label(_("&Lower Case"), "format.lower_case"),
        )
        case_menu.Append(
            self._id_title_case,
            self._menu_label(_("&Title Case"), "format.title_case"),
        )
        case_menu.Append(
            self._id_sentence_case,
            self._menu_label(_("&Sentence Case"), "format.sentence_case"),
        )
        case_menu.Append(
            self._id_toggle_case,
            self._menu_label(_("To&ggle Case"), "format.toggle_case"),
        )
        format_menu.AppendSubMenu(case_menu, _("Change &Case"))

        # --- Comments ---
        format_menu.Append(
            self._id_toggle_line_comment,
            self._menu_label(
                _("Toggle Line &Comment"),
                "format.toggle_line_comment",
            ),
        )
        format_menu.Append(
            self._id_toggle_block_comment,
            self._menu_label(
                _("Toggle &Block Comment"),
                "format.toggle_block_comment",
            ),
        )
        format_menu.AppendSeparator()

        # --- Line submenu ---
        line_menu = wx.Menu()
        line_menu.Append(
            self._id_move_line_up,
            self._menu_label(_("Move Line &Up"), "format.move_line_up"),
        )
        line_menu.Append(
            self._id_move_line_down,
            self._menu_label(_("Move Line &Down"), "format.move_line_down"),
        )
        line_menu.Append(
            self._id_move_section_up,
            self._menu_label(_("Move Secti&on Up"), "format.move_section_up"),
        )
        line_menu.Append(
            self._id_move_section_down,
            self._menu_label(_("Move Section Do&wn"), "format.move_section_down"),
        )
        line_menu.AppendSeparator()
        line_menu.Append(
            self._id_duplicate_line,
            self._menu_label(_("D&uplicate Line"), "format.duplicate_line"),
        )
        line_menu.Append(
            self._id_delete_line,
            self._menu_label(_("De&lete Line"), "format.delete_line"),
        )
        line_menu.AppendSeparator()
        line_menu.Append(
            self._id_join_lines,
            self._menu_label(_("&Join Lines"), "format.join_lines"),
        )
        # Number Lines, Hard-Wrap Lines and delete operations (power tools format_line group)
        self._append_power_tools_format_line_items(line_menu)
        line_menu.AppendSeparator()
        line_menu.Append(
            self._id_quote_lines, self._menu_label(_("&Quote Lines"), "edit.quote_lines")
        )
        line_menu.Append(
            self._id_unquote_lines, self._menu_label(_("&Unquote Lines"), "edit.unquote_lines")
        )
        format_menu.AppendSubMenu(line_menu, _("&Line"))

        # --- Sort & Filter submenu ---
        sort_menu = wx.Menu()
        sort_menu.Append(
            self._id_sort_lines_ascending,
            self._menu_label(_("Sort Lines &A to Z"), "edit.sort_lines_ascending"),
        )
        sort_menu.Append(
            self._id_sort_lines_descending,
            self._menu_label(_("Sort Lines &Z to A"), "edit.sort_lines_descending"),
        )
        # Numeric, by length, shuffle, keep unique, delete-containing (power tools)
        self._append_power_tools_sort_filter_items(sort_menu)
        sort_menu.AppendSeparator()
        sort_menu.Append(
            self._id_reverse_lines,
            self._menu_label(_("&Reverse Lines"), "edit.reverse_lines"),
        )
        sort_menu.AppendSeparator()
        sort_menu.Append(
            self._id_remove_duplicate_lines,
            self._menu_label(_("Remove &Duplicate Lines"), "edit.remove_duplicate_lines"),
        )
        format_menu.AppendSubMenu(sort_menu, _("Sort and &Filter"))

        # --- Whitespace submenu ---
        ws_menu = wx.Menu()
        ws_menu.Append(
            self._id_trim_trailing_whitespace,
            self._menu_label(_("Trim Trailing &Whitespace"), "edit.trim_trailing_whitespace"),
        )
        # Trim Blank Lines (power tools trim_blank group)
        self._append_power_tools_trim_blank_items(ws_menu)
        ws_menu.Append(
            self._id_normalize_whitespace,
            self._menu_label(_("&Normalize Whitespace"), "edit.normalize_whitespace"),
        )
        ws_menu.AppendSeparator()
        ws_menu.Append(
            self._id_convert_indentation_to_spaces,
            self._menu_label(
                _("Convert Indentation to &Spaces"),
                "edit.convert_indentation_to_spaces",
            ),
        )
        ws_menu.Append(
            self._id_convert_indentation_to_tabs,
            self._menu_label(
                _("Convert Indentation to &Tabs"),
                "edit.convert_indentation_to_tabs",
            ),
        )
        format_menu.AppendSubMenu(ws_menu, _("&Whitespace"))

        # --- HTML & Encoding submenu ---
        html_menu = wx.Menu()
        self._append_power_tools_html_encoding_items(html_menu)
        format_menu.AppendSubMenu(html_menu, _("&HTML and Encoding"))

        # --- Markdown submenu (#257: profiles, table of contents, line breaks) ---
        markdown_menu = wx.Menu()
        self._append_power_tools_markdown_profiles_items(markdown_menu)
        format_menu.AppendSubMenu(markdown_menu, _("&Markdown"))

        # --- Document Language submenu (#181): pin the editing language so a
        # plain .txt can be written as HTML/Markdown/code and get those
        # characteristics. Radio items show and switch the active profile;
        # "Auto-detect" clears the override. The dialog (Ctrl+Shift+L, also in
        # Navigate) remains for type-ahead selection.
        from quill.core.language_profile import all_profiles as _all_lang_profiles

        language_menu = wx.Menu()
        self._language_menu_item_ids: dict[int, str] = {}
        auto_item = language_menu.AppendRadioItem(wx.ID_ANY, _("&Auto-detect from file"))
        self._language_menu_item_ids[auto_item.GetId()] = ""
        for _profile in _all_lang_profiles():
            radio = language_menu.AppendRadioItem(wx.ID_ANY, _profile.name)
            self._language_menu_item_ids[radio.GetId()] = _profile.name
        plain_item = language_menu.AppendRadioItem(wx.ID_ANY, _("Plain text"))
        self._language_menu_item_ids[plain_item.GetId()] = "Plain text"
        for _lang_id in self._language_menu_item_ids:
            self.frame.Bind(wx.EVT_MENU, self._on_document_language_menu, id=_lang_id)
        format_menu.AppendSubMenu(language_menu, _("Document &Language"))

        # Quillin-contributed Format items
        self._append_quillin_menu_items(format_menu, "Format")

        heading_menu = wx.Menu()
        heading_menu.Append(
            self._id_heading_1, self._menu_label(_("Heading &1"), "format.heading_1")
        )
        heading_menu.Append(
            self._id_heading_2, self._menu_label(_("Heading &2"), "format.heading_2")
        )
        heading_menu.Append(
            self._id_heading_3, self._menu_label(_("Heading &3"), "format.heading_3")
        )
        heading_menu.Append(
            self._id_heading_4, self._menu_label(_("Heading &4"), "format.heading_4")
        )
        heading_menu.Append(
            self._id_heading_5, self._menu_label(_("Heading &5"), "format.heading_5")
        )
        heading_menu.Append(
            self._id_heading_6, self._menu_label(_("Heading &6"), "format.heading_6")
        )
        heading_menu.AppendSeparator()
        heading_menu.Append(
            self._id_decrease_heading_level,
            self._menu_label(
                _("Decrease Level"),
                "format.decrease_heading_level",
            ),
        )
        heading_menu.Append(
            self._id_increase_heading_level,
            self._menu_label(
                _("Increase Level"),
                "format.increase_heading_level",
            ),
        )
        heading_menu.AppendSeparator()
        heading_menu.Append(
            self._id_style_headings,
            self._menu_label(_("&Style Headings..."), "format.style_headings"),
        )
        insert_menu.Append(
            self._id_insert_link,
            self._menu_label(_("Insert &Link..."), "edit.insert_link"),
        )
        insert_menu.Append(
            self._id_insert_equation,
            self._menu_label(_("Insert &Equation..."), "edit.insert_equation"),
        )
        insert_menu.Append(
            self._id_insert_citation,
            self._menu_label(_("Insert &Citation..."), "edit.insert_citation"),
        )
        insert_menu.Append(
            self._id_snippet_gallery,
            self._menu_label(_("Snippet &Gallery..."), "power.open_snippet_gallery"),
        )
        insert_menu.AppendSeparator()
        insert_menu.AppendSubMenu(heading_menu, _("&Heading"))
        list_menu = wx.Menu()
        list_menu.Append(
            self._id_insert_bullet_list,
            self._menu_label(_("B&ullet"), "format.insert_bullet_list"),
        )
        list_menu.Append(
            self._id_insert_numbered_list,
            self._menu_label(_("&Numbered"), "format.insert_numbered_list"),
        )
        # EdSharp port: toggle variants — strip the list if the caret is
        # already inside one, otherwise insert.  Bound to Ctrl+Alt+7/8.
        list_menu.Append(
            self._id_toggle_bullet_list,
            self._menu_label(_("Toggle &Bullet"), "format.toggle_bullet_list"),
        )
        list_menu.Append(
            self._id_toggle_numbered_list,
            self._menu_label(_("Toggle &Numbered"), "format.toggle_numbered_list"),
        )
        list_menu.Append(
            self._id_insert_task_list,
            self._menu_label(_("&Task"), "format.insert_task_list"),
        )
        list_menu.AppendSeparator()
        list_menu.Append(
            self._id_open_list_manager,
            self._menu_label(_("List &Manager..."), "format.list_manager"),
        )
        list_menu.Append(
            self._id_open_list_studio,
            self._menu_label(_("Structured List &Studio..."), "format.list_studio"),
        )
        list_menu.Append(
            self._id_list_studio_settings,
            self._menu_label(_("List Studio Se&ttings..."), "format.list_studio_settings"),
        )
        insert_menu.AppendSubMenu(list_menu, _("&List"))
        insert_menu.Append(
            self._id_insert_code_block,
            self._menu_label(_("Insert Code &Block"), "format.insert_code_block"),
        )
        insert_menu.Append(
            self._id_insert_footnote,
            self._menu_label(_("Insert &Footnote"), "format.insert_footnote"),
        )
        insert_menu.Append(
            self._id_insert_table,
            self._menu_label(_("Insert &Table..."), "format.insert_table"),
        )
        insert_menu.Append(
            self._id_insert_blockquote,
            self._menu_label(_("Insert Block &Quote"), "format.blockquote"),
        )
        insert_menu.Append(
            self._id_insert_horizontal_rule,
            self._menu_label(_("Insert Horizontal &Rule"), "format.horizontal_rule"),
        )
        insert_menu.AppendSeparator()
        insert_menu.Append(
            self._id_insert_html_tag,
            self._menu_label(_("Insert &HTML Tag..."), "format.insert_html_tag"),
        )
        insert_menu.Append(
            self._id_insert_markdown_tag,
            self._menu_label(_("Insert &Markdown Tag..."), "format.insert_markdown_tag"),
        )
        insert_menu.Append(
            self._id_insert_snippet,
            self._menu_label(_("Insert S&nippet..."), "format.insert_snippet"),
        )
        insert_menu.Append(
            self._id_manage_snippets,
            self._menu_label(_("Manage Snippets..."), "format.manage_snippets"),
        )
        if self._feature_enabled("core.abbreviations"):
            insert_menu.AppendSeparator()
            insert_menu.Append(
                self._id_expand_abbreviation,
                self._menu_label(_("E&xpand Abbreviation"), "format.expand_abbreviation"),
            )
            insert_menu.Append(
                self._id_manage_abbreviations,
                self._menu_label(_("Manage Abbrevi&ations..."), "format.manage_abbreviations"),
            )
            insert_menu.Append(
                self._id_toggle_abbreviation_expansion,
                self._menu_label(
                    _("&Toggle Abbreviation Expansion"), "format.toggle_abbreviation_expansion"
                ),
            )
        # Power Tools recirculation (menus.md Phase 4). The power-tool date/time
        # entries were removed: the bundled ``com.quill.bundled.insert-tools``
        # Quillin is now the single home for Insert Date / Insert Time / Insert
        # Date and Time, surfaced through the new "Date and Time" submenu below.
        self._append_power_tools_insert_items(insert_menu)
        # Quillin contributions whose ``parent`` is one of the conventional
        # top-level menus. The new ``Date and Time`` submenu is built explicitly
        # below and routes Quillin contributions whose parent matches its name.
        self._append_quillin_menu_items(insert_menu, "Insert")
        date_time_menu = wx.Menu()
        # No separator-before: this is the first item of a new submenu.
        self._append_quillin_menu_items(date_time_menu, "Date and Time", prepend_separator=False)
        # Always show the submenu, even when no Quillin contributes a date/time
        # item (the bundled ``insert-tools`` Quillin is enabled by default and
        # ships the three snippets, but a user can disable it). The disabled
        # case is the only one that surfaces an empty submenu, and a stock
        # ``wx.Menu`` with a single visible item is still a navigable
        # submenu, not a bug.
        insert_menu.AppendSubMenu(date_time_menu, _("Date and &Time"))
        insert_menu.Append(
            self._id_insert_emoji,
            self._menu_label(_("Insert &Emoji..."), "edit.insert_emoji"),
        )
        self._id_new_tab = wx.NewIdRef()  # #1246: Ctrl+T new document tab
        self._id_next_document = wx.NewIdRef()
        self._id_previous_document = wx.NewIdRef()
        # Accelerator-only ids for Go to Document 1..10 (Alt+1..Alt+9, Alt+0).
        # They carry the Alt+digit accelerators in the table; no menu items.
        self._id_go_to_document = [wx.NewIdRef() for _ in range(10)]
        self._id_close_other_documents = wx.NewIdRef()
        window_menu = wx.Menu()
        window_menu.Append(
            self._id_new_tab,
            self._menu_label(_("New &Tab"), "window.new_document_tab"),
        )
        window_menu.Append(
            self._id_next_document,
            self._menu_label(_("&Next Document"), "window.next_document"),
        )
        window_menu.Append(
            self._id_previous_document,
            self._menu_label(_("&Previous Document"), "window.previous_document"),
        )
        window_menu.Append(
            self._id_close_other_documents,
            self._menu_label(
                _("Close &Other Documents\tCtrl+Shift+F4"), "window.close_other_documents"
            ),
        )
        window_menu.AppendSeparator()
        window_menu.Append(
            self._id_send_to_tray,
            self._menu_label(_("Send to S&ystem Tray"), "view.send_to_tray"),
        )
        window_menu.AppendSeparator()
        self._window_menu = window_menu  # doc items appended here dynamically

        self._id_word_count = wx.NewIdRef()
        self._id_quill_eraser = wx.NewIdRef()
        self._id_quill_eraser_selection = wx.NewIdRef()
        self._id_spell_check = wx.NewIdRef()
        self._id_spell_check_ranked = wx.NewIdRef()
        self._id_spell_check_word = wx.NewIdRef()
        self._id_previous_misspelling = wx.NewIdRef()
        self._id_next_misspelling = wx.NewIdRef()
        self._id_misspelling_list = wx.NewIdRef()
        self._id_misspelling_list_ranked = wx.NewIdRef()
        self._id_dictionary_status = wx.NewIdRef()
        self._id_ocr_image = wx.NewIdRef()
        self._id_table_studio = wx.NewIdRef()
        self._id_csv_studio = wx.NewIdRef()
        self._id_ocr_clipboard = wx.NewIdRef()
        self._id_ocr_screen = wx.NewIdRef()
        self._id_describe_image = wx.NewIdRef()
        self._id_regex_helper = wx.NewIdRef()
        self._id_external_tools = wx.NewIdRef()
        self._id_read_aloud = wx.NewIdRef()
        self._id_read_aloud_stop = wx.NewIdRef()
        self._id_read_aloud_voice = wx.NewIdRef()
        self._id_read_aloud_settings = wx.NewIdRef()
        self._id_read_aloud_generate_audio = wx.NewIdRef()
        self._id_read_aloud_edge = wx.NewIdRef()
        self._id_announcement_backend = wx.NewIdRef()
        self._id_announcement_backend_auto = wx.NewIdRef()
        self._id_announcement_backend_prism = wx.NewIdRef()
        self._id_announcement_backend_status_only = wx.NewIdRef()
        self._id_toggle_announcement_trace = wx.NewIdRef()
        self._id_toggle_sound = wx.NewIdRef()
        self._id_sound_events = wx.NewIdRef()
        self._id_dictation = wx.NewIdRef()
        self._id_bw_model_manager = wx.NewIdRef()
        self._id_bw_model_status = wx.NewIdRef()
        self._id_bw_model_recommend = wx.NewIdRef()
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
        self._id_whats_new = wx.NewIdRef()
        self._id_check_glow_updates = wx.NewIdRef()
        self._id_status_bar_settings = wx.NewIdRef()
        self._id_share_export = wx.NewIdRef()
        self._id_share_import = wx.NewIdRef()
        self._id_post_mastodon = wx.NewIdRef()
        self._id_mastodon_accounts = wx.NewIdRef()
        self._id_keymap_editor = wx.NewIdRef()
        self._id_export_keymap = wx.NewIdRef()
        self._id_import_keymap = wx.NewIdRef()
        self._id_reset_keymap = wx.NewIdRef()
        self._id_reset_all_defaults = wx.NewIdRef()
        self._id_profiles_and_features = wx.NewIdRef()
        self._id_glow_audit_document = wx.NewIdRef()
        self._id_glow_audit_selection = wx.NewIdRef()
        self._id_glow_fix_document = wx.NewIdRef()
        self._id_glow_fix_selection = wx.NewIdRef()
        self._id_ai_hub = wx.NewIdRef()
        self._id_ai_assistant = wx.NewIdRef()
        self._id_ai_prompt_studio = wx.NewIdRef()
        self._id_ai_agent_center = wx.NewIdRef()
        self._id_ai_accessibility_agent = wx.NewIdRef()
        self._id_ask_quill_chat = wx.NewIdRef()
        self._id_ask_quill_voice = wx.NewIdRef()
        self._id_ai_library = wx.NewIdRef()
        self._id_prompt_library = wx.NewIdRef()
        self._id_skill_library = wx.NewIdRef()
        self._id_check_grammar_ai = wx.NewIdRef()
        self._id_ai_enabled = wx.NewIdRef()
        self._id_ai_status_badge = wx.NewIdRef()
        self._id_ai_status_detail = wx.NewIdRef()
        self._id_ai_model = wx.NewIdRef()
        self._id_ai_switch_engine = wx.NewIdRef()
        self._id_ai_copilot_setup = wx.NewIdRef()
        self._id_ai_validate_agents = wx.NewIdRef()
        self._id_ai_session_browser = wx.NewIdRef()
        self._id_speech_models = wx.NewIdRef()
        self._id_speech_voices = wx.NewIdRef()
        self._id_speech_transcribe = wx.NewIdRef()
        self._id_speech_captions = wx.NewIdRef()
        self._id_speech_dictate = wx.NewIdRef()
        self._id_speech_voice_command = wx.NewIdRef()
        self._id_speech_voice_conversation = wx.NewIdRef()
        self._id_speech_wakeword = wx.NewIdRef()
        self._id_speech_voice_status = wx.NewIdRef()
        self._id_speech_microphone = wx.NewIdRef()
        # Locked Dictation menu items (the commands are the remappable Ctrl+F9 family).
        self._id_dictation_lock = wx.NewIdRef()
        self._id_dictation_pause = wx.NewIdRef()
        self._id_dictation_status = wx.NewIdRef()
        self._id_dictation_stop = wx.NewIdRef()
        self._id_dictation_cancel = wx.NewIdRef()
        self._id_dictation_settings = wx.NewIdRef()
        self._id_dictation_history = wx.NewIdRef()
        self._id_speech_hf_token = wx.NewIdRef()
        self._id_speech_export_audio = wx.NewIdRef()
        self._id_speech_export_translated = wx.NewIdRef()
        self._id_speech_batch_export = wx.NewIdRef()
        self._id_speech_pronunciations = wx.NewIdRef()
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
        self._id_ai_spell_check = wx.NewIdRef()
        self._id_ai_spell_check_interactive = wx.NewIdRef()
        self._id_ai_grammar_style = wx.NewIdRef()
        self._id_ai_translate_selection = wx.NewIdRef()
        self._id_ai_translate_document = wx.NewIdRef()
        self._id_ai_transcribe_audio = wx.NewIdRef()
        self._id_ai_tts_read_selection = wx.NewIdRef()
        self._id_ai_tts_read_document = wx.NewIdRef()
        self._id_ai_tts_stop = wx.NewIdRef()
        self._id_ai_tts_export_mp3 = wx.NewIdRef()
        self._id_ai_expand_selection = wx.NewIdRef()
        self._id_ai_generate_toc = wx.NewIdRef()
        self._id_ai_thesaurus = wx.NewIdRef()
        self._id_ai_reading_order = wx.NewIdRef()
        self._id_ai_document_qa = wx.NewIdRef()
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
        self._id_enable_braille_mode = wx.NewIdRef()
        self._id_save_diagnostics = wx.NewIdRef()
        self._id_report_bug = wx.NewIdRef()
        self._id_open_logs_folder = wx.NewIdRef()
        self._id_open_diagnostics_folder = wx.NewIdRef()
        self._id_help_on_control = wx.NewIdRef()
        self._id_context_help = wx.NewIdRef()
        self._id_announce_context_shortcuts = wx.NewIdRef()
        self._id_show_spoken_echo = wx.NewIdRef()
        self._id_help_status_page = wx.NewIdRef()
        self._id_why_dont_i_see_feature = wx.NewIdRef()
        self._id_switch_feature_profile = wx.NewIdRef()
        self._id_feature_profile_health_check = wx.NewIdRef()
        self._id_individual_feature_toggles = wx.NewIdRef()
        self._id_undo_profile_change = wx.NewIdRef()
        self._id_reset_feature_profile = wx.NewIdRef()
        self._id_profile_onboarding = wx.NewIdRef()
        self._id_yaml_structure_editor = wx.NewIdRef()
        self._id_dev_console_python = wx.NewIdRef()
        self._id_dev_console_ts = wx.NewIdRef()
        self._id_dev_copy_diagnostic = wx.NewIdRef()
        self._id_dev_restart_ts_worker = wx.NewIdRef()
        self._id_open_story_studio = wx.NewIdRef()
        self._id_work_personas = wx.NewIdRef()
        self._id_calculator = wx.NewIdRef()
        self._id_vault_open = wx.NewIdRef()
        self._id_vault_follow_link = wx.NewIdRef()
        self._id_vault_backlinks = wx.NewIdRef()
        self._id_vault_explorer = wx.NewIdRef()
        self._id_vault_neighborhood = wx.NewIdRef()
        self._id_vault_unlinked = wx.NewIdRef()
        self._id_vault_insert_link = wx.NewIdRef()
        self._id_vault_complete = wx.NewIdRef()
        self._id_vault_rename = wx.NewIdRef()
        self._id_vault_quick_switch = wx.NewIdRef()
        self._id_vault_search = wx.NewIdRef()
        self._id_vault_tags = wx.NewIdRef()
        self._id_vault_speak_embed = wx.NewIdRef()
        self._id_vault_resolve_embed = wx.NewIdRef()
        self._id_vault_insert_template = wx.NewIdRef()
        self._id_vault_today = wx.NewIdRef()
        self._id_vault_prev_daily = wx.NewIdRef()
        self._id_vault_next_daily = wx.NewIdRef()
        self._id_vault_export_site = wx.NewIdRef()
        self._id_vault_sync = wx.NewIdRef()
        self._id_vault_settings = wx.NewIdRef()
        self._id_git_sync_folder = wx.NewIdRef()
        self._id_github_create_repo = wx.NewIdRef()
        self._id_github_fork_repo = wx.NewIdRef()
        self._id_github_rename_repo = wx.NewIdRef()
        self._id_github_change_visibility = wx.NewIdRef()
        self._id_github_change_default_branch = wx.NewIdRef()
        self._id_github_branch_protection = wx.NewIdRef()
        self._id_github_delete_branch = wx.NewIdRef()
        self._id_github_commit_multiple = wx.NewIdRef()
        self._id_github_browse_org = wx.NewIdRef()
        self._id_github_create_release = wx.NewIdRef()
        self._id_github_dispatch_workflow = wx.NewIdRef()
        self._id_github_notifications = wx.NewIdRef()
        self._id_github_security_alerts = wx.NewIdRef()
        self._id_github_list_codespaces = wx.NewIdRef()
        self._id_github_create_codespace = wx.NewIdRef()
        self._id_github_copilot_suggest = wx.NewIdRef()
        self._id_github_copilot_explain = wx.NewIdRef()
        self._id_localgit_uncommitted = wx.NewIdRef()
        self._id_localgit_switch_branch = wx.NewIdRef()
        self._id_localgit_stash_changes = wx.NewIdRef()
        self._id_localgit_manage_stashes = wx.NewIdRef()
        self._id_localgit_blame = wx.NewIdRef()
        self._id_localgit_bisect_start = wx.NewIdRef()
        self._id_localgit_bisect_reset = wx.NewIdRef()
        self._id_localgit_resolve_conflicts = wx.NewIdRef()
        self._id_localgit_interactive_rebase = wx.NewIdRef()
        self._id_localgit_rebase_abort = wx.NewIdRef()
        self._id_localgit_worktrees = wx.NewIdRef()
        self._id_localgit_new_worktree = wx.NewIdRef()
        tools_menu = wx.Menu()
        tools_menu.Append(
            self._id_palette,
            self._menu_label(_("&Command Palette..."), "app.command_palette"),
        )
        tools_menu.Append(
            self._id_open_story_studio,
            self._menu_label(_("Story &Studio..."), "story.open_studio"),
        )
        tools_menu.Append(
            self._id_work_personas,
            self._menu_label(_("Work &Personas..."), "tools.work_personas"),
        )
        tools_menu.Append(
            self._id_calculator,
            self._menu_label(_("Ca&lculator..."), "tools.calculator"),
        )
        # (The cross-app launchers live in the top-level QuillVille menu, built
        # near the end of the menu bar -- see the QuillVille append below.)
        vault_menu = wx.Menu()
        vault_menu.Append(self._id_vault_open, self._menu_label(_("&Open Vault..."), "vault.open"))
        vault_menu.Append(
            self._id_vault_explorer, self._menu_label(_("Vault E&xplorer..."), "vault.explorer")
        )
        vault_menu.Append(
            self._id_vault_follow_link,
            self._menu_label(_("&Follow Wikilink"), "vault.follow_link"),
        )
        vault_menu.Append(
            self._id_vault_backlinks, self._menu_label(_("Show &Backlinks"), "vault.backlinks")
        )
        vault_menu.Append(
            self._id_vault_neighborhood,
            self._menu_label(_("Note &Neighborhood"), "vault.neighborhood"),
        )
        vault_menu.Append(
            self._id_vault_unlinked,
            self._menu_label(_("&Unlinked Mentions"), "vault.unlinked_mentions"),
        )
        vault_menu.Append(
            self._id_vault_insert_link,
            self._menu_label(_("&Insert Link to Note..."), "vault.insert_link"),
        )
        vault_menu.Append(
            self._id_vault_complete,
            self._menu_label(_("&Complete Link or Tag..."), "vault.complete"),
        )
        vault_menu.Append(
            self._id_vault_rename, self._menu_label(_("&Rename Note..."), "vault.rename")
        )
        vault_menu.Append(
            self._id_vault_quick_switch, self._menu_label(_("&Go to Note..."), "vault.quick_switch")
        )
        vault_menu.Append(
            self._id_vault_search, self._menu_label(_("&Search Vault..."), "vault.search")
        )
        vault_menu.Append(self._id_vault_tags, self._menu_label(_("Show &Tags..."), "vault.tags"))
        vault_menu.AppendSeparator()
        vault_menu.Append(
            self._id_vault_speak_embed,
            self._menu_label(_("Spea&k Embed at Cursor"), "vault.speak_embed"),
        )
        vault_menu.Append(
            self._id_vault_resolve_embed,
            self._menu_label(_("&Resolve Embed Inline"), "vault.resolve_embed"),
        )
        vault_menu.Append(
            self._id_vault_insert_template,
            self._menu_label(_("Insert &Template..."), "vault.insert_template"),
        )
        vault_menu.Append(
            self._id_vault_today, self._menu_label(_("Open Toda&y's Note"), "vault.today")
        )
        vault_menu.Append(
            self._id_vault_prev_daily,
            self._menu_label(_("&Previous Daily Note"), "vault.prev_daily"),
        )
        vault_menu.Append(
            self._id_vault_next_daily, self._menu_label(_("&Next Daily Note"), "vault.next_daily")
        )
        vault_menu.AppendSeparator()
        vault_menu.Append(
            self._id_vault_export_site,
            self._menu_label(_("&Export Vault as Website..."), "vault.export_site"),
        )
        vault_menu.Append(self._id_vault_sync, self._menu_label(_("S&ync Vault"), "vault.sync"))
        vault_menu.Append(
            self._id_vault_settings, self._menu_label(_("Vault Se&ttings..."), "vault.settings")
        )
        tools_menu.AppendSubMenu(vault_menu, _("&Vault"))
        github_admin_menu = wx.Menu()
        # Open/browse a repository -- the everyday "I just want to open a repo"
        # action, alongside the admin operations. Reuses the same command (and its
        # existing binding) as File > Open Remote > GitHub Repository.
        github_admin_menu.Append(
            self._id_github_repository,
            self._menu_label(_("&Open a Repository..."), "file.open_github_repository"),
        )
        github_admin_menu.Append(
            self._id_git_sync_folder,
            self._menu_label(_("S&ync Folder with GitHub..."), "sync.sync_folder"),
        )
        github_admin_menu.AppendSeparator()
        github_admin_menu.Append(
            self._id_github_create_repo,
            self._menu_label(_("&Create Repository..."), "github.create_repository"),
        )
        github_admin_menu.Append(
            self._id_github_fork_repo,
            self._menu_label(_("&Fork Repository..."), "github.fork_repository"),
        )
        github_admin_menu.Append(
            self._id_github_rename_repo,
            self._menu_label(_("&Rename Repository..."), "github.rename_repository"),
        )
        github_admin_menu.Append(
            self._id_github_change_visibility,
            self._menu_label(_("Change &Visibility..."), "github.change_repository_visibility"),
        )
        github_admin_menu.Append(
            self._id_github_change_default_branch,
            self._menu_label(_("Change &Default Branch..."), "github.change_default_branch"),
        )
        github_admin_menu.Append(
            self._id_github_branch_protection,
            self._menu_label(
                _("Configure Branch &Protection..."), "github.configure_branch_protection"
            ),
        )
        github_admin_menu.Append(
            self._id_github_delete_branch,
            self._menu_label(_("&Delete Branch..."), "github.delete_branch"),
        )
        github_admin_menu.Append(
            self._id_github_commit_multiple,
            self._menu_label(_("Commit &Multiple Files..."), "github.commit_multiple_files"),
        )
        github_admin_menu.AppendSeparator()
        github_admin_menu.Append(
            self._id_github_browse_org,
            self._menu_label(
                _("Browse &Organization Repositories..."), "github.browse_organization"
            ),
        )
        github_admin_menu.Append(
            self._id_github_create_release,
            self._menu_label(_("Create &Release..."), "github.create_release"),
        )
        github_admin_menu.Append(
            self._id_github_dispatch_workflow,
            self._menu_label(_("Dispatch &Workflow..."), "github.dispatch_workflow"),
        )
        github_admin_menu.Append(
            self._id_github_notifications,
            self._menu_label(_("&Notifications..."), "github.view_notifications"),
        )
        github_admin_menu.Append(
            self._id_github_security_alerts,
            self._menu_label(_("&Security Alerts..."), "github.view_security_alerts"),
        )
        github_admin_menu.AppendSeparator()
        github_admin_menu.Append(
            self._id_github_list_codespaces,
            self._menu_label(_("Code&spaces..."), "github.list_codespaces"),
        )
        github_admin_menu.Append(
            self._id_github_create_codespace,
            self._menu_label(_("Create Codespace..."), "github.create_codespace"),
        )
        github_admin_menu.Append(
            self._id_github_copilot_suggest,
            self._menu_label(_("Ask Copilot for a Command..."), "github.copilot_suggest"),
        )
        github_admin_menu.Append(
            self._id_github_copilot_explain,
            self._menu_label(_("Explain a Command..."), "github.copilot_explain"),
        )
        git_family_menu = wx.Menu()
        git_family_menu.AppendSubMenu(github_admin_menu, _("Git&Hub"))
        local_git_menu = wx.Menu()
        local_git_menu.Append(
            self._id_localgit_uncommitted,
            self._menu_label(_("&Uncommitted Changes..."), "localgit.uncommitted_changes"),
        )
        local_git_menu.Append(
            self._id_localgit_switch_branch,
            self._menu_label(_("Switch &Branch..."), "localgit.switch_branch"),
        )
        local_git_menu.AppendSeparator()
        local_git_menu.Append(
            self._id_localgit_stash_changes,
            self._menu_label(_("&Stash Changes..."), "localgit.stash_changes"),
        )
        local_git_menu.Append(
            self._id_localgit_manage_stashes,
            self._menu_label(_("Manage St&ashes..."), "localgit.manage_stashes"),
        )
        local_git_menu.AppendSeparator()
        local_git_menu.Append(
            self._id_localgit_blame,
            self._menu_label(_("&Who Wrote This Line..."), "localgit.blame_at_cursor"),
        )
        local_git_menu.AppendSeparator()
        local_git_menu.Append(
            self._id_localgit_bisect_start,
            self._menu_label(_("Start &Bisect..."), "localgit.bisect_start"),
        )
        local_git_menu.Append(
            self._id_localgit_bisect_reset,
            self._menu_label(_("&End Bisect"), "localgit.bisect_reset"),
        )
        local_git_menu.AppendSeparator()
        local_git_menu.Append(
            self._id_localgit_resolve_conflicts,
            self._menu_label(_("&Resolve Conflicts..."), "localgit.resolve_conflicts"),
        )
        local_git_menu.Append(
            self._id_localgit_interactive_rebase,
            self._menu_label(_("&Interactive Rebase..."), "localgit.interactive_rebase"),
        )
        local_git_menu.Append(
            self._id_localgit_rebase_abort,
            self._menu_label(_("A&bort Rebase"), "localgit.rebase_abort"),
        )
        local_git_menu.AppendSeparator()
        local_git_menu.Append(
            self._id_localgit_worktrees,
            self._menu_label(_("Wor&ktrees..."), "localgit.worktrees"),
        )
        local_git_menu.Append(
            self._id_localgit_new_worktree,
            self._menu_label(_("&New Worktree..."), "localgit.new_worktree"),
        )
        git_family_menu.AppendSubMenu(local_git_menu, _("&Local Git"))
        tools_menu.AppendSubMenu(git_family_menu, _("&Git and GitHub"))
        tools_menu.AppendSeparator()

        # Writing & Language -----------------------------------------------
        writing_menu = wx.Menu()
        writing_menu.Append(
            self._id_word_count,
            self._menu_label(_("&Word Count..."), "tools.word_count"),
        )
        writing_menu.Append(
            self._id_spell_check,
            self._menu_label(_("&Spell Check..."), "tools.spell_check_dialog"),
        )
        writing_menu.Append(
            self._id_spell_check_ranked,
            self._menu_label(
                _("Spell Check (&Ranked by Frequency)..."), "tools.spell_check_ranked"
            ),
        )
        writing_menu.Append(
            self._id_spell_check_word,
            self._menu_label(_("Spell Check &Word"), "tools.spell_check_word_at_cursor"),
        )
        writing_menu.Append(
            self._id_previous_misspelling,
            self._menu_label(_("Previous Mi&sspelling"), "tools.previous_misspelling"),
        )
        writing_menu.Append(
            self._id_next_misspelling,
            self._menu_label(_("Next &Misspelling"), "tools.next_misspelling"),
        )
        writing_menu.Append(
            self._id_misspelling_list,
            self._menu_label(_("&Misspelling List..."), "tools.misspelling_list"),
        )
        writing_menu.Append(
            self._id_misspelling_list_ranked,
            self._menu_label(
                _("Misspelling List (&Ranked by Frequency)..."), "tools.misspelling_list_ranked"
            ),
        )
        self._id_spell_language = wx.NewIdRef()
        writing_menu.Append(
            self._id_spell_language,
            self._menu_label(_("Spell Check &Language..."), "tools.spell_language"),
        )
        writing_menu.AppendSeparator()
        self._id_add_inline_note = wx.NewIdRef()
        self._id_next_inline_note = wx.NewIdRef()
        self._id_previous_inline_note = wx.NewIdRef()
        self._id_speak_inline_note = wx.NewIdRef()
        writing_menu.Append(
            self._id_add_inline_note,
            self._menu_label(_("Add &Inline Note..."), "notes.add_inline_note"),
        )
        writing_menu.Append(
            self._id_next_inline_note,
            self._menu_label(_("Next Inline &Note"), "notes.next_inline_note"),
        )
        writing_menu.Append(
            self._id_previous_inline_note,
            self._menu_label(_("Previous Inline No&te"), "notes.previous_inline_note"),
        )
        writing_menu.Append(
            self._id_speak_inline_note,
            self._menu_label(_("Speak Inline Note (double to &edit)"), "notes.speak_inline_note"),
        )
        writing_menu.AppendSeparator()
        self._id_thesaurus = wx.NewIdRef()
        writing_menu.Append(
            self._id_thesaurus,
            self._menu_label(_("&Thesaurus..."), "tools.thesaurus"),
        )
        writing_menu.Append(
            self._id_dictionary_status,
            self._menu_label(_("Dictionary &Status..."), "tools.dictionary_status"),
        )
        writing_menu.AppendSeparator()
        self._id_display_language = wx.NewIdRef()
        writing_menu.Append(
            self._id_display_language,
            self._menu_label(_("Change &Display Language..."), "app.display_language"),
        )
        # GLOW is an experimental opt-in: _feature_enabled("core.glow") is true
        # only when the profile flag AND the Experimental-tab gates (master
        # switch + GLOW checkbox) are on. The items appear on the settings-apply
        # menu rebuild — no restart.
        if self._feature_enabled("core.glow"):
            writing_menu.AppendSeparator()
            writing_menu.Append(
                self._id_glow_audit_document,
                self._menu_label(_("GLOW &Audit Document"), "tools.glow_audit_document"),
            )
            writing_menu.Append(
                self._id_glow_audit_selection,
                self._menu_label(_("GLOW Audit &Selection"), "tools.glow_audit_selection"),
            )
            writing_menu.AppendSeparator()
            writing_menu.Append(
                self._id_glow_fix_document,
                self._menu_label(_("GLOW &Fix Document"), "tools.glow_fix_document"),
            )
            writing_menu.Append(
                self._id_glow_fix_selection,
                self._menu_label(_("GLOW Fix &Selection"), "tools.glow_fix_selection"),
            )
        # Table Studio is an experimental opt-in (Preferences > Experimental):
        # one accessible grid for a new table or an opened CSV. Appears on
        # settings-apply.
        if self._experimental_gate_on("table_studio_experimental_enabled"):
            writing_menu.AppendSeparator()
            writing_menu.Append(
                self._id_table_studio,
                self._menu_label(_("&Table Studio..."), "tools.table_studio"),
            )
            writing_menu.Append(
                self._id_csv_studio,
                self._menu_label(_("Open CS&V in Table Studio..."), "tools.csv_studio"),
            )
        writing_menu.AppendSeparator()
        writing_menu.Append(
            self._id_quill_eraser,
            self._menu_label(_("&Quill Eraser..."), "tools.quill_eraser"),
        )
        writing_menu.Append(
            self._id_quill_eraser_selection,
            self._menu_label(_("Quill Eraser on &Selection..."), "tools.quill_eraser_selection"),
        )
        tools_menu.AppendSubMenu(writing_menu, _("&Writing and Language"))

        # Reading & Dictation (merges Read Aloud, Dictation, OCR) ------------
        read_aloud_menu = wx.Menu()
        read_aloud_menu.Append(
            self._id_read_aloud,
            self._menu_label(_("&Start / Pause"), "tools.read_aloud_start_pause"),
        )
        read_aloud_menu.Append(
            self._id_read_aloud_voice,
            self._menu_label(_("&Voice..."), "tools.read_aloud_voice"),
        )
        read_aloud_menu.Append(
            self._id_read_aloud_settings,
            self._menu_label(_("Se&ttings..."), "tools.read_aloud_settings"),
        )
        read_aloud_menu.Append(
            self._id_read_aloud_generate_audio,
            self._menu_label(_("Generate &Audio..."), "tools.read_aloud_generate_audio"),
        )
        # Experimental in-browser reading: shown only after the user opts in
        # under Preferences > Experimental (the command is likewise only
        # registered then). Opens an accessible reader page in the real browser,
        # where the full/online voices are available.
        if getattr(self.settings, "edge_read_aloud_enabled", False) and getattr(
            self.settings, "experimental_acknowledged", False
        ):
            read_aloud_menu.AppendSeparator()
            read_aloud_menu.Append(
                self._id_read_aloud_edge,
                self._menu_label(_("Read in &Browser (Experimental)"), "tools.read_aloud_edge"),
            )
        read_aloud_menu.Append(
            self._id_announcement_backend,
            self._menu_label(_("Announcement &Backend..."), "tools.announcement_backend"),
        )
        read_aloud_menu.Append(
            self._id_toggle_announcement_trace,
            _("Announcement &Trace (in Settings)..."),
        )
        reading_menu = wx.Menu()
        reading_menu.AppendSubMenu(read_aloud_menu, _("Read &Aloud"))
        reading_menu.Append(
            self._id_read_aloud_stop,
            self._menu_label(_("&Stop Reading"), "tools.read_aloud_stop"),
        )
        reading_menu.Append(
            self._id_say_selected,
            self._menu_label(_("&Say Selected"), "edit.say_selected"),
        )
        reading_menu.Append(
            self._id_read_all,
            self._menu_label(_("&Read All"), "edit.read_all"),
        )
        reading_menu.AppendSeparator()
        reading_menu.Append(
            self._id_toggle_sound,
            self._menu_label(_("Toggle &Sound Notifications"), "tools.sound_toggle"),
        )
        reading_menu.Append(
            self._id_sound_events,
            self._menu_label(_("&Manage Sound Events..."), "tools.sound_events"),
        )
        reading_menu.AppendSeparator()
        reading_menu.Append(
            self._id_ocr_image,
            self._menu_label(_("OCR &Image..."), "tools.ocr_image"),
        )
        reading_menu.Append(
            self._id_ocr_clipboard,
            self._menu_label(_("OCR &Clipboard Image"), "tools.ocr_clipboard"),
        )
        reading_menu.Append(
            self._id_ocr_screen,
            self._menu_label(_("OCR &Screen Capture..."), "tools.ocr_screen"),
        )
        reading_menu.Append(
            self._id_describe_image,
            self._menu_label(_("&Describe Image..."), "tools.describe_image"),
        )
        reading_menu.AppendSeparator()
        # The supported OCR / document-conversion tool (OCR PRD §4.2): one
        # submenu holding the whole workflow, from import to review to service
        # management, so it reads as a first-class QUILL tool.
        conversion_menu = wx.Menu()
        conversion_menu.Append(
            self._id_import_convert,
            self._menu_label(_("&Import / Convert Document..."), "file.import_convert"),
        )
        conversion_menu.Append(
            self._id_review_last_ocr,
            self._menu_label(_("&Review Last OCR Result..."), "tools.review_last_ocr"),
        )
        conversion_menu.AppendSeparator()
        conversion_menu.Append(
            self._id_install_local_ocr,
            self._menu_label(
                _("I&nstall Local OCR Engine (Tesseract)..."), "tools.install_local_ocr"
            ),
        )
        conversion_menu.Append(
            self._id_ocr_service_settings,
            self._menu_label(_("OCR Service &Settings..."), "tools.ocr_service_settings"),
        )
        conversion_menu.Append(
            self._id_ocr_services,
            self._menu_label(_("OCR and Conversion Ser&vices..."), "tools.ocr_services"),
        )
        conversion_menu.AppendSeparator()
        conversion_menu.Append(
            self._id_delete_ocr_temp,
            self._menu_label(_("&Delete OCR Temporary Files"), "tools.delete_ocr_temp"),
        )
        reading_menu.AppendSubMenu(conversion_menu, _("&OCR and Document Conversion"))
        tools_menu.AppendSubMenu(reading_menu, _("R&eading and Dictation"))
        # Tools > Speech: flat menu consolidating offline speech, Windows dictation,
        # and model management (#669). Previously split across Reading & Dictation >
        # Dictation (Windows) and Speech > Whisperer (offline). One menu is simpler.
        speech_menu = wx.Menu()
        # One unified entry opens the Speech hub (Read Aloud + Dictation tabs);
        # voices and dictation models are managed in the same dialog (#700).
        speech_menu.Append(
            self._id_speech_models,
            self._menu_label(_("&Speech and Dictation..."), "tools.speech_models"),
        )
        speech_menu.AppendSeparator()
        speech_menu.Append(
            self._id_speech_dictate,
            self._menu_label(_("&Dictate (Offline)"), "tools.speech_dictate"),
        )
        # Hey QUILL Phase 1: push-to-talk voice command over the offline speech
        # stack, bounded by the agent safe-tool allowlist. Off by default
        # (settings.voice_commands_enabled); always off in Safe Mode. Plan:
        # docs/planning/quill-hey-quill-voice-interaction-plan.md.
        speech_menu.Append(
            self._id_speech_voice_command,
            self._menu_label(_("&Voice Command (Offline)"), "tools.voice_command"),
        )
        # Hey QUILL Phase 2: the hands-free conversation loop (warm cues,
        # cancel window, follow-up) over the same on-device capture.
        speech_menu.Append(
            self._id_speech_voice_conversation,
            self._menu_label(_("Voice &Conversation Mode"), "tools.voice_conversation"),
        )
        # Hey QUILL Phase 3: always-listening for the "Hey QUILL" wake phrase.
        speech_menu.Append(
            self._id_speech_wakeword,
            self._menu_label(_("Listen for &Hey QUILL"), "tools.voice_wakeword"),
        )
        speech_menu.Append(
            self._id_speech_voice_status,
            self._menu_label(_("Speak Voice &Status"), "tools.voice_status"),
        )
        # Windows (SAPI) dictation is no longer supported -- offline Whisper
        # Locked Dictation (Ctrl+F9) replaces it -- so it is not exposed in the
        # menu. The command machinery stays for back-compat.
        speech_menu.Append(
            self._id_speech_microphone,
            self._menu_label(_("Dictation &Microphone..."), "tools.speech_microphone"),
        )
        # Locked Dictation control submenu (#10 discoverability). The keybinding
        # for each is shown so the keyboard-first workflow stays obvious.
        dictation_menu = wx.Menu()
        dictation_menu.Append(
            self._id_dictation_lock,
            self._menu_label(_("&Locked Dictation (start/finish)"), "tools.dictation_lock_toggle"),
        )
        dictation_menu.Append(
            self._id_dictation_pause,
            self._menu_label(_("&Pause or Resume"), "tools.dictation_pause"),
        )
        dictation_menu.Append(
            self._id_dictation_status,
            self._menu_label(_("Speak &Status"), "tools.dictation_status"),
        )
        dictation_menu.Append(
            self._id_dictation_stop,
            self._menu_label(_("S&top (keep speech)"), "tools.dictation_emergency_stop"),
        )
        dictation_menu.Append(
            self._id_dictation_cancel,
            self._menu_label(_("&Cancel (discard)"), "tools.dictation_cancel"),
        )
        dictation_menu.AppendSeparator()
        dictation_menu.Append(
            self._id_dictation_settings,
            self._menu_label(_("Dictation &Settings..."), "tools.dictation_settings"),
        )
        dictation_menu.Append(
            self._id_dictation_history,
            self._menu_label(_("Dictation &History && Review..."), "tools.dictation_history"),
        )
        # Hold-to-Dictate was removed (a held key repeats and announces itself
        # endlessly), so the submenu carries only the Locked Dictation surface.
        speech_menu.AppendSubMenu(dictation_menu, _("&Locked Dictation"))
        speech_menu.AppendSeparator()
        speech_menu.Append(
            self._id_speech_transcribe,
            self._menu_label(
                _("&Transcribe Audio or Video (Offline)..."), "tools.speech_transcribe"
            ),
        )
        speech_menu.Append(
            self._id_speech_captions,
            self._menu_label(_("Generate &Captions (Offline)..."), "tools.speech_captions"),
        )
        # The offline speech engine, Faster Whisper, and FFmpeg downloads used to
        # live here as separate items; they are consolidated into Help > Download
        # Optional Components (offline speech opens the guided engine+model picker),
        # so they no longer clutter this menu.
        speech_menu.AppendSeparator()
        speech_menu.Append(
            self._id_speech_hf_token,
            self._menu_label(_("&Hugging Face Token..."), "tools.speech_hf_token"),
        )
        speech_menu.AppendSeparator()
        speech_menu.Append(
            self._id_speech_export_audio,
            self._menu_label(_("&Export to Speech Audio..."), "tools.speech_export_audio"),
        )
        speech_menu.Append(
            self._id_speech_export_translated,
            self._menu_label(
                _("Export to &Translated Speech Audio..."), "tools.speech_export_translated"
            ),
        )
        speech_menu.Append(
            self._id_speech_batch_export,
            self._menu_label(_("Audiobook && &Batch Speech..."), "tools.speech_batch_export"),
        )
        speech_menu.Append(
            self._id_speech_pronunciations,
            self._menu_label(_("Manage &Pronunciations..."), "tools.speech_pronunciations"),
        )
        tools_menu.AppendSubMenu(speech_menu, _("&Speech"))
        # Media (Internet Radio, Podcasts) -------------------------------------
        radio_enabled = self._feature_enabled("core.radio")
        podcasts_enabled = self._feature_enabled("core.podcasts")
        library_enabled = self._feature_enabled("core.library")
        if radio_enabled or podcasts_enabled or library_enabled or is_app_released("player"):
            media_menu = wx.Menu()
        if radio_enabled:
            id_radio_browse = wx.NewIdRef()
            id_radio_add_custom = wx.NewIdRef()
            id_radio_find_streams = wx.NewIdRef()
            id_radio_manage_favorites = wx.NewIdRef()
            id_radio_play_pause = wx.NewIdRef()
            id_radio_stop = wx.NewIdRef()
            id_radio_mute = wx.NewIdRef()
            id_radio_volume_up = wx.NewIdRef()
            id_radio_volume_down = wx.NewIdRef()
            media_menu.Append(
                id_radio_browse, self._menu_label(_("&Browse Stations..."), "radio.browse")
            )
            media_menu.Append(
                id_radio_add_custom,
                self._menu_label(_("Add &Custom Station..."), "radio.add_custom_station"),
            )
            media_menu.Append(
                id_radio_find_streams,
                self._menu_label(_("&Find Streams from a Website..."), "radio.find_streams"),
            )
            media_menu.Append(
                id_radio_manage_favorites,
                self._menu_label(_("Manage Fa&vorites..."), "radio.manage_favorites"),
            )
            id_radio_play_last = wx.NewIdRef()
            media_menu.Append(
                id_radio_play_last,
                self._menu_label(_("Play &Last Station"), "radio.play_last"),
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_play_last(), id=id_radio_play_last)
            id_radio_whats_playing = wx.NewIdRef()
            media_menu.Append(
                id_radio_whats_playing,
                self._menu_label(_("&What's Playing?"), "radio.whats_playing"),
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.radio_whats_playing(), id=id_radio_whats_playing
            )
            id_radio_whats_playing_details = wx.NewIdRef()
            media_menu.Append(
                id_radio_whats_playing_details,
                self._menu_label(
                    _("What's Playing - Re&view and Copy..."), "radio.whats_playing_details"
                ),
            )
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.radio_whats_playing_details(),
                id=id_radio_whats_playing_details,
            )
            id_radio_announce_titles = wx.NewIdRef()
            media_menu.AppendCheckItem(
                id_radio_announce_titles,
                self._menu_label(_("Announce Trac&k Titles"), "radio.toggle_title_announcements"),
            )
            media_menu.Check(id_radio_announce_titles, self._radio_history.announce_track_titles)
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.radio_toggle_title_announcements(),
                id=id_radio_announce_titles,
            )
            media_menu.AppendSeparator()
            media_menu.Append(
                id_radio_play_pause, self._menu_label(_("&Play/Pause"), "radio.play_pause")
            )
            media_menu.Append(id_radio_stop, self._menu_label(_("&Stop"), "radio.stop"))
            media_menu.Append(
                id_radio_mute, self._menu_label(_("&Mute/Unmute"), "radio.mute_toggle")
            )
            media_menu.AppendSeparator()
            media_menu.Append(
                id_radio_volume_up, self._menu_label(_("Volume &Up"), "radio.volume_up")
            )
            media_menu.Append(
                id_radio_volume_down, self._menu_label(_("Volume &Down"), "radio.volume_down")
            )
            id_radio_volume_boost = wx.NewIdRef()
            media_menu.AppendCheckItem(
                id_radio_volume_boost,
                self._menu_label(_("Volume &Boost"), "radio.volume_boost"),
            )
            media_menu.Check(id_radio_volume_boost, self._radio_history.volume_boost)
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.radio_toggle_volume_boost(),
                id=id_radio_volume_boost,
            )
            # Live DVR (mpv engine): move within the buffered live window.
            id_radio_rewind = wx.NewIdRef()
            id_radio_forward = wx.NewIdRef()
            id_radio_live = wx.NewIdRef()
            media_menu.Append(
                id_radio_rewind, self._menu_label(_("Re&wind 30 Seconds"), "radio.rewind")
            )
            media_menu.Append(
                id_radio_forward, self._menu_label(_("&Forward 30 Seconds"), "radio.forward")
            )
            media_menu.Append(
                id_radio_live, self._menu_label(_("Back to &Live"), "radio.jump_to_live")
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_rewind(), id=id_radio_rewind)
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_forward(), id=id_radio_forward)
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_jump_to_live(), id=id_radio_live)
            from quill.core.speech.ffmpeg import ffmpeg_available

            if ffmpeg_available():
                media_menu.AppendSeparator()
                id_radio_record = wx.NewIdRef()
                id_radio_schedule = wx.NewIdRef()
                id_radio_rec_settings = wx.NewIdRef()
                id_radio_recordings = wx.NewIdRef()
                media_menu.Append(
                    id_radio_record,
                    self._menu_label(_("&Record Now / Stop Recording"), "radio.record_toggle"),
                )
                media_menu.Append(
                    id_radio_schedule,
                    self._menu_label(_("&Schedule Recording..."), "radio.schedule_recording"),
                )
                media_menu.Append(
                    id_radio_rec_settings,
                    self._menu_label(_("Recording &Settings..."), "radio.recording_settings"),
                )
                media_menu.Append(
                    id_radio_recordings,
                    self._menu_label(_("Recordin&gs..."), "radio.recordings"),
                )
                id_radio_record_station = wx.NewIdRef()
                media_menu.Append(
                    id_radio_record_station,
                    self._menu_label(_("Record Statio&n..."), "radio.record_station"),
                )
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e: self.open_record_station_dialog(),
                    id=id_radio_record_station,
                )
                # Concurrent recording: stop every recording at once. Always
                # present (it announces "Nothing is recording" when idle) so it
                # has a stable place; most useful when several run together.
                id_radio_stop_all = wx.NewIdRef()
                media_menu.Append(
                    id_radio_stop_all,
                    self._menu_label(_("Stop A&ll Recordings"), "radio.stop_all_recordings"),
                )
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e: self.radio_stop_all_recordings(),
                    id=id_radio_stop_all,
                )
                id_radio_wake_timer = wx.NewIdRef()
                media_menu.Append(
                    id_radio_wake_timer,
                    self._menu_label(_("Wake-Up Time&r..."), "radio.wake_timer"),
                )
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e: self.open_wake_timer_dialog(),
                    id=id_radio_wake_timer,
                )
                self.frame.Bind(
                    wx.EVT_MENU, lambda _e: self.radio_record_toggle(), id=id_radio_record
                )
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e: self._radio_open_schedule_recording(),
                    id=id_radio_schedule,
                )
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e: self._radio_open_recording_settings(),
                    id=id_radio_rec_settings,
                )
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e: self.open_radio_recordings(),
                    id=id_radio_recordings,
                )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_internet_radio(), id=id_radio_browse)
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self._radio_open_add_custom(None),
                id=id_radio_add_custom,
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self._radio_open_link_finder(), id=id_radio_find_streams
            )
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.open_manage_radio_favorites(),
                id=id_radio_manage_favorites,
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.radio_toggle_play_pause(), id=id_radio_play_pause
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_stop(), id=id_radio_stop)
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_mute_toggle(), id=id_radio_mute)
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.radio_volume_up(), id=id_radio_volume_up)
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.radio_volume_down(), id=id_radio_volume_down
            )
        if podcasts_enabled:
            if radio_enabled:
                media_menu.AppendSeparator()
            id_podcasts_open = wx.NewIdRef()
            id_podcasts_add = wx.NewIdRef()
            id_podcasts_import_opml = wx.NewIdRef()
            id_podcasts_export_opml = wx.NewIdRef()
            id_podcasts_play_pause = wx.NewIdRef()
            id_podcasts_stop = wx.NewIdRef()
            id_podcasts_pause_downloads = wx.NewIdRef()
            id_podcasts_resume_downloads = wx.NewIdRef()
            media_menu.Append(
                id_podcasts_open, self._menu_label(_("&Podcasts..."), "podcasts.open_manager")
            )
            media_menu.Append(
                id_podcasts_add, self._menu_label(_("&Add Podcast..."), "podcasts.add")
            )
            media_menu.Append(
                id_podcasts_import_opml,
                self._menu_label(_("&Import OPML..."), "podcasts.import_opml"),
            )
            media_menu.Append(
                id_podcasts_export_opml,
                self._menu_label(_("&Export OPML..."), "podcasts.export_opml"),
            )
            media_menu.AppendSeparator()
            media_menu.Append(
                id_podcasts_play_pause,
                self._menu_label(_("Podcast Play/Pa&use"), "podcasts.play_pause"),
            )
            media_menu.Append(
                id_podcasts_stop, self._menu_label(_("Podcast &Stop"), "podcasts.stop")
            )
            media_menu.AppendSeparator()
            media_menu.Append(
                id_podcasts_pause_downloads,
                self._menu_label(_("Pause All &Downloads"), "podcasts.pause_all_downloads"),
            )
            media_menu.Append(
                id_podcasts_resume_downloads,
                self._menu_label(_("Resume All D&ownloads"), "podcasts.resume_all_downloads"),
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_podcast_manager(), id=id_podcasts_open
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self._podcast_open_add_dialog(), id=id_podcasts_add
            )
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self._podcast_open_import_opml(),
                id=id_podcasts_import_opml,
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self._podcast_export_opml(), id=id_podcasts_export_opml
            )
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.podcast_toggle_play_pause(),
                id=id_podcasts_play_pause,
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_stop(), id=id_podcasts_stop)
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.podcast_pause_all_downloads(),
                id=id_podcasts_pause_downloads,
            )
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e: self.podcast_resume_all_downloads(),
                id=id_podcasts_resume_downloads,
            )
        if library_enabled:
            if radio_enabled or podcasts_enabled:
                media_menu.AppendSeparator()
            id_library_open = wx.NewIdRef()
            media_menu.Append(
                id_library_open, self._menu_label(_("&Book Library..."), "library.open")
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_library_dialog(), id=id_library_open)
        if radio_enabled or podcasts_enabled:
            media_menu.AppendSeparator()
            id_sleep_timer = wx.NewIdRef()
            media_menu.Append(
                id_sleep_timer, self._menu_label(_("Sleep &Timer..."), "media.sleep_timer")
            )
            self.frame.Bind(
                wx.EVT_MENU, lambda _e: self.open_sleep_timer_dialog(), id=id_sleep_timer
            )
        if is_app_released("player"):
            if media_menu.GetMenuItemCount():
                media_menu.AppendSeparator()
            id_media_player = wx.NewIdRef()
            media_menu.Append(
                id_media_player, self._menu_label(_("&Media Player..."), "app.open_media_player")
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_media_player(), id=id_media_player)
        if radio_enabled or podcasts_enabled or library_enabled or is_app_released("player"):
            tools_menu.AppendSubMenu(media_menu, _("&Media"))

        # Comparison (was Compare Documents) ----------------------------------
        compare_menu = wx.Menu()
        compare_menu.Append(self._id_compare_with_file, _("Compare with &File..."))
        compare_menu.Append(self._id_compare_open_documents, _("Compare &Open Documents..."))
        compare_menu.AppendSeparator()
        compare_menu.Append(self._id_compare_next_difference, _("&Next Difference"))
        compare_menu.Append(self._id_compare_previous_difference, _("&Previous Difference"))
        compare_menu.Append(self._id_compare_announce_difference, _("&Announce Current Difference"))
        compare_menu.Append(self._id_compare_difference_list, _("Difference &List..."))
        compare_menu.Append(self._id_compare_toggle_sync, _("Toggle &Synchronized Navigation"))
        compare_menu.Append(self._id_compare_toggle_whitespace, _("Toggle &Ignore Whitespace"))
        compare_menu.Append(self._id_compare_options, _("Compare O&ptions..."))
        compare_menu.Append(self._id_compare_generate_report, _("&Generate Accessible Report"))
        compare_menu.AppendSeparator()
        compare_menu.Append(self._id_compare_create_summary, _("Create Difference &Summary"))
        compare_menu.Append(self._id_compare_copy_current, _("Copy &Current Difference"))
        compare_menu.Append(self._id_compare_copy_all, _("Copy A&ll Differences"))
        tools_menu.AppendSubMenu(compare_menu, _("C&omparison"))

        # Braille -----------------------------------------------------------------
        tools_menu.AppendSubMenu(self._build_braille_menu_with_repair(), _("&Braille"))

        # Watch Folder (extracted from former Dictation submenu) --------------
        watch_folder_menu = wx.Menu()
        watch_folder_menu.Append(
            self._id_watch_folder_toggle,
            _("Watch Folder &Monitoring (in Settings)..."),
        )
        watch_folder_menu.Append(
            self._id_watch_folder_settings,
            self._menu_label(_("Watch Folder &Profiles..."), "tools.watch_folder_settings"),
        )
        watch_folder_menu.Append(
            self._id_watch_folder_status,
            self._menu_label(_("Watch Folder &Queue..."), "tools.watch_folder_status"),
        )
        tools_menu.AppendSubMenu(watch_folder_menu, _("&Watch Folder"))

        # AI menu — promoted to a top-level "&AI" menu (was Tools > AI Assistant).
        # Structured into four pillars: the conversation (Ask Quill), context
        # actions + agents, task submenus, and the Library/Hub management surfaces.
        # See PRD sections 5.84a (the four-pillar menu) and 5.84c (AI onboarding).
        ai_menu = wx.Menu()
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.ai.onboarding import ai_needs_setup
        from quill.ui.agent_editor_host import append_action_ring_menu, append_agent_menu
        from quill.ui.ai_setup_wizard import run_ai_setup_wizard
        from quill.ui.concierge_menu import append_concierge_action

        # -- Set Up AI (the gentle on-ramp) -----------------------------------
        # Always reachable; labeled "start here" and shown first until AI is set
        # up, then it stays as a quiet re-run point. Direct-bound so the
        # size-budgeted main_frame module does not need to grow.
        _setup_id = wx.NewIdRef()
        _setup_label = _("&Set Up AI... (start here)") if ai_needs_setup() else _("&Set Up AI...")
        ai_menu.Append(_setup_id, _setup_label)
        self.frame.Bind(wx.EVT_MENU, lambda _e: run_ai_setup_wizard(self), id=_setup_id)
        ai_menu.AppendSeparator()

        # -- The conversation (the front door) --------------------------------
        ai_menu.Append(
            self._id_ask_quill_chat,
            self._menu_label(_("&Ask Quill..."), "tools.ask_quill_chat"),
        )
        ai_menu.Append(
            self._id_ask_quill_voice,
            self._menu_label(_("Ask Quill by &Voice..."), "tools.ask_quill_conversation"),
        )
        ai_menu.AppendSeparator()

        # -- Context actions + agents -----------------------------------------
        # Accessibility Tune-Up stays first-class for the screen-reader audience.
        ai_menu.Append(
            self._id_ai_accessibility_agent,
            self._menu_label(_("Accessibility &Tune-Up..."), "tools.ai_accessibility_agent"),
        )
        # "What can I do here?" is generated by the Concierge from live context;
        # "Rewrite & Improve" is the Selection Action Ring for the current file
        # type; "Run Agent" lists the full catalog. These power-user, agentic
        # entries are hidden in the gentle Basic experience mode (set in the AI
        # Setup Wizard) so newcomers see a smaller surface; they stay reachable
        # from the command palette and return the moment the user switches to
        # Advanced. Everyday features (Proofread, Translate, Read Aloud, ...) stay.
        from quill.core.ai.onboarding import is_basic_mode

        if not is_basic_mode():
            append_concierge_action(self, ai_menu)
            append_action_ring_menu(self, ai_menu)
            append_agent_menu(self, ai_menu)
        ai_menu.AppendSeparator()

        # -- Proofread --------------------------------------------------------
        proofread_menu = wx.Menu()
        proofread_menu.Append(
            self._id_check_grammar_ai,
            self._menu_label(_("Check Grammar with &AI..."), "tools.check_grammar_ai"),
        )
        proofread_menu.Append(
            self._id_ai_grammar_style,
            self._menu_label(_("&Grammar and Style Check..."), "tools.ai_grammar_style"),
        )
        proofread_menu.Append(
            self._id_ai_spell_check,
            self._menu_label(_("&Spell Check..."), "tools.ai_spell_check"),
        )
        proofread_menu.Append(
            self._id_ai_spell_check_interactive,
            self._menu_label(_("Spell Check &Interactive..."), "tools.ai_spell_check_interactive"),
        )
        ai_menu.AppendSubMenu(proofread_menu, _("&Proofread"))

        # -- Transform Selection (single-shot verbs; canonical Ctrl+Alt+Shift+ chords)
        transform_menu = wx.Menu()
        transform_menu.Append(
            self._id_ai_rewrite_selection,
            self._menu_label(_("&Rewrite Selection"), "tools.ai_rewrite_selection"),
        )
        transform_menu.Append(
            self._id_ai_summarize_selection,
            self._menu_label(_("&Summarize Selection"), "tools.ai_summarize_selection"),
        )
        transform_menu.Append(
            self._id_ai_expand_selection,
            self._menu_label(_("E&xpand Selection"), "tools.ai_expand_selection"),
        )
        transform_menu.Append(
            self._id_ai_continue_writing,
            self._menu_label(_("&Continue Writing"), "tools.ai_continue_writing"),
        )
        transform_menu.Append(
            self._id_ai_fix_grammar,
            self._menu_label(_("Fix &Grammar"), "tools.ai_fix_grammar"),
        )
        transform_menu.Append(
            self._id_ai_generate_toc,
            self._menu_label(_("Generate &Table of Contents"), "tools.ai_generate_toc"),
        )
        ai_menu.AppendSubMenu(transform_menu, _("Trans&form Selection"))

        # -- Translate --------------------------------------------------------
        translate_menu = wx.Menu()
        translate_menu.Append(
            self._id_ai_translate_selection,
            self._menu_label(_("Translate &Selection..."), "tools.ai_translate_selection"),
        )
        translate_menu.Append(
            self._id_ai_translate_document,
            self._menu_label(_("Translate &Document..."), "tools.ai_translate_document"),
        )
        ai_menu.AppendSubMenu(translate_menu, _("Tra&nslate"))

        # -- Read Aloud (AI voice) --------------------------------------------
        read_aloud_menu = wx.Menu()
        read_aloud_menu.Append(
            self._id_ai_tts_read_selection,
            self._menu_label(_("Read &Selection Aloud"), "tools.ai_tts_read_selection"),
        )
        read_aloud_menu.Append(
            self._id_ai_tts_read_document,
            self._menu_label(_("Read &Document Aloud"), "tools.ai_tts_read_document"),
        )
        read_aloud_menu.Append(
            self._id_ai_tts_stop,
            self._menu_label(_("Sto&p AI Reading"), "tools.ai_tts_stop"),
        )
        read_aloud_menu.Append(
            self._id_ai_tts_export_mp3,
            self._menu_label(_("E&xport Document as Audio..."), "tools.ai_tts_export_mp3"),
        )
        ai_menu.AppendSubMenu(read_aloud_menu, _("Read A&loud"))

        # -- Transcribe audio -------------------------------------------------
        transcribe_menu = wx.Menu()
        # One entry: the dialog's "Translate audio to English" checkbox covers
        # translation, so a separate Translate menu item would open the same dialog.
        transcribe_menu.Append(
            self._id_ai_transcribe_audio,
            self._menu_label(_("Transcri&be Audio File..."), "tools.ai_transcribe_audio"),
        )
        # The Listening Companion: run a Transcript Action (Meeting Minutes, Action
        # Items, Clean Up & Draft, ...) on the current selection or document — the same
        # magic offered after transcription, reachable anytime. Bound directly so the
        # size-budgeted main_frame module does not need to grow.
        from quill.ui.transcript_actions_ui import run_transcript_actions_on_document

        transcribe_menu.AppendSeparator()
        _ta_actions_id = wx.NewIdRef()
        transcribe_menu.Append(_ta_actions_id, _("Transcript &Actions..."))
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: run_transcript_actions_on_document(self),
            id=_ta_actions_id,
        )
        ai_menu.AppendSubMenu(transcribe_menu, _("Transcri&be Audio"))

        # -- More -------------------------------------------------------------
        more_menu = wx.Menu()
        more_menu.Append(
            self._id_ai_document_qa,
            self._menu_label(_("Document &Q&&A..."), "tools.ai_document_qa"),
        )
        more_menu.Append(
            self._id_ai_reading_order,
            self._menu_label(_("Improve &Reading Order..."), "tools.ai_reading_order"),
        )
        more_menu.Append(
            self._id_ai_thesaurus,
            self._menu_label(_("AI T&hesaurus..."), "tools.ai_thesaurus"),
        )
        more_menu.Append(
            self._id_train_style,
            self._menu_label(_("&Train Writing Style..."), "tools.train_writing_style"),
        )
        more_menu.Append(
            self._id_writing_instructions,
            self._menu_label(_("&Writing Instructions..."), "tools.writing_instructions"),
        )
        ai_menu.AppendSubMenu(more_menu, _("&More"))
        ai_menu.AppendSeparator()

        # -- AI Library (Prompts / Skills / Agents — one unified manager) -----
        # Prompts, Skills, and Agents now live in one tabbed manager with a single
        # verb set and the Promote continuum. Prompt Studio, Writing Assistant,
        # Agent Center, and Validate Agents remain reachable as commands during the
        # deprecation window, but no longer scatter the menu.
        ai_menu.Append(
            self._id_ai_library,
            self._menu_label(_("AI &Library..."), "tools.ai_library"),
        )

        # -- Configuration ----------------------------------------------------
        # The AI Hub is the single config front door. Engine switching, GitHub
        # Copilot setup, and Session Branches all now live inside the Hub (its
        # Engines and Sessions tabs), so the old "Engine & Sessions" submenu is
        # gone entirely — the menu keeps only the Hub and the Use AI switch.
        ai_menu.Append(
            self._id_ai_hub,
            self._menu_label(_("AI &Hub..."), "tools.ai_hub"),
        )
        ai_menu.AppendSeparator()

        # -- Master switch ----------------------------------------------------
        ai_menu.AppendCheckItem(self._id_ai_enabled, _("Use Artificial &Intelligence"))
        ai_menu.Check(self._id_ai_enabled, load_ai_enabled())

        # Basic vs Advanced: a one-click way to grow into the full AI surface (or
        # keep it simple) without re-running the wizard. Direct-bound; toggling it
        # saves the experience mode and rebuilds the menu so the agentic entries
        # appear or hide immediately.
        from quill.core.ai.onboarding import (
            EXPERIENCE_ADVANCED,
            EXPERIENCE_BASIC,
            is_basic_mode,
            save_experience_mode,
        )

        _adv_id = wx.NewIdRef()
        adv_item = ai_menu.AppendCheckItem(_adv_id, _("Show &advanced AI features"))
        adv_item.Check(not is_basic_mode())

        def _toggle_experience(_event: object) -> None:
            # Flip the saved mode: advanced <-> basic. Reading is_basic_mode() to pick the
            # *same* value (the original code) was a no-op — the mode never changed, so the
            # menu never toggled.
            save_experience_mode(EXPERIENCE_ADVANCED if is_basic_mode() else EXPERIENCE_BASIC)
            # The agentic entries are appended once while building the menu, gated on
            # is_basic_mode(); a contextual refresh only enables/disables existing items
            # and would never add or remove them. Rebuild the whole menubar so the
            # entries appear or hide immediately. Deferred so the rebuild happens after
            # this menu-selection event has finished dispatching.
            self._wx.CallAfter(self._build_menu)

        self.frame.Bind(wx.EVT_MENU, _toggle_experience, id=_adv_id)
        # "Forget API Key" moved into the AI Hub as a per-provider action
        # ("Forget this provider's key"), since a single global forget is
        # ambiguous once each provider keeps its own key.

        # BITS Whisperer (conditional, deferred to QUILL 2.0) ----------------
        # "About Whisperer" was folded into the single About Quill dialog.
        whisperer_menu = wx.Menu()
        whisperer_menu.Append(
            self._id_profile_onboarding,
            self._menu_label(_("&Startup Wizard..."), "help.startup_wizard"),
        )
        # Windows dictation removed (offline Locked Dictation replaces it); this
        # submenu is now just Watch Folder.
        bw_dictation_menu = wx.Menu()
        bw_dictation_menu.Append(
            self._id_watch_folder_toggle,
            _("Watch Folder &Monitoring (in Settings)..."),
        )
        bw_dictation_menu.Append(
            self._id_watch_folder_settings,
            self._menu_label(_("Watch Folder &Profiles..."), "tools.watch_folder_settings"),
        )
        bw_dictation_menu.Append(
            self._id_watch_folder_status,
            self._menu_label(_("Watch Folder &Queue..."), "tools.watch_folder_status"),
        )
        whisperer_menu.AppendSubMenu(bw_dictation_menu, _("&Watch Folder"))
        bw_models_menu = wx.Menu()
        self._append_bw_safe_mode_badge(bw_models_menu)
        bw_models_menu.Append(
            self._id_bw_model_manager,
            self._menu_label(_("&Model Manager..."), "whisperer.model_manager"),
        )
        bw_models_menu.Append(
            self._id_bw_model_status,
            self._menu_label(_("Model &Status"), "whisperer.model_status"),
        )
        bw_models_menu.Append(
            self._id_bw_model_recommend,
            self._menu_label(_("Use &Recommended Model"), "whisperer.model_recommend"),
        )
        bw_models_menu.AppendSeparator()
        bw_models_menu.Append(
            self._id_bw_check_faster_whisper,
            self._menu_label(_("Check &faster-whisper Engine"), "whisperer.check_faster_whisper"),
        )
        bw_models_menu.Append(
            self._id_bw_download_queue,
            self._menu_label(_("Download &Queue..."), "whisperer.download_queue"),
        )
        whisperer_menu.AppendSubMenu(bw_models_menu, _("Speech &Models"))
        bw_providers_menu = wx.Menu()
        self._append_bw_safe_mode_badge(bw_providers_menu)
        bw_providers_menu.Append(
            self._id_bw_provider_center,
            self._menu_label(_("&Provider Center..."), "whisperer.provider_center"),
        )
        bw_providers_menu.Append(
            self._id_bw_provider_status,
            self._menu_label(_("Provider &Status"), "whisperer.provider_status"),
        )
        bw_providers_menu.Append(
            self._id_bw_provider_recommend,
            self._menu_label(_("Use Re&commended Provider"), "whisperer.provider_recommend"),
        )
        bw_providers_menu.Append(
            self._id_bw_provider_select,
            self._menu_label(_("&Select Provider..."), "whisperer.provider_select"),
        )
        whisperer_menu.AppendSubMenu(bw_providers_menu, _("&Providers"))
        bw_rollout_menu = wx.Menu()
        self._append_bw_safe_mode_badge(bw_rollout_menu)
        bw_rollout_menu.Append(
            self._id_bw_readiness_check,
            self._menu_label(_("&Readiness Check"), "whisperer.readiness_check"),
        )
        bw_rollout_menu.Append(
            self._id_bw_capability_matrix,
            self._menu_label(_("&Capability Matrix"), "whisperer.capability_matrix"),
        )
        whisperer_menu.AppendSubMenu(bw_rollout_menu, _("&Rollout"))
        if self._feature_enabled("core.bw_whisperer"):
            tools_menu.AppendSubMenu(whisperer_menu, _("&BITS Whisperer"))

        # Share (Mastodon) ---------------------------------------------------
        share_menu = wx.Menu()
        share_menu.Append(
            self._id_post_mastodon,
            self._menu_label(_("&Post to Mastodon..."), "tools.post_to_mastodon"),
        )
        share_menu.Append(
            self._id_mastodon_accounts,
            self._menu_label(_("Mastodon &Accounts..."), "tools.manage_mastodon_accounts"),
        )
        # Ids stored on self so the NewIdRefs stay alive for the frame's lifetime.
        self._id_mastodon_profile = wx.NewIdRef()
        share_menu.Append(
            self._id_mastodon_profile,
            self._menu_label(_("&View Mastodon Profile..."), "tools.view_mastodon_profile"),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.view_mastodon_profile(), id=self._id_mastodon_profile
        )
        self._id_mastodon_add_list = wx.NewIdRef()
        share_menu.Append(
            self._id_mastodon_add_list,
            self._menu_label(
                _("Add a User to a Mastodon &List..."), "tools.mastodon_add_user_to_list"
            ),
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.mastodon_add_user_to_list(), id=self._id_mastodon_add_list
        )
        tools_menu.AppendSubMenu(share_menu, _("&Share"))

        self._id_global_hotkeys = wx.NewIdRef()
        tools_menu.Append(
            self._id_global_hotkeys,
            self._menu_label(_("&Global Hotkeys..."), "tools.global_hotkeys"),
        )

        # Advanced (expanded: power-tool utilities + Macros + Authoring +
        # Document Intake + Shell Integration, per menus.md §10.3) ----------
        power_tools_menu = wx.Menu()
        self._append_power_tools_group(power_tools_menu, "power_tools")
        power_tools_menu.AppendSeparator()
        macro_menu = wx.Menu()
        macro_menu.Append(
            self._id_start_macro_recording,
            self._menu_label(_("&Start Recording"), "tools.start_macro_recording"),
        )
        macro_menu.Append(
            self._id_stop_macro_recording,
            self._menu_label(_("S&top Recording"), "tools.stop_macro_recording"),
        )
        macro_menu.Append(
            self._id_play_last_macro,
            self._menu_label(_("&Play Last Macro"), "tools.play_last_macro"),
        )
        macro_menu.Append(
            self._id_manage_macros,
            self._menu_label(_("&Manage Macros..."), "tools.manage_macros"),
        )
        power_tools_menu.AppendSubMenu(macro_menu, _("&Macros"))
        power_tools_menu.AppendSeparator()
        dev_console_menu = wx.Menu()
        dev_console_menu.Append(
            self._id_dev_console_python,
            self._menu_label(_("Open &Python Console..."), "tools.open_python_console"),
        )
        dev_console_menu.Append(
            self._id_dev_console_ts,
            self._menu_label(_("Open &TypeScript Console..."), "tools.open_typescript_console"),
        )
        dev_console_menu.AppendSeparator()
        dev_console_menu.Append(
            self._id_dev_copy_diagnostic,
            self._menu_label(_("&Copy Diagnostic Summary"), "tools.copy_diagnostic_summary"),
        )
        dev_console_menu.Append(
            self._id_dev_restart_ts_worker,
            self._menu_label(_("&Restart TypeScript Worker"), "tools.restart_typescript_worker"),
        )
        power_tools_menu.AppendSubMenu(dev_console_menu, _("&Developer Console"))
        power_tools_menu.AppendSeparator()
        power_tools_menu.Append(
            self._id_regex_helper,
            self._menu_label(_("Regular Expression &Helper..."), "tools.regex_helper"),
        )
        power_tools_menu.Append(
            self._id_external_tools,
            self._menu_label(
                _("External Tools and Format &Support..."),
                "tools.external_tools",
            ),
        )
        power_tools_menu.Append(
            self._id_yaml_structure_editor,
            self._menu_label(_("&YAML Structure Editor..."), "tools.yaml_structure_editor"),
        )
        power_tools_menu.AppendSeparator()
        intake_menu = wx.Menu()
        intake_menu.Append(
            self._id_document_intake_report,
            self._menu_label(_("&Document Intake Report..."), "tools.document_intake_report"),
        )
        intake_menu.Append(
            self._id_review_extraction_quality,
            self._menu_label(_("&Review Extraction Quality..."), "tools.review_extraction_quality"),
        )
        intake_menu.Append(
            self._id_report_bad_extraction,
            self._menu_label(_("R&eport Bad Extraction..."), "tools.report_bad_extraction"),
        )
        power_tools_menu.AppendSubMenu(intake_menu, _("Document &Intake"))
        power_tools_menu.AppendSeparator()
        power_tools_menu.Append(
            self._id_shell_install,
            self._menu_label(_("&Install Shell Integration..."), "tools.shell_install"),
        )
        power_tools_menu.Append(
            self._id_shell_remove,
            self._menu_label(_("&Remove Shell Integration"), "tools.shell_remove"),
        )
        tools_menu.AppendSubMenu(power_tools_menu, _("&Advanced"))

        # Quillins ------------------------------------------------------------
        tools_menu.AppendSubMenu(self._build_quillins_menu(), _("&Quillins"))

        # Customize & Support (Support + Customize merged per §10.3) ----------
        customize_support_menu = wx.Menu()
        customize_support_menu.Append(
            self._id_preferences,
            self._menu_label(_("Pre&ferences..."), "app.preferences"),
        )
        customize_support_menu.Append(
            self._id_menu_editor,
            self._menu_label(_("Customize &Menus..."), "app.menu_editor"),
        )
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(
            self._id_profiles_and_features,
            self._menu_label(
                _("&Profiles and Features..."), "tools.profiles_and_features_settings"
            ),
        )
        customize_support_menu.Append(self._id_status_bar_settings, _("&Status Bar Layout..."))
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(self._id_share_export, _("&Export and Back Up..."))
        customize_support_menu.Append(self._id_share_import, _("&Import or Restore..."))
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(self._id_keymap_editor, _("&Keymap Editor..."))
        customize_support_menu.Append(self._id_export_keymap, _("&Export Keymap..."))
        customize_support_menu.Append(self._id_import_keymap, _("&Import Keymap..."))
        customize_support_menu.Append(self._id_reset_keymap, _("&Reset Keymap"))
        customize_support_menu.Append(
            self._id_reset_all_defaults, _("Reset &Everything to Factory Defaults...")
        )
        customize_support_menu.AppendSeparator()
        customize_support_menu.Append(self._id_notifications, _("Show &Notifications"))
        customize_support_menu.Append(self._id_save_diagnostics, _("Save &Diagnostics..."))
        customize_support_menu.Append(self._id_open_logs_folder, _("Open &Logs Folder"))
        self._id_view_startup_logs = wx.NewIdRef()
        customize_support_menu.Append(
            self._id_view_startup_logs,
            self._menu_label(_("View &Startup Logs..."), "help.view_startup_logs"),
        )
        customize_support_menu.Append(
            self._id_open_diagnostics_folder,
            _("Open &Diagnostics Folder"),
        )
        customize_support_menu.Append(self._id_check_updates, _("Check for &Updates"))
        tools_menu.AppendSubMenu(customize_support_menu, _("&Customize and Support"))

        # The former top-level "Settings" menu is gone. All configuration now
        # lives together under Tools > Customize (Preferences, Customize Menus,
        # profiles/features, export/import, and keymap), which is the
        # Windows/Tools convention. Nothing references settings_menu after
        # this point; do not append it to the menu bar.

        help_menu = wx.Menu()
        help_menu.Append(
            self._id_help_on_control,
            self._menu_label(_("Help on This &Control\tF1"), "help.help_on_control"),
        )
        help_menu.Append(
            self._id_context_help,
            self._menu_label(_("&What Can I Do Here?\tShift+F1"), "help.what_can_i_do_here"),
        )
        help_menu.Append(
            self._id_announce_context_shortcuts,
            self._menu_label(_("Announce Mode &Shortcuts"), "help.context_help"),
        )
        help_menu.Append(
            self._id_show_spoken_echo,
            self._menu_label(_("Show Spoken &Echo"), "view.spoken_echo"),
        )
        help_menu.Append(
            self._id_help_status_page,
            self._menu_label(_("Status &Page"), "help.status_page"),
        )
        help_menu.Append(
            self._id_why_dont_i_see_feature,
            self._menu_label(_("&Why Don't I See a Feature?"), "help.why_dont_i_see_feature"),
        )
        self._id_download_components = wx.NewIdRef()
        help_menu.Append(
            self._id_download_components,
            self._menu_label(_("&Download Optional Components..."), "help.download_components"),
        )
        self._id_redeem_unlock_code = wx.NewIdRef()
        if is_dev_build():
            # Tester-only surface: redeemed codes are still honored everywhere,
            # but the redeem entry is hidden from public builds (all apps).
            help_menu.Append(
                self._id_redeem_unlock_code,
                self._menu_label(_("Redeem &Unlock Code..."), "help.redeem_unlock_code"),
            )
        help_menu.AppendSeparator()
        self._id_open_user_guide = wx.NewIdRef()
        self._id_open_third_party_notices = wx.NewIdRef()
        help_menu.Append(self._id_open_user_guide, _("Open User &Guide\tCtrl+F1"))
        help_menu.Append(
            self._id_open_third_party_notices,
            _("Open &Third-Party Notices"),
        )
        help_menu.Append(self._id_open_welcome_guide, _("Open &Welcome Guide"))
        help_menu.Append(self._id_open_keyboard_reference, _("Open Keyboard &Reference"))
        help_menu.Append(
            self._id_profile_onboarding,
            self._menu_label(_("&Personalise QUILL..."), "help.startup_wizard"),
        )
        if not self._feature_enabled("core.braille"):
            help_menu.Append(
                self._id_enable_braille_mode,
                self._menu_label(_("Enable &Braille Mode..."), "help.enable_braille_mode"),
            )
        help_menu.AppendSeparator()
        help_menu.Append(
            self._id_save_diagnostics,
            self._menu_label(_("Save &Diagnostics..."), "help.save_diagnostics"),
        )
        help_menu.AppendSeparator()
        profiles_menu = wx.Menu()
        profiles_menu.Append(
            self._id_switch_feature_profile,
            self._menu_label(_("&Switch Profile..."), "help.switch_feature_profile"),
        )
        profiles_menu.Append(
            self._id_feature_profile_health_check,
            self._menu_label(
                _("Profile &Health Check..."),
                "help.feature_profile_health_check",
            ),
        )
        profiles_menu.Append(
            self._id_individual_feature_toggles,
            self._menu_label(
                _("Manage &Individual Features..."),
                "tools.individual_feature_toggles",
            ),
        )
        profiles_menu.AppendSeparator()
        profiles_menu.Append(
            self._id_undo_profile_change,
            self._menu_label(_("&Undo Last Profile Change"), "help.undo_last_profile_change"),
        )
        profiles_menu.Append(
            self._id_reset_feature_profile,
            self._menu_label(_("Reset to &Essential Profile"), "help.reset_feature_profile"),
        )
        help_menu.AppendSubMenu(profiles_menu, _("Feature &Profiles"))
        help_menu.Append(
            self._id_report_bug,
            self._menu_label(_("Report a &Bug..."), "help.report_bug"),
        )
        # "Check for Updates on Startup" lives in Settings now (removed the
        # duplicate Help-menu toggle).
        help_menu.Append(self._id_check_updates, _("Check for &Updates..."))
        help_menu.Append(self._id_whats_new, _("&What's New..."))
        if self._feature_enabled("core.glow"):
            help_menu.Append(self._id_check_glow_updates, _("Check for &GLOW Updates..."))
        # On macOS the Application menu already shows "About Quill" via the
        # wx.ID_ABOUT binding below, so appending it to Help too produced a
        # duplicate entry. Windows has no Application menu, so it stays here.
        if sys.platform != "darwin":
            help_menu.Append(self._id_about_quill, _("&About Quill"))

        # MENU-REORDER (menus.md Phase 1): every top-level menu is attached to the
        # bar here, in one place, in the conventional Windows order. Menu *content*
        # is built above in arbitrary order; wx lets bar order be set independently
        # of construction order. Keep this list in sync with ``_TOP_MENU_DEFS``.
        menu_bar.Append(file_menu, _("&File"))
        menu_bar.Append(edit_menu, _("&Edit"))
        menu_bar.Append(view_menu, _("&View"))
        menu_bar.Append(insert_menu, _("&Insert"))
        menu_bar.Append(format_menu, _("F&ormat"))
        menu_bar.Append(navigate_menu, _("&Navigate"))
        menu_bar.Append(search_menu, _("&Search"))
        menu_bar.Append(tools_menu, _("&Tools"))
        menu_bar.Append(ai_menu, _("&AI"))
        # Pre-release top-level Audio Description Project menu, promoted out of
        # Tools > Media so QUILL matches the companion apps (Quill Radio, QUILL
        # Cast). Present by default (see ``_build_adp_menu``); like the AI and
        # QuillVille menus it is conditional and stays out of ``_TOP_MENU_DEFS``.
        adp_menu = self._build_adp_menu()
        if adp_menu is not None:
            menu_bar.Append(adp_menu, _("A&udio Description Project"))
        menu_bar.Append(window_menu, _("&Window"))
        # The standard QuillVille cross-app switcher, just before Help -- the
        # same menu every QuillVille app carries.
        from quill.ui.quillville_menu import build_quillville_menu

        self._quillville_menu_ids: list[object] = []
        quillville_menu = build_quillville_menu(
            wx,
            self.frame,
            self.open_companion_app,
            exclude="quill",
            retain=self._quillville_menu_ids.append,
        )
        menu_bar.Append(quillville_menu, _("&QuillVille"))
        menu_bar.Append(help_menu, _("&Help"))

        # #76: on macOS, tell wx this is the system Window menu. AppKit then
        # moves it to its conventional slot (just left of Help) and merges in
        # the standard items a Mac user expects -- Minimize (Cmd+M), Zoom,
        # Bring All to Front, and the live window list -- alongside Quill's own
        # Next/Previous/Close-Other/Send-to-Tray entries. Without SetWindowMenu
        # the Window menu is an ordinary menu missing all the standard items.
        # Guarded like the SetHelpMenu hint below so a wx build without the API
        # degrades gracefully.
        if sys.platform == "darwin":
            try:
                if hasattr(menu_bar, "SetWindowMenu"):
                    menu_bar.SetWindowMenu(window_menu)
            except Exception:  # noqa: BLE001
                pass

        # #613: on macOS, tell wx that the "Help" menu is the system
        # Help menu so the OS moves it to the rightmost position (where
        # macOS users expect it) instead of leaving it in the slot wx
        # gave it (the menu bar's tail, but wx only respects the
        # SetHelpMenu hint for the system Help menu). Without this,
        # VoiceOver users see a top-level menu order that does not
        # match the macOS AppKit convention. Wrapped in hasattr +
        # try/except so a wx build without the API degrades gracefully
        # (and the dialog_inventory / module_size gates do not see an
        # attribute error).
        if sys.platform == "darwin":
            try:
                if hasattr(menu_bar, "SetHelpMenu"):
                    menu_bar.SetHelpMenu(help_menu)
                elif hasattr(menu_bar, "MacSetHelpMenuTitle"):
                    menu_bar.MacSetHelpMenuTitle(_("&Help"))
            except Exception:  # noqa: BLE001
                # Help-menu hint is best-effort; do not break menu
                # construction if the wx build rejects the call.
                pass

        self._apply_menu_customization(menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._refresh_contextual_menu_items()
        self._apply_ai_menu_enabled()
        # Kill switch: dim menu items whose feature a safety advisory has locked.
        self._apply_feature_lock_menu_state()

        self._bind_menu_events()
