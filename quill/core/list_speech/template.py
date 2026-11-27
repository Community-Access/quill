"""The template model: a declarative description of how one list's rows are spoken.

A :class:`Template` is data, never code: the fields to say, in order, a
separator, whether each field is introduced by its spoken label, whether an
empty field is left out, and text to say for an empty field when it is not.

Validation never throws a person's choices away. A field the list type no
longer offers stays in the template (so it comes back if the API restores it)
and is *reported* by :func:`unavailable_fields` instead of being spoken as a
blank. Wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from quill.core.list_speech.catalog import ListType, Preset

__all__ = [
    "MAX_FALLBACK",
    "MAX_NAME",
    "MAX_SEPARATOR",
    "SEPARATOR_CHOICES",
    "Template",
    "from_preset",
    "move_field",
    "template_from_dict",
    "template_to_dict",
    "unavailable_fields",
]

MAX_NAME = 60
MAX_SEPARATOR = 12
MAX_FALLBACK = 40

#: The separators the editor offers by name; any short text is also accepted.
SEPARATOR_CHOICES: tuple[tuple[str, str], ...] = (
    (", ", "Comma"),
    ("; ", "Semicolon"),
    (" / ", "Slash"),
    (" - ", "Dash"),
    (". ", "Full stop"),
    (" ", "Space"),
)


@dataclass(frozen=True, slots=True)
class Template:
    """How one list type's rows are spoken."""

    list_type: str
    name: str
    fields: tuple[str, ...]
    separator: str = ", "
    labels: bool = False
    omit_empty: bool = True
    fallback: str = ""


def from_preset(list_type: ListType, preset: Preset) -> Template:
    """A built-in preset as a template (named for the preset, never saved by itself)."""
    return Template(list_type.id, preset.title, preset.fields, ", ", preset.labels, True, "")


def unavailable_fields(template: Template, list_type: ListType) -> tuple[str, ...]:
    """The template's fields the list type does not offer, in template order."""
    known = set(list_type.field_ids())
    return tuple(f for f in template.fields if f not in known)


def move_field(fields: Sequence[str], index: int, delta: int) -> tuple[tuple[str, ...], int]:
    """Move the field at *index* up (-1) or down (+1); returns the fields and its new index.

    Moving past either end changes nothing and returns the same index, so a
    caller can tell nothing moved.
    """
    target = index + delta
    if not (0 <= index < len(fields)) or not (0 <= target < len(fields)):
        return tuple(fields), index
    ordered = list(fields)
    ordered[index], ordered[target] = ordered[target], ordered[index]
    return tuple(ordered), target


def template_to_dict(template: Template) -> dict[str, Any]:
    return {
        "name": template.name,
        "list_type": template.list_type,
        "fields": list(template.fields),
        "separator": template.separator,
        "labels": template.labels,
        "omit_empty": template.omit_empty,
        "fallback": template.fallback,
    }


def _text(value: object, default: str, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else default


def _flag(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def template_from_dict(raw: Mapping[str, Any]) -> Template | None:
    """A template from stored data, coerced field by field; None when it has no name or type.

    A hand-edited value that is the wrong shape falls back to that field's
    default rather than losing the whole template.
    """
    name = _text(raw.get("name"), "", MAX_NAME).strip()
    list_type = _text(raw.get("list_type"), "", 80)
    if not name or not list_type:
        return None
    fields_raw = raw.get("fields")
    fields: list[str] = []
    if isinstance(fields_raw, list):
        for item in fields_raw:
            if isinstance(item, str) and item and item not in fields:
                fields.append(item)
    return Template(
        list_type=list_type,
        name=name,
        fields=tuple(fields),
        separator=_text(raw.get("separator"), ", ", MAX_SEPARATOR),
        labels=_flag(raw.get("labels"), False),
        omit_empty=_flag(raw.get("omit_empty"), True),
        fallback=_text(raw.get("fallback"), "", MAX_FALLBACK),
    )


def renamed(template: Template, name: str) -> Template:
    return replace(template, name=name.strip()[:MAX_NAME])
