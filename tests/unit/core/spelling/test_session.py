"""Unit tests for quill.core.spelling.session.ReviewSession."""

from quill.core.spelling.session import ReviewSession, _case_match

SMALL_DICT: set[str] = {
    "the",
    "cat",
    "sat",
    "on",
    "mat",
    "quick",
    "brown",
    "fox",
    "jumped",
    "over",
    "lazy",
    "dog",
    "hello",
    "world",
    "is",
    "a",
    "test",
    "this",
    "accommodate",
    "separate",
    "definitely",
}


def _session(text: str, dictionary: set[str] | None = None) -> ReviewSession:
    d = dictionary if dictionary is not None else SMALL_DICT
    return ReviewSession(text=text, dictionary=d)


# ------------------------------------------------------------------
# Basic issue detection
# ------------------------------------------------------------------


def test_no_issues_on_clean_text():
    s = _session("the cat sat on the mat")
    assert s.is_complete()
    assert s.total() == 0


def test_detects_single_misspelling():
    s = _session("the cat satt on the mat")
    assert not s.is_complete()
    assert s.total() >= 1
    issue = s.current()
    assert issue is not None
    assert issue.word == "satt"


def test_total_includes_all_issues():
    s = _session("teh catt sat on teh maat")
    assert s.total() >= 2


def test_position_starts_at_one():
    s = _session("teh cat")
    assert s.position() == 1


# ------------------------------------------------------------------
# apply_change
# ------------------------------------------------------------------


def test_apply_change_returns_op():
    s = _session("the catt sat")
    ops = s.apply_change("cat")
    assert len(ops) == 1
    start, old_end, repl = ops[0]
    assert repl == "cat"
    assert start >= 0
    assert old_end > start


def test_apply_change_advances_to_next():
    s = _session("teh catt sat")
    s.apply_change("the")
    # After changing "teh" → "the", next issue should be "catt".
    if not s.is_complete():
        issue = s.current()
        assert issue is not None
        assert issue.word == "catt"


def test_apply_change_updates_counters():
    s = _session("teh cat")
    s.apply_change("the")
    c = s.get_counters()
    assert c.changed == 1
    assert c.reviewed == 1


# ------------------------------------------------------------------
# apply_change_all
# ------------------------------------------------------------------


def test_change_all_replaces_all_occurrences():
    s = _session("teh cat and teh dog")
    ops = s.apply_change_all("the")
    # Both "teh" occurrences should be replaced.
    assert len(ops) == 2


def test_change_all_updates_counters():
    s = _session("teh cat teh dog")
    s.apply_change_all("the")
    c = s.get_counters()
    assert c.changed_all == 2


# ------------------------------------------------------------------
# apply_ignore_once
# ------------------------------------------------------------------


def test_ignore_once_advances_index():
    s = _session("teh catt sat")
    s.apply_ignore_once()
    assert s.position() == 2


def test_ignore_once_counted():
    s = _session("teh cat")
    s.apply_ignore_once()
    assert s.get_counters().ignored_once == 1


# ------------------------------------------------------------------
# apply_ignore_all
# ------------------------------------------------------------------


def test_ignore_all_removes_word_from_session():
    s = _session("teh cat and teh dog")
    # "teh" appears twice
    s.apply_ignore_all()
    # After ignore_all, "teh" should not appear in any remaining issue.
    remaining = []
    while not s.is_complete():
        issue = s.current()
        if issue:
            remaining.append(issue.word.lower())
        s.apply_ignore_once()
    assert "teh" not in remaining


# ------------------------------------------------------------------
# undo
# ------------------------------------------------------------------


def test_undo_change_restores_text():
    s = _session("teh cat")
    s.apply_change("the")
    assert s.get_counters().changed == 1
    undo_ops = s.undo_last()
    assert s.get_counters().changed == 0
    # Undo op should restore original word.
    assert len(undo_ops) == 1
    _, _, repl = undo_ops[0]
    assert repl == "teh"


def test_undo_ignore_once_restores_issue():
    s = _session("teh cat")
    s.apply_ignore_once()
    assert s.position() == 2 or s.is_complete()
    s.undo_last()
    assert s.position() == 1
    assert not s.is_complete()


def test_can_undo_false_initially():
    s = _session("teh cat")
    assert not s.can_undo()


def test_can_undo_true_after_action():
    s = _session("teh cat")
    s.apply_ignore_once()
    assert s.can_undo()


# ------------------------------------------------------------------
# Scope
# ------------------------------------------------------------------


def test_scope_limits_issues():
    text = "teh cat teh dog"
    # Only check the first "teh" (first 3 chars).
    s = ReviewSession(text=text, dictionary=SMALL_DICT, scope_start=0, scope_end=3)
    assert s.total() == 1


def test_scope_excludes_out_of_range():
    text = "good text teh bad"
    ws = text.index("teh")
    s = ReviewSession(text=text, dictionary=SMALL_DICT, scope_start=0, scope_end=ws)
    assert s.total() == 0


# ------------------------------------------------------------------
# Case matching helper
# ------------------------------------------------------------------


def test_case_match_upper():
    assert _case_match("TEH", "the") == "THE"


def test_case_match_title():
    assert _case_match("Teh", "the") == "The"


def test_case_match_lower():
    assert _case_match("teh", "the") == "the"
