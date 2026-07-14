"""Built-in hygiene rules for Quill Eraser."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Literal

from quill.core.hygiene.findings import HygieneContext, HygieneFinding


class HygieneRule(ABC):
    id: str
    name: str
    description: str
    default_enabled: bool = True

    @abstractmethod
    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]: ...

    def _finding(
        self,
        text: str,
        context: HygieneContext,
        start: int,
        end: int,
        title: str,
        description: str,
        confidence: Literal["high", "medium", "low"],
        suggested_text: str | None,
    ) -> HygieneFinding:
        line, col = context.offset_to_line_col(start)
        return HygieneFinding(
            rule_id=self.id,
            title=title,
            description=description,
            confidence=confidence,
            start_offset=start,
            end_offset=end,
            line=line,
            column=col,
            original_text=text[start:end],
            suggested_text=suggested_text,
            can_auto_fix=suggested_text is not None,
        )


# ---------------------------------------------------------------------------
# Rule 1: Multiple spaces between words
# ---------------------------------------------------------------------------


class MultipleSpacesRule(HygieneRule):
    id = "prose.multiple_spaces"
    name = "Multiple spaces between words"
    description = "Two or more spaces between words in prose."
    _PATTERN = re.compile(r"(?<=[^\s\n])([ \t]{2,})(?=[^\s\n])")

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        findings = []
        for m in self._PATTERN.finditer(text):
            start, end = m.start(), m.end()
            if context.is_in_ignored_range(start, end):
                continue
            if (
                context.settings.allow_double_space_after_period
                and start > 0
                and text[start - 1] in ".!?"
                and end - start == 2
            ):
                continue
            n = end - start
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    "Multiple spaces between words",
                    f"Found {n} spaces; expected one.",
                    "high",
                    " ",
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Rule 2: Trailing spaces at end of line
# ---------------------------------------------------------------------------


class TrailingSpacesRule(HygieneRule):
    id = "prose.trailing_spaces"
    name = "Trailing spaces at end of line"
    description = "Spaces or tabs at the end of a line."
    _PATTERN = re.compile(r"[ \t]+(?=\n|$)")

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        findings = []
        for m in self._PATTERN.finditer(text):
            start, end = m.start(), m.end()
            if context.is_in_ignored_range(start, end):
                continue
            n = end - start
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    "Trailing spaces at end of line",
                    f"Found {n} trailing space{'s' if n != 1 else ''} at end of line.",
                    "high",
                    "",
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Rule 3: Space before punctuation
# ---------------------------------------------------------------------------


class SpaceBeforePunctuationRule(HygieneRule):
    id = "prose.space_before_punctuation"
    name = "Space before punctuation"
    description = "One or more spaces immediately before punctuation."
    _PATTERN = re.compile(r"[ \t]+([,\.!?;:])")

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        findings = []
        for m in self._PATTERN.finditer(text):
            start, end = m.start(), m.end()
            if context.is_in_ignored_range(start, end):
                continue
            punct = m.group(1)
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    f"Space before '{punct}'",
                    f"Found space before '{punct}'. Expected no space.",
                    "high",
                    punct,
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Rule 4: Missing space after sentence-ending punctuation
# ---------------------------------------------------------------------------


class MissingSpaceAfterSentencePunctuationRule(HygieneRule):
    id = "prose.missing_space_after_sentence_punct"
    name = "Missing space after sentence punctuation"
    description = "Sentence-ending punctuation not followed by a space."
    # Require lowercase before period (avoids abbreviation `U.S.Army`)
    _PATTERN = re.compile(r"(?<=[a-z0-9\])])[.!?](?=[A-Za-z])")

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        findings = []
        for m in self._PATTERN.finditer(text):
            start = m.start() + 1  # position of the letter (no space)
            end = m.end()
            match_start = m.start()
            if context.is_in_ignored_range(match_start, end):
                continue
            punct = text[match_start]
            findings.append(
                self._finding(
                    text,
                    context,
                    match_start,
                    end,
                    f"Missing space after '{punct}'",
                    f"Found '{punct}' directly followed by a letter. Expected a space.",
                    "medium",
                    text[match_start] + " " + text[start:end],
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Rule 5: Missing space after comma, semicolon, or colon
# ---------------------------------------------------------------------------


class MissingSpaceAfterCommaRule(HygieneRule):
    id = "prose.missing_space_after_comma"
    name = "Missing space after comma, semicolon, or colon"
    description = "Comma, semicolon, or colon directly followed by a letter."
    _PATTERN = re.compile(r"([,;:])(?=[A-Za-z])")

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        findings = []
        for m in self._PATTERN.finditer(text):
            start, end = m.start(), m.end()
            if context.is_in_ignored_range(start, end):
                continue
            punct = m.group(1)
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    f"Missing space after '{punct}'",
                    f"Found '{punct}' directly followed by a letter.",
                    "medium",
                    punct + " " + text[end - 1],
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Rule 6: Excessive blank lines
# ---------------------------------------------------------------------------


class ExcessiveBlankLinesRule(HygieneRule):
    id = "prose.excessive_blank_lines"
    name = "Excessive blank lines"
    description = "More consecutive blank lines than the configured maximum."

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        threshold = context.settings.max_blank_lines
        # (threshold + 1) blank lines = (threshold + 2) newline chars in a row
        repeat = threshold + 2
        pattern = re.compile(r"(\n[ \t]*){" + str(repeat) + r",}")
        findings = []
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            if context.is_in_ignored_range(start, end):
                continue
            n = m.group(0).count("\n") - 1
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    "Excessive blank lines",
                    f"Found {n} consecutive blank lines; maximum is {threshold}.",
                    "high",
                    "\n" * (threshold + 1),
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Rule 7: Sentence starts with lowercase letter
# ---------------------------------------------------------------------------


class LowercaseSentenceStartRule(HygieneRule):
    id = "prose.lowercase_sentence_start"
    name = "Sentence starts with lowercase letter"
    description = "A sentence appears to begin with a lowercase letter."
    # After `. `, `! `, `? ` (space present) a lowercase letter follows
    _AFTER_PUNCT = re.compile(r"(?<=[.!?] )([a-z])")
    # After a blank line (paragraph start)
    _PARA_START = re.compile(r"(?:\n\n[ \t]*)([a-z])")

    def check(self, text: str, context: HygieneContext) -> list[HygieneFinding]:
        findings: list[HygieneFinding] = []
        for m in self._AFTER_PUNCT.finditer(text):
            start = m.start(1)
            end = m.end(1)
            if context.is_in_ignored_range(start, end):
                continue
            char = m.group(1)
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    "Sentence starts with lowercase letter",
                    f"Sentence appears to start with lowercase '{char}'.",
                    "medium",
                    char.upper(),
                )
            )
        for m in self._PARA_START.finditer(text):
            start = m.start(1)
            end = m.end(1)
            if context.is_in_ignored_range(start, end):
                continue
            char = m.group(1)
            findings.append(
                self._finding(
                    text,
                    context,
                    start,
                    end,
                    "Paragraph starts with lowercase letter",
                    f"Paragraph appears to start with lowercase '{char}'.",
                    "medium",
                    char.upper(),
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILTIN_RULES: tuple[HygieneRule, ...] = (
    MultipleSpacesRule(),
    TrailingSpacesRule(),
    SpaceBeforePunctuationRule(),
    MissingSpaceAfterSentencePunctuationRule(),
    MissingSpaceAfterCommaRule(),
    ExcessiveBlankLinesRule(),
    LowercaseSentenceStartRule(),
)
