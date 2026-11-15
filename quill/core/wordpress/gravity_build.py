"""Building and editing a Gravity Forms form in QUILL (complete.md 10B.3, WP-C).

A Gravity Forms form is held exactly as REST API v2 returns it
(``GET gf/v2/forms/{id}``): one dict with ``title``, ``description``,
``labelPlacement``, ``button``, ``fields``, ``confirmations`` and
``notifications``. Every edit here works on a deep copy and touches only the
keys it names, so a property QUILL does not edit -- an add-on's settings, a
field family QUILL does not build, a key a newer Gravity Forms adds -- goes
back to the site exactly as it came.

The field families QUILL builds are :data:`FIELD_TYPES`. A field of any other
type (a product, an upload, a list) stays in the form and can be moved or
removed, never edited. Field ids are never reused: a new field takes the next
id above every id the form has had (``nextFieldId``, then the highest seen),
because entries keep their answers under the old id.

Conditional logic is Gravity Forms' own: ``{"actionType": "show"|"hide",
"logicType": "all", "rules": [{"fieldId", "operator", "value"}]}``. QUILL
edits a field's logic when it is one rule with ``is`` or ``isnot``; anything
richer is kept as it is and said so.

Saving, the checks and the QAF conversion are in
:mod:`quill.core.wordpress.gravity_build_save`,
:mod:`quill.core.wordpress.gravity_build_checks` and
:mod:`quill.core.wordpress.gravity_qaf`. Wx-free.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "CHOICE_TYPES",
    "DISPLAY_TYPES",
    "FIELD_TYPES",
    "LABEL_PLACEMENTS",
    "Condition",
    "Settings",
    "add_field",
    "admin_notification",
    "apply_settings",
    "choices_from_text",
    "choices_to_text",
    "condition_of",
    "default_confirmation",
    "edit_field",
    "field_line",
    "field_name",
    "fields_of",
    "is_editable",
    "move_field",
    "new_form",
    "remove_field",
    "set_condition",
    "settings_of",
]

#: The Gravity Forms field types QUILL builds and edits, with Gravity Forms' own names.
FIELD_TYPES: dict[str, str] = {
    "text": "Single Line Text",
    "textarea": "Paragraph Text",
    "email": "Email",
    "phone": "Phone",
    "number": "Number",
    "select": "Drop Down",
    "radio": "Radio Buttons",
    "checkbox": "Checkboxes",
    "multiselect": "Multi Select",
    "date": "Date",
    "time": "Time",
    "website": "Website",
    "name": "Name",
    "address": "Address",
    "consent": "Consent",
    "html": "HTML",
    "section": "Section",
    "page": "Page",
}
CHOICE_TYPES = frozenset({"select", "radio", "checkbox", "multiselect"})
#: Fields that show something rather than ask: no answer, no required.
DISPLAY_TYPES = frozenset({"html", "section", "page"})
#: Gravity Forms' label placements, as its form settings name them.
LABEL_PLACEMENTS: dict[str, str] = {
    "top_label": "Top aligned",
    "left_label": "Left aligned",
    "right_label": "Right aligned",
}
_OPERATORS = ("is", "isnot")

#: The sub-inputs Gravity Forms gives its complex fields, by input number.
_NAME_INPUTS = ((2, "Prefix", True), (3, "First", False), (4, "Middle", True),
                (6, "Last", False), (8, "Suffix", True))  # fmt: skip
_ADDRESS_INPUTS = ((1, "Street Address", False), (2, "Address Line 2", False), (3, "City", False),
                   (4, "State / Province", False), (5, "ZIP / Postal Code", False),
                   (6, "Country", False))  # fmt: skip
_TIME_INPUTS = ((1, "HH", False), (2, "MM", False), (3, "AM/PM", False))
_CONSENT_INPUTS = ((1, "Consent", False), (2, "Text", True), (3, "Description", True))

Form = dict[str, Any]
Field = dict[str, Any]


def _new_id() -> str:
    """Gravity Forms gives confirmations and notifications a 13-character uniqid."""
    return uuid.uuid4().hex[:13]


# --------------------------------------------------------------------------- #
# reading


def fields_of(form: Mapping[str, Any]) -> list[Field]:
    found = form.get("fields")
    return [f for f in found if isinstance(f, dict)] if isinstance(found, list) else []


def is_editable(field: Mapping[str, Any]) -> bool:
    """True for the families QUILL edits; any other field is moved or removed only."""
    return str(field.get("type", "")) in FIELD_TYPES


def field_name(field: Mapping[str, Any]) -> str:
    """How a field is spoken: its label, else its admin label, else its type and id."""
    label = str(field.get("label") or "").strip() or str(field.get("adminLabel") or "").strip()
    if label:
        return label
    kind = str(field.get("type", ""))
    return f"{FIELD_TYPES.get(kind, kind or 'Field')} {field.get('id', '')}".strip()


def field_line(field: Mapping[str, Any], number: int) -> str:
    """One row of the editor's field list: number, name, type, required, logic."""
    kind = str(field.get("type", ""))
    parts = [f"{number}. {field_name(field)}", FIELD_TYPES.get(kind, f"{kind}, kept as it is")]
    if field.get("isRequired") and kind not in DISPLAY_TYPES:
        parts.append("required")
    condition = condition_of(field)
    if isinstance(condition, Condition):
        parts.append(condition.spoken_short())
    elif condition == "complex":
        parts.append("has conditional logic QUILL keeps")
    return ", ".join(parts)


