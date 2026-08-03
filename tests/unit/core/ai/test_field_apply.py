"""Field-by-field apply model (assessment finding 5e.38)."""

from __future__ import annotations

from quill.core.ai.field_apply import ApplySession, FieldSuggestion, guess_target_field


def test_guess_prefers_exact_then_prefix_then_substring() -> None:
    fields = ["Title", "Subtitle", "summary_text", "tags"]
    assert guess_target_field(fields, "title") == "Title"
    assert guess_target_field(fields, "summary") == "summary_text"
    assert guess_target_field(fields, "sub") == "Subtitle"
    assert guess_target_field(fields, "narrator") == ""
    assert guess_target_field([], "title") == ""


def test_guess_ignores_case_and_punctuation() -> None:
    assert guess_target_field(["Reading List"], "reading-list") == "Reading List"


def test_suggestion_summary_previews_long_values() -> None:
    short = FieldSuggestion(field="title", value="A Title")
    assert short.summary() == "title: A Title"
    long = FieldSuggestion(field="summary", value="word " * 40)
    assert long.summary().endswith("...")
    assert len(long.summary()) < 80


def test_session_accept_skip_and_accepted_values() -> None:
    session = ApplySession(
        suggestions=[
            FieldSuggestion("title", "New Title"),
            FieldSuggestion("summary", "A summary."),
            FieldSuggestion("tags", "a, b"),
        ]
    )
    session.accept(0)
    session.skip(1)
    assert session.accepted_values() == {"title": "New Title"}
    assert "1 accepted, 1 skipped, 1 to review." == session.summary()


def test_next_pending_wraps_and_reports_exhaustion() -> None:
    session = ApplySession(
        suggestions=[FieldSuggestion("a", "1"), FieldSuggestion("b", "2")],
    )
    session.accept(1)
    assert session.next_pending(1) == 0
    session.accept(0)
    assert session.next_pending(0) == -1
