"""AI Suggest Document Metadata for MainFrame (assessment finding 5e.38).

The first consumer of the field-by-field apply flow: ask the configured AI for
front matter (title, summary, tags, category), review each suggestion in
:class:`~quill.ui.field_apply_dialog.FieldApplyDialog`, and apply only the
accepted fields into the document's front matter in one replacement (one undo
step). The AI proposes; the user disposes — field by field, never as a bulk
overwrite, with a No-defaulted confirmation before any non-empty field is
replaced.
"""

from __future__ import annotations

import threading

from quill.core.error_codes import user_facing_message
from quill.core.story.frontmatter import join_front_matter, split_front_matter


class MetadataAiMixin:
    """Mixin for MainFrame: the ai.suggest_metadata command."""

    def suggest_document_metadata(self) -> None:
        """Ask the AI for metadata, then review it field by field."""
        result = self._ai_require_connection()
        if result is None:
            return
        connection, api_key = result
        text = str(self.editor.GetValue())
        if not text.strip():
            self._set_status("Document is empty - nothing to describe.")
            return
        self._announce("Asking the AI for metadata suggestions.")

        def _worker() -> None:
            import wx as _wx

            from quill.core.ai.metadata_suggest import suggest_document_metadata

            try:
                suggestions = suggest_document_metadata(text, connection, api_key)
            except Exception as exc:  # noqa: BLE001 - surface the specific reason
                _wx.CallAfter(self._set_status, user_facing_message(exc))
                return
            _wx.CallAfter(self._review_metadata_suggestions, text, suggestions)

        threading.Thread(  # GATE-40-OK: one-shot AI metadata request.
            target=_worker, daemon=True, name="quill-ai-metadata"
        ).start()

    def _review_metadata_suggestions(self, snapshot: str, suggestions: list) -> None:
        wx = self._wx
        if self.editor.GetValue() != snapshot:
            self._set_status("The document changed while the AI was thinking; run it again.")
            return
        fields, body = split_front_matter(snapshot)
        current_values = {
            name: (
                ", ".join(str(item) for item in value)
                if isinstance(value, (list, tuple))
                else str(value)
            )
            for name, value in fields.items()
        }
        from quill.ui.field_apply_dialog import FieldApplyDialog

        dlg = FieldApplyDialog(
            self.frame,
            title="Review Metadata Suggestions",
            suggestions=suggestions,
            current_values=current_values,
            announce=self._announce,
        )
        result = dlg.show_modal()
        accepted = dlg.accepted()
        if result != wx.ID_OK or not accepted:
            self._set_status("No metadata was applied; the document is unchanged.")
            return
        updated_fields = dict(fields)
        for name, value in accepted.items():
            # The dialog reviews tags as a readable comma list; the front
            # matter stores real lists (and keeps a field's existing shape).
            if name == "tags" or isinstance(fields.get(name), (list, tuple)):
                updated_fields[name] = [t.strip() for t in value.split(",") if t.strip()]
            else:
                updated_fields[name] = value
        updated = join_front_matter(updated_fields, body)
        self._replace_document_text(updated)
        self.document.set_text(updated)
        count = len(accepted)
        names = ", ".join(accepted)
        self._announce(
            f"Applied {count} metadata field{'s' if count != 1 else ''} ({names}) as one undo step."
        )
        self._set_status(f"Metadata updated: {names}")
