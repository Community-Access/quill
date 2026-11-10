"""Safe field-type conversion for QUILL Accessible Forms.

The form model stores field properties alongside their type. A type change
keeps the shared settings and carries option data between compatible choice
controls; only settings the new control cannot represent are removed, and the
caller receives those details before applying the change.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from quill.core.forms import model as M

__all__ = ["TypeChangePlan", "plan_type_change"]

_CHOICE_CONTROLS = frozenset((*M.CHOICE_TYPES, *M.OPTIONAL_CHOICE_TYPES))
_MULTI_CHOICE_CONTROLS = frozenset({"checkbox", "multiselect", "ranking", "image_choice"})
_SINGLE_CHOICE_CONTROLS = frozenset({"radio", "select"})
_REQUIRED_SETUP: dict[str, tuple[str, ...]] = {
    "calculation": ("calculation",),
    "quiz": ("scoring",),
    "matrix": ("props.rows", "props.columns"),
    "likert": ("props.rows",),
    "repeater": ("items",),
}


@dataclass(frozen=True, slots=True)
class TypeChangePlan:
    """A converted field and the properties a person should review first."""

    field: dict[str, Any]
    old_type: str
    new_type: str
    kept: tuple[str, ...]
    converted: tuple[str, ...]
    removed: tuple[str, ...]
    blocked: tuple[str, ...]

    @property
    def can_apply(self) -> bool:
        return not self.blocked

    @property
    def summary(self) -> str:
        old = M.TYPE_NAMES.get(self.old_type, self.old_type)
        new = M.TYPE_NAMES.get(self.new_type, self.new_type)
        return f"Change this field from {old} to {new}."

    def review_lines(self) -> list[str]:
        lines = ["Kept: " + (", ".join(self.kept) if self.kept else "the field label and id") + "."]
        if self.converted:
            lines.append("Adjusted: " + "; ".join(self.converted) + ".")
        if self.removed:
            lines.append("Cannot carry over: " + ", ".join(self.removed) + ".")
        if self.blocked:
            lines.append("Set up first: " + "; ".join(self.blocked) + ".")
        return lines


def _has_path(field: dict[str, Any], path: str) -> bool:
    value: Any = field
    for key in path.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value is not None and value != [] and value != {}


def _choice_values(field: dict[str, Any]) -> list[str]:
    return [
        str(choice.get("value", ""))
        for choice in field.get("choices", [])
        if isinstance(choice, dict) and str(choice.get("value", ""))
    ]


def _default_choice(field: dict[str, Any]) -> dict[str, str]:
    """Seed a new choice control from the existing default, or with one clear option."""
    value = field.get("default")
    if isinstance(value, list):
        value = value[0] if value else ""
    label = str(value).strip() if value not in (None, "") else "Choice 1"
    choice_value = M.slug(label) or "choice-1"
    return {"value": choice_value, "label": label}


def plan_type_change(field: dict[str, Any], new_type: str) -> TypeChangePlan:
    """Return a safe field conversion without mutating *field*."""
    old_type = str(field.get("type", "text"))
    if not M.is_field_type(new_type):
        raise ValueError(f"{new_type!r} is not a QAF field type.")
    if old_type == new_type:
        return TypeChangePlan(deepcopy(field), old_type, new_type, (), (), (), ())

    converted = deepcopy(field)
    converted["type"] = new_type
    removed: list[str] = []
    adjusted: list[str] = []
    choice_target = new_type in _CHOICE_CONTROLS
    if choice_target:
        if new_type in M.CHOICE_TYPES and not any(
            converted.get(key) for key in ("choices", "choice_library", "cascade")
        ):
            starter = _default_choice(converted)
            converted["choices"] = [starter]
            if converted.get("default") not in (None, "", []):
                converted["default"] = starter["value"]
                adjusted.append("made the existing default a matching choice")
            else:
                adjusted.append("added one starter choice so the new control can be filled in")
    else:
        for key in ("choices", "choice_library", "cascade"):
            if key in converted:
                converted.pop(key)
                removed.append(key.replace("_", " "))

    default = converted.get("default")
    if (
        new_type in _MULTI_CHOICE_CONTROLS
        and default not in (None, "")
        and not isinstance(default, list)
    ):
        converted["default"] = [default]
        adjusted.append("kept the selected default as a one-item selection")
    elif new_type in _SINGLE_CHOICE_CONTROLS and isinstance(default, list):
        converted["default"] = default[0] if default else ""
        adjusted.append("kept the first selected default for the single-choice control")
    elif new_type not in _CHOICE_CONTROLS and isinstance(default, list):
        converted["default"] = ", ".join(str(value) for value in default)
        adjusted.append("kept selected values as comma-separated text")

    blocked = tuple(
        path for path in _REQUIRED_SETUP.get(new_type, ()) if not _has_path(converted, path)
    )
    kept = tuple(
        key.replace("_", " ")
        for key in (
            "label",
            "help",
            "placeholder",
            "required",
            "default",
            "smart_default",
            "when",
            "validation",
            "attributes",
            "props",
            "choices",
            "choice_library",
            "cascade",
        )
        if key in converted
    )
    return TypeChangePlan(
        converted,
        old_type,
        new_type,
        kept,
        tuple(adjusted),
        tuple(removed),
        blocked,
    )
