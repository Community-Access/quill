import re
from pathlib import Path

from quill.core.format_ops import (
    compute_line_statistics,
    continue_markdown_list,
    convert_indentation_to_spaces,
    convert_indentation_to_tabs,
    count_occurrences,
    decode_html_entities,
    delete_lines_containing,
    delete_lines_not_containing,
    describe_indent_depth,
    encode_html_entities,
    hex_dump,
    indent_lines,
    multi_replace,
    normalize_whitespace,
    outdent_lines,
    quote_lines,
    remove_duplicate_lines,
    remove_email_quote_markers,
    reverse_lines,
    shuffle_lines,
    sort_lines,
    sort_lines_by_length,
    sort_lines_numeric,
    strip_high_ascii,
    strip_html_tags,
    strip_low_ascii,
    toggle_block_comment,
    toggle_line_comment,
    trim_blank_lines,
    trim_trailing_whitespace,
    unquote_lines,
)


def test_indent_and_outdent_lines() -> None:
    indented, start, end = indent_lines("alpha\nbeta", 0, 10)
    assert indented == "    alpha\n    beta"
    assert (start, end) == (0, len(indented))

    outdented, _, _ = outdent_lines(indented, 0, len(indented))
    assert outdented == "alpha\nbeta"


def test_toggle_line_comment_prefix_style() -> None:
    text = "print('x')\nprint('y')\n"
    commented, _, _ = toggle_line_comment(text, 0, len(text), Path("script.py"))
    assert commented == "# print('x')\n# print('y')\n"

    uncommented, _, _ = toggle_line_comment(commented, 0, len(commented), Path("script.py"))
    assert uncommented == text


def test_toggle_line_comment_prefix_style_on_blank_line() -> None:
    commented, _, _ = toggle_line_comment("", 0, 0, Path("script.py"))
    assert commented == "# "


def test_toggle_comment_honors_pinned_profile_over_path() -> None:
    # A .txt file pinned to HTML/Python comments per the profile, not the name.
    from quill.core.language_profile import get_profile_by_name

    html = get_profile_by_name("HTML")
    python = get_profile_by_name("Python")
    text = "hello"
    html_line, _, _ = toggle_line_comment(text, 0, len(text), Path("note.txt"), html)
    assert html_line == "<!-- hello -->"
    py_line, _, _ = toggle_line_comment(text, 0, len(text), Path("note.txt"), python)
    assert py_line == "# hello"
    # Block comment likewise follows the profile.
    wrapped, _, _ = toggle_block_comment("alpha", 0, 5, Path("note.txt"), html)
    assert wrapped.startswith("<!--") and wrapped.endswith("-->")


def test_toggle_line_comment_html_style() -> None:
    text = "hello\nworld"
    commented, _, _ = toggle_line_comment(text, 0, len(text), Path("notes.md"))
    assert commented == "<!-- hello -->\n<!-- world -->"

    uncommented, _, _ = toggle_line_comment(commented, 0, len(commented), Path("notes.md"))
    assert uncommented == text


def test_toggle_line_comment_html_style_on_blank_line() -> None:
    commented, _, _ = toggle_line_comment("", 0, 0, Path("notes.md"))
    assert commented == "<!--  -->"


def test_toggle_block_comment_wraps_and_unwraps() -> None:
    wrapped, start, end = toggle_block_comment("alpha", 0, 5, Path("script.py"))
    assert wrapped == "/* alpha */"
    assert wrapped[start:end] == "/* alpha */"

    unwrapped, _, _ = toggle_block_comment(wrapped, 0, len(wrapped), Path("script.py"))
    assert unwrapped == "alpha"


def test_toggle_block_comment_insert_when_no_selection() -> None:
    updated, start, end = toggle_block_comment("", 0, 0, Path("notes.md"))
    assert updated == "<!--  -->"
    assert start == end == len("<!-- ")


def test_text_cleanup_helpers() -> None:
    text = "beta  \nalpha\t\nalpha\n"

    assert trim_trailing_whitespace(text) == "beta\nalpha\nalpha\n"
    assert normalize_whitespace(" one\t two \n\nthree   four ") == "one two\n\nthree four"
    assert sort_lines(text) == "alpha\nalpha\t\nbeta  \n"
    assert reverse_lines("one\ntwo\nthree") == "three\ntwo\none"
    assert remove_duplicate_lines("one\ntwo\none\nONE\n") == "one\ntwo\nONE\n"
    assert convert_indentation_to_spaces("\talpha\n  beta", 4) == "    alpha\n  beta"
    assert convert_indentation_to_tabs("        alpha\n  beta", 4) == "\t\talpha\n  beta"