@dataclass(frozen=True, slots=True)
class Condition:
    """Show or hide a field when another field is, or is not, a value."""

    action: str  # "show" or "hide"
    field_id: str
    operator: str  # "is" or "isnot"
    value: str

    def spoken_short(self) -> str:
        verb = "shown" if self.action == "show" else "hidden"
        op = "is" if self.operator == "is" else "is not"
        return f"{verb} when field {self.field_id} {op} {self.value or 'empty'}"

    def sentence(self, form: Mapping[str, Any]) -> str:
        other = next((f for f in fields_of(form) if str(f.get("id")) == self.field_id), None)
        name = field_name(other) if other else f"field {self.field_id}"
        op = "is" if self.operator == "is" else "is not"
        return f"{self.action.title()} this field when {name} {op} {self.value or 'empty'}."


def condition_of(field: Mapping[str, Any]) -> Condition | str | None:
    """The field's one-rule logic, ``"complex"`` for logic QUILL keeps, or None."""
    logic = field.get("conditionalLogic")
    if not isinstance(logic, dict) or not logic:
        return None
    rules = logic.get("rules")
    action = str(logic.get("actionType", "show"))
    if (
        not isinstance(rules, list)
        or len(rules) != 1
        or not isinstance(rules[0], dict)
        or action not in ("show", "hide")
        or str(rules[0].get("operator", "is")) not in _OPERATORS
    ):
        return "complex"
    rule = rules[0]
    return Condition(
        action,
        str(rule.get("fieldId", "")),
        str(rule.get("operator", "is")),
        str(rule.get("value", "")),
    )


def set_condition(field: Field, condition: Condition | None) -> None:
    """Give *field* one rule of logic, or none (``""``, as Gravity Forms stores none)."""
    if condition is None:
        field["conditionalLogic"] = ""
        return
    if condition.action not in ("show", "hide") or condition.operator not in _OPERATORS:
        raise ValueError("A condition shows or hides, when a field is or is not a value.")
    field["conditionalLogic"] = {
        "actionType": condition.action,
        "logicType": "all",
        "rules": [
            {
                "fieldId": condition.field_id,
                "operator": condition.operator,
                "value": condition.value,
            }
        ],
    }


# --------------------------------------------------------------------------- #
# choices as text: one a line, "text = value", "*" first for chosen at the start


