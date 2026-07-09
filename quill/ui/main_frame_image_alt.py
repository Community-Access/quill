"""Image alt-text commands for MainFrame (#899): Insert Image with mandatory
alt text, and Describe Image at Cursor for whatever is already in the
document.

Extracted into a mixin (CQ-1). ``ImageAltMixin`` relies on ``self.editor``,
``self.frame``, ``self.document``, ``self._set_status``, ``self._announce``,
and ``self._document_is_read_only`` staying on ``MainFrame``.
"""

from __future__ import annotations

from quill.core.inline_image_alt import describe_image, image_at_position


class ImageAltMixin:
    """Insert Image (mandatory alt text) and Describe Image at Cursor."""

    def insert_image(self) -> None:
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        from quill.ui.insert_image_dialog import InsertImageDialog

        dlg = InsertImageDialog(self.frame, announce_cb=self._announce)
        markdown = dlg.show()
        dlg.close()
        if markdown is None:
            return
        pos = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        updated = text[:pos] + markdown + text[pos:]
        self._replace_document_text(updated)
        self.document.set_text(updated)
        new_pos = pos + len(markdown)
        self.editor.SetInsertionPoint(new_pos)
        self.editor.SetSelection(new_pos, new_pos)
        self._set_status("Image inserted.")

    def describe_image_at_cursor(self) -> None:
        text = self.editor.GetValue()
        position = self.editor.GetInsertionPoint()
        record = image_at_position(text, position)
        if record is None:
            self._set_status("No image at the cursor.")
            return
        self._set_status(describe_image(record))
