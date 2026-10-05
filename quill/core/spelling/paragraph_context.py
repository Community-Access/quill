"""The "Full paragraph" choice for the F7 Context field (``spell_review_context_mode``).

The default Context is the sentence with the word plus one sentence either side
(:func:`quill.core.spelling.context_builder.build_context`). Some people would
rather hear the whole paragraph, so the setting offers it -- and until 2026-10
nothing read the setting. A paragraph here is what pressing Enter makes: the
text between the line breaks around the word, which is what a paragraph is in
both editors.

wx-free, strict-typed.
"""

from __future__ import annotations

#: The choice values, as Settings offers them.
CONTEXT_MODES: tuple[str, ...] = ("sentence", "paragraph")

#: A paragraph is usually short; this keeps a giant unbroken one readable.
PARAGRAPH_MAX_CHARS = 2000


def normalize_context_mode(value: object) -> str:
    """``"paragraph"`` when asked for, else the sentence default."""
    text = str(value or "").strip().lower()
    return text if text in CONTEXT_MODES else "sentence"


def paragraph_context(
    text: str,
    word_start: int,
    word_end: int,
    max_chars: int = PARAGRAPH_MAX_CHARS,
) -> tuple[str, int, int]:
    """Return (paragraph_text, word_start_in_ctx, word_end_in_ctx)."""
    if not text:
        return ("", 0, 0)
    start = text.rfind("\n", 0, word_start) + 1
    end = text.find("\n", word_end)
    if end == -1:
        end = len(text)
    raw = text[start:end]
    # Strip surrounding whitespace (a CR from CRLF included) without losing
    # the word's offsets.
    lead = len(raw) - len(raw.lstrip())
    context = raw.strip()
    ws = word_start - start - lead
    we = word_end - start - lead
    if len(context) > max_chars:
        half = max_chars // 2
        cut = max(0, min(ws - half, len(context) - max_chars))
        context = context[cut : cut + max_chars]
        ws -= cut
        we -= cut
    ws = max(0, min(ws, len(context)))
    we = max(ws, min(we, len(context)))
    return (context, ws, we)


__all__ = [
    "CONTEXT_MODES",
    "PARAGRAPH_MAX_CHARS",
    "normalize_context_mode",
    "paragraph_context",
]
