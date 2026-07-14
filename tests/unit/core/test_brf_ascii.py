"""Tests for :mod:`quill.core.brf_ascii` (Braille Mode BR-005)."""

from __future__ import annotations

import pytest

from quill.core.brf_ascii import (
    BRF_FORM_FEED,
    detect_line_endings,
    find_non_brf_ascii_offsets,
    is_brf_ascii_byte,
    strip_bom,
)


def test_is_brf_ascii_byte_accepts_nabcc_printable_range() -> None:
    """NABCC allows printable ASCII plus the standard whitespace controls."""
    for byte in (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0x41, 0x7E):
        assert is_brf_ascii_byte(byte), f"expected byte 0x{byte:02X} to be BRF-ASCII"
    for byte in (0x00, 0x08, 0x1B, 0x7F, 0x80, 0xC0, 0xFF):
        assert not is_brf_ascii_byte(byte), f"expected byte 0x{byte:02X} to be rejected"


def test_strip_bom_removes_utf8_bom_and_reports_presence() -> None:
    text, had_bom = strip_bom(b"\xef\xbb\xbfhello")
    assert text == "hello"
    assert had_bom is True


def test_strip_bom_passes_through_plain_ascii() -> None:
    text, had_bom = strip_bom(b"hello\r\nworld")
    assert text == "hello\r\nworld"
    assert had_bom is False


def test_strip_bom_keeps_form_feeds_and_trailing_spaces() -> None:
    payload = b",,,  PAGE 1   \r\n\x0c,,,\r\n"
    text, had_bom = strip_bom(payload)
    assert had_bom is False
    assert text.encode("utf-8") == payload


def test_find_non_brf_ascii_offsets_returns_sorted_offsets() -> None:
    text = "abc\x80def\u2800ghi"  # two non-BRF-ASCII codepoints
    offsets = find_non_brf_ascii_offsets(text)
    assert offsets == [3, 7]


def test_find_non_brf_ascii_offsets_empty_for_clean_brf() -> None:
    text = ",,,HELLO\r\n  \r\n\x0c"
    assert find_non_brf_ascii_offsets(text) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", (0, 0, 0, 0)),
        ("hello", (0, 0, 0, 0)),
        ("a\r\nb\r\n", (2, 0, 0, 0)),
        ("a\nb\n", (0, 2, 0, 0)),
        ("a\rb\r", (0, 0, 2, 0)),
        ("\r\n\n\r", (1, 1, 1, 0)),
        ("a\x0cb\x0c", (0, 0, 0, 2)),
    ],
)
def test_detect_line_endings_counts_each_kind_once(
    text: str, expected: tuple[int, int, int, int]
) -> None:
    report = detect_line_endings(text)
    assert (report.crlf, report.lf, report.cr, report.form_feed) == expected


def test_detect_line_endings_reports_mixed_when_more_than_one_kind() -> None:
    report = detect_line_endings("a\r\nb\nc")
    assert report.crlf == 1
    assert report.lf == 1
    assert report.cr == 0
    assert report.is_mixed is True
    assert report.dominant == "\r\n"


def test_detect_line_endings_reports_unmixed_for_single_kind() -> None:
    report = detect_line_endings("a\nb\nc")
    assert report.is_mixed is False
    assert report.dominant == "\n"


def test_detect_line_endings_empty_string_is_neutral() -> None:
    report = detect_line_endings("")
    assert report.is_mixed is False
    assert report.dominant == ""
    assert report.total == 0


def test_brf_form_feed_constant_matches_literal() -> None:
    assert BRF_FORM_FEED == "\x0c"


class TestLooksLikeBraille:
    def test_detects_ascii_braille(self) -> None:
        from quill.core.brf_ascii import looks_like_braille

        brf = (
            ",! QUICK ,BROWN ,FOX JUMPS OV} ! LAZY ,DOG4\n"
            "#A4 ,! FIRST C8APT}3 ,A ,TALE\n"
            ",?IS IS A L9E OF GRADE #B ,BRAILLE4\n"
            ",WE CONT9UE ) MORE ,BRAILLE TEXT 6 F NEXT L9E4\n"
        )
        assert looks_like_braille(brf) is True

    def test_rejects_ordinary_prose(self) -> None:
        from quill.core.brf_ascii import looks_like_braille

        prose = (
            "The quick brown fox jumps over the lazy dog. This is ordinary text "
            "with normal sentences and lowercase letters throughout the paragraph."
        )
        assert looks_like_braille(prose) is False

    def test_rejects_all_caps_text_without_braille_indicators(self) -> None:
        from quill.core.brf_ascii import looks_like_braille

        caps = (
            "ROSES ARE RED\nVIOLETS ARE BLUE\nSUGAR IS SWEET\nAND SO ARE YOU\n"
            "THIS IS AN ALL CAPS POEM WITH NO BRAILLE INDICATORS AT ALL HERE\n"
        )
        assert looks_like_braille(caps) is False

    def test_rejects_short_input(self) -> None:
        from quill.core.brf_ascii import looks_like_braille

        assert looks_like_braille(",A ,B #C") is False
