"""Large-document context handling (PRD §11, §3 large-doc): chunk, slice, summarize.

When an agent works on a whole document, the document may exceed a model's context
window. These wx-free, deterministic helpers let the platform deal with the
document in focus completely:

- :func:`chunk_text` splits a document into paragraph-aligned chunks under a token
  budget (so a long document can be processed piece by piece).
- :func:`section_text` extracts one outline section's text (for section-scoped
  agents that preview/edit per heading instead of rewriting the whole file).
- :func:`structured_summary` produces a compact, structure-aware summary (heading
  list + per-paragraph leading excerpts) that fits a budget — a better
  "document_summary" context than a flat truncation.

Token counts reuse the tokenizer-free estimate in :mod:`quill.core.ai.compaction`.
"""

from __future__ import annotations

from quill.core.ai.compaction import estimate_tokens
from quill.core.outline import OutlineEntry

__all__ = ["chunk_text", "section_text", "structured_summary"]


def _paragraphs(text: str) -> list[str]:
    """Split into paragraphs on blank lines, preserving non-empty blocks."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _hard_split(block: str, max_tokens: int) -> list[str]:
    """Split a single over-budget block on word boundaries to fit the budget."""
    words = block.split(" ")
    out: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if estimate_tokens(" ".join(current)) >= max_tokens:
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def chunk_text(text: str, *, max_tokens: int = 2000) -> list[str]:
    """Return paragraph-aligned chunks each at or under ``max_tokens``.

    Paragraphs are kept whole where possible; a single paragraph larger than the
    budget is split on word boundaries. Empty input yields an empty list. The
    concatenation of chunks preserves all non-whitespace content.
    """
    if not text.strip():
        return []
    max_tokens = max(1, max_tokens)
    chunks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            chunks.append("\n\n".join(current))
            current.clear()

    for block in _paragraphs(text):
        if estimate_tokens(block) > max_tokens:
            flush()
            chunks.extend(_hard_split(block, max_tokens))
            continue
        tentative = "\n\n".join([*current, block])
        if current and estimate_tokens(tentative) > max_tokens:
            flush()
        current.append(block)
    flush()
    return chunks


def section_text(document: str, outline: list[OutlineEntry], index: int) -> str:
    """Return the text of the outline section at ``index`` (heading -> next heading).

    ``outline`` is the document's :class:`OutlineEntry` list (with character
    ``position``s). The slice runs from this heading's position to the next
    heading's position (or end of document). Raises ``IndexError`` for a bad index.
    """
    if not 0 <= index < len(outline):
        raise IndexError(f"Section index {index} out of range (0..{len(outline) - 1}).")
    ordered = sorted(outline, key=lambda e: e.position)
    start = ordered[index].position
    end = ordered[index + 1].position if index + 1 < len(ordered) else len(document)
    return document[start:end].strip()


def structured_summary(
    text: str, *, max_tokens: int = 600, outline_titles: list[str] | None = None
) -> str:
    """Return a compact, structure-aware summary that fits ``max_tokens``.

    Includes the heading list (when provided) and the leading excerpt of each
    paragraph, added until the token budget is reached. Deterministic and
    tokenizer-free; a model-backed summary can replace the body later without
    changing the contract. Guaranteed no larger than the source.
    """
    parts: list[str] = []
    if outline_titles:
        parts.append("Headings: " + "; ".join(t for t in outline_titles if t.strip()))

    budget = max(1, max_tokens)
    for block in _paragraphs(text):
        first_line = block.split("\n", 1)[0].strip()
        excerpt = first_line[:200]
        candidate = parts + [excerpt]
        if estimate_tokens("\n".join(candidate)) > budget:
            break
        parts.append(excerpt)

    summary = "\n".join(parts)
    # Never return something larger than the source.
    return summary if len(summary) <= len(text) or not text else text
