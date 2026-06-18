from quill.core.line_ops import (
    chunk_span,
    delete_line,
    delete_paragraph,
    delete_to_document_end,
    delete_to_document_start,
    delete_to_line_end,
    delete_to_line_start,
    duplicate_line,
    first_non_blank_position,
    join_paragraph,
    join_selected_lines,
    join_with_next_line,
    last_non_blank_position,
    move_line_down,
    move_line_up,
    move_lines_down,
    move_lines_up,
    number_lines,
    number_lines_advanced,
    selected_line_bounds,
    to_roman_numeral,
)


def test_duplicate_line() -> None:
    updated, cursor = duplicate_line("a\nb\nc", 2)
    assert updated == "a\nb\nb\nc"
    assert cursor > 0


def test_delete_line() -> None:
    updated, _ = delete_line("a\nb\nc", 2)
    assert updated == "a\nc"


def test_move_line_up() -> None:
    updated, _ = move_line_up("a\nb\nc", 2)
    assert updated == "b\na\nc"


def test_move_line_down() -> None:
    updated, _ = move_line_down("a\nb\nc", 2)
    assert updated == "a\nc\nb"


def test_join_with_next_line() -> None:
    updated, _ = join_with_next_line("a\nb\nc", 0)
    assert updated == "a b\nc"


def test_move_lines_up_moves_whole_selection() -> None:
    # Select line3 and line4 (issue #133): both move, not just the first.
    text = "line1\nline2\nline3\nline4"
    start = text.index("line3")
    end = len(text)
    updated, new_start, new_end = move_lines_up(text, start, end)
    assert updated == "line1\nline3\nline4\nline2"
    assert updated[new_start:new_end] == "line3\nline4"


def test_move_lines_down_moves_whole_selection() -> None:
    text = "line1\nline2\nline3\nline4"
    start = text.index("line1")
    end = text.index("line2") + len("line2")
    updated, new_start, new_end = move_lines_down(text, start, end)
    assert updated == "line3\nline1\nline2\nline4"
    assert updated[new_start:new_end] == "line1\nline2"


def test_move_lines_up_single_line_without_selection() -> None:
    text = "a\nb\nc"
    caret = text.index("b")
    updated, _start, _end = move_lines_up(text, caret, caret)
    assert updated == "b\na\nc"


def test_move_lines_up_at_top_is_noop() -> None:
    text = "a\nb\nc"
    updated, start, end = move_lines_up(text, 0, 0)
    assert updated == text
    assert (start, end) == (0, 0)


def test_selected_line_bounds_counts_selected_lines() -> None:
    text = "line1\nline2\nline3\nline4"
    # Caret with no selection spans a single line.
    assert selected_line_bounds(text, 0, 0) == (0, 0)
    # Selecting line3 through end of line4 spans two lines.
    start = text.index("line3")
    first, last = selected_line_bounds(text, start, len(text))
    assert (first, last) == (2, 3)
    assert last - first + 1 == 2


def test_selected_line_bounds_excludes_trailing_line_start() -> None:
    # A selection ending exactly at a line start does not pull in the next line.
    text = "a\nb\nc"
    start = 0
    end = text.index("b")  # end sits at the start of line "b"
    assert selected_line_bounds(text, start, end) == (0, 0)


def test_join_selected_lines_collapses_whole_selection() -> None:
    # Issue #135: each word on its own line, select all, join -> one line.
    text = "this\nis\na\ntest\nof\nthe\neditor"
    updated, new_start, new_end = join_selected_lines(text, 0, len(text))
    assert updated == "this is a test of the editor"
    assert updated[new_start:new_end] == "this is a test of the editor"


def test_join_selected_lines_preserves_paragraph_breaks() -> None:
    text = "one\ntwo\n\nthree\nfour"
    updated, _start, _end = join_selected_lines(text, 0, len(text))
    assert updated == "one two\n\nthree four"


def test_join_paragraph_without_selection() -> None:
    text = "this\nis\na\ntest\n\nnext para"
    caret = text.index("this")
    updated, cursor = join_paragraph(text, caret)
    assert updated == "this is a test\n\nnext para"
    assert cursor == 0


def test_join_paragraph_on_blank_line_is_noop() -> None:
    text = "a\n\nb"
    blank = text.index("\n\n") + 1
    updated, cursor = join_paragraph(text, blank)
    assert updated == text
    assert cursor == blank


def test_number_lines_start_value() -> None:
    assert number_lines("a\nb\nc", start=5) == "5. a\n6. b\n7. c"


def test_number_lines_skips_blank_lines() -> None:
    assert number_lines("a\n\nb", start=1) == "1. a\n\n2. b"


