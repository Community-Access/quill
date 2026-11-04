"""Where BAF's current PHP reader and QUILL's reading of the same BFL disagree.

Check This Form uses this to warn before publishing: BAF's parser on the site
today drops the first choice of an indented list, the field straight after an
indented ``if``, the contents of an indented ``columns`` and every model
feature it has no spelling for yet. Each disagreement is one plain sentence.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.baf_parser import baf_parse
from quill.core.forms.bfl_read import read_form
from quill.core.forms.errors import ExpressionError
from quill.core.forms.model import Field, Form, walk_items

_OPERATORS = {
    "=": "equals",
    "contains": "contains",
    "starts": "starts_with",
    "ends": "ends_with",
    ">": "greater_than",
    "<": "less_than",
}


def _baf_fields(config: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in config["form"]["fields"]:
        if f.get("type") == "columns":
            for column in f.get("columns", []):
                out.extend(column)
        elif f.get("type") != "section":
            out.append(f)
    return out


def _model_fields(form: Form) -> list[Field]:
    out: list[Field] = []
    for page in form.pages:
        for item in walk_items(page.items):
            if isinstance(item, Field):
                out.append(item)
    return out


def _baf_rule(expression: str) -> dict[str, Any] | None:
    """The one BAF rule an expression is, or None when BAF has no spelling for it."""
    try:
        node = E.parse(expression)
    except ExpressionError:
        return None
    if isinstance(node, E.Empty) and isinstance(node.value, E.Ref):
        return {
            "field": node.value.field,
            "operator": "is_not_empty" if node.negate else "is_empty",
            "value": "",
        }
    if isinstance(node, E.Compare) and isinstance(node.left, E.Ref) and node.op in _OPERATORS:
        right = node.right
        if isinstance(right, (E.Str, E.Num)):
            value = right.value if isinstance(right, E.Str) else str(right.value)
            return {"field": node.left.field, "operator": _OPERATORS[node.op], "value": value}
    return None


def divergences(text: str) -> list[str]:
    """Sentences saying what BAF's current reader would make differently of ``text``."""
    form = read_form(text)
    baf = _baf_fields(baf_parse(text))
    by_id = {f["id"]: f for f in baf if not str(f["id"]).startswith("field_")}
    auto = [f for f in baf if str(f["id"]).startswith("field_")]
    out: list[str] = []
    for item in _model_fields(form):
        name = item.label or item.id
        theirs = by_id.get(item.id)
        if theirs is None and item.id.startswith("field_"):
            theirs = next(
                (f for f in auto if f.get("label", "") == item.label and f["type"] == item.type),
                None,
            )
        if theirs is None:
            out.append(f"BAF's reader skips {name} ({item.type}).")
            continue
        _choices(item, theirs, name, out)
        rule = theirs.get("conditional_logic", {}).get("rules")
        if item.visible_when and not rule:
            out.append(f"BAF shows {name} every time: it does not read the condition.")
        elif item.visible_when and rule:
            ours = _baf_rule(item.visible_when)
            if ours is None or [ours] != rule:
                out.append(f"BAF reads only part of the condition on {name}.")
        for key in item.settings:
            if key != "unknown_modifiers" and key not in theirs:
                out.append(f"BAF does not read the {key.replace('_', ' ')} setting on {name}.")
        for attr, key in (
            ("required", "required"),
            ("placeholder", "placeholder"),
            ("help", "description"),
        ):
            if getattr(item, attr) and key not in theirs:
                out.append(f"BAF does not read the {attr} setting on {name}.")
    return out


def _choices(item: Field, theirs: dict[str, Any], name: str, out: list[str]) -> None:
    if not item.choices:
        return
    labels = [c.get("label") for c in theirs.get("choices", []) if isinstance(c, dict)]
    dropped = [c.label for c in item.choices if c.label not in labels]
    if dropped:
        out.append(f"BAF's reader drops {', '.join(dropped)} from {name}.")
