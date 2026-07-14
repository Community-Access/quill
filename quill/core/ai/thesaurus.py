"""AI-powered thesaurus for QUILL.

Sends the selected word (and optional sentence context) to the configured AI
provider and returns a list of synonyms with brief usage notes. The result is
a list of ThesaurusEntry objects, one per synonym, ranked roughly by similarity.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.core.ai.custom_instructions import split_instruction
from quill.core.assistant_ai import generate_assistant_response
from quill.core.error_codes import CodedError

if TYPE_CHECKING:
    from quill.core.assistant_ai import AssistantConnectionSettings

_MAX_WORD_CHARS = 80
_MAX_CONTEXT_CHARS = 400

_PROMPT_TEMPLATE = """\
You are a professional thesaurus. The user wants synonyms for the word or phrase "{word}".
{context_line}
Return a JSON array (no other text) where each element has:
  "synonym": the alternative word or phrase,
  "note": a very brief usage note (1 sentence, <=15 words) about how meaning differs.

Provide 6-10 synonyms, ordered from most to least similar in meaning.
Example format:
[{{"synonym": "happy", "note": "General positive emotion, interchangeable in most contexts."}}]
"""


@dataclass(frozen=True, slots=True)
class ThesaurusEntry:
    synonym: str
    note: str


class ThesaurusError(CodedError):
    code = "QUILL-AI-THESAURUS-FAILED"


class ThesaurusAuthError(ThesaurusError):
    pass


class ThesaurusEmptyError(ThesaurusError):
    pass


def get_synonyms(
    word: str,
    connection: AssistantConnectionSettings,
    api_key: str = "",
    context_sentence: str = "",
) -> list[ThesaurusEntry]:
    """Return a list of ThesaurusEntry for *word*.

    Parameters
    ----------
    word:
        The word or short phrase to look up (stripped to _MAX_WORD_CHARS).
    connection:
        AssistantConnectionSettings for the configured provider.
    api_key:
        Provider API key (empty for on-device models).
    context_sentence:
        Optional sentence in which the word appears, used to disambiguate
        meaning (e.g. "bank" has different synonyms in financial vs. river contexts).
    """
    word = word.strip()[:_MAX_WORD_CHARS]
    if not word:
        raise ThesaurusEmptyError("No word provided.")

    ctx = context_sentence.strip()[:_MAX_CONTEXT_CHARS]
    context_line = f'The word appears in this sentence: "{ctx}"' if ctx else ""
    system_prompt, user_prompt = split_instruction(
        "thesaurus",
        _PROMPT_TEMPLATE.format(word=word, context_line=context_line),
    )

    text, error = generate_assistant_response(
        connection,
        api_key,
        user_prompt,
        max_tokens=512,
        system_prompt=system_prompt,
        timeout_seconds=30.0,
    )

    if error:
        if "401" in error or "auth" in error.lower() or "key" in error.lower():
            raise ThesaurusAuthError(error)
        raise ThesaurusError(error)

    return _parse_response(text or "")


def _parse_response(text: str) -> list[ThesaurusEntry]:
    # Strip markdown fences if the model wrapped the JSON
    cleaned = re.sub(r"```[a-z]*\n?", "", text).strip()

    # Find the JSON array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return []

    results = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            synonym = str(item.get("synonym", "")).strip()
            note = str(item.get("note", "")).strip()
            if synonym:
                results.append(ThesaurusEntry(synonym=synonym, note=note))

    return results
