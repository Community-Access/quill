"""AI-powered spell check for QUILL.

Sends document text to the configured AI provider and returns a structured list
of spelling corrections. Uses the same provider infrastructure as the writing
assistant (AssistantConnectionSettings, _post_chat).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from quill.core.ai.custom_instructions import split_instruction
from quill.core.assistant_ai import AssistantConnectionSettings, generate_assistant_response
from quill.core.error_codes import CodedError

_SPELL_CHECK_PROMPT_PREFIX = (
    "You are a professional copy editor. Find all spelling errors in the text below. "
    "Return ONLY a JSON array and nothing else.\n\n"
    "Each item must have:\n"
    '  "original": exact misspelled text as it appears\n'
    '  "correction": correct spelling\n'
    '  "context": 40-char window surrounding the error (for disambiguation)\n\n'
    "Only report genuine spelling errors - not style choices, proper nouns, or "
    "technical terms correct in context. If no errors, return: []\n\n"
    "Return ONLY valid JSON. No explanation, no markdown fences.\n\n"
    "TEXT TO CHECK:\n"
)

_MAX_CHUNK_CHARS = 60_000  # safe under most model context windows


class SpellCheckError(CodedError):
    code = "QUILL-AI-SPELLCHECK-FAILED"


class SpellCheckParseError(SpellCheckError):
    pass


class SpellCheckAuthError(SpellCheckError):
    pass


@dataclass(frozen=True)
class SpellCorrection:
    original: str
    correction: str
    context: str


def ai_spell_check(
    document_text: str,
    connection: AssistantConnectionSettings,
    api_key: str = "",
) -> list[SpellCorrection]:
    """Send *document_text* to the AI, return a list of spelling corrections.

    For large documents, splits into chunks and merges results, deduplicating
    by (original, context) pair.

    Raises SpellCheckParseError if the response is not valid JSON.
    Raises SpellCheckAuthError on authentication failure.
    """
    if not document_text.strip():
        return []

    chunks = _chunk_document(document_text)
    all_corrections: list[SpellCorrection] = []
    seen: set[tuple[str, str]] = set()

    for chunk in chunks:
        raw = _run_spell_check_on_chunk(chunk, connection, api_key)
        for item in raw:
            key = (item.original, item.context)
            if key not in seen:
                seen.add(key)
                all_corrections.append(item)

    return all_corrections


def _chunk_document(text: str) -> list[str]:
    if len(text) <= _MAX_CHUNK_CHARS:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= _MAX_CHUNK_CHARS:
            chunks.append(remaining)
            break
        # Split at paragraph boundary
        split_pos = remaining.rfind("\n\n", 0, _MAX_CHUNK_CHARS)
        if split_pos > 0:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 2 :]
        else:
            # Fall back to sentence boundary
            split_pos = remaining.rfind(". ", 0, _MAX_CHUNK_CHARS)
            if split_pos > 0:
                chunks.append(remaining[: split_pos + 1])
                remaining = remaining[split_pos + 2 :]
            else:
                chunks.append(remaining[:_MAX_CHUNK_CHARS])
                remaining = remaining[_MAX_CHUNK_CHARS:]
    return [c for c in chunks if c.strip()]


def _run_spell_check_on_chunk(
    text: str,
    connection: AssistantConnectionSettings,
    api_key: str,
) -> list[SpellCorrection]:
    system_prompt, user_prompt = split_instruction("spell_check", _SPELL_CHECK_PROMPT_PREFIX + text)
    response, error = generate_assistant_response(
        connection,
        api_key,
        user_prompt,
        max_tokens=4096,
        timeout_seconds=120.0,
        system_prompt=system_prompt,
    )
    if error:
        msg = error.lower()
        if "auth" in msg or "401" in msg or "api key" in msg:
            raise SpellCheckAuthError(error)
        raise SpellCheckError(error)
    if response is None:
        raise SpellCheckError("AI returned no response.")
    return _parse_corrections(response, text)


def _parse_corrections(response: str, source_text: str) -> list[SpellCorrection]:
    """Parse the AI JSON response into SpellCorrection objects."""
    # Strip markdown code fences if present
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SpellCheckParseError(f"AI returned non-JSON response: {response[:200]}") from exc

    if not isinstance(data, list):
        raise SpellCheckParseError(f"Expected JSON array, got {type(data).__name__}")

    corrections: list[SpellCorrection] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        original = str(item.get("original", "")).strip()
        correction = str(item.get("correction", "")).strip()
        context = str(item.get("context", "")).strip()
        if not original or not correction or original == correction:
            continue
        # Verify the original actually exists in the source text
        if original not in source_text:
            continue
        corrections.append(
            SpellCorrection(
                original=original,
                correction=correction,
                context=context,
            )
        )

    return corrections


def apply_corrections(
    document_text: str,
    corrections: list[SpellCorrection],
) -> tuple[str, int]:
    """Apply *corrections* to *document_text*.

    Uses context-aware matching when a word appears multiple times.
    Applies in reverse position order to preserve earlier offsets.
    Returns (corrected_text, applied_count).
    """
    if not corrections:
        return document_text, 0

    # Find all positions for each correction using context
    replacements: list[tuple[int, int, str]] = []  # (start, end, replacement)

    for corr in corrections:
        positions = _find_positions(document_text, corr)
        for start, end in positions:
            replacements.append((start, end, corr.correction))

    if not replacements:
        return document_text, 0

    # Sort in reverse order and apply
    replacements.sort(key=lambda r: r[0], reverse=True)
    result = document_text
    applied = 0
    for start, end, replacement in replacements:
        result = result[:start] + replacement + result[end:]
        applied += 1

    return result, applied


def _find_positions(text: str, corr: SpellCorrection) -> list[tuple[int, int]]:
    """Find occurrence positions of corr.original in text, using context to disambiguate."""
    original = corr.original
    context = corr.context
    positions: list[tuple[int, int]] = []

    start = 0
    while True:
        pos = text.find(original, start)
        if pos == -1:
            break
        end = pos + len(original)

        if context:
            # Check if context matches around this occurrence
            ctx_start = max(0, pos - 20)
            ctx_end = min(len(text), end + 20)
            surrounding = text[ctx_start:ctx_end]
            if context in surrounding:
                positions.append((pos, end))
        else:
            positions.append((pos, end))

        start = end

    # If context matching found nothing, fall back to first occurrence only
    if not positions and original in text:
        pos = text.find(original)
        positions.append((pos, pos + len(original)))

    return positions[:1]  # Only replace first matching occurrence per correction