def choices_to_text(choices: Any) -> str:
    lines = []
    for choice in choices if isinstance(choices, list) else []:
        if not isinstance(choice, dict):
            continue
        text = str(choice.get("text", ""))
        value = str(choice.get("value", text))
        line = text if value == text else f"{text} = {value}"
        lines.append(("* " if choice.get("isSelected") else "") + line)
    return "\n".join(lines)


def choices_from_text(text: str, old: Any = None) -> list[dict[str, Any]]:
    """The choices *text* describes, each keeping what it had before (a price, say)."""
    before = [c for c in old if isinstance(c, dict)] if isinstance(old, list) else []
    out: list[dict[str, Any]] = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        selected = line.startswith("*")
        line = line.lstrip("*").strip()
        label, _sep, value = line.partition(" = ")
        label = label.strip()
        value = value.strip() if _sep else label
        match = next(
            (c for c in before if str(c.get("value", "")) == value or c.get("text") == label), None
        )
        if match is not None:
            before.remove(match)
        choice = dict(match) if match is not None else {}
        choice.update({"text": label, "value": value, "isSelected": selected})
        choice.setdefault("price", "")
        out.append(choice)
    return out


# --------------------------------------------------------------------------- #
# making and changing fields


def _next_id(form: Form, ever: Sequence[int] = ()) -> int:
    ids = [int(f["id"]) for f in fields_of(form) if str(f.get("id", "")).isdigit()]
    ids += [int(i) for i in ever]
    try:
        ids.append(int(form.get("nextFieldId") or 0) - 1)
    except (TypeError, ValueError):
        pass
    return max([0, *ids]) + 1


def _inputs(field_id: int, table: Sequence[tuple[int, str, bool]]) -> list[dict[str, Any]]:
    out = []
    for number, label, hidden in table:
        sub: dict[str, Any] = {"id": f"{field_id}.{number}", "label": label, "name": ""}
        if hidden:
            sub["isHidden"] = True
        out.append(sub)
    return out


def _checkbox_inputs(field: Field) -> list[dict[str, Any]]:
    """One input per choice, numbered as Gravity Forms numbers them (no multiples of ten).

    An input keeps its id by position, so answers already given stay where they are.
    """
    old = [i for i in field.get("inputs") or [] if isinstance(i, dict)]
    used = {str(i.get("id", "")) for i in old}
    out = []
    number = 0
    for index, choice in enumerate(field.get("choices") or []):
        if index < len(old):
            sub = dict(old[index])
        else:
            while True:
                number += 1
                candidate = f"{field['id']}.{number}"
                if number % 10 and candidate not in used:
                    break
            sub = {"id": candidate, "name": ""}
            used.add(candidate)
        sub["label"] = str(choice.get("text", ""))
        out.append(sub)
    return out


def _blank(kind: str, field_id: int, form_id: Any) -> Field:
    field: Field = {
        "type": kind,
        "id": field_id,
        "formId": form_id,
        "label": "",
        "adminLabel": "",
        "isRequired": False,
        "description": "",
        "placeholder": "",
        "defaultValue": "",
        "cssClass": "",
        "visibility": "visible",
        "conditionalLogic": "",
        "inputs": None,
        "choices": "",
    }
    if kind in DISPLAY_TYPES:
        field["displayOnly"] = True
    if kind in CHOICE_TYPES:
        field["choices"] = []
        field["enableChoiceValue"] = False
    if kind == "checkbox":
        field["inputs"] = []
    if kind == "phone":
        field["phoneFormat"] = "standard"
    if kind == "date":
        field.update({"dateType": "datepicker", "dateFormat": "mdy", "calendarIconType": "none"})
    if kind == "time":
        field.update({"timeFormat": "12", "inputs": _inputs(field_id, _TIME_INPUTS)})
    if kind == "name":
        field.update({"nameFormat": "advanced", "inputs": _inputs(field_id, _NAME_INPUTS)})
    if kind == "address":
        field.update({"addressType": "international", "inputs": _inputs(field_id, _ADDRESS_INPUTS)})
    if kind == "consent":
        field.update({
            "checkboxLabel": "I agree.",
            "inputs": _inputs(field_id, _CONSENT_INPUTS),
            "choices": [{"text": "Checked", "value": "1", "price": ""}],
        })
    if kind == "html":
        field["content"] = ""
    if kind == "page":
        field["nextButton"] = {"type": "text", "text": "Next", "imageUrl": ""}
        field["previousButton"] = {"type": "text", "text": "Previous", "imageUrl": ""}
    return field


