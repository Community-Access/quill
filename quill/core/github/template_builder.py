"""Build and check GitHub issue forms and discussion forms (GitHub PRD 21.3 to 21.5).

A :class:`FormDraft` is the YAML of one form held as plain dictionaries, so
whatever the builder does not know (``projects``, ``type``, a future key)
survives the round trip untouched: the builder only ever changes the keys it
was asked to change. Fields are the ``body`` elements in order; the builder's
list is that order, and Move Up and Move Down change it.

:func:`check` finds what GitHub would only report after the form was on the
default branch -- missing name or description, a field with no label, ids
or labels used twice, ids with characters GitHub refuses, drop-downs and
check boxes without options or with "None" -- and a few accessibility habits
from QUILL's Forms checks. Each problem names its field.

Starters (bug report, feature request, accessibility bug report, blank) and
:func:`markdown_to_form` (a Markdown template's ``###`` headings become long
text fields) start a draft. YAML is read with ``yaml.safe_load`` only.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "FIELD_KIND_NAMES",
    "STARTERS",
    "FormDraft",
    "TemplateDraftError",
    "TemplateProblem",
    "check",
    "dump_draft",
    "field_summary",
    "load_draft",
    "make_id",
    "markdown_to_form",
    "new_field",
    "starter",
    "update_field",
]

#: Each element type, as the builder names it.
FIELD_KIND_NAMES: dict[str, str] = {
    "markdown": "instructions",
    "input": "short text",
    "textarea": "long text",
    "dropdown": "drop-down",
    "checkboxes": "check boxes",
}
_TOP_KEYS = {"name", "description", "title", "labels", "assignees", "projects", "type", "body"}
_FIELD_KEYS = {"type", "id", "attributes", "validations"}
_ATTRIBUTE_KEYS = {
    "label",
    "description",
    "placeholder",
    "value",
    "render",
    "options",
    "multiple",
    "default",
}
_ID = re.compile(r"^[A-Za-z0-9_-]+$")
#: The largest form QUILL will load or save (GitHub's own limit is larger).
MAX_FORM_BYTES = 50_000


class TemplateDraftError(CodedError):
    """A template QUILL could not read as a form; the message says why."""

    code = "QUILL-GITHUB-TEMPLATE-UNREADABLE"


@dataclass(frozen=True, slots=True)
class TemplateProblem:
    """One problem: ``error`` stops a save, ``warning`` is said and allowed."""

    where: str
    message: str
    severity: str = "error"

    def sentence(self) -> str:
        prefix = "Warning: " if self.severity == "warning" else ""
        return f"{prefix}{self.where}: {self.message}"


@dataclass
class FormDraft:
    """One form's YAML as dictionaries; :attr:`fields` is ``body`` in order."""

    top: dict[str, Any] = field(default_factory=dict)
    fields: list[dict[str, Any]] = field(default_factory=list)
    #: "issue_form" or "discussion_form": a discussion form has no name.
    kind: str = "issue_form"

    def get(self, key: str) -> str:
        value = self.top.get(key)
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return "" if value is None else str(value)

    def set(self, key: str, value: str) -> None:
        """Set a top-level key, or remove it when *value* is empty."""
        value = value.strip() if key != "title" else value
        if key in ("labels", "assignees", "projects"):
            parts = [part.strip() for part in value.split(",") if part.strip()]
            if parts:
                self.top[key] = parts
            else:
                self.top.pop(key, None)
            return
        if value:
            self.top[key] = value
        else:
            self.top.pop(key, None)

    def move(self, index: int, delta: int) -> int:
        """Move field *index* by *delta*; returns where it now is."""
        target = index + delta
        if not 0 <= index < len(self.fields) or not 0 <= target < len(self.fields):
            return index
        self.fields[index], self.fields[target] = self.fields[target], self.fields[index]
        return target

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.fields):
            del self.fields[index]

    def ids(self, skip: int = -1) -> frozenset[str]:
        return frozenset(
            str(raw.get("id"))
            for position, raw in enumerate(self.fields)
            if position != skip and raw.get("id")
        )


