"""Expressions as sentences: a port of ``QAF_Expression::to_sentence``.

``#type is "business" or #type is "charity"`` reads "Type is Business or Type
is Charity": each ``#id`` becomes the field's label, and a value compared with
a choice field becomes that choice's label. QAF and QUILL say the same words.
Nothing here announces anything; callers route the text through the
announcement service.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from quill.core.forms import expr as E

Labels = Mapping[str, str]
ChoiceLabels = Mapping[str, Mapping[str, str]]

_INVERSES = {
    "is": "is_not", "is_not": "is", "empty": "not_empty", "not_empty": "empty",
    "one_of": "not_one_of", "not_one_of": "one_of", "contains": "not_contains",
    "not_contains": "contains",
}  # fmt: skip
_WORDS = {
    "is": "is", "is_not": "is not", "lt": "is less than", "le": "is at most",
    "gt": "is greater than", "ge": "is at least", "contains": "contains",
    "not_contains": "does not contain", "starts_with": "starts with", "ends_with": "ends with",
    "before": "is before", "after": "is after", "add": "plus", "sub": "minus", "mul": "times",
    "div": "divided by", "mod": "remainder after dividing by",
}  # fmt: skip
_NAMES = {
    "sum": "the total of", "avg": "the average of", "min": "the smallest of",
    "max": "the largest of", "round": "rounded", "floor": "rounded down", "ceil": "rounded up",
    "abs": "the size of", "age": "the age in years from", "date": "the date",
}  # fmt: skip


def _php_json(v: Any) -> str:
    if isinstance(v, float):
        return E.number_text(v, False)
    return json.dumps(v, ensure_ascii=False)


class _Speaker:
    def __init__(self, labels: Labels, choices: ChoiceLabels) -> None:
        self.labels = labels
        self.choices = choices

    def group(self, n: E.Node, ctx: str | None = None) -> str:
        text = self.say(n, ctx)
        return f"({text})" if n.get("type") == "op" and n["op"] in ("and", "or") else text

    def say(self, node: E.Node, context: str | None = None) -> str:  # noqa: C901
        kind = node["type"]
        if kind == "literal":
            v = node["value"]
            if v is None:
                return "nothing"
            if isinstance(v, bool):
                return "yes" if v else "no"
            if context is not None and isinstance(v, str) and v in self.choices.get(context, {}):
                return str(self.choices[context][v])
            return v if isinstance(v, str) else _php_json(v)
        if kind == "ref":
            label = self.labels.get(node["field"])
            return str(label) if label else str(node["field"])
        if kind == "var":
            return "the score"
        if kind == "list":
            items = [self.say(n, context) for n in node["items"]]
            if len(items) <= 1:
                return "".join(items)
            return ", ".join(items[:-1]) + " or " + items[-1]
        if kind == "call":
            return self.call(node)
        a = node["args"]
        name = node["op"]
        ctx = a[0]["field"] if a[0].get("type") == "ref" else None
        if name in ("or", "and"):
            parts = [self.group(n) for n in a]
            last = parts.pop()
            return ", ".join(parts) + ("," if len(parts) > 1 else "") + f" {name} " + last
        if name == "not":
            inner = a[0]
            if inner.get("type") == "op" and inner["op"] in _INVERSES:
                return self.say({"type": "op", "op": _INVERSES[inner["op"]], "args": inner["args"]})
            if inner.get("type") == "op":
                return "not (" + self.say(inner) + ")"
            return "not " + self.say(inner)
        if name == "neg":
            return "minus " + self.say(a[0])
        if name == "empty":
            return self.say(a[0]) + " is empty"
        if name == "not_empty":
            return self.say(a[0]) + " is filled in"
        if name in ("one_of", "not_one_of"):
            word = " is one of " if name == "one_of" else " is not one of "
            return self.say(a[0]) + word + self.say(a[1], ctx)
        if name == "within":
            base = self.say(a[2]) if len(a) > 2 else "today"
            return f"{self.say(a[0])} is within {self.say(a[1])} days of {base}"
        left = self.say(a[0])
        right = self.say(a[1], ctx)
        prec = E.PRECEDENCE[name]
        if prec >= 5:
            if a[0].get("type") == "op" and E.PRECEDENCE[a[0]["op"]] < prec:
                left = f"({left})"
            if a[1].get("type") == "op" and E.PRECEDENCE[a[1]["op"]] <= prec:
                right = f"({right})"
        return f"{left} {_WORDS[name]} {right}"

    def call(self, node: E.Node) -> str:  # noqa: C901
        args = node["args"]
        name = node["name"]
        if name == "today":
            return "today"
        if name == "geo":
            return "the visitor's location"
        if name == "score":
            return "the score for " + self.say(args[0])
        if name == "count":
            return "the number of choices in " + self.say(args[0])
        if name == "length":
            return "the length of " + self.say(args[0])
        if name == "user":
            return "the signed-in user's " + str(args[0].get("value") or "").replace("_", " ")
        if name == "query":
            return "the link's " + str(args[0].get("value") or "") + " value"
        if name == "if":
            return f"{self.say(args[1])} if {self.say(args[0])}, otherwise {self.say(args[2])}"
        if name == "days_between":
            return f"the days from {self.say(args[0])} to {self.say(args[1])}"
        parts = [self.say(a) for a in args]
        if name == "round" and len(parts) == 2:
            return f"{parts[0]} rounded to {parts[1]} places"
        if name in ("round", "floor", "ceil"):
            return f"{parts[0]} {_NAMES[name]}"
        last = parts.pop()
        return _NAMES[name] + " " + (", ".join(parts) + " and " if parts else "") + last


def sentence(
    expression: E.Node | str, labels: Labels | None = None, choices: ChoiceLabels | None = None
) -> str:
    """An expression as words, with these labels and choice labels."""
    node = E.parse(expression) if isinstance(expression, str) else expression
    return _Speaker(labels or {}, choices or {}).say(node)


def rule_sentence(
    target: str,
    expression: E.Node | str,
    labels: Labels | None = None,
    choices: ChoiceLabels | None = None,
    action: str = "Show",
) -> str:
    """ "Show Company name when Type is Business or Type is Charity." """
    return f"{action} {target} when {sentence(expression, labels, choices)}."


def calculation_sentence(
    target: str,
    expression: E.Node | str,
    labels: Labels | None = None,
    choices: ChoiceLabels | None = None,
) -> str:
    """ "Total is Quantity times Price." """
    return f"{target} is {sentence(expression, labels, choices)}."
