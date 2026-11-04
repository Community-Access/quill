"""Canonical expression text: how BAF and QUILL both write an expression tree.

Split from :mod:`expr` for GATE-11. The rules are BAF's
(``docs/expression-language.md``, "Canonical text"): ``#id`` references,
text as JSON with non-ASCII and ``/`` as themselves, numbers as JSON writes
them (keeping ``.0``), flat ``and``/``or`` chains, and parentheses only where
they are needed.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

Node = dict[str, Any]

PRECEDENCE: dict[str, int] = {
    "or": 1, "and": 2, "not": 3,
    "is": 4, "is_not": 4, "lt": 4, "le": 4, "gt": 4, "ge": 4, "one_of": 4,
    "not_one_of": 4, "empty": 4, "not_empty": 4, "contains": 4, "not_contains": 4,
    "starts_with": 4, "ends_with": 4, "before": 4, "after": 4, "within": 4,
    "add": 5, "sub": 5, "mul": 6, "div": 6, "mod": 6, "neg": 7,
}  # fmt: skip


# -- canonical text ---------------------------------------------------------------


def quote(s: str) -> str:
    """Text as the model and BFL write it: JSON, non-ASCII and / kept as they are."""
    return json.dumps(str(s), ensure_ascii=False)


def number_text(v: int | float, float_mark: bool = True) -> str:
    """A number as plain decimal digits, never in exponent form (BAF's ``number_text``).

    Canonical text must read back, and the grammar has no exponents, so 1e17 is
    ``100000000000000000.0`` and 1e-5 is ``0.00001``. An integral float keeps
    ``.0`` when ``float_mark`` is set (canonical text) and drops it otherwise
    (sentences), as PHP's ``json_encode`` with and without
    ``JSON_PRESERVE_ZERO_FRACTION``. The digits are the shortest that read back,
    which is what PHP's ``serialize_precision`` of -1 gives.
    """
    if isinstance(v, int):
        return str(v)
    if not math.isfinite(v):
        return "0"
    text = format(Decimal(repr(v)), "f")
    if float(v).is_integer():
        text = text.split(".")[0]
        return text + ".0" if float_mark else text
    return text


def php_json_float(v: float, float_mark: bool = False) -> str:
    """A float exactly as PHP's ``json_encode`` writes it, exponent form included.

    BAF's evaluator turns numbers into text this way (``str()``), so ``#n contains "e"``
    can see an exponent: plain digits from 1e-4 up to below 1e17, else ``1.0e+17``.
    """
    if not math.isfinite(v):
        return "0"
    d = Decimal(repr(v))
    adjusted = d.adjusted() if v != 0 else 0
    if -5 < adjusted < 17:
        return number_text(v, float_mark)
    sign, digits, _exp = d.as_tuple()
    figures = "".join(str(x) for x in digits).rstrip("0") or "0"
    mantissa = figures[0] + "." + (figures[1:] or "0")
    return (
        ("-" if sign else "")
        + mantissa
        + "e"
        + ("+" if adjusted >= 0 else "-")
        + str(abs(adjusted))
    )


def literal_text(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return number_text(v)
    return quote(v)


def _prec(node: Node) -> int:
    if node.get("type") == "op":
        return PRECEDENCE[node["op"]]
    value = node.get("value")
    if (
        node.get("type") == "literal"
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value < 0
    ):
        return 7
    return 8


def _child(node: Node, minimum: int) -> str:
    text = to_text(node)
    return f"({text})" if _prec(node) < minimum else text


_INFIX = {
    "is": "is", "is_not": "is not", "lt": "<", "le": "<=", "gt": ">", "ge": ">=",
    "contains": "contains", "not_contains": "does not contain", "starts_with": "starts with",
    "ends_with": "ends with", "before": "is before", "after": "is after",
    "add": "+", "sub": "-", "mul": "*", "div": "/", "mod": "%",
}  # fmt: skip


def to_text(node: Node) -> str:  # noqa: C901
    """A tree as canonical text."""
    kind = node["type"]
    if kind == "literal":
        return literal_text(node["value"])
    if kind == "ref":
        return "#" + str(node["field"])
    if kind == "var":
        return str(node["name"])
    if kind == "list":
        return "[" + ", ".join(_child(n, 5) for n in node["items"]) + "]"
    if kind == "call":
        return str(node["name"]) + "(" + ", ".join(to_text(a) for a in node["args"]) + ")"
    a = node["args"]
    name = node["op"]
    if name in ("or", "and"):
        p = PRECEDENCE[name]
        return f" {name} ".join(_child(n, p + 1) for n in a)
    if name == "not":
        return "not " + _child(a[0], 3)
    if name == "neg":
        return "-" + _child(a[0], 7)
    if name == "empty":
        return _child(a[0], 5) + " is empty"
    if name == "not_empty":
        return _child(a[0], 5) + " is not empty"
    if name in ("one_of", "not_one_of"):
        word = " is one of " if name == "one_of" else " is not one of "
        return _child(a[0], 5) + word + to_text(a[1])
    if name == "within":
        text = _child(a[0], 5) + " is within " + _child(a[1], 5) + " days"
        if len(a) > 2:
            text += " of " + _child(a[2], 5)
        return text
    p = PRECEDENCE[name]
    if p == 4:
        return _child(a[0], 5) + " " + _INFIX[name] + " " + _child(a[1], 5)
    return _child(a[0], p) + " " + _INFIX[name] + " " + _child(a[1], p + 1)
