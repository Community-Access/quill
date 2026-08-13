"""Unit tests for the bounded keystroke memory behind system-wide expansion.

The limits asserted here are the privacy contract, not implementation detail:
if any of these change, the user guide and PRD are wrong.
"""

from __future__ import annotations

from quill.core.expansion.ring_buffer import MAX_LENGTH, RingBuffer


def test_push_and_read_back() -> None:
    buffer = RingBuffer()
    for char in "hello":
        buffer.push(char)
    assert buffer.text() == "hello"
    assert len(buffer) == 5


def test_is_bounded_and_drops_the_oldest() -> None:
    buffer = RingBuffer(maxlen=4)
    for char in "abcdef":
        buffer.push(char)
    assert buffer.text() == "cdef"
    assert len(buffer) == 4


def test_default_bound_is_the_documented_one() -> None:
    buffer = RingBuffer()
    for _ in range(MAX_LENGTH * 2):
        buffer.push("x")
    assert len(buffer) == MAX_LENGTH


def test_backspace_forgets_one_character() -> None:
    buffer = RingBuffer()
    for char in "word":
        buffer.push(char)
    buffer.backspace()
    assert buffer.text() == "wor"


def test_backspace_on_empty_is_harmless() -> None:
    buffer = RingBuffer()
    buffer.backspace()
    assert buffer.text() == ""


def test_clear_empties_it() -> None:
    buffer = RingBuffer()
    for char in "secret":
        buffer.push(char)
    buffer.clear()
    assert buffer.text() == ""
    assert len(buffer) == 0


def test_only_single_characters_are_kept() -> None:
    buffer = RingBuffer()
    buffer.push("ab")
    buffer.push("")
    buffer.push("c")
    assert buffer.text() == "c"
