"""A Gravity Form's other notifications and confirmations (complete.md 2.3, Forms).

QUILL's form editor changes the default confirmation and the Admin
Notification. A form that sends a different email by answer, or thanks people
differently, has more of each, and those were kept untouched with no way to
see or change them. This module lists, adds, changes, removes and turns on or
off **the others**: every notification but the Admin Notification and every
confirmation but the default, so the editor's own boxes and this list never
change the same record.

A notification or confirmation with routing or conditional logic is listed and
can be turned on or off or removed, and its other keys are always kept; its
routing and logic are changed in Gravity Forms, which this says. Every edit
works on the form dict the editor holds; the Workbench previews and saves the
whole form as before. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from quill.core.wordpress.gravity_build import (
    Form,
    _new_id,
    admin_notification,
    default_confirmation,
)

__all__ = [
    "Message",
    "add_confirmation",
    "add_notification",
    "change",
    "others",
    "remove",
    "spoken",
    "toggle",
]

Kind = Literal["notifications", "confirmations"]


@dataclass(frozen=True, slots=True)
class Message:
    """One notification or confirmation, by where it lives in the form."""

    kind: Kind
    id: str
    record: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.record.get("name") or "Unnamed")

    @property
    def simple(self) -> bool:
        """No routing and no conditional logic: QUILL can change all of it."""
        record = self.record
        if record.get("conditionalLogic") or record.get("routing"):
            return False
        if self.kind == "notifications":
            return str(record.get("toType") or "email") == "email"
        return str(record.get("type") or "message") == "message"


def _store(form: Form, kind: Kind) -> dict[str, Any]:
    """The form's records of *kind*, as Gravity Forms keeps them: by id."""
    found = form.get(kind)
    if isinstance(found, list):  # an older export keeps a list; store it by id
        found = {str(r.get("id") or _new_id()): r for r in found if isinstance(r, dict)}
        form[kind] = found
    if not isinstance(found, dict):
        found = form[kind] = {}
    return found


def others(form: Form) -> list[Message]:
    """Every notification but the Admin Notification, then every confirmation but the default."""
    skip = {id(admin_notification(form)), id(default_confirmation(form))}
    found: list[Message] = []
    for kind in ("notifications", "confirmations"):
        for key, record in _store(form, kind).items():  # type: ignore[arg-type]
            if isinstance(record, dict) and id(record) not in skip:
                found.append(Message(kind, str(record.get("id") or key), record))  # type: ignore[arg-type]
    return found


def spoken(message: Message) -> str:
    """ "Ticket email, notification, to {field:3}, on" -- what the list says."""
    record = message.record
    if message.kind == "notifications":
        to = str(record.get("to") or "nobody")
        state = "on" if record.get("isActive", True) not in (False, 0, "0") else "off"
        where = f"to {to}" if message.simple else "routed in Gravity Forms"
        return f"{message.name}, notification, {where}, {state}"
    state = "on" if record.get("isActive", True) not in (False, 0, "0") else "off"
    shows = "a message" if message.simple else "a page or address, or by logic"
    return f"{message.name}, confirmation, shows {shows}, {state}"


def add_notification(form: Form, name: str, to: str, subject: str, body: str) -> Message:
    new_id = _new_id()
    record = {
        "id": new_id,
        "name": name,
        "isActive": True,
        "event": "form_submission",
        "toType": "email",
        "to": to,
        "subject": subject,
        "message": body or "{all_fields}",
    }
    _store(form, "notifications")[new_id] = record
    return Message("notifications", new_id, record)


def add_confirmation(form: Form, name: str, body: str) -> Message:
    new_id = _new_id()
    record = {
        "id": new_id,
        "name": name,
        "isDefault": False,
        "isActive": True,
        "type": "message",
        "message": body,
        "url": "",
        "pageId": "",
        "queryString": "",
    }
    _store(form, "confirmations")[new_id] = record
    return Message("confirmations", new_id, record)


def change(message: Message, values: Mapping[str, str]) -> list[str]:
    """Set *values* (name, to, subject, message) on a simple record; what changed, in words."""
    said = []
    allowed = (
        ("name", "to", "subject", "message")
        if message.kind == "notifications"
        else (
            "name",
            "message",
        )
    )
    for key in allowed:
        if key in values and str(message.record.get(key) or "") != values[key]:
            message.record[key] = values[key]
            said.append(key)
    return said


def toggle(message: Message) -> bool:
    """Turn it on or off; True when it is on now."""
    on = message.record.get("isActive", True) in (False, 0, "0")
    message.record["isActive"] = on
    return on


def remove(form: Form, message: Message) -> None:
    store = _store(form, message.kind)
    for key, record in list(store.items()):
        if record is message.record:
            del store[key]
