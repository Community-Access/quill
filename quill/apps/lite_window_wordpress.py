"""QUILL Lite's door to the shared WordPress commands: File > WordPress (wordpress.md 11).

An adapter with no commands of its own: each ``cmd_wp_*`` below hands straight
to the shared :class:`~quill.ui.wordpress_commands.WordPressCommands`, the same
object QUILL's ``main_frame_wordpress.py`` reaches. The rows come from
:data:`quill.core.wordpress.menu.WORDPRESS_ROWS`, so the two menus match.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any


class LiteWordPressHost:
    """A QUILL Lite document window, as the shared WordPress commands see it."""

    def __init__(self, window: Any) -> None:
        self._w = window

    @property
    def parent(self) -> Any:
        return self._w

    def show_modal(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))

    def announce(self, text: str) -> None:
        self._w._announce(text)

    def run_task(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[BaseException], None],
    ) -> None:
        from quill.apps.lite_window_open import app_task_manager

        app_task_manager(self._w.app).submit(
            name,
            lambda **_kw: func(),
            on_success=lambda _op, result: on_success(result),
            on_failure=lambda _op, exc: on_failure(exc),
        )

    def current_path(self) -> Path | None:
        path = getattr(self._w, "path", None)
        return Path(path) if path else None

    def current_text(self) -> str:
        return str(self._w.control.GetValue())

    def replace_text(self, text: str) -> None:
        control = self._w.control
        control.SetSelection(0, control.GetLastPosition())
        control.WriteText(text)

    def insert_text(self, text: str) -> None:
        self._w.control.WriteText(text)

    def selected_text(self) -> str:
        return str(self._w.control.GetStringSelection())

    def caret_offset(self) -> int:
        return int(self._w.control.GetInsertionPoint())

    def go_to_offset(self, offset: int) -> None:
        control = self._w.control
        control.SetInsertionPoint(offset)
        control.ShowPosition(offset)
        control.SetFocus()

    def open_path(self, path: Path) -> None:
        self._w.app.open_path(path)

    def save_current(self) -> bool:
        self._w.cmd_save()
        control = self._w.control
        is_modified = getattr(control, "IsModified", None)
        return not bool(is_modified()) if callable(is_modified) else True

    def clipboard_text(self) -> str:
        from quill.ui.main_frame_wordpress import read_clipboard_text

        return read_clipboard_text()

    def set_clipboard_text(self, text: str) -> None:
        from quill.ui.main_frame_wordpress import write_clipboard_text

        write_clipboard_text(text)

    def open_in_browser(self, url: str) -> None:
        webbrowser.open(url)

    def clipboard_image_png(self) -> bytes | None:
        from quill.ui.wordpress_media_host import read_clipboard_png

        return read_clipboard_png()

    def ai_describe_image(
        self,
        path: Path,
        question: str,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> bool:
        from quill.ui.wordpress_media_host import ask_editor_ai

        return ask_editor_ai(self._w, path, question, on_done, on_error)

    def ai_editor(self) -> Any:
        return self._w

    def start_repeating(self, seconds: float, callback: Callable[[], None]) -> Callable[[], None]:
        from quill.ui.main_frame_wordpress import start_wx_repeating

        return start_wx_repeating(self._w, seconds, callback)


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
