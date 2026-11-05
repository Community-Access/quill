"""Working an expression out: a port of ``BAF_Expression::evaluate``.

The context is BAF's, all keys optional:

- ``values``: field ID to answer (text, number, true or false, a list, or None);
- ``today``: ``"YYYY-MM-DD"`` (today in UTC when absent);
- ``user`` and ``query``: key to value, for ``user("key")`` and ``query("key")``;
- ``geo``: the value of ``geo()``;
- ``scores``: field ID to points, for ``score(#field)``; ``score``: the total.

The rules (empty, truth, ``is``, dates, arithmetic) are written down in BAF's
``docs/expression-language.md``; Fill It In Yourself relies on them matching
the site exactly.
"""

from __future__ import annotations

import datetime as dt
import math
import re
from collections.abc import Mapping
from typing import Any

from quill.core.forms import expr as E

_NUMERIC = re.compile(r"^\s*-?(\d+(\.\d*)?|\.\d+)\s*$")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:$|[T ])")


def _arr(v: Any) -> bool:
    """PHP's ``is_array``: a list, or an object (a composite answer such as a name)."""
    return isinstance(v, (list, dict))


def _vals(v: Any) -> list[Any]:
    return list(v.values()) if isinstance(v, dict) else list(v)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def truthy(v: Any) -> bool:
    if v is None or v is False or (isinstance(v, str) and v == "") or (_arr(v) and not v):
        return False
    if _is_num(v):
        return bool(v != 0)
    return True


def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if v is False:
        return False
    if isinstance(v, list):
        return all(is_empty(x) for x in v)
    if isinstance(v, dict):
        return all(is_empty(x) for x in v.values())
    if isinstance(v, str):
        return v.strip(" \t\n\r\0\x0b") == ""
    return False


def to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if _arr(v):
        return ", ".join(to_str(x) for x in _vals(v))
    if isinstance(v, float):
        return E.php_json_float(v)
    return str(v)


def is_numeric_value(v: Any) -> bool:
    return _is_num(v) or (isinstance(v, str) and _NUMERIC.match(v) is not None)


def num(v: Any) -> int | float:
    if _is_num(v):
        return v  # type: ignore[no-any-return]
    if v is True:
        return 1
    if _arr(v):
        total: int | float = 0
        for x in _vals(v):
            total += num(x)
        return total
    if isinstance(v, str) and _NUMERIC.match(v):
        text = v.strip()
        return float(text) if "." in text else int(text)
    return 0


def normalize_number(n: Any) -> Any:
    if isinstance(n, float) and math.isfinite(n) and n.is_integer() and abs(n) < 1e15:
        return int(n)
    return n


def _ascii_lower(s: str) -> str:
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def scalar_equals(a: Any, b: Any) -> bool:
    a = "" if a is None else a
    b = "" if b is None else b
    if is_numeric_value(a) and is_numeric_value(b):
        return bool(num(a) == num(b))
    return to_str(a) == to_str(b)


def contains(a: Any, b: Any) -> bool:
    if _arr(a):
        return any(scalar_equals(x, b) for x in _vals(a))
    needle = _ascii_lower(to_str(b))
    return needle == "" or needle in _ascii_lower(to_str(a))


def equals(a: Any, b: Any) -> bool:
    if _arr(a) and _arr(b):
        return len(a) == len(b) and all(contains(a, x) for x in _vals(b))
    if _arr(a):
        return contains(a, b)
    return scalar_equals(a, b)


def parse_date(v: Any) -> tuple[int, int, int] | None:
    if not isinstance(v, str):
        return None
    m = _DATE.match(v)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        dt.date(y, mo, d)
    except ValueError:
        return None
    return y, mo, d


def day_number(v: Any) -> int | None:
    p = parse_date(v)
    if p is None:
        return None
    return (dt.date(*p) - dt.date(1970, 1, 1)).days


def day_to_date(z: int) -> str:
    return (dt.date(1970, 1, 1) + dt.timedelta(days=z)).isoformat()


