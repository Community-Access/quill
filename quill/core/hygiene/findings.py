"""Data structures for the Quill Eraser text hygiene checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class HygieneFinding:
    rule_id: str
    title: str
    description: str
    confidence: Literal["high", "medium", "low"]
    start_offset: int
    end_offset: int
    line: int  # 1-based
    column: int  # 0-based
    original_text: str
    suggested_text: str | None
    can_auto_fix: bool


@dataclass(frozen=True, slots=True)
class TextRange:
    start: int
    end: int

    def contains(self, offset: int) -> bool:
        return self.start <= offset < self.end

    def overlaps(self, start: int, end: int) -> bool:
        return self.start < end and start < self.end


@dataclass(frozen=True, slots=True)
class HygieneSettings:
    min_confidence: Literal["high", "medium", "low"] = "high"
    allow_double_space_after_period: bool = False
    max_blank_lines: int = 2
    rules_disabled: frozenset[str] = field(default_factory=frozenset)

    def is_rule_enabled(self, rule_id: str) -> bool:
        return rule_id not in self.rules_disabled

    def confidence_passes(self, confidence: Literal["high", "medium", "low"]) -> bool:
        order = {"high": 0, "medium": 1, "low": 2}
        return order[confidence] <= order[self.min_confidence]


@dataclass
class HygieneContext:
    text: str
    file_ext: str  # e.g. "py", "md", "txt", "" — lowercase, no dot
    scope_start: int
    scope_end: int
    ignored_ranges: list[TextRange]
    settings: HygieneSettings

    def is_in_ignored_range(self, start: int, end: int) -> bool:
        return any(r.overlaps(start, end) for r in self.ignored_ranges)

    def offset_to_line_col(self, offset: int) -> tuple[int, int]:
        """Return 1-based line and 0-based column for *offset*."""
        before = self.text[:offset]
        line = before.count("\n") + 1
        col = offset - before.rfind("\n") - 1
        return line, col