def test_continue_markdown_list_for_bullets() -> None:
    source = "- item"
    result = continue_markdown_list(source, len(source))
    assert result is not None
    assert result.text == "- item\n- "
    assert result.exited_list is False


def test_continue_markdown_list_for_numbered_items() -> None:
    source = "2. next"
    result = continue_markdown_list(source, len(source))
    assert result is not None
    assert result.text == "2. next\n3. "
    assert result.exited_list is False


def test_continue_markdown_list_for_task_items() -> None:
    source = "- [x] done"
    result = continue_markdown_list(source, len(source))
    assert result is not None
    assert result.text == "- [x] done\n- [ ] "
    assert result.exited_list is False


def test_continue_markdown_list_exits_empty_item() -> None:
    source = "- "
    result = continue_markdown_list(source, len(source))
    assert result is not None
    assert result.text == ""
    assert result.caret == 0
    assert result.exited_list is True


# HTML / entity transforms (§4.22 EDS-21)


def test_strip_html_tags_removes_tags() -> None:
    assert strip_html_tags("<b>bold</b> and <i>italic</i>") == "bold and italic"


def test_strip_html_tags_leaves_plain_text_unchanged() -> None:
    assert strip_html_tags("no tags here") == "no tags here"


def test_decode_html_entities_unescapes_common() -> None:
    assert decode_html_entities("&lt;p&gt;Hello &amp; world&lt;/p&gt;") == "<p>Hello & world</p>"


def test_encode_html_entities_escapes_special_chars() -> None:
    assert encode_html_entities("<p>Hello & world</p>") == "&lt;p&gt;Hello &amp; world&lt;/p&gt;"


def test_encode_decode_roundtrip() -> None:
    original = 'say "hello" & <farewell>'
    assert decode_html_entities(encode_html_entities(original)) == original


# Line-level transforms (§4.22/§4.23 TextMonkey parity)


def test_trim_blank_lines_removes_leading_and_trailing() -> None:
    assert trim_blank_lines("\n\nhello\nworld\n\n") == "hello\nworld"


def test_trim_blank_lines_preserves_interior_blanks() -> None:
    assert trim_blank_lines("\none\n\ntwo\n") == "one\n\ntwo"


def test_trim_blank_lines_all_blank_returns_empty() -> None:
    assert trim_blank_lines("\n\n\n") == ""


def test_quote_lines_prefixes_non_blank() -> None:
    assert quote_lines("hello\nworld") == "> hello\n> world"


def test_quote_lines_skips_blank_lines() -> None:
    assert quote_lines("one\n\ntwo") == "> one\n\n> two"


def test_unquote_lines_strips_gt_space() -> None:
    assert unquote_lines("> hello\n> world") == "hello\nworld"


def test_unquote_lines_strips_bare_gt() -> None:
    assert unquote_lines(">hello") == "hello"


def test_unquote_lines_leaves_unquoted_unchanged() -> None:
    assert unquote_lines("no quote here") == "no quote here"


def test_quote_unquote_roundtrip() -> None:
    original = "alpha\nbeta\ngamma"
    assert unquote_lines(quote_lines(original)) == original


def test_shuffle_lines_preserves_line_set() -> None:
    text = "a\nb\nc\nd\ne"
    result = shuffle_lines(text)
    assert sorted(result.splitlines()) == sorted(text.splitlines())


def test_sort_lines_numeric_ascending() -> None:
    result = sort_lines_numeric("10 items\n2 things\n50 widgets")
    assert result.splitlines()[0].startswith("2")
    assert result.splitlines()[-1].startswith("50")


def test_sort_lines_numeric_descending() -> None:
    result = sort_lines_numeric("1\n100\n10", descending=True)
    assert result.splitlines()[0] == "100"
    assert result.splitlines()[-1] == "1"


def test_sort_lines_numeric_non_numeric_lines_go_last() -> None:
    result = sort_lines_numeric("hello\n3\n1")
    lines = result.splitlines()
    assert lines[0] == "1"
    assert lines[1] == "3"
    assert lines[2] == "hello"


def test_sort_lines_by_length_ascending() -> None:
    result = sort_lines_by_length("longline\nhi\nmediumlen")
    lines = result.splitlines()
    assert lines[0] == "hi"
    assert lines[-1] == "mediumlen"


def test_sort_lines_by_length_descending() -> None:
    result = sort_lines_by_length("longline\nhi\nmediumlen", descending=True)
    assert result.splitlines()[0] == "mediumlen"
    assert result.splitlines()[-1] == "hi"


def test_delete_lines_containing_removes_matching() -> None:
    text = "keep this\ndelete me\nalso keep"
    result = delete_lines_containing(text, "delete")
    assert "delete me" not in result
    assert "keep this" in result
    assert "also keep" in result


