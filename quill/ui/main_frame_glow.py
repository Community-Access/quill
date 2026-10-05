"""GLOW structured-document commands (MainFrame mixin).

The in-editor GLOW commands (audit/fix of the current document or selection)
work on the text in front of the user (``GlowEditorMixin``, at the end of this
module since F-08). ``GlowFileMixin`` adds the file-level half of GLOW:
auditing and fixing structured documents on disk — DOCX, PPTX, XLSX, PDF,
EPUB, Markdown — through the shared GLOW engine seam (:mod:`quill.core.glow`).

Behavior contract:

* Parsing a structured file can be slow, so both commands run on the
  background task pool and report back on the UI thread; the editor never
  blocks on a document parse.
* Fixing **never** overwrites the original: the engine writes a repaired copy
  next to the source and QUILL says exactly where it went.
* When the optional shared engine is not installed, the seam degrades to an
  honest "engine unavailable" report instead of an error dialog.

Wiring expectations from MainFrame: ``_wx``, ``frame``, ``_task_manager``,
``_show_modal_dialog``, ``_create_named_scratch_tab``, ``_set_status``,
``_announce``, ``_show_message_box``, ``_record_notification``.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.core.glow import build_audit_report, build_fix_report, fix_text
from quill.core.selection import line_span, paragraph_span

GLOW_STRUCTURED_WILDCARD = (
    "Structured documents (*.docx;*.pptx;*.xlsx;*.pdf;*.epub;*.md)"
    "|*.docx;*.pptx;*.xlsx;*.pdf;*.epub;*.md"
    "|All files (*.*)|*.*"
)


def glow_fixed_copy_path(source: Path) -> Path:
    """The non-destructive output path for a GLOW file fix.

    ``report.docx`` -> ``report-accessible.docx`` in the same folder; when that
    name is already taken, a numeric suffix is added (``report-accessible-2``)
    so an existing fixed copy is never silently replaced either.
    """
    candidate = source.with_name(f"{source.stem}-accessible{source.suffix}")
    counter = 2
    while candidate.exists():
        candidate = source.with_name(f"{source.stem}-accessible-{counter}{source.suffix}")
        counter += 1
    return candidate


class GlowFileMixin:
    """The ``tools.glow_audit_file`` / ``tools.glow_fix_file`` handlers."""

    def _glow_pick_file(self, title: str) -> Path | None:
        wx = self._wx
        dialog = wx.FileDialog(
            self.frame,
            title,
            wildcard=GLOW_STRUCTURED_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                self._set_status(f"{title} cancelled")
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()

    def glow_audit_file(self) -> None:
        """Audit a structured document on disk and open the report as a tab."""
        if not self._ensure_glow_enabled():
            return
        source = self._glow_pick_file("GLOW Audit File")
        if source is None:
            return
        from quill.core.glow import audit_file

        self._set_status(f"GLOW is auditing {source.name}...")

        def _on_success(_operation_id: str, result) -> None:
            from quill.core.glow import build_file_audit_report

            report = build_file_audit_report(result)
            self._create_named_scratch_tab(f"GLOW Audit - {source.name}", report)
            self._announce(
                f"GLOW audit for {source.name}: score {result.score}, "
                f"grade {result.grade}, {len(result.findings)} findings."
            )
            self._set_status(f"Opened GLOW audit for {source.name}")

        def _on_failure(_operation_id: str, error: BaseException) -> None:
            wx = self._wx
            self._set_status("GLOW audit failed")
            self._show_message_box(
                f"GLOW could not audit {source.name}.\n\n{error}",
                "GLOW Audit File",
                wx.ICON_ERROR | wx.OK,
            )

        self._task_manager.submit(
            name="glow-audit-file",
            func=lambda **_kw: audit_file(source),
            on_success=_on_success,
            on_failure=_on_failure,
        )

    def glow_fix_file(self) -> None:
        """Fix a structured document into a new copy and report what changed."""
        if not self._ensure_glow_enabled():
            return
        source = self._glow_pick_file("GLOW Fix File")
        if source is None:
            return
        wx = self._wx
        output = glow_fixed_copy_path(source)
        proceed = self._show_message_box(
            (
                f"GLOW will write a repaired copy of {source.name} to:\n\n"
                f"{output}\n\n"
                "The original file is never modified. Continue?"
            ),
            "GLOW Fix File",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if proceed != wx.YES:
            self._set_status("GLOW fix cancelled")
            return
        from quill.core.glow import fix_file

        self._set_status(f"GLOW is fixing {source.name}...")

        def _on_success(_operation_id: str, result) -> None:
            from quill.core.glow import build_file_audit_report

            report_lines = [
                f"GLOW fix for {source.name}",
                "",
                f"Fixed copy: {result.output_path}",
                f"Applied fixes: {result.total_fixes}",
            ]
            if result.warnings:
                report_lines.extend(["", "Warnings:"])
                report_lines.extend(f"- {warning}" for warning in result.warnings)
            report_lines.extend(["", build_file_audit_report(result.audit)])
            self._create_named_scratch_tab(f"GLOW Fix - {source.name}", "\n".join(report_lines))
            self._record_notification(
                f"GLOW applied {result.total_fixes} fixes to a copy of {source.name}",
                "glow",
            )
            self._announce(
                f"GLOW applied {result.total_fixes} fixes. "
                f"The repaired copy is {Path(result.output_path).name}."
            )
            self._set_status(f"GLOW fix complete: {result.output_path}")

        def _on_failure(_operation_id: str, error: BaseException) -> None:
            self._set_status("GLOW fix failed")
            self._show_message_box(
                f"GLOW could not fix {source.name}.\n\n{error}\n\n"
                f"The original file was not changed.",
                "GLOW Fix File",
                wx.ICON_ERROR | wx.OK,
            )

        self._task_manager.submit(
            name="glow-fix-file",
            func=lambda **_kw: fix_file(source, output),
            on_success=_on_success,
            on_failure=_on_failure,
        )


class GlowEditorMixin:
    """GLOW on the text in front of you: audit or fix the document or the selection.

    Moved here from ``main_frame.py`` under F-08 (2026-10-03), beside the file-level half.
    """

    def _glow_scope(self) -> tuple[str, int, int, str]:
        start, end = self.editor.GetSelection()
        if start != end:
            return self.editor.GetRange(start, end), start, end, "selection"
        cursor = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        start, end = paragraph_span(text, cursor)
        scope = self.editor.GetRange(start, end)
        if not scope.strip():
            start, end = line_span(text, cursor)
            scope = self.editor.GetRange(start, end)
            return scope, start, end, "current line"
        return scope, start, end, "current paragraph"

    def _ensure_glow_enabled(self) -> bool:
        """Gate every GLOW command behind the Experimental opt-in.

        GLOW ships as an experimental feature: it runs only when both the
        Experimental master switch and the GLOW checkbox are on (Preferences >
        Experimental). Commands stay in the palette so they are discoverable;
        invoking one while gated explains exactly how to turn GLOW on — the
        same pattern as Read Document in Browser.
        """
        if self._feature_enabled("core.glow"):
            return True
        wx = self._wx
        self._show_message_box(
            "GLOW is an experimental feature and is currently turned off.\n\n"
            "To enable it, open Preferences > Experimental, check 'Enable "
            "experimental features', then check 'GLOW accessibility review and "
            "repair'. It takes effect as soon as you apply Settings - no "
            "restart needed.",
            "GLOW (Experimental)",
            wx.ICON_INFORMATION | wx.OK,
        )
        return False

    def glow_audit_document(self) -> None:
        if not self._ensure_glow_enabled():
            return
        markup = self._current_markup_context()
        text = self.editor.GetValue()
        report = build_audit_report(self.document.name, text, markup, "current document")
        self._create_named_scratch_tab(f"GLOW Audit - {self.document.name}", report)
        self._set_status(f"Opened GLOW audit for {self.document.name}")

    def glow_audit_selection(self) -> None:
        if not self._ensure_glow_enabled():
            return
        text, _start, _end, scope_label = self._glow_scope()
        markup = self._current_markup_context()
        report = build_audit_report(self.document.name, text, markup, scope_label)
        self._create_named_scratch_tab(f"GLOW Audit - {scope_label.title()}", report)
        self._set_status(f"Opened GLOW audit for {scope_label}")

    def glow_fix_document(self) -> None:
        if not self._ensure_glow_enabled():
            return
        original = self.editor.GetValue()
        markup = self._current_markup_context()
        result = fix_text(original, markup)
        if result.text == original:
            report = build_fix_report(self.document.name, result, markup, "current document")
            self._create_named_scratch_tab(f"GLOW Fix Report - {self.document.name}", report)
            self._set_status("No deterministic GLOW fixes were available")
            return
        preview_title = f"{self.document.name} - GLOW Fix Preview"
        index = self._create_document_tab(
            Document(text=result.text, path=None, modified=False),
            select=True,
        )
        self._set_tab_page_text(index, preview_title)
        report = build_fix_report(self.document.name, result, markup, "current document")
        self._record_notification(report.splitlines()[0], "glow")
        self._start_compare_session([(self.document.name, original), (preview_title, result.text)])
        self._set_status(
            f"Opened GLOW fix preview with {len(result.fixes)} changes and started compare"
        )

    def glow_fix_selection(self) -> None:
        if not self._ensure_glow_enabled():
            return
        text, start, end, scope_label = self._glow_scope()
        markup = self._current_markup_context()
        result = fix_text(text, markup)
        if result.text == text:
            self._set_status(f"No deterministic GLOW fixes were available for {scope_label}")
            return
        self.editor.Replace(start, end, result.text)
        self.editor.SetSelection(start, start + len(result.text))
        self.document.set_text(self.editor.GetValue())
        report = build_fix_report(self.document.name, result, markup, scope_label)
        self._record_notification(report.splitlines()[0], "glow")
        self._set_status(f"Applied {len(result.fixes)} GLOW fixes to {scope_label}")
