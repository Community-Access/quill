"""Braille layout diagnostics and repair commands (NLS-BRT parity).

A mixin on :class:`~quill.ui.main_frame.MainFrame` that adds the Braille > Repair
submenu: NLS-style layout metrics, trailing-space removal (current line and whole
file), and "go to the longest line/page" navigation. These are the proofreader's
tools for the two classic BRF problems — page width exceeded (trailing spaces)
and page depth exceeded.

Kept in its own module (under the GATE-11 default cap) so the at-budget
:mod:`quill.ui.main_frame_braille` does not have to grow. The wx-free logic lives
in :mod:`quill.core.brf_repair`; this layer wires it to the editor, the page-map
resolver, settings, and announcements. The cell-per-line and line-per-page limits
come from the existing ``braille_cells_per_line`` / ``braille_lines_per_page``
settings, so the diagnostics honour the user's configured page geometry.

All handlers degrade gracefully: layout/page commands announce "not a braille
document" without a resolver; trailing-space and longest-line commands operate on
the active editor text and so work on any document.
"""

from __future__ import annotations


class BrailleRepairMixin:
    """Braille layout-diagnostic and repair command handlers."""

    # Relies on MainFrame helpers: _active_brf_resolver, editor, settings,
    # _say, _announce_not_braille, _record_location_before_jump, _move_point,
    # _location_ring, _replace_document_text, document, _wx, frame, _menu_label,
    # and _binding_for.

    def _build_braille_menu_with_repair(self) -> object:
        """Return the Braille menu with the Repair submenu appended.

        Net-zero wiring seam: ``main_frame_menu`` calls this in place of
        ``_build_braille_menu`` so the at-budget braille file and the menu file
        need no extra lines for the Repair submenu.
        """
        braille_menu = self._build_braille_menu()
        braille_menu.AppendSubMenu(self._build_braille_repair_menu(), "&Repair")
        return braille_menu

    def _build_braille_repair_menu(self) -> object:
        """Build the Braille > Repair submenu, binding each item as it is added."""
        wx = self._wx
        menu = wx.Menu()
        items: list[tuple[str, str, object]] = [
            (
                "Read &Layout Metrics",
                "braille.read_layout_metrics",
                self.read_braille_layout_metrics,
            ),
            ("Go to Longest &Line", "braille.go_to_longest_line", self.go_to_longest_braille_line),
            ("Go to Longest &Page", "braille.go_to_longest_page", self.go_to_longest_braille_page),
            (None, None, None),  # separator
            (
                "Remove Trailing Spaces on This Li&ne",
                "braille.strip_trailing_spaces_line",
                self.strip_trailing_spaces_line,
            ),
            (
                "Remove &Trailing Spaces in Whole File",
                "braille.strip_trailing_spaces_document",
                self.strip_trailing_spaces_document,
            ),
        ]
        for label, command_id, handler in items:
            if label is None:
                menu.AppendSeparator()
                continue
            item_id = wx.NewIdRef()
            menu.Append(item_id, self._menu_label(label, command_id))
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)
        return menu

    def _register_braille_repair_commands(self) -> None:
        """Register the Braille > Repair commands with the command registry."""
        commands: list[tuple[str, str, object]] = [
            (
                "braille.read_layout_metrics",
                "Read Braille Layout Metrics",
                self.read_braille_layout_metrics,
            ),
            (
                "braille.go_to_longest_line",
                "Go to Longest Braille Line",
                self.go_to_longest_braille_line,
            ),
            (
                "braille.go_to_longest_page",
                "Go to Longest Braille Page",
                self.go_to_longest_braille_page,
            ),
            (
                "braille.strip_trailing_spaces_line",
                "Remove Trailing Spaces on Current Line",
                self.strip_trailing_spaces_line,
            ),
            (
                "braille.strip_trailing_spaces_document",
                "Remove Trailing Spaces in Whole File",
                self.strip_trailing_spaces_document,
            ),
        ]
        for command_id, label, handler in commands:
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    # ------------------------------------------------------------------ shared
    def _braille_limits(self) -> tuple[int, int]:
        cells = int(getattr(self.settings, "braille_cells_per_line", 40) or 40)
        lines = int(getattr(self.settings, "braille_lines_per_page", 25) or 25)
        return cells, lines

    def _braille_editor_text_cursor(self) -> tuple[str, int] | None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return None
        try:
            return editor.GetValue(), editor.GetInsertionPoint()
        except Exception:  # noqa: BLE001
            return None

    def _apply_braille_text(self, updated: str, cursor: int, message: str) -> None:
        if getattr(self, "_document_is_read_only", lambda: False)():
            self._say("Document is read-only")
            return
        self._replace_document_text(updated)
        self.document.set_text(updated)
        editor = self.editor
        editor.SetInsertionPoint(cursor)
        editor.SetSelection(cursor, cursor)
        self._say(message)

    # ------------------------------------------------------------------ metrics
    def read_braille_layout_metrics(self) -> None:
        from quill.core.brf_repair import compute_layout_metrics, describe_layout

        resolver = self._active_brf_resolver()
        pair = self._braille_editor_text_cursor()
        if resolver is None or pair is None:
            self._announce_not_braille()
            return
        text, cursor = pair
        cells, lines = self._braille_limits()
        metrics = compute_layout_metrics(
            resolver.page_map, text, cursor, cells_per_line=cells, lines_per_page=lines
        )
        self._say(describe_layout(metrics))

    # --------------------------------------------------------------- navigation
    def go_to_longest_braille_line(self) -> None:
        from quill.core.brf_repair import longest_line_offset

        pair = self._braille_editor_text_cursor()
        if pair is None:
            return
        text, _cursor = pair
        if not text:
            self._say("The document is empty.")
            return
        target = longest_line_offset(text)
        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        cells, _lines = self._braille_limits()
        start, end = self._line_bounds(text, target)
        length = end - start
        warn = " Page width exceeded." if length > cells else ""
        self._say(f"Longest line: {length} cells.{warn}")

    def go_to_longest_braille_page(self) -> None:
        from quill.core.brf_repair import longest_page_offset

        resolver = self._active_brf_resolver()
        if resolver is None:
            self._announce_not_braille()
            return
        target = longest_page_offset(resolver.page_map)
        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        position = resolver.resolve(target)
        cells, lines = self._braille_limits()
        warn = " Page depth exceeded." if position.line_count_in_page > lines else ""
        self._say(
            f"Longest page: braille page {position.page} of {position.page_count}, "
            f"{position.line_count_in_page} lines.{warn}"
        )

    @staticmethod
    def _line_bounds(text: str, offset: int) -> tuple[int, int]:
        from quill.core.brf_repair import _current_line_bounds

        return _current_line_bounds(text, offset)

    # ------------------------------------------------------------------- repair
    def strip_trailing_spaces_line(self) -> None:
        from quill.core.brf_repair import strip_trailing_spaces_current_line

        pair = self._braille_editor_text_cursor()
        if pair is None:
            return
        text, cursor = pair
        updated, new_cursor, removed = strip_trailing_spaces_current_line(text, cursor)
        if removed == 0:
            self._say("No trailing spaces on this line.")
            return
        noun = "character" if removed == 1 else "characters"
        self._apply_braille_text(updated, new_cursor, f"Removed {removed} trailing {noun}.")

    def strip_trailing_spaces_document(self) -> None:
        from quill.core.brf_repair import strip_trailing_spaces_all

        pair = self._braille_editor_text_cursor()
        if pair is None:
            return
        text, cursor = pair
        updated, removed = strip_trailing_spaces_all(text)
        if removed == 0:
            self._say("No trailing spaces found.")
            return
        new_cursor = min(cursor, len(updated))
        noun = "character" if removed == 1 else "characters"
        self._apply_braille_text(
            updated, new_cursor, f"Removed {removed} trailing {noun} from the file."
        )
