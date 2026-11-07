"""QUILL Lite's door to the shared WordPress commands: File > WordPress (wordpress.md 11).

An adapter with no commands of its own: each ``cmd_wp_*`` below hands straight
to the shared :class:`~quill.ui.wordpress_commands.WordPressCommands`, the same
object QUILL's ``main_frame_wordpress.py`` reaches. The rows come from
:data:`quill.core.wordpress.menu.WORDPRESS_ROWS`, so the two menus match.
"""

from __future__ import annotations

from typing import Any

from quill.apps.lite_window_wordpress_host import LiteWordPressHost

__all__ = ["DocumentWordPressMixin", "LiteWordPressHost"]


class DocumentWordPressMixin:
    """The WordPress rows in a QUILL Lite window (wordpress.md 11, 12)."""

    def _sync_wordpress_items(self) -> None:
        """Dim the page commands unless this window holds a WordPress document."""
        from quill.core.wordpress.menu import DOCUMENT_ONLY, all_rows, lite_handler

        items = getattr(self, "_menu_items", {})
        try:
            path = LiteWordPressHost(self).current_path()
            is_wordpress = self._wordpress().local.copy_for_path(path) is not None
        except Exception:  # noqa: BLE001 - a menu refresh must never raise
            is_wordpress = False
        for _path, (command_id, _title, handler) in all_rows():
            item = items.get(lite_handler(command_id))
            if handler in DOCUMENT_ONLY and item is not None:
                item.Enable(is_wordpress)

    def _wordpress_key_down(self, event: Any) -> bool:
        """The WordPress keys: Ctrl+Alt+Shift+Grave, then a letter (wordpress.md 19).

        Called first from the editor's key-down handler. True when the key was
        the layer's. The shared :class:`~quill.core.wordpress.keys.WordPressKeyLayer`
        decides what a key means -- the same object QUILL's char hook asks -- and
        the letters are the keys the command table resolves to now, so a row the
        Keyboard Manager moved, or an area switched off, is not a layer letter.
        """
        import wx

        from quill.core.wordpress import keys

        layer = getattr(self, "_wordpress_key_layer", None)
        if layer is None:
            layer = self._wordpress_key_layer = keys.WordPressKeyLayer()
        code = int(event.GetKeyCode())

        def held(name: str) -> bool:
            # A key event from a test or another control may lack a modifier
            # query; treat that as "not held" rather than failing the key.
            query = getattr(event, name, None)
            return bool(query()) if callable(query) else False

        if layer.active:
            if code in {wx.WXK_SHIFT, wx.WXK_CONTROL, wx.WXK_ALT}:
                return True  # Shift going down on the way to Shift+S
            key = keys.event_key(
                code,
                ctrl=held("ControlDown"),
                alt=held("AltDown"),
                shift=held("ShiftDown"),
                escape_code=wx.WXK_ESCAPE,
            )
            if not key:
                layer.cancel()
                return False
            outcome = layer.press(key, keys.layer_from_bindings(self._wordpress_key_bindings()))
            if outcome.command:
                self.run_unless_read_only(outcome.command)
            elif outcome.message:
                self._announce(outcome.message)
            return outcome.consumed
        if not (held("ControlDown") and held("AltDown") and held("ShiftDown")):
            return False
        # The grave key, matched by where it sits so it works on any layout
        # (#1753): the same shared check QUILL uses for its QUILL key.
        from quill.core.grave_key import is_grave_key

        def raw(name: str) -> int:
            query = getattr(event, name, None)
            try:
                return int(query()) if callable(query) else 0
            except (TypeError, ValueError):
                return 0

        if not is_grave_key(
            key_code=code,
            unicode_key=raw("GetUnicodeKey"),
            raw_key_code=raw("GetRawKeyCode"),
            raw_key_flags=raw("GetRawKeyFlags"),
        ):
            return False
        if not self._wordpress_key_bindings():
            return False  # the WordPress area is switched off: not our key
        self._announce(layer.start())
        return True

    def _wordpress_key_bindings(self) -> dict[str, str]:
        """Each WordPress handler's key as the command table resolves it now."""
        from quill.core.lite.keymap import resolved_commands

        app = self.app
        return {
            handler: key
            for _menu, _label, key, handler, kind in resolved_commands(
                app.feature_enabled, getattr(app, "keymap", None)
            )
            if handler.startswith("cmd_wp_") and kind not in {"sep", "sub"}
        }

    def _wordpress(self) -> Any:
        commands = getattr(self, "_wordpress_commands", None)
        if commands is None:
            from quill.ui.wordpress_commands import WordPressCommands

            commands = WordPressCommands(LiteWordPressHost(self))
            self._wordpress_commands = commands
        return commands

    def cmd_wp_new_page(self) -> None:
        """File > WordPress > New Page."""
        self._wordpress().cmd_new_page()

    def cmd_wp_new_post(self) -> None:
        """File > WordPress > New Post."""
        self._wordpress().cmd_new_post()

    def cmd_wp_open(self) -> None:
        """File > WordPress > Open Page or Post."""
        self._wordpress().cmd_open()

    def cmd_wp_open_by_address(self) -> None:
        """File > WordPress > Open by Web Address."""
        self._wordpress().cmd_open_by_address()

    def cmd_wp_open_local_draft(self) -> None:
        """File > WordPress > Open Local Draft."""
        self._wordpress().cmd_open_local_draft()

    def cmd_wp_save_draft(self) -> None:
        """File > WordPress > Save Draft to Site."""
        self._wordpress().cmd_save_draft()

    def cmd_wp_publish(self) -> None:
        """File > WordPress > Publish or Update."""
        self._wordpress().cmd_publish()

    def cmd_wp_schedule(self) -> None:
        """File > WordPress > Schedule Publish."""
        self._wordpress().cmd_schedule()

    def cmd_wp_open_on_site(self) -> None:
        """File > WordPress > Open on Site."""
        self._wordpress().cmd_open_on_site()

    def cmd_wp_copy_address(self) -> None:
        """File > WordPress > Copy Address."""
        self._wordpress().cmd_copy_address()

    def cmd_wp_properties(self) -> None:
        """File > WordPress > Properties."""
        self._wordpress().cmd_properties()

    def cmd_wp_versions(self) -> None:
        """File > WordPress > Previous Versions."""
        self._wordpress().cmd_versions()

    def cmd_wp_compare(self) -> None:
        """File > WordPress > Compare with Site."""
        self._wordpress().cmd_compare()

    def cmd_wp_trash(self) -> None:
        """File > WordPress > Move to Trash."""
        self._wordpress().cmd_trash()

    def cmd_wp_switch_site(self) -> None:
        """File > WordPress > Switch Site."""
        self._wordpress().cmd_switch_site()

    def cmd_wp_sites(self) -> None:
        """File > WordPress > Sites."""
        self._wordpress().cmd_sites()

    def cmd_wp_connect(self) -> None:
        """File > WordPress > Connect a Site."""
        self._wordpress().cmd_connect()

    def cmd_wp_next_block(self) -> None:
        """Edit > WordPress > Next Block."""
        self._wordpress().cmd_next_block()

    def cmd_wp_previous_block(self) -> None:
        """Edit > WordPress > Previous Block."""
        self._wordpress().cmd_previous_block()

    def cmd_wp_where_am_i(self) -> None:
        """Edit > WordPress > Where Am I."""
        self._wordpress().cmd_where_am_i()

    def cmd_wp_blocks(self) -> None:
        """View > WordPress Blocks."""
        self._wordpress().cmd_blocks_window()

    def cmd_wp_preview_blocks(self) -> None:
        """View > Preview Blocks."""
        self._wordpress().cmd_preview_blocks()

    def cmd_wp_play_media_here(self) -> None:
        """View > Play Media Here."""
        self._wordpress().cmd_play_media_here()

    def cmd_wp_insert_block(self) -> None:
        """Insert > WordPress Block."""
        self._wordpress().cmd_insert_block()

    def cmd_wp_insert_from_library(self) -> None:
        """Insert > Picture from the Media Library."""
        self._wordpress().cmd_insert_from_library()

    def cmd_wp_insert_picture(self) -> None:
        """Insert > Picture from This Computer."""
        self._wordpress().cmd_insert_picture()

    def cmd_wp_insert_link(self) -> None:
        """Insert > Link to a Page on This Site."""
        self._wordpress().cmd_insert_link()

    def cmd_wp_picture_maker(self) -> None:
        """Insert > Make a Picture."""
        self._wordpress().cmd_picture_maker()

    def cmd_wp_block_settings(self) -> None:
        """Format > WordPress > Block Settings."""
        self._wordpress().cmd_block_settings()

    def cmd_wp_image_size(self) -> None:
        """Format > WordPress > Image Size."""
        self._wordpress().cmd_image_size()

    def cmd_wp_mark_language(self) -> None:
        """Format > WordPress > Mark Language."""
        self._wordpress().cmd_mark_language()

    def cmd_wp_check(self) -> None:
        """Tools > WordPress > Check Before Publishing."""
        self._wordpress().cmd_check()

    def cmd_wp_check_page(self) -> None:
        """Tools > WordPress > Check This Page."""
        self._wordpress().cmd_check_page()

    def cmd_wp_check_site(self) -> None:
        """Tools > WordPress > Check the Whole Site."""
        self._wordpress().cmd_check_site()

    def cmd_wp_undo_site_fix(self) -> None:
        """Tools > WordPress > Undo Site Fix."""
        self._wordpress().cmd_undo_site_fix()

    def cmd_wp_site_find_replace(self) -> None:
        """Tools > WordPress > Site-wide Find and Replace."""
        self._wordpress().cmd_site_find_replace()

    def cmd_wp_accessibility_statement(self) -> None:
        """Tools > WordPress > Write an Accessibility Statement."""
        self._wordpress().cmd_accessibility_statement()

    def cmd_wp_palette_report(self) -> None:
        """Tools > WordPress > Palette Report."""
        self._wordpress().cmd_palette_report()

    def cmd_wp_in_short(self) -> None:
        """Tools > WordPress > In Short."""
        self._wordpress().cmd_in_short()

    def cmd_wp_media_library(self) -> None:
        """Tools > WordPress > Media Library."""
        self._wordpress().cmd_media_library()

    def cmd_wp_alt_text_review(self) -> None:
        """Tools > WordPress > Alt Text Review."""
        self._wordpress().cmd_alt_text_review()

    def cmd_wp_visual_review(self) -> None:
        """Tools > WordPress > Visual Review."""
        self._wordpress().cmd_visual_review()

    def cmd_wp_upload_files(self) -> None:
        """Tools > WordPress > More Media > Upload Files."""
        self._wordpress().cmd_upload_files()

    def cmd_wp_upload_from_address(self) -> None:
        """Tools > WordPress > More Media > Upload from Web Address."""
        self._wordpress().cmd_upload_from_address()

    def cmd_wp_paste_image(self) -> None:
        """Tools > WordPress > More Media > Paste Image."""
        self._wordpress().cmd_paste_image()

    def cmd_wp_smaller_copy(self) -> None:
        """Tools > WordPress > More Media > Make a Smaller Copy."""
        self._wordpress().cmd_smaller_copy()

    def cmd_wp_site_logo(self) -> None:
        """Tools > WordPress > More Media > Site Logo."""
        self._wordpress().cmd_site_logo()

    def cmd_wp_preview_and_review(self) -> None:
        """Tools > WordPress > More Media > Preview and Review."""
        self._wordpress().cmd_preview_and_review()

    def cmd_wp_captions(self) -> None:
        """Tools > WordPress > More Media > Captions for Video."""
        self._wordpress().cmd_captions()

    def cmd_wp_transcript(self) -> None:
        """Tools > WordPress > More Media > Transcript for Audio."""
        self._wordpress().cmd_transcript()

    def cmd_wp_listening_version(self) -> None:
        """Tools > WordPress > More Media > Make a Listening Version."""
        self._wordpress().cmd_listening_version()

    def cmd_wp_name_embeds(self) -> None:
        """Tools > WordPress > More Media > Name Embeds."""
        self._wordpress().cmd_name_embeds()

    def cmd_wp_document_as_page(self) -> None:
        """Tools > WordPress > More Media > Publish a Document as a Page."""
        self._wordpress().cmd_document_as_page()

    def cmd_wp_comments(self) -> None:
        """Tools > WordPress > Comments."""
        self._wordpress().cmd_comments()

    def cmd_wp_manage_terms(self) -> None:
        """Tools > WordPress > Categories and Tags."""
        self._wordpress().cmd_manage_terms()

    def cmd_wp_menus(self) -> None:
        """Tools > WordPress > Menus."""
        self._wordpress().cmd_menus()

    def cmd_wp_site_check(self) -> None:
        """Tools > WordPress > Site Check."""
        self._wordpress().cmd_site_check()

    def cmd_wp_site_settings(self) -> None:
        """Tools > WordPress > Site Settings."""
        self._wordpress().cmd_site_settings()

    def cmd_wp_users(self) -> None:
        """Tools > WordPress > Manage > Users."""
        self._wordpress().cmd_users()

    def cmd_wp_app_passwords(self) -> None:
        """Tools > WordPress > Manage > Application Passwords."""
        self._wordpress().cmd_app_passwords()

    def cmd_wp_plugins(self) -> None:
        """Tools > WordPress > Manage > Plugins."""
        self._wordpress().cmd_plugins()

    def cmd_wp_themes(self) -> None:
        """Tools > WordPress > Manage > Themes."""
        self._wordpress().cmd_themes()

    def cmd_wp_fonts(self) -> None:
        """Tools > WordPress > Manage > Fonts."""
        self._wordpress().cmd_fonts()

    def cmd_wp_synced_patterns(self) -> None:
        """Tools > WordPress > Manage > Synced Patterns."""
        self._wordpress().cmd_synced_patterns()

    def cmd_wp_widgets(self) -> None:
        """Tools > WordPress > Manage > Widgets."""
        self._wordpress().cmd_widgets()

    def cmd_wp_site_map(self) -> None:
        """Tools > WordPress > Manage > Site Map."""
        self._wordpress().cmd_site_map()

    def cmd_wp_template_outline(self) -> None:
        """Tools > WordPress > Manage > Template Outline."""
        self._wordpress().cmd_template_outline()

    def cmd_wp_bulk_edit(self) -> None:
        """Tools > WordPress > Manage > Bulk Edit."""
        self._wordpress().cmd_bulk_edit()

    def cmd_wp_page_order(self) -> None:
        """Tools > WordPress > Manage > Page Order."""
        self._wordpress().cmd_page_order()

    def cmd_wp_sign_out(self) -> None:
        """Tools > WordPress > Manage > Sign Out This Site."""
        self._wordpress().cmd_sign_out()

    def cmd_wp_custom_fields(self) -> None:
        """File > WordPress > Custom Fields."""
        self._wordpress().cmd_custom_fields()

    def cmd_wp_notes(self) -> None:
        """View > Block Notes."""
        self._wordpress().cmd_notes()

    def cmd_wp_add_note(self) -> None:
        """Insert > Note on This Block."""
        self._wordpress().cmd_add_note()

    def cmd_wp_library_alt_text(self) -> None:
        """Tools > WordPress > Alt Text for the Whole Library."""
        self._wordpress().cmd_library_alt_text()

    def cmd_wp_edit_picture_on_site(self) -> None:
        """Tools > WordPress > More Media > Edit a Picture on the Site."""
        self._wordpress().cmd_edit_picture_on_site()

    def cmd_wp_send_document(self) -> None:
        """File > WordPress > Send and Copy > Send This Document to WordPress."""
        self._wordpress().cmd_send_document()

    def cmd_wp_publish_elsewhere(self) -> None:
        """File > WordPress > Send and Copy > Publish to Another Site."""
        self._wordpress().cmd_publish_elsewhere()

    def cmd_wp_duplicate(self) -> None:
        """File > WordPress > Send and Copy > Duplicate."""
        self._wordpress().cmd_duplicate()

    def cmd_wp_send_folder(self) -> None:
        """File > WordPress > Send and Copy > Send a Folder as Drafts."""
        self._wordpress().cmd_send_folder()

    def cmd_wp_download_writing(self) -> None:
        """File > WordPress > Send and Copy > Download My Writing."""
        self._wordpress().cmd_download_writing()

    def cmd_wp_hear_link(self) -> None:
        """Edit > WordPress > Hear Where a Link Goes."""
        self._wordpress().cmd_hear_link()

    def cmd_wp_fix_link_text(self) -> None:
        """Edit > WordPress > Fix Link Text."""
        self._wordpress().cmd_fix_link_text()

    def cmd_wp_insert_icon(self) -> None:
        """Insert > WordPress Icon."""
        self._wordpress().cmd_insert_icon()

    def cmd_wp_upload_large_file(self) -> None:
        """Tools > WordPress > More Media > Upload a Large File."""
        self._wordpress().cmd_upload_large_file()

    def cmd_wp_regenerate_sizes(self) -> None:
        """Tools > WordPress > More Media > Regenerate Sizes."""
        self._wordpress().cmd_regenerate_sizes()

    def cmd_wp_menu_history(self) -> None:
        """Tools > WordPress > Menu History."""
        self._wordpress().cmd_menu_history()

    def cmd_wp_previous_looks(self) -> None:
        """Tools > WordPress > Manage > Previous Looks."""
        self._wordpress().cmd_previous_looks()

    def cmd_wp_site_space(self) -> None:
        """Tools > WordPress > Manage > Space Used."""
        self._wordpress().cmd_site_space()

    def cmd_wp_download_design(self) -> None:
        """Tools > WordPress > Manage > Download a Copy of the Site's Design."""
        self._wordpress().cmd_download_design()

    def cmd_wp_coming_up(self) -> None:
        """Tools > WordPress > Your Sites > Coming Up."""
        self._wordpress().cmd_coming_up()

    def cmd_wp_what_changed(self) -> None:
        """Tools > WordPress > Your Sites > What Changed on My Sites."""
        self._wordpress().cmd_what_changed()

    def cmd_wp_plugin_fields(self) -> None:
        """File > WordPress > Plugin Fields."""
        self._wordpress().cmd_plugin_fields()

    def cmd_wp_style_variations(self) -> None:
        """Tools > WordPress > Design > Style Variations."""
        self._wordpress().cmd_style_variations()

    def cmd_wp_site_styles(self) -> None:
        """Tools > WordPress > Design > Site Styles."""
        self._wordpress().cmd_site_styles()

    def cmd_wp_events_coming_up(self) -> None:
        """Tools > WordPress > Plugin Extras > Events Coming Up."""
        self._wordpress().cmd_events_coming_up()

    def cmd_wp_new_event(self) -> None:
        """Tools > WordPress > Plugin Extras > New Event."""
        self._wordpress().cmd_new_event()

    def cmd_wp_shop_orders(self) -> None:
        """Tools > WordPress > Plugin Extras > Shop Orders."""
        self._wordpress().cmd_shop_orders()

    def cmd_wp_abilities(self) -> None:
        """Tools > WordPress > Manage > AI Abilities."""
        self._wordpress().cmd_abilities()

    def cmd_wp_ask_site(self) -> None:
        """Tools > WordPress > Manage > Ask the Site."""
        self._wordpress().cmd_ask_site()
