"""AI grammar and style check review dialog for QUILL."""

from __future__ import annotations

from collections.abc import Callable

from quill.core.ai.grammar_check import CATEGORIES, GrammarIssue, apply_grammar_fixes
from quill.ui.dialog_contract import apply_modal_ids


class AIGrammarCheckDialog:
    """Review all grammar/style suggestions from the AI in one pass.

    Presents issues in a ListCtrl grouped by category.
    Returns (corrected_text, applied_count) on Apply, or (original, 0) on Cancel.
    """

    def __init__(
        self,
        parent: object,
        document_text: str,
        issues: list[GrammarIssue],
        show_modal_dialog: Callable,
    ) -> None:
        import wx

        self._wx = wx
        self._document_text = document_text
        self._issues = list(issues)
        self._show_modal = show_modal_dialog
        self._accepted: set[int] = set()
        self._skipped: set[int] = set()
        self.result_text = document_text
        self.applied_count = 0

        n = len(issues)
        self.dialog = wx.Dialog(
            parent,
            title=f"AI Grammar Check - {n} suggestion{'s' if n != 1 else ''}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(820, 600))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        n = len(self._issues)
        summary = wx.StaticText(
            self.dialog,
            label=(
                f"AI found {n} grammar and style suggestion{'s' if n != 1 else ''}. "
                "Select issues and use the review buttons to accept or skip each one."
            ),
        )
        summary.Wrap(760)
        root.Add(summary, 0, wx.ALL, 8)

        # Category filter row
        cat_row = wx.BoxSizer(wx.HORIZONTAL)
        cat_label = wx.StaticText(self.dialog, label="Filter by category:")
        self._cat_choice = wx.Choice(
            self.dialog,
            choices=["All categories"] + [CATEGORIES[k] for k in sorted(CATEGORIES)],
        )
        self._cat_choice.SetSelection(0)
        self._cat_choice.SetName("Filter by category")
        cat_row.Add(cat_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        cat_row.Add(self._cat_choice, 0)
        root.Add(cat_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Issues list
        self._list = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName("Grammar issues")
        self._list.InsertColumn(0, "#", width=40)
        self._list.InsertColumn(1, "Category", width=110)
        self._list.InsertColumn(2, "Original", width=180)
        self._list.InsertColumn(3, "Suggestion", width=180)
        self._list.InsertColumn(4, "Context", width=220)
        self._populate_list()
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Detail panel
        detail_box = wx.StaticBox(self.dialog, label="Issue detail")
        detail_sizer = wx.StaticBoxSizer(detail_box, wx.VERTICAL)
        self._explain_label = wx.StaticText(self.dialog, label="Select an issue above.")
        self._explain_label.Wrap(760)
        self._before_label = wx.StaticText(self.dialog, label="")
        self._after_label = wx.StaticText(self.dialog, label="")
        detail_sizer.Add(self._explain_label, 0, wx.ALL, 4)
        detail_sizer.Add(self._before_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        detail_sizer.Add(self._after_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        root.Add(detail_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Buttons - per item
        btn1 = wx.BoxSizer(wx.HORIZONTAL)
        self._accept_btn = wx.Button(self.dialog, label="&Accept (Alt+A)")
        self._skip_btn = wx.Button(self.dialog, label="&Skip (Alt+S)")
        self._accept_cat_btn = wx.Button(self.dialog, label="Accept &Category")
        self._skip_cat_btn = wx.Button(self.dialog, label="Skip Categ&ory")
        for b in (self._accept_btn, self._skip_btn, self._accept_cat_btn, self._skip_cat_btn):
            btn1.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Buttons - global
        btn2 = wx.BoxSizer(wx.HORIZONTAL)
        self._accept_all_btn = wx.Button(self.dialog, label="Accept &All Remaining")
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
        if self._issues:
            self._list.SetItemState(
                0,
                self._wx.LIST_STATE_SELECTED | self._wx.LIST_STATE_FOCUSED,
                self._wx.LIST_STATE_SELECTED | self._wx.LIST_STATE_FOCUSED,
            )
            self._update_detail(0)
        self._wx.CallAfter(self._list.SetFocus)

    def _populate_list(self, filter_category: str | None = None) -> None:
        self._list.DeleteAllItems()
        self._displayed_indices: list[int] = []
        for i, issue in enumerate(self._issues):
            if filter_category and issue.category != filter_category:
                continue
            row = self._list.GetItemCount()
            state = ""
            if i in self._accepted:
                state = " [Accepted]"
            elif i in self._skipped:
                state = " [Skipped]"
            self._list.InsertItem(row, str(i + 1))
            self._list.SetItem(row, 1, issue.category_label + state)
            self._list.SetItem(row, 2, issue.original[:40])
            self._list.SetItem(row, 3, issue.suggestion[:40])
            self._list.SetItem(row, 4, issue.context[:55])
            self._displayed_indices.append(i)

    def _update_detail(self, row: int) -> None:
        if not hasattr(self, "_displayed_indices") or row >= len(self._displayed_indices):
            return
        idx = self._displayed_indices[row]
        issue = self._issues[idx]
        self._explain_label.SetLabel(f"Explanation: {issue.explanation}")
        self._explain_label.Wrap(760)
        self._before_label.SetLabel(f"Before: {issue.original}")
        self._after_label.SetLabel(f"After: {issue.suggestion}")

    def _bind_events(self) -> None:
        wx = self._wx
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._cat_choice.Bind(wx.EVT_CHOICE, self._on_filter)
        self._accept_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept_current())
        self._skip_btn.Bind(wx.EVT_BUTTON, lambda _e: self._skip_current())
        self._accept_cat_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept_category())
        self._skip_cat_btn.Bind(wx.EVT_BUTTON, lambda _e: self._skip_category())
        self._accept_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept_all())
        self._reject_all_btn.Bind(wx.EVT_BUTTON, self._on_reject_all)
        self._apply_close_btn.Bind(wx.EVT_BUTTON, self._on_apply)

    def _on_select(self, event: object) -> None:
        row = self._list.GetFirstSelected()
        if row >= 0:
            self._update_detail(row)

    def _on_filter(self, event: object) -> None:
        sel = self._cat_choice.GetSelection()
        if sel <= 0:
            self._populate_list()
        else:
            category_label = self._cat_choice.GetString(sel)
            cat_key = next((k for k, v in CATEGORIES.items() if v == category_label), None)
            self._populate_list(filter_category=cat_key)

    def _current_real_index(self) -> int:
        row = self._list.GetFirstSelected()
        if row < 0 or not hasattr(self, "_displayed_indices"):
            return -1
        if row >= len(self._displayed_indices):
            return -1
        return self._displayed_indices[row]

    def _accept_current(self) -> None:
        idx = self._current_real_index()
        if idx < 0:
            return
        self._accepted.add(idx)
        self._skipped.discard(idx)
        self._refresh_and_advance()

    def _skip_current(self) -> None:
        idx = self._current_real_index()
        if idx < 0:
            return
        self._skipped.add(idx)
        self._accepted.discard(idx)
        self._refresh_and_advance()

    def _accept_category(self) -> None:
        row = self._list.GetFirstSelected()
        if row < 0 or not hasattr(self, "_displayed_indices"):
            return
        idx = self._displayed_indices[row]
        cat = self._issues[idx].category
        for i, issue in enumerate(self._issues):
            if issue.category == cat:
                self._accepted.add(i)
                self._skipped.discard(i)
        self._repopulate_current_filter()

    def _skip_category(self) -> None:
        row = self._list.GetFirstSelected()
        if row < 0 or not hasattr(self, "_displayed_indices"):
            return
        idx = self._displayed_indices[row]
        cat = self._issues[idx].category
        for i, issue in enumerate(self._issues):
            if issue.category == cat:
                self._skipped.add(i)
                self._accepted.discard(i)
        self._repopulate_current_filter()

    def _accept_all(self) -> None:
        for i in range(len(self._issues)):
            self._accepted.add(i)
            self._skipped.discard(i)
        self._repopulate_current_filter()

    def _refresh_and_advance(self) -> None:
        row = self._list.GetFirstSelected()
        self._repopulate_current_filter()
        next_row = min(row, self._list.GetItemCount() - 1)
        if next_row >= 0:
            self._list.SetItemState(
                next_row,
                self._wx.LIST_STATE_SELECTED,
                self._wx.LIST_STATE_SELECTED,
            )
            self._update_detail(next_row)

    def _repopulate_current_filter(self) -> None:
        sel = self._cat_choice.GetSelection()
        if sel <= 0:
            self._populate_list()
        else:
            category_label = self._cat_choice.GetString(sel)
            cat_key = next((k for k, v in CATEGORIES.items() if v == category_label), None)
            self._populate_list(filter_category=cat_key)

    def _on_reject_all(self, event: object) -> None:
        self.result_text = self._document_text
        self.applied_count = 0
        self.dialog.EndModal(self._wx.ID_CANCEL)

    def _on_apply(self, event: object) -> None:
        self.result_text, self.applied_count = apply_grammar_fixes(
            self._document_text, self._issues, self._accepted
        )
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[str, int]:
        self._show_modal(self.dialog, "AI Grammar Check")
        result_text, applied_count = self.result_text, self.applied_count
        self.dialog.Destroy()
        return result_text, applied_count
