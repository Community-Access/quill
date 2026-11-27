"""The one call a list makes: "how should this row be spoken?"

``speak_row`` returns the row spoken under the template the person assigned to
that kind of list, or **None** -- which means "use the existing wording". With
no template assigned (the default) it always returns None, so nothing changes
until a person opts in. A template that cannot say anything for a row (every
field empty or unavailable) also returns None rather than a silent row.

``has_template`` lets a list decide cheaply whether to switch to its single
spoken column at all. Wx-free.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from quill.core.list_speech.catalog import get_list_type
from quill.core.list_speech.library import Library, resolve
from quill.core.list_speech.render import Rendered, render_row
from quill.core.list_speech.row_fields import (
    explore_row_fields,
    github_item_fields,
    wordpress_row_fields,
)
from quill.core.list_speech.store import load_cached

__all__ = ["SPEECH_COLUMN", "fields_for_row", "has_template", "speak_row"]

#: The one column a list shows while a template is speaking its rows.
SPEECH_COLUMN = "row"


def fields_for_row(row: Any, today: date | None = None) -> tuple[str, dict[str, str]] | None:
    """(list type id, field values) for a row a template can speak, else None."""
    if hasattr(row, "is_pr") and hasattr(row, "number"):
        return github_item_fields(row, today)
    if hasattr(row, "cells") and hasattr(row, "subkind"):
        return wordpress_row_fields(row)
    return explore_row_fields(row)


def has_template(list_type: str, library: Library | None = None) -> bool:
    """True when the person assigned a template to this list type."""
    return resolve(library or load_cached(), list_type).template is not None


def speak_row(row: Any, library: Library | None = None, today: date | None = None) -> str | None:
    """The row as its template speaks it, or None to use the existing wording."""
    found = fields_for_row(row, today)
    if found is None:
        return None
    list_type_id, values = found
    list_type = get_list_type(list_type_id)
    if list_type is None:
        return None
    template = resolve(library or load_cached(), list_type_id).template
    if template is None:
        return None
    rendered: Rendered = render_row(template, list_type, values)
    return rendered.text or None
