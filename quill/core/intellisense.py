from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.spellcheck import suggest_words
from quill.core.tagging import (
    build_markdown_insertion,
    search_html_tag_choices,
    search_markdown_tag_choices,
)

_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z']*")


@dataclass(frozen=True, slots=True)
class IntellisenseContext:
    replacement_start: int
    replacement_end: int
    fragment: str
    mode: str


@dataclass(frozen=True, slots=True)
class IntellisenseSuggestion:
    label: str
    inserted_text: str
    caret_offset: int
    kind: str


def collect_document_words(text: str) -> set[str]:
    return {match.group(0).lower() for match in _WORD_PATTERN.finditer(text)}


def extract_intellisense_context(text: str, cursor: int) -> IntellisenseContext | None:
    if cursor < 0 or cursor > len(text):
        return None
    line_start = text.rfind("\n", 0, cursor) + 1
    line_prefix = text[line_start:cursor]

    html_marker = line_prefix.rfind("<")
    if html_marker >= 0:
        after_marker = line_prefix[html_marker + 1 :]
        if ">" not in after_marker:
            replacement_start = line_start + html_marker + 1
            if (
                replacement_start < cursor
                and text[replacement_start : replacement_start + 1] == "/"
            ):
                replacement_start += 1
            fragment = text[replacement_start:cursor]
            return IntellisenseContext(
                replacement_start=replacement_start,
                replacement_end=cursor,
                fragment=fragment,
                mode="html",
            )

    replacement_start = cursor
    while replacement_start > line_start and _is_word_character(text[replacement_start - 1]):
        replacement_start -= 1
    fragment = text[replacement_start:cursor]
    if not fragment:
        return None
    return IntellisenseContext(
        replacement_start=replacement_start,
        replacement_end=cursor,
        fragment=fragment,
        mode="word",
    )


def build_intellisense_suggestions(
    text: str,
    cursor: int,
    dictionary: set[str],
    *,
    limit: int = 8,
) -> tuple[IntellisenseContext | None, list[IntellisenseSuggestion]]:
    context = extract_intellisense_context(text, cursor)
    if context is None:
        return None, []

    fragment = context.fragment.strip()
    if not fragment:
        return context, []

    suggestions: list[IntellisenseSuggestion] = []
    seen: set[tuple[str, str]] = set()

    def add_suggestion(kind: str, label: str, inserted_text: str, caret_offset: int) -> None:
        key = (kind, inserted_text.lower())
        if key in seen:
            return
        seen.add(key)
        suggestions.append(
            IntellisenseSuggestion(
                label=label,
                inserted_text=inserted_text,
                caret_offset=caret_offset,
                kind=kind,
            )
        )

    if context.mode == "html":
        for tag in search_html_tag_choices(fragment):
            add_suggestion(
                "html",
                f"HTML tag: {tag}",
                f"{tag}>",
                len(tag) + 1,
            )

    for choice in search_markdown_tag_choices(fragment):
        result = build_markdown_insertion(choice, "")
        add_suggestion(
            "markdown",
            f"Markdown: {choice}",
            result.inserted_text,
            result.caret_offset,
        )

    for word in suggest_words(fragment, dictionary, limit=limit):
        # Label is just the word: word predictions dominate the list, so a
        # "Word: " prefix makes a screen reader announce "Word" before every
        # item when arrowing. The kind ("word") still distinguishes it; the
        # rarer HTML/Markdown suggestions keep their prefixes to disambiguate.
        add_suggestion("word", word, word, len(word))

    return context, suggestions[:limit]


def _is_word_character(character: str) -> bool:
    return character.isalpha() or character == "'"
