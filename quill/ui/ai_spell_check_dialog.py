"""AI spell check review dialogs for QUILL.

AISpellCheckDialog: Quick mode (F7) - full document, review all at once.
AISpellCheckInteractiveDialog: Interactive mode (Shift+F7) - paragraph by paragraph.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.ai.spell_check import SpellCorrection, apply_corrections
from quill.ui.dialog_contract import apply_modal_ids


class AISpellCheckDialog:
    """Review dialog for Quick mode AI spell check.

    Presents all corrections in a ListCtrl; user accepts/skips each one.
    Returns (corrected_text, applied_count) on OK, or (original_text, 0) on Cancel.
    """

    def __init__(
        self,
        parent: object,
        document_text: str,
        corrections: list[SpellCorrection],
        show_modal_dialog: Callable,
    ) -> None:
        import wx

        self._wx = wx
        self._document_text = document_text
        self._corrections = list(corrections)
        self._show_modal = show_modal_dialog
        self._accepted: set[int] = set()
        self._skipped: set[int] = set()
        self._override_texts: dict[int, str] = {}
        self.result_text = document_text
        self.applied_count = 0

        n = len(corrections)
        self.dialog = wx.Dialog(
            parent,
            title=f"AI Spell Check - {n} suggestion{'s' if n != 1 else ''}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(760, 560))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        n = len(self._corrections)
        summary = wx.StaticText(
            self.dialog,
            label=f"AI found {n} spelling suggestion{'s' if n != 1 else ''}. "
            "Review each one below. Accept or skip with Alt+A / Alt+S.",
        )
        summary.Wrap(700)
        root.Add(summary, 0, wx.ALL, 8)

        # Correction list
        self._list = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName("Spelling corrections")
        self._list.InsertColumn(0, "#", width=40)
        self._list.InsertColumn(1, "Misspelled", width=160)
        self._list.InsertColumn(2, "Suggestion", width=160)
        self._list.InsertColumn(3, "Context", width=280)
        self._populate_list()
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Detail section
        detail_box = wx.StaticBox(self.dialog, label="Selected correction")
        detail_sizer = wx.StaticBoxSizer(detail_box, wx.VERTICAL)
        self._before_label = wx.StaticText(self.dialog, label="Before: ")
        self._after_label = wx.StaticText(self.dialog, label="After: ")
        self._before_label.Wrap(680)
        self._after_label.Wrap(680)
        detail_sizer.Add(self._before_label, 0, wx.ALL, 4)
        detail_sizer.Add(self._after_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

        override_row = wx.BoxSizer(wx.HORIZONTAL)
        override_label = wx.StaticText(self.dialog, label="Override correction:")
        self._override = wx.TextCtrl(self.dialog)
        self._override.SetName("Override correction")
        override_row.Add(override_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        override_row.Add(self._override, 1, wx.EXPAND)
        detail_sizer.Add(override_row, 0, wx.EXPAND | wx.ALL, 4)
        root.Add(detail_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Per-item buttons
        btn1 = wx.BoxSizer(wx.HORIZONTAL)
        self._accept_btn = wx.Button(self.dialog, label="&Accept (Alt+A)")
        self._accept_all_like = wx.Button(self.dialog, label="Accept A&ll Like This")
        self._skip_btn = wx.Button(self.dialog, label="&Skip (Alt+S)")
        self._skip_all_like = wx.Button(self.dialog, label="Skip Al&l Like This")
        for b in (self._accept_btn, self._accept_all_like, self._skip_btn, self._skip_all_like):
            btn1.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Global buttons
        btn2 = wx.BoxSizer(wx.HORIZONTAL)
        self._accept_all_btn = wx.Button(self.dialog, label="Accept All &Remaining")
        self._reject_all_btn = wx.Button(self.dialog, label="Re&ject All")
        self._apply_close_btn = wx.Button(self.dialog, label="App&ly and Close")
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._apply_close_btn.GetId(),
            escape_id=self._reject_all_btn.GetId(),
        )
        for b in (self._accept_all_btn, self._reject_all_btn, self._apply_close_btn):
            btn2.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self._bind_events()

        if self._corrections:
            self._list.SetItemState(
                0,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
            )
            self._update_detail(0)
        wx.CallAfter(self._list.SetFocus)

    def _populate_list(self) -> None:
        self._list.DeleteAllItems()
        for i, corr in enumerate(self._corrections):
            state = ""
            if i in self._accepted:
                state = " [Accepted]"
            elif i in self._skipped:
                state = " [Skipped]"
            self._list.InsertItem(i, str(i + 1))
            self._list.SetItem(i, 1, corr.original + state)
            self._list.SetItem(i, 2, corr.correction)
            self._list.SetItem(i, 3, corr.context[:60])

    def _update_detail(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._corrections):
            return
        corr = self._corrections[idx]
        ctx = corr.context
        before = ctx.replace(corr.original, f"[{corr.original}]") if corr.original in ctx else ctx
        after = (
            ctx.replace(corr.original, corr.correction) if corr.original in ctx else corr.correction
        )
        self._before_label.SetLabel(f"Before: {before}")
        self._after_label.SetLabel(f"After: {after}")
        self._override.SetValue(self._override_texts.get(idx, corr.correction))

    def _bind_events(self) -> None:
        wx = self._wx
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._accept_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept_current())
        self._skip_btn.Bind(wx.EVT_BUTTON, lambda _e: self._skip_current())
        self._accept_all_like.Bind(wx.EVT_BUTTON, lambda _e: self._accept_all_like_current())
        self._skip_all_like.Bind(wx.EVT_BUTTON, lambda _e: self._skip_all_like_current())
        self._accept_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept_all())
        self._reject_all_btn.Bind(wx.EVT_BUTTON, self._on_reject_all)
        self._apply_close_btn.Bind(wx.EVT_BUTTON, self._on_apply)

    def _on_select(self, event: object) -> None:
        idx = self._list.GetFirstSelected()
        if idx >= 0:
            self._update_detail(idx)

    def _accept_current(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return
        override = self._override.GetValue().strip()
        if override and override != self._corrections[idx].correction:
            self._override_texts[idx] = override
        self._accepted.add(idx)
        self._skipped.discard(idx)
        self._populate_list()
        next_idx = min(idx + 1, len(self._corrections) - 1)
        if next_idx != idx:
            self._list.SetItemState(
                next_idx, self._wx.LIST_STATE_SELECTED, self._wx.LIST_STATE_SELECTED
            )
            self._update_detail(next_idx)

    def _skip_current(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return
        self._skipped.add(idx)
        self._accepted.discard(idx)
        self._populate_list()
        next_idx = min(idx + 1, len(self._corrections) - 1)
        if next_idx != idx:
            self._list.SetItemState(
                next_idx, self._wx.LIST_STATE_SELECTED, self._wx.LIST_STATE_SELECTED
            )
            self._update_detail(next_idx)

    def _accept_all_like_current(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return
        original = self._corrections[idx].original
        for i, corr in enumerate(self._corrections):
            if corr.original == original:
                self._accepted.add(i)
                self._skipped.discard(i)
        self._populate_list()

    def _skip_all_like_current(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0:
            return
        original = self._corrections[idx].original
        for i, corr in enumerate(self._corrections):
            if corr.original == original:
                self._skipped.add(i)
                self._accepted.discard(i)
        self._populate_list()

    def _accept_all(self) -> None:
        for i in range(len(self._corrections)):
            self._accepted.add(i)
            self._skipped.discard(i)
        self._populate_list()

    def _on_reject_all(self, event: object) -> None:
        self.result_text = self._document_text
        self.applied_count = 0
        self.dialog.EndModal(self._wx.ID_CANCEL)

    def _on_apply(self, event: object) -> None:
        # Build effective corrections (with overrides)
        effective: list[SpellCorrection] = []
        for i in sorted(self._accepted):
            corr = self._corrections[i]
            override = self._override_texts.get(i, "").strip()
            if override:
                from quill.core.ai.spell_check import SpellCorrection as SC

                effective.append(SC(corr.original, override, corr.context))
            else:
                effective.append(corr)
        self.result_text, self.applied_count = apply_corrections(self._document_text, effective)
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[str, int]:
        self._show_modal(self.dialog, "AI Spell Check")
        return self.result_text, self.applied_count


class AISpellCheckInteractiveDialog:
    """Paragraph-by-paragraph interactive spell check dialog.

    Processes one paragraph at a time, overlapping network calls with user review.
    Non-modal: opens immediately, fetches corrections per paragraph in background.
    """

    def __init__(
        self,
        parent: object,
        paragraphs: list[str],
        connection: object,
        api_key: str,
        show_modal_dialog: Callable,
        apply_to_document: Callable[[list[SpellCorrection]], None],
    ) -> None:
        import wx

        self._wx = wx
        self._paragraphs = paragraphs
        self._connection = connection
        self._api_key = api_key
        self._show_modal = show_modal_dialog
        self._apply_to_document = apply_to_document
        self._current_para = 0
        self._total = len(paragraphs)
        self._pending_corrections: list[SpellCorrection] = []
        self._all_accepted: list[SpellCorrection] = []
        self._fetch_event = threading.Event()
        self._stop_event = threading.Event()

        self.dialog = wx.Dialog(
            parent,
            title="Interactive Spell Check",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(780, 580))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # Progress
        self._progress_label = wx.StaticText(
            self.dialog,
            label=f"Paragraph 1 of {self._total}: checking...",
        )
        root.Add(self._progress_label, 0, wx.ALL, 8)
        self._gauge = wx.Gauge(self.dialog, range=self._total)
        root.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Correction list
        self._list = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName("Paragraph corrections")
        self._list.InsertColumn(0, "#", width=40)
        self._list.InsertColumn(1, "Misspelled", width=160)
        self._list.InsertColumn(2, "Suggestion", width=160)
        self._list.InsertColumn(3, "Context", width=260)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        # Status
        self._status = wx.StaticText(self.dialog, label="Checking paragraph 1...")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._accept_btn = wx.Button(self.dialog, label="&Accept (Alt+A)")
        self._skip_btn = wx.Button(self.dialog, label="&Skip (Alt+S)")
        self._jump_btn = wx.Button(self.dialog, label="&Jump to Error (Alt+J)")
        self._next_btn = wx.Button(self.dialog, label="&Next Paragraph (Alt+N)")
        self._finish_btn = wx.Button(self.dialog, label="&Finish")
        self._next_btn.Enable(False)
        for b in (
            self._accept_btn,
            self._skip_btn,
            self._jump_btn,
            self._next_btn,
            self._finish_btn,
        ):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn_row, 0, wx.ALL, 8)

        apply_modal_ids(
            self.dialog,
            affirmative_id=self._finish_btn.GetId(),
            escape_id=self._finish_btn.GetId(),
        )

        self.dialog.SetSizer(root)
        self._bind_events()

    def _bind_events(self) -> None:
        wx = self._wx
        self._accept_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept_current())
        self._skip_btn.Bind(wx.EVT_BUTTON, lambda _e: self._skip_current())
        self._next_btn.Bind(wx.EVT_BUTTON, lambda _e: self._advance_paragraph())
        self._finish_btn.Bind(wx.EVT_BUTTON, self._on_finish)

    def run(self) -> None:
        self._start_fetch_paragraph(0)
        self.dialog.Show()

    def _start_fetch_paragraph(self, idx: int) -> None:
        if idx >= self._total or self._stop_event.is_set():
            return
        para = self._paragraphs[idx]
        label = para[:60].replace("\n", " ")
        wx = self._wx
        wx.CallAfter(
            self._progress_label.SetLabel, f"Paragraph {idx + 1} of {self._total}: {label}..."
        )
        wx.CallAfter(self._gauge.SetValue, idx)
        wx.CallAfter(self._status.SetLabel, f"Checking paragraph {idx + 1}...")
        wx.CallAfter(self._list.DeleteAllItems)
        wx.CallAfter(self._next_btn.Enable, False)

        def _fetch():
            from quill.core.ai.spell_check import SpellCheckError, ai_spell_check

            try:
                corrections = ai_spell_check(para, self._connection, self._api_key)
            except SpellCheckError as exc:
                wx.CallAfter(self._status.SetLabel, f"Error: {exc}")
                corrections = []
            wx.CallAfter(self._on_paragraph_done, idx, corrections)

        t = __import__("threading").Thread(target=_fetch, daemon=True)
        t.start()

    def _on_paragraph_done(self, idx: int, corrections: list[SpellCorrection]) -> None:
        self._pending_corrections = corrections
        n = len(corrections)
        if n == 0:
            self._status.SetLabel(
                f"Paragraph {idx + 1}: no issues. Press Next Paragraph to continue."
            )
        else:
            self._status.SetLabel(
                f"Paragraph {idx + 1} checked. {n} issue{'s' if n != 1 else ''} found."
            )
        self._populate_list(corrections)
        self._next_btn.Enable(True)

    def _populate_list(self, corrections: list[SpellCorrection]) -> None:
        self._list.DeleteAllItems()
        for i, corr in enumerate(corrections):
            self._list.InsertItem(i, str(i + 1))
            self._list.SetItem(i, 1, corr.original)
            self._list.SetItem(i, 2, corr.correction)
            self._list.SetItem(i, 3, corr.context[:60])

    def _accept_current(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._pending_corrections):
            return
        self._all_accepted.append(self._pending_corrections[idx])
        self._list.DeleteItem(idx)
        self._pending_corrections.pop(idx)

    def _skip_current(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx >= 0 and idx < len(self._pending_corrections):
            self._list.DeleteItem(idx)
            self._pending_corrections.pop(idx)

    def _advance_paragraph(self) -> None:
        self._current_para += 1
        if self._current_para >= self._total:
            self._on_finish(None)
            return
        self._start_fetch_paragraph(self._current_para)

    def _on_finish(self, event: object) -> None:
        self._stop_event.set()
        if self._all_accepted:
            self._apply_to_document(self._all_accepted)
        self.dialog.Destroy()
