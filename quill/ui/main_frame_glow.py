"""GLOW structured-document commands (MainFrame mixin).

The in-editor GLOW commands (audit/fix of the current document or selection)
live in ``main_frame.py`` and work on the text in front of the user. This
mixin adds the file-level half of GLOW: auditing and fixing structured
documents on disk — DOCX, PPTX, XLSX, PDF, EPUB, Markdown — through the
shared GLOW engine seam (:mod:`quill.core.glow`).

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
