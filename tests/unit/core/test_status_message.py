"""A status message stops being true, and the cell has to know when.

Reported as a question, which is the right way round: "if I go do a bunch of
edits and still see Find not found, that is a problem, is it not?" It is. Every
other cell in the bar answers a question that is still true a minute later; the
message cell holds the last thing that was said, which is true for about as
long as it takes to say it.
"""

from __future__ import annotations

from quill.core.status_message import (
    IDLE_MESSAGE,
    MESSAGE_TTL_SECONDS,
    StatusMessage,
    current_message,
)


def _said(text: str, *, at: float = 100.0, revision: int = 7) -> StatusMessage:
    return StatusMessage(text, at, revision)


def test_a_fresh_message_reads_back() -> None:
    message = _said("String not found")
    assert current_message(message, now=100.5, revision=7) == "String not found"


def test_nothing_said_reads_as_idle() -> None:
    assert current_message(None, now=100.0, revision=0) == IDLE_MESSAGE


def test_an_empty_message_reads_as_idle() -> None:
    """A cell with no text is a button with no name, not a silent one."""
    assert current_message(_said(""), now=100.0, revision=7) == IDLE_MESSAGE


def test_the_next_edit_clears_it() -> None:
    """The whole report. "String not found" must not survive the typing."""
    message = _said("String not found", revision=7)
    assert current_message(message, now=100.1, revision=8) == IDLE_MESSAGE


def test_it_survives_its_own_edit() -> None:
    """The revision is stamped *after* the edit that prompted the message, so
    "Replaced 3 occurrences" is still there to be read back a moment later."""
    message = _said("Replaced 3 occurrences", revision=9)
    assert current_message(message, now=100.1, revision=9) == "Replaced 3 occurrences"


def test_a_revision_going_backwards_clears_it_too() -> None:
    """Switching documents is a move as much as an edit is. The comparison is
    inequality rather than order, so a per-tab revision that drops does not
    resurrect the other document's message."""
    message = _said("Saved", revision=9)
    assert current_message(message, now=100.1, revision=2) == IDLE_MESSAGE


def test_it_ages_out_without_an_edit() -> None:
    """Somebody reading rather than typing would keep it forever otherwise."""
    message = _said("String not found", at=100.0)
    assert current_message(message, now=100.0 + MESSAGE_TTL_SECONDS, revision=7) == IDLE_MESSAGE


def test_it_lasts_long_enough_to_arrow_over_and_read() -> None:
    """The cell exists to be read back. Expiring in a couple of seconds would
    take away the thing it is for."""
    message = _said("String not found", at=100.0)
    assert current_message(message, now=110.0, revision=7) == "String not found"
