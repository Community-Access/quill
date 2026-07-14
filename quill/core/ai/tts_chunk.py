"""Boundary-safe text chunking for cloud TTS (OpenAI, Gemini).

Cloud TTS endpoints cap the characters per request, so long documents must be
split before synthesis. The split must never end a chunk on a "weird spot" -- a
mid-word or mid-sentence break makes the synthesized audio clip or trail off
oddly. This splitter (learned from the git-going-with-github Kokoro audiobook
generator) groups whole sentences under the limit and only ever falls back to a
word boundary for a single sentence that is itself longer than the limit; it
never splits inside a word.

It also normalizes runs of whitespace so stray newlines in the source do not
turn into unnatural pauses or waste characters against the per-request cap, while
preserving paragraph breaks as preferred split points for natural phrasing.
"""

from __future__ import annotations

import re

# A sentence ends at . ! ? (optionally followed by closing quotes/brackets) when
# the next character is whitespace or end-of-text.
_SENTENCE_END = re.compile(r'[.!?]["\')\]]*(?=\s|$)')
_PARAGRAPH = re.compile(r"\n\s*\n+")
_WHITESPACE = re.compile(r"[^\S\n]+")  # runs of spaces/tabs, but not newlines


def _normalize(text: str) -> str:
    """Collapse intra-line whitespace runs to single spaces; trim line edges."""
    lines = [_WHITESPACE.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(lines)


def _sentences(text: str) -> list[str]:
    """Split one paragraph into sentences, keeping terminal punctuation."""
    text = _WHITESPACE.sub(" ", text.replace("\n", " ")).strip()
    if not text:
        return []
    sentences: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        end = match.end()
        sentences.append(text[start:end].strip())
        start = end
    remainder = text[start:].strip()
    if remainder:
        sentences.append(remainder)
    return sentences or [text]


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Split a single over-long sentence at word boundaries (never mid-word)."""
    parts: list[str] = []
    current = ""
    for word in sentence.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            parts.append(current)
            current = word
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split *text* into chunks of at most *max_chars*, on natural boundaries.

    Priority: paragraph break, then sentence boundary, then (only for a sentence
    longer than ``max_chars``) word boundary. A chunk never ends inside a word,
    and ends on a sentence boundary whenever the sentence fits.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    normalized = _normalize(text).strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [_WHITESPACE.sub(" ", normalized.replace("\n", " ")).strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in _PARAGRAPH.split(normalized):
        for sentence in _sentences(paragraph):
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_split_long_sentence(sentence, max_chars))
                continue
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > max_chars and current:
                chunks.append(current)
                current = sentence
            else:
                current = candidate
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]
