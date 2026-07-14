"""Conversions between list types, with information-loss detection (§19).

The PRD insists conversions never silently discard structure: alternate terms,
extra definitions, checked states, ordered start values, and nesting must be
surfaced as warnings before the change is committed (§19.4). These functions
return both the converted model and a :class:`ConversionLoss` describing what a
given conversion *would* drop, so the dialog can warn and require confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.lists.model import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)


@dataclass(slots=True)
class ConversionLoss:
    """What a conversion would discard (empty ``reasons`` means lossless)."""

    reasons: list[str] = field(default_factory=list)

    @property
    def lossy(self) -> bool:
        return bool(self.reasons)


def flat_to_definition(
    model: FlatList, *, split: str = "colon"
) -> tuple[DefinitionList, ConversionLoss]:
    """Convert a flat list to a definition list (§19.1).

    ``split`` chooses how each item becomes a term/definition:
    ``"colon"`` splits on the first ``": "``, ``"tab"`` on a tab, ``"term_only"``
    uses the whole item as the term with a blank definition. QUILL never guesses
    the relationship without the caller's explicit ``split`` choice (§19.1).
    """
    loss = ConversionLoss()
    if model.list_type is ListType.CHECKLIST and any(i.checked for i in model.items):
        loss.reasons.append("Checked states will be discarded.")
    if any(item.level > 0 for item in model.items):
        loss.reasons.append("Nesting relationships will be flattened.")

    entries: list[DefinitionEntry] = []
    for item in model.items:
        term, definition = _split_item(item.text, split)
        entries.append(DefinitionEntry(terms=[term], definitions=[definition]))
    return DefinitionList(entries=entries), loss


def _split_item(text: str, split: str) -> tuple[str, str]:
    cleaned = text.strip()
    if split == "term_only":
        return cleaned, ""
    sep = "\t" if split == "tab" else ": "
    idx = cleaned.find(sep)
    if idx < 0:
        return cleaned, ""
    return cleaned[:idx].strip(), cleaned[idx + len(sep) :].strip()


def definition_to_flat(
    model: DefinitionList,
    *,
    list_type: ListType = ListType.BULLET,
    style: str = "term_definition",
) -> tuple[FlatList, ConversionLoss]:
    """Convert a definition list to a bullet/ordered/checklist list (§19.2, §19.3).

    ``style`` controls each item's text: ``"term_definition"`` -> ``Term: Def``,
    ``"term_only"`` -> the term, ``"definition_only"`` -> the definition. Entries
    with multiple terms or definitions are flagged in the returned loss so the
    caller can require review (§19.4).
    """
    loss = ConversionLoss()
    items: list[ListItem] = []
    for entry in model.entries:
        terms = [t for t in entry.terms if t.strip()]
        definitions = [d for d in entry.definitions if d.strip()]
        if len(terms) > 1:
            loss.reasons.append(f"Alternate terms for '{entry.primary_term}' will be dropped.")
        if len(definitions) > 1:
            loss.reasons.append(f"Extra definitions for '{entry.primary_term}' will be dropped.")
        term = terms[0] if terms else ""
        definition = definitions[0] if definitions else ""
        items.append(ListItem(text=_compose(term, definition, style)))
    return FlatList(list_type=list_type, items=items), loss


def _compose(term: str, definition: str, style: str) -> str:
    if style == "term_only":
        return term
    if style == "definition_only":
        return definition
    if term and definition:
        return f"{term}: {definition}"
    return term or definition
