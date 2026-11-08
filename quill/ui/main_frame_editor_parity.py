"""QUILL's half of Paste Copied Files and the saved replace jobs: the rows and the hooks.

No commands of its own. Paste Copied Files is :class:`quill.ui.paste_file.PasteFileMixin`'s
and Run Replace Job and Manage Replace Jobs are
:class:`quill.ui.replace_jobs.ReplaceJobsMixin`'s -- the same handlers QUILL Lite's
command table names, so the two editors cannot do one of these two ways (rule
10). A test asserts this module defines no ``cmd_*``.

What lives here:

- **Where the rows are.** Paste Copied Files is at the foot of Edit > Clipboard, which
  :mod:`quill.ui.main_frame_say_commands` builds just before this mixin's
  Forms hook runs. The
  two replace-job rows follow Multi Replace and Count Occurrences, at the foot
  of the search tools, placed from the hook the menu builder already calls with
  that menu (``main_frame_menu.py`` is at its GATE-11 ceiling).
- **Open Keyboard Reference shows its key.** Its row was a literal label in
  ``main_frame_menu.py``; it is relabelled through ``_menu_label`` from the
  What's New hook, beside it in Help, so the label follows a rebinding.
- **The hooks QUILL answers differently:** speech through ``_announce`` with
  ``force``; windows through ``_show_modal_dialog``; text through
  ``_atomic_replace``, one undo step over the span that changed; the jobs file
  in QUILL's own data folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.paste_file import PasteFileMixin
from quill.ui.replace_jobs import ReplaceJobsMixin

__all__ = ["PASTE_FILE_ROW", "REPLACE_JOB_ROWS", "EditorParityAdapterMixin"]

#: Paste Copied Files, at the foot of the Edit > Clipboard submenu the Say rows build.
PASTE_FILE_ROW: tuple[str, str, str] = (
    "edit.paste_file",
    "Paste Copie&d Files...",
    "cmd_paste_file",
)

#: ``(command id, label, shared handler)``, in menu order, after Count Occurrences.
REPLACE_JOB_ROWS: tuple[tuple[str, str, str], ...] = (
    ("edit.run_replace_job", "Run Replace &Job...", "cmd_run_replace_job"),
    ("edit.manage_replace_jobs", "Ma&nage Replace Jobs...", "cmd_manage_replace_jobs"),
)


class EditorParityAdapterMixin(PasteFileMixin, ReplaceJobsMixin):
    """Places the shared rows in QUILL's menus and answers their hooks."""

    # -- the rows ----------------------------------------------------------- #

    def _parity_menu_ids(self) -> dict[str, int]:
        ids = getattr(self, "_parity_ids", None)
        if ids is None:
            import wx

            # Keep the refs: wx releases an id when its WindowIDRef is collected.
            rows = (PASTE_FILE_ROW, *REPLACE_JOB_ROWS)
            refs = {cid: wx.NewIdRef() for cid, _label, _handler in rows}
            self._parity_id_refs = refs
            ids = {command_id: int(ref) for command_id, ref in refs.items()}
            self._parity_ids = ids
        return ids

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        if getattr(self, "_parity_ids", None):
            mapping.update(self._parity_ids)
        return mapping

    def _parity_row(self, menu: Any, row: tuple[str, str, str]) -> None:
        import wx

        from quill.core.i18n import _

        command_id, label, handler_name = row
        menu_id = self._parity_menu_ids()[command_id]
        handler = getattr(self, handler_name)
        self.commands.try_register(  # type: ignore[attr-defined]
            command_id,
            label.replace("&", "").removesuffix("..."),
            handler,
            self._binding_for(command_id),  # type: ignore[attr-defined]
        )
        menu.Append(menu_id, self._menu_label(_(label), command_id))  # type: ignore[attr-defined]
        # Bound once: a rebuilt menu bar reuses the ids, and a second binding
        # would run the command twice.
        wired: set[str] = self.__dict__.setdefault("_parity_rows_wired", set())
        if command_id not in wired:
            wired.add(command_id)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=menu_id)  # type: ignore[attr-defined]

    def _append_power_tools_search_items(self, search_menu: Any) -> None:
        """The search tools, then Run Replace Job and Manage Replace Jobs."""
        super()._append_power_tools_search_items(search_menu)  # type: ignore[misc]
        search_menu.AppendSeparator()
        for row in REPLACE_JOB_ROWS:
            self._parity_row(search_menu, row)

    def _place_forms_rows(self, menus: dict[str, Any]) -> None:
        """Paste Copied Files at the foot of Edit > Clipboard, then the Forms rows."""
        clipboard = getattr(self, "_say_clipboard_menu", None)
        if clipboard is not None:
            self._parity_row(clipboard, PASTE_FILE_ROW)
        super()._place_forms_rows(menus)  # type: ignore[misc]

    def _install_whats_new_item(self, help_menu: Any) -> None:
        """Open Keyboard Reference shows its key; then What's New."""
        from quill.core.i18n import _

        menu_id = getattr(self, "_id_open_keyboard_reference", None)
        if menu_id is not None:
            label = self._menu_label(  # type: ignore[attr-defined]
                _("Open Keyboard &Reference"), "tools.open_keyboard_reference"
            )
            try:
                help_menu.SetLabel(int(menu_id), label)
            except Exception:  # noqa: BLE001 - a relabel must never cost the Help menu
                pass
        super()._install_whats_new_item(help_menu)  # type: ignore[misc]

    # -- Paste Copied Files: the hooks -------------------------------------- #

    def _paste_file_say(self, message: str) -> None:
        self._announce(message, force=True)  # type: ignore[attr-defined]

    def _paste_file_parent(self) -> Any:
        return self.frame  # type: ignore[attr-defined]

    def _paste_file_show_modal(self, dialog: Any, title: str) -> int:
        return int(self._show_modal_dialog(dialog, title))  # type: ignore[attr-defined]

    def _paste_file_read_only(self) -> bool:
        return bool(self._document_is_read_only())  # type: ignore[attr-defined]

    def _paste_file_insert(self, text: str) -> None:
        start, end = self.editor.GetSelection()  # type: ignore[attr-defined]
        self._atomic_replace(start, end, text)  # type: ignore[attr-defined]
        self.editor.SetInsertionPoint(start + len(text))  # type: ignore[attr-defined]
        self.document.set_text(self.editor.GetValue())  # type: ignore[attr-defined]
        self.editor.SetFocus()  # type: ignore[attr-defined]

    # -- the replace jobs' hooks -------------------------------------------- #

    def _replace_jobs_dir(self) -> Path:
        from quill.core.paths import app_data_dir

        return Path(app_data_dir())

    def _replace_jobs_say(self, message: str) -> None:
        self._announce(message, force=True)  # type: ignore[attr-defined]

    def _replace_jobs_parent(self) -> Any:
        return self.frame  # type: ignore[attr-defined]

    def _replace_jobs_show_modal(self, dialog: Any, title: str) -> int:
        return int(self._show_modal_dialog(dialog, title))  # type: ignore[attr-defined]

    def _replace_jobs_read_only(self) -> bool:
        return bool(self._document_is_read_only())  # type: ignore[attr-defined]

    def _replace_jobs_span(self) -> tuple[str, int, int, bool]:
        text = str(self.editor.GetValue())  # type: ignore[attr-defined]
        start, end = self.editor.GetSelection()  # type: ignore[attr-defined]
        in_selection = end > start
        if not in_selection:
            start, end = 0, len(text)
        return text[start:end], int(start), int(end), in_selection

    def _replace_jobs_confirm_whole(self) -> bool:
        return bool(self._confirm_whole_document_rewrite())  # type: ignore[attr-defined]

    def _replace_jobs_write(self, start: int, end: int, text: str) -> None:
        self._atomic_replace(start, end, text)  # type: ignore[attr-defined]
        self.document.set_text(self.editor.GetValue())  # type: ignore[attr-defined]
        self.editor.SetSelection(start, start + len(text))  # type: ignore[attr-defined]

    def _replace_jobs_focus(self) -> None:
        self.editor.SetFocus()  # type: ignore[attr-defined]
