"""Unit tests for quill.core.encoding_tools (issue #197)."""

from __future__ import annotations

from quill.core.encoding_tools import (
    ENCODING_CHOICES,
    encode_non_ascii_to_entities,
    find_non_ascii,
    reencode_text,
    summarize_non_ascii,
)


class TestFindNonAscii:
    def test_pure_ascii_finds_nothing(self) -> None:
        assert find_non_ascii("hello world\nplain text\n") == []

    def test_locates_char_with_line_and_column(self) -> None:
        occ = find_non_ascii("abc\nxéz\n")  # é on line 2, column 2
        assert len(occ) == 1
        assert occ[0].line == 2
        assert occ[0].column == 2
        assert occ[0].char == "é"
        assert occ[0].codepoint == 0xE9
        assert "E" in occ[0].name  # LATIN SMALL LETTER E WITH ACUTE

    def test_latin1_and_cp1252_flags(self) -> None:
        # é fits Latin-1; the em dash (U+2014) does not, but fits cp1252.
        occ = {o.char: o for o in find_non_ascii("é—中")}
        assert occ["é"].latin1_ok and occ["é"].cp1252_ok
        assert not occ["—"].latin1_ok and occ["—"].cp1252_ok
        # A CJK char fits neither.
        assert not occ["中"].latin1_ok and not occ["中"].cp1252_ok


class TestSummarize:
    def test_pure_ascii_message(self) -> None:
        assert "pure ASCII" in summarize_non_ascii("just ascii\n")

    def test_reports_count_and_lossy_section(self) -> None:
        report = summarize_non_ascii("café 中\n")
        assert "Found 2 non-ASCII" in report
        assert "cannot be converted losslessly to Windows-1252" in report
        assert "U+4E2D" in report


class TestEncodeEntities:
    def test_named_entity_for_known_char(self) -> None:
        assert encode_non_ascii_to_entities("café") == "caf&eacute;"

    def test_numeric_fallback_for_unnamed(self) -> None:
        # CJK has no HTML named entity -> numeric.
        assert encode_non_ascii_to_entities("中") == "&#20013;"

    def test_ascii_and_markup_left_untouched(self) -> None:
        # & and < are ASCII and must not be escaped by this transform.
        assert encode_non_ascii_to_entities("a & b < c") == "a & b < c"

    def test_numeric_only_when_named_disabled(self) -> None:
        assert encode_non_ascii_to_entities("café", prefer_named=False) == "caf&#233;"


class TestReencode:
    def test_utf8_roundtrips(self) -> None:
        data = reencode_text("café 中", "utf-8")
        assert data.decode("utf-8") == "café 中"

    def test_utf8_sig_has_bom(self) -> None:
        data = reencode_text("x", "utf-8-sig")
        assert data.startswith(b"\xef\xbb\xbf")

    def test_ascii_uses_numeric_entities_for_non_ascii(self) -> None:
        # No data loss: the em dash becomes a numeric entity, not "?".
        assert reencode_text("a—b", "ascii") == b"a&#8212;b"

    def test_latin1_keeps_representable_bytes(self) -> None:
        assert reencode_text("café", "latin-1") == b"caf\xe9"

    def test_cp1252_falls_back_to_entity_for_unrepresentable(self) -> None:
        assert reencode_text("中", "cp1252") == b"&#20013;"


def test_encoding_choices_are_well_formed() -> None:
    assert ENCODING_CHOICES
    for codec, label in ENCODING_CHOICES:
        assert isinstance(codec, str) and codec
        assert isinstance(label, str) and label
        # Every advertised codec must be usable by reencode_text.
        assert isinstance(reencode_text("test", codec), bytes)
