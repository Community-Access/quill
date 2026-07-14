"""Data ordering model for verbosity announcements (verbosity §14).

When a verb has no custom *template*, its announcement is assembled from an
ordered list of fields joined by a separator — the *data order*. A user can move
fields up and down to hear, say, the word before its position, or drop a field
entirely. When both a custom template and a custom data order exist for a verb,
the template wins (verbosity §14); this module only owns the ordering side.

:class:`DataOrder` is a frozen, hashable value object: every reordering returns a
new instance, so it is safe to share and to use as a dict key.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["DataOrder"]


@dataclass(frozen=True, slots=True)
class DataOrder:
    """An ordered set of fields for one verb's announcement."""

    verb_id: str
    fields: tuple[str, ...]
    separator: str = ", "

    def move_up(self, field_name: str) -> DataOrder:
        """Return a copy with ``field_name`` moved one place earlier.

        A no-op (returns an equal instance) when the field is missing or already
        first.
        """
        return self._move(field_name, -1)

    def move_down(self, field_name: str) -> DataOrder:
        """Return a copy with ``field_name`` moved one place later."""
        return self._move(field_name, +1)

    def _move(self, field_name: str, delta: int) -> DataOrder:
        if field_name not in self.fields:
            return self
        index = self.fields.index(field_name)
        target = index + delta
        if target < 0 or target >= len(self.fields):
            return self
        items = list(self.fields)
        items[index], items[target] = items[target], items[index]
        return DataOrder(self.verb_id, tuple(items), self.separator)

    def reset(self, default_fields: tuple[str, ...]) -> DataOrder:
        """Return a copy whose fields are restored to ``default_fields``."""
        return DataOrder(self.verb_id, tuple(default_fields), self.separator)

    def render(self, values: dict[str, Any]) -> str:
        """Join the present field values in order, skipping missing/empty ones."""
        rendered = [
            str(values[name])
            for name in self.fields
            if name in values and values[name] not in (None, "")
        ]
        return self.separator.join(rendered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verb_id": self.verb_id,
            "fields": list(self.fields),
            "separator": self.separator,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataOrder:
        return cls(
            verb_id=str(data["verb_id"]),
            fields=tuple(str(field) for field in data.get("fields", ())),
            separator=str(data.get("separator", ", ")),
        )
