"""Line-by-line diff review model for AI edits (AI-7), with word-level detail.

This is the wx-free core behind the accessible "Review AI Changes" dialog. It
turns an original text and a proposed revision into an ordered list of
segments. Each changed segment becomes a *hunk* the user can accept or reject
independently, so a person can apply all, some, or none of an AI edit and read
every change line by line before anything touches the document.

Line hunks alone are too coarse for prose: when the AI changes one word in a
90-character line, a line diff makes the user hear the whole line twice and
spot the difference by ear. So each "changed" hunk also carries a second-stage
**word-level** diff (:class:`WordChange`) with the surrounding sentence for
context — "Changed 'quick' to 'rapid'" plus the sentence it happened in — and
degrades back to plain line hunks when a change is really a rewrite (too many
word edits, or edits too large to be meaningful as phrases).

The model is deliberately simple and deterministic (built on
:class:`difflib.SequenceMatcher` with ``autojunk=False`` — autojunk silently
degrades diffs over ordinary prose) so the same review can be described to a
screen reader, navigated by hunk, and re-applied as a single text replacement
(one undo step in the editor).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

__all__ = [
    "DiffHunk",
    "DiffReview",
    "WordChange",
    "build_diff_review",
]

#: Above this many word-level edits a "changed" hunk is presented as lines: a
#: wholesale rewrite spoken as forty word pairs is worse than hearing the old
#: and new lines whole.
_MAX_WORD_CHANGES_PER_HUNK = 8

#: A single "phrase" edit longer than this is a rewrite, not a word change.
_MAX_PHRASE_CHARS = 100

#: Word (with internal apostrophe), whitespace run, or punctuation run — every
#: character falls into exactly one class, so joining tokens reconstructs the
#: text and token boundaries never split a word.
_TOKEN_PATTERN = re.compile(r"\w+(?:['’]\w+)?|\s+|[^\w\s]+", re.UNICODE)

_SENTENCE_TERMINATORS = ".!?"
_CLOSERS_AFTER_TERMINATOR = "\"')]}’”"


def _split_lines(text: str) -> list[str]:
    """Split into lines without losing the final-newline distinction.

    ``"a\\nb".split("\\n") == ["a", "b"]`` and ``"a\\nb\\n".split("\\n")``
    ``== ["a", "b", ""]``; joining back with ``"\\n"`` round-trips exactly, so
    accepting or rejecting hunks never silently adds or drops a trailing
    newline.
    """
    return text.split("\n")


@dataclass(frozen=True, slots=True)
class WordChange:
    """One word-level edit inside a changed hunk, with sentence context.

    "Changed 'quick' to 'rapid'" is meaningless on its own; "in the sentence
    'The quick brown fox...', changed 'quick' to 'rapid'" is reviewable by
    ear. ``old_sentence``/``new_sentence`` carry the enclosing sentence from
    each side of the hunk (whitespace-collapsed for speech).
    """

    old_words: str
    new_words: str
    old_sentence: str = ""
    new_sentence: str = ""

    def action_phrase(self) -> str:
        """The spoken verb phrase: Changed / Inserted / Removed the words."""
        if self.old_words and self.new_words:
            return f'Changed "{self.old_words}" to "{self.new_words}"'
        if self.new_words:
            return f'Inserted "{self.new_words}"'
        return f'Removed "{self.old_words}"'


@dataclass(frozen=True, slots=True)
class DiffHunk:
    """A single accept/reject unit of change.

    ``kind`` is one of ``"added"``, ``"removed"``, or ``"changed"``.
    ``old_lines`` are the original lines (empty for a pure addition) and
    ``new_lines`` are the proposed lines (empty for a pure deletion).
    ``old_line_no`` is the 1-based line number in the original where the change
    begins, for human-readable announcements. ``word_changes`` is the
    second-stage word diff for a "changed" hunk — empty when the change is
    better presented as whole lines (rewrites, spacing-only edits, other
    kinds).
    """

    index: int
    kind: str
    old_lines: tuple[str, ...]
    new_lines: tuple[str, ...]
    old_line_no: int
    word_changes: tuple[WordChange, ...] = ()

    def describe(self) -> str:
        """A one-line, screen-reader-friendly summary of this hunk."""
        position = f"at line {self.old_line_no}"
        if self.kind == "added":
            count = len(self.new_lines)
            return f"Added {count} line{'s' if count != 1 else ''} {position}."
        if self.kind == "removed":
            count = len(self.old_lines)
            return f"Removed {count} line{'s' if count != 1 else ''} {position}."
        if len(self.word_changes) == 1:
            return f"{self.word_changes[0].action_phrase()} {position}."
        if self.word_changes:
            count = len(self.word_changes)
            return f"Changed {count} phrases {position}."
        return (
            f"Changed {len(self.old_lines)} line"
            f"{'s' if len(self.old_lines) != 1 else ''} to "
            f"{len(self.new_lines)} line"
            f"{'s' if len(self.new_lines) != 1 else ''} {position}."
        )

    def detail_lines(self) -> list[str]:
        """Readable detail for the pane: word edits with sentence context first
        (when available), then the whole old/new lines, which stay reviewable
        exactly as before."""
        lines: list[str] = [self.describe()]
        for change in self.word_changes:
            lines.append(f"{change.action_phrase()}.")
            if change.old_sentence and change.old_sentence != change.old_words:
                lines.append(f"  Sentence before: {change.old_sentence}")
            if (
                change.new_sentence
                and change.new_sentence != change.new_words
                and change.new_sentence != change.old_sentence
            ):
                lines.append(f"  Sentence after: {change.new_sentence}")
        for old in self.old_lines:
            lines.append(f"- removed: {old}" if old else "- removed: (blank line)")
        for new in self.new_lines:
            lines.append(f"+ added: {new}" if new else "+ added: (blank line)")
        return lines


@dataclass(frozen=True, slots=True)
class _Segment:
    """An ordered piece of the diff. ``hunk_index`` is -1 for unchanged text."""

    old_lines: tuple[str, ...]
    new_lines: tuple[str, ...]
    hunk_index: int


@dataclass(slots=True)
class DiffReview:
    """The full reviewable diff between two texts."""

    original: str
    revised: str
    hunks: list[DiffHunk] = field(default_factory=list)
    _segments: list[_Segment] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.hunks)

    def apply(self, accepted: set[int]) -> str:
        """Rebuild the text accepting only the hunks whose index is in *accepted*.

        Unchanged segments are kept verbatim. A rejected hunk keeps its original
        lines; an accepted hunk uses the proposed lines. The result is a single
        string ready to drop into the editor in one replacement (one undo).
        """
        out: list[str] = []
        for segment in self._segments:
            if segment.hunk_index < 0:
                out.extend(segment.old_lines)
            elif segment.hunk_index in accepted:
                out.extend(segment.new_lines)
            else:
                out.extend(segment.old_lines)
        return "\n".join(out)

    def accept_all(self) -> str:
        return self.apply({hunk.index for hunk in self.hunks})

    def reject_all(self) -> str:
        return self.apply(set())

    def summary(self) -> str:
        """A short overall summary for an opening announcement."""
        if not self.hunks:
            return "No changes to review."
        added = sum(1 for h in self.hunks if h.kind == "added")
        removed = sum(1 for h in self.hunks if h.kind == "removed")
        changed = sum(1 for h in self.hunks if h.kind == "changed")
        parts: list[str] = []
        if added:
            parts.append(f"{added} addition{'s' if added != 1 else ''}")
        if removed:
            parts.append(f"{removed} removal{'s' if removed != 1 else ''}")
        if changed:
            parts.append(f"{changed} change{'s' if changed != 1 else ''}")
        total = len(self.hunks)
        return f"{total} hunk{'s' if total != 1 else ''} to review: " + ", ".join(parts) + "."


def _sentence_context(text: str, start: int, end: int) -> str:
    """The sentence enclosing ``text[start:end]``, whitespace-collapsed.

    Scans outward to a sentence terminator (., !, ?) or a line break, keeping
    closing quotes/brackets attached to the terminator; falls back to the
    whole line. Approximate on abbreviations, which is fine — this is spoken
    orientation, not parsing.
    """
    left = start
    while left > 0:
        ch = text[left - 1]
        if ch == "\n" or ch in _SENTENCE_TERMINATORS:
            break
        left -= 1
    right = end
    length = len(text)
    while right < length:
        ch = text[right]
        if ch == "\n":
            break
        right += 1
        if ch in _SENTENCE_TERMINATORS:
            while right < length and text[right] in _CLOSERS_AFTER_TERMINATOR:
                right += 1
            break
    return " ".join(text[left:right].split())


def _token_offsets(tokens: list[str]) -> list[int]:
    """Cumulative character offsets: ``offsets[i]`` is where token *i* starts."""
    offsets = [0]
    for token in tokens:
        offsets.append(offsets[-1] + len(token))
    return offsets


def _word_changes(old_text: str, new_text: str) -> tuple[WordChange, ...]:
    """The second-stage word diff for one changed hunk, or () to stay line-level.

    Tokens are words, whitespace runs, and punctuation runs, so nothing is
    lost between them; adjacent edits separated only by whitespace merge into
    one phrase ("quick brown" -> "rapid red" is one change, not two).
    Returns () — meaning "present this hunk as lines" — for rewrites (too
    many edits or oversized phrases) and for spacing-only changes, which read
    better as whole lines.
    """
    old_tokens = _TOKEN_PATTERN.findall(old_text)
    new_tokens = _TOKEN_PATTERN.findall(new_text)
    matcher = SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    spans: list[list[int]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if spans:
            previous = spans[-1]
            gap_old = old_tokens[previous[1] : i1]
            gap_new = new_tokens[previous[3] : j1]
            if all(t.isspace() for t in gap_old) and all(t.isspace() for t in gap_new):
                previous[1], previous[3] = i2, j2
                continue
        spans.append([i1, i2, j1, j2])
    old_offsets = _token_offsets(old_tokens)
    new_offsets = _token_offsets(new_tokens)
    changes: list[WordChange] = []
    for i1, i2, j1, j2 in spans:
        old_words = "".join(old_tokens[i1:i2]).strip()
        new_words = "".join(new_tokens[j1:j2]).strip()
        if not old_words and not new_words:
            continue  # spacing-only edit: nothing meaningful to speak
        if len(old_words) > _MAX_PHRASE_CHARS or len(new_words) > _MAX_PHRASE_CHARS:
            return ()
        if len(changes) >= _MAX_WORD_CHANGES_PER_HUNK:
            return ()
        changes.append(
            WordChange(
                old_words=old_words,
                new_words=new_words,
                old_sentence=_sentence_context(old_text, old_offsets[i1], old_offsets[i2]),
                new_sentence=_sentence_context(new_text, new_offsets[j1], new_offsets[j2]),
            )
        )
    return tuple(changes)


def build_diff_review(original: str, revised: str) -> DiffReview:
    """Build a :class:`DiffReview` from *original* to *revised* text."""
    old_lines = _split_lines(original)
    new_lines = _split_lines(revised)
    matcher = SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    segments: list[_Segment] = []
    hunks: list[DiffHunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_block = tuple(old_lines[i1:i2])
        new_block = tuple(new_lines[j1:j2])
        if tag == "equal":
            segments.append(_Segment(old_block, new_block, -1))
            continue
        if tag == "insert":
            kind = "added"
        elif tag == "delete":
            kind = "removed"
        else:  # "replace"
            kind = "changed"
        word_changes: tuple[WordChange, ...] = ()
        if kind == "changed":
            word_changes = _word_changes("\n".join(old_block), "\n".join(new_block))
        index = len(hunks)
        hunks.append(
            DiffHunk(
                index=index,
                kind=kind,
                old_lines=old_block,
                new_lines=new_block,
                old_line_no=i1 + 1,
                word_changes=word_changes,
            )
        )
        segments.append(_Segment(old_block, new_block, index))
    return DiffReview(original=original, revised=revised, hunks=hunks, _segments=segments)
