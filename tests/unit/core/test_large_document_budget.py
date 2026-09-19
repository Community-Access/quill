"""GATE-PERF: a large document stays usable, in both editors (bad.md gate 5).

The last gate the parity program asked for, and the one that keeps the shared
``DocumentText`` from rotting. What it measures is not speed for its own sake: it
is whether the *work per keystroke* is bounded. A status bar that recomputes word
counts on every arrow press, or an autoformat rule that reads the whole buffer to
look at one character, is fine in a note and unusable in a novel -- and the
person who notices first is the one whose screen reader is waiting on the same
thread.

Measured **against a ceiling, not against each other**, and deliberately:
comparing the two editors would pass a build where both had become slow
together, which is exactly what happened before ``DocumentText`` existed
(QuillLite read the control three times per status refresh and QUILL twice).

The ceilings are generous on purpose -- a CI box under load is several times
slower than a developer's machine, and a gate that fails on a bad afternoon gets
deleted. What they catch is a change of *complexity*: an O(N) scan per keystroke
against a 50 MB buffer does not come in slightly over, it comes in hundreds of
times over.

Marked ``perf``, which the repo runs with ``RUN_PERF=1`` and excludes with
``-m 'not perf'``: building a 50 MB string is most of the cost of this file, and
a wall-clock budget on a shared CI worker is informative rather than definitive.
"""

from __future__ import annotations

import time

import pytest

from quill.core.document_text import DocumentText
from quill.core.metrics import compute_document_stats

#: 50 MB of plausible prose: long-ish lines, real word boundaries. Built once per
#: module, because building it is most of the cost of this file.
_LINE = "The quick brown fox jumps over the lazy dog and keeps going for a while. "
_TARGET_BYTES = 50 * 1024 * 1024


@pytest.fixture(scope="module")
def big_text() -> str:
    repeats = _TARGET_BYTES // len(_LINE)
    # One newline every ten lines, so the line table has work to do without the
    # document becoming one line of 50 MB (which nothing real ever is).
    chunks = []
    for index in range(repeats):
        chunks.append(_LINE)
        if index % 10 == 9:
            chunks.append("\n")
    return "".join(chunks)


@pytest.fixture(scope="module")
def mirror_and_reads(big_text: str) -> tuple[DocumentText, list[int]]:
    """The mirror, and the tally of how many times it went to the document.

    A tuple rather than an attribute on the mirror: ``DocumentText`` has
    ``__slots__``, and that is deliberate -- one per document in a session with
    twenty tabs open is exactly where a stray ``__dict__`` costs real memory.
    """
    reads: list[int] = []

    def _read() -> str:
        reads.append(1)
        return big_text

    return DocumentText(_read), reads


@pytest.fixture
def mirror(mirror_and_reads: tuple[DocumentText, list[int]]) -> DocumentText:
    return mirror_and_reads[0]


def _seconds(action) -> float:
    start = time.perf_counter()
    action()
    return time.perf_counter() - start


# -- the ceilings --------------------------------------------------------------

#: One full pass over 50 MB. Generous: this is the *uncached* cost, paid once.
_FIRST_STATS_CEILING_S = 12.0

#: A cached answer. This is the number that matters -- it is what a caret move
#: costs -- and it must not scale with the document at all.
_CACHED_CEILING_S = 0.01

#: One line/column lookup off the cached table: a binary search, so flat.
_LINE_COLUMN_CEILING_S = 0.01

#: One character before the caret. QuillLite's autoformat used to read the whole
#: buffer for this, on the hottest path in the app (bad.md T1).
_CHAR_BEFORE_CEILING_S = 0.01


@pytest.mark.perf
def test_the_first_statistics_pass_is_within_budget(mirror: DocumentText) -> None:
    elapsed = _seconds(mirror.stats)
    assert elapsed < _FIRST_STATS_CEILING_S, f"first stats pass took {elapsed:.2f}s"


@pytest.mark.perf
def test_a_second_statistics_read_costs_nothing(mirror: DocumentText) -> None:
    """The whole reason the mirror exists: readers after the first pay nothing."""
    mirror.stats()
    elapsed = _seconds(mirror.stats)
    assert elapsed < _CACHED_CEILING_S, f"cached stats took {elapsed:.4f}s"


@pytest.mark.perf
def test_a_status_refresh_does_not_re_read_the_document(
    mirror_and_reads: tuple[DocumentText, list[int]],
) -> None:
    """Three cells asking three questions must cost one read, not three."""
    mirror, reads = mirror_and_reads
    mirror.stats()
    before = len(reads)
    mirror.stats()
    mirror.line_column(1_000_000)
    mirror.char_before(1_000_000)
    assert len(reads) == before, "a status refresh re-read the buffer"


@pytest.mark.perf
def test_a_caret_move_is_flat_not_linear(mirror: DocumentText) -> None:
    """Holding Down must not rebuild the line table on every press (bad.md P1.2a)."""
    mirror.line_column(0)  # build the table once
    elapsed = _seconds(
        lambda: [mirror.line_column(offset) for offset in range(0, 5_000_000, 500_000)]
    )
    assert elapsed < _LINE_COLUMN_CEILING_S, f"ten line/column lookups took {elapsed:.4f}s"


@pytest.mark.perf
def test_the_character_before_the_caret_is_one_character(mirror: DocumentText) -> None:
    mirror.text  # noqa: B018 - warm the mirror the way typing already has
    elapsed = _seconds(lambda: [mirror.char_before(offset) for offset in range(0, 100_000, 10_000)])
    assert elapsed < _CHAR_BEFORE_CEILING_S, f"ten char_before calls took {elapsed:.4f}s"


@pytest.mark.perf
def test_an_edit_costs_nothing_until_something_reads(mirror: DocumentText) -> None:
    """Invalidation is O(1) on purpose: the typist must not pay the reader's bill."""
    mirror.stats()
    elapsed = _seconds(lambda: [mirror.invalidate() for _ in range(1000)])
    assert elapsed < _CACHED_CEILING_S, f"1000 invalidations took {elapsed:.4f}s"


@pytest.mark.perf
def test_the_document_really_is_large(big_text: str) -> None:
    """A budget measured against a small document proves nothing."""
    assert len(big_text) > 40 * 1024 * 1024


@pytest.mark.perf
def test_the_shared_statistics_function_is_what_both_editors_use(big_text: str) -> None:
    """Rule 10, as a measurement: one implementation, so one performance story."""
    sample = big_text[:1_000_000]
    direct = compute_document_stats(sample)
    mirror = DocumentText(lambda: sample)
    assert mirror.stats() == direct
