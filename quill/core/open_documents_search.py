"""Find and replace across every open document. wx-free; both editors use it.

Asked for on QUILLVille by Chris Nova (October 2026): NoteTab could load a
hundred files and find or replace across all of them at once, and neither QUILL
nor QUILL Lite could. QUILL had Search in Files, which reads what is saved on
disk; this is the other half -- the text exactly as it is in each open window,
so unsaved changes and never-saved documents are found too, and nothing that
is not open is touched.

Pure functions over :class:`OpenDoc` snapshots, matched by the same
:mod:`quill.core.find_model` both editors' Find windows already use, so a
query means the same thing here as it does in one document:

* :func:`find_across` -- the next or previous match, moving from document to
  document and coming back round to where the search started.
* :func:`find_all_across` -- every match, grouped by document, for a list.
* :func:`plan_replace` -- what Replace All would change, document by document,
  before anything is changed, so the editor can ask first.

QUILL Lite may never be ahead of QUILL: the editors share this module and the
window in ``quill/ui/open_documents_find.py``, and each only supplies the
adapter that says what its open documents are.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from quill.core.find_model import (
    FindMatch,
    FindQuery,
    all_matches,
    compile_query,
    find_next,
)
from quill.core.find_model import (
    replace_all as replace_in_text,
)

__all__ = [
    "CrossHit",
    "OpenDoc",
    "ReplacePlan",
    "find_across",
    "find_all_across",
    "line_text",
    "plan_replace",
]


@dataclass(frozen=True)
class OpenDoc:
    """One open document as the search sees it: its name, its live text, and
    whether it may be changed (a read-only file or a generated report may not)."""

    name: str
    text: str
    editable: bool = True


@dataclass(frozen=True)
class CrossHit:
    """A match, which document it is in, and how the search got there.

    ``moved`` is True when it is in a different document from the one the
    search started in (so the editor says the document's name); ``wrapped`` is
    True when the search went past the last document and came back round.
    """

    doc: int
    match: FindMatch
    moved: bool
    wrapped: bool


def _no_wrap(query: FindQuery) -> FindQuery:
    return replace(query, wrap=False)


def find_across(
    docs: list[OpenDoc],
    query: FindQuery,
    *,
    current: int,
    position: int,
    backwards: bool = False,
) -> CrossHit | None:
    """The next (or previous) match after *position* in document *current*.

    Searches the rest of the current document, then each following document
    from its start (or each earlier one from its end, going backwards), then --
    when the query allows wrapping -- the documents before the current one and
    finally the part of the current one the search started past. None when
    nothing matches anywhere.
    """
    if not docs:
        return None
    compiled = compile_query(_no_wrap(query))
    if compiled.pattern is None:
        return None
    current = max(0, min(current, len(docs) - 1))
    found, _ = find_next(compiled, docs[current].text, from_pos=position, backwards=backwards)
    if found is not None:
        return CrossHit(current, found, moved=False, wrapped=False)
    step = -1 if backwards else 1
    count = len(docs)
    for offset in range(1, count + 1):
        index = (current + step * offset) % count
        wrapped = (index <= current) if not backwards else (index >= current)
        if wrapped and not query.wrap:
            return None
        text = docs[index].text
        start = len(text) if backwards else 0
        if index == current:
            # Back where it started: only the part it skipped at first.
            found, _ = find_next(compiled, text, from_pos=start, backwards=backwards)
            if found is None:
                return None
            before = found.start < position if not backwards else found.end > position
            return CrossHit(index, found, moved=False, wrapped=True) if before else None
        found = _first_or_last(compiled, text, backwards=backwards)
        if found is not None:
            return CrossHit(index, found, moved=True, wrapped=wrapped)
    return None


def _first_or_last(compiled: object, text: str, *, backwards: bool) -> FindMatch | None:
    if not backwards:
        found, _ = find_next(compiled, text, from_pos=0)  # type: ignore[arg-type]
        return found
    matches, _ = all_matches(compiled, text)  # type: ignore[arg-type]
    return matches[-1] if matches else None


def find_all_across(
    docs: list[OpenDoc], query: FindQuery, *, max_matches: int = 5_000
) -> tuple[list[tuple[int, FindMatch]], bool]:
    """Every match in every document, in document order; and whether it was cut short."""
    compiled = compile_query(_no_wrap(query))
    results: list[tuple[int, FindMatch]] = []
    for index, doc in enumerate(docs):
        left = max_matches - len(results)
        if left <= 0:
            return results, True
        matches, truncated = all_matches(compiled, doc.text, max_matches=left)
        results.extend((index, match) for match in matches)
        if truncated:
            return results, True
    return results, False


def line_text(text: str, match: FindMatch, *, max_chars: int = 160) -> str:
    """The line a match is on, trimmed, for a results list or an announcement."""
    start = text.rfind("\n", 0, match.start) + 1
    end = text.find("\n", match.end)
    line = text[start : end if end != -1 else len(text)].strip()
    return line if len(line) <= max_chars else line[: max_chars - 3].rstrip() + "..."


@dataclass(frozen=True)
class ReplacePlan:
    """What Replace All would do, worked out before anything changes.

    ``changes`` is ``[(doc index, new text, replacements)]`` for every editable
    document with a match; ``skipped`` counts the read-only documents that had
    matches and are left alone.
    """

    changes: tuple[tuple[int, str, int], ...]
    skipped: int
    skipped_matches: int

    @property
    def total(self) -> int:
        return sum(count for _index, _text, count in self.changes)

    @property
    def documents(self) -> int:
        return len(self.changes)


def plan_replace(docs: list[OpenDoc], query: FindQuery, replacement: str) -> ReplacePlan:
    """Every replacement Replace All would make, per document, without making it."""
    compiled = compile_query(_no_wrap(query))
    changes: list[tuple[int, str, int]] = []
    skipped = skipped_matches = 0
    for index, doc in enumerate(docs):
        new_text, count = replace_in_text(compiled, doc.text, replacement)
        if not count:
            continue
        if not doc.editable:
            skipped += 1
            skipped_matches += count
            continue
        changes.append((index, new_text, count))
    return ReplacePlan(tuple(changes), skipped, skipped_matches)
