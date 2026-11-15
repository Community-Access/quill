"""Gravity Forms forms to QUILL Accessible Forms models and back (WP-C).

Both directions make a **new** form and say, line by line, what cannot carry
over, so the preview can show it before anything is sent:

- :func:`to_qaf`: a Gravity Forms form object as a QAF model
  (``quill/core/forms/schema/form.schema.json``). Page breaks become pages,
  sections become sections holding the questions after them, one-rule logic
  becomes a ``when`` expression. A CSS class, an admin label and any field
  family QAF has no match for are listed as lost.
- :func:`to_gravity`: a QAF model as a Gravity Forms form, through
  :func:`quill.core.wordpress.gravity_build.add_field`, so it is built exactly
  as New Gravity Form builds one. A ``when`` that is not "this field is, or is
  not, a value" (or its ``not``) is listed as lost; so are columns' layout,
  rules, scoring and translations.

The editor also uses :func:`to_qaf` to run QUILL's own QAF checks over a
Gravity Forms form. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.wordpress.gravity_build import (
    FIELD_TYPES,
    Condition,
    add_field,
    admin_notification,
    apply_settings,
    condition_of,
    default_confirmation,
    field_name,
    fields_of,
    new_form,
    set_condition,
    settings_of,
)

__all__ = ["Conversion", "qaf_id", "to_gravity", "to_qaf"]

#: The field families both plugins have under the same name.
SHARED = frozenset(FIELD_TYPES) - {"section", "page"}


@dataclass
class Conversion:
    """The converted form, and a sentence for each thing that could not carry over."""

    form: dict[str, Any]
    lost: list[str] = dc_field(default_factory=list)


def qaf_id(gravity_id: Any) -> str:
    """The QAF id a Gravity Forms field gets: ``field_3`` for field 3."""
    return f"field_{str(gravity_id).replace('.', '_')}"


# --------------------------------------------------------------------------- #
# Gravity Forms to QAF


def _when(condition: Condition) -> str:
    test: dict[str, Any] = {
        "type": "op",
        "op": "is" if condition.operator == "is" else "is_not",
        "args": [
            {"type": "ref", "field": qaf_id(condition.field_id)},
            {"type": "literal", "value": condition.value},
        ],
    }
    if condition.action == "hide":
        test = {"type": "op", "op": "not", "args": [test]}
    return str(E.to_text(test))


def _qaf_choices(field: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for choice in field.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        label = str(choice.get("text") or "")
        value = str(choice.get("value") or "") or M.slug(label) or "choice"
        base, n = value, 1
        while value in seen:
            n += 1
            value = f"{base}-{n}"
        seen.add(value)
        item: dict[str, Any] = {"value": value, "label": label}
        if choice.get("isSelected"):
            item["selected"] = True
        out.append(item)
    return out


def _qaf_item(field: Mapping[str, Any], lost: list[str]) -> dict[str, Any]:
    kind = str(field.get("type"))
    item: dict[str, Any] = {"id": qaf_id(field.get("id")), "type": kind}
    if str(field.get("label") or ""):
        item["label"] = str(field["label"])
    if str(field.get("description") or ""):
        item["help"] = str(field["description"])
    if kind == "html":
        item["props"] = {"html": str(field.get("content") or "")}
        return item
    if field.get("isRequired"):
        item["required"] = True
    if str(field.get("placeholder") or ""):
        item["placeholder"] = str(field["placeholder"])
    if str(field.get("defaultValue") or ""):
        item["default"] = str(field["defaultValue"])
    if kind in ("select", "radio", "checkbox", "multiselect"):
        item["choices"] = _qaf_choices(field)
    if kind == "consent":
        item["choices"] = [{"value": "1", "label": str(field.get("checkboxLabel") or "I agree.")}]
    for key, word in (("cssClass", "CSS class"), ("adminLabel", "admin label")):
        if str(field.get(key) or "").strip():
            lost.append(f"{field_name(field)}: its {word} cannot carry over.")
    return item


def to_qaf(form: Mapping[str, Any]) -> Conversion:
    """*form* (Gravity Forms) as a new QAF model."""
    lost: list[str] = []
    model = M.create(str(form.get("title") or "Untitled form"))
    if str(form.get("description") or ""):
        model["description"] = str(form["description"])
    page = model["pages"][0]
    target: list[dict[str, Any]] = page["items"]
    for field in fields_of(form):
        kind = str(field.get("type", ""))
        if kind == "page":
            page = {"id": f"page_{len(model['pages']) + 1}", "items": []}
            if str(field.get("label") or ""):
                page["title"] = str(field["label"])
            model["pages"].append(page)
            target = page["items"]
            continue
        if kind == "section":
            section: dict[str, Any] = {
                "type": "section",
                "id": qaf_id(field.get("id")),
                "items": [],
            }
            if str(field.get("label") or ""):
                section["label"] = str(field["label"])
            if str(field.get("description") or ""):
                section["help"] = str(field["description"])
            page["items"].append(section)
            target = section["items"]
            continue
        if kind not in SHARED:
            lost.append(
                f"{field_name(field)} is a {kind} field, which QUILL Accessible Forms "
                "has no match for."
            )
            continue
        item = _qaf_item(field, lost)
        condition = condition_of(field)
        if isinstance(condition, Condition):
            item["when"] = _when(condition)
        elif condition == "complex":
            lost.append(f"{field_name(field)}: its conditional logic has more than one rule.")
        target.append(item)
    known = {str(i.get("id")) for i in M.iter_items(model)}
    for item in M.iter_items(model):
        when = item.get("when")
        if when and any(ref not in known for ref in E.refs(E.parse(when))):
            del item["when"]
            lost.append(
                f"{item.get('label') or item['id']}: its logic names a field that does not "
                "carry over."
            )
    settings = settings_of(dict(form))
    confirmation = default_confirmation(dict(form))
    if confirmation is not None:
        if settings.confirmation_editable:
            model["confirmations"] = [
                {"id": "confirmation_1", "type": "message", "message": settings.confirmation}
            ]
        else:
            lost.append("The confirmation sends people to a page or address; it cannot carry over.")
    if admin_notification(dict(form)) is not None:
        note: dict[str, Any] = {"id": "notification_1", "subject": settings.notify_subject}
        if "@" in settings.notify_to and "{" not in settings.notify_to:
            note["to"] = settings.notify_to
        else:
            lost.append(
                f"The notification goes to {settings.notify_to or 'a field'}, which QUILL "
                "Accessible Forms cannot read; set its To there."
            )
        model["notifications"] = [note]
    if settings.button.strip() and settings.button != "Submit":
        lost.append(f"The button text {settings.button} cannot carry over.")
    if settings.label_placement != "top_label":
        lost.append("The label placement cannot carry over; labels go above their fields.")
    return Conversion(model, lost)


# --------------------------------------------------------------------------- #
# QAF to Gravity Forms


def _condition(when: str, ids: Mapping[str, str]) -> Condition | None:
    try:
        tree = E.parse(when)
    except Exception:  # noqa: BLE001 - an unreadable rule is simply not carried
        return None
    action = "show"
    if tree.get("type") == "op" and tree.get("op") == "not":
        action, tree = "hide", tree["args"][0]
    if tree.get("type") != "op" or tree.get("op") not in ("is", "is_not"):
        return None
    left, right = tree["args"]
    if left.get("type") != "ref" or right.get("type") != "literal":
        return None
    target = ids.get(str(left.get("field")))
    if target is None:
        return None
    operator = "is" if tree["op"] == "is" else "isnot"
    return Condition(action, target, operator, str(right.get("value", "")))


def _values(item: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(item.get("type"))
    values: dict[str, Any] = {
        "label": str(item.get("label") or ""),
        "description": str(item.get("help") or ""),
        "isRequired": bool(item.get("required")),
        "placeholder": str(item.get("placeholder") or ""),
    }
    default = item.get("default")
    if isinstance(default, (str, int, float)) and not isinstance(default, bool):
        values["defaultValue"] = str(default)
    if kind in ("select", "radio", "checkbox", "multiselect"):
        values["choices"] = [
            {
                "text": str(c.get("label", "")),
                "value": str(c.get("value", "")),
                "isSelected": bool(c.get("selected")),
                "price": "",
            }
            for c in item.get("choices") or []
            if isinstance(c, dict)
        ]
    if kind == "consent":
        choices = item.get("choices") or []
        first = choices[0] if choices and isinstance(choices[0], dict) else {}
        values["checkboxLabel"] = str(first.get("label") or item.get("label") or "I agree.")
    if kind == "html":
        values["content"] = str((item.get("props") or {}).get("html", ""))
    return values


def _walk(entries: list[dict[str, Any]], out: list[dict[str, Any]], lost: list[str]) -> None:
    for item in entries:
        kind = str(item.get("type"))
        if kind == "section":
            out.append(item)
            _walk(item.get("items") or [], out, lost)
        elif kind == "columns":
            lost.append(
                "Columns become one column: Gravity Forms lays fields out one under another."
            )
            for column in item.get("columns") or []:
                _walk(column.get("items") or [], out, lost)
        else:
            out.append(item)


def to_gravity(model: Mapping[str, Any]) -> Conversion:
    """*model* (QAF) as a new Gravity Forms form."""
    lost: list[str] = []
    form = new_form(str(model.get("title") or "Untitled form"))
    form["description"] = str(model.get("description") or "")
    ids: dict[str, str] = {}
    built: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for number, page in enumerate(model.get("pages") or []):
        if number:
            made = add_field(form, "page", {"label": str(page.get("title") or "")})
            if page.get("when"):
                lost.append(f"Page {number + 1}: its rule cannot carry over.")
            ids[str(page.get("id"))] = str(made["id"])
        flat: list[dict[str, Any]] = []
        _walk(list(page.get("items") or []), flat, lost)
        for item in flat:
            kind = str(item.get("type"))
            if kind == "section":
                made = add_field(
                    form,
                    "section",
                    {
                        "label": str(item.get("label") or ""),
                        "description": str(item.get("help") or ""),
                    },
                )
            elif kind in SHARED:
                made = add_field(form, kind, _values(item))
            else:
                lost.append(
                    f"{item.get('label') or item.get('id')} is a "
                    f"{M.TYPE_NAMES.get(kind, kind)}, which QUILL does not build in Gravity Forms."
                )
                continue
            ids[str(item.get("id"))] = str(made["id"])
            built.append((item, made))
            for key in ("calculation", "smart_default", "mask", "validation", "scoring", "cascade"):
                if key in item:
                    lost.append(
                        f"{item.get('label') or item.get('id')}: its {key.replace('_', ' ')} "
                        "cannot carry over."
                    )
    for item, made in built:
        when = item.get("when")
        if not when:
            continue
        condition = _condition(str(when), ids)
        if condition is None:
            lost.append(
                f"{item.get('label') or item.get('id')}: its rule ({when}) is more than one "
                "field being a value, and cannot carry over."
            )
        else:
            set_condition(made, condition)
    for key, word in (
        ("rules", "rules"),
        ("scoring", "scoring"),
        ("translations", "translations"),
        ("choice_libraries", "choice libraries"),
    ):
        if model.get(key):
            lost.append(f"The form's {word} cannot carry over.")
    settings = settings_of(form)
    confirmations = [c for c in model.get("confirmations") or [] if isinstance(c, dict)]
    message = next((c for c in confirmations if c.get("type", "message") == "message"), None)
    if message is not None:
        settings = _with(settings, confirmation=str(message.get("message") or ""))
    if len(confirmations) > 1 or (confirmations and message is None):
        lost.append("Only one confirmation message carries over.")
    notes = [n for n in model.get("notifications") or [] if isinstance(n, dict)]
    if notes:
        first = notes[0]
        settings = _with(
            settings,
            notify_to=str(first.get("to") or settings.notify_to),
            notify_subject=str(first.get("subject") or settings.notify_subject),
        )
        if len(notes) > 1:
            lost.append("Only the first notification carries over.")
    apply_settings(form, settings)
    return Conversion(deepcopy(form), lost)


def _with(settings: Any, **changes: Any) -> Any:
    from dataclasses import replace

    return replace(settings, **changes)
