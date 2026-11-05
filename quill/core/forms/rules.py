"""What a form does with some answers: scores, the quiz outcome, what is shown.

:func:`score`, :func:`context`, :func:`outcome` and :func:`is_shown` are ports
of ``QAF_Form_Model``'s, and QAF's ``tests/conformance/models/behaviour.json``
checks them. :func:`evaluate_form` puts them together for Fill It In
Yourself: visibility of every item, calculations in document order, which
shown fields still need an answer, and the rules (require, optional, set,
skip_to) that hold.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import expr_eval as V
from quill.core.forms import model as M
from quill.core.forms.errors import ExpressionError


def _whole(n: Any) -> Any:
    return int(n) if isinstance(n, float) and n.is_integer() else n


def _php_lower(s: str) -> str:
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def _php_str(v: Any) -> str:
    if v is True:
        return "1"
    if v is False or v is None:
        return ""
    if isinstance(v, float):
        return V.to_str(v)
    return str(v)


def score(model: M.Model, values: Mapping[str, Any]) -> dict[str, Any]:
    """``{"fields": {id: points}, "total": points}`` for these answers."""
    scores: dict[str, Any] = {}
    for fid, fld in M.fields(model).items():
        answer = values.get(fid)
        if isinstance(answer, list):
            chosen = [_php_str(a) for a in answer]
        else:
            chosen = [] if V.is_empty(answer) else [_php_str(answer)]
        points: Any = 0
        has = False
        scoring = fld.get("scoring")
        if scoring and "correct" in scoring:
            has = True
            worth = scoring.get("points", 1)
            fold = not scoring.get("case_sensitive")

            def norm(s: str, fold: bool = fold) -> str:
                s = s.strip(" \t\n\r\0\x0b")
                return _php_lower(s) if fold else s

            correct = sorted(norm(_php_str(c)) for c in scoring["correct"])
            picked = sorted(norm(c) for c in chosen)
            if picked == correct and picked:
                points += worth
            elif scoring.get("partial") and picked and not set(picked) - set(correct):
                points += worth * len(picked) / len(correct)
        for choice in fld.get("choices") or []:
            if "points" in choice:
                has = True
                if _php_str(choice["value"]) in chosen:
                    points += choice["points"]
        if has:
            scores[fid] = _whole(points)
    return {"fields": scores, "total": _whole(sum(scores.values()))}


def context(
    model: M.Model, values: Mapping[str, Any], extra: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    result = score(model, values)
    return {
        **(extra or {}),
        "values": dict(values),
        "scores": result["fields"],
        "score": result["total"],
    }


def outcome(
    model: M.Model, values: Mapping[str, Any], extra: Mapping[str, Any] | None = None
) -> dict[str, Any] | None:
    """The first quiz outcome whose condition holds, or None."""
    ctx = context(model, values, extra)
    for item in (model.get("scoring") or {}).get("outcomes") or []:
        if V.truthy(V.evaluate(item["when"], ctx)):
            return dict(item)
    return None


def _chain(entries: list[M.Item], item_id: str) -> list[M.Item] | None:
    for item in entries:
        if item.get("id") == item_id:
            return [item]
        if item.get("type") == "columns":
            children = [c for col in item.get("columns") or [] for c in col.get("items") or []]
        else:
            children = item.get("items") or []
        sub = _chain(children, item_id)
        if sub is not None:
            return [item, *sub]
    return None


def _shown_in(model: M.Model, item_id: str, ctx: Mapping[str, Any]) -> bool:
    for page in model["pages"]:
        chain = _chain(page.get("items") or [], item_id)
        if chain is None:
            continue
        if "when" in page and not V.truthy(V.evaluate(page["when"], ctx)):
            return False
        for item in chain:
            if "when" in item and not V.truthy(V.evaluate(item["when"], ctx)):
                return False
        shown = True
        names = {i["id"] for i in chain} | {page["id"]}
        for rule in model.get("rules") or []:
            if not names & set(rule["targets"]):
                continue
            holds = V.truthy(V.evaluate(rule["when"], ctx))
            if rule["action"] == "hide" and holds:
                return False
            if rule["action"] == "show" and not holds:
                shown = False
        return shown
    return False


def is_shown(
    model: M.Model, item_id: str, values: Mapping[str, Any], extra: Mapping[str, Any] | None = None
) -> bool:
    """Whether an item is shown: its condition, its sections' and page's, and show/hide rules."""
    return _shown_in(model, item_id, context(model, values, extra))


@dataclass
class FormState:
    """Everything Fill It In Yourself needs after an answer."""

    shown: set[str] = field(default_factory=set)
    hidden: set[str] = field(default_factory=set)
    values: dict[str, Any] = field(default_factory=dict)
    calculated: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, Any] = field(default_factory=dict)
    score: Any = 0
    outcome: dict[str, Any] | None = None
    missing_required: list[str] = field(default_factory=list)
    skip_to: str | None = None
    #: (where, problem) for every expression that could not be worked out.
    problems: list[tuple[str, str]] = field(default_factory=list)


def evaluate_form(
    model: M.Model, answers: Mapping[str, Any], extra: Mapping[str, Any] | None = None
) -> FormState:
    """Calculations (in order), visibility, rules, missing answers, score and outcome."""
    state = FormState(values=dict(answers))
    rules = model.get("rules") or []
    for item in M.iter_items(model):
        if "calculation" in item:
            try:
                value = V.evaluate(item["calculation"], context(model, state.values, extra))
            except ExpressionError as exc:
                state.problems.append((item["id"], str(exc)))
                value = None
            state.calculated[item["id"]] = value
            state.values[item["id"]] = value
    ctx = context(model, state.values, extra)
    for rule in rules:
        if rule["action"] == "set" and "value" in rule and V.truthy(V.evaluate(rule["when"], ctx)):
            for target in rule["targets"]:
                state.values[target] = V.evaluate(rule["value"], ctx)
    ctx = context(model, state.values, extra)
    required_by_rule: dict[str, bool] = {}
    for rule in rules:
        if rule["action"] in ("require", "optional") and V.truthy(V.evaluate(rule["when"], ctx)):
            for target in rule["targets"]:
                required_by_rule[target] = rule["action"] == "require"
        if (
            rule["action"] == "skip_to"
            and state.skip_to is None
            and V.truthy(V.evaluate(rule["when"], ctx))
        ):
            state.skip_to = rule["targets"][0]
    for page in model["pages"]:
        page_ok = "when" not in page or V.truthy(V.evaluate(page["when"], ctx))
        (state.shown if page_ok else state.hidden).add(page["id"])
    for item in M.iter_items(model):
        shown = _shown_in(model, item["id"], ctx)
        (state.shown if shown else state.hidden).add(item["id"])
        needed = required_by_rule.get(item["id"], bool(item.get("required")))
        if (
            shown
            and needed
            and M.is_field_type(item["type"])
            and V.is_empty(state.values.get(item["id"]))
        ):
            state.missing_required.append(item["id"])
    state.scores, state.score = ctx["scores"], ctx["score"]
    state.outcome = outcome(model, state.values, extra)
    return state


def smart_default(item: M.Item, extra: Mapping[str, Any] | None = None) -> Any:
    """A field's starting value: its smart default worked out, else its fixed default."""
    if "smart_default" in item:
        try:
            return V.evaluate(item["smart_default"], dict(extra or {}))
        except ExpressionError:
            return item.get("default")
    return item.get("default")
