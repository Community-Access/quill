"""AI-powered grammar and style check for QUILL.

Sends document text to the configured AI provider and returns structured issues
with categories (grammar, punctuation, clarity, style, word choice).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from quill.core.ai.custom_instructions import split_instruction
from quill.core.assistant_ai import AssistantConnectionSettings, generate_assistant_response

_GRAMMAR_PROMPT_PREFIX = (
    "You are a professional editor. Analyze the text below for grammar, punctuation, "
    "clarity, style, and word choice issues. Return ONLY a JSON array.\n\n"
    "Each item must have:\n"
    '  "category": one of "grammar", "punctuation", "clarity", "style", "word_choice"\n'
    '  "original": the exact problematic text as it appears\n'
    '  "suggestion": the corrected or improved version\n'
    '  "explanation": one sentence explaining why this is an issue\n'
    '  "context": 40-char window surrounding the issue\n\n'
    "Focus on clear, actionable issues. Skip stylistic preferences unless they "
    "significantly harm readability. If no issues, return: []\n\n"
    "Return ONLY valid JSON. No explanation, no markdown fences.\n\n"
    "TEXT TO CHECK:\n"
)

_MAX_CHUNK_CHARS = 40_000

CATEGORIES: dict[str, str] = {
    "grammar": "Grammar",
    "punctuation": "Punctuation",
    "clarity": "Clarity",
    "style": "Style",
    "word_choice": "Word Choice",
}


class GrammarCheckError(Exception):
    pass


class GrammarCheckParseError(GrammarCheckError):
    pass


class GrammarCheckAuthError(GrammarCheckError):
    pass


@dataclass(frozen=True)
class GrammarIssue:
    category: str
    original: str
    suggestion: str
    explanation: str
    context: str

    @property
    def category_label(self) -> str:
        return CATEGORIES.get(self.category, self.category.replace("_", " ").title())


def ai_grammar_check(
    document_text: str,
    connection: AssistantConnectionSettings,
    api_key: str = "",
    categories: set[str] | None = None,
) -> list[GrammarIssue]:
    """Send *document_text* to the AI, return a list of grammar and style issues.

    *categories* filters results to the given category set. If None, all are returned.
    """
    if not document_text.strip():
        return []

    chunks = _chunk_document(document_text)
    all_issues: list[GrammarIssue] = []
    seen: set[tuple[str, str]] = set()

    for chunk in chunks:
        issues = _run_grammar_check_on_chunk(chunk, connection, api_key)
        for issue in issues:
            key = (issue.original, issue.context)
            if key not in seen:
                seen.add(key)
                if categories is None or issue.category in categories:
                    all_issues.append(issue)

    return all_issues


def _chunk_document(text: str) -> list[str]:
    if len(text) <= _MAX_CHUNK_CHARS:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= _MAX_CHUNK_CHARS:
            chunks.append(remaining)
            break
        split_pos = remaining.rfind("\n\n", 0, _MAX_CHUNK_CHARS)
        if split_pos > 0:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 2 :]
        else:
            split_pos = remaining.rfind(". ", 0, _MAX_CHUNK_CHARS)
            if split_pos > 0:
                chunks.append(remaining[: split_pos + 1])
                remaining = remaining[split_pos + 2 :]
            else:
                chunks.append(remaining[:_MAX_CHUNK_CHARS])
                remaining = remaining[_MAX_CHUNK_CHARS:]
    return [c for c in chunks if c.strip()]


def _run_grammar_check_on_chunk(
    text: str,
    connection: AssistantConnectionSettings,
    api_key: str,
) -> list[GrammarIssue]:
    system_prompt, user_prompt = split_instruction("grammar_check", _GRAMMAR_PROMPT_PREFIX + text)
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
            raise GrammarCheckAuthError(error)
        raise GrammarCheckError(error)
    if response is None:
        raise GrammarCheckError("AI returned no response.")
    return _parse_issues(response, text)


def _parse_issues(response: str, source_text: str) -> list[GrammarIssue]:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GrammarCheckParseError(f"AI returned non-JSON response: {response[:200]}") from exc

    if not isinstance(data, list):
        raise GrammarCheckParseError(f"Expected JSON array, got {type(data).__name__}")

    issues: list[GrammarIssue] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "grammar")).strip().lower()
        if category not in CATEGORIES:
            category = "grammar"
        original = str(item.get("original", "")).strip()
        suggestion = str(item.get("suggestion", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        context = str(item.get("context", "")).strip()
        if not original or not suggestion:
            continue
        if original not in source_text:
            continue
        issues.append(
            GrammarIssue(
                category=category,
                original=original,
                suggestion=suggestion,
                explanation=explanation,
                context=context,
            )
        )

    return issues


def apply_grammar_fixes(
    document_text: str,
    issues: list[GrammarIssue],
    accepted: set[int],
) -> tuple[str, int]:
    """Apply accepted grammar fixes by index (reverse order to preserve offsets)."""
    to_apply = [issues[i] for i in sorted(accepted, reverse=True) if i < len(issues)]
    result = document_text
    applied = 0
    for issue in to_apply:
        if issue.original in result:
            result = result.replace(issue.original, issue.suggestion, 1)
            applied += 1
    return result, applied
