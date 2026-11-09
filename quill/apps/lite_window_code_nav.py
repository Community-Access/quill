"""Navigate > Code in QUILL Lite: blocks, indent changes and the problem keys.

The same rows, letters and keys as QUILL's Navigate > Code
(``quill/ui/main_frame_code_nav.py``), over the same shared code:
:mod:`quill.core.navigation` for blocks and indentation, and
:class:`quill.ui.problems_commands.ProblemsCommandsMixin` over
:mod:`quill.core.problems` for Check This File.

QUILL Lite's languages are plain text, Markdown and HTML, so that is what it
uses them for. A block in Markdown or plain text is a paragraph and in HTML is a
heading or landmark element -- QUILL's HTML pattern, read from the same profile.
Check This File checks Markdown and HTML with the built-in checkers and never
starts an outside tool; QUILL, which knows many more languages, checks those
too. That keeps QUILL Lite level with QUILL rather than ahead of it (rule 10).

View > Problems > Show Pane docks the same problems under the text, above the status
bar, in every open window at once (the setting is the app's). F6 goes from the
text to the pane and on to the status bar; Escape in the pane comes back.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.problems_commands import ProblemsCommandsMixin

__all__ = ["DocumentCodeNavMixin"]


class DocumentCodeNavMixin(ProblemsCommandsMixin):
    """Next / Previous Block and Indent Change, Check This File, the problem keys."""

    # -- blocks ------------------------------------------------------------- #

    def _lite_block_pattern(self) -> str:
        if self.markup_surface() != "html":
            return ""
        from quill.core.language_profile import get_profile_by_name

        profile = get_profile_by_name("HTML")
        return profile.block_pattern if profile is not None else ""

    def cmd_next_block(self) -> None:
        """Next Block: the next paragraph, or in HTML the next heading or landmark."""
        self._walk_block(forward=True)

    def cmd_previous_block(self) -> None:
        """Previous Block: as Next Block, backwards."""
        self._walk_block(forward=False)

    def _walk_block(self, *, forward: bool) -> None:
        from quill.core.navigation import next_block_start, previous_block_start

        text = self.control.GetValue()
        caret = int(self.control.GetInsertionPoint())
        finder = next_block_start if forward else previous_block_start
        target = finder(text, caret, self._lite_block_pattern())
        if target is None:
            self._announce("No next block" if forward else "No previous block")
            return
        # The screen reader reads the line the caret lands on; nothing to add.
        self._go_to(target)

    # -- indent changes ------------------------------------------------------ #

    def cmd_next_indent(self) -> None:
        """Next Indent Change: the next line, skipping blanks, indented differently."""
        self._walk_indent(forward=True)

    def cmd_previous_indent(self) -> None:
        """Previous Indent Change: as Next Indent Change, backwards."""
        self._walk_indent(forward=False)

    def _walk_indent(self, *, forward: bool) -> None:
        from quill.core.navigation import describe_indent, indent_change_target

        text = self.control.GetValue()
        target = indent_change_target(text, int(self.control.GetInsertionPoint()), forward=forward)
        if target is None:
            self._announce("No change of indent below" if forward else "No change of indent above")
            return
        self._go_to(target)
        # The reader says the line; how deep it sits is the part it may not.
        self._announce(describe_indent(text, target).capitalize())

    # -- Check This File and the problem keys --------------------------------- #

    def cmd_check_this_file(self) -> None:
        """Check This File: every problem in a Markdown or HTML document, as a list."""
        if not self._problems_can_check():
            self._announce(_NOTHING_TO_CHECK)
            return
        self._check_this_file()

    def cmd_next_problem(self) -> None:
        """Next Problem: move to the next problem and say what it is."""
        if not self._problems_can_check():
            self._announce(_NOTHING_TO_CHECK)
            return
        self._step_problem(forward=True)

    def cmd_previous_problem(self) -> None:
        """Previous Problem: as Next Problem, backwards."""
        if not self._problems_can_check():
            self._announce(_NOTHING_TO_CHECK)
            return
        self._step_problem(forward=False)

    # -- the Problems pane -------------------------------------------------- #

    def cmd_toggle_problems_pane(self) -> None:
        """View > Problems > Show Pane: the problems docked under the text, in every window."""
        self._toggle_problems_pane()

    def cmd_problems_this_file(self) -> None:
        """View > Problems > This File Only: the pane lists this document's problems."""
        self._problems_choose_files(False)

    def cmd_problems_all_files(self) -> None:
        """View > Problems > All Open Files: the pane lists every window's problems."""
        self._problems_choose_files(True)

    def _problems_all_files_setting(self) -> bool:
        return bool(getattr(self.app.settings, "problems_all_open_files", False))

    def _problems_mark_all_files(self, all_files: bool) -> None:
        self._sync_check_items()

    def problems_listing_all_files(self) -> bool:
        """What this window's View > Problems radio pair shows."""
        if self._problems_files_chosen:
            return self._problems_all_files
        return self._problems_all_files_setting()

    def _problems_can_check(self) -> bool:
        serves = getattr(self, "_ls_serves", None)
        return self._problems_surface() is not None or bool(
            callable(serves) and serves(self._problems_path())
        )

    def _problems_replace(self, start: int, end: int, text: str) -> None:
        from quill.ui.atomic_edit import replace_as_one_undo

        replace_as_one_undo(self.control, start, end, text)

    def _problems_in_background(self, work: Any, done: Any) -> None:
        from quill.apps.lite_window_open import app_task_manager

        app_task_manager(self.app).submit(
            "check-this-file",
            lambda **_kwargs: work(),
            on_success=lambda _op, report: done(report),
            on_failure=lambda _op, error: self._announce(f"Check This File failed: {error}"),
        )

    def _problems_pane(self, *, create: bool) -> Any:
        pane = getattr(self, "_problems_pane_widget", None)
        if pane is not None or not create:
            return pane
        import wx

        from quill.ui.dpi import dip_size
        from quill.ui.problems_pane import ProblemsPane

        pane = ProblemsPane(
            wx,
            self,
            go_to=self._problems_pane_go_to,
            back_to_editor=self._problems_back_to_editor,
            copy_text=self._problems_copy,
            say=self._problems_say,
            tick=self._problems_tick,
            pause_enabled=self._problems_pause_enabled(),
            set_pause_enabled=self._problems_set_pause_enabled,
            set_all_files=self._problems_set_all_files,
            switch_files=self._problems_switch_files,
            quick_fix=self._problems_quick_fix,
        )
        pane.panel.SetMinSize(dip_size(pane.panel, -1, 140))
        pane.panel.Hide()
        sizer = self.GetSizer()
        index = sizer.GetItemCount()
        for position in range(sizer.GetItemCount()):
            if sizer.GetItem(position).GetWindow() is self.status_panel:
                index = position
                break
        # Above the status bar, so F6 meets them in screen order.
        sizer.Insert(index, pane.panel, 0, wx.EXPAND)
        self._problems_pane_widget = pane
        if not self._problems_files_chosen:
            self._problems_all_files = self._problems_all_files_setting()
        pane.set_all_files(self._problems_all_files)
        return pane

    def _problems_pane_set_shown(self, shown: bool) -> None:
        self.app.settings.problems_pane_visible = shown
        self.app._queue_settings_save()
        self.app.reapply_settings()  # every window, this one included
        self.apply_problems_pane_visibility()  # idempotent; here before the check

    def apply_problems_pane_visibility(self) -> None:
        """Match the pane to the setting; built only the first time it shows."""
        shown = bool(getattr(self.app.settings, "problems_pane_visible", False))
        pane = self._problems_pane(create=shown)
        if pane is None or pane.is_shown() == shown:
            return
        if not shown and pane.has_focus():
            self.control.SetFocus()
        pane.set_shown(shown)
        self.Layout()

    def problems_pane_takes_f6(self) -> bool:
        """True when F6 from here should land in the pane rather than the bar."""
        pane = self._problems_pane(create=False)
        return pane is not None and pane.is_shown() and not pane.has_focus()

    def focus_problems_pane(self) -> None:
        pane = self._problems_pane(create=False)
        if pane is not None:
            pane.focus()

    def _problems_open_documents(self) -> list[Any]:
        from quill.core.problems.pane import OpenProblemDocument

        frames = list(getattr(self.app, "frames", []) or []) or [self]
        return [
            OpenProblemDocument(
                key=frame,
                name=frame.document_name(),
                text=str(frame.control.GetValue()),
                language=frame._problems_language(),
                path=getattr(frame, "path", None),
                modified=bool(getattr(frame, "modified", True)),
            )
            for frame in frames
        ]

    def _problems_document_key(self) -> object:
        return self

    def _problems_go_to_document(self, key: object, line: int, column: int) -> None:
        from quill.core.problems import offset_for

        frame: Any = key
        self.app.focus_frame(frame)
        frame._problems_go_to(offset_for(str(frame.control.GetValue()), line, column))

    def _problems_pause_enabled(self) -> bool:
        return bool(getattr(self.app.settings, "problems_check_after_pause", False))

    def _problems_set_pause_enabled(self, enabled: bool) -> None:
        self.app.settings.problems_check_after_pause = enabled
        self.app._queue_settings_save()

    def _problems_back_to_editor(self) -> None:
        self.control.SetFocus()

    def _problems_copy(self, text: str) -> None:
        self._set_clipboard_text(text)

    def _problems_surface(self) -> str | None:
        return self.markup_surface()

    def _problems_text(self) -> str:
        return str(self.control.GetValue())

    def _problems_caret(self) -> int:
        return int(self.control.GetInsertionPoint())

    def _problems_language(self) -> str:
        return self._problems_surface() or "plain"

    def _problems_path(self) -> Path | None:
        return getattr(self, "path", None)

    def _problems_modified(self) -> bool:
        return bool(getattr(self, "modified", True))

    def _problems_go_to(self, offset: int) -> None:
        self._go_to(offset)

    def _problems_say(self, message: str) -> None:
        self._announce(message)

    def _problems_choose(self, summary: str, rows: list[str]) -> int | None:
        from quill.apps.lite_dialogs import choose_from_rows

        chosen = choose_from_rows(
            self,
            title="Problems",
            label=f"{summary} &Problems:",
            help_text=(
                "Every problem Check This File found, in document order, with its "
                "line and column. Press Enter to go to the one selected; Escape "
                "closes the list. Next Problem and Previous Problem walk the same "
                "list from the document without opening it."
            ),
            rows=[(index, row) for index, row in enumerate(rows)],
        )
        if chosen is None:
            self.control.SetFocus()
            return None
        return int(chosen) if isinstance(chosen, int) else None


_NOTHING_TO_CHECK = (
    "Nothing to check: QUILL Lite checks Markdown and HTML documents. "
    "QUILL checks code and data files too."
)
