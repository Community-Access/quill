"""QUILL's half of the Say commands: where the rows sit, and the hooks that differ.

No commands of its own. Say Clipboard, Append Selection to Clipboard, Save
Clipboard to File, Clear Clipboard, Say Time and Date, Say Windows Open and
Copy Log are :class:`quill.ui.say_commands.SayCommandsMixin`'s, the same
handlers QUILL Lite's command table names, on the same keys -- so the two
editors cannot do one of these two ways (rule 10). A test asserts this module
defines no ``cmd_*``.

What lives here:

- **Where the rows are.** The four clipboard rows in a Clipboard submenu of
  Edit, after Copy With Attribution; Say Time and Date in Navigate, beside the
  other things QUILL speaks on request (Speak Window Title, Speak Status
  Summary); Say Windows Open in Window, after Close Other Documents; Copy Log in
  Help, after Save Diagnostics, where somebody writing to support already is.
  Each shows its key through ``_menu_label``. They are placed from hooks the
  menu builder already calls with each menu (``main_frame_menu.py`` is at its
  GATE-11 ceiling): Edit and Window from the Forms hook, which runs once every
  menu is built and before the menu customization pass; Navigate from the
  Table submenu's hook; Help from What's New's.
- **The hooks QUILL answers differently:** speech goes through ``_announce``
  with ``force`` (a second Say Time a minute later is a new answer, not a
  repeat to collapse); the documents are the tabs; the log is in QUILL's data
  folder; the two windows go through ``_show_modal_dialog``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.say_commands import SayCommandsMixin

__all__ = ["SAY_ROWS", "SayCommandsAdapterMixin"]

#: ``place -> ((command id, label, shared handler), ...)``, in menu order.
SAY_ROWS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "edit": (
        ("edit.say_clipboard", "Sa&y Clipboard", "cmd_say_clipboard"),
        ("edit.append_to_clipboard", "&Append Selection to Clipboard", "cmd_append_to_clipboard"),
        ("edit.save_clipboard_to_file", "Save Clipboard to &File...", "cmd_save_clipboard"),
        ("edit.clear_clipboard", "Clear Clip&board", "cmd_clear_clipboard"),
    ),
    "navigate": (("navigate.say_time", "Say Time and Date", "cmd_say_time"),),
    "window": (("window.say_windows_open", "Say &Windows Open", "cmd_say_windows_open"),),
    "help": (("help.copy_log", "Copy &Log", "cmd_copy_log"),),
}


class SayCommandsAdapterMixin(SayCommandsMixin):
    """Places the shared Say rows in QUILL's menus and answers their hooks."""

    # -- the rows ----------------------------------------------------------- #

    def _say_menu_ids(self) -> dict[str, int]:
        ids = getattr(self, "_say_ids", None)
        if ids is None:
            import wx

            # Keep the refs: wx releases an id when its WindowIDRef is collected.
            refs = {cid: wx.NewIdRef() for rows in SAY_ROWS.values() for cid, _l, _h in rows}
            self._say_id_refs = refs
            ids = {command_id: int(ref) for command_id, ref in refs.items()}
            self._say_ids = ids
        return ids

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        if getattr(self, "_say_ids", None):
            mapping.update(self._say_ids)
        return mapping

    def _say_row(self, menu: Any, row: tuple[str, str, str], position: int = -1) -> None:
        import wx

        from quill.core.i18n import _

        command_id, label, handler_name = row
        menu_id = self._say_menu_ids()[command_id]
        handler = getattr(self, handler_name)
        self.commands.try_register(  # type: ignore[attr-defined]
            command_id,
            label.replace("&", "").removesuffix("..."),
            handler,
            self._binding_for(command_id),  # type: ignore[attr-defined]
        )
        text = self._menu_label(_(label), command_id)  # type: ignore[attr-defined]
        if position >= 0:
            menu.Insert(position, menu_id, text)
        else:
            menu.Append(menu_id, text)
        # Bound once: a rebuilt menu bar reuses the ids, and a second binding
        # would run the command twice.
        wired: set[str] = self.__dict__.setdefault("_say_rows_wired", set())
        if command_id not in wired:
            wired.add(command_id)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=menu_id)  # type: ignore[attr-defined]

    @staticmethod
    def _say_position_after(menu: Any, menu_id: Any) -> int:
        """The index just after the item with *menu_id*, or -1 to append."""
        try:
            wanted = int(menu_id)
        except (TypeError, ValueError):
            return -1
        for index, item in enumerate(menu.GetMenuItems()):
            if item.GetId() == wanted:
                return index + 1
        return -1

    def _place_forms_rows(self, menus: dict[str, Any]) -> None:
        """Edit > Clipboard and Window > Say Windows Open, then the Forms rows."""
        import wx

        from quill.core.i18n import _

        edit_menu = menus.get("edit")
        if edit_menu is not None:
            clipboard = wx.Menu()
            for row in SAY_ROWS["edit"]:
                self._say_row(clipboard, row)
            # Paste Copied Files follows (main_frame_editor_parity.py), into this submenu.
            self._say_clipboard_menu = clipboard
            after = self._say_position_after(edit_menu, getattr(self, "_id_copy_with_source", None))
            title = _("Clip&board")
            if after >= 0:
                edit_menu.Insert(after, wx.ID_ANY, title, clipboard)
            else:
                edit_menu.AppendSubMenu(clipboard, title)
        self._say_rows_after(
            getattr(self, "_window_menu", None), "_id_close_other_documents", "window"
        )
        super()._place_forms_rows(menus)  # type: ignore[misc]

    def _append_table_submenu(self, navigate_menu: Any) -> None:
        """Navigate > Say Time and Date, after Speak Status Summary; then the Table submenu."""
        self._say_rows_after(navigate_menu, "_id_speak_status_summary", "navigate")
        super()._append_table_submenu(navigate_menu)  # type: ignore[misc]

    def _install_whats_new_item(self, help_menu: Any) -> None:
        """Help > Copy Log, after Save Diagnostics; then What's New."""
        self._say_rows_after(help_menu, "_id_save_diagnostics", "help")
        super()._install_whats_new_item(help_menu)  # type: ignore[misc]

    def _say_rows_after(self, menu: Any, anchor: str, place: str) -> None:
        if menu is None:
            return
        position = self._say_position_after(menu, getattr(self, anchor, None))
        for offset, row in enumerate(SAY_ROWS[place]):
            self._say_row(menu, row, position + offset if position >= 0 else -1)

    # -- the hooks ---------------------------------------------------------- #

    def _say_result(self, message: str) -> None:
        self._announce(message, force=True)  # type: ignore[attr-defined]

    def _say_open_documents(self) -> tuple[list[str], int]:
        tabs = list(getattr(self, "_document_tabs", []))
        names = [str(getattr(getattr(tab, "document", None), "name", "")) for tab in tabs]
        return names, int(getattr(self, "_active_tab_index", -1))

    def _say_log_dir(self) -> Path:
        from quill.core.paths import app_data_dir

        return app_data_dir() / "logs"

    def _say_show_text(self, title: str, text: str) -> None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
        from quill.ui.dpi import dip_size

        dialog = wx.Dialog(
            self.frame,  # type: ignore[attr-defined]
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        try:
            sizer = wx.BoxSizer(wx.VERTICAL)
            label = wx.StaticText(dialog, label="Clipboard &text:")
            sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            field = wx.TextCtrl(
                dialog,
                value=text,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
                name="Clipboard text",
            )
            field.SetHelpText(
                "What is on the clipboard, to read with the arrow keys. Nothing here "
                "changes the clipboard. Escape closes this window."
            )
            sizer.Add(field, 1, wx.EXPAND | wx.ALL, 8)
            close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
            close_btn.SetHelpText("Close this window and go back to your document.")
            buttons = wx.BoxSizer(wx.HORIZONTAL)
            buttons.AddStretchSpacer()
            buttons.Add(close_btn, 0)
            sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            dialog.SetSizer(sizer)
            dialog.SetSize(dip_size(dialog, 640, 480))
            apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
            bind_close_button(dialog, close_btn, modeless=False)
            field.SetFocus()
            field.SetInsertionPoint(0)
            self._show_modal_dialog(dialog, title)  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    def _say_ask_save_path(self, suggested: str) -> Path | None:
        import wx

        dialog = wx.FileDialog(
            self.frame,  # type: ignore[attr-defined]
            "Save Clipboard to File",
            defaultFile=suggested,
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if self._show_modal_dialog(dialog, "Save Clipboard to File") != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()