def test_delete_lines_containing_case_insensitive() -> None:
    result = delete_lines_containing("Hello\nworld", "hello", case_sensitive=False)
    assert "Hello" not in result
    assert "world" in result


def test_delete_lines_containing_invalid_pattern_raises() -> None:
    import pytest

    with pytest.raises(re.error):
        delete_lines_containing("text", "[invalid")


def test_delete_lines_not_containing_keeps_matching() -> None:
    text = "alpha\nbeta\ngamma"
    result = delete_lines_not_containing(text, "beta")
    assert result.strip() == "beta"


def test_delete_lines_not_containing_case_insensitive() -> None:
    result = delete_lines_not_containing("Alpha\nbeta", "alpha", case_sensitive=False)
    assert "Alpha" in result
    assert "beta" not in result


def test_remove_email_quote_markers_strips_leading_chevrons() -> None:
    text = "> quoted line\n>> double quoted\nplain line"
    result = remove_email_quote_markers(text)
    assert result == "quoted line\ndouble quoted\nplain line"


def test_remove_email_quote_markers_strips_name_prefix() -> None:
    text = "Joe> said hello"
    assert remove_email_quote_markers(text) == "said hello"


def test_strip_low_ascii_removes_control_chars_keeps_tab_and_newline() -> None:
    text = "a\x07b\tc\nd"
    assert strip_low_ascii(text) == "ab\tc\nd"


def test_strip_high_ascii_keeps_plain_ascii_only() -> None:
    assert strip_high_ascii("café 中 plain") == "caf  plain"


def test_hex_dump_formats_offset_hex_and_ascii() -> None:
    result = hex_dump("AB")
    assert result.startswith("00000000  ")
    assert "41 42" in result
    assert result.endswith("AB")


def test_hex_dump_wraps_at_bytes_per_line() -> None:
    result = hex_dump("A" * 17)
    lines = result.splitlines()
    assert len(lines) == 2
    assert lines[1].startswith("00000010")


def test_multi_replace_applies_pairs_in_order() -> None:
    result = multi_replace("a b c", [("a", "1"), ("b", "2"), ("c", "3")])
    assert result == "1 2 3"


def test_multi_replace_skips_empty_search() -> None:
    assert multi_replace("hello world", [("", "x"), ("world", "there")]) == "hello there"


def test_multi_replace_case_insensitive() -> None:
    result = multi_replace("Hello HELLO", [("hello", "hi")], case_sensitive=False)
    assert result == "hi hi"


def test_multi_replace_case_sensitive_default() -> None:
    result = multi_replace("Hello hello", [("hello", "hi")])
    assert result == "Hello hi"


def test_count_occurrences_basic() -> None:
    assert count_occurrences("ababab", "ab") == 3


def test_count_occurrences_empty_needle() -> None:
    assert count_occurrences("text", "") == 0


def test_count_occurrences_case_insensitive() -> None:
    assert count_occurrences("Cat cat CAT", "cat", case_sensitive=False) == 3


def test_compute_line_statistics_no_numbers() -> None:
    assert compute_line_statistics("hello\nworld") == "No numeric lines were found."


def test_compute_line_statistics_reports_values() -> None:
    report = compute_line_statistics("1\n2\n3\n4\n5")
    assert "Numeric lines: 5" in report
    assert "Total: 15" in report
    assert "Average: 3" in report
    assert "Median: 3" in report
    assert "Standard deviation" in report


def test_compute_line_statistics_single_value_skips_stdev() -> None:
    report = compute_line_statistics("42")
    assert "Standard deviation: not enough data" in report


def test_describe_indent_depth_spaces() -> None:
    # Caret on the second line, which has four leading spaces.
    text = "top\n    body"
    assert describe_indent_depth(text, len(text)) == "4 spaces"


def test_describe_indent_depth_single_space_is_singular() -> None:
    assert describe_indent_depth(" x", 2) == "1 space"


def test_describe_indent_depth_tabs() -> None:
    assert describe_indent_depth("\t\tx", 3) == "2 tabs"
    assert describe_indent_depth("\tx", 2) == "1 tab"


def test_describe_indent_depth_none() -> None:
    assert describe_indent_depth("flush", 5) == "No indentation"


def test_describe_indent_depth_mixed_tabs_and_spaces() -> None:
    assert describe_indent_depth("\t  x", 4) == "1 tab, 2 spaces"


def test_describe_indent_depth_is_line_local() -> None:
    # The depth describes the caret's line only, not earlier lines.
    text = "        deep\nb"
    assert describe_indent_depth(text, len(text)) == "No indentation"


def test_describe_indent_depth_clamps_out_of_range_caret() -> None:
    assert describe_indent_depth("    x", 999) == "4 spaces"
    assert describe_indent_depth("    x", -5) == "4 spaces"
