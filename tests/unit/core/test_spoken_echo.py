from quill.core.spoken_echo import (
    SPOKEN_ECHO_LIMIT,
    format_spoken_echo,
    new_history,
    record_spoken,
)


def test_record_skips_empty_and_whitespace() -> None:
    history = new_history()
    assert record_spoken(history, "") is False
    assert record_spoken(history, "   ") is False
    assert record_spoken(history, None) is False
    assert list(history) == []


def test_record_trims_and_keeps() -> None:
    history = new_history()
    assert record_spoken(history, "  Saved  ") is True
    assert list(history) == ["Saved"]


def test_record_drops_consecutive_duplicate() -> None:
    history = new_history()
    assert record_spoken(history, "Modified") is True
    assert record_spoken(history, "Modified") is False
    # A non-consecutive repeat is allowed back in.
    assert record_spoken(history, "Saved") is True
    assert record_spoken(history, "Modified") is True
    assert list(history) == ["Modified", "Saved", "Modified"]


def test_history_is_bounded() -> None:
    history = new_history(limit=3)
    for i in range(10):
        record_spoken(history, f"line {i}")
    assert list(history) == ["line 7", "line 8", "line 9"]


def test_default_limit_applied() -> None:
    history = new_history()
    for i in range(SPOKEN_ECHO_LIMIT + 5):
        record_spoken(history, f"line {i}")
    assert len(history) == SPOKEN_ECHO_LIMIT


def test_format_newest_first_numbered() -> None:
    text = format_spoken_echo(["first", "second", "third"])
    assert text == "1. third\n2. second\n3. first"


def test_format_empty_history() -> None:
    assert format_spoken_echo([]) == "Nothing has been announced yet."
    assert format_spoken_echo(["  ", ""]) == "Nothing has been announced yet."
