"""Custom fields that are lists or groups: read, edited and sent back whole (WP-R-033).

A registered meta key whose schema ``type`` is ``array`` is a list (speakers,
a gallery's picture ids, a repeater's rows); ``object`` is a group of named
fields (an address, a venue). WordPress stores and returns them as JSON, and
takes them back the same way, replacing the whole value.

Three promises, which the tests hold:

- **Nothing is lost.** A group keeps every key it came with, including ones
  its schema does not name (``additionalProperties``), and a list keeps
  every item, including ones QUILL cannot edit (a list inside a list).
- **Types are the site's.** What a person types is turned into the schema's
  type (an integer, a number, true or false) before it goes back, and a
  value that cannot be is a :class:`~quill.core.wordpress.custom_fields.FieldValueError`
  naming the field, never a quiet zero.
- **Said, not shown.** Every list and group has a sentence for its row
  (``Speakers, a list of 3: Ann, Bo, Cy``), and every item a sentence for
  its row, so a list reads well in a list box.

List edits (add, remove, move up, move down) are pure functions over a list,
so the dialog above them holds no logic of its own.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.block_catalog import Field, assign_access_keys

__all__ = [
    "SCALARS",
    "StructuredField",
    "add_item",
    "apply_group",
    "blank",
    "coerce",
    "describe",
    "editable",
    "group_fields",
    "item_sentence",
    "json_type",
    "move_item",
    "remove_item",
    "shape_of",
]

SCALARS = ("string", "integer", "number", "boolean")

#: How many items a row names before it says "and n more".
_NAMED = 3


@dataclass
class StructuredField:
    """One list or group on the Custom Fields page."""

    key: str
    label: str
    help: str
    #: "list" or "group".
    shape: str
    schema: dict[str, Any] = field(default_factory=dict)
    #: What is shown and edited: the kept value if changed, else the site's.
    value: Any = None


def json_type(spec: Mapping[str, Any]) -> str:
    """The schema's one type: ``["integer", "null"]`` is ``integer``; none is ``""``."""
    kind = spec.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), "")
    return str(kind or "")


def shape_of(spec: Mapping[str, Any]) -> str:
    """``scalar``, ``list``, ``group``, or ``""`` for a schema QUILL cannot edit safely.

    A list needs an ``items`` schema and a group a ``properties`` one;
    WordPress insists on both when the meta is shown in REST, so a schema
    without them is one QUILL leaves as the site has it.
    """
    kind = json_type(spec)
    if kind in SCALARS:
        return "scalar"
    if kind == "array" and isinstance(spec.get("items"), dict) and spec["items"]:
        return "list"
    if kind == "object" and isinstance(spec.get("properties"), dict):
        return "group"
    return ""


def editable(spec: Mapping[str, Any]) -> bool:
    """True when every value inside the schema has a control: lists of scalars or of flat groups."""
    shape = shape_of(spec)
    if shape == "scalar":
        return True
    if shape == "group":
        return all(shape_of(s) == "scalar" for s in _props(spec).values())
    if shape == "list":
        items = spec["items"]
        return shape_of(items) == "scalar" or (shape_of(items) == "group" and editable(items))
    return False


def _props(spec: Mapping[str, Any]) -> dict[str, Any]:
    props = spec.get("properties")
    return (
        {k: v for k, v in props.items() if isinstance(v, dict)} if isinstance(props, dict) else {}
    )


def blank(spec: Mapping[str, Any]) -> Any:
    """A new item's value: the schema's default, or empty of the right type."""
    if "default" in spec:
        return spec["default"]
    shape = shape_of(spec)
    if shape == "list":
        return []
    if shape == "group":
        return {key: blank(sub) for key, sub in _props(spec).items()}
    enum = spec.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    return {"boolean": False, "integer": 0, "number": 0}.get(json_type(spec), "")


def coerce(spec: Mapping[str, Any], value: Any, label: str = "") -> Any:
    """*value* as the schema's type, keeping whatever the schema does not describe.

    Raises :class:`~quill.core.wordpress.custom_fields.FieldValueError` naming
    *label* when a number field holds something that is not a number.
    """
    from quill.core.wordpress.custom_fields import FieldValueError

    shape = shape_of(spec)
    kind = json_type(spec)
    if shape == "list":
        if not isinstance(value, (list, tuple)):
            return [] if value in (None, "") else value
        return [coerce(spec["items"], item, label) for item in value]
    if shape == "group":
        if not isinstance(value, Mapping):
            return value
        props = _props(spec)
        # Keys the schema does not name are carried through untouched.
        return {
            key: coerce(props[key], item, label) if key in props else item
            for key, item in value.items()
        }
    if kind == "boolean":
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on", "checked")
        return bool(value)
    if kind in ("integer", "number"):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value) if kind == "integer" and float(value).is_integer() else value
        text = "" if value is None else str(value).strip()
        if not text:
            return None
        try:
            return int(text) if kind == "integer" else float(text)
        except ValueError as exc:
            raise FieldValueError(label or "This field") from exc
    if kind == "string":
        return "" if value is None else str(value)
    return value


