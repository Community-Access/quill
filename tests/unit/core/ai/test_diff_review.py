"""Line-by-line diff review model for AI edits (AI-7)."""

from __future__ import annotations

from quill.core.ai.diff_review import DiffHunk, build_diff_review


def test_no_changes_has_no_hunks() -> None:
    review = build_diff_review("alpha\nbeta", "alpha\nbeta")
    assert not review.has_changes
    assert review.hunks == []
    assert review.summary() == "No changes to review."
    # Applying nothing round-trips the original exactly.
    assert review.accept_all() == "alpha\nbeta"
    assert review.reject_all() == "alpha\nbeta"


def test_pure_addition_is_added_hunk() -> None:
    review = build_diff_review("line one", "line one\nline two")
    assert len(review.hunks) == 1
    hunk = review.hunks[0]
    assert hunk.kind == "added"
    assert hunk.new_lines == ("line two",)
    assert "Added 1 line" in hunk.describe()


def test_pure_deletion_is_removed_hunk() -> None:
    review = build_diff_review("keep\ndrop", "keep")
    assert len(review.hunks) == 1
    hunk = review.hunks[0]
    assert hunk.kind == "removed"
    assert hunk.old_lines == ("drop",)
    assert "Removed 1 line" in hunk.describe()


def test_replacement_is_changed_hunk() -> None:
    review = build_diff_review("before", "after")
    assert len(review.hunks) == 1
    hunk = review.hunks[0]
    assert hunk.kind == "changed"
    assert hunk.old_lines == ("before",)
    assert hunk.new_lines == ("after",)
    assert "Changed" in hunk.describe()


def test_accept_all_yields_revised() -> None:
    review = build_diff_review("a\nb\nc", "a\nB\nc\nd")
    assert review.accept_all() == "a\nB\nc\nd"


def test_reject_all_yields_original() -> None:
    review = build_diff_review("a\nb\nc", "a\nB\nc\nd")
    assert review.reject_all() == "a\nb\nc"


def test_partial_apply_accepts_only_selected_hunks() -> None:
    # Two independent hunks: change "b"->"B" and append "d".
    review = build_diff_review("a\nb\nc", "a\nB\nc\nd")
    assert len(review.hunks) == 2
    # Accept only the first hunk (the change), reject the addition.
    first_only = review.apply({review.hunks[0].index})
    assert first_only == "a\nB\nc"
    # Accept only the second hunk (the addition), reject the change.
    second_only = review.apply({review.hunks[1].index})
    assert second_only == "a\nb\nc\nd"


def test_trailing_newline_round_trips() -> None:
    original = "a\nb\n"
    revised = "a\nb\n"
    review = build_diff_review(original, revised)
    assert review.accept_all() == original
    # A change preserving the trailing newline does not gain or lose one.
    review2 = build_diff_review("a\nb\n", "a\nB\n")
    assert review2.accept_all() == "a\nB\n"
    assert review2.reject_all() == "a\nb\n"


def test_detail_lines_label_removed_and_added() -> None:
    review = build_diff_review("old text", "new text")
    detail = review.hunks[0].detail_lines()
    assert detail[0] == review.hunks[0].describe()
    assert any(line.startswith("- removed: old text") for line in detail)
    assert any(line.startswith("+ added: new text") for line in detail)


def test_detail_lines_mark_blank_lines() -> None:
    hunk = DiffHunk(index=0, kind="changed", old_lines=("",), new_lines=("x",), old_line_no=1)
    detail = hunk.detail_lines()
    assert "- removed: (blank line)" in detail
    assert "+ added: x" in detail


def test_summary_counts_each_kind() -> None:
    review = build_diff_review("a\nb\nc\nd", "a\nB\nc")
    summary = review.summary()
    assert "hunk" in summary
    # There is at least one change and one removal in this diff.
    assert review.has_changes


def test_old_line_no_is_one_based() -> None:
    review = build_diff_review("a\nb\nc", "a\nb\nC")
    assert review.hunks[0].old_line_no == 3


# -- word-level review with sentence context (plan item 3) -------------------


def test_single_word_change_is_described_at_word_level() -> None:
    original = "The quick brown fox jumps over the lazy dog. A second sentence here."
    revised = "The rapid brown fox jumps over the lazy dog. A second sentence here."
    review = build_diff_review(original, revised)

    assert len(review.hunks) == 1
    hunk = review.hunks[0]
    assert len(hunk.word_changes) == 1
    change = hunk.word_changes[0]
    assert change.old_words == "quick"
    assert change.new_words == "rapid"
    assert hunk.describe() == 'Changed "quick" to "rapid" at line 1.'


