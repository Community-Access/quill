"""Translate a document's sections for translated audio export (roadmap §7).

Given the heading-bounded sections from :func:`text_polish.extract_sections`,
translate each section's title and body into a target language, then hand the
translated sections to the normal chaptered/separate synthesis path. wx-free.

The single-string translator is **injected** (a closure the caller builds over
``quill.core.ai.translation.translate_text`` with the user's configured AI provider
or LibreTranslate), so this module is provider-neutral and unit-testable. It adds
the robustness the ACB reference pipeline used:

- **bounded retries with exponential backoff** per string,
- **halt-this-language on persistent failure** (raise rather than emit
  half-translated audio), and
- a **cache** so identical strings (e.g. a repeated heading) are translated once.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from quill.core.error_codes import CodedError
from quill.core.speech.text_polish import DocumentSection

#: A translator: ``translate(text) -> translated_text``; may raise on failure.
Translator = Callable[[str], str]


class SectionTranslationError(CodedError):
    """A section could not be translated after all retries (halt this language)."""

    code = "QUILL-SPEECH-SECTION-TRANSLATE"


def _translate_one(
    text: str,
    translate: Translator,
    cache: dict[str, str],
    *,
    max_retries: int,
    backoff_base: float,
    backoff_max: float,
    sleep: Callable[[float], None],
) -> str:
    """Translate *text* with caching + bounded exponential backoff; raise on failure."""
    stripped = text.strip()
    if not stripped:
        return text
    if stripped in cache:
        return cache[stripped]
    backoff = backoff_base
    last_error: Exception | None = None
    for attempt in range(1, max(1, max_retries) + 1):
        try:
            result = translate(stripped)
        except Exception as exc:  # noqa: BLE001 - any provider error retries then halts
            last_error = exc
            if attempt < max_retries:
                sleep(min(backoff, backoff_max))
                backoff *= 2
            continue
        if result and result.strip():
            cache[stripped] = result
            return result
        last_error = last_error or SectionTranslationError("empty translation")
        if attempt < max_retries:
            sleep(min(backoff, backoff_max))
            backoff *= 2
    raise SectionTranslationError(
        f"Translation failed after {max_retries} attempt(s): {last_error}"
    )


def translate_sections(
    sections: list[DocumentSection],
    translate: Translator,
    *,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    backoff_max: float = 10.0,
    sleep: Callable[[float], None] = time.sleep,
) -> list[DocumentSection]:
    """Return *sections* with each title and body translated via *translate*.

    Titles and bodies are translated independently (so chapter markers stay coherent)
    and cached. Raises :class:`SectionTranslationError` if any string cannot be
    translated after the retries — the caller halts that language rather than
    producing a partially-translated file.
    """
    cache: dict[str, str] = {}

    def _t(text: str) -> str:
        return _translate_one(
            text,
            translate,
            cache,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
            sleep=sleep,
        )

    return [DocumentSection(title=_t(s.title), text=_t(s.text)) for s in sections]
