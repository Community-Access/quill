"""What an editor tells Ask about the document (codex.md 10C.3).

Ask takes a small block of named facts from the editor's own state, rebuilt for
every turn, plus the person's question. For QUILL and QUILL Lite the facts are:

* **the passage** -- the selection, else the paragraph the cursor is in, else
  the section (:func:`quill.core.ai.gateway_context.resolve_scope`, the same
  resolution every other AI command uses, so Ask never sends more than they do);
* **the title** of the document;
* **the outline** -- its headings, in order.

Never the whole document: a passage plus the shape around it answers "what
does this paragraph mean" and "where does this belong" without sending a file
somebody did not choose to send (10C.3, "Never leaves the machine without a
yes").

wx-free and strict-typed. Both editors call :func:`ask_context` with their own
text, selection and caret, so neither has a copy.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.ai.gateway_context import _HEADING, resolve_scope

__all__ = ["AskFacts", "ask_context", "facts_block"]

#: The longest passage sent, in characters. A section can be a chapter; Ask is
#: a conversation about where the cursor is, not a way to send a book.
_PASSAGE_CHARS = 6000

#: The most headings the outline lists. Past this the outline stops helping
#: anyone place a paragraph and starts costing a request.
_OUTLINE_HEADINGS = 40

_SCOPE_WORDS = {
    "selection": "The selected text",
    "paragraph": "The paragraph the cursor is in",
    "section": "The section the cursor is in",
}


@dataclass(frozen=True, slots=True)
class AskFacts:
    """The named facts one turn of Ask sends."""

    scope: str
    passage: str
    title: str
    outline: tuple[str, ...]


def _outline(text: str) -> tuple[str, ...]:
    headings: list[str] = []
    for match in _HEADING.finditer(text):
        hashes, atx, setext, underline = match.groups()
        if atx:
            level = len(hashes)
            name = atx.strip()
        else:
            level = 1 if underline.startswith("=") else 2
            name = (setext or "").strip()
        if name:
            headings.append(f"{'  ' * (level - 1)}{name}")
        if len(headings) >= _OUTLINE_HEADINGS:
            break
    return tuple(headings)


def ask_context(text: str, selection: str, position: int, title: str = "") -> AskFacts:
    """The facts for one turn, read from the editor's text, selection and caret."""
    scope, passage = resolve_scope(text, selection, position)
    if len(passage) > _PASSAGE_CHARS:
        passage = passage[:_PASSAGE_CHARS].rstrip() + " ..."
    return AskFacts(scope=scope, passage=passage, title=title.strip(), outline=_outline(text))


def facts_block(facts: AskFacts) -> list[str]:
    """The facts as the excerpts a conversation sends with each message."""
    block: list[str] = []
    head: list[str] = []
    if facts.title:
        head.append(f"Document title: {facts.title}")
    if facts.outline:
        head.append("Outline:\n" + "\n".join(facts.outline))
    if head:
        block.append("\n".join(head))
    if facts.passage:
        lead = _SCOPE_WORDS.get(facts.scope, "The passage")
        block.append(f"{lead}:\n{facts.passage}")
    return block