def compare(a: Any, b: Any) -> int | None:
    if is_empty(a) or is_empty(b):
        return None
    if is_numeric_value(a) and is_numeric_value(b):
        x, y = num(a), num(b)
        return (x > y) - (x < y)
    da, db = day_number(a), day_number(b)
    if da is not None and db is not None:
        return (da > db) - (da < db)
    if _arr(a) or _arr(b):
        x, y = num(a), num(b)
        return (x > y) - (x < y)
    sa, sb = to_str(a).encode("utf-8"), to_str(b).encode("utf-8")
    return (sa > sb) - (sa < sb)


def today(context: Mapping[str, Any]) -> str:
    if "today" in context and context["today"] is not None:
        return str(context["today"])
    return dt.datetime.now(dt.UTC).date().isoformat()


def _pow10(power: int) -> float:
    return float(10**power) if 0 <= power <= 22 else 10.0**power


def _half_up(value: float) -> float:
    return math.floor(value + 0.5) if value >= 0.0 else math.ceil(value - 0.5)


def _php_round(x: int | float, places: int) -> float:
    """PHP 8's ``round()``, pre-rounding included: round(0.49999999999999994) is 1."""
    value = float(x)
    if not math.isfinite(value) or value == 0.0:
        return value
    precision_places = 14 - math.floor(math.log10(abs(value)))
    f1 = _pow10(abs(places))
    if precision_places > places and precision_places - 15 < places:
        use = max(precision_places, -4 * 15)
        basic = value * _pow10(use) if use >= 0 else value / _pow10(-use)
        tmp = _half_up(basic)
        use = max(places - use, -4 * 15)
        tmp = tmp / _pow10(abs(use))
    else:
        tmp = value * f1 if places >= 0 else value / f1
        if abs(tmp) >= 1e15:
            return value
    tmp = _half_up(tmp)
    if abs(places) < 23:
        tmp = tmp / f1 if places > 0 else tmp * f1
    else:
        tmp = float(f"{tmp:15f}e{-places}")
    return tmp


def evaluate(node: E.Node | str, context: Mapping[str, Any] | None = None) -> Any:  # noqa: C901
    """Work an expression (a tree or text) out in ``context``."""
    ctx: Mapping[str, Any] = context or {}
    if isinstance(node, str):
        node = E.parse(node)
    kind = node["type"]
    if kind == "literal":
        return node["value"]
    if kind == "ref":
        return (ctx.get("values") or {}).get(node["field"])
    if kind == "var":
        return ctx.get("score", 0)
    if kind == "list":
        return [evaluate(n, ctx) for n in node["items"]]
    if kind == "call":
        return _call(node["name"], node["args"], ctx)
    a = node["args"]
    name = node["op"]

    def ev(i: int) -> Any:
        return evaluate(a[i], ctx)

    if name == "or":
        return any(truthy(evaluate(x, ctx)) for x in a)
    if name == "and":
        return all(truthy(evaluate(x, ctx)) for x in a)
    if name == "not":
        return not truthy(ev(0))
    if name == "neg":
        return normalize_number(-num(ev(0)))
    if name == "empty":
        return is_empty(ev(0))
    if name == "not_empty":
        return not is_empty(ev(0))
    if name == "is":
        return equals(ev(0), ev(1))
    if name == "is_not":
        return not equals(ev(0), ev(1))
    if name in ("lt", "le", "gt", "ge"):
        c = compare(ev(0), ev(1))
        if c is None:
            return False
        return {"lt": c < 0, "le": c <= 0, "gt": c > 0, "ge": c >= 0}[name]
    if name in ("one_of", "not_one_of"):
        left, options = ev(0), ev(1)
        options = _vals(options) if _arr(options) else [options]
        lefts = _vals(left) if _arr(left) else [left]
        hit = any(scalar_equals(x, y) for x in lefts for y in options)
        return hit if name == "one_of" else not hit
    if name in ("contains", "not_contains"):
        hit = contains(ev(0), ev(1))
        return hit if name == "contains" else not hit
    if name in ("starts_with", "ends_with"):
        left_s, right_s = _ascii_lower(to_str(ev(0))), _ascii_lower(to_str(ev(1)))
        if right_s == "":
            return True
        return left_s.startswith(right_s) if name == "starts_with" else left_s.endswith(right_s)
    if name in ("before", "after"):
        x, y = day_number(ev(0)), day_number(ev(1))
        if x is None or y is None:
            return False
        return x < y if name == "before" else x > y
    if name == "within":
        x = day_number(ev(0))
        n = num(ev(1))
        y = day_number(ev(2) if len(a) > 2 else today(ctx))
        if x is None or y is None:
            return False
        return abs(x - y) <= n
    if name in ("add", "sub"):
        left, right = ev(0), ev(1)
        ld, rd = day_number(left), day_number(right)
        if ld is not None and rd is None:
            days = int(_php_round(num(right), 0))
            return day_to_date(ld + days if name == "add" else ld - days)
        if name == "sub" and ld is not None and rd is not None:
            return ld - rd
        return normalize_number(num(left) + num(right) if name == "add" else num(left) - num(right))
    if name == "mul":
        return normalize_number(num(ev(0)) * num(ev(1)))
    if name in ("div", "mod"):
        d = num(ev(1))
        if d == 0:
            return None
        left_n = num(ev(0))
        return normalize_number(left_n / d if name == "div" else math.fmod(left_n, d))
    return None


