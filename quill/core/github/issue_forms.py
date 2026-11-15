"""GitHub issue forms (``.github/ISSUE_TEMPLATE/*.yml``), read and filled natively.

Until now a YAML issue form showed as "open in GitHub to fill its structured
fields". This reads the form's schema -- ``name``, ``description``, ``title``,
``labels``, ``assignees`` and ``body`` with its ``markdown``, ``input``,
``textarea``, ``dropdown`` and ``checkboxes`` elements -- checks required
answers, and writes the issue body the way GitHub's own form does, so an issue
filed from QUILL reads the same as one filed on the website:

    ### Label

    The answer, or _No response_ when an optional field was left empty.

A ``textarea`` with ``render`` is fenced as that language; ``checkboxes`` are
``- [X]`` / ``- [ ]`` lines; a ``markdown`` element is shown while filling and
never written. ``validations.required`` is honoured per field (and per check
box option). Anything the schema allows that this cannot represent makes the
form *unsupported*, with the reason, so the caller can offer the website
rather than file something incomplete.

YAML is parsed with ``yaml.safe_load`` only, and nothing in a form runs. No
``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "FIELD_KINDS",
    "FormField",
    "IssueForm",
    "answer_key",
    "parse_issue_form",
    "render_body",
    "validate",
]

#: The element types GitHub's issue forms define.
FIELD_KINDS = ("markdown", "input", "textarea", "dropdown", "checkboxes")
_NO_RESPONSE = "_No response_"
_MAX_TEXT = 50_000


@dataclass(frozen=True, slots=True)
class FormField:
    """One element of the form's ``body``."""

    kind: str
    id: str = ""
    label: str = ""
    description: str = ""
    placeholder: str = ""
    value: str = ""
    required: bool = False
    render: str = ""
    multiple: bool = False
    #: Dropdown options, or check box labels.
    options: tuple[str, ...] = ()
    #: For checkboxes: which options must be checked.
    required_options: tuple[bool, ...] = ()
    #: Dropdown: the index chosen by default, or -1.
    default: int = -1

    @property
    def answers(self) -> bool:
        """Whether the person fills this in (a markdown element is only read)."""
        return self.kind != "markdown"


@dataclass(frozen=True, slots=True)
class IssueForm:
    name: str
    description: str = ""
    title: str = ""
    labels: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    fields: tuple[FormField, ...] = ()
    #: Why QUILL cannot fill this form ("" when it can).
    unsupported: str = ""
    problems: tuple[str, ...] = field(default_factory=tuple)


def _text(value: object, limit: int = 2000) -> str:
    return "" if value is None else str(value)[:limit]


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, Sequence):
        return tuple(_text(part, 200).strip() for part in value if _text(part).strip())
    return ()


def _field(raw: Mapping[str, Any], position: int) -> tuple[FormField | None, str]:
    kind = _text(raw.get("type"), 40).strip()
    if kind not in FIELD_KINDS:
        return None, f"element {position} has a type QUILL does not know ({kind or 'none'})"
    attrs = raw.get("attributes")
    attrs = attrs if isinstance(attrs, Mapping) else {}
    rules = raw.get("validations")
    rules = rules if isinstance(rules, Mapping) else {}
    ident = _text(raw.get("id"), 100).strip()
    if kind == "markdown":
        return FormField("markdown", ident, value=_text(attrs.get("value"), _MAX_TEXT)), ""
    label = _text(attrs.get("label"), 300).strip()
    if not label:
        return None, f"element {position} ({kind}) has no label"
    common: dict[str, Any] = {
        "id": ident,
        "label": label,
        "description": _text(attrs.get("description")),
        "required": bool(rules.get("required", False)),
    }
    if kind in ("input", "textarea"):
        return FormField(
            kind,
            placeholder=_text(attrs.get("placeholder")),
            value=_text(attrs.get("value"), _MAX_TEXT),
            render=_text(attrs.get("render"), 40).strip() if kind == "textarea" else "",
            **common,
        ), ""
    options = attrs.get("options")
    if kind == "dropdown":
        names = _strings(options)
        if not names:
            return None, f"the drop-down {label!r} has no options"
        default = attrs.get("default")
        index = default if isinstance(default, int) and 0 <= default < len(names) else -1
        return FormField(
            kind, options=names, multiple=bool(attrs.get("multiple")), default=index, **common
        ), ""
    rows = [row for row in options if isinstance(row, Mapping)] if isinstance(options, list) else []
    if not rows:
        return None, f"the check boxes {label!r} have no options"
    return FormField(
        kind,
        options=tuple(_text(row.get("label"), 300) for row in rows),
        required_options=tuple(bool(row.get("required", False)) for row in rows),
        **common,
    ), ""


