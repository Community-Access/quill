"""QUILL Lite's door to the shared Forms commands (wordpress.md 17a.10).

An adapter with no commands of its own: each ``cmd_forms_*`` below hands
straight to the shared :class:`~quill.ui.forms_commands.FormsCommands`, the
same object QUILL's ``main_frame_forms.py`` reaches. The rows come from
:data:`quill.core.forms.menu.PLACES`, so the two editors' menus match. The
window is reached through
:class:`~quill.apps.lite_window_wordpress_host.LiteWordPressHost`, which is
already a Lite window as a shared command sees it.
"""

from __future__ import annotations

from typing import Any

__all__ = ["DocumentFormsMixin"]


class DocumentFormsMixin:
    """The Forms rows in a QUILL Lite window (wordpress.md 17a.10)."""

    def _sync_forms_items(self) -> None:
        """Dim the form commands unless this window holds a form document."""
        from quill.core.forms.menu import DOCUMENT_ONLY, all_rows, is_form_path, lite_handler

        items = getattr(self, "_menu_items", {})
        is_form = is_form_path(getattr(self, "path", None))
        for _path, (command_id, _title, handler) in all_rows():
            item = items.get(lite_handler(command_id))
            if handler in DOCUMENT_ONLY and item is not None:
                item.Enable(is_form)

    def _forms(self) -> Any:
        commands = getattr(self, "_forms_commands", None)
        if commands is None:
            from quill.apps.lite_window_wordpress_host import LiteWordPressHost
            from quill.ui.forms_commands import FormsCommands

            commands = FormsCommands(LiteWordPressHost(self))
            self._forms_commands = commands
        return commands

    def cmd_forms_new_form(self) -> None:
        """File > New Form."""
        self._forms().cmd_new_form()

    def cmd_forms_insert_field(self) -> None:
        """Insert > Form Field."""
        self._forms().cmd_insert_field()

    def cmd_forms_outline(self) -> None:
        """View > Form Outline."""
        self._forms().cmd_outline()

    def cmd_forms_rules(self) -> None:
        """Format > Form Rules."""
        self._forms().cmd_rules()

    def cmd_forms_check(self) -> None:
        """Tools > Forms > Check This Form."""
        self._forms().cmd_check()

    def cmd_forms_fill_in(self) -> None:
        """Tools > Forms > Fill It In Yourself."""
        self._forms().cmd_fill_in()

    def cmd_forms_properties(self) -> None:
        """Tools > Forms > Form Properties."""
        self._forms().cmd_properties()

    def cmd_forms_payments_setup(self) -> None:
        """Tools > Forms > Form Payments Setup."""
        self._forms().cmd_payments_setup()

    def cmd_forms_insert_payment(self) -> None:
        """Tools > Forms > Insert Payment Field."""
        self._forms().cmd_insert_payment()

    def cmd_forms_verify_payments(self) -> None:
        """Tools > Forms > Verify Payment Setup."""
        self._forms().cmd_verify_payments()

    def cmd_forms_responses(self) -> None:
        """Tools > Forms > Responses."""
        self._forms().cmd_form_responses()

    def cmd_forms_publish(self) -> None:
        """Tools > Forms > Publish Form."""
        self._forms().cmd_publish_form()

    def cmd_forms_insert_into_page(self) -> None:
        """Tools > Forms > Insert Form Into Page."""
        self._forms().cmd_insert_into_page()

    def cmd_forms_test_on_site(self) -> None:
        """Tools > Forms > Test on Site."""
        self._forms().cmd_test_on_site()

    def cmd_forms_save_web_page(self) -> None:
        """Tools > Forms > Save As Web Page."""
        self._forms().cmd_save_web_page()

    def cmd_forms_save_word(self) -> None:
        """Tools > Forms > Save As Word Document."""
        self._forms().cmd_save_word()

    def cmd_forms_save_large_print(self) -> None:
        """Tools > Forms > Save As Large Print."""
        self._forms().cmd_save_large_print()

    def cmd_forms_save_braille(self) -> None:
        """Tools > Forms > Save As Braille-Ready Text."""
        self._forms().cmd_save_braille()

    def cmd_forms_draft(self) -> None:
        """Tools > Forms > Draft a Form."""
        self._forms().cmd_draft_form()

    def cmd_forms_plain_language(self) -> None:
        """Tools > Forms > Plain Language."""
        self._forms().cmd_plain_language()

    def cmd_forms_suggest_autofill(self) -> None:
        """Tools > Forms > Suggest Autofill Hints."""
        self._forms().cmd_suggest_autofill()
