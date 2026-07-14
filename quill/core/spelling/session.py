"""ReviewSession: orchestrates the F7 spelling review workflow.

Owns all mutable review state. Never imports wx. The dialog passes callbacks
for editor reads/writes and dictionary persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.spellcheck import (
    Misspelling,
    add_word_to_scope,
    rank_misspellings_by_frequency,
    suggest_words,
)
from quill.core.spelling.context_builder import build_context
from quill.core.spelling.models import (
    ActionKind,
    ReviewCounters,
    SpellingIssue,
)


@dataclass
class _UndoRecord:
    kind: ActionKind
    word: str
    replacement: str = ""
    doc_start: int = 0
    doc_end_before: int = 0
    doc_end_after: int = 0
    all_ranges: list[tuple[int, int, int, str]] = field(default_factory=list)
    scope: str = ""
    # ignored_once: position that was skipped
    ignored_pos: int = -1
    # ignored_all: the word added to session ignore set
    ignored_word: str = ""


class ReviewSession:
    """Stateful controller for a single F7 spelling review pass.

    All position arithmetic is relative to the current live text, which the
    session maintains as a private copy. The dialog is responsible for keeping
    the editor in sync by calling ``apply_change`` and friends and using the
    returned (start, old_end, replacement) tuples to drive ``editor.Replace``.
    """

    def __init__(
        self,
        text: str,
        dictionary: set[str],
        scope_start: int = 0,
        scope_end: int | None = None,
        ranked: bool = False,
    ) -> None:
        self._text = text
        self._dictionary = dictionary
        self._scope_start = scope_start
        self._scope_end = scope_end if scope_end is not None else len(text)
        # Kurzweil-1000-style ranked spelling (community feature request):
        # the guided review walks issues most-frequent-word-first instead of
        # document order. Re-applied on every _rescan(), which runs after
        # every action -- so as Change All clears the current top offender,
        # the next most-frequent word naturally rises to the front instead of
        # the ranking going stale mid-session.
        self._ranked = ranked
        self._session_ignores: set[str] = set()
        self._ignored_once_positions: set[int] = set()
        self._counters = ReviewCounters()
        self._undo_stack: list[_UndoRecord] = []
        self._issues: list[Misspelling] = []
        self._current_idx: int = 0
        self._rescan(advance_past=None)

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def current(self) -> SpellingIssue | None:
        if self._current_idx >= len(self._issues):
            return None
        m = self._issues[self._current_idx]
        ctx, ws, we = build_context(self._text, m.start, m.end)
        suggs = tuple(suggest_words(m.word, self._dictionary))
        return SpellingIssue(
            word=m.word,
            doc_start=m.start,
            doc_end=m.end,
            context_text=ctx,
            context_word_start=ws,
            context_word_end=we,
            suggestions=suggs,
        )

    def total(self) -> int:
        return len(self._issues)

    def position(self) -> int:
        """1-based index of the current issue."""
        return self._current_idx + 1

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def is_complete(self) -> bool:
        return self._current_idx >= len(self._issues)

    def get_counters(self) -> ReviewCounters:
        c = self._counters
        return ReviewCounters(
            reviewed=c.reviewed,
            changed=c.changed,
            changed_all=c.changed_all,
            ignored_once=c.ignored_once,
            ignored_all=c.ignored_all,
            added_to_dict=c.added_to_dict,
        )

    # ------------------------------------------------------------------
    # Actions — each returns a list of (start, old_end, replacement)
    # tuples the dialog must apply to the editor, in order.
    # ------------------------------------------------------------------

    def apply_change(self, replacement: str) -> list[tuple[int, int, str]]:
        """Replace the current occurrence with *replacement*."""
        m = self._issues[self._current_idx]
        old_start, old_end, old_word = m.start, m.end, m.word
        new_end = old_start + len(replacement)
        delta = len(replacement) - (old_end - old_start)

        self._text = self._text[:old_start] + replacement + self._text[old_end:]
        self._scope_end += delta
        self._shift_ignored_positions(old_start, delta)

        self._undo_stack.append(
            _UndoRecord(
                kind=ActionKind.CHANGE,
                word=old_word,
                replacement=replacement,
                doc_start=old_start,
                doc_end_before=old_end,
                doc_end_after=new_end,
            )
        )
        self._counters.changed += 1
        self._counters.reviewed += 1

        self._rescan(advance_past=old_start)
        return [(old_start, old_end, replacement)]

    def apply_change_all(self, replacement: str) -> list[tuple[int, int, str]]:
        """Replace every remaining in-scope occurrence of the current word."""
        m = self._issues[self._current_idx]
        target_word = m.word
        target_lower = target_word.lower()

        # Collect all in-scope positions matching this word (forward order).
        from quill.core.spellcheck import list_misspellings as _lm

        all_ms = [
            x
            for x in _lm(self._text, self._dictionary)
            if self._scope_start <= x.start < self._scope_end and x.word.lower() == target_lower
        ]

        ranges_applied: list[tuple[int, int, str]] = []
        undo_ranges: list[tuple[int, int, int, str]] = []

        # Apply in reverse to preserve earlier positions.
        cumulative_delta = 0
        for x in reversed(all_ms):
            repl = _case_match(x.word, replacement)
            new_end = x.start + len(repl)
            delta = len(repl) - (x.end - x.start)
            self._text = self._text[: x.start] + repl + self._text[x.end :]
            self._scope_end += delta
            self._shift_ignored_positions(x.start, delta)
            undo_ranges.append((x.start, x.end, new_end, x.word))
            ranges_applied.append((x.start, x.end, repl))
            cumulative_delta += delta

        self._undo_stack.append(
            _UndoRecord(
                kind=ActionKind.CHANGE_ALL,
                word=target_word,
                replacement=replacement,
                all_ranges=undo_ranges,
            )
        )
        self._counters.changed_all += len(all_ms)
        self._counters.reviewed += 1

        self._rescan(advance_past=None)
        return list(reversed(ranges_applied))  # forward order for editor

    def apply_ignore_once(self) -> None:
        """Skip the current occurrence without adding the word to any ignore set."""
        m = self._issues[self._current_idx]
        self._ignored_once_positions.add(m.start)
        self._undo_stack.append(
            _UndoRecord(
                kind=ActionKind.IGNORE_ONCE,
                word=m.word,
                ignored_pos=m.start,
            )
        )
        self._counters.ignored_once += 1
        self._counters.reviewed += 1
        self._current_idx += 1

    def apply_ignore_all(self) -> None:
        """Ignore all occurrences of the current word for the rest of the session."""
        m = self._issues[self._current_idx]
        word_lower = m.word.lower()
        self._session_ignores.add(word_lower)
        self._undo_stack.append(
            _UndoRecord(
                kind=ActionKind.IGNORE_ALL,
                word=m.word,
                ignored_word=word_lower,
            )
        )
        self._counters.ignored_all += 1
        self._counters.reviewed += 1
        self._rescan(advance_past=None)

    def add_to_dict(
        self,
        scope: str,
        document_path: Path | None,
        project_root: Path | None,
    ) -> None:
        """Add the current word to the named dictionary scope."""
        m = self._issues[self._current_idx]
        add_word_to_scope(m.word, scope, document_path, project_root)
        # Also add to the in-memory dictionary so the session respects it.
        self._dictionary.add(m.word.lower())
        self._undo_stack.append(
            _UndoRecord(
                kind=ActionKind.ADD_TO_DICT,
                word=m.word,
                scope=scope,
            )
        )
        self._counters.added_to_dict += 1
        self._counters.reviewed += 1
        self._rescan(advance_past=None)

    def undo_last(self) -> list[tuple[int, int, str]]:
        """Undo the most recent action. Returns editor replace tuples (forward order)."""
        if not self._undo_stack:
            return []
        rec = self._undo_stack.pop()

        if rec.kind == ActionKind.CHANGE:
            # Restore original at replacement position.
            start, old_end_after, old_word = rec.doc_start, rec.doc_end_after, rec.word
            self._text = self._text[:start] + old_word + self._text[old_end_after:]
            delta = len(old_word) - (old_end_after - start)
            self._scope_end += delta
            self._shift_ignored_positions(start, delta)
            self._counters.changed -= 1
            self._counters.reviewed -= 1
            self._rescan(advance_past=None)
            return [(start, old_end_after, old_word)]

        if rec.kind == ActionKind.CHANGE_ALL:
            ops: list[tuple[int, int, str]] = []
            # undo_ranges stored as (start, original_end, new_end, original_word)
            for start, orig_end, new_end, orig_word in reversed(rec.all_ranges):
                self._text = self._text[:start] + orig_word + self._text[new_end:]
                delta = orig_end - start - (new_end - start)
                self._scope_end += delta
                self._shift_ignored_positions(start, delta)
                ops.append((start, new_end, orig_word))
            self._counters.changed_all -= len(rec.all_ranges)
            self._counters.reviewed -= 1
            self._rescan(advance_past=None)
            return list(reversed(ops))

        if rec.kind == ActionKind.IGNORE_ONCE:
            self._ignored_once_positions.discard(rec.ignored_pos)
            self._counters.ignored_once -= 1
            self._counters.reviewed -= 1
            self._current_idx = max(0, self._current_idx - 1)
            return []

        if rec.kind == ActionKind.IGNORE_ALL:
            self._session_ignores.discard(rec.ignored_word)
            self._counters.ignored_all -= 1
            self._counters.reviewed -= 1
            self._rescan(advance_past=None)
            return []

        if rec.kind == ActionKind.ADD_TO_DICT:
            self._dictionary.discard(rec.word.lower())
            # Remove from file-based dictionary too.
            try:
                from quill.core.paths import app_data_dir
                from quill.core.spellcheck import load_scope_dictionary
                from quill.core.storage import write_json_atomic

                path = app_data_dir() / "dictionaries" / "personal.json"
                words = load_scope_dictionary(rec.scope, None, None)
                words.discard(rec.word.lower())
                write_json_atomic(path, sorted(words))
            except Exception:  # noqa: BLE001
                pass
            self._counters.added_to_dict -= 1
            self._counters.reviewed -= 1
            self._rescan(advance_past=None)
            return []

        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rescan(self, advance_past: int | None) -> None:
        """Re-scan _text and set _current_idx to the first unhandled issue.

        If *advance_past* is given, the first issue must start strictly after
        that position (used after Change to skip the replacement location).
        In ranked mode, "next" has no positional meaning -- the freshly
        re-ranked list's top entry is always shown next, which naturally
        surfaces the next-most-frequent word once the current one is cleared.
        """
        from quill.core.spellcheck import list_misspellings as _lm

        self._issues = [
            m
            for m in _lm(self._text, self._dictionary)
            if self._scope_start <= m.start < self._scope_end
            and m.word.lower() not in self._session_ignores
            and m.start not in self._ignored_once_positions
        ]
        if self._ranked:
            self._issues = rank_misspellings_by_frequency(self._issues)
        if advance_past is not None:
            if self._ranked:
                self._current_idx = 0 if self._issues else len(self._issues)
                return
            # Find the index of the first issue strictly after advance_past.
            for i, m in enumerate(self._issues):
                if m.start > advance_past:
                    self._current_idx = i
                    return
            self._current_idx = len(self._issues)
        else:
            # Stay at or before the current position; find the issue that was
            # here before the rescan (for undo / ignore_all / add_to_dict).
            self._current_idx = min(self._current_idx, len(self._issues))

    def _shift_ignored_positions(self, after: int, delta: int) -> None:
        if not self._ignored_once_positions or delta == 0:
            return
        self._ignored_once_positions = {
            pos + delta if pos > after else pos for pos in self._ignored_once_positions
        }


def _case_match(original: str, replacement: str) -> str:
    """Preserve capitalisation pattern of *original* in *replacement*."""
    if original.isupper():
        return replacement.upper()
    if original.istitle():
        return replacement.capitalize()
    return replacement
