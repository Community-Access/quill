"""Accessible announcement strings for the Structured List Studio (§11, §16, §25).

Screen-reader output is a first-class product requirement, so the phrasing lives
here — wx-free and unit-tested — rather than being inlined in the dialog. The
functions build the per-item outline labels and the whole-list summaries at the
configured verbosity, using human words ("term", "definition", "of") and never
leaking ``<dt>``/``<dd>`` element names (§16 final note).
"""

from __future__ import annotations

from quill.core.lists.model import (
    DefinitionList,
    FlatList,
    ListType,
)
from quill.core.lists.settings import StructuredListSettings

_TYPE_WORD = {
    ListType.BULLET: "Bulleted list",
    ListType.ORDERED: "Numbered list",
    ListType.CHECKLIST: "Checklist",
    ListType.DEFINITION: "Definition list",
}


def flat_item_announcement(
    model: FlatList, index: int, settings: StructuredListSettings | None = None
) -> str:
    """Announce one flat-list item (§11.1 verbosity profiles)."""
    cfg = settings if settings is not None else StructuredListSettings()
    if index < 0 or index >= len(model.items):
        return ""
    item = model.items[index]
    parts: list[str] = []
    if model.list_type is ListType.CHECKLIST:
        parts.append("Checked" if item.checked else "Not checked")
    elif model.list_type is ListType.ORDERED:
        parts.append(f"{_ordinal_number(model, index)}.")
    parts.append((item.text.split("\n", 1)[0]).strip() or "(empty)")
    if cfg.verbosity in {"standard", "detailed"}:
        parts.append(f"{index + 1} of {len(model.items)}")
        if item.level > 0:
            parts.append(f"level {item.level + 1}")
    if cfg.verbosity == "detailed" and model.list_type is ListType.CHECKLIST:
        done = sum(1 for i in model.items if i.checked)
        parts.append(f"{done} of {len(model.items)} complete")
    return ". ".join(parts).replace("..", ".")


def _ordinal_number(model: FlatList, index: int) -> int:
    number = model.ordered_start
    for i in range(index):
        if model.items[i].level == model.items[index].level:
            number += 1
    return number


def checklist_toggle_announcement(
    model: FlatList, index: int, settings: StructuredListSettings | None = None
) -> str:
    """Announce a checked-state change (§10.3 recommended: state, name, total)."""
    cfg = settings if settings is not None else StructuredListSettings()
    item = model.items[index]
    state = "Checked" if item.checked else "Unchecked"
    name = item.text.split("\n", 1)[0].strip() or "item"
    if cfg.verbosity == "concise":
        return f"{state}: {name}."
    done = sum(1 for i in model.items if i.checked)
    return f"{state}: {name}. {done} of {len(model.items)} tasks complete."


def definition_entry_announcement(
    model: DefinitionList, index: int, settings: StructuredListSettings | None = None
) -> str:
    """Announce one definition entry (§16 examples)."""
    if index < 0 or index >= len(model.entries):
        return ""
    entry = model.entries[index]
    total = len(model.entries)
    terms = [t.strip() for t in entry.terms if t.strip()]
    definitions = [d for d in entry.definitions if d.strip()]
    term_label = "Terms" if len(terms) > 1 else "Term"
    term_text = " and ".join(terms) if terms else "(no term)"
    head = f"{term_label}: {term_text}. Entry {index + 1} of {total}."
    if len(terms) > 1:
        head += f" {len(terms)} terms,"
        head += f" {_count_phrase(len(definitions), 'definition')}."
    else:
        head += f" {_count_phrase(len(definitions), 'definition')}."
    return head


def _count_phrase(count: int, noun: str) -> str:
    if count == 1:
        return f"One {noun}"
    if count == 0:
        return f"No {noun}s"
    return f"{count} {noun}s"


def list_summary(
    model: FlatList | DefinitionList, settings: StructuredListSettings | None = None
) -> str:
    """One-line summary of the whole list (§25)."""
    cfg = settings if settings is not None else StructuredListSettings()
    if isinstance(model, DefinitionList):
        entries = len(model.entries)
        base = f"Definition list, {_count_phrase(entries, 'entry').lower()}"
        base = base.replace("entrys", "entries")
        if cfg.verbosity == "detailed":
            base += f", {model.term_count()} terms, {model.definition_count()} definitions"
        return base + "."
    word = _TYPE_WORD[model.list_type]
    count = len(model.items)
    summary = f"{word}, {count} item{'s' if count != 1 else ''}"
    if model.list_type is ListType.CHECKLIST:
        done = sum(1 for i in model.items if i.checked)
        summary += f", {done} of {count} complete"
    return summary + "."
