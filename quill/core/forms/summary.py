"""Spoken summaries: one line per item, for the outline and Check This Form.

"Email address, email field, required, with an autofill hint, page 1". The
order is fixed (name, kind, what it needs, how it behaves, where it is), so a
listener learns where to stop listening. Rules are read as QAF's sentences.
Nothing here announces anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.forms import libraries
from quill.core.forms import model as M
from quill.core.forms.errors import ChoiceLibraryError, ExpressionError
from quill.core.forms.expr_sentence import sentence


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


class _Vocab:
    def __init__(self, model: M.Model | None) -> None:
        self.model = model or M.create()
        self.labels = M.labels(self.model)
        self.choices = M.choice_labels(self.model)

    def rule(self, text: str) -> str:
        try:
            return sentence(text, self.labels, self.choices)
        except ExpressionError:
            return "a rule QUILL cannot read"

    def library(self, name: str) -> str:
        if name in (self.model.get("choice_libraries") or {}):
            return f"the form's own {name.replace('_', ' ')} list"
        try:
            return f"the {libraries.info(name).label} list"
        except ChoiceLibraryError:
            return f"the {name.replace('_', ' ')} list"


def _count(entries: list[M.Item]) -> int:
    n = 0
    for item in entries:
        if M.is_field_type(item.get("type")):
            n += 1
        if item.get("type") == "columns":
            n += sum(_count(c.get("items") or []) for c in item.get("columns") or [])
        elif item.get("type") != "repeater":
            n += _count(item.get("items") or [])
    return n


def item_summary(
    item: M.Item, model: M.Model | None = None, *, page_number: int | None = None
) -> str:  # noqa: C901
    v = _Vocab(model)
    kind = item.get("type", "")
    if kind == "section":
        text = f"Section, {item.get('label') or 'untitled'}, {_plural(_count(item.get('items') or []), 'question')}"  # noqa: E501
        return text + (f", shown when {v.rule(item['when'])}" if "when" in item else "")
    if kind == "columns":
        cols = item.get("columns") or []
        questions = sum(_count(c.get("items") or []) for c in cols)
        return f"{_plural(len(cols), 'column')} side by side, {_plural(questions, 'question')}"
    name = str(M.TYPE_NAMES.get(kind, kind))
    if kind in M.INPUT_FAMILY:
        name += " field"
    parts: list[str] = [str(item.get("label") or f"Untitled question ({item.get('id')})"), name]
    props = item.get("props") or {}
    validation = item.get("validation") or {}
    if item.get("required"):
        parts.append("required")
    if "choice_library" in item:
        parts.append("choices from " + v.library(item["choice_library"]))
    elif item.get("choices"):
        parts.append(_plural(len(item["choices"]), "choice"))
    if "cascade" in item:
        source = item["cascade"].get("from", "")
        parts.append("follows " + (v.labels.get(source) or source))
    if props.get("autocomplete"):
        parts.append("with an autofill hint")
    if item.get("help"):
        parts.append("with help text")
    if item.get("mask") or validation.get("pattern"):
        parts.append("with a format rule")
    if props.get("read_only"):
        parts.append("read only")
    if props.get("visibility") == "hidden" or kind == "hidden":
        parts.append("hidden from visitors")
    if "smart_default" in item:
        parts.append("starts as " + v.rule(item["smart_default"]))
    if "calculation" in item:
        parts.append("worked out as " + v.rule(item["calculation"]))
    if "scoring" in item:
        parts.append("scored")
    if "when" in item:
        parts.append("shown when " + v.rule(item["when"]))
    if kind == "repeater":
        parts.append(_plural(len(item.get("items") or []), "question") + " each time")
    if page_number is not None:
        parts.append(f"page {page_number}")
    return ", ".join(parts)


field_summary = item_summary


@dataclass
class OutlineRow:
    level: int  # 0 page, 1 a page's items, 2 inside a section...
    text: str
    item: Any


def outline(model: M.Model, islands: list[str] | None = None) -> list[OutlineRow]:
    """Pages, then their sections and fields, each as a sentence; islands last."""
    rows: list[OutlineRow] = []
    for number, page in enumerate(model.get("pages") or [], 1):
        title = f", {page['title']}" if page.get("title") else ""
        when = f", shown when {_Vocab(model).rule(page['when'])}" if "when" in page else ""
        count = _plural(_count(page.get("items") or []), "question")
        rows.append(OutlineRow(0, f"Page {number}{title}, {count}{when}", page))
        _rows(page.get("items") or [], 1, model, number, rows)
    for text in islands or []:
        first = text.strip().splitlines()[0] if text.strip() else ""
        rows.append(OutlineRow(0, f"Kept as written, not read by QAF: {first[:80]}", text))
    return rows


def _rows(
    entries: list[M.Item], level: int, model: M.Model, page: int, rows: list[OutlineRow]
) -> None:
    for item in entries:
        rows.append(OutlineRow(level, item_summary(item, model, page_number=page), item))
        if item.get("type") == "columns":
            for col in item.get("columns") or []:
                _rows(col.get("items") or [], level + 1, model, page, rows)
        else:
            _rows(item.get("items") or [], level + 1, model, page, rows)


def outline_rows(model: M.Model, islands: list[str] | None = None) -> list[tuple[str, str | None]]:
    """The outline as ``(spoken row, item id)``: pages carry None, and each level
    is indented two more spaces, as the Form Outline window lists it.
    """
    out: list[tuple[str, str | None]] = []
    for row in outline(model, islands):
        if row.level == 0:
            out.append((row.text, None))
        else:
            out.append(("  " * row.level + row.text, str(row.item.get("id"))))
    return out
