"""Check This Form: what to fix, each with Go to It (wordpress.md 17a.5).

wx-free, so every check is a plain test. A finding is one sentence saying
what to fix and the id of the question it is about, which is how Go to It
finds the line. Four sources, in this order: what the reader could not read
(BFL errors, in the core's own words), what the form model does not allow
(the core's schema and semantic checks), the accessibility checks in 17a.5,
and where QAF's current reader would make something different of the text
(:func:`quill.core.forms.qaf_compare.divergences`) -- a form that reads well
here and loses a question on the site is a finding too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from quill.core.forms import model as M
from quill.ui import forms_doc as fd

#: Autofill hints a person's details should carry (the tokens QAF writes).
AUTOFILL: dict[str, str] = {
    "email": "email",
    "phone": "tel",
    "name": "name",
    "address": "street-address",
}

#: Over this many choices, a list is easier as a library or a search (17a.5).
LONG_LIST = 15
#: Over this many questions on one page, the page wants splitting (17a.5).
LONG_PAGE = 30
_GROUPS = ("radio", "checkbox", "likert", "matrix", "ranking")
_FORMAT_RULES = ("min", "max", "min_length", "max_length", "pattern")


@dataclass(frozen=True)
class Finding:
    text: str
    item_id: str | None = None
    offset: int | None = None


def check(text: str) -> list[Finding]:
    """Every finding for the form in *text*, most serious first."""
    doc = fd.read(text)
    model = doc.model
    out = [Finding(message, None, offset) for message, offset in fd.reading_problems(doc)]
    for island in getattr(doc, "islands", None) or []:
        first = str(island).strip().splitlines()[0][:80] if str(island).strip() else ""
        if first and not first.startswith("//"):
            out.append(
                Finding(
                    f"QUILL keeps this as written and cannot read it: {first}",
                    None,
                    text.find(island),
                )
            )
    out += _model_problems(model)
    out += accessibility(model)
    out += [Finding(sentence) for sentence in _divergences(text)]
    return out


def _model_problems(model: fd.Model) -> list[Finding]:
    out: list[Finding] = []
    try:
        found: list[Any] = list(M.validate(model)) or list(M.semantic_errors(model))
    except Exception as exc:  # noqa: BLE001 - a check never stops at a broken form
        return [Finding(f"QUILL could not check this form's structure: {exc}")]
    for problem in found:
        if isinstance(problem, dict):
            message, path = str(problem.get("message", problem)), str(problem.get("path", ""))
        else:
            message, path = (
                str(getattr(problem, "message", problem)),
                str(getattr(problem, "path", "")),
            )
        out.append(Finding(message, _id_at(model, path)))
    return out


def _id_at(model: fd.Model, path: str) -> str | None:
    """The innermost item id a JSON pointer like ``/pages/0/items/2/when`` reaches."""
    node: Any = model
    found: str | None = None
    for part in [p for p in path.split("/") if p]:
        try:
            node = node[int(part)] if isinstance(node, list) else node[part]
        except (KeyError, IndexError, ValueError, TypeError):
            break
        if isinstance(node, dict) and "type" in node and "id" in node:
            found = str(node["id"])
    return found


def _divergences(text: str) -> list[str]:
    try:
        from quill.core.forms.qaf_compare import divergences

        return [f"On the site today: {s}" for s in divergences(text)]
    except Exception:  # noqa: BLE001 - the comparison is advice, never a failure
        return []


def accessibility(model: fd.Model) -> list[Finding]:
    """The checks of 17a.5 that are about the people filling the form in."""
    out: list[Finding] = []
    ids: dict[str, int] = {}
    known = {str(i.get("id")) for i in M.iter_items(model)}
    known |= {str(p.get("id")) for p in model.get("pages") or []}
    for number, page in enumerate(model.get("pages") or [], 1):
        questions = [i for i in fd._all(page.get("items") or []) if M.is_field_type(i.get("type"))]
        if not questions:
            out.append(Finding(f"Page {number} has no questions. Remove it, or add some."))
        elif len(questions) > LONG_PAGE:
            out.append(
                Finding(
                    f"Page {number} has {len(questions)} questions. Over {LONG_PAGE} on one "
                    "page is a lot to move through; split it with a page break."
                )
            )
    for item in M.iter_items(model):
        item_id = str(item.get("id"))
        ids[item_id] = ids.get(item_id, 0) + 1
        if M.is_field_type(item.get("type")):
            out += [Finding(t, item_id) for t in _field_checks(item)]
        for key in ("when", "calculation"):
            for ref in _refs(item.get(key)):
                if ref not in known:
                    out.append(
                        Finding(
                            f"{fd.name_of(item)} has a rule that names #{ref}, which is not "
                            "in this form.",
                            item_id,
                        )
                    )
        if item.get("required") and item.get("when") and _never(model, str(item["when"])):
            out.append(
                Finding(
                    f"{fd.name_of(item)} is required, but its rule can never show it, so the "
                    "form could never be sent.",
                    item_id,
                )
            )
    for item_id, count in ids.items():
        if count > 1:
            out.append(
                Finding(f"The id {item_id} is used {count} times. Each needs its own.", item_id)
            )
    for rule in model.get("rules") or []:
        for target in rule.get("targets") or []:
            if target not in known:
                out.append(Finding(f"A rule points at #{target}, which is not in this form."))
    return out


def _field_checks(item: fd.Item) -> list[str]:  # noqa: C901 - one check per rule of 17a.5
    out: list[str] = []
    name = fd.name_of(item)
    kind = str(item.get("type"))
    label = str(item.get("label") or "").strip()
    hidden = kind in ("hidden", "html", "submit", "save", "progress", "summary", "captcha")
    if not label and not hidden:
        if item.get("placeholder"):
            out.append(
                f"{item.get('placeholder')} ({kind}) has only a placeholder for a label. A "
                "placeholder disappears as soon as somebody types; give it a label."
            )
        else:
            out.append(f"The {kind} question {item.get('id')} has no label. Give it one.")
    if kind in _GROUPS and not label:
        out.append(f"The {kind} group {item.get('id')} has no question for its choices.")
    if re.search(r"\*\s*$|^\s*\*|\(required\)", label, re.IGNORECASE) and not item.get("required"):
        out.append(
            f"{name} marks itself required only with an asterisk or a word. Turn on Required "
            "instead, so a screen reader says so."
        )
    validation = item.get("validation") or {}
    has_rule = item.get("mask") or any(k in validation for k in _FORMAT_RULES)
    if has_rule and not item.get("help"):
        out.append(f"{name} has a format rule but no help saying what is expected. Add help text.")
    hint = AUTOFILL.get(kind)
    props = item.get("props") or {}
    attributes = item.get("attributes") or {}
    if hint and not (props.get("autocomplete") or attributes.get("autocomplete")):
        out.append(
            f"{name} has no autofill hint, so the browser cannot fill it in. The hint is {hint}."
        )
    choices = item.get("choices") or []
    if len(choices) > LONG_LIST:
        out.append(
            f"{name} has {len(choices)} choices. Over {LONG_LIST} are easier as a choice "
            "library, or a list somebody can search."
        )
    return out


def _refs(expression: Any) -> list[str]:
    if not isinstance(expression, str) or not expression.strip():
        return []
    try:
        from quill.core.forms import expr as E

        return [str(r) for r in E.refs(E.parse(expression))]
    except Exception:  # noqa: BLE001 - an unreadable rule is the reader's finding
        return []


def _never(model: fd.Model, expression: str) -> bool:
    """A rule naming only fields that do not exist can never hold."""
    refs = _refs(expression)
    return bool(refs) and all(M.find(model, r) is None for r in refs)
