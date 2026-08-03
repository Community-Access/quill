"""Type-ahead buffer with the reference timings (hardening pass)."""

from __future__ import annotations

from quill.core.type_ahead import TypeAheadBuffer, find_match

NAMES = ["Apple", "Apricot", "Banana", "Blueberry", "Cherry"]


def test_find_match_wraps_from_the_current_selection() -> None:
    # From "Apple" (0), pressing "a" cycles to "Apricot", then wraps to "Apple".
    assert find_match(NAMES, "a", 0) == 1
    assert find_match(NAMES, "a", 1) == 0


def test_find_match_returns_minus_one_when_nothing_starts_with_query() -> None:
    assert find_match(NAMES, "z", 0) == -1
    assert find_match([], "a", 0) == -1


def test_multi_character_buffer_narrows_the_match() -> None:
    buffer = TypeAheadBuffer()
    assert buffer.press("b", NAMES, 0, now=10.0).index == 2  # Banana
    assert buffer.press("l", NAMES, 2, now=10.3).index == 3  # "bl" -> Blueberry


def test_buffer_times_out_and_restarts() -> None:
    buffer = TypeAheadBuffer()
    buffer.press("b", NAMES, 0, now=10.0)
    # 1.2 s later the buffer is stale; "c" is a fresh single-letter search.
    assert buffer.press("c", NAMES, 0, now=11.5).index == 4  # Cherry


def test_failed_multi_char_buffer_retries_with_last_character() -> None:
    buffer = TypeAheadBuffer()
    buffer.press("b", NAMES, 0, now=10.0)
    # "bc" matches nothing, but the trailing "c" alone finds Cherry: the user
    # started a new search without waiting for the timeout.
    result = buffer.press("c", NAMES, 0, now=10.2)
    assert result.index == 4
    assert result.query == "c"
    assert not result.failed


def test_total_failure_is_reported_for_speech() -> None:
    buffer = TypeAheadBuffer()
    result = buffer.press("z", NAMES, 0, now=10.0)
    assert result.index == -1
    assert result.failed
    assert result.query == "z"  # the caller speaks: No match for z


def test_keystrokes_are_suppressed_right_after_the_surface_opens() -> None:
    buffer = TypeAheadBuffer()
    buffer.surface_opened(now=10.0)
    # A keystroke still in flight from launching the window must not select.
    swallowed = buffer.press("b", NAMES, 0, now=10.4)
    assert swallowed.index == -1
    assert not swallowed.failed
    # After the 800 ms window, typing works normally.
    assert buffer.press("b", NAMES, 0, now=11.0).index == 2
