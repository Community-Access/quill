"""Custom fields: the post meta a site registers for the REST API (wordpress.md 9.15).

A plugin or theme that registers meta with ``show_in_rest`` puts it in the
schema of the post type's route, under ``properties.meta.properties``. That
schema is read with an ``OPTIONS`` request and turned into the same labelled
fields Insert Block's forms use (:class:`~quill.core.wordpress.block_catalog.Field`),
so an SEO title, an event date or a subtitle is one more edit field in
Properties. Values a plain form cannot hold (lists and objects) are left as
the site has them and counted, never dropped.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.block_catalog import Field, assign_access_keys
from quill.core.wordpress.site import kind_route

#: Meta keys the block editor and core use for their own plumbing.
_PLUMBING = frozenset({"footnotes", "_wp_note_status"})

_SHORT = 80


@dataclass
class CustomFields:
    """The form for one item, and what the site had before it was shown."""

    fields: list[Field] = field(default_factory=list)
    #: Key -> value on the site now, for every field shown.
    site_values: dict[str, Any] = field(default_factory=dict)
    #: Key -> JSON type ("string", "integer", "number", "boolean").
    types: dict[str, str] = field(default_factory=dict)
    #: How many registered fields are lists or objects, left as they are.
    left_alone: int = 0


def meta_schema(api: WordPressApi, kind: str) -> dict[str, Any]:
    """``properties.meta.properties`` of the kind's route schema, or ``{}``."""
    payload = api.request("OPTIONS", kind_route(kind)).payload
    schema = payload.get("schema") if isinstance(payload, dict) else None
    props = schema.get("properties") if isinstance(schema, dict) else None
    meta = props.get("meta") if isinstance(props, dict) else None
    found = meta.get("properties") if isinstance(meta, dict) else None
    return dict(found) if isinstance(found, dict) else {}


def site_values(api: WordPressApi, kind: str, item_id: int) -> dict[str, Any]:
    if not item_id:
        return {}
    raw = api.get(f"{kind_route(kind)}/{item_id}", context="edit", _fields="meta")
    meta = raw.get("meta") if isinstance(raw, dict) else None
    return dict(meta) if isinstance(meta, dict) else {}


def label_for(key: str, schema: Mapping[str, Any]) -> str:
    title = str(schema.get("title", "") or "").strip()
    if title:
        return title
    words = key.lstrip("_").replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:] if words else key


def help_for(key: str, schema: Mapping[str, Any]) -> str:
    description = str(schema.get("description", "") or "").strip()
    base = description or "A custom field this site registers"
    return (
        f"{base.rstrip('.')}. Saved as {key} and sent with your next Save Draft to Site or Publish."
    )


def build_form(
    schema: Mapping[str, Any], values: Mapping[str, Any], kept: Mapping[str, Any]
) -> CustomFields:
    """The fields to show: the site's value, or the one kept with the copy if changed."""
    out = CustomFields()
    for key, spec in schema.items():
        if key in _PLUMBING or not isinstance(spec, dict):
            continue
        kind = spec.get("type")
        if isinstance(kind, list):
            kind = next((k for k in kind if k != "null"), "")
        if kind in ("array", "object") or kind not in ("string", "integer", "number", "boolean"):
            out.left_alone += 1
            continue
        current = kept.get(key, values.get(key, spec.get("default")))
        out.site_values[key] = values.get(key, spec.get("default"))
        out.types[key] = str(kind)
        label = label_for(key, spec)
        help_text = help_for(key, spec)
        enum = spec.get("enum")
        if isinstance(enum, list) and enum:
            f = Field(key, label + ":", "choice", help_text, current)
            f.choices, f.values = [str(v) for v in enum], list(enum)
        elif kind == "boolean":
            f = Field(key, label, "check", help_text, bool(current))
        else:
            text = "" if current is None else str(current)
            long = kind == "string" and (len(text) > _SHORT or "\n" in text)
            f = Field(key, label + ":", "multiline" if long else "text", help_text, text)
        out.fields.append(f)
    for f, label in zip(out.fields, assign_access_keys([f.label for f in out.fields]), strict=True):
        f.label = label
    return out


class FieldValueError(CodedError):
    """A number field that does not hold a number (never raised past the command)."""

    code = "QUILL-WP-FIELDS-NOT-A-NUMBER"

    def __init__(self, field_label: str) -> None:
        super().__init__(field_label)
        self.field_label = field_label


def changes(form: CustomFields, answers: Mapping[str, Any]) -> dict[str, Any]:
    """The fields whose answer differs from the site's value, typed for the site.

    Raises :class:`FieldValueError` naming the field when a number field holds
    something that is not a number.
    """
    out: dict[str, Any] = {}
    labels = {f.key: f.label.replace("&", "").rstrip(":") for f in form.fields}
    for key, answer in answers.items():
        kind = form.types.get(key, "string")
        value: Any = answer
        if kind in ("integer", "number") and not isinstance(answer, (int, float)):
            text = str(answer).strip()
            if not text:
                value = None
            else:
                try:
                    value = int(text) if kind == "integer" else float(text)
                except ValueError as exc:
                    raise FieldValueError(labels.get(key, key)) from exc
        before = form.site_values.get(key)
        if value == before or (value in ("", None) and before in ("", None)):
            continue
        out[key] = "" if value is None and kind == "string" else value
    return out