def add_field(
    form: Form,
    kind: str,
    values: Mapping[str, Any],
    *,
    at: int | None = None,
    ever: Sequence[int] = (),
) -> Field:
    """A new *kind* field with *values*, placed at *at* (the end when None); returns it.

    *ever* is every field id the form had when it was opened, so a removed field's
    id is never given out again in the same edit.
    """
    if kind not in FIELD_TYPES:
        raise ValueError(f"QUILL does not build {kind} fields.")
    fields = form.setdefault("fields", [])
    field = _blank(kind, _next_id(form, ever), form.get("id", ""))
    edit_field(field, values)
    fields.insert(len(fields) if at is None else max(0, min(at, len(fields))), field)
    form["nextFieldId"] = int(field["id"]) + 1
    return field


#: The keys :func:`edit_field` sets, and the editor's names for them.
EDITABLE = {
    "label": "label",
    "description": "description",
    "isRequired": "required",
    "placeholder": "placeholder",
    "defaultValue": "default value",
    "adminLabel": "admin label",
    "cssClass": "CSS class",
    "choices": "choices",
    "content": "content",
    "checkboxLabel": "check box text",
}


def edit_field(field: Field, values: Mapping[str, Any]) -> list[str]:
    """Set the properties in *values* (keys of :data:`EDITABLE`); returns what changed."""
    if not is_editable(field):
        raise ValueError(
            f"{field_name(field)} is a {field.get('type')} field; QUILL keeps it as is."
        )
    kind = str(field.get("type"))
    changed = []
    for key, value in values.items():
        if key not in EDITABLE:
            continue
        if key == "choices":
            if kind not in CHOICE_TYPES:
                continue
            value = (
                choices_from_text(value, field.get("choices")) if isinstance(value, str) else value
            )
        if key == "isRequired":
            value = bool(value) and kind not in DISPLAY_TYPES
        if key == "content" and kind != "html":
            continue
        if key == "checkboxLabel" and kind != "consent":
            continue
        if field.get(key, "" if key != "isRequired" else False) != value:
            changed.append(EDITABLE[key])
            field[key] = value
    if kind == "checkbox":
        field["inputs"] = _checkbox_inputs(field)
    if kind in CHOICE_TYPES and isinstance(field.get("choices"), list):
        field["enableChoiceValue"] = bool(field.get("enableChoiceValue")) or any(
            str(c.get("value")) != str(c.get("text")) for c in field["choices"]
        )
    return changed


def move_field(form: Form, index: int, step: int) -> int:
    """Move the field at *index* by *step*; returns where it is now."""
    fields = form.get("fields")
    if not isinstance(fields, list) or not 0 <= index < len(fields):
        return index
    target = max(0, min(len(fields) - 1, index + step))
    if target != index:
        fields.insert(target, fields.pop(index))
    return target


def remove_field(form: Form, index: int) -> Field | None:
    """Take the field at *index* out, and any logic that pointed at it."""
    fields = form.get("fields")
    if not isinstance(fields, list) or not 0 <= index < len(fields):
        return None
    gone = fields.pop(index)
    gone_id = str(gone.get("id", "")) if isinstance(gone, dict) else ""
    for field in fields_of(form):
        condition = condition_of(field)
        if isinstance(condition, Condition) and condition.field_id == gone_id:
            set_condition(field, None)
    return gone if isinstance(gone, dict) else None


# --------------------------------------------------------------------------- #
# the form's own settings


