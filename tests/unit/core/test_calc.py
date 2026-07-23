"""QUILL Calculator core: the safe expression evaluator (arithmetic, scientific,
natural-language, and its refusal to execute anything unsafe) and the
document-aware data operations (numbers, tables, aggregates, summary)."""

from __future__ import annotations

import math

import pytest

from quill.core.calc import data_ops
from quill.core.calc.data_ops import DataError
from quill.core.calc.evaluator import CalculatorError, evaluate, format_result, normalize

# -- evaluator: arithmetic ----------------------------------------------------


def test_precedence_and_parentheses() -> None:
    assert evaluate("4 + 12 / 2") == 10
    assert evaluate("(4 + 12) / 2") == 8
    assert evaluate("2 + 3 * 4") == 14
    assert evaluate("-5 + 3") == -2


def test_power_caret_and_star_star() -> None:
    assert evaluate("2^10") == 1024
    assert evaluate("2 ** 10") == 1024


def test_scientific_functions_and_constants() -> None:
    assert evaluate("sqrt(264)") == pytest.approx(16.2480768, rel=1e-6)
    assert evaluate("5!") == 120  # factorial postfix
    assert evaluate("factorial(5)") == 120
    assert evaluate("fact(5)") == 120
    assert evaluate("sin(pi/6)") == pytest.approx(0.5, abs=1e-9)
    assert evaluate("cosd(60)") == pytest.approx(0.5, abs=1e-9)
    assert evaluate("log10(1000)") == pytest.approx(3.0)
    assert evaluate("max(3, 9, 5)") == 9
    assert evaluate("e") == pytest.approx(math.e)


# -- evaluator: natural language (Leasey parity) ------------------------------


def test_natural_language_forms() -> None:
    assert evaluate("what is the square root of 264") == pytest.approx(16.248, rel=1e-4)
    assert evaluate("what is 10 percent of 500?") == 50
    assert evaluate("15% of 240") == 36
    assert evaluate("25%") == 0.25
    assert evaluate("6 x 7") == 42  # 'x' as a multiply sign
    assert evaluate("100 minus 40") == 60


def test_normalize_is_pure_text_transform() -> None:
    assert normalize("What is 10 percent of 500?") == "(10/100)*500"
    assert normalize("2^8") == "2**8"


# -- evaluator: safety --------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "__import__('os')",
        "os.system('x')",
        "open('f')",
        "().__class__",
        "1 if True else 2",
        "[1, 2, 3]",
        "lambda: 1",
        "a = 1",
    ],
)
def test_rejects_unsafe_or_non_math(bad: str) -> None:
    with pytest.raises(CalculatorError):
        evaluate(bad)


def test_math_errors_are_friendly() -> None:
    with pytest.raises(CalculatorError, match="divide by zero"):
        evaluate("1/0")
    with pytest.raises(CalculatorError):
        evaluate("sqrt(-1)")  # domain error
    with pytest.raises(CalculatorError):
        evaluate("")  # nothing to calculate


def test_unknown_name_and_function() -> None:
    with pytest.raises(CalculatorError, match="not a known name"):
        evaluate("foo + 1")
    with pytest.raises(CalculatorError, match="not a known function"):
        evaluate("bogus(2)")


def test_format_result_trims() -> None:
    assert format_result(10.0) == "10"
    assert format_result(3.14159) == "3.14159"
    assert format_result(evaluate("1/3")).startswith("0.3333")


# -- data ops: number parsing -------------------------------------------------


def test_to_number_handles_money_percent_negatives() -> None:
    assert data_ops.to_number("$1,234.50") == 1234.5
    assert data_ops.to_number("45%") == 0.45
    assert data_ops.to_number("(1,200)") == -1200.0
    assert data_ops.to_number("hello") is None
    assert data_ops.to_number("") is None


def test_numbers_in_free_text() -> None:
    assert data_ops.numbers_in("I spent 12 and 3.50 today") == [12.0, 3.5]


# -- data ops: tables ---------------------------------------------------------

_CSV = "Item,Qty,Price\nApples,3,1.50\nPears,2,2.00\nPlums,5,0.80"
_MD = "| Item | Qty | Price |\n| --- | --- | --- |\n| Apples | 3 | 1.50 |\n| Pears | 2 | 2.00 |"
_WS = "Apples 3 1.50\nPears 2 2.00"


def test_detect_delimiter() -> None:
    assert data_ops.detect_delimiter(_CSV) == ","
    assert data_ops.detect_delimiter(_MD) == "|"
    assert data_ops.detect_delimiter(_WS) == "ws"
    assert data_ops.detect_delimiter("a\tb\tc") == "\t"


def test_parse_table_markdown_drops_separator_row() -> None:
    table = data_ops.parse_table(_MD)
    assert table[0] == ["Item", "Qty", "Price"]
    assert ["Apples", "3", "1.50"] in table
    assert len(table) == 3  # header + 2 data rows, separator dropped


def test_column_values_skips_header() -> None:
    table = data_ops.parse_table(_CSV)
    assert data_ops.column_values(table, 2) == [1.5, 2.0, 0.8]  # Price column


# -- data ops: aggregates -----------------------------------------------------


def test_aggregate_all_ops_and_aliases() -> None:
    v = [1.0, 2.0, 3.0, 4.0]
    assert data_ops.aggregate(v, "sum") == 10
    assert data_ops.aggregate(v, "total") == 10  # alias
    assert data_ops.aggregate(v, "average") == 2.5
    assert data_ops.aggregate(v, "mean") == 2.5  # alias
    assert data_ops.aggregate(v, "minimum") == 1
    assert data_ops.aggregate(v, "maximum") == 4
    assert data_ops.aggregate(v, "count") == 4
    assert data_ops.aggregate(v, "product") == 24
    assert data_ops.aggregate(v, "median") == 2.5
    assert data_ops.aggregate(v, "range") == 3
    assert data_ops.aggregate(v, "standard deviation") == pytest.approx(1.290994, rel=1e-5)


def test_aggregate_errors() -> None:
    assert data_ops.aggregate([], "count") == 0  # count of nothing is fine
    with pytest.raises(DataError):
        data_ops.aggregate([], "sum")
    with pytest.raises(DataError):
        data_ops.aggregate([5.0], "stdev")  # needs two


def test_column_and_row_aggregates() -> None:
    table = data_ops.parse_table(_CSV)
    # Column sums: the Item column has no numbers (None); Qty=10, Price=4.30.
    cols = data_ops.column_aggregates(table, "sum")
    assert cols[0] is None
    assert cols[1] == 10  # 3+2+5
    assert cols[2] == pytest.approx(4.30)
    # Row sums include the header row (no numbers -> None) then each data row.
    rows = data_ops.row_aggregates(table, "sum")
    assert rows[0] is None  # header
    assert rows[1] == pytest.approx(4.5)  # 3 + 1.50


def test_summarize() -> None:
    s = data_ops.summarize([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert s.count == 8
    assert s.total == 40
    assert s.average == 5.0
    assert s.minimum == 2 and s.maximum == 9
    assert s.value_range == 7
    # Sample standard deviation (statistics.stdev), matching aggregate("stdev").
    assert s.stdev == pytest.approx(2.13808993, rel=1e-6)
    assert "8 numbers." in s.line and "Sum 40." in s.line