def parse_issue_form(text: str, filename: str = "") -> IssueForm:
    """Read one issue form. Never raises: a form QUILL cannot fill says why."""
    fallback = (
        filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title() or "Issue form"
    )
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return IssueForm(fallback, unsupported="This copy of QUILL cannot read YAML.")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return IssueForm(fallback, unsupported=f"The form is not valid YAML: {exc}")
    if not isinstance(data, Mapping):
        return IssueForm(fallback, unsupported="The form has no fields QUILL can read.")
    body = data.get("body")
    if not isinstance(body, list) or not body:
        return IssueForm(fallback, unsupported="The form has no body elements.")
    fields: list[FormField] = []
    problems: list[str] = []
    seen: set[str] = set()
    for position, raw in enumerate(body, 1):
        if not isinstance(raw, Mapping):
            problems.append(f"element {position} is not a field")
            continue
        made, problem = _field(raw, position)
        if made is None:
            problems.append(problem)
            continue
        if made.id:
            if made.id in seen:
                problems.append(f"two elements share the id {made.id!r}")
            seen.add(made.id)
        fields.append(made)
    name = _text(data.get("name"), 200).strip() or fallback
    unsupported = ""
    if problems:
        unsupported = "QUILL cannot fill this form: " + "; ".join(problems) + "."
    return IssueForm(
        name=name,
        description=_text(data.get("description"), 500).strip(),
        title=_text(data.get("title"), 300),
        labels=_strings(data.get("labels")),
        assignees=_strings(data.get("assignees")),
        fields=tuple(fields),
        unsupported=unsupported,
        problems=tuple(problems),
    )


Answer = str | Sequence[str] | Sequence[bool]


def _answer_text(item: FormField, answer: object) -> str:
    """One field's answer as text ("" when empty)."""
    if item.kind == "dropdown":
        chosen = [answer] if isinstance(answer, str) else list(answer or [])  # type: ignore[call-overload]
        return ", ".join(str(c) for c in chosen if str(c).strip())
    return str(answer or "").strip()


def validate(form: IssueForm, answers: Mapping[str, object]) -> list[str]:
    """Required answers still missing, as sentences naming the field ([] when ready).

    *answers* is keyed by :func:`answer_key`; check boxes answer a sequence of
    booleans, one per option.
    """
    missing: list[str] = []
    for index, item in enumerate(form.fields):
        if not item.answers:
            continue
        answer = answers.get(answer_key(item, index))
        if item.kind == "checkboxes":
            checked = list(answer or [])  # type: ignore[call-overload]
            for option, must, ticked in zip(
                item.options,
                item.required_options,
                checked + [False] * len(item.options),
                strict=False,
            ):
                if must and not ticked:
                    missing.append(f"{item.label}: check {option!r}.")
        elif item.required and not _answer_text(item, answer):
            missing.append(f"{item.label} is required.")
    return missing


def answer_key(item: FormField, index: int) -> str:
    """The key an answer is stored under: the element's id, else its position."""
    return item.id or f"#{index}"


def render_body(form: IssueForm, answers: Mapping[str, object]) -> str:
    """The issue body GitHub's form would write for *answers*."""
    sections: list[str] = []
    for index, item in enumerate(form.fields):
        if not item.answers:
            continue
        answer = answers.get(answer_key(item, index))
        if item.kind == "checkboxes":
            checked = list(answer or [])  # type: ignore[call-overload]
            checked += [False] * (len(item.options) - len(checked))
            lines = [
                f"- [{'X' if ticked else ' '}] {option}"
                for option, ticked in zip(item.options, checked, strict=False)
            ]
            sections.append(f"### {item.label}\n\n" + "\n".join(lines))
            continue
        text = _answer_text(item, answer)
        if not text:
            text = _NO_RESPONSE
        elif item.kind == "textarea" and item.render:
            text = f"```{item.render}\n{text}\n```"
        sections.append(f"### {item.label}\n\n{text}")
    return "\n\n".join(sections)
