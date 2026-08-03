"""QUILL Calculator dialog -- an accessible scientific calculator that also does
statistics over selected numbers, CSV, and tables (Tools > Calculator).

Two things in one accessible window:

* **Calculate** a scientific/natural-language expression (``sqrt(264)``, ``10
  percent of 500``, ``2^10 + 5!``) -- the pocket-calculator half.
* **Data operations** over whatever numbers are in the input box -- sum,
  average, min, max, median, and more -- either over **all numbers**, **down
  each column**, or **across each row** of a pasted CSV or table. This is the
  half a calculator living inside a writing tool can do that a standalone one
  cannot.

The input box is pre-filled with the editor selection, so "select some numbers,
open the calculator" just works. Results can be copied or inserted at the cursor.
Every control is native and labeled; the dialog goes through the shared modal
contract. wx lives only here; all the math is in ``quill.core.calc``.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.calc import data_ops
from quill.core.calc.data_ops import AGGREGATES, DataError
from quill.core.calc.evaluator import CalculatorError, evaluate, format_result
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

_SCOPES = ("All numbers", "Down each column", "Across each row", "Full summary")


def _fmt(value: float | None) -> str:
    return "-" if value is None else format_result(value)


class CalculatorDialog:
    def __init__(
        self,
        parent: object,
        *,
        initial_text: str = "",
        insert_cb: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._insert_cb = insert_cb
        self._announce = announce_cb or (lambda _m: None)
        self._last_result = ""

        self.dialog = wx.Dialog(
            parent, title="Calculator", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                self.dialog,
                label="&Enter a calculation, or paste numbers, a column, or a table:",
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        self._input = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        set_accessible_name(self._input, "Calculation or data to work on")
        self._input.SetMinSize((-1, 90))
        self._input.SetValue(initial_text)
        root.Add(self._input, 1, wx.EXPAND | wx.ALL, 10)

        # -- expression row --
        calc_row = wx.BoxSizer(wx.HORIZONTAL)
        self._calc_btn = wx.Button(self.dialog, label="&Calculate expression")
        calc_row.Add(self._calc_btn, 0, wx.RIGHT, 6)
        calc_row.Add(
            wx.StaticText(
                self.dialog,
                label="(for example: sqrt(264), 10 percent of 500, 2^10 + 5!)",
            ),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        root.Add(calc_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- data-operation row --
        data_row = wx.BoxSizer(wx.HORIZONTAL)
        data_row.Add(
            wx.StaticText(self.dialog, label="Data &operation:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._op = wx.Choice(self.dialog, choices=[a.title() for a in AGGREGATES])
        set_accessible_name(self._op, "Data operation")
        self._op.SetSelection(0)
        data_row.Add(self._op, 0, wx.RIGHT, 6)
        data_row.Add(
            wx.StaticText(self.dialog, label="applied to:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._scope = wx.Choice(self.dialog, choices=list(_SCOPES))
        set_accessible_name(self._scope, "What to apply the data operation to")
        self._scope.SetSelection(0)
        data_row.Add(self._scope, 0, wx.RIGHT, 6)
        self._apply_btn = wx.Button(self.dialog, label="A&pply")
        data_row.Add(self._apply_btn, 0)
        root.Add(data_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # -- result --
        root.Add(wx.StaticText(self.dialog, label="&Result:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._result = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        set_accessible_name(self._result, "Result")
        self._result.SetMinSize((-1, 80))
        root.Add(self._result, 1, wx.EXPAND | wx.ALL, 10)

        # -- buttons --
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label="Cop&y Result")
        btn_row.Add(self._copy_btn, 0, wx.RIGHT, 6)
        if insert_cb is not None:
            self._insert_btn = wx.Button(self.dialog, label="&Insert Result at Cursor")
            btn_row.Add(self._insert_btn, 0, wx.RIGHT, 6)
            self._insert_btn.Bind(wx.EVT_BUTTON, lambda _e: self._insert_result())
        btn_row.AddStretchSpacer()
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Close"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        self.dialog.SetMinSize((560, 460))

        self._calc_btn.Bind(wx.EVT_BUTTON, lambda _e: self._calculate())
        self._apply_btn.Bind(wx.EVT_BUTTON, lambda _e: self._apply_data_op())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy_result())

    # -- actions ----------------------------------------------------------------

    def _set_result(self, text: str) -> None:
        self._last_result = text
        self._result.SetValue(text)
        self._announce(text)

    def _calculate(self) -> None:
        try:
            value = evaluate(self._input.GetValue())
        except CalculatorError as error:
            self._set_result(str(error))
            return
        self._set_result(format_result(value))

    def _apply_data_op(self) -> None:
        text = self._input.GetValue()
        op = AGGREGATES[self._op.GetSelection()]
        scope = _SCOPES[self._scope.GetSelection()]
        try:
            self._set_result(self._compute_data(text, op, scope))
        except DataError as error:
            self._set_result(str(error))

    def _compute_data(self, text: str, op: str, scope: str) -> str:
        if scope == "Full summary":
            return data_ops.summarize(data_ops.numbers_in(text)).line
        if scope == "All numbers":
            value = data_ops.aggregate(data_ops.numbers_in(text), op)
            return f"{op.title()}: {_fmt(value)}"
        table = data_ops.parse_table(text)
        if scope == "Down each column":
            results = data_ops.column_aggregates(table, op)
            labeled = [f"Column {i + 1}: {_fmt(v)}" for i, v in enumerate(results) if v is not None]
            return (
                f"{op.title()} down each column. " + "; ".join(labeled)
                if labeled
                else ("No numeric columns were found.")
            )
        # Across each row
        results = data_ops.row_aggregates(table, op)
        labeled = [f"Row {i + 1}: {_fmt(v)}" for i, v in enumerate(results) if v is not None]
        return (
            f"{op.title()} across each row. " + "; ".join(labeled)
            if labeled
            else ("No numeric rows were found.")
        )

    def _copy_result(self) -> None:
        wx = self._wx
        if not self._last_result:
            self._announce("There is no result to copy yet.")
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._last_result))
            finally:
                wx.TheClipboard.Close()
            self._announce("Result copied.")

    def _insert_result(self) -> None:
        if self._insert_cb is None or not self._last_result:
            self._announce("There is no result to insert yet.")
            return
        self._insert_cb(self._last_result)
        self._announce("Result inserted.")

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL, cancel_label="Close")
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Calculator", announce=self._announce)
        finally:
            self.dialog.Destroy()
