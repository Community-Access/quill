"""The three sentences a screen reader cannot say (bad.md P3.7, P0.6c).

Approved 2026-09-16 as the magical tier. Each answers a question a sighted user
answers with a glance and a listener could not answer at all -- not because the
information is hidden, but because it is the *application's* own knowledge and
nothing was saying it.

The fourth of the four, repeat the last announcement, shipped as #1304.
"""

from __future__ import annotations

from quill.core.document_text import DocumentText, EditRecord
from quill.core.list_structure import count_list_items
from quill.core.magical import (
    NOTHING_TO_REPORT,
    arrival_summary,
    describe_change,
    describe_undo,
)
from quill.core.metrics import compute_document_stats


def _record(action: str, before: str, after: str, position: int = -1) -> EditRecord:
    return DocumentText(lambda: after).record(action, before, after, position=position)


# -- the journal ---------------------------------------------------------------


def test_the_journal_records_sizes_not_the_text() -> None:
    """A journal holding what was typed is a journal holding a pasted password."""
    record = _record("Paste", "", "hunter2")

    assert record.characters_after == 7
    fields = {name: getattr(record, name) for name in record.__dataclass_fields__}
    assert not any("hunter2" in str(value) for value in fields.values())


def test_the_journal_is_bounded() -> None:
    mirror = DocumentText(lambda: "", journal_limit=3)
    for index in range(5):
        mirror.record(f"Edit {index}", "a", "b")

    journal = mirror.journal()
    assert len(journal) == 3
    assert [entry.action for entry in journal] == ["Edit 2", "Edit 3", "Edit 4"]
    assert mirror.last_edit is not None
    assert mirror.last_edit.action == "Edit 4"


def test_a_zero_limit_journal_records_nothing() -> None:
    mirror = DocumentText(lambda: "", journal_limit=0)
    mirror.record("Edit", "a", "b")
    assert mirror.journal() == ()
    assert mirror.last_edit is None


# -- following a revision ------------------------------------------------------


def test_syncing_to_an_unchanged_revision_reads_nothing_again() -> None:
    reads: list[int] = []

    def _read() -> str:
        reads.append(1)
        return "hello"

    mirror = DocumentText(_read)
    mirror.sync_to(7)
    assert mirror.stats().words == 1
    mirror.sync_to(7)
    mirror.sync_to(7)
    assert mirror.stats().words == 1
    assert len(reads) == 1, "an unchanged revision must not re-read the document"


def test_syncing_to_a_moved_revision_re_reads() -> None:
    text = ["one"]
    mirror = DocumentText(lambda: text[0])
    assert mirror.stats().words == 1

    text[0] = "one two three"
    assert mirror.sync_to(2) is True
    assert mirror.stats().words == 3


def test_no_revision_at_all_means_never_trust_the_mirror() -> None:
    """A bare stub with no counter: honest beats fast."""
    text = ["one"]
    mirror = DocumentText(lambda: text[0])
    mirror.sync_to(None)
    text[0] = "one two"
    assert mirror.sync_to(None) is True
    assert mirror.stats().words == 2


# -- what changed --------------------------------------------------------------


def test_nothing_recorded_is_answered_not_left_silent() -> None:
    assert describe_change(None) == NOTHING_TO_REPORT


def test_a_reordering_says_the_length_did_not_move() -> None:
    said = describe_change(_record("Sorted lines ascending", "b\na", "a\nb", position=0))
    assert "Sorted lines ascending" in said
    assert "at position 0" in said
    assert "same length" in said


def test_a_removal_says_what_it_removed() -> None:
    said = describe_change(_record("Removed duplicate lines", "a\na\nb", "a\nb"))
    assert "over the whole document" in said
    assert "-1 lines" in said
    assert "-2 characters" in said


def test_an_addition_is_signed() -> None:
    said = describe_change(_record("Pasted from slot 1", "", "hello"))
    assert "+5 characters" in said


# -- undo ----------------------------------------------------------------------


def test_an_undo_with_nothing_to_undo_says_so() -> None:
    assert describe_undo(None, worked=False) == "Nothing left to undo."
    assert describe_undo(_record("Edit", "a", "b"), worked=False) == "Nothing left to undo."


def test_an_undo_reports_the_change_reversed() -> None:
    """Undoing an edit that removed two lines puts two lines back."""
    said = describe_undo(_record("Removed duplicate lines", "a\na\nb", "a\nb"), worked=True)
    assert said.startswith("Undone: Removed duplicate lines")
    assert "+1 lines" in said
    assert "+2 characters" in said


def test_an_undo_of_a_reordering_says_the_length_is_the_same() -> None:
    said = describe_undo(_record("Sorted lines", "b\na", "a\nb"), worked=True)
    assert "same length" in said


def test_an_undo_with_no_journal_still_confirms_it_happened() -> None:
    assert describe_undo(None, worked=True) == "Undone."


# -- arrival -------------------------------------------------------------------


def test_an_empty_document_says_it_is_empty() -> None:
    """Empty and failed-to-load sound identical; the difference is what to do."""
    said = arrival_summary(compute_document_stats(""), kind="Plain text")
    assert said == "Plain text: Empty document."


def test_the_summary_leads_with_size_then_shape() -> None:
    said = arrival_summary(
        compute_document_stats("# Title\n- one\n- two\n"),
        kind="Markdown",
        headings=1,
        list_items=2,
    )
    assert said.startswith("Markdown: ")
    assert "1 heading and 2 list items" in said


def test_a_document_with_no_headings_is_told_so() -> None:
    """Why Alt+Down will not move, said once rather than discovered by pressing."""
    said = arrival_summary(compute_document_stats("just prose here"))
    assert "No headings" in said


def test_read_only_comes_last_because_it_changes_what_you_do() -> None:
    said = arrival_summary(compute_document_stats("text"), read_only=True)
    assert said.endswith("Read-only.")


def test_the_summary_is_one_sentence_per_fact_and_ends_cleanly() -> None:
    said = arrival_summary(compute_document_stats("a\nb"), kind="Plain text", headings=2)
    assert said.count("..") == 0
    assert said.endswith(".")


# -- counting the list items the summary reports --------------------------------


def test_list_items_are_counted_from_the_real_scan() -> None:
    assert count_list_items("- one\n- two\ntext\n") == 2
    assert count_list_items("1. one\n2. two\n3. three\n") == 3
    assert count_list_items("nothing here") == 0


def test_a_bullet_inside_a_code_fence_is_not_a_list_item() -> None:
    """The reason to use the scan rather than grep for a hyphen."""
    assert count_list_items("```\n- not a list\n```\n") == 0
