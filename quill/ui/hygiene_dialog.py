"""Quill Eraser review dialog — modeless, keyboard-first, screen-reader-friendly."""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.hygiene.findings import HygieneFinding
from quill.core.i18n import _
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

_CONFIDENCE_LABEL = {
    "high": "High confidence",
    "medium": "Medium confidence",
    "low": "Low confidence",
}


class HygieneReviewDialog:
    """Modeless dialog that presents hygiene findings for interactive review.

    The caller supplies callbacks so the dialog never imports wx from the
    main frame or touches the editor directly.

    Parameters
    ----------
    parent:
        Parent wx.Frame.
    findings:
        Initial list of findings from the engine.
    on_apply_fix:
        Called with ``(finding, new_text)`` when the user confirms a fix.
        The callback should apply the replacement and return the updated
        document text (or ``None`` if the text at the range has changed).
    on_go_to:
        Called with ``finding`` when the user presses Go To Issue.
    on_rescan:
        Called with no arguments; should re-run the engine and call
        ``update_findings`` with the new list.
    """

    def __init__(
        self,
        parent: wx.Frame,
        findings: list[HygieneFinding],
        *,
        on_apply_fix: Callable[[HygieneFinding], str | None],
        on_go_to: Callable[[HygieneFinding], None],
        on_rescan: Callable[[], None],
    ) -> None:
        self._parent = parent
        self._findings: list[HygieneFinding] = list(findings)
        self._ignored: set[int] = set()  # indices of ignored findings
        self._on_apply_fix = on_apply_fix
        self._on_go_to = on_go_to
        self._on_rescan = on_rescan
        self._dialog = wx.Dialog(
            parent,
            title=_("Quill Eraser Review"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._build(self._dialog)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        self._dialog.Show()
        self._list.SetFocus()

    def close(self) -> None:
        self._dialog.Destroy()

    def update_findings(self, findings: list[HygieneFinding]) -> None:
        self._findings = list(findings)
        self._ignored.clear()
        self._rebuild_list()
        self._update_detail(None)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, dlg: wx.Dialog) -> None:
        dlg.SetMinSize((560, 440))
        dlg.SetSize((700, 520))
        dlg.SetName("Quill Eraser Review")

        root = wx.BoxSizer(wx.VERTICAL)

        # --- Summary label ---
        self._summary = wx.StaticText(dlg, label="")
        self._summary.SetName("Summary")
        root.Add(self._summary, 0, wx.EXPAND | wx.ALL, 8)

        # --- Findings list ---
        list_label = wx.StaticText(dlg, label=_("Findings:"))
        root.Add(list_label, 0, wx.LEFT | wx.RIGHT, 8)

        self._list = wx.ListCtrl(
            dlg,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES,
        )
        self._list.SetName("Findings list")
        self._list.InsertColumn(0, _("#"), width=40)
        self._list.InsertColumn(1, _("Confidence"), width=120)
        self._list.InsertColumn(2, _("Issue"), width=260)
        self._list.InsertColumn(3, _("Line"), width=60)
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Detail pane ---
        detail_box = wx.StaticBoxSizer(wx.VERTICAL, dlg, _("Detail"))
        detail_inner = detail_box.GetStaticBox()

        self._detail = wx.TextCtrl(
            detail_inner,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._detail.SetName("Issue detail")
        detail_box.Add(self._detail, 1, wx.EXPAND | wx.ALL, 4)

        root.Add(detail_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Button row ---
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._btn_apply = wx.Button(dlg, label=_("&Apply Fix"))
        self._btn_apply.SetName("Apply fix for selected issue")
        self._btn_ignore = wx.Button(dlg, label=_("&Ignore"))
        self._btn_ignore.SetName("Ignore selected issue")
        self._btn_goto = wx.Button(dlg, label=_("&Go to Issue"))
        self._btn_goto.SetName("Go to issue in editor")
        self._btn_prev = wx.Button(dlg, label=_("&Previous"))
        self._btn_prev.SetName("Go to previous issue")
        self._btn_next = wx.Button(dlg, label=_("&Next"))
        self._btn_next.SetName("Go to next issue")
        self._btn_rescan = wx.Button(dlg, label=_("&Rescan"))
        self._btn_rescan.SetName("Rescan document for issues")
        btn_close = wx.Button(dlg, wx.ID_CLOSE, label=_("&Close"))
        btn_close.SetName("Close Quill Eraser")

        for btn in (
            self._btn_apply,
            self._btn_ignore,
            self._btn_goto,
            self._btn_prev,
            self._btn_next,
            self._btn_rescan,
            btn_close,
        ):
            btn_sizer.Add(btn, 0, wx.RIGHT, 4)

        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)
        dlg.SetSizer(root)

        apply_modal_ids(dlg, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

        # --- Events ---
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_list_select)
        self._btn_apply.Bind(wx.EVT_BUTTON, self._on_apply)
        self._btn_ignore.Bind(wx.EVT_BUTTON, self._on_ignore)
        self._btn_goto.Bind(wx.EVT_BUTTON, self._on_goto)
        self._btn_prev.Bind(wx.EVT_BUTTON, self._on_prev)
        self._btn_next.Bind(wx.EVT_BUTTON, self._on_next)
        self._btn_rescan.Bind(wx.EVT_BUTTON, lambda _e: self._on_rescan())
        btn_close.Bind(wx.EVT_BUTTON, lambda _e: self.close())
        dlg.Bind(wx.EVT_CLOSE, lambda _e: dlg.Destroy())

        self._rebuild_list()
        self._update_buttons()

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _visible_findings(self) -> list[tuple[int, HygieneFinding]]:
        """Return (original_index, finding) for non-ignored findings."""
        return [(i, f) for i, f in enumerate(self._findings) if i not in self._ignored]

    def _rebuild_list(self) -> None:
        self._list.DeleteAllItems()
        visible = self._visible_findings()
        for pos, (orig_idx, f) in enumerate(visible):
            self._list.InsertItem(pos, str(pos + 1))
            self._list.SetItem(pos, 1, _CONFIDENCE_LABEL.get(f.confidence, f.confidence))
            self._list.SetItem(pos, 2, f.title)
            self._list.SetItem(pos, 3, str(f.line))
            self._list.SetItemData(pos, orig_idx)
        n = len(visible)
        ignored = len(self._ignored)
        parts = [f"{n} issue{'s' if n != 1 else ''} found"]
        if ignored:
            parts.append(f"{ignored} ignored")
        self._summary.SetLabel(", ".join(parts) + ".")
        self._update_buttons()

    def _selected_orig_index(self) -> int | None:
        idx = self._list.GetFirstSelected()
        if idx == -1:
            return None
        return self._list.GetItemData(idx)  # type: ignore[return-value]

    def _selected_list_index(self) -> int:
        return self._list.GetFirstSelected()

    def _select_list_row(self, row: int) -> None:
        if 0 <= row < self._list.GetItemCount():
            self._list.Select(row)
            self._list.EnsureVisible(row)
            self._list.SetFocus()

    def _update_detail(self, orig_idx: int | None) -> None:
        if orig_idx is None or orig_idx >= len(self._findings):
            self._detail.SetValue("")
            return
        f = self._findings[orig_idx]
        lines = [
            f"Issue: {f.title}",
            f"Confidence: {_CONFIDENCE_LABEL.get(f.confidence, f.confidence)}",
            f"Location: line {f.line}, column {f.column}",
            "",
            f"Found: {repr(f.original_text)}",
        ]
        if f.suggested_text is not None:
            lines.append(f"Suggested: {repr(f.suggested_text)}")
        else:
            lines.append("No automatic fix available.")
        lines += ["", f.description]
        self._detail.SetValue("\n".join(lines))

    def _update_buttons(self) -> None:
        has_sel = self._selected_orig_index() is not None
        orig_idx = self._selected_orig_index()
        can_fix = has_sel and orig_idx is not None and self._findings[orig_idx].can_auto_fix
        self._btn_apply.Enable(bool(can_fix))
        self._btn_ignore.Enable(has_sel)
        self._btn_goto.Enable(has_sel)
        visible = self._visible_findings()
        sel = self._selected_list_index()
        self._btn_prev.Enable(sel > 0)
        self._btn_next.Enable(sel < len(visible) - 1)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_list_select(self, _event: wx.ListEvent) -> None:
        self._update_detail(self._selected_orig_index())
        self._update_buttons()

    def _on_apply(self, _event: wx.CommandEvent) -> None:
        orig_idx = self._selected_orig_index()
        if orig_idx is None:
            return
        finding = self._findings[orig_idx]
        result = self._on_apply_fix(finding)
        if result is None:
            show_message_box(
                _(
                    "This issue could not be fixed automatically because the "
                    "surrounding text has changed. Please rescan the document."
                ),
                _("Fix Not Applied"),
                wx.OK | wx.ICON_INFORMATION,
                self._dialog,
            )
            return
        # Mark resolved by "ignoring" it from the visible list
        self._ignored.add(orig_idx)
        old_row = self._selected_list_index()
        self._rebuild_list()
        n_remaining = self._list.GetItemCount()
        if n_remaining > 0:
            next_row = min(old_row, n_remaining - 1)
            self._select_list_row(next_row)
        wx.GetApp().GetTopWindow().GetEventHandler().ProcessEvent(  # type: ignore[union-attr]
            wx.CommandEvent(wx.EVT_NULL.typeId)
        )

    def _on_ignore(self, _event: wx.CommandEvent) -> None:
        orig_idx = self._selected_orig_index()
        if orig_idx is None:
            return
        self._ignored.add(orig_idx)
        old_row = self._selected_list_index()
        self._rebuild_list()
        n_remaining = self._list.GetItemCount()
        if n_remaining > 0:
            next_row = min(old_row, n_remaining - 1)
            self._select_list_row(next_row)

    def _on_goto(self, _event: wx.CommandEvent) -> None:
        orig_idx = self._selected_orig_index()
        if orig_idx is None:
            return
        self._on_go_to(self._findings[orig_idx])

    def _on_prev(self, _event: wx.CommandEvent) -> None:
        row = self._selected_list_index()
        if row > 0:
            self._select_list_row(row - 1)

    def _on_next(self, _event: wx.CommandEvent) -> None:
        row = self._selected_list_index()
        if row < self._list.GetItemCount() - 1:
            self._select_list_row(row + 1)