def _scalar_text(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return "empty"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _label(key: str, spec: Mapping[str, Any]) -> str:
    from quill.core.wordpress.custom_fields import label_for

    return label_for(key, spec)


def item_sentence(spec: Mapping[str, Any], value: Any) -> str:
    """One item of a list, or a group, as one line: ``Street 1 Main St, City Springfield``."""
    if shape_of(spec) == "group" and isinstance(value, Mapping):
        props = _props(spec)
        parts = [
            f"{_label(key, props.get(key, {}))} {item_sentence(props.get(key, {}), item)}"
            for key, item in value.items()
        ]
        return ", ".join(parts) if parts else "empty"
    if isinstance(value, Mapping):
        return f"a group of {len(value)}"
    if isinstance(value, (list, tuple)):
        return f"a list of {len(value)}"
    return _scalar_text(value)


def describe(sf: StructuredField) -> str:
    """The row for a list or group: ``Speakers, a list of 3: Ann, Bo, Cy``."""
    name = sf.label.replace("&", "").rstrip(":")
    value = sf.value
    if sf.shape == "list":
        items = list(value) if isinstance(value, (list, tuple)) else []
        if not items:
            return f"{name}, an empty list"
        noun = "item" if len(items) == 1 else "items"
        named = "; ".join(item_sentence(sf.schema.get("items", {}), i) for i in items[:_NAMED])
        more = f", and {len(items) - _NAMED} more" if len(items) > _NAMED else ""
        return f"{name}, a list of {len(items)} {noun}: {named}{more}"
    return f"{name}, a group: {item_sentence(sf.schema, value)}"


def group_fields(spec: Mapping[str, Any], value: Any) -> list[Field]:
    """The labelled fields for a group's scalar members, the value's own first."""
    from quill.core.wordpress.custom_fields import field_for

    have = value if isinstance(value, Mapping) else {}
    fields: list[Field] = []
    for key, sub in _props(spec).items():
        if shape_of(sub) != "scalar":
            continue
        current = have.get(key, sub.get("default"))
        fields.append(field_for(key, sub, current, help_text=_member_help(key, sub)))
    for f, label in zip(fields, assign_access_keys([f.label for f in fields]), strict=True):
        f.label = label
    return fields


def _member_help(key: str, spec: Mapping[str, Any]) -> str:
    description = str(spec.get("description", "") or "").strip().rstrip(".")
    return f"{description or 'One field of this group'}. Saved as {key}."


def apply_group(
    spec: Mapping[str, Any], before: Any, answers: Mapping[str, Any], label: str
) -> Any:
    """The group with *answers* written in, typed, and every other key kept."""
    out = dict(before) if isinstance(before, Mapping) else {}
    props = _props(spec)
    for key, answer in answers.items():
        sub = props.get(key, {})
        out[key] = coerce(sub, answer, f"{label}, {_label(key, sub)}")
    return out


def add_item(values: Sequence[Any], item: Any, at: int | None = None) -> tuple[list[Any], int]:
    """A new list with *item* after row *at* (or at the end); and where it went."""
    out = list(values)
    where = len(out) if at is None else max(0, min(at + 1, len(out)))
    out.insert(where, item)
    return out, where


def remove_item(values: Sequence[Any], at: int) -> tuple[list[Any], int | None]:
    """A new list without row *at*; and the row to select after (``None`` when empty)."""
    out = list(values)
    if 0 <= at < len(out):
        del out[at]
    if not out:
        return out, None
    return out, min(at, len(out) - 1)


def move_item(values: Sequence[Any], at: int, step: int) -> tuple[list[Any], int]:
    """A new list with row *at* moved up (``-1``) or down (``+1``); and where it is now.

    At either end it stays where it is, and the caller says so.
    """
    out = list(values)
    target = at + step
    if not (0 <= at < len(out)) or not (0 <= target < len(out)):
        return out, at
    out[at], out[target] = out[target], out[at]
    return out, target
