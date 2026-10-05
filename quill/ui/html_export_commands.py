"""Export as HTML, shared by QUILL and QUILL Lite (File > Export).

One self-contained page with its styles inside and no scripts
(:mod:`quill.io.html_page`), so it can be emailed, attached or put on a web
server as it is. Unlike Save As ``.html``, the document you are editing stays
the document you are editing: the page is a copy.

When the document has notes written into it (``quill-note`` comments), the
export asks whether to include them, marked as notes, and the answer defaults
to **No**: a forgotten note must never turn up in a page somebody publishes.
QUILL overrides :meth:`_write_html_export` to run Pandoc when it is installed;
QUILL Lite, which ships without Pandoc, always uses QUILL's own renderer.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.storage import write_text_atomic
from quill.io.html_page import count_file_notes, standalone_html
from quill.ui.editor_host import EditorHostMixin

__all__ = ["HtmlExportCommandsMixin"]

_TITLE = "Export as HTML"


class HtmlExportCommandsMixin(EditorHostMixin):
    """``cmd_export_html``. Mixed into both editors."""

    def cmd_export_html(self) -> None:
        """Write the document as a shareable web page, and keep editing this one."""
        import wx

        text = self._host_control().GetValue()
        kind = self._host_kind()
        title = self._host_title()
        path = self._host_path()
        with wx.FileDialog(
            self._host_parent(),
            _TITLE,
            defaultDir=str(path.parent) if path is not None else "",
            defaultFile=f"{title}.html",
            wildcard="Web page (*.html)|*.html|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._host_show_modal(dialog, _TITLE) != wx.ID_OK:
                self._host_say("Export cancelled")
                return
            target = Path(dialog.GetPath())
        if not target.suffix:
            target = target.with_suffix(".html")
        include = False
        count = count_file_notes(text, kind)
        if count:
            noun = "note" if count == 1 else "notes"
            include = self._host_ask_yes_no(
                f"This document has {count} {noun} written into it. "
                "Include them in the page, marked as notes?",
                _TITLE,
            )
        try:
            self._write_html_export(target, text, kind, title, include)
        except Exception as error:  # noqa: BLE001 - reported, never a crash
            self._host_say(f"Could not export {target.name}: {error}")
            return
        self._host_say(f"Exported {target.name}")

    def _write_html_export(
        self, target: Path, text: str, kind: str, title: str, include_notes: bool
    ) -> None:
        """QUILL's own renderer; QUILL overrides this to try Pandoc first."""
        page = standalone_html(
            text, kind, title, lang=self._host_language(), include_notes=include_notes
        )
        write_text_atomic(target, page)
