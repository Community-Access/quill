"""QUILL's Insert Page Break (Ctrl+Enter), by the kind of document.

Kept out of ``main_frame_format_codes.py`` (GATE-11): the command row there
delegates here. QUILL Lite's half is ``quill.apps.lite_page_break``; both put a
page break in a Word or Rich Text document through the one shared
``RichEditStructureMixin.insert_page_break``.
"""

from __future__ import annotations

from typing import Any

from quill.core.tagging import build_page_break
from quill.platform.sr_announce import announce

__all__ = ["insert_page_break"]


def insert_page_break(host: Any) -> None:
    """Ctrl+Enter, Word's key: a page break in whatever kind of document this is.

    * **Word and Rich Text** (rich mode): a real page break, which saves as
      ``\\page`` in RTF and as Word's own page break in a .docx.
    * **Braille** (a BRF): the form feed that is a braille page.
    * **Markdown**: the ``::: pagebreak`` line, made real at export.
    * **On a link** in any of the text kinds, Ctrl+Enter still follows it.
      It was Follow Link's key until 2026-11-03, and a habit that opens a
      link should not quietly start typing page breaks into a document.
    * Anywhere else it says why it cannot -- a command is never silent.
    """
    if not host._feature_enabled("core.format"):
        host._set_status("Page break is unavailable in this profile")
        return
    if host._current_editor_mode() == "rich":
        wrapper = host._active_richedit()
        if wrapper is not None:
            from quill.ui.richedit_rtf_surface import RichEditRtfError

            try:
                wrapper.insert_page_break()
            except RichEditRtfError as error:
                host._set_status(f"Could not insert a page break: {error}")
                return
            host._mark_rich_formatting_dirty()
            host._set_status("Page break inserted")
            return
    from quill.core.links import find_link_at_cursor

    if find_link_at_cursor(host.editor.GetValue(), host.editor.GetInsertionPoint()):
        host.follow_link()
        return
    if getattr(host, "_active_brf_resolver", lambda: None)() is not None:
        host.insert_braille_page_break()
        return
    if host._active_markup_surface() != "markdown":
        host._set_status("A page break needs a Word, Rich Text, Markdown or braille document")
        return
    marker = build_page_break().inserted_text
    start, end = host.editor.GetSelection()
    host.editor.Replace(start, end, f"\n{marker}\n")
    host.editor.SetInsertionPoint(start + len(marker) + 2)
    host.editor.SetFocus()
    status = "Page break inserted"
    host._set_status(status)
    announce(status)
