"""Saving a Gravity Forms form QUILL built or edited (complete.md 10B.3, WP-C).

Every write is Gravity Forms REST API v2, and every one sends the whole form,
because ``PUT gf/v2/forms/{id}`` replaces the form rather than merging it:

- **New:** ``POST gf/v2/forms`` with the form; the reply is the stored form (or,
  on older versions, its id), which is read back with ``GET gf/v2/forms/{id}``.
- **Edit:** the form is read again just before the ``PUT`` and compared with
  the copy read when the editor opened; if anyone changed it meanwhile, nothing
  is sent (:class:`FormChanged`). After the ``PUT`` it is read back and
  :func:`readback_problems` says any way the site kept something else.
- **Undo** puts the previous form back, the same way and with the same check
  against what the save left; undoing a new form moves it to Gravity Forms'
  Trash (``DELETE gf/v2/forms/{id}`` without ``force``), which keeps it.

Entries are never read or written here: a form's entries live under
``gf/v2/entries`` and no call in this module goes there. :data:`ENTRIES_LINE`
is the sentence every preview carries to say so. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.gravity_build import (
    FIELD_TYPES,
    admin_notification,
    default_confirmation,
    field_name,
    fields_of,
    settings_of,
)
from quill.core.wordpress.workbench_forms import GRAVITY_NAMESPACE

__all__ = [
    "ENTRIES_LINE",
    "FormChanged",
    "Saved",
    "change_lines",
    "create",
    "form_route",
    "put_back",
    "readback_problems",
    "trash",
    "update",
]

ENTRIES_LINE = "Entries are never read, changed or deleted: only the form itself is sent."


class FormChanged(WordPressApiError):
    """The form on the site is not the one the editor opened; nothing was sent."""

    code = "QUILL-WORDPRESS-GRAVITY-FORM-CHANGED"


def form_route(form_id: Any) -> str:
    return f"{GRAVITY_NAMESPACE}/forms/{form_id}"


@dataclass(frozen=True, slots=True)
class Saved:
    """What the site kept, its id and route, and any way it differs from what was sent."""

    form_id: str
    route: str
    stored: dict[str, Any]
    problems: tuple[str, ...]


# --------------------------------------------------------------------------- #
# what a save will change, as lines for the preview


def _by_id(form: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(f.get("id", "")): f for f in fields_of(form)}


def _field_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    names = {
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
        "conditionalLogic": "conditional logic",
        "type": "type",
        "inputs": "sub-fields",
    }
    keys = set(before) | set(after)
    return [
        word
        for key, word in names.items()
        if key in keys and before.get(key) != after.get(key) and (before.get(key) or after.get(key))
    ] + sorted(
        f"{key} (kept from the site)"
        for key in keys
        if key not in names
        and key not in ("enableChoiceValue",)
        and before.get(key) != after.get(key)
    )


def change_lines(before: Mapping[str, Any] | None, after: Mapping[str, Any]) -> list[str]:
    """One line for each thing a save changes; *before* is None for a new form."""
    lines: list[str] = []
    new = before is None
    old = before or {}
    a, b = settings_of(dict(old)), settings_of(dict(after))
    if new:
        lines.append(f"New form: {b.title or 'Untitled'}.")
    for word, x, y in (
        ("Title", a.title, b.title),
        ("Description", a.description, b.description),
        ("Button text", a.button, b.button),
        ("Label placement", a.label_placement, b.label_placement),
        ("Confirmation message", a.confirmation, b.confirmation),
        ("Admin notification To", a.notify_to, b.notify_to),
        ("Admin notification subject", a.notify_subject, b.notify_subject),
    ):
        if not new and x != y:
            lines.append(f"{word}: {y or 'empty'} (was {x or 'empty'}).")
    old_fields, new_fields = _by_id(old), _by_id(after)
    for number, field in enumerate(fields_of(after), 1):
        key = str(field.get("id", ""))
        kind = FIELD_TYPES.get(str(field.get("type")), str(field.get("type")))
        if key not in old_fields:
            lines.append(f"Add field {number}: {field_name(field)}, {kind}.")
            continue
        changed = _field_changes(old_fields[key], field)
        if changed:
            lines.append(f"Change {field_name(field)}: {', '.join(changed)}.")
    for key, field in old_fields.items():
        if key not in new_fields:
            lines.append(
                f"Remove {field_name(field)}. Answers already given to it stay in the entries."
            )
    kept_old = [k for k in _by_id(old) if k in new_fields]
    kept_new = [k for k in new_fields if k in old_fields]
    if kept_old != kept_new:
        lines.append("Fields move: " + ", ".join(field_name(new_fields[k]) for k in kept_new) + ".")
    if not new and len(lines) == 0:
        lines.append("Nothing changes.")
    lines.append(ENTRIES_LINE)
    return lines


def readback_problems(sent: Mapping[str, Any], stored: Any) -> list[str]:
    """How the form read back differs from what was sent, in what QUILL edits."""
    if not isinstance(stored, dict):
        return ["Gravity Forms did not send the form back to check."]
    problems = []
    if str(stored.get("title", "")) != str(sent.get("title", "")):
        problems.append(f"The title reads back as {stored.get('title')!r}.")
    kept = _by_id(stored)
    for field in fields_of(sent):
        key = str(field.get("id", ""))
        back = kept.get(key)
        if back is None:
            problems.append(f"{field_name(field)} is missing.")
            continue
        for prop in ("type", "label"):
            if str(back.get(prop, "")) != str(field.get(prop, "")):
                problems.append(f"{field_name(field)}'s {prop} reads back as {back.get(prop)!r}.")
        if bool(back.get("isRequired")) != bool(field.get("isRequired")):
            problems.append(f"{field_name(field)}'s required setting reads back differently.")
        if isinstance(field.get("choices"), list):
            sent_texts = [c.get("text") for c in field["choices"] if isinstance(c, dict)]
            raw_choices = back.get("choices")
            back_choices: list[Any] = raw_choices if isinstance(raw_choices, list) else []
            if sent_texts != [c.get("text") for c in back_choices if isinstance(c, dict)]:
                problems.append(f"{field_name(field)}'s choices read back differently.")
    sent_ids, back_ids = list(_by_id(sent)), list(kept)
    if [k for k in back_ids if k in sent_ids] != [k for k in sent_ids if k in back_ids]:
        problems.append("The fields read back in another order.")
    extra = [k for k in back_ids if k not in sent_ids]
    if extra:
        problems.append(f"The site has fields QUILL did not send: {', '.join(extra)}.")
    for name, find in (
        ("confirmation", default_confirmation),
        ("notification", admin_notification),
    ):
        mine, theirs = find(dict(sent)), find(stored)
        if (
            mine
            and theirs
            and mine.get("message" if name == "confirmation" else "subject")
            != (theirs.get("message" if name == "confirmation" else "subject"))
        ):
            problems.append(f"The {name} reads back differently.")
    return problems


# --------------------------------------------------------------------------- #
# the writes


def _payload(answer: Any) -> Any:
    return getattr(answer, "payload", answer)


def create(api: Any, form: Mapping[str, Any]) -> Saved:
    """POST a new form, then read it back."""
    answer = _payload(api.request("POST", f"{GRAVITY_NAMESPACE}/forms", json_body=dict(form)))
    if isinstance(answer, dict):
        form_id = str(answer.get("id", ""))
    else:
        form_id = str(answer or "")
    if not form_id:
        raise WordPressApiError("Gravity Forms did not say which form it made.")
    route = form_route(form_id)
    stored = api.get(route)
    sent = {**form, "id": form_id}
    return Saved(
        form_id,
        route,
        stored if isinstance(stored, dict) else {},
        tuple(readback_problems(sent, stored)),
    )


def update(api: Any, route: str, opened: Mapping[str, Any], edited: Mapping[str, Any]) -> Saved:
    """PUT *edited*, after checking the site still has *opened*; then read it back."""
    current = api.get(route)
    if not isinstance(current, dict) or current != opened:
        raise FormChanged(
            f"{opened.get('title') or 'The form'} changed on the site since you opened it. "
            "Nothing was sent; open it again to see the newer form."
        )
    api.request("PUT", route, json_body=dict(edited))
    stored = api.get(route)
    form_id = str(edited.get("id") or route.rsplit("/", 1)[-1])
    return Saved(
        form_id,
        route,
        stored if isinstance(stored, dict) else {},
        tuple(readback_problems(edited, stored)),
    )


def put_back(api: Any, route: str, expected: Mapping[str, Any], body: Mapping[str, Any]) -> Any:
    """Undo or redo: replace the form with *body* if it is still *expected*."""
    current = api.get(route)
    if not isinstance(current, dict) or current != expected:
        raise FormChanged(
            f"{expected.get('title') or 'The form'} changed on the site since. "
            "QUILL did not replace the newer form."
        )
    api.request("PUT", route, json_body=dict(body))
    return api.get(route)


def trash(api: Any, route: str) -> None:
    """Move a form to Gravity Forms' Trash (no ``force``), where it can be restored."""
    api.request("DELETE", route)
