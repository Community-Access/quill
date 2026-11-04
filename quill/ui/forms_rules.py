"""A form's rules as sentences, and building one from three choices (17a.4.4).

wx-free. Format > Form Rules lists every condition and calculation in the form
as the sentence it is -- "Show Company name when Type is Business.", "Total
is Quantity times Price." -- and Add Rule builds one from *when what*, *is
what* and *then what*, so nobody has to write rule syntax unless they want to.

Two places in the model hold rules, and both are listed: a question's own
``when`` and ``calculation`` (BFL's ``if`` block and ``@calculate``), and the
form's ``rules`` list (show, hide, require, optional, enable, disable, set,
skip to). A new "show" rule is written as the question's own ``when``, which
BFL spells as the ``if`` block a person would have written; the other actions
go in the rules list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.ui.forms_doc import Model, labels, name_of, sentence

#: Rule actions, with the verb a sentence starts with.
ACTIONS: dict[str, str] = {
    "show": "Show",
    "hide": "Hide",
    "require": "Require",
    "optional": "Make optional",
    "enable": "Enable",
    "disable": "Disable",
    "skip_to": "Skip to",
}

#: The "is what" choices: (spoken, how to write it; {v} is the quoted value).
TESTS: tuple[tuple[str, str], ...] = (
    ("is", "{f} is {v}"),
    ("is not", "{f} is not {v}"),
    ("is filled in", "{f} is filled"),
    ("is empty", "{f} is empty"),
    ("contains", "{f} contains {v}"),
    ("is more than", "{f} > {v}"),
    ("is less than", "{f} < {v}"),
)


@dataclass(frozen=True)
class RuleRow:
    """One rule as the Rules window shows it."""

    text: str
    kind: str  # "when", "calculation" or "rule"
    key: Any  # the item id, or the index in model["rules"]


def rule_rows(model: Model) -> list[RuleRow]:
    names = labels(model)
    rows: list[RuleRow] = []
    for page_number, page in enumerate(model.get("pages") or [], 1):
        if page.get("when"):
            what = f"page {page_number}" + (f", {page['title']}" if page.get("title") else "")
            rows.append(
                RuleRow(f"Show {what} when {sentence(model, page['when'])}.", "page", page["id"])
            )
    for item in M.iter_items(model):
        if item.get("when"):
            text = f"Show {name_of(item)} when {sentence(model, item['when'])}."
            rows.append(RuleRow(text, "when", item["id"]))
        if item.get("calculation"):
            text = f"{name_of(item)} is {sentence(model, item['calculation'])}."
            rows.append(RuleRow(text, "calculation", item["id"]))
    for index, rule in enumerate(model.get("rules") or []):
        targets = [names.get(t, t) for t in rule.get("targets") or []]
        target = " and ".join(targets) or "nothing"
        when = sentence(model, str(rule.get("when", "")))
        if rule.get("action") == "set":
            value = sentence(model, str(rule.get("value", "")))
            text = f"Set {target} to {value} when {when}."
        else:
            action = str(rule.get("action"))
            text = f"{ACTIONS.get(action, action)} {target} when {when}."
        rows.append(RuleRow(text, "rule", index))
    return rows


def condition(field_id: str, test: int, value: str) -> str:
    """The expression for *field_id*, the *test*-th of :data:`TESTS`, and *value*.

    A number stays a number for "more than" and "less than"; anything else is
    quoted, so "Business" is text and never a field.
    """
    _spoken, pattern = TESTS[test]
    raw = value.strip()
    numeric = pattern.endswith(("> {v}", "< {v}")) and _is_number(raw)
    quoted = raw if numeric else E.quote(raw)
    return E.canonical(pattern.format(f="#" + field_id, v=quoted))


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def problem(expression: str) -> str | None:
    """None when *expression* reads, else the sentence saying why it does not."""
    return E.check(expression)


def add_rule(model: Model, action: str, target: str, when: str) -> str:
    """Add a rule and return its sentence. "show" goes on the target itself."""
    when = E.canonical(when)
    item = M.find(model, target)
    if action == "show" and item is not None:
        old = item.get("when")
        item["when"] = E.canonical(f"({old}) and ({when})") if old else when
    else:
        model.setdefault("rules", []).append({"action": action, "targets": [target], "when": when})
    name = name_of(item) if item is not None else target
    return f"{ACTIONS.get(action, action)} {name} when {sentence(model, when)}."


def edit_rule(model: Model, row: RuleRow, expression: str) -> str:
    """Replace a rule's condition (or a calculation) with *expression*; empty removes it."""
    text = expression.strip()
    if not text:
        remove_rule(model, row)
        return "Rule removed."
    text = E.canonical(text)
    if row.kind in ("when", "calculation"):
        item = M.find(model, str(row.key))
        if item is not None:
            item[row.kind] = text
    elif row.kind == "page":
        for page in model.get("pages") or []:
            if page.get("id") == row.key:
                page["when"] = text
    else:
        model["rules"][int(row.key)]["when"] = text
    return "Rule changed."


def remove_rule(model: Model, row: RuleRow) -> None:
    if row.kind in ("when", "calculation"):
        item = M.find(model, str(row.key))
        if item is not None:
            item.pop(row.kind, None)
    elif row.kind == "page":
        for page in model.get("pages") or []:
            if page.get("id") == row.key:
                page.pop("when", None)
    else:
        rules = model.get("rules") or []
        del rules[int(row.key)]
        if not rules:
            model.pop("rules", None)


def current_text(model: Model, row: RuleRow) -> str:
    """The rule's expression as written, for editing."""
    if row.kind in ("when", "calculation"):
        return str((M.find(model, str(row.key)) or {}).get(row.kind, ""))
    if row.kind == "page":
        page = next((p for p in model.get("pages") or [] if p.get("id") == row.key), {})
        return str(page.get("when", ""))
    return str(model["rules"][int(row.key)].get("when", ""))
