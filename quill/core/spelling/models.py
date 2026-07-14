"""Data classes for the F7 spelling review session."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ActionKind(StrEnum):
    CHANGE = "change"
    CHANGE_ALL = "change_all"
    IGNORE_ONCE = "ignore_once"
    IGNORE_ALL = "ignore_all"
    ADD_TO_DICT = "add_to_dict"


@dataclass(frozen=True, slots=True)
class SpellingIssue:
    word: str
    doc_start: int
    doc_end: int
    context_text: str
    context_word_start: int
    context_word_end: int
    suggestions: tuple[str, ...]


@dataclass
class ReviewCounters:
    reviewed: int = 0
    changed: int = 0
    changed_all: int = 0
    ignored_once: int = 0
    ignored_all: int = 0
    added_to_dict: int = 0


@dataclass
class ReviewAction:
    kind: ActionKind
    word: str
    replacement: str = ""
    doc_start: int = 0
    doc_end_before: int = 0
    doc_end_after: int = 0
    all_ranges: list[tuple[int, int, int]] = field(default_factory=list)
    scope: str = ""
