"""Quill Eraser (text hygiene) commands for MainFrame."""

from __future__ import annotations

import wx

from quill.core.hygiene.engine import HygieneEngine
from quill.core.hygiene.findings import HygieneFinding, HygieneSettings
from quill.core.i18n import _
from quill.ui.hygiene_dialog import HygieneReviewDialog


class HygieneMixin:
    """Mix into MainFrame to add Quill Eraser commands."""

    # set by MainFrame.__init__
    _hygiene_dialog: HygieneReviewDialog | None = None

    # ------------------------------------------------------------------
    # Public entry points (called from menu / command map)
    # ------------------------------------------------------------------

    def open_quill_eraser(self) -> None:
        """Launch Quill Eraser for the full document."""
        self._run_hygiene(scope="document")

    def open_quill_eraser_selection(self) -> None:
        """Launch Quill Eraser for the current selection (or full doc)."""
        self._run_hygiene(scope="selection")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _hygiene_settings(self) -> HygieneSettings:
        s = getattr(self, "settings", None)
        if s is None:
            return HygieneSettings()
        disabled_str = getattr(s, "hygiene_rules_disabled", "")
        disabled = frozenset(x.strip() for x in disabled_str.split(",") if x.strip())
        min_conf = getattr(s, "hygiene_min_confidence", "high")
        if min_conf not in {"high", "medium", "low"}:
            min_conf = "high"
        return HygieneSettings(
            min_confidence=min_conf,  # type: ignore[arg-type]
            allow_double_space_after_period=bool(
                getattr(s, "hygiene_allow_double_space_after_period", False)
            ),
            max_blank_lines=int(getattr(s, "hygiene_max_blank_lines", 2)),
            rules_disabled=disabled,
        )

    def _run_hygiene(self, scope: str) -> None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return

        text: str = editor.GetValue()
        doc = getattr(self, "document", None)
        path = getattr(doc, "path", None)
        file_ext = path.suffix.lstrip(".").lower() if path else ""

        engine = HygieneEngine()

        if engine.is_code_file(file_ext):
            answer = self._show_message_box(  # type: ignore[attr-defined]
                _(
                    "Quill Eraser is designed for prose. This appears to be a "
                    f"{file_ext.upper() or 'code'} file, where spacing may be "
                    "meaningful. Prose rules are disabled.\n\n"
                    "Would you like to run safe trailing-whitespace checks only?"
                ),
                _("Quill Eraser"),
                wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION,
            )
            if answer == wx.CANCEL:
                return
            safe_only = answer == wx.YES
        else:
            safe_only = False

        scope_start = 0
        scope_end = len(text)
        if scope == "selection":
            sel_start, sel_end = editor.GetSelection()
            if sel_start < sel_end:
                scope_start = sel_start
                scope_end = sel_end
            else:
                answer = self._show_message_box(  # type: ignore[attr-defined]
                    _("No text is selected. Check the entire document instead?"),
                    _("Quill Eraser"),
                    wx.YES_NO | wx.ICON_QUESTION,
                )
                if answer != wx.YES:
                    return

        settings = self._hygiene_settings()
        findings = engine.check(
            text,
            file_ext=file_ext,
            scope_start=scope_start,
            scope_end=scope_end,
            settings=settings,
            safe_only=safe_only,
        )

        announce = getattr(self, "_announce", None)
        if not findings:
            msg = _("Quill Eraser: no issues found.")
            if callable(announce):
                announce(msg)
            else:
                self._show_message_box(msg, _("Quill Eraser"), wx.OK | wx.ICON_INFORMATION)  # type: ignore[attr-defined]
            return

        n = len(findings)
        hi = sum(1 for f in findings if f.confidence == "high")
        mid = sum(1 for f in findings if f.confidence == "medium")
        summary = f"Quill Eraser: {n} issue{'s' if n != 1 else ''} found"
        if hi:
            summary += f", {hi} high confidence"
        if mid:
            summary += f", {mid} medium confidence"
        summary += "."
        if callable(announce):
            announce(summary)

        if self._hygiene_dialog is not None:
            try:
                self._hygiene_dialog.update_findings(findings)
                self._hygiene_dialog.show()
                return
            except Exception:  # noqa: BLE001
                self._hygiene_dialog = None

        # The dialog must be parented to the real wx.Frame (stored as
        # ``self.frame``), not the mixin instance itself — the mixin class
        # does not inherit from wx.Window, so passing ``self`` here produces
        # a ``TypeError: Dialog(): argument 1 has unexpected type
        # 'MainFrame'`` from wxPython's SIP wrapper. See issue #624.
        parent_frame = getattr(self, "frame", None)
        if parent_frame is None:
            return
        self._hygiene_dialog = HygieneReviewDialog(
            parent_frame,
            findings,
            on_apply_fix=self._hygiene_apply_fix,
            on_go_to=self._hygiene_goto,
            on_rescan=lambda: self._run_hygiene(scope),
        )
        self._hygiene_dialog.show()

    def _hygiene_apply_fix(self, finding: HygieneFinding) -> str | None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return None
        text: str = editor.GetValue()
        engine = HygieneEngine()
        new_text = engine.apply_fix(text, finding)
        if new_text is None:
            return None
        editor.SetValue(new_text)
        doc = getattr(self, "document", None)
        if doc is not None and hasattr(doc, "set_text"):
            doc.set_text(new_text)
        announce = getattr(self, "_announce", None)
        if callable(announce):
            announce(
                _(
                    f"Fixed: {finding.title}. "
                    f"Changed {repr(finding.original_text)} to "
                    f"{repr(finding.suggested_text)}."
                )
            )
        return new_text

    def _hygiene_goto(self, finding: HygieneFinding) -> None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        start = finding.start_offset
        end = finding.end_offset
        text: str = editor.GetValue()
        capped_start = max(0, min(start, len(text)))
        capped_end = max(capped_start, min(end, len(text)))
        editor.SetSelection(capped_start, capped_end)
        wx.CallAfter(editor.SetFocus)
        announce = getattr(self, "_announce", None)
        if callable(announce):
            announce(
                _(f"Quill Eraser: {finding.title}, line {finding.line}, column {finding.column}.")
            )
