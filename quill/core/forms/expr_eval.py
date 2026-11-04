"""Working out an expression against a set of answers.

The meaning follows BAF's site (``public/js/baf-public.js``) wherever the site
has one, so Fill It In Yourself is honest about what a visitor will see:

- ``is`` compares the stored *value* as text, exactly as the site does, and a
  check-box group "is" a value when that value is one of those checked. Two
  numbers compare as numbers, so ``5`` is ``5.0``.
- ``<`` and ``>`` compare numbers, or dates; anything else is false, as
  ``parseFloat`` makes it on the site.
- ``is empty`` is true for no answer, empty text and nothing checked.

Arithmetic treats an unanswered field as 0. A date plus a number is that many
days later; a date minus a date is a number of days. Text plus text joins.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.errors import ExpressionEvalError

Value = None | str | Decimal | bool | dt.date | list[str]

_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def to_number(value: Any) -> Decimal | None:
    if value is None or isinstance(value, (list, dt.date)):
        return None
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)", text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:  # pragma: no cover - the pattern prevents it
        return None


def to_date(value: Any) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        m = _ISO.match(value.strip())
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
    return None


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return E.to_text(E.Num(value))
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, list):
        return ", ".join(as_text(v) for v in value)
    return str(value)


def truthy(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (str, list)):
        return len(value) > 0
    if isinstance(value, Decimal):
        return value != 0
    return True


def normal(value: Any) -> Value:
    if isinstance(value, (list, tuple)):
        return [as_text(v) for v in value]
    if isinstance(value, bool) or value is None or isinstance(value, (str, Decimal, dt.date)):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return str(value)


def _equal(left: Value, right: Value) -> bool:
    if isinstance(left, list):
        if isinstance(right, list):
            return sorted(left) == sorted(right)
        return as_text(right) in left
    a, b = to_number(left), to_number(right)
    if (
        a is not None
        and b is not None
        and not isinstance(left, bool)
        and not isinstance(right, bool)
    ):
        return a == b
    da, db = to_date(left), to_date(right)
    if da is not None and db is not None:
        return da == db
    return as_text(left) == as_text(right)


class Evaluator:
    def __init__(
        self,
        answers: Mapping[str, Any],
        *,
        today: dt.date | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        self.answers = answers
        self.today = today or dt.date.today()
        self.context = context or {}

    def run(self, node: E.Node) -> Value:  # noqa: C901 - one case per node kind
        if isinstance(node, E.Num):
            return node.value
        if isinstance(node, E.Str):
            return node.value
        if isinstance(node, E.Bool):
            return node.value
        if isinstance(node, E.Today):
            return self.today
        if isinstance(node, E.Ref):
            return normal(self.answers.get(node.field))
        if isinstance(node, E.Ctx):
            current: Any = self.context
            for part in node.path:
                current = current.get(part) if isinstance(current, Mapping) else None
            return normal(current)
        if isinstance(node, E.Call):
            return self.call(node)
        if isinstance(node, E.Neg):
            n = to_number(self.run(node.operand))
            return None if n is None else -n
        if isinstance(node, E.Arith):
            return self.arith(node.op, self.run(node.left), self.run(node.right))
        if isinstance(node, E.Compare):
            return self.compare(node.op, self.run(node.left), self.run(node.right))
        if isinstance(node, E.OneOf):
            value = self.run(node.value)
            options = [self.run(o) for o in node.options]
            if isinstance(value, list):
                hit = any(as_text(o) in value for o in options)
            else:
                hit = any(_equal(value, o) for o in options)
            return hit != node.negate
        if isinstance(node, E.Empty):
            return truthy(self.run(node.value)) == node.negate
        if isinstance(node, E.Within):
            return self.within(node)
        if isinstance(node, E.Logic):
            if node.op == "and":
                return all(truthy(self.run(i)) for i in node.items)
            return any(truthy(self.run(i)) for i in node.items)
        return not truthy(self.run(node.operand))

    def arith(self, op: str, left: Value, right: Value) -> Value:
        dl, dr = to_date(left), to_date(right)
        nl, nr = to_number(left), to_number(right)
        if dl is not None and op in "+-" and (nr is not None or right is None):
            days = int(nr or 0)
            return dl + dt.timedelta(days=days if op == "+" else -days)
        if dl is not None and dr is not None and op == "-":
            return Decimal((dl - dr).days)
        if op == "+" and (
            (isinstance(left, str) and nl is None and left != "")
            or (isinstance(right, str) and nr is None and right != "")
        ):
            return as_text(left) + as_text(right)
        a = nl if nl is not None else (Decimal(0) if left in (None, "", []) else None)
        b = nr if nr is not None else (Decimal(0) if right in (None, "", []) else None)
        if a is None or b is None:
            raise ExpressionEvalError(
                f"I cannot work out {as_text(left)!r} {op} {as_text(right)!r}."
            )
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if b == 0:
            raise ExpressionEvalError("A calculation divides by zero.")
        return a / b if op == "/" else a % b

    def compare(self, op: str, left: Value, right: Value) -> bool:
        if op == "=":
            return _equal(left, right)
        if op == "!=":
            return not _equal(left, right)
        if op in ("contains", "not_contains"):
            hit = (
                as_text(right) in left
                if isinstance(left, list)
                else as_text(right) in as_text(left)
            )
            return hit == (op == "contains")
        if op == "starts":
            return as_text(left).startswith(as_text(right))
        if op == "ends":
            return as_text(left).endswith(as_text(right))
        if op in ("before", "after"):
            dl, dr = to_date(left), to_date(right)
            if dl is None or dr is None:
                return False
            return dl < dr if op == "before" else dl > dr
        a, b = to_number(left), to_number(right)
        if a is None or b is None:
            da, db = to_date(left), to_date(right)
            if da is None or db is None:
                return False
            a, b = Decimal(da.toordinal()), Decimal(db.toordinal())
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

    def within(self, node: E.Within) -> bool:
        value = to_date(self.run(node.value))
        days = to_number(self.run(node.days))
        base = to_date(self.run(node.of)) if node.of is not None else self.today
        if value is None or days is None or base is None:
            return False
        return (abs((value - base).days) <= days) != node.negate

    def call(self, node: E.Call) -> Value:
        args = [self.run(a) for a in node.args]
        name = node.name
        if name == "if":
            if len(args) != 3:
                raise ExpressionEvalError(
                    "if() needs a test, a value when true, and a value when false."
                )
            return args[1] if truthy(args[0]) else args[2]
        flat: list[Any] = []
        for a in args:
            flat.extend(a if isinstance(a, list) else [a])
        if name == "count":
            return Decimal(sum(1 for v in flat if truthy(v)))
        if name in ("days_between", "age"):
            first = to_date(args[0]) if args else None
            second = to_date(args[1]) if len(args) > 1 else self.today
            if first is None or second is None:
                return None
            if name == "days_between":
                return Decimal((second - first).days)
            years = (
                second.year - first.year - ((second.month, second.day) < (first.month, first.day))
            )
            return Decimal(years)
        numbers = [n for n in (to_number(v) for v in flat) if n is not None]
        if name == "sum":
            return sum(numbers, Decimal(0))
        if name in ("min", "max"):
            return (min if name == "min" else max)(numbers) if numbers else None
        if name == "abs":
            return abs(numbers[0]) if numbers else None
        if name == "round":
            if not numbers:
                return None
            places = int(to_number(args[1]) or 0) if len(args) > 1 else 0
            return numbers[0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        raise ExpressionEvalError(f"{name}() is not a function rules know.")  # pragma: no cover


def evaluate(
    expression: str | E.Node,
    answers: Mapping[str, Any],
    *,
    today: dt.date | None = None,
    context: Mapping[str, Any] | None = None,
) -> Value:
    node = E.parse(expression) if isinstance(expression, str) else expression
    return Evaluator(answers, today=today, context=context).run(node)


def holds(
    expression: str | E.Node,
    answers: Mapping[str, Any],
    *,
    today: dt.date | None = None,
    context: Mapping[str, Any] | None = None,
) -> bool:
    return truthy(evaluate(expression, answers, today=today, context=context))
