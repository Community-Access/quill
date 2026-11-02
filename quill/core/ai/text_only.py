"""Everything is text: the family instruction, and the rule for chart-like answers.

Decision 13 (codex.md 10C.5): every AI answer in every QuillVille app is
sentences and lists, spoken through the announcement service and brailled on
the same path. Two halves make that true:

* :data:`FAMILY_INSTRUCTION` is one line **appended** to each connection's
  system text at the connection layer (:func:`with_family_instruction`). No
  basic prompt's wording changes (10D.1): the line goes after the prompt, at
  the place a request leaves for a connection, never into a template.
* :func:`as_text` is the rendering rule for anything chart-like a model sends
  anyway. A Mermaid block keeps its words but loses the fence label a
  renderer would draw from, and a Markdown image link becomes a sentence
  naming the picture, so nothing fetches or draws it. Text bars are already
  text and are left alone.

wx-free and strict-typed.
"""

from __future__ import annotations

import re

__all__ = ["FAMILY_INSTRUCTION", "as_text", "with_family_instruction"]

#: The one shared line, the same for every connection and every app.
FAMILY_INSTRUCTION = (
    "Never draw charts, graphs or diagrams, in text art or otherwise; "
    "answer in sentences and lists."
)

_DRAWN_FENCE = re.compile(
    r"^(\s*)(```|~~~)\s*(mermaid|plantuml|graphviz|dot|vega(?:-lite)?|chart)\b[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)
_IMAGE_LINK = re.compile(r"!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")


def with_family_instruction(system: str) -> str:
    """*system* with the family line after it, once."""
    text = (system or "").rstrip()
    if FAMILY_INSTRUCTION in text:
        return text
    return f"{text}\n\n{FAMILY_INSTRUCTION}" if text else FAMILY_INSTRUCTION


def as_text(answer: str) -> str:
    """*answer* with anything that would be drawn turned into the text it is."""
    if not answer:
        return answer
    text = _DRAWN_FENCE.sub(lambda m: f"{m.group(1)}{m.group(2)}text", answer)

    def picture(match: re.Match[str]) -> str:
        alt = match.group(1).strip()
        where = match.group(2).strip()
        return f"(picture link: {alt}, {where})" if alt else f"(picture link: {where})"

    return _IMAGE_LINK.sub(picture, text)
