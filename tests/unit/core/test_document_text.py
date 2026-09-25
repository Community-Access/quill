"""The mirror that stops display code reading the control.

Every test here counts reads. That is the whole point of the class: the answers
it gives are the same answers the control would give, and what is being asserted
is how *often* it goes and asks. A version of this that was always correct and
read the buffer per question would pass an equality test and fail the user --
which is exactly what QUILL Lite shipped, three full scans and two marshals per
status refresh (bad.md V2, V3, S8, T1).
"""

from __future__ import annotations

from quill.core.document_text import DocumentText


class Source:
    """A text control, minus the control: text, and a tally of the reads."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.reads = 0

    def read(self) -> str:
        self.reads += 1
        return self.text


def test_the_text_is_read_once_however_often_it_is_asked_for() -> None:
    source = Source("alpha bravo")
    doc = DocumentText(source.read)
    assert doc.text == "alpha bravo"
    assert doc.text == "alpha bravo"
    assert doc.stats().words == 2
    assert doc.line_column(3) == (1, 4)
    assert source.reads == 1


def test_nothing_is_read_until_something_asks() -> None:
    """An edit marks the mirror stale and does no work. A hook that read the
    buffer would move the cost from the status bar to the typist, which is
    worse than the bug."""
    source = Source("alpha")
    doc = DocumentText(source.read)
    for _ in range(100):
        doc.invalidate()
    assert source.reads == 0


def test_an_edit_is_seen_by_the_next_reader() -> None:
    source = Source("alpha")
    doc = DocumentText(source.read)
    assert doc.stats().characters == 5
    source.text = "alpha bravo"
    doc.invalidate()
    assert doc.text == "alpha bravo"
    assert doc.stats().characters == 11
    assert source.reads == 2


def test_stats_are_recomputed_only_when_the_document_changes() -> None:
    source = Source("one two three")
    doc = DocumentText(source.read)
    first = doc.stats()
    assert doc.stats() is first
    doc.invalidate()
    assert doc.stats() is not first


def test_the_revision_counts_edits() -> None:
    doc = DocumentText(lambda: "")
    assert doc.revision == 0
    doc.invalidate()
    doc.invalidate()
    assert doc.revision == 2


def test_line_starts_are_the_offsets_each_line_begins_at() -> None:
    doc = DocumentText(lambda: "one\ntwo\n\nfour")
    assert doc.line_starts() == [0, 4, 8, 9]


def test_line_starts_are_built_once_per_edit() -> None:
    source = Source("one\ntwo\nthree")
    doc = DocumentText(source.read)
    first = doc.line_starts()
    assert doc.line_starts() is first
    doc.invalidate()
    assert doc.line_starts() is not first


def test_line_and_column_agree_with_the_shared_helper() -> None:
    """The mirror uses a cached table and a binary search; the shared helper
    counts newlines. They must not be able to disagree, so the answer is
    checked against it rather than against a hand-written expectation."""
    from quill.core.marks import line_column_for_position

    text = "alpha\nbravo charlie\n\ndelta\n"
    doc = DocumentText(lambda: text)
    for position in range(-3, len(text) + 4):
        assert doc.line_column(position) == line_column_for_position(text, position)


def test_char_before_reads_one_character_and_not_the_document() -> None:
    doc = DocumentText(lambda: "abc")
    assert doc.char_before(0) == ""
    assert doc.char_before(1) == "a"
    assert doc.char_before(3) == "c"
    assert doc.char_before(4) == ""
    assert doc.char_before(-5) == ""


def test_an_empty_document_answers_without_special_casing() -> None:
    doc = DocumentText(lambda: "")
    assert doc.text == ""
    assert doc.stats().lines == 0
    assert doc.line_starts() == [0]
    assert doc.line_column(0) == (1, 1)
