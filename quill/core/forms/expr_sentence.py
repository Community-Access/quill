"""Expressions read aloud: "Show Company name when Type is Business or Type is Charity."

Rules (Format > Form Rules) and the outline speak a rule as the sentence it
is, using each field's label and each choice's label, never the ids or the
symbols. Nothing here is announced by itself; callers route the text through
the announcement service.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from quill.core.forms import expr as E
from quill.core.forms.model import Form, all_fields

_MONTHS = (
    "January February March April May June July August September October November December"
).split()
_COMPARE = {
    "=": "is", "!=": "is not", "<": "is less than", "<=": "is at most", ">": "is more than",
    ">=": "is at least", "contains": "contains", "not_contains": "does not contain",
    "starts": "starts with", "ends": "ends with", "before": "is before", "after": "is after",
}  # fmt: skip
_ARITH = {
    "+": "plus",
    "-": "minus",
    "*": "times",
    "/": "divided by",
    "%": "remainder after dividing by",
}
_CONTEXT = {"user": "the visitor's", "geo": "the visitor's", "query": "the address's"}


@dataclass
class Vocabulary:
    """What to call each field and each choice."""

    labels: dict[str, str] = field(default_factory=dict)
    choices: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_form(cls, form: Form) -> Vocabulary:
        vocab = cls()
        for item in all_fields(form):
            vocab.labels[item.id] = item.label or item.id.replace("_", " ")
            if item.choices:
                vocab.choices[item.id] = {c.value: c.label for c in item.choices}
        return vocab


def spoken_date(value: dt.date) -> str:
    return f"{value.day} {_MONTHS[value.month - 1]} {value.year}"


def _join(parts: list[str], word: str) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + f" {word} " + parts[-1]


class _Speaker:
    def __init__(self, vocab: Vocabulary) -> None:
        self.vocab = vocab

    def value(self, node: E.Node, subject: E.Node | None = None) -> str:
        """A value, using the choice label when it compares with a choice field."""
        if isinstance(node, E.Str):
            if isinstance(subject, E.Ref):
                label = self.vocab.choices.get(subject.field, {}).get(node.value)
                if label is not None:
                    return label
            date = _iso(node.value)
            return spoken_date(date) if date else node.value
        return self.say(node)

    def say(self, node: E.Node) -> str:  # noqa: C901 - one case per node kind
        if isinstance(node, E.Num):
            return E.to_text(node)
        if isinstance(node, E.Str):
            return node.value
        if isinstance(node, E.Bool):
            return "yes" if node.value else "no"
        if isinstance(node, E.Today):
            return "today"
        if isinstance(node, E.Ref):
            return self.vocab.labels.get(node.field, node.field.replace("_", " "))
        if isinstance(node, E.Ctx):
            head = _CONTEXT.get(node.path[0], node.path[0])
            return head + " " + " ".join(p.replace("_", " ") for p in node.path[1:])
        if isinstance(node, E.Call):
            return self.call(node)
        if isinstance(node, E.Neg):
            return "minus " + self.say(node.operand)
        if isinstance(node, E.Arith):
            if isinstance(node.left, E.Today) and isinstance(node.right, E.Num) and node.op in "+-":
                days = E.to_text(node.right)
                unit = "day" if days == "1" else "days"
                return f"{days} {unit} from today" if node.op == "+" else f"{days} {unit} ago"
            return f"{self.say(node.left)} {_ARITH[node.op]} {self.say(node.right)}"
        if isinstance(node, E.Compare):
            return f"{self.say(node.left)} {_COMPARE[node.op]} {self.value(node.right, node.left)}"
        if isinstance(node, E.OneOf):
            options = [self.value(o, node.value) for o in node.options]
            verb = "is not" if node.negate else "is"
            return f"{self.say(node.value)} {verb} {_join(options, 'or')}"
        if isinstance(node, E.Empty):
            return f"{self.say(node.value)} {'is answered' if node.negate else 'has no answer'}"
        if isinstance(node, E.Within):
            base = self.say(node.of) if node.of is not None else "today"
            verb = "is not within" if node.negate else "is within"
            return f"{self.say(node.value)} {verb} {self.say(node.days)} days of {base}"
        if isinstance(node, E.Logic):
            parts = []
            for item in node.items:
                text = self.say(item)
                if isinstance(item, E.Logic):
                    text = ("both " if item.op == "and" else "either ") + text
                parts.append(text)
            return _join(parts, node.op)
        inner = node.operand
        if isinstance(inner, E.Compare) and inner.op in ("=", "contains"):
            op = "!=" if inner.op == "=" else "not_contains"
            return self.say(E.Compare(op, inner.left, inner.right))
        if isinstance(inner, (E.OneOf, E.Empty, E.Within)):
            flipped: E.Node
            if isinstance(inner, E.OneOf):
                flipped = E.OneOf(inner.value, inner.options, not inner.negate)
            elif isinstance(inner, E.Empty):
                flipped = E.Empty(inner.value, not inner.negate)
            else:
                flipped = E.Within(inner.value, inner.days, inner.of, not inner.negate)
            return self.say(flipped)
        return "it is not the case that " + self.say(inner)

    def call(self, node: E.Call) -> str:
        args = [self.say(a) for a in node.args]
        name = node.name
        if name == "sum":
            return "the total of " + _join(args, "and")
        if name in ("min", "max"):
            return ("the smallest of " if name == "min" else "the largest of ") + _join(args, "and")
        if name == "round":
            places = args[1] if len(args) > 1 else "0"
            return (
                f"{args[0]} rounded to {places} decimal places"
                if places != "0"
                else f"{args[0]} rounded"
            )
        if name == "abs":
            return f"the size of {args[0]}"
        if name == "count":
            return f"how many of {_join(args, 'and')} are answered"
        if name == "days_between":
            return f"the days from {args[0]} to {args[1] if len(args) > 1 else 'today'}"
        if name == "age":
            return f"the age in years from {args[0]}"
        return f"{args[1]} if {args[0]}, otherwise {args[2]}" if len(args) == 3 else name


def _iso(text: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(text) if len(text) == 10 else None
    except ValueError:
        return None


def sentence(expression: str | E.Node, vocab: Vocabulary | None = None) -> str:
    """An expression as words: ``#type is "biz"`` becomes "Type is Business"."""
    node = E.parse(expression) if isinstance(expression, str) else expression
    return _Speaker(vocab or Vocabulary()).say(node)


def rule_sentence(
    target: str, expression: str | E.Node, vocab: Vocabulary | None = None, action: str = "Show"
) -> str:
    """ "Show Company name when Type is Business or Type is Charity." """
    return f"{action} {target} when {sentence(expression, vocab)}."


def calculation_sentence(
    target: str, expression: str | E.Node, vocab: Vocabulary | None = None
) -> str:
    """ "Total is Quantity times Price." """
    return f"{target} is {sentence(expression, vocab)}."


def number_words(value: Decimal) -> str:
    return E.to_text(E.Num(value))
