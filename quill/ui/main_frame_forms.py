"""QUILL's door to the shared Forms commands (wordpress.md 17a.10).

An adapter with no commands of its own, the shape of ``main_frame_wordpress.py``:
:class:`FormsMenuMixin` puts the rows of :data:`quill.core.forms.menu.PLACES`
in File, Insert, View, Format and Tools, registers each as a palette command
and binds it. Every ``cmd_*`` that runs is in :mod:`quill.ui.forms_commands`,
which QUILL Lite reaches too -- a test asserts this module defines none,
because a second implementation is how the two editors drift. The editor is
reached through :class:`~quill.ui.main_frame_wordpress.QuillWordPressHost`,
which is already the main frame as a shared command sees it.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms.menu import DOCUMENT_ONLY, PLACES, Submenu, all_rows, is_form_path

_FEATURE = "core.forms"


class FormsMenuMixin:
    def _forms(self) -> Any:
        commands = getattr(self, "_forms_commands", None)
        if commands is None:
            from quill.ui.forms_commands import FormsCommands
            from quill.ui.main_frame_wordpress import QuillWordPressHost

            commands = FormsCommands(QuillWordPressHost(self))
            self._forms_commands = commands
        return commands

    def _forms_menu_ids(self) -> dict[str, int]:
        ids = getattr(self, "_forms_ids", None)
        if ids is None:
            import wx

            # Keep the refs: wx releases an id when its WindowIDRef is collected.
            refs = {row[0]: wx.NewIdRef() for _sub, row in all_rows()}
            self._forms_id_refs = refs
            ids = {command_id: int(ref) for command_id, ref in refs.items()}
            self._forms_ids = ids
        return ids

    def _append_forms_new_row(self, file_menu: Any) -> None:
        """File > New Form, beside the other New rows, when Forms is on."""
        if self._feature_enabled(_FEATURE):  # type: ignore[attr-defined]
            self._fill_forms_menu(file_menu, PLACES["file"][1])

    def _place_forms_rows(self, menus: dict[str, Any]) -> None:
        """The rows at the foot of Insert, View, Format and Tools (17a.10).

        *menus* maps a place in :data:`PLACES` to the built ``wx.Menu``; a place
        Forms does not use is ignored.
        """
        if not self._feature_enabled(_FEATURE):  # type: ignore[attr-defined]
            return
        for place, menu in menus.items():
            if place in PLACES and place != "file" and menu is not None:
                self._fill_forms_menu(menu, PLACES[place][1])

    def _refresh_forms_menu_items(self, menu_bar: Any) -> None:
        """Enable the form commands only while a form document is in front.

        Elsewhere they are dimmed; reached another way (the Command Palette),
        the command itself says why.
        """
        ids = getattr(self, "_forms_ids", None)
        if not ids or menu_bar is None:
            return
        try:
            is_form = is_form_path(getattr(getattr(self, "document", None), "path", None))
        except Exception:  # noqa: BLE001 - a menu refresh must never raise
            is_form = False
        for _path, (command_id, _title, handler) in all_rows():
            if handler in DOCUMENT_ONLY and command_id in ids:
                item = menu_bar.FindItemById(ids[command_id])
                if item is not None:
                    item.Enable(is_form)

    def _fill_forms_menu(self, menu: Any, rows: tuple[Any, ...]) -> Any:
        """Put *rows* in *menu*, nesting each :class:`Submenu` as it comes."""
        import wx

        ids = self._forms_menu_ids()
        for row in rows:
            if row is None:
                menu.AppendSeparator()
                continue
            if isinstance(row, Submenu):
                menu.AppendSubMenu(self._fill_forms_menu(wx.Menu(), row.rows), row.title)
                continue
            command_id, title, handler = row
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                title.replace("&", "").removesuffix("..."),
                (lambda h=handler: getattr(self._forms(), h)()),
                self._binding_for(command_id),  # type: ignore[attr-defined]
            )
            menu.Append(ids[command_id], self._menu_label(title, command_id))  # type: ignore[attr-defined]
            self.frame.Bind(  # type: ignore[attr-defined]
                wx.EVT_MENU,
                lambda _e, h=handler: getattr(self._forms(), h)(),
                id=ids[command_id],
            )
        return menu

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        if getattr(self, "_forms_ids", None):
            mapping.update(self._forms_ids)
        return mapping
