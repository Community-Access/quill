"""What every import shares: the report of what a source had that the model did not.

17a.15 point 4: anything a source has that the model cannot hold is listed
in an import report, never silently dropped. Each importer also keeps those
properties in the field's ``settings`` under the notation's name, so exporting
back to the same tool gives them back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.forms import expr as E
from quill.core.forms.errors import ExpressionError
from quill.core.forms.model import Form


@dataclass
class ImportResult:
    form: Form
    #: One plain sentence per thing the model could not hold.
    report: list[str] = field(default_factory=list)


def safe_id(text: str, taken: set[str]) -> str:
    """A field id the model accepts (letters, digits, underscores), unique in ``taken``."""
    base = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_") or "field"
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    taken.add(candidate)
    return candidate


def convert_expression(text: str, rewrites: list[tuple[str, str]]) -> str | None:
    """Another tool's expression in the model's language, or None if it will not go."""
    out = text
    for pattern, replacement in rewrites:
        out = re.sub(pattern, replacement, out, flags=re.I)
    try:
        return E.normalise(out)
    except ExpressionError:
        return None
