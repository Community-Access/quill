"""Spoken summaries: one line per field, section and page, for the outline.

"Email address, email, required, with an autofill hint" is what View > Form
Outline and Check This Form say for a field. The wording is plain and the
order fixed (name, kind, what it needs, how it behaves, where it is), so a
listener learns where to stop listening. Nothing here announces anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.forms import libraries
from quill.core.forms.errors import ChoiceLibraryError, ExpressionError
from quill.core.forms.expr_sentence import Vocabulary, sentence
from quill.core.forms.model import (
    FIELD_TYPES,
    TYPE_NAMES,
    Columns,
    Field,
    Form,
    Island,
    Item,
    Section,
    walk_items,
)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _rule(expression: str, vocab: Vocabulary) -> str:
    try:
        return sentence(expression, vocab)
    except ExpressionError:
        return "a rule QUILL cannot read"


def _library_name(library_id: str) -> str:
    try:
        return libraries.info(library_id).label
    except ChoiceLibraryError:
        return library_id.replace("_", " ")


def field_summary(
    item: Field, vocab: Vocabulary | None = None, *, page_number: int | None = None
) -> str:
    vocab = vocab or Vocabulary()
    kind = TYPE_NAMES.get(item.type, item.type)
    if FIELD_TYPES.get(item.type) in ("input", "contact", "date"):
        kind += " field"
    parts = [item.label or f"Untitled question ({item.id})", kind]
    s = item.settings
    if item.required:
        parts.append("required")
    if item.choice_library:
        parts.append(f"choices from the {_library_name(item.choice_library)} list")
    elif item.choices:
        parts.append(_plural(len(item.choices), "choice"))
    if item.cascade is not None:
        parts.append(f"follows {vocab.labels.get(item.cascade.source, item.cascade.source)}")
    if s.get("autocomplete"):
        parts.append("with an autofill hint")
    if item.help:
        parts.append("with help text")
    if s.get("input_mask") or s.get("pattern"):
        parts.append("with a format rule")
    if s.get("read_only"):
        parts.append("read only")
    if s.get("visibility") == "hidden" or item.type == "hidden":
        parts.append("hidden from visitors")
    if item.default_expr:
        parts.append(f"starts as {_rule(item.default_expr, vocab)}")
    if item.calculate:
        parts.append(f"worked out as {_rule(item.calculate, vocab)}")
    if item.score:
        parts.append("scored")
    if item.visible_when:
        parts.append(f"shown when {_rule(item.visible_when, vocab)}")
    if item.fields:
        parts.append(_plural(len(item.fields), "question") + " each time")
    if s.get("unknown_modifiers"):
        unknown = s["unknown_modifiers"]
        count = len(unknown) if isinstance(unknown, list) else 1
        parts.append(_plural(count, "setting") + " QUILL keeps as written")
    if page_number is not None:
        parts.append(f"page {page_number}")
    return ", ".join(parts)


def _count(items: list[Item]) -> int:
    return sum(1 for i in walk_items(items) if isinstance(i, Field))


def item_summary(
    item: Item, vocab: Vocabulary | None = None, *, page_number: int | None = None
) -> str:
    vocab = vocab or Vocabulary()
    if isinstance(item, Field):
        return field_summary(item, vocab, page_number=page_number)
    if isinstance(item, Section):
        text = f"Section, {item.title or 'untitled'}, {_plural(_count(item.items), 'question')}"
        return text + (
            f", shown when {_rule(item.visible_when, vocab)}" if item.visible_when else ""
        )
    if isinstance(item, Columns):
        questions = sum(_count(c) for c in item.columns)
        return (
            f"{_plural(len(item.columns), 'column')} side by side, {_plural(questions, 'question')}"
        )
    first = item.text.strip().splitlines()[0] if item.text.strip() else ""
    if item.reason == "comment":
        return f"Comment: {first.lstrip('/').strip(' */')}"
    return f"Kept as written, not read by QUILL: {first[:80]}"


@dataclass
class OutlineRow:
    level: int  # 0 page, 1 section or top-level item, 2 inside a section...
    text: str
    item: Any


def outline(form: Form) -> list[OutlineRow]:
    """The form outline: pages, then their sections and fields, each as a sentence."""
    vocab = Vocabulary.from_form(form)
    rows: list[OutlineRow] = []
    for number, page in enumerate(form.pages, 1):
        title = f", {page.title}" if page.title else ""
        rows.append(
            OutlineRow(0, f"Page {number}{title}, {_plural(_count(page.items), 'question')}", page)
        )
        _rows(page.items, 1, vocab, number, rows)
    return rows


def _rows(
    items: list[Item], level: int, vocab: Vocabulary, page: int, rows: list[OutlineRow]
) -> None:
    for item in items:
        rows.append(OutlineRow(level, item_summary(item, vocab, page_number=page), item))
        if isinstance(item, Section):
            _rows(item.items, level + 1, vocab, page, rows)
        elif isinstance(item, Columns):
            for column in item.columns:
                _rows(column, level + 1, vocab, page, rows)


def island_summary(item: Island) -> str:
    return item_summary(item)