def load_draft(text: str, *, kind: str = "issue_form") -> FormDraft:
    """Read a form's YAML; raises :class:`TemplateDraftError` saying why it cannot."""
    if len(text.encode("utf-8")) > MAX_FORM_BYTES:
        raise TemplateDraftError(
            f"The form is larger than {MAX_FORM_BYTES // 1000} KB; edit its source instead."
        )
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise TemplateDraftError("This copy of QUILL cannot read YAML.") from exc
    try:
        data = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError as exc:
        raise TemplateDraftError(f"The form is not valid YAML: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TemplateDraftError("The form's top level is not a set of keys.")
    body = data.pop("body", [])
    if body is None:
        body = []
    if not isinstance(body, list) or not all(isinstance(raw, dict) for raw in body):
        raise TemplateDraftError("The form's body is not a list of fields.")
    return FormDraft(top=dict(data), fields=[dict(raw) for raw in body], kind=kind)


def dump_draft(draft: FormDraft) -> str:
    """The draft as YAML, keys in the order they were read (body last)."""
    import yaml

    data = dict(draft.top)
    data["body"] = draft.fields
    return str(
        yaml.safe_dump(
            data, sort_keys=False, allow_unicode=True, default_flow_style=False, width=4096
        )
    )


def make_id(label: str, taken: Iterable[str] = ()) -> str:
    """An id made from *label*: lower case, hyphens, unique among *taken*."""
    base = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")[:60] or "field"
    used = set(taken)
    candidate, number = base, 2
    while candidate in used:
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def new_field(
    kind: str,
    label: str = "",
    *,
    taken: Iterable[str] = (),
    required: bool = False,
    description: str = "",
    placeholder: str = "",
    value: str = "",
    render: str = "",
    options: Iterable[str] = (),
    required_options: Iterable[bool] = (),
    multiple: bool = False,
    default: int = -1,
    ident: str | None = None,
) -> dict[str, Any]:
    """One body element, written the way GitHub's documentation writes them."""
    if kind not in FIELD_KIND_NAMES:
        raise TemplateDraftError(f"GitHub forms have no {kind!r} field.")
    if kind == "markdown":
        return {"type": "markdown", "attributes": {"value": value}}
    attrs: dict[str, Any] = {"label": label}
    if description:
        attrs["description"] = description
    if kind in ("input", "textarea"):
        if placeholder:
            attrs["placeholder"] = placeholder
        if value:
            attrs["value"] = value
        if kind == "textarea" and render:
            attrs["render"] = render
    elif kind == "dropdown":
        attrs["options"] = list(options)
        if multiple:
            attrs["multiple"] = True
        if default >= 0:
            attrs["default"] = default
    else:
        musts = list(required_options)
        attrs["options"] = [
            {"label": option, **({"required": True} if index < len(musts) and musts[index] else {})}
            for index, option in enumerate(options)
        ]
    raw: dict[str, Any] = {
        "type": kind,
        "id": ident if ident is not None else make_id(label, taken),
        "attributes": attrs,
    }
    if not raw["id"]:
        raw.pop("id")
    if required and kind != "checkboxes":
        raw["validations"] = {"required": True}
    return raw


def update_field(raw: dict[str, Any], replacement: Mapping[str, Any]) -> dict[str, Any]:
    """*replacement* over *raw*, keeping any key the builder does not edit."""
    merged = {**raw, **{k: v for k, v in replacement.items() if k != "attributes"}}
    attrs = dict(raw.get("attributes") or {})
    for key in _ATTRIBUTE_KEYS:
        attrs.pop(key, None)
    attrs.update(replacement.get("attributes") or {})
    merged["attributes"] = attrs
    if "validations" not in replacement:
        rules = dict(raw.get("validations") or {})
        rules.pop("required", None)
        if rules:
            merged["validations"] = rules
        else:
            merged.pop("validations", None)
    if "id" not in replacement:
        merged.pop("id", None)
    return merged


def _attrs(raw: Mapping[str, Any]) -> dict[str, Any]:
    attrs = raw.get("attributes")
    return dict(attrs) if isinstance(attrs, Mapping) else {}


def _required(raw: Mapping[str, Any]) -> bool:
    rules = raw.get("validations")
    return bool(rules.get("required")) if isinstance(rules, Mapping) else False


def _option_labels(raw: Mapping[str, Any]) -> list[str]:
    options = _attrs(raw).get("options")
    if not isinstance(options, list):
        return []
    if raw.get("type") == "checkboxes":
        return [str(o.get("label", "")) if isinstance(o, Mapping) else str(o) for o in options]
    return [str(o) for o in options]


def field_summary(raw: Mapping[str, Any]) -> str:
    """One builder row: "Steps to reproduce, long text, required"."""
    kind = str(raw.get("type") or "")
    name = FIELD_KIND_NAMES.get(kind, f"unknown kind {kind or 'none'}")
    attrs = _attrs(raw)
    if kind == "markdown":
        text = " ".join(str(attrs.get("value") or "").split())
        return f"Instructions: {text[:60] or '(empty)'}"
    parts = [str(attrs.get("label") or "(no label)"), name]
    options = _option_labels(raw)
    if options:
        parts.append(f"{len(options)} options")
    if _required(raw):
        parts.append("required")
    return ", ".join(parts)


def _where(raw: Mapping[str, Any], position: int) -> str:
    label = str(_attrs(raw).get("label") or "").strip()
    return f"Field {position} ({label})" if label else f"Field {position}"


def check(
    draft: FormDraft,
    *,
    other_names: Iterable[str] = (),
    known_labels: Iterable[str] | None = None,
    known_assignees: Iterable[str] | None = None,
) -> list[TemplateProblem]:
    """Every problem GitHub would report, and the accessibility habits, in order."""
    found: list[TemplateProblem] = []
    add = found.append
    if draft.kind == "issue_form":
        name = draft.get("name").strip()
        if not name:
            add(TemplateProblem("Name", "an issue form needs a name"))
        elif name.casefold() in {n.casefold() for n in other_names}:
            add(TemplateProblem("Name", "another template in this repository has this name"))
        if not draft.get("description").strip():
            add(TemplateProblem("Description", "an issue form needs a description"))
    for key in sorted(set(draft.top) - _TOP_KEYS):
        add(
            TemplateProblem(
                key, "GitHub's forms do not know this key; it is kept as written", "warning"
            )
        )
    if known_labels is not None:
        known = {label.casefold() for label in known_labels}
        for label in draft.top.get("labels") or []:
            if str(label).casefold() not in known:
                add(
                    TemplateProblem(
                        "Labels",
                        f"the label {label!r} does not exist; GitHub drops it silently",
                        "warning",
                    )
                )
    if known_assignees is not None:
        people = {login.casefold() for login in known_assignees}
        for login in draft.top.get("assignees") or []:
            if str(login).lstrip("@").casefold() not in people:
                add(
                    TemplateProblem(
                        "Assignees",
                        f"{login} cannot be assigned in this repository; GitHub skips them",
                        "warning",
                    )
                )
    if not draft.fields:
        add(TemplateProblem("Fields", "the form has no fields"))
    elif all(raw.get("type") == "markdown" for raw in draft.fields):
        add(TemplateProblem("Fields", "at least one field must be something to fill in"))
    ids: dict[str, int] = {}
    labels: dict[str, int] = {}
    for position, raw in enumerate(draft.fields, 1):
        where = _where(raw, position)
        kind = str(raw.get("type") or "")
        attrs = _attrs(raw)
        if kind not in FIELD_KIND_NAMES:
            add(TemplateProblem(where, f"GitHub has no field of kind {kind or 'none'}"))
            continue
        for key in sorted(set(raw) - _FIELD_KEYS):
            add(TemplateProblem(where, f"unknown key {key!r}, kept as written", "warning"))
        ident = str(raw.get("id") or "")
        if ident:
            if not _ID.match(ident):
                add(
                    TemplateProblem(
                        where, f"the id {ident!r} may use only letters, numbers, - and _"
                    )
                )
            if ident in ids:
                add(TemplateProblem(where, f"the id {ident!r} is also field {ids[ident]}'s"))
            ids.setdefault(ident, position)
        if kind == "markdown":
            if not str(attrs.get("value") or "").strip():
                add(TemplateProblem(where, "instructions need some text"))
            if ident:
                add(TemplateProblem(where, "instructions cannot have an id"))
            continue
        label = str(attrs.get("label") or "").strip()
        if not label:
            add(TemplateProblem(where, "every field but instructions needs a label"))
        else:
            folded = label.casefold()
            if folded in labels:
                add(TemplateProblem(where, f"the label is also field {labels[folded]}'s"))
            labels.setdefault(folded, position)
        if kind in ("dropdown", "checkboxes"):
            options = _option_labels(raw)
            if not options:
                add(TemplateProblem(where, "needs at least one option"))
            if any(not o.strip() for o in options):
                add(TemplateProblem(where, "an option is empty"))
            folded_options = [o.casefold() for o in options]
            if len(set(folded_options)) < len(folded_options):
                add(TemplateProblem(where, "two options are the same"))
            if "none" in folded_options and kind == "dropdown":
                add(TemplateProblem(where, '"None" is reserved by GitHub; use another word'))
            default = attrs.get("default")
            if kind == "dropdown" and default is not None:
                if not isinstance(default, int) or not 0 <= default < len(options):
                    add(TemplateProblem(where, "the default is not one of the options"))
            if kind == "checkboxes" and _required(raw):
                add(
                    TemplateProblem(
                        where,
                        "check boxes are required per option, not as a whole",
                        "warning",
                    )
                )
        if attrs.get("placeholder") and not attrs.get("description") and len(label) < 4:
            add(
                TemplateProblem(
                    where,
                    "the placeholder disappears once someone types; say it in the description",
                    "warning",
                )
            )
        if len(str(attrs.get("description") or "")) > 300:
            add(TemplateProblem(where, "the description is long; keep it short", "warning"))
    return found


def _bug(kind: str) -> FormDraft:
    taken: list[str] = []

    def add(*args: Any, **kwargs: Any) -> dict[str, Any]:
        made = new_field(*args, taken=taken, **kwargs)
        taken.append(str(made.get("id") or ""))
        return made

    draft = FormDraft(
        top={
            "name": "Bug report",
            "description": "Something does not work as it should.",
            "title": "[Bug]: ",
            "labels": ["bug"],
        },
        kind=kind,
    )
    draft.fields = [
        add("markdown", value="Thanks for taking the time to report this."),
        add(
            "textarea",
            "What happened?",
            description="What you did, what you expected, and what happened instead.",
            required=True,
        ),
        add("textarea", "Steps to reproduce", description="One step per line.", required=True),
        add("input", "Version", description="The version you were using."),
    ]
    return draft


def _feature(kind: str) -> FormDraft:
    draft = FormDraft(
        top={
            "name": "Feature request",
            "description": "Suggest something new.",
            "title": "[Feature]: ",
            "labels": ["enhancement"],
        },
        kind=kind,
    )
    draft.fields = [
        new_field(
            "textarea",
            "What would you like?",
            description="Describe the feature and who it helps.",
            required=True,
        ),
        new_field(
            "textarea",
            "Why?",
            description="The problem it solves.",
            taken=("what-would-you-like",),
        ),
    ]
    return draft


def _accessibility(kind: str) -> FormDraft:
    draft = _bug(kind)
    draft.top.update({
        "name": "Accessibility bug report",
        "description": "Something does not work with a screen reader, keyboard or magnifier.",
        "title": "[Accessibility]: ",
        "labels": ["bug", "accessibility"],
    })
    taken: list[str] = list(draft.ids())
    for label, options in (
        ("Screen reader", ["NVDA", "JAWS", "Narrator", "VoiceOver", "Other", "No screen reader"]),
        ("Browser or app", ["Chrome", "Edge", "Firefox", "Safari", "The desktop app", "Other"]),
    ):
        made = new_field("dropdown", label, options=options, taken=taken, required=True)
        taken.append(str(made["id"]))
        draft.fields.append(made)
    draft.fields.append(
        new_field(
            "input",
            "Assistive technology version",
            description="For example NVDA 2025.3.",
            taken=taken,
        )
    )
    return draft


def _blank(kind: str) -> FormDraft:
    top = {"name": "New form", "description": "What this form is for."}
    if kind == "discussion_form":
        top = {}
    return FormDraft(
        top=top,
        fields=[new_field("textarea", "Details", required=True)],
        kind=kind,
    )


#: Starter name -> what it is, in the New Template chooser's order.
STARTERS: dict[str, str] = {
    "bug": "Bug report",
    "feature": "Feature request",
    "accessibility": "Accessibility bug report",
    "blank": "Blank form",
}


def starter(name: str, *, kind: str = "issue_form") -> FormDraft:
    """A starter draft; discussion forms drop the issue-only keys."""
    made = {"bug": _bug, "feature": _feature, "accessibility": _accessibility}.get(name, _blank)(
        kind
    )
    if kind == "discussion_form":
        for key in ("name", "description", "assignees", "projects", "type"):
            made.top.pop(key, None)
    return made


def markdown_to_form(text: str, *, filename: str = "") -> FormDraft:
    """A Markdown issue template as an issue form.

    Front matter becomes the form's keys (``about`` becomes ``description``);
    text before the first heading becomes instructions; each ``##`` or ``###``
    heading becomes a long-text field whose description is the text under it.
    """
    from quill.core.github.issue_templates import _front_matter, _list_value

    metadata, body = _front_matter(text)
    fallback = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip().title()
    top: dict[str, Any] = {
        "name": str(metadata.get("name") or fallback or "Converted template"),
        "description": str(metadata.get("about") or "Converted from a Markdown template."),
    }
    if metadata.get("title"):
        top["title"] = str(metadata["title"])
    for key in ("labels", "assignees"):
        values = _list_value(metadata.get(key, ""))
        if values:
            top[key] = list(values)
    draft = FormDraft(top=top)
    heading = ""
    lines: list[str] = []

    def flush() -> None:
        content = "\n".join(lines).strip()
        if heading:
            draft.fields.append(
                new_field(
                    "textarea",
                    heading,
                    description=" ".join(re.sub(r"<!--|--!?>", "", content).split())[:300],
                    taken=draft.ids(),
                )
            )
        elif content:
            draft.fields.append(new_field("markdown", value=content))

    for line in body.splitlines():
        match = re.match(r"^#{2,3}\s+(.+?)\s*#*\s*$", line)
        if match:
            flush()
            heading, lines = match.group(1), []
        else:
            lines.append(line)
    flush()
    if not any(raw.get("type") != "markdown" for raw in draft.fields):
        draft.fields.append(new_field("textarea", "Details", taken=draft.ids()))
    return draft
