"""A form laid out for paper and braille: one source, every format (wordpress.md 17a.7).

wx-free. The Word, large-print and braille-ready exports all read the form
through :func:`blocks`, so a paper form and its web form cannot disagree: the
same questions, in the same order, with the same choices and help, from the
same model. Choice libraries are written out as their choices
(:func:`resolve_choices`), because paper cannot look a list up.

The braille-ready text (:func:`braille_text`) is one question per block, its
choices listed one to a line, wrapped at 40 cells -- the width of a standard
braille page -- so it reads well on a display before it is ever translated.
"""

from __future__ import annotations

import copy
import textwrap
from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import model as M

#: Cells on a standard braille line.
BRAILLE_WIDTH = 40

#: Field types that have nothing to fill in on paper.
_NOT_ON_PAPER = frozenset(
    "hidden captcha submit save progress summary social payment calculation total".split()
)
#: How many lines to leave for a written answer.
_LINES = {"textarea": 4, "rich_text": 4, "address": 3, "post_content": 6, "signature": 2}

_PICK_MANY = frozenset("checkbox multiselect ranking".split())


@dataclass(frozen=True)
class Block:
    """One thing on the page: a heading, a question, or a paragraph of text."""

    kind: str  # "page", "section", "question", "text"
    label: str
    help: str = ""
    required: bool = False
    field_type: str = ""
    choices: tuple[str, ...] = ()
    lines: int = 1
    number: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def pick(self) -> str:
        """ "one", "many" or "" -- how the choices are answered."""
        if not self.choices:
            return ""
        return "many" if self.field_type in _PICK_MANY else "one"


def resolve_choices(model: M.Model) -> M.Model:
    """A copy of *model* with every choice library written out as choices.

    The form's own libraries come first, then QAF's built-in ones. A cascading
    library (State after Country) has no fixed list, so it stays empty and the
    question gets lines to write on instead.
    """
    out = copy.deepcopy(model)
    own = out.get("choice_libraries") or {}
    for item in M.iter_items(out):
        library = item.get("choice_library")
        if not library or item.get("choices"):
            continue
        found = own.get(library)
        if found is None:
            try:
                from quill.core.forms import libraries

                found = libraries.choices(library)
            except Exception:  # noqa: BLE001 - an unknown library leaves the question open
                found = []
        if found:
            item["choices"] = [dict(c) for c in found]
    return out


def blocks(model: M.Model) -> list[Block]:
    """The form, top to bottom, as paper and braille show it."""
    resolved = resolve_choices(model)
    pages = resolved.get("pages") or []
    out: list[Block] = []
    counter = [0]
    for index, page in enumerate(pages, 1):
        if len(pages) > 1:
            title = page.get("title") or f"Page {index} of {len(pages)}"
            out.append(Block("page", str(title), str(page.get("description") or "")))
        _walk(page.get("items") or [], out, counter)
    return out


def _walk(entries: list[M.Item], out: list[Block], counter: list[int]) -> None:
    for item in entries:
        kind = item.get("type", "")
        if kind == "section":
            out.append(Block("section", str(item.get("label") or ""), str(item.get("help") or "")))
            _walk(item.get("items") or [], out, counter)
        elif kind == "columns":
            for column in item.get("columns") or []:
                _walk(column.get("items") or [], out, counter)
        elif kind == "html":
            text = _plain_html(str((item.get("props") or {}).get("html", "")))
            if text:
                out.append(Block("text", text))
        elif kind in _NOT_ON_PAPER or not M.is_field_type(kind):
            continue
        else:
            counter[0] += 1
            choices = tuple(
                str(c.get("label", c.get("value", ""))) for c in item.get("choices") or []
            )
            if kind == "consent" and not choices:
                choices = (str(item.get("label") or "I agree"),)
            out.append(
                Block(
                    "question",
                    str(item.get("label") or item.get("id") or ""),
                    str(item.get("help") or ""),
                    bool(item.get("required")),
                    kind,
                    choices,
                    _LINES.get(kind, 1),
                    counter[0],
                )
            )


def _plain_html(text: str) -> str:
    import re
    from html import unescape

    return " ".join(unescape(re.sub(r"<[^>]+>", " ", text)).split())


def how_to_answer(block: Block) -> str:
    """What a reader does with the question, in words rather than a symbol."""
    if block.field_type == "consent":
        return "Check the box to agree."
    if block.pick == "many":
        return "Check all that apply."
    if block.pick == "one":
        return "Choose one."
    if block.field_type in ("date", "datetime", "daterange"):
        return "Write the date."
    if block.lines > 1:
        return "Write your answer."
    return ""


def question_heading(block: Block) -> str:
    """ "3. Email address (required)" -- required is a word, never an asterisk."""
    required = " (required)" if block.required else ""
    return f"{block.number}. {block.label}{required}"


def braille_text(model: M.Model, *, width: int = BRAILLE_WIDTH) -> str:
    """The form as braille-ready text: one question per block, choices listed.

    Plain text wrapped at *width* cells, with a blank line between blocks and
    choices lettered a, b, c so a reader can answer by letter. Nothing in it
    needs print layout to make sense.
    """
    wrap = textwrap.TextWrapper(width=width, break_long_words=True, break_on_hyphens=False)
    lines: list[str] = []

    def para(text: str, indent: str = "") -> None:
        if text.strip():
            wrap.initial_indent = indent
            wrap.subsequent_indent = indent
            lines.extend(wrap.wrap(" ".join(text.split())))

    para(str(model.get("title") or "Form"))
    para(str(model.get("description") or ""))
    lines.append("")
    for block in blocks(model):
        if block.kind in ("page", "section"):
            para(block.label.upper() if block.kind == "page" else block.label)
            para(block.help)
        elif block.kind == "text":
            para(block.label)
        else:
            para(question_heading(block))
            para(block.help)
            para(how_to_answer(block))
            for letter, choice in zip(_letters(), block.choices, strict=False):
                para(f"{letter}. {choice}", "  ")
            if not block.choices:
                lines.append("Answer:")
        lines.append("")
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def _letters() -> list[str]:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    return list(alphabet) + [a + b for a in alphabet for b in alphabet]


__all__ = [
    "BRAILLE_WIDTH",
    "Block",
    "blocks",
    "braille_text",
    "how_to_answer",
    "question_heading",
    "resolve_choices",
]
