"""Navigate > Code: indent changes, Check This File and the problem keys.

QUILL's side of three things QUILL Lite has too, over the same shared code:

* **Next / Previous Indent Change** (``quill.core.navigation.indent_change_target``):
  the next line, skipping blanks, whose indentation differs from this one --
  how you get out of a Python block or a YAML mapping without reading it.
* **View > Problems Pane** (:class:`quill.ui.problems_pane.ProblemsPane`):
  the same problems docked under the editor, above the status bar, which F6
  reaches. Built the first time it is shown, so it costs nothing until then.
* **Check This File**, **Next Problem**, **Previous Problem**
  (:class:`quill.ui.problems_commands.ProblemsCommandsMixin`, over
  :mod:`quill.core.problems`). QUILL checks every language it has a checker
  for, including the outside tools on the PATH; QUILL Lite checks the two
  languages it knows, Markdown and HTML.

It also answers the language-aware Next / Previous Block: the block pattern of
the document's language profile (``_block_pattern``).

Host requirements (provided by MainFrame): ``editor``, ``document``,
``_set_status``, ``_announce_navigation_move``, ``_record_location_before_jump``,
``_location_ring``, ``_show_modal_dialog``, ``_task_manager``, ``statusbar``,
``settings``, ``_set_active_region``, ``_copy_text_to_clipboard``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.problems import CheckReport, language_key
from quill.ui.problems_commands import ProblemsCommandsMixin

#: Navigate > Code, top to bottom: ``(command id, menu label, palette label,
#: handler)``. The same rows, letters and keys as QUILL Lite's Navigate > Code.
_CODE_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "navigate.next_indent",
        "Next &Indent Change",
        "Next Indent Change",
        "navigate_next_indent",
    ),
    (
        "navigate.previous_indent",
        "Previous In&dent Change",
        "Previous Indent Change",
        "navigate_previous_indent",
    ),
    ("", "", "", ""),
    ("tools.check_this_file", "&Check This File...", "Check This File...", "tools_check_this_file"),
    ("navigate.next_problem", "Next P&roblem", "Next Problem", "navigate_next_problem"),
    (
        "navigate.previous_problem",
        "Previous Pro&blem",
        "Previous Problem",
        "navigate_previous_problem",
    ),
)


class CodeNavMixin(ProblemsCommandsMixin):
    # Host-provided by MainFrame: type-only annotations, never method stubs,
    # which would shadow the real implementations through the MRO.
    editor: Any
    document: Any
    frame: Any
    _location_ring: Any
    _set_status: Any
    _announce_navigation_move: Any
    _record_location_before_jump: Any
    _show_modal_dialog: Any
    _task_manager: Any
    statusbar: Any
    settings: Any
    _set_active_region: Any
    _copy_text_to_clipboard: Any

    # -- language-aware blocks ------------------------------------------------ #

    def _current_language_profile(self) -> Any:
        from quill.core.language_profile import get_profile_for_path

        tab = getattr(self, "_current_tab", None)
        profile = getattr(tab, "_language_profile", None)
        if profile is None:
            profile = get_profile_for_path(getattr(self.document, "path", None))
        return profile

    def _block_pattern(self) -> str:
        """The current document's block pattern; empty means paragraphs."""
        return str(getattr(self._current_language_profile(), "block_pattern", "") or "")

    # -- Next / Previous Indent Change --------------------------------------- #

    def navigate_next_indent(self) -> None:
        self._navigate_indent(forward=True)

    def navigate_previous_indent(self) -> None:
        self._navigate_indent(forward=False)

    def _navigate_indent(self, *, forward: bool) -> None:
        from quill.core.navigation import describe_indent, indent_change_target

        text = self.editor.GetValue()
        tab_size = int(getattr(self._current_language_profile(), "indent_unit", 4) or 4)
        target = indent_change_target(
            text, self.editor.GetInsertionPoint(), forward=forward, tab_size=max(tab_size, 1)
        )
        if target is None:
            self._set_status(
                "No change of indent below" if forward else "No change of indent above"
            )
            return
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(target)
        self.editor.SetSelection(target, target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        self._announce_navigation_move(describe_indent(text, target).capitalize(), target)

    # -- Check This File and the problem keys -------------------------------- #

    def tools_check_this_file(self) -> None:
        self._check_this_file()

    def navigate_next_problem(self) -> None:
        self._step_problem(forward=True)

    def navigate_previous_problem(self) -> None:
        self._step_problem(forward=False)

    def _problems_text(self) -> str:
        return str(self.editor.GetValue())

    def _problems_caret(self) -> int:
        return int(self.editor.GetInsertionPoint())

    def _problems_path(self) -> Path | None:
        return getattr(self.document, "path", None)

    def _problems_language(self) -> str:
        return language_key(
            getattr(self._current_language_profile(), "name", None), self._problems_path()
        )

    def _problems_modified(self) -> bool:
        return bool(getattr(self.document, "modified", True))

    def _problems_outside_allowed(self) -> bool:
        return True

    def _problems_go_to(self, offset: int) -> None:
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(offset)
        self.editor.SetSelection(offset, offset)
        self.editor.SetFocus()
        self._location_ring.record(offset)

    def _problems_say(self, message: str) -> None:
        self._set_status(message)

    def _problems_choose(self, summary: str, rows: list[str]) -> int | None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids

        with wx.SingleChoiceDialog(
            self.frame,
            f"{summary} Choose a problem to go to it:",
            "Problems",
            choices=rows,
        ) as dialog:
            dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Problems") != wx.ID_OK:
                return None
            return int(dialog.GetSelection())

    def _problems_in_background(
        self, work: Callable[[], CheckReport], done: Callable[[CheckReport], None]
    ) -> None:
        manager = getattr(self, "_task_manager", None)
        if manager is None:
            done(work())
            return
        manager.submit(
            name="check-this-file",
            func=lambda **_kwargs: work(),
            on_success=lambda _op, report: done(report),
            on_failure=lambda _op, error: self._set_status(f"Check This File failed: {error}"),
        )

    # -- the Problems pane ---------------------------------------------------- #

    def view_toggle_problems_pane(self) -> None:
        self._toggle_problems_pane()

    def _problems_pane(self, *, create: bool) -> Any:
        pane = getattr(self, "_problems_pane_widget", None)
        if pane is not None or not create:
            return pane
        import wx

        from quill.ui.dpi import dip_size
        from quill.ui.problems_pane import ProblemsPane

        pane = ProblemsPane(
            wx,
            self.frame,
            go_to=self._problems_pane_go_to,
            back_to_editor=self._problems_back_to_editor,
            copy_text=self._problems_copy,
            say=self._problems_say,
            tick=self._problems_tick,
            pause_enabled=self._problems_pause_enabled(),
            set_pause_enabled=self._problems_set_pause_enabled,
        )
        pane.panel.SetMinSize(dip_size(pane.panel, -1, 140))
        pane.panel.Hide()
        sizer = self.frame.GetSizer()
        # Under the editor and Reveal Codes, above the status bar: where F6
        # finds it, because the ring is in screen order.
        index = sizer.GetItemCount()
        for position in range(sizer.GetItemCount()):
            if sizer.GetItem(position).GetWindow() is self.statusbar:
                index = position
                break
        sizer.Insert(index, pane.panel, 0, wx.EXPAND)
        self._problems_pane_widget = pane
        return pane

    def _problems_pane_is_shown(self) -> bool:
        pane = self._problems_pane(create=False)
        return pane is not None and pane.is_shown()

    def _is_problems_panel(self, window: Any) -> bool:
        pane = self._problems_pane(create=False)
        return pane is not None and window is pane.panel

    def _focus_problems_pane(self) -> None:
        pane = self._problems_pane(create=False)
        if pane is not None:
            pane.focus()

    def _problems_pane_set_shown(self, shown: bool) -> None:
        pane = self._problems_pane(create=True)
        pane.set_shown(shown)
        self.frame.GetSizer().Layout()
        self.settings.problems_pane_visible = shown
        try:
            from quill.core.settings import save_settings

            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - remembering it is best-effort
            pass
        item_id = getattr(self, "_id_problems_pane", None)
        menu_bar = self.frame.GetMenuBar()
        if item_id is not None and menu_bar is not None:
            menu_bar.Check(item_id, shown)

    def _problems_pause_enabled(self) -> bool:
        return bool(getattr(self.settings, "problems_check_after_pause", False))

    def _problems_set_pause_enabled(self, enabled: bool) -> None:
        self.settings.problems_check_after_pause = enabled
        try:
            from quill.core.settings import save_settings

            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - remembering it is best-effort
            pass

    def _problems_back_to_editor(self) -> None:
        self._set_active_region("Editor")
        self.editor.SetFocus()

    def _problems_copy(self, text: str) -> None:
        self._copy_text_to_clipboard(text)

    def _append_problems_pane_item(self, view_menu: Any) -> None:
        """View > Problems Pane, under Reveal Codes: the other pane under the editor."""
        import wx

        from quill.core.i18n import _

        self._id_problems_pane = wx.NewIdRef()
        view_menu.AppendCheckItem(
            self._id_problems_pane,
            self._menu_label(_("&Problems Pane"), "view.problems_pane"),  # type: ignore[attr-defined]
        )
        shown = bool(getattr(self.settings, "problems_pane_visible", False))
        if shown and not self._problems_pane_is_shown():
            self._problems_pane_set_shown(True)
        view_menu.Check(self._id_problems_pane, shown)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.view_toggle_problems_pane(), id=self._id_problems_pane
        )

    # -- Navigate > Code ------------------------------------------------------ #

    def _code_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_code_row_ids", None)
        if ids is None:
            import wx

            ids = {row[0]: wx.NewIdRef() for row in _CODE_ROWS if row[0]}
            self._code_row_ids = ids
        return ids

    def _register_code_commands(self) -> None:
        self.commands.try_register(  # type: ignore[attr-defined]
            "view.problems_pane",
            "Problems Pane",
            self.view_toggle_problems_pane,
            self._binding_for("view.problems_pane"),  # type: ignore[attr-defined]
        )
        for command_id, _label, palette, handler_name in _CODE_ROWS:
            if command_id:
                self.commands.try_register(  # type: ignore[attr-defined]
                    command_id,
                    palette,
                    getattr(self, handler_name),
                    self._binding_for(command_id),  # type: ignore[attr-defined]
                )

    def _append_code_submenu(self, navigate_menu: Any) -> None:
        """Navigate > Code: the same rows as QUILL Lite's, on the same keys."""
        import wx

        from quill.core.i18n import _

        ids = self._code_menu_ids()
        self._register_code_commands()
        submenu = wx.Menu()
        for command_id, label, _palette, _handler in _CODE_ROWS:
            if not command_id:
                submenu.AppendSeparator()
                continue
            submenu.Append(ids[command_id], self._menu_label(_(label), command_id))  # type: ignore[attr-defined]
        navigate_menu.AppendSubMenu(submenu, _("Code"))
        if not getattr(self, "_code_rows_wired", False):
            self._code_rows_wired = True
            for command_id, _label, _palette, handler_name in _CODE_ROWS:
                if command_id:
                    handler = getattr(self, handler_name)
                    self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id])

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping.update(self._code_menu_ids())
        item_id = getattr(self, "_id_problems_pane", None)
        if item_id is not None:
            mapping["view.problems_pane"] = item_id
        return mapping
