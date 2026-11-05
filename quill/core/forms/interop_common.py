"""What every import shares: the report, and turning another tool's rules into ours.

Anything a source has that the model cannot hold is named in the import
report, never silently dropped (17a.15, point 4). Each importer also keeps
those properties under ``extensions.<tool>`` (QAF passes extensions back
unchanged), so exporting to the same tool gives them back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.errors import ExpressionError


@dataclass
class ImportResult:
    model: M.Model
    #: One plain sentence per thing the model could not hold, or to check.
    report: list[str] = field(default_factory=list)


def safe_id(text: str, taken: set[str]) -> str:
    """An ID the model accepts (letters, digits, underscores, not starting with a digit)."""
    base = re.sub(r"[^A-Za-z0-9_]+", "_", str(text)).strip("_") or "field"
    if base[0].isdigit():
        base = "f_" + base
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    taken.add(candidate)
    return candidate


def convert_expression(text: str, rewrites: list[tuple[str, str]]) -> str | None:
    """Another tool's expression as canonical model text, or None if it will not go."""
    out = str(text)
    for pattern, replacement in rewrites:
        out = re.sub(pattern, replacement, out, flags=re.I)
    try:
        return E.canonical(out)
    except ExpressionError:
        return None


def clean(item: dict[str, object]) -> dict[str, object]:
    """Leave out empty values, in the model's key order."""
    from quill.core.forms.bfl_read_parts import ITEM_ORDER

    out = {k: item[k] for k in ITEM_ORDER if k in item and item[k] not in (None, "", {}, [])}
    if "items" in item and item.get("type") in ("section", "repeater"):
        out["items"] = item["items"]
    if "columns" in item:
        out["columns"] = item["columns"]
    return out
