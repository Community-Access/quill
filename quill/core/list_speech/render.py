"""Turn a row's data and a template into the sentence a screen reader speaks.

Pure and wx-free. The row is a mapping of field id to its value as text; the
extractors in :mod:`quill.core.list_speech.row_fields` build it from a model.

Rules, in order, for each field in the template:

1. A field the list type does not offer (the API dropped it) is **unavailable**:
   skipped and reported, never spoken as a blank.
2. A field the list type offers but this row does not carry is **missing**:
   skipped and reported the same way.
3. An empty value is left out when *omit_empty* is on; otherwise the
   template's *fallback* text is spoken in its place, and when there is no
   fallback it is left out anyway, because a bare label with nothing after it
   is the blank placeholder this system exists to avoid.
4. A field with a spoken label is introduced by it when labels are on.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.list_speech.catalog import ListType
from quill.core.list_speech.template import Template

__all__ = ["Rendered", "render_row"]


@dataclass(frozen=True, slots=True)
class Rendered:
    """The spoken row, and what was left out of it and why."""

    text: str
    spoken: tuple[str, ...] = ()
    unavailable: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    empty: tuple[str, ...] = ()


def render_row(template: Template, list_type: ListType, row: Mapping[str, str]) -> Rendered:
    """The row spoken under *template*. ``text`` is empty when nothing could be said."""
    parts: list[str] = []
    spoken: list[str] = []
    unavailable: list[str] = []
    missing: list[str] = []
    empty: list[str] = []
    for field_id in template.fields:
        definition = list_type.field(field_id)
        if definition is None:
            unavailable.append(field_id)
            continue
        if field_id not in row:
            missing.append(field_id)
            continue
        value = str(row[field_id]).strip()
        if not value:
            empty.append(field_id)
            if template.omit_empty or not template.fallback:
                continue
            value = template.fallback
        if template.labels and definition.spoken_label:
            value = f"{definition.spoken_label} {value}"
        parts.append(value)
        spoken.append(field_id)
    return Rendered(
        text=template.separator.join(parts),
        spoken=tuple(spoken),
        unavailable=tuple(unavailable),
        missing=tuple(missing),
        empty=tuple(empty),
    )
