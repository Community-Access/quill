"""What a property sheet's save did, and the one sentence that says so.

Split from ``sheet_engine`` (GATE-11): the engine plans, sends and re-reads;
this module only holds the outcome it proves and turns it into words. Both
names are re-exported from ``sheet_engine``, which is where callers import them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.workbench.properties import MIXED, FieldChange, Value

__all__ = ["SaveOutcome", "sentence"]


@dataclass
class SaveOutcome:
    """What a save did, field by field, as the re-read proved it."""

    done: list[FieldChange] = field(default_factory=list)
    not_taken: list[FieldChange] = field(default_factory=list)
    failed: list[tuple[FieldChange, str]] = field(default_factory=list)
    conflicts: tuple[FieldChange, ...] = ()
    after: dict[str, Value] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.not_taken and not self.failed and not self.conflicts


def _value_words(value: object) -> str:
    if isinstance(value, tuple):
        return ", ".join(value) if value else "none"
    if isinstance(value, bool):
        return "on" if value else "off"
    if value is None or value == "" or value is MIXED:
        return "none"
    return str(value)


def _change_words(change: FieldChange) -> str:
    label = change.label.lower()
    before, after = change.before, change.after
    if isinstance(after, tuple):
        old = before if isinstance(before, tuple) else ()
        added = [item for item in after if item not in old]
        removed = [item for item in old if item not in after]
        if label.startswith("assignee"):
            parts = [f"assigned to {', '.join(added)}"] if added else []
            parts += [f"unassigned {', '.join(removed)}"] if removed else []
        else:
            parts = [f"added {', '.join(added)}"] if added else []
            parts += [f"removed {', '.join(removed)}"] if removed else []
        return ", ".join(parts) or f"{label} unchanged"
    if label in {"body", "description"} and isinstance(after, str) and len(after) > 40:
        return f"{label} changed"
    return f"{label} {_value_words(after)}"


def sentence(name: str, outcome: SaveOutcome) -> str:
    """The one sentence after a save: "#42: added bug, removed docs; milestone 2027.1."

    Only what the re-read proved is claimed; a field that did not take, or
    failed, is named after it.
    """
    parts: list[str] = []
    if outcome.done:
        parts.append(f"{name}: " + "; ".join(_change_words(c) for c in outcome.done) + ".")
    if outcome.not_taken:
        names = ", ".join(c.label.lower() for c in outcome.not_taken)
        parts.append(
            f"GitHub accepted but did not change {names}; you may not have access to set it."
        )
    for change, reason in outcome.failed:
        parts.append(f"Could not change {change.label.lower()}: {reason}")
    if outcome.conflicts:
        names = ", ".join(c.label.lower() for c in outcome.conflicts)
        parts.append(f"Changed on GitHub since you opened this: {names}. Nothing was saved.")
    return " ".join(parts) or f"{name}: nothing changed."