def test_word_change_carries_the_enclosing_sentence() -> None:
    original = "First sentence stays. The quick fox runs. Last sentence stays."
    revised = "First sentence stays. The rapid fox runs. Last sentence stays."
    review = build_diff_review(original, revised)

    change = review.hunks[0].word_changes[0]
    assert change.old_sentence == "The quick fox runs."
    assert change.new_sentence == "The rapid fox runs."


def test_adjacent_word_edits_merge_into_one_phrase() -> None:
    original = "The quick brown fox."
    revised = "The rapid red fox."
    review = build_diff_review(original, revised)

    changes = review.hunks[0].word_changes
    assert len(changes) == 1
    assert changes[0].old_words == "quick brown"
    assert changes[0].new_words == "rapid red"


def test_insertion_and_removal_inside_a_line_get_their_own_verbs() -> None:
    review = build_diff_review("The fox jumps.", "The very swift fox jumps.")
    change = review.hunks[0].word_changes[0]
    assert change.old_words == ""
    assert change.new_words == "very swift"
    assert change.action_phrase() == 'Inserted "very swift"'

    review2 = build_diff_review("The very swift fox jumps.", "The fox jumps.")
    change2 = review2.hunks[0].word_changes[0]
    assert change2.new_words == ""
    assert change2.action_phrase() == 'Removed "very swift"'


def test_short_rewrite_reads_as_one_phrase_change() -> None:
    # A short full-line rewrite still fits the phrase cap: one spoken pair
    # ("changed old line to new line") beats a removed/added line reading.
    original = "Alpha beta gamma delta."
    revised = "Completely different words here."
    review = build_diff_review(original, revised)

    hunk = review.hunks[0]
    assert len(hunk.word_changes) == 1
    assert hunk.word_changes[0].old_words == "Alpha beta gamma delta"


def test_wholesale_rewrite_degrades_to_line_hunks() -> None:
    # A long rewrite (phrases beyond the cap) is presented as lines: hearing
    # two 150-character "phrases" is worse than hearing the lines whole.
    original = "Alpha beta gamma delta epsilon zeta eta theta " * 4 + "end."
    revised = "Completely different words with nothing shared at all " * 4 + "done."
    review = build_diff_review(original, revised)

    hunk = review.hunks[0]
    assert hunk.word_changes == ()
    assert "Changed 1 line to 1 line" in hunk.describe()


def test_many_scattered_edits_degrade_to_line_hunks() -> None:
    # More than the per-hunk cap of distinct word edits -> line-level view.
    original = " ".join(f"word{i} filler{i}" for i in range(12))
    revised = " ".join(f"WORD{i} filler{i}" for i in range(12))
    review = build_diff_review(original, revised)

    assert review.hunks[0].word_changes == ()


def test_detail_lines_include_sentences_and_keep_full_lines() -> None:
    original = "Intro stays. The quick fox runs far. Outro stays."
    revised = "Intro stays. The rapid fox runs far. Outro stays."
    review = build_diff_review(original, revised)

    detail = review.hunks[0].detail_lines()
    assert detail[0] == review.hunks[0].describe()
    assert 'Changed "quick" to "rapid".' in detail
    assert "  Sentence before: The quick fox runs far." in detail
    assert "  Sentence after: The rapid fox runs far." in detail
    # The whole-line view is still there for full review.
    assert any(line.startswith("- removed: ") for line in detail)
    assert any(line.startswith("+ added: ") for line in detail)


def test_sentence_context_stops_at_line_breaks() -> None:
    original = "Heading line\nThe quick fox.\nAnother line"
    revised = "Heading line\nThe rapid fox.\nAnother line"
    review = build_diff_review(original, revised)

    change = review.hunks[0].word_changes[0]
    assert change.old_sentence == "The quick fox."


def test_spacing_only_change_stays_line_level() -> None:
    review = build_diff_review("word  spaced", "word spaced")
    assert review.hunks[0].word_changes == ()


def test_multiple_word_edits_summarised_as_phrases() -> None:
    original = "The quick fox ran. The tall dog slept."
    revised = "The rapid fox ran. The small dog slept."
    review = build_diff_review(original, revised)

    hunk = review.hunks[0]
    assert len(hunk.word_changes) == 2
    assert hunk.describe() == "Changed 2 phrases at line 1."


def test_apostrophe_words_stay_whole() -> None:
    review = build_diff_review("It doesn't work.", "It shouldn't work.")
    change = review.hunks[0].word_changes[0]
    assert change.old_words == "doesn't"
    assert change.new_words == "shouldn't"
