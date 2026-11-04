"""QUILL Lite's Insert > Page Break (Ctrl+Enter), by the kind of document.

Kept out of ``lite_window_format.py`` (GATE-11): the command handler there
delegates here. QUILL's half is ``quill.ui.page_break``.
"""

from __future__ import annotations

from typing import Any

from quill.ui.richedit_editing import RICH
from quill.ui.richedit_rtf_surface import RichEditRtfError

__all__ = ["insert_page_break"]


def insert_page_break(host: Any) -> None:
    """Ctrl+Enter, Word's key: start a new page here.

    In a Word or Rich Text document it is a real page break, which saves as
    ``\\page`` in RTF and as Word's own page break in a .docx -- the shared
    :meth:`~quill.ui.richedit_structure.RichEditStructureMixin.insert_page_break`,
    the one QUILL's Ctrl+Enter calls. In Markdown it is the
    ``::: pagebreak`` line QUILL writes, which becomes a page break when the
    document is exported. Plain text has no pages, and says so.
    """
    if host.editor.mode == RICH and host.editor.rtf_available():
        try:
            host.editor.insert_page_break()
        except RichEditRtfError as exc:
            host._announce(str(exc))
            return
        host._set_modified(True)
        host._announce("Page break inserted")
        host._touch_status()
        return
    if host.document_language() != "markdown":
        host._announce("A page break needs a Word, Rich Text or Markdown document")
        return
    from quill.core.tagging import PAGE_BREAK_MARKER

    host.control.WriteText(f"\n{PAGE_BREAK_MARKER}\n")
    host._set_modified(True)
    host._announce("Page break inserted")
    host._touch_status()
