"""Suggest document metadata (title, summary, tags, category) via the AI.

The first consumer of the field-by-field apply flow
(:mod:`quill.core.ai.field_apply`): ask the configured provider for front
matter values, parse the JSON defensively (models drift into code fences and
preambles), and hand back plain :class:`FieldSuggestion` rows for review.
Nothing here writes to the document. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re

from quill.core.ai.field_apply import FieldSuggestion
from quill.core.assistant_ai import AssistantConnectionSettings, generate_assistant_response
from quill.core.error_codes import CodedError

__all__ = ["MetadataSuggestError", "suggest_document_metadata"]

_MAX_DOC_CHARS = 20_000

_PROMPT = (
    "Read the document and propose metadata for it. Respond with ONLY a JSON "
    "object, no preamble and no code fence, with exactly these keys:\n"
    '  "title": a concise title (under 80 characters),\n'
    '  "summary": one or two sentences describing the document,\n'
    '  "tags": an array of 3 to 6 short lowercase topic tags,\n'
    '  "category": one short category word or phrase.\n\n'
    "DOCUMENT:\n{document}"
)


class MetadataSuggestError(CodedError):
    code = "QUILL-AI-METADATA-FAILED"
    user_hint = "Check your AI provider and key in the AI Hub, or switch to a local model."


def _extract_json(text: str) -> dict[str, object]:
    """Parse a model reply into a dict, tolerating fences and preambles."""
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip("` \n")
    try:
        parsed = json.loads(cleaned)
    except ValueError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise MetadataSuggestError("The AI reply was not valid JSON.") from None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except ValueError as exc:
            raise MetadataSuggestError("The AI reply was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise MetadataSuggestError("The AI reply was not a JSON object.")
    return parsed


def suggest_document_metadata(
    document_text: str,
    connection: AssistantConnectionSettings,
    api_key: str = "",
) -> list[FieldSuggestion]:
    """Ask the AI for metadata suggestions; raises MetadataSuggestError on failure."""
    document = (document_text or "").strip()
    if not document:
        raise MetadataSuggestError("The document is empty - nothing to describe.")
    response, error = generate_assistant_response(
        connection,
        api_key,
        _PROMPT.format(document=document[:_MAX_DOC_CHARS]),
        max_tokens=512,
        timeout_seconds=90.0,
    )
    if error:
        raise MetadataSuggestError(error)
    if not response:
        raise MetadataSuggestError("The AI returned no response.")
    data = _extract_json(response)
    suggestions: list[FieldSuggestion] = []
    for key in ("title", "summary", "category"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            suggestions.append(FieldSuggestion(field=key, value=value.strip()))
    tags = data.get("tags")
    if isinstance(tags, list):
        cleaned_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        if cleaned_tags:
            suggestions.append(FieldSuggestion(field="tags", value=", ".join(cleaned_tags)))
    if not suggestions:
        raise MetadataSuggestError("The AI reply contained no usable metadata fields.")
    return suggestions
