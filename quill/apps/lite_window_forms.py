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

    def cmd_forms_responses(self) -> None:
        """Tools > Forms > Responses."""
        self._forms().cmd_responses()
