"""Calculator dialog: builds, evaluates expressions, runs data operations over
numbers/tables, and inserts results. Real wx.App, no modal shown."""

from __future__ import annotations

import pytest
import wx

from quill.ui.calculator_dialog import CalculatorDialog


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    a.Destroy()


def test_calculate_expression(app) -> None:
    dlg = CalculatorDialog(None, initial_text="10 percent of 500")
    try:
        dlg._calculate()
        assert dlg._result.GetValue() == "50"
    finally:
        dlg.dialog.Destroy()


def test_calculate_reports_errors_gracefully(app) -> None:
    dlg = CalculatorDialog(None, initial_text="1/0")
    try:
        dlg._calculate()
        assert "divide by zero" in dlg._result.GetValue()
    finally:
        dlg.dialog.Destroy()


def test_data_operation_all_numbers(app) -> None:
    dlg = CalculatorDialog(None, initial_text="10\n20\n30")
    try:
        dlg._op.SetSelection(0)  # Sum
        dlg._scope.SetStringSelection("All numbers")
        dlg._apply_data_op()
        assert "60" in dlg._result.GetValue()
    finally:
        dlg.dialog.Destroy()


def test_data_operation_down_columns(app) -> None:
    dlg = CalculatorDialog(None, initial_text="Item,Qty,Price\nA,3,1.50\nB,2,2.00")
    try:
        dlg._op.SetStringSelection("Sum")
        dlg._scope.SetStringSelection("Down each column")
        dlg._apply_data_op()
        out = dlg._result.GetValue()
        assert "Column 2: 5" in out  # Qty 3+2
        assert "Column 3: 3.5" in out  # Price 1.50+2.00
    finally:
        dlg.dialog.Destroy()


def test_full_summary(app) -> None:
    dlg = CalculatorDialog(None, initial_text="2 4 4 4 5 5 7 9")
    try:
        dlg._scope.SetStringSelection("Full summary")
        dlg._apply_data_op()
        out = dlg._result.GetValue()
        assert "8 numbers." in out and "Average 5." in out
    finally:
        dlg.dialog.Destroy()


def test_insert_result_uses_callback(app) -> None:
    inserted: list[str] = []
    dlg = CalculatorDialog(None, initial_text="2+2", insert_cb=inserted.append)
    try:
        dlg._calculate()
        dlg._insert_result()
        assert inserted == ["4"]
    finally:
        dlg.dialog.Destroy()
