"""Tests for the spoken credits texts (pure parts)."""

from __future__ import annotations

from quill.core.speech.credits import closing_credit_text, opening_credit_text


def test_opening_credit_full() -> None:
    assert (
        opening_credit_text("My Book", "Jane Doe", "Sam Reader")
        == "My Book. Written by Jane Doe. Narrated by Sam Reader."
    )


def test_opening_credit_drops_empty_fields() -> None:
    assert opening_credit_text("My Book") == "My Book."
    assert opening_credit_text("My Book", narrator="Sam") == "My Book. Narrated by Sam."


def test_closing_credit() -> None:
    assert closing_credit_text(" My Book ") == "This has been My Book. Thank you for listening."
