"""Boxer-style compare engine for QUILL (issues #193/#194).

Pure Python — no wx imports. Provides structured difference navigation
and speech-ready summaries. The UI layer (compare_dialog.py) calls this;
no diff computation happens on the UI thread.

Architecture:
  CompareOptions  — whitespace / case settings
  InlineChange    — character-span change within a line
  DifferenceGroup — one logical diff hunk with navigation metadata
  CompareService  — runs the diff, owns navigation state
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class CompareOptions:
    """Controls how two texts are compared."""

    ignore_trailing_whitespace: bool = False
    ignore_leading_trailing_whitespace: bool = False
    ignore_all_whitespace: bool = False
    ignore_line_endings: bool = True
    case_sensitive: bool = True


@dataclass(frozen=True, slots=True)
class InlineChange:
    """A character-level span within a single replaced line."""

    left_start: int
    left_end: int
    right_start: int
    right_end: int
    left_text: str
    right_text: str


@dataclass
class DifferenceGroup:
    """One logical hunk of differences between left and right files."""

    index: int  # 1-based position in the sequence
    total: int  # total number of groups
    kind: Literal["insert", "delete", "replace", "whitespace", "line_ending"]
    left_start_line: int | None  # 1-based, None for pure insertions
    left_end_line: int | None
    right_start_line: int | None  # 1-based, None for pure deletions
    right_end_line: int | None
    left_text: list[str]
    right_text: list[str]
    inline_spans: list[InlineChange] = field(default_factory=list)
    summary_short: str = ""
    summary_verbose: str = ""


def _normalize_line(line: str, opts: CompareOptions) -> str:
    if opts.ignore_all_whitespace:
        return re.sub(r"\s+", "", line)
    if opts.ignore_leading_trailing_whitespace:
        return line.strip()
    if opts.ignore_trailing_whitespace:
        return line.rstrip()
    if opts.ignore_line_endings:
        return line.rstrip("\r\n")
    return line


def _classify_hunk(
    left_lines: list[str],
    right_lines: list[str],
    opts: CompareOptions,
) -> Literal["insert", "delete", "replace", "whitespace", "line_ending"]:
    if not left_lines:
        return "insert"
    if not right_lines:
        return "delete"
    # Chunks arrive with \r\n already stripped. Classify as "whitespace" when
    # the only differences are spaces/tabs (leading, trailing, or amount).
    stripped_left = [re.sub(r"\s+", " ", ln.strip()) for ln in left_lines]
    stripped_right = [re.sub(r"\s+", " ", ln.strip()) for ln in right_lines]
    if stripped_left == stripped_right:
        return "whitespace"
    return "replace"


def _build_inline_spans(left_line: str, right_line: str) -> list[InlineChange]:
    """Character-level diff between two single lines."""
    matcher = difflib.SequenceMatcher(None, left_line, right_line, autojunk=False)
    spans: list[InlineChange] = []
    for tag, l0, l1, r0, r1 in matcher.get_opcodes():
        if tag == "equal":
            continue
        spans.append(
            InlineChange(
                left_start=l0,
                left_end=l1,
                right_start=r0,
                right_end=r1,
                left_text=left_line[l0:l1],
                right_text=right_line[r0:r1],
            )
        )
    return spans


def _word_diff_label(left_line: str, right_line: str) -> str:
    """Return a short English description of word-level changes."""
    left_words = re.findall(r"\S+|\s+", left_line.strip())
    right_words = re.findall(r"\S+|\s+", right_line.strip())
    left_tokens = [w for w in left_words if w.strip()]
    right_tokens = [w for w in right_words if w.strip()]

    matcher = difflib.SequenceMatcher(None, left_tokens, right_tokens, autojunk=False)
    added: list[str] = []
    removed: list[str] = []
    for tag, l0, l1, r0, r1 in matcher.get_opcodes():
        if tag == "insert":
            added.extend(right_tokens[r0:r1])
        elif tag == "delete":
            removed.extend(left_tokens[l0:l1])
        elif tag == "replace":
            removed.extend(left_tokens[l0:l1])
            added.extend(right_tokens[r0:r1])

    parts: list[str] = []
    if removed and added:
        parts.append(f"changed {' '.join(removed)!r} to {' '.join(added)!r}")
    elif added:
        parts.append(f"added {' '.join(added)!r}")
    elif removed:
        parts.append(f"removed {' '.join(removed)!r}")
    return "; ".join(parts) if parts else "text changed"


class CompareService:
    """Runs a two-layer diff and owns navigation state.

    Call :meth:`compare` to (re)run the diff; then use :meth:`next`,
    :meth:`previous`, :meth:`first`, :meth:`last`, and :meth:`current`
    to navigate ``DifferenceGroup`` objects.
    """

    def __init__(self) -> None:
        self._groups: list[DifferenceGroup] = []
        self._cursor: int = -1  # index into _groups, -1 = before first
        self.left_label: str = "Left"
        self.right_label: str = "Right"
        self.left_path: Path | None = None
        self.right_path: Path | None = None
        self.options: CompareOptions = CompareOptions()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(
        self,
        left_text: str,
        right_text: str,
        *,
        left_label: str = "Left",
        right_label: str = "Right",
        left_path: Path | None = None,
        right_path: Path | None = None,
        options: CompareOptions | None = None,
    ) -> list[DifferenceGroup]:
        """Run the diff and return all DifferenceGroup objects."""
        self.left_label = left_label
        self.right_label = right_label
        self.left_path = left_path
        self.right_path = right_path
        self.options = options or CompareOptions()
        self._groups = self._build_groups(left_text, right_text, self.options)
        self._cursor = -1
        return self._groups

    @property
    def group_count(self) -> int:
        return len(self._groups)

    @property
    def has_differences(self) -> bool:
        return bool(self._groups)

    def current(self) -> DifferenceGroup | None:
        if self._cursor < 0 or self._cursor >= len(self._groups):
            return None
        return self._groups[self._cursor]

    def next(self) -> DifferenceGroup | None:
        if not self._groups:
            return None
        self._cursor = min(self._cursor + 1, len(self._groups) - 1)
        return self._groups[self._cursor]

    def previous(self) -> DifferenceGroup | None:
        if not self._groups:
            return None
        self._cursor = max(self._cursor - 1, 0)
        return self._groups[self._cursor]

    def first(self) -> DifferenceGroup | None:
        if not self._groups:
            return None
        self._cursor = 0
        return self._groups[0]

    def last(self) -> DifferenceGroup | None:
        if not self._groups:
            return None
        self._cursor = len(self._groups) - 1
        return self._groups[-1]

    def at_start(self) -> bool:
        return self._cursor <= 0

    def at_end(self) -> bool:
        return self._cursor >= len(self._groups) - 1

    # ------------------------------------------------------------------
    # Internal diff construction
    # ------------------------------------------------------------------

    def _build_groups(
        self, left_text: str, right_text: str, opts: CompareOptions
    ) -> list[DifferenceGroup]:
        left_raw = left_text.splitlines(keepends=True)
        right_raw = right_text.splitlines(keepends=True)
        left_norm = [_normalize_line(ln, opts) for ln in left_raw]
        right_norm = [_normalize_line(r, opts) for r in right_raw]

        matcher = difflib.SequenceMatcher(None, left_norm, right_norm, autojunk=False)
        groups: list[DifferenceGroup] = []

        for tag, l0, l1, r0, r1 in matcher.get_opcodes():
            if tag == "equal":
                continue
            left_chunk = [ln.rstrip("\r\n") for ln in left_raw[l0:l1]]
            right_chunk = [r.rstrip("\r\n") for r in right_raw[r0:r1]]
            kind = _classify_hunk(left_chunk, right_chunk, opts)

            # Build inline spans for single-line replacements.
            spans: list[InlineChange] = []
            if kind == "replace" and len(left_chunk) == 1 and len(right_chunk) == 1:
                spans = _build_inline_spans(left_chunk[0], right_chunk[0])

            group = DifferenceGroup(
                index=len(groups) + 1,
                total=0,  # patched below
                kind=kind,
                left_start_line=l0 + 1 if left_chunk else None,
                left_end_line=l1 if left_chunk else None,
                right_start_line=r0 + 1 if right_chunk else None,
                right_end_line=r1 if right_chunk else None,
                left_text=left_chunk,
                right_text=right_chunk,
                inline_spans=spans,
            )
            groups.append(group)

        total = len(groups)
        for g in groups:
            g.total = total
            g.summary_short = _short_summary(g, self.left_label, self.right_label)
            g.summary_verbose = _verbose_summary(g, self.left_label, self.right_label)

        return groups


# ------------------------------------------------------------------
# Speech summary builders
# ------------------------------------------------------------------


def _short_summary(g: DifferenceGroup, left_label: str, right_label: str) -> str:
    loc = _location_label(g)
    if g.kind == "insert":
        n = len(g.right_text)
        word = "line" if n == 1 else "lines"
        return f"Difference {g.index} of {g.total}. {n} {word} added at {loc}."
    if g.kind == "delete":
        n = len(g.left_text)
        word = "line" if n == 1 else "lines"
        return f"Difference {g.index} of {g.total}. {n} {word} deleted at {loc}."
    if g.kind == "whitespace":
        return f"Difference {g.index} of {g.total}. Whitespace-only change at {loc}."
    if g.kind == "line_ending":
        return f"Difference {g.index} of {g.total}. Line-ending change at {loc}."
    # replace
    n_left = len(g.left_text)
    n_right = len(g.right_text)
    if n_left == 1 and n_right == 1:
        return f"Difference {g.index} of {g.total}. Text changed at {loc}."
    return f"Difference {g.index} of {g.total}. {n_left} lines replaced with {n_right} at {loc}."


def _verbose_summary(g: DifferenceGroup, left_label: str, right_label: str) -> str:
    loc = _location_label(g)
    parts: list[str] = [f"Difference {g.index} of {g.total}."]

    if g.kind == "insert":
        parts.append(f"Lines inserted at {loc}.")
        for line in g.right_text[:3]:
            parts.append(f"Added: {line!r}")
        if len(g.right_text) > 3:
            parts.append(f"... and {len(g.right_text) - 3} more lines.")
        return " ".join(parts)

    if g.kind == "delete":
        parts.append(f"Lines deleted at {loc}.")
        for line in g.left_text[:3]:
            parts.append(f"Removed: {line!r}")
        if len(g.left_text) > 3:
            parts.append(f"... and {len(g.left_text) - 3} more lines.")
        return " ".join(parts)

    if g.kind == "whitespace":
        left_desc = _whitespace_description(g.left_text[0] if g.left_text else "")
        right_desc = _whitespace_description(g.right_text[0] if g.right_text else "")
        parts.append(f"Whitespace-only change at {loc}.")
        parts.append(f"{left_label}: {left_desc}.")
        parts.append(f"{right_label}: {right_desc}.")
        return " ".join(parts)

    if g.kind == "line_ending":
        parts.append(f"Line-ending change at {loc}.")
        return " ".join(parts)

    # replace
    parts.append(f"Text replaced at {loc}.")
    if len(g.left_text) == 1 and len(g.right_text) == 1:
        parts.append(f"{left_label}: {g.left_text[0]!r}.")
        parts.append(f"{right_label}: {g.right_text[0]!r}.")
        if g.inline_spans:
            word_label = _word_diff_label(g.left_text[0], g.right_text[0])
            parts.append(f"Change: {word_label}.")
    else:
        for line in g.left_text[:2]:
            parts.append(f"{left_label}: {line!r}")
        for line in g.right_text[:2]:
            parts.append(f"{right_label}: {line!r}")
        if len(g.left_text) > 2 or len(g.right_text) > 2:
            parts.append("(truncated — use difference list for full text)")
    return " ".join(parts)


def _location_label(g: DifferenceGroup) -> str:
    if g.left_start_line is not None and g.right_start_line is not None:
        if g.left_start_line == g.right_start_line:
            return f"line {g.left_start_line}"
        return f"left line {g.left_start_line}, right line {g.right_start_line}"
    if g.right_start_line is not None:
        return f"line {g.right_start_line}"
    if g.left_start_line is not None:
        return f"line {g.left_start_line}"
    return "unknown line"


def _whitespace_description(line: str) -> str:
    stripped = line.rstrip()
    leading = len(stripped) - len(stripped.lstrip())
    trailing = len(line.rstrip("\r\n")) - len(stripped)
    parts: list[str] = []
    if leading:
        kind = "tabs" if stripped[:leading].replace("\t", "") == "" else "spaces"
        parts.append(f"{leading} leading {kind}")
    if trailing:
        parts.append(f"{trailing} trailing spaces")
    text_content = stripped.lstrip()
    if text_content:
        parts.append(f"text: {text_content[:40]!r}")
    return "; ".join(parts) if parts else "(blank line)"
