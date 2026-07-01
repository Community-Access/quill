"""Per-kind field schema for the element details form (wx-free).

Each element kind offers a small set of *optional* structured fields (a
character's goal, a plot thread's status). The form shows these, plus any
unknown keys already in the file (preserved verbatim), plus a universal
``tags`` list. Nothing is required: an empty field is simply dropped, so files
stay clean and never accumulate ``goal: ""`` clutter. The ``type`` key is
preserved but not shown (it records the element kind).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.story.model import ElementKind

__all__ = ["FieldSpec", "FieldRow", "DEFAULT_FIELDS", "build_rows", "collect_fields"]

_TAGS_KEY = "tags"
_TYPE_KEY = "type"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """A known field for a kind: its stored key and human label."""

    key: str
    label: str


@dataclass(frozen=True, slots=True)
class FieldRow:
    """One row shown in the details form."""

    key: str
    label: str
    value: str
    is_list: bool


DEFAULT_FIELDS: dict[ElementKind, tuple[FieldSpec, ...]] = {
    ElementKind.CHARACTER: (
        FieldSpec("role", "Role"),
        FieldSpec("goal", "Goal"),
        FieldSpec("motivation", "Motivation"),
        FieldSpec("arc", "Arc"),
    ),
    ElementKind.LOCATION: (FieldSpec("significance", "Significance"),),
    ElementKind.PLOT: (FieldSpec("status", "Status"),),
    ElementKind.RESEARCH: (FieldSpec("source", "Source"),),
    ElementKind.BRAINSTORM: (),
}


def build_rows(kind: ElementKind, stored: Mapping[str, Any]) -> list[FieldRow]:
    """Rows for the form: schema fields, then unknown stored keys, then tags."""
    specs = DEFAULT_FIELDS.get(kind, ())
    schema_keys = {spec.key for spec in specs}
    rows = [
        FieldRow(spec.key, spec.label, _as_text(stored.get(spec.key, "")), is_list=False)
        for spec in specs
    ]
    for key, value in stored.items():
        if key in schema_keys or key in (_TAGS_KEY, _TYPE_KEY):
            continue
        rows.append(FieldRow(str(key), str(key), _as_text(value), is_list=False))
    rows.append(FieldRow(_TAGS_KEY, "Tags", _as_csv(stored.get(_TAGS_KEY, [])), is_list=True))
    return rows


def collect_fields(
    kind: ElementKind, stored: Mapping[str, Any], edits: Mapping[str, str]
) -> dict[str, Any]:
    """Merge form ``edits`` back into a fields dict, dropping now-empty values.

    ``type`` and any unknown keys are preserved; ``tags`` is split on commas.
    A field the user cleared is omitted so the file does not keep empty keys.
    """
    result: dict[str, Any] = {}
    if _TYPE_KEY in stored:
        result[_TYPE_KEY] = stored[_TYPE_KEY]
    for row in build_rows(kind, stored):
        if row.key == _TAGS_KEY:
            continue
        value = edits.get(row.key, row.value).strip()
        if value:
            result[row.key] = value
    raw_tags = edits.get(_TAGS_KEY, _as_csv(stored.get(_TAGS_KEY, [])))
    tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    if tags:
        result[_TAGS_KEY] = tags
    return result


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def _as_csv(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return _as_text(value)
