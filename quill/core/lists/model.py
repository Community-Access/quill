"""Neutral structured-list model (§22).

A format-independent representation the dialog edits and the renderers serialize.
The same model covers bulleted, numbered, and checklist items (``FlatList``) and
term/definition entries (``DefinitionList``), so conversions between them are
plain data transformations rather than text surgery.

Stable ``*_id`` identities exist for the UI (outline selection, reordering) and
must **never** appear in the user's generated source (§22 final note).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum

_ids = itertools.count(1)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{next(_ids)}"


class ListType(Enum):
    """The kind of structure the model represents."""

    BULLET = "bullet"
    ORDERED = "ordered"
    CHECKLIST = "checklist"
    DEFINITION = "definition"


@dataclass(slots=True)
class ListItem:
    """One item in a flat (or nested) bullet/ordered/checklist list.

    ``level`` is the nesting depth (0 = top level). ``checked`` only applies to
    checklist items. ``text`` may contain internal newlines for a loose,
    multi-line item; the renderer handles continuation indentation.
    """

    text: str = ""
    level: int = 0
    checked: bool = False
    item_id: str = field(default_factory=lambda: _new_id("item"))


@dataclass(slots=True)
class FlatList:
    """A bullet, ordered, or checklist list (possibly nested via item levels)."""

    list_type: ListType = ListType.BULLET
    items: list[ListItem] = field(default_factory=list)
    ordered_start: int = 1

    def is_empty(self) -> bool:
        return not any(item.text.strip() for item in self.items)


@dataclass(slots=True)
class DefinitionEntry:
    """One entry: one or more terms, one or more definitions (§22).

    Terms and definitions are stored as plain strings here (the simple, common
    case the PRD centres on, §14.2). The model permits several of each so the
    HTML/Markdown renderers can emit multiple ``<dt>``/``<dd>`` and multi-term
    syntax without the UI having to special-case them.
    """

    terms: list[str] = field(default_factory=lambda: [""])
    definitions: list[str] = field(default_factory=lambda: [""])
    entry_id: str = field(default_factory=lambda: _new_id("entry"))

    @property
    def primary_term(self) -> str:
        return self.terms[0] if self.terms else ""

    @property
    def primary_definition(self) -> str:
        return self.definitions[0] if self.definitions else ""

    def terms_text(self) -> str:
        """This entry's terms as a one-per-line string for an editor field."""
        return "\n".join(self.terms)

    def set_terms_text(self, text: str) -> None:
        """Replace the terms from a one-per-line editor field (§15.3).

        Each non-blank line becomes a term (synonyms render as multiple ``<dt>``).
        Surrounding whitespace is trimmed; an all-blank field keeps a single empty
        term so the entry still round-trips and never collapses to zero terms.
        """
        kept = [line.strip() for line in text.splitlines() if line.strip()]
        self.terms = kept or [""]

    def definitions_text(self) -> str:
        """The entry's definitions as one editor string, blank-line separated.

        A blank line separates definitions so each one may itself span several
        lines (a multi-paragraph definition keeps its internal newlines).
        """
        return "\n\n".join(self.definitions)

    def set_definitions_text(self, text: str) -> None:
        """Replace the definitions from a blank-line-separated editor field (§15.4).

        Each block separated by one or more blank lines becomes a definition
        (rendered as its own ``<dd>``); internal single newlines are preserved so
        a definition can be multi-line. Trailing/leading blank lines are ignored;
        an all-blank field keeps a single empty definition so the entry still
        round-trips and never collapses to zero definitions.
        """
        blocks: list[str] = []
        current: list[str] = []
        for line in text.splitlines():
            if line.strip():
                current.append(line.rstrip())
            elif current:
                blocks.append("\n".join(current).strip())
                current = []
        if current:
            blocks.append("\n".join(current).strip())
        self.definitions = blocks or [""]

    def is_blank(self) -> bool:
        return not any(t.strip() for t in self.terms) and not any(
            d.strip() for d in self.definitions
        )


@dataclass(slots=True)
class DefinitionList:
    """A definition/description list (§22)."""

    entries: list[DefinitionEntry] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.entries or all(entry.is_blank() for entry in self.entries)

    def term_count(self) -> int:
        return sum(len([t for t in e.terms if t.strip()]) for e in self.entries)

    def definition_count(self) -> int:
        return sum(len([d for d in e.definitions if d.strip()]) for e in self.entries)