def test_delete_to_line_start() -> None:
    text = "hello world"
    updated, cursor = delete_to_line_start(text, 6)
    assert updated == "world"
    assert cursor == 0


def test_delete_to_line_end() -> None:
    text = "hello world\nnext"
    updated, cursor = delete_to_line_end(text, 5)
    assert updated == "hello\nnext"
    assert cursor == 5


def test_delete_to_document_start() -> None:
    updated, cursor = delete_to_document_start("abc\ndef", 4)
    assert updated == "def"
    assert cursor == 0


def test_delete_to_document_end() -> None:
    updated, cursor = delete_to_document_end("abc\ndef", 4)
    assert updated == "abc\n"
    assert cursor == 4


def test_delete_paragraph() -> None:
    text = "one\ntwo\n\nthree\nfour"
    updated, _ = delete_paragraph(text, 0)
    assert updated == "three\nfour"


def test_first_non_blank_position() -> None:
    text = "    indented"
    assert first_non_blank_position(text, 8) == 4


def test_last_non_blank_position() -> None:
    text = "trailing   "
    assert last_non_blank_position(text, 0) == len("trailing")


# chunk_span tests (§4.22 EdSharp parity)


def test_chunk_span_selects_word() -> None:
    text = "hello world"
    start, end = chunk_span(text, 2)
    assert (start, end) == (0, 5)
    assert text[start:end] == "hello"


def test_chunk_span_selects_word_at_end_boundary() -> None:
    text = "hello world"
    start, end = chunk_span(text, 9)
    assert (start, end) == (6, 11)
    assert text[start:end] == "world"


def test_chunk_span_selects_whitespace_run() -> None:
    text = "foo   bar"
    start, end = chunk_span(text, 4)
    assert (start, end) == (3, 6)
    assert text[start:end] == "   "


def test_chunk_span_selects_punctuation_run() -> None:
    text = "hello...world"
    start, end = chunk_span(text, 7)
    assert (start, end) == (5, 8)
    assert text[start:end] == "..."


def test_chunk_span_empty_text_returns_cursor() -> None:
    assert chunk_span("", 0) == (0, 0)


def test_chunk_span_cursor_past_end_clamps() -> None:
    text = "abc"
    start, end = chunk_span(text, 99)
    assert start == 0
    assert end == 3


def test_chunk_span_underscore_is_word_char() -> None:
    text = "my_var = 1"
    start, end = chunk_span(text, 3)
    assert text[start:end] == "my_var"


# Advanced line numbering (TextMonkey-parity gap fill)


def test_to_roman_numeral_basic_values() -> None:
    assert to_roman_numeral(1) == "I"
    assert to_roman_numeral(4) == "IV"
    assert to_roman_numeral(9) == "IX"
    assert to_roman_numeral(40) == "XL"
    assert to_roman_numeral(90) == "XC"
    assert to_roman_numeral(400) == "CD"
    assert to_roman_numeral(1994) == "MCMXCIV"


def test_to_roman_numeral_rejects_non_positive() -> None:
    import pytest

    with pytest.raises(ValueError):
        to_roman_numeral(0)
    with pytest.raises(ValueError):
        to_roman_numeral(-5)


def test_number_lines_advanced_increment() -> None:
    result = number_lines_advanced("a\nb\nc", start=10, increment=5)
    assert result == "10. a\n15. b\n20. c"


def test_number_lines_advanced_roman_style() -> None:
    # Numbers share a left-justified column width across the widest rendered
    # numeral (III = 3 chars), so shorter numerals pick up trailing padding.
    result = number_lines_advanced("a\nb\nc", start=1, style="roman")
    assert result == "I  . a\nII . b\nIII. c"


def test_number_lines_advanced_padding_zero_fills() -> None:
    result = number_lines_advanced("a\nb\nc", start=8, pad_width=3)
    assert result == "008. a\n009. b\n010. c"


def test_number_lines_advanced_skips_blank_lines() -> None:
    result = number_lines_advanced("a\n\nb", start=1)
    assert result == "1. a\n\n2. b"


def test_number_lines_advanced_custom_suffix() -> None:
    result = number_lines_advanced("a\nb", start=1, suffix=") ")
    assert result == "1) a\n2) b"


def test_number_lines_advanced_right_align_pads_with_spaces() -> None:
    result = number_lines_advanced("a\nb\nc", start=9, align="right")
    lines = result.splitlines()
    # Right-aligned numbers share a common column width across all rendered numbers.
    widths = {len(line.split(".", 1)[0]) for line in lines}
    assert len(widths) == 1