def _call(name: str, args: list[E.Node], ctx: Mapping[str, Any]) -> Any:  # noqa: C901
    def arg(i: int) -> Any:
        return evaluate(args[i], ctx)

    def values() -> list[Any]:
        out: list[Any] = []
        for n in args:
            v = evaluate(n, ctx)
            out.extend(_vals(v) if _arr(v) else [v])
        return out

    if name == "today":
        return today(ctx)
    if name == "date":
        d = day_number(arg(0))
        return None if d is None else day_to_date(d)
    if name == "days_between":
        x, y = day_number(arg(0)), day_number(arg(1))
        return None if x is None or y is None else y - x
    if name == "age":
        born, now = parse_date(arg(0)), parse_date(today(ctx))
        if not born or not now:
            return None
        years = now[0] - born[0]
        if now[1] < born[1] or (now[1] == born[1] and now[2] < born[2]):
            years -= 1
        return years
    if name == "abs":
        return normalize_number(abs(num(arg(0))))
    if name == "round":
        places = int(num(arg(1))) if len(args) > 1 else 0
        return normalize_number(_php_round(num(arg(0)), places))
    if name in ("floor", "ceil"):
        f = math.floor if name == "floor" else math.ceil
        return normalize_number(float(f(num(arg(0)))))
    if name in ("min", "max", "sum", "avg"):
        nums = [num(v) for v in values() if not is_empty(v)]
        if name == "sum":
            return normalize_number(sum(nums))
        if not nums:
            return None
        if name == "avg":
            return normalize_number(sum(nums) / len(nums))
        return normalize_number(min(nums) if name == "min" else max(nums))
    if name == "count":
        v = arg(0)
        if _arr(v):
            return sum(1 for x in _vals(v) if not is_empty(x))
        return 0 if is_empty(v) else 1
    if name == "length":
        return len(to_str(arg(0)))
    if name == "if":
        return arg(1) if truthy(arg(0)) else arg(2)
    if name == "score":
        ref = args[0]
        key = ref["field"] if ref["type"] == "ref" else to_str(arg(0))
        return (ctx.get("scores") or {}).get(key, 0)
    if name in ("user", "query"):
        return (ctx.get(name) or {}).get(to_str(arg(0)))
    if name == "geo":
        return ctx.get("geo")
    return None


def holds(node: E.Node | str, context: Mapping[str, Any] | None = None) -> bool:
    return truthy(evaluate(node, context))