def _records(form: Form, key: str) -> list[dict[str, Any]]:
    found = form.get(key)
    values = found.values() if isinstance(found, dict) else found if isinstance(found, list) else []
    return [r for r in values if isinstance(r, dict)]


def default_confirmation(form: Form) -> dict[str, Any] | None:
    found = _records(form, "confirmations")
    return next((c for c in found if c.get("isDefault") in (True, 1, "1", "true")), None) or (
        found[0] if found else None
    )


def admin_notification(form: Form) -> dict[str, Any] | None:
    found = _records(form, "notifications")
    named = next((n for n in found if str(n.get("name", "")) == "Admin Notification"), None)
    return named or (found[0] if found else None)


@dataclass(frozen=True, slots=True)
class Settings:
    """What the editor's form page shows and changes."""

    title: str = ""
    description: str = ""
    button: str = "Submit"
    label_placement: str = "top_label"
    confirmation: str = ""
    confirmation_editable: bool = True
    notify_to: str = ""
    notify_to_editable: bool = True
    notify_subject: str = ""
    has_notification: bool = True


def settings_of(form: Form) -> Settings:
    raw_button = form.get("button")
    button: dict[str, Any] = raw_button if isinstance(raw_button, dict) else {}
    confirmation = default_confirmation(form) or {}
    notification = admin_notification(form)
    note = notification or {}
    return Settings(
        title=str(form.get("title") or ""),
        description=str(form.get("description") or ""),
        button=str(button.get("text") or "Submit"),
        label_placement=str(form.get("labelPlacement") or "top_label"),
        confirmation=str(confirmation.get("message") or ""),
        confirmation_editable=str(confirmation.get("type") or "message") == "message",
        notify_to=str(note.get("to") or ""),
        notify_to_editable=str(note.get("toType") or "email") == "email",
        notify_subject=str(note.get("subject") or ""),
        has_notification=notification is not None,
    )


def apply_settings(form: Form, settings: Settings) -> None:
    """Write *settings* into *form*, leaving every other key of each record alone."""
    form["title"] = settings.title
    form["description"] = settings.description
    if settings.label_placement in LABEL_PLACEMENTS:
        form["labelPlacement"] = settings.label_placement
    button = form.get("button") if isinstance(form.get("button"), dict) else None
    if button is None:
        button = form["button"] = {"type": "text", "text": "", "imageUrl": ""}
    if button.get("text") != settings.button:
        button["text"] = settings.button
    confirmation = default_confirmation(form)
    if confirmation is not None and settings.confirmation_editable:
        if confirmation.get("message") != settings.confirmation:
            confirmation["message"] = settings.confirmation
    notification = admin_notification(form)
    if notification is not None:
        if settings.notify_to_editable and notification.get("to") != settings.notify_to:
            notification["to"] = settings.notify_to
        if notification.get("subject") != settings.notify_subject:
            notification["subject"] = settings.notify_subject


def new_form(title: str, *, make_id: Callable[[], str] = _new_id) -> Form:
    """A new form as Gravity Forms makes one: a Submit button, its default confirmation
    and its Admin Notification, and no fields yet."""
    confirmation_id, notification_id = make_id(), make_id()
    return {
        "title": title,
        "description": "",
        "labelPlacement": "top_label",
        "descriptionPlacement": "below",
        "button": {"type": "text", "text": "Submit", "imageUrl": ""},
        "fields": [],
        "is_active": True,
        "confirmations": {
            confirmation_id: {
                "id": confirmation_id,
                "name": "Default Confirmation",
                "isDefault": True,
                "type": "message",
                "message": "Thanks for contacting us! We will get in touch with you shortly.",
                "url": "",
                "pageId": "",
                "queryString": "",
            }
        },
        "notifications": {
            notification_id: {
                "id": notification_id,
                "name": "Admin Notification",
                "isActive": True,
                "event": "form_submission",
                "toType": "email",
                "to": "{admin_email}",
                "subject": "New submission from {form_title}",
                "message": "{all_fields}",
            }
        },
    }
