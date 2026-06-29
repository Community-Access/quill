from __future__ import annotations

from quill.core.char_describe import describe_character


def test_plain_letter() -> None:
    desc = describe_character("Abc", 0)
    assert "U+0041" in desc.summary
    assert "Uppercase letter" in desc.detail
    assert "decimal 65" in desc.detail


def test_end_of_document() -> None:
    desc = describe_character("hi", 2)
    assert "End of document" in desc.summary
    desc_empty = describe_character("", 0)
    assert "End of document" in desc_empty.summary


def test_no_break_space_is_named_and_noted() -> None:
    desc = describe_character(chr(0xA0), 0)
    assert "No-break space" in desc.summary
    assert "U+00A0" in desc.summary
    assert "never wraps" in desc.detail.lower()


def test_zero_width_space_flagged_invisible() -> None:
    desc = describe_character(chr(0x200B), 0)
    assert "Zero-width space" in desc.summary
    assert "U+200B" in desc.detail


def test_smart_quote_distinguished_from_apostrophe() -> None:
    desc = describe_character(chr(0x2019), 0)
    assert "Right single quotation mark" in desc.summary
    assert "curly" in desc.detail.lower()


def test_tab_and_newline() -> None:
    assert "Tab" in describe_character("\t", 0).summary
    assert "Line feed" in describe_character("\n", 0).summary


def test_non_ascii_note() -> None:
    desc = describe_character(chr(0xE9), 0)  # e with acute accent
    assert "non-ASCII" in desc.detail


def test_negative_position_clamped() -> None:
    desc = describe_character("hi", -5)
    assert "U+0068" in desc.summary  # 'h'
