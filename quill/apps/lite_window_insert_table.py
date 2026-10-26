"""Insert > Table in QUILL Lite: QUILL's command, on QUILL's key (rule 2).

QUILL has had Insert Table on Ctrl+Alt+T; QUILL Lite had cell-by-cell table
navigation (Navigate > Table) and no way to make a table to navigate. Same
questions (:mod:`quill.ui.table_shape_prompt`), same builders
(:mod:`quill.core.tagging`), so the two editors cannot drift.

**What is inserted follows the document**, the way every QUILL table works:

* an HTML document gets a real ``<table>``, its header cells marked
  ``scope="col"`` so a screen reader announces the column for each cell;
* a rich text document gets a **real table** -- RichEdit's own, a grid on
  screen and a table to a screen reader, to Word and to WordPad
  (:mod:`quill.ui.richedit_tables`), its first row the header row when asked.
  The table keys read it cell by cell from RichEdit's marks
  (:mod:`quill.core.native_tables`), Tab moves through it as in Word, and Tab
  in the last cell adds a row;
* Markdown and plain text get a table of pipe rows, which the same keys read.

The table goes on lines of its own: a caret in the middle of a line gets a line
break first, so the first row is never glued to the text before it.
"""

from __future__ import annotations

import re
from typing import Any

from quill.core.lite.keymap import spoken_key_for
from quill.core.tagging import InsertionResult, build_html_table, build_markdown_table
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentTableMixin"]


class DocumentTableMixin:
    """Insert > Table for a :class:`~quill.apps.lite_window.DocumentFrame`."""

    app: Any
    control: Any

    def cmd_insert_table(self) -> None:
        """Ctrl+Alt+T: ask the table's shape, then insert it in the document's own form."""
        from quill.ui.dialog_contract import show_message_box
        from quill.ui.table_shape_prompt import prompt_table_shape

        shape = prompt_table_shape(
            self,
            self._show_lite_modal,  # type: ignore[attr-defined]
            lambda message, title, style: show_message_box(message, title, style, self),
        )
        if shape is None:
            self.control.SetFocus()
            return
        rows, columns, include_header = shape
        if self.editor.mode == RICH:  # type: ignore[attr-defined]
            self._insert_real_table(rows, columns, include_header)
            return
        html = self.markup_surface() == "html"  # type: ignore[attr-defined]
        built = (build_html_table if html else build_markdown_table)(
            rows, columns, include_header=include_header
        )
        start, _end = self.control.GetSelection()
        line_start = self.control.GetValue()[:start].rsplit("\n", 1)[-1] == ""
        prefix = "" if line_start else "\n"
        text = f"{prefix}{built.inserted_text}\n"
        self._apply_insertion(  # type: ignore[attr-defined]
            InsertionResult(inserted_text=text, caret_offset=_first_cell(text, prefix, html))
        )
        self.control.SetFocus()
        header = ", with a header row" if include_header else ""
        said = f"Inserted a table of {rows} rows and {columns} columns{header}."
        if not html:
            # The table keys read pipe rows; an HTML table is markup to edit.
            next_cell = spoken_key_for(getattr(self.app, "keymap", None), "cmd_table_next_cell")
            said += f" {next_cell} moves to the next cell."
        self._announce(said)  # type: ignore[attr-defined]

    def _insert_real_table(self, rows: int, columns: int, include_header: bool) -> None:
        """Rich text: RichEdit's own table at the caret, as one undo step."""
        from quill.ui.richedit_tables import insert_native_table

        first = insert_native_table(self.control, rows, columns, header=include_header)
        self.doc_text.invalidate()  # type: ignore[attr-defined]
        self.control.SetInsertionPoint(first)
        self._set_modified(True)  # type: ignore[attr-defined]
        self._touch_status()  # type: ignore[attr-defined]
        self.control.SetFocus()
        header = ", with a header row" if include_header else ""
        next_cell = spoken_key_for(getattr(self.app, "keymap", None), "cmd_table_next_cell")
        self._announce(  # type: ignore[attr-defined]
            f"Inserted a table of {rows} rows and {columns} columns{header}. "
            f"Tab or {next_cell} moves to the next cell."
        )


def _first_cell(text: str, prefix: str, html: bool) -> int:
    """Where the caret lands, ready to type: inside the first cell.

    Just past ``"| "`` on a pipe table's first row; just past the opening tag of
    an HTML table's first ``<th>`` (or ``<td>`` with no header row).
    """
    if not html:
        return len(prefix) + 2
    cell = re.search(r"<t[hd][\s>]", text)  # not <thead> or <tbody>
    assert cell is not None  # build_html_table always writes a cell
    return text.index(">", cell.start()) + 1
