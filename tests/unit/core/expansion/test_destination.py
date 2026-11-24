"""FUX-07: what is said, and offered, when text is kept back from the wrong place."""

from __future__ import annotations

from quill.core.expansion.destination import HeldText, failure_reason, held_offer
from quill.core.external_text import (
    ExternalTextReason,
    OperationResult,
    OperationStatus,
    TargetSnapshot,
)

_PRIVATE = "my account number is 1234"


def _result(status: OperationStatus, reason: ExternalTextReason) -> OperationResult:
    return OperationResult(status, reason, "internal detail")


def test_typed_text_needs_no_offer() -> None:
    assert held_offer(_result(OperationStatus.APPLIED, ExternalTextReason.APPLIED)) is None


def test_a_moved_focus_offers_insert_and_copy_in_one_sentence() -> None:
    offer = held_offer(_result(OperationStatus.STALE, ExternalTextReason.STALE_TARGET))

    assert offer is not None
    assert offer.can_insert
    assert offer.sentence.count(".") == 1  # one sentence, said once
    assert "not where you started" in offer.sentence
    assert "Insert" in offer.sentence and "Copy" in offer.sentence


def test_a_password_field_offers_copy_only_and_says_windows_reported_it() -> None:
    offer = held_offer(_result(OperationStatus.PROTECTED, ExternalTextReason.PROTECTED_TARGET))

    assert offer is not None
    assert not offer.can_insert
    assert "Windows reports a password field" in offer.sentence


def test_part_typed_never_offers_insert_again() -> None:
    offer = held_offer(_result(OperationStatus.FAILED, ExternalTextReason.PARTIAL_INJECTION))

    assert offer is not None
    assert not offer.can_insert
    assert offer.sentence.startswith("Only part of the text was typed")


def test_the_reason_never_carries_the_internal_message() -> None:
    result = _result(OperationStatus.FAILED, ExternalTextReason.FAILED)

    assert "internal" not in failure_reason(result)
    assert "internal" not in str(held_offer(result))


def test_held_text_never_shows_its_words_in_a_log_line() -> None:
    target = TargetSnapshot(target_id="t", window_handle=7)
    held = HeldText(_PRIVATE, target)

    assert _PRIVATE not in repr(held)
    assert held.window == 7
    assert HeldText(_PRIVATE, None).window == 0


def test_a_partly_typed_expansion_is_never_called_not_expanded() -> None:
    from quill.core.expansion.destination import refusal_sentence

    partial = _result(OperationStatus.FAILED, ExternalTextReason.PARTIAL_INJECTION)
    assert refusal_sentence(partial, action="expanded") == "Only partly expanded; check the text."


def test_an_undo_in_another_window_says_the_focus_moved_there() -> None:
    from quill.core.expansion.destination import refusal_sentence

    moved = _result(OperationStatus.STALE, ExternalTextReason.STALE_TARGET)
    assert refusal_sentence(moved, action="undone") == (
        "Not undone, because the focus has moved to another window."
    )
