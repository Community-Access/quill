"""Accessibility checks on a Gravity Forms form before QUILL saves it (WP-C).

The same questions QUILL's own Check This Form asks of a QUILL Accessible
Forms form (``quill/ui/forms_check.py``, wordpress.md 17a.5), asked of a
Gravity Forms form object: is every question labelled, is a required field
marked so a screen reader says so, does every choice field have choices, do
the page breaks and sections make sense when walked in order, and would two
questions sound the same to a listener. The editor also runs QUILL's shared
QAF checks over the form converted by :mod:`quill.core.wordpress.gravity_qaf`
and adds what they find.

Each finding is one sentence and the id of the field it is about, so the
editor can put focus on it. Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.gravity_build import (
    CHOICE_TYPES,
    DISPLAY_TYPES,
    Condition,
    condition_of,
    field_name,
    fields_of,
)

__all__ = ["Finding", "check_form"]

#: Fields whose label a visitor never hears, so it may be empty.
_NO_LABEL_NEEDED = DISPLAY_TYPES | {"hidden", "captcha", "page"}
_ASTERISK = re.compile(r"\*\s*$|^\s*\*|\(required\)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Finding:
    text: str
    field_id: str | None = None


def _labels(field: Mapping[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    fid = str(field.get("id", ""))
    kind = str(field.get("type", ""))
    label = str(field.get("label") or "").strip()
    if not label and kind not in _NO_LABEL_NEEDED:
        if str(field.get("placeholder") or "").strip():
            out.append(
                Finding(
                    f"Field {fid} has only a placeholder for a label. A placeholder disappears "
                    "as soon as somebody types; give it a label.",
                    fid,
                )
            )
        else:
            out.append(Finding(f"Field {fid} ({kind}) has no label. Give it one.", fid))
    if label and _ASTERISK.search(label) and not field.get("isRequired"):
        out.append(
            Finding(
                f"{label} marks itself required only with an asterisk or a word. Turn on "
                "Required instead, so a screen reader says so.",
                fid,
            )
        )
    for sub in field.get("inputs") or []:
        if isinstance(sub, dict) and not sub.get("isHidden") and not str(sub.get("label") or ""):
            if kind == "checkbox":
                continue  # a check box's label is its choice, checked below
            out.append(Finding(f"{field_name(field)} has a part with no label.", fid))
    if kind == "consent" and not str(field.get("checkboxLabel") or "").strip():
        out.append(Finding(f"{field_name(field)} has no text beside its check box.", fid))
    return out


def _choices(field: Mapping[str, Any]) -> list[Finding]:
    fid = str(field.get("id", ""))
    if str(field.get("type", "")) not in CHOICE_TYPES:
        return []
    choices = [c for c in field.get("choices") or [] if isinstance(c, dict)]
    if not choices:
        return [Finding(f"{field_name(field)} has no choices. Add some, one a line.", fid)]
    out = []
    if any(not str(c.get("text") or "").strip() for c in choices):
        out.append(Finding(f"{field_name(field)} has a choice with no words.", fid))
    texts = [str(c.get("text") or "").strip().lower() for c in choices]
    if len(set(texts)) != len(texts):
        out.append(Finding(f"{field_name(field)} offers the same choice twice.", fid))
    if field.get("type") == "radio" and sum(1 for c in choices if c.get("isSelected")) > 1:
        out.append(Finding(f"{field_name(field)} starts with more than one choice chosen.", fid))
    return out


def _structure(fields: list[dict[str, Any]]) -> list[Finding]:
    out: list[Finding] = []
    kinds = [str(f.get("type", "")) for f in fields]
    if kinds and kinds[0] == "page":
        out.append(
            Finding(
                "The form starts with a page break, so its first page is empty.",
                str(fields[0].get("id")),
            )
        )
    if kinds and kinds[-1] == "page":
        out.append(
            Finding(
                "The form ends with a page break, so its last page is empty.",
                str(fields[-1].get("id")),
            )
        )
    for index in range(1, len(kinds)):
        if kinds[index] == "page" and kinds[index - 1] == "page":
            out.append(
                Finding(
                    "Two page breaks in a row leave a page with nothing on it.",
                    str(fields[index].get("id")),
                )
            )
        if kinds[index - 1] == "section" and kinds[index] in ("section", "page"):
            out.append(
                Finding(
                    f"Section {field_name(fields[index - 1])} has nothing in it.",
                    str(fields[index - 1].get("id")),
                )
            )
    if kinds and kinds[-1] == "section":
        out.append(
            Finding(
                f"Section {field_name(fields[-1])} has nothing in it.", str(fields[-1].get("id"))
            )
        )
    asking = [k for k in kinds if k not in DISPLAY_TYPES]
    if fields and not asking:
        out.append(Finding("The form asks nothing: every field only shows text or structure."))
    return out


def _sounds_alike(fields: list[dict[str, Any]]) -> list[Finding]:
    """Two questions with the same label, in the same part of the form, sound alike."""
    out: list[Finding] = []
    seen: dict[tuple[int, str], str] = {}
    part = 0
    for field in fields:
        kind = str(field.get("type", ""))
        if kind in ("page", "section"):
            part += 1
            continue
        label = re.sub(r"\s+", " ", str(field.get("label") or "")).strip().lower()
        if not label or kind in DISPLAY_TYPES:
            continue
        key = (part, label)
        if key in seen:
            out.append(
                Finding(
                    f"Two questions are both called {field.get('label')}: fields {seen[key]} and "
                    f"{field.get('id')}. A listener cannot tell them apart; make one label "
                    "different, or put them under different sections.",
                    str(field.get("id")),
                )
            )
        else:
            seen[key] = str(field.get("id"))
    return out


def _logic(fields: list[dict[str, Any]]) -> list[Finding]:
    out: list[Finding] = []
    position = {str(f.get("id")): i for i, f in enumerate(fields)}
    for index, field in enumerate(fields):
        condition = condition_of(field)
        if not isinstance(condition, Condition):
            continue
        fid = str(field.get("id"))
        if condition.field_id == fid:
            out.append(Finding(f"{field_name(field)} shows or hides on its own answer.", fid))
        elif condition.field_id not in position:
            out.append(
                Finding(
                    f"{field_name(field)} depends on field {condition.field_id}, which is not in "
                    "this form.",
                    fid,
                )
            )
        elif position[condition.field_id] > index:
            out.append(
                Finding(
                    f"{field_name(field)} depends on a question asked after it, so it changes "
                    "behind the person filling it in.",
                    fid,
                )
            )
        if (
            field.get("isRequired")
            and condition.action == "show"
            and condition.field_id not in position
        ):
            out.append(Finding(f"{field_name(field)} is required but can never show.", fid))
    return out


def check_form(form: Mapping[str, Any]) -> list[Finding]:
    """Every finding for *form*, the form's own first, then field by field."""
    out: list[Finding] = []
    if not str(form.get("title") or "").strip():
        out.append(Finding("The form has no title. Give it one; it names the form everywhere."))
    raw_button = form.get("button")
    button: dict[str, Any] = raw_button if isinstance(raw_button, dict) else {}
    if button.get("type", "text") == "text" and not str(button.get("text") or "").strip():
        out.append(Finding("The submit button has no text, so it would be read as just button."))
    if (
        str(form.get("requiredIndicator") or "") == "custom"
        and not str(form.get("customRequiredIndicator") or "").strip()
    ):
        if any(f.get("isRequired") for f in fields_of(form)):
            out.append(Finding("Required fields are marked with nothing. Choose a marker."))
    fields = fields_of(form)
    out += _structure(fields)
    for field in fields:
        out += _labels(field)
        out += _choices(field)
    out += _sounds_alike(fields)
    out += _logic(fields)
    return out
