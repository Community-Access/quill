"""Document-aware calculations for the QUILL Calculator.

Turns a block of selected text into numbers and does statistics on them, and
recognizes tabular data (CSV, TSV, pipe/markdown tables, or whitespace columns)
so it can sum, average, and otherwise aggregate **down a column** or **across a
row** -- the thing a calculator inside a writing tool should do that a pocket
calculator cannot. Currency symbols, thousands separators, percent signs, and
parenthesized negatives are all understood.

Pure, wx-free, strict-typed. No ``eval`` -- this only parses numbers and text.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from quill.core.error_codes import CodedError

#: The aggregate operations the calculator offers over a set of numbers.
AGGREGATES = (
    "sum",
    "average",
    "minimum",
    "maximum",
    "count",
    "product",
    "median",
    "range",
    "standard deviation",
)

_NUMBER_RE = re.compile(r"[-+]?\(?\$?\s*\d[\d,]*(?:\.\d+)?\)?%?")


class DataError(CodedError):
    """A data operation could not be completed (e.g. no numbers found)."""

    code = "QUILL-CALC-DATA-INVALID"


def to_number(cell: str) -> float | None:
    """Parse one cell/token into a number, or None if it is not numeric.

    Understands ``$1,234.50``, ``1 234``, ``45%`` (-> 0.45), and accounting
    negatives ``(1,200)`` (-> -1200). Returns None for empty or non-numeric text.
    """
    text = cell.strip()
    if not text:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()
    text = text.replace("$", "").replace("€", "").replace("£", "")
    text = text.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"[-+]?\d*\.?\d+", text):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if percent:
        value /= 100.0
    return -value if negative else value


def numbers_in(text: str) -> list[float]:
    """Every number found anywhere in a block of free text, in order. Ignores
    non-numeric words, so 'I spent 12 and 3.50 today' -> [12.0, 3.5]."""
    found: list[float] = []
    for match in _NUMBER_RE.findall(text):
        value = to_number(match)
        if value is not None:
            found.append(value)
    return found


# -- tabular data -------------------------------------------------------------


def detect_delimiter(text: str) -> str:
    """Guess a table's column delimiter from the first few non-empty lines:
    pipe (markdown/psv), tab (TSV), comma (CSV), else runs of whitespace."""
    sample = [ln for ln in text.splitlines() if ln.strip()][:10]
    if not sample:
        return ","
    joined = "\n".join(sample)
    if "|" in joined:
        return "|"
    if "\t" in joined:
        return "\t"
    if "," in joined:
        return ","
    return "ws"  # whitespace-separated columns


def _is_separator_row(cells: list[str]) -> bool:
    """A markdown header underline like ``--- | :--: | ---``."""
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells if c.strip())


def parse_table(text: str) -> list[list[str]]:
    """Split a block into rows of string cells. Handles markdown tables (outer
    pipes and the ``---`` separator row are dropped) and whitespace columns."""
    delimiter = detect_delimiter(text)
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if delimiter == "ws":
            cells = line.split()
        elif delimiter == "|":
            stripped = line.strip().strip("|")
            cells = [c.strip() for c in stripped.split("|")]
        else:
            cells = [c.strip() for c in line.split(delimiter)]
        if _is_separator_row(cells):
            continue
        rows.append(cells)
    return rows


def column_values(table: list[list[str]], index: int) -> list[float]:
    """The numeric values in one column (non-numeric cells, e.g. a header, are
    skipped)."""
    values: list[float] = []
    for row in table:
        if index < len(row):
            number = to_number(row[index])
            if number is not None:
                values.append(number)
    return values


def row_values(row: list[str]) -> list[float]:
    """The numeric values in one row."""
    return [n for n in (to_number(c) for c in row) if n is not None]


def column_count(table: list[list[str]]) -> int:
    return max((len(r) for r in table), default=0)


# -- aggregation --------------------------------------------------------------


def aggregate(values: list[float], op: str) -> float:
    """Apply one named aggregate to a list of numbers.

    ``op`` is one of :data:`AGGREGATES` (case-insensitive; a few aliases like
    'mean', 'avg', 'total', 'min', 'max', 'stdev' are accepted). Raises
    :class:`DataError` when there are no numbers (or too few for the operation).
    """
    name = op.strip().lower()
    aliases = {
        "mean": "average",
        "avg": "average",
        "total": "sum",
        "min": "minimum",
        "max": "maximum",
        "stdev": "standard deviation",
        "std": "standard deviation",
        "sd": "standard deviation",
    }
    name = aliases.get(name, name)
    if name == "count":
        return float(len(values))
    if not values:
        raise DataError("No numbers were found to calculate with.")
    if name == "sum":
        return float(sum(values))
    if name == "average":
        return statistics.fmean(values)
    if name == "minimum":
        return float(min(values))
    if name == "maximum":
        return float(max(values))
    if name == "median":
        return float(statistics.median(values))
    if name == "range":
        return float(max(values) - min(values))
    if name == "product":
        result = 1.0
        for v in values:
            result *= v
        return result
    if name == "standard deviation":
        if len(values) < 2:
            raise DataError("Standard deviation needs at least two numbers.")
        return statistics.stdev(values)
    raise DataError(f"'{op}' is not a calculation I know.")


def column_aggregates(table: list[list[str]], op: str) -> list[float | None]:
    """Apply an aggregate down each column; None where a column has no numbers."""
    result: list[float | None] = []
    for i in range(column_count(table)):
        values = column_values(table, i)
        result.append(aggregate(values, op) if (values or op.lower() == "count") else None)
    return result


def row_aggregates(table: list[list[str]], op: str) -> list[float | None]:
    """Apply an aggregate across each row; None where a row has no numbers."""
    result: list[float | None] = []
    for row in table:
        values = row_values(row)
        result.append(aggregate(values, op) if (values or op.lower() == "count") else None)
    return result


@dataclass(slots=True)
class DataSummary:
    """A full statistical summary of a set of numbers, for one-glance reporting."""

    count: int
    total: float
    average: float
    minimum: float
    maximum: float
    median: float
    value_range: float
    stdev: float | None  # None when fewer than two values

    @property
    def line(self) -> str:
        """A fully spoken one-line summary."""
        from quill.core.calc.evaluator import format_result as _f

        parts = [
            f"{self.count} numbers.",
            f"Sum {_f(self.total)}.",
            f"Average {_f(self.average)}.",
            f"Minimum {_f(self.minimum)}, maximum {_f(self.maximum)}.",
            f"Median {_f(self.median)}.",
            f"Range {_f(self.value_range)}.",
        ]
        if self.stdev is not None:
            parts.append(f"Standard deviation {_f(self.stdev)}.")
        return " ".join(parts)


def summarize(values: list[float]) -> DataSummary:
    """Compute a full :class:`DataSummary` for a list of numbers."""
    if not values:
        raise DataError("No numbers were found to summarize.")
    return DataSummary(
        count=len(values),
        total=float(sum(values)),
        average=statistics.fmean(values),
        minimum=float(min(values)),
        maximum=float(max(values)),
        median=float(statistics.median(values)),
        value_range=float(max(values) - min(values)),
        stdev=statistics.stdev(values) if len(values) >= 2 else None,
    )
