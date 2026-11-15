"""Change a Gravity Forms response's answers from its Properties (wp_missing.md, Forms).

An entry's answers are its keys that start with a digit -- a field's id
(``"1"``), or a part of one (``"1.3"``, a name's first part; ``"4.2"``, the
second check box). Gravity Forms' ``PUT gf/v2/entries/{id}`` replaces the
whole entry, so a change is always sent as the entry read just before, with
only the changed answers replaced (as :func:`quill.core.wordpress.workbench_gravity.set_entry_flag`
does for Starred and Read). Before that write:

- the entry's ``date_updated`` must be the one the sheet loaded, and each
  answer being changed must still say what the sheet showed; otherwise
  somebody changed the response meanwhile and nothing is sent;
- the answers it had are returned, so Ctrl+Z can send them back the same
  way (checked against what this change wrote).

Wx-free; runs off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_edit import EditConflict

__all__ = [
    "ANSWER_KEY",
    "answer_ids",
    "answer_key",
    "answer_labels",
    "field_of",
    "set_answers",
]

ANSWER_KEY = "answer:"
"""The prefix of an answer's key on the Properties sheet (``answer:1.3``)."""

_ID = re.compile(r"^\d+(\.\d+)?$")


def answer_key(field_id: str) -> str:
    return f"{ANSWER_KEY}{field_id}"


def field_of(key: str) -> str:
    """The entry key a sheet key stands for ("" when it is not an answer)."""
    return key.removeprefix(ANSWER_KEY) if key.startswith(ANSWER_KEY) else ""


def _order(field_id: str) -> tuple[int, ...]:
    return tuple(int(n) for n in field_id.split("."))


def answer_ids(entry: Mapping[str, Any]) -> list[str]:
    """The entry's answer keys, in field order (1, 1.3, 2, 10)."""
    return sorted((k for k in entry if _ID.match(str(k))), key=_order)


def answer_labels(form: Mapping[str, Any]) -> dict[str, str]:
    """Each field's and field part's label, from the form (``1.3``: "Name, First")."""
    labels: dict[str, str] = {}
    for field in form.get("fields") or []:
        if not isinstance(field, Mapping):
            continue
        ident = str(field.get("id", ""))
        label = str(field.get("adminLabel") or field.get("label") or f"Field {ident}")
        labels[ident] = label
        for part in field.get("inputs") or []:
            if isinstance(part, Mapping) and part.get("id") is not None:
                words = str(part.get("customLabel") or part.get("label") or "")
                labels[str(part["id"])] = f"{label}, {words}" if words else label
    return labels


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def set_answers(
    api: Any,
    route: str,
    *,
    seen: Mapping[str, str],
    changed: Mapping[str, str],
    seen_updated: str = "",
) -> dict[str, str]:
    """Send the whole entry with *changed* answers; returns what those answers were.

    *seen* is what the sheet showed for each changed answer, and *seen_updated*
    the entry's ``date_updated`` when it loaded ("" skips that check, as the
    undo does). Either differing from the site means a conflict, and nothing
    is sent.
    """
    if not changed:
        return {}
    unknown = [key for key in changed if not _ID.match(key)]
    if unknown:
        raise ValueError(f"{unknown[0]} is not an answer of this entry.")
    current = api.get(route)
    if not isinstance(current, dict) or not current.get("id"):
        raise WordPressApiError("Gravity Forms did not return this entry, so nothing was changed.")
    updated = _text(current.get("date_updated"))
    moved = [key for key in changed if _text(current.get(key)) != _text(seen.get(key))]
    if (seen_updated and updated and updated != seen_updated) or moved:
        raise EditConflict(
            "This response was changed in Gravity Forms after QUILL read it. Nothing was sent; "
            "open its Properties again and make the change there."
        )
    before = {key: _text(current.get(key)) for key in changed}
    api.request("PUT", route, json_body={**current, **dict(changed)})
    return before
