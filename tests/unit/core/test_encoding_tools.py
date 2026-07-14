"""Unit tests for quill.core.encoding_tools (issue #197)."""

from __future__ import annotations

from quill.core.encoding_tools import (
    ENCODING_CHOICES,
    ansi_to_oem,
    can_encode,
    convert_box_drawing_to_ascii,
    describe_minimum_encoding,
    encode_non_ascii_to_entities,
    find_non_ascii,
    minimum_encoding,
    oem_to_ansi,
    reencode_text,
    strip_box_drawing,
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


class TestCanEncode:
    def test_ascii_text_fits_ascii(self) -> None:
        assert can_encode("hello", "ascii") is True

    def test_em_dash_does_not_fit_ascii(self) -> None:
        assert can_encode("a—b", "ascii") is False


class TestMinimumEncoding:
    def test_pure_ascii_text(self) -> None:
        assert minimum_encoding("hello world") == "ascii"

    def test_latin1_required(self) -> None:
        # 13.5: Renée requires Latin-1 (not representable in plain ASCII).
        assert minimum_encoding("Renée") == "latin-1"

    def test_windows_1252_required_for_smart_quotes_and_dash(self) -> None:
        # 13.6: smart quotes + em dash are not in Latin-1 but are in cp1252.
        assert minimum_encoding("“Hello”—said Renée.") == "cp1252"

    def test_utf8_required_for_emoji(self) -> None:
        # 13.7: emoji require UTF-8.
        assert minimum_encoding("Hello \U0001f60a") == "utf-8"


class TestOemAnsiConversion:
    def test_ascii_text_is_unchanged_either_direction(self) -> None:
        assert oem_to_ansi("hello world") == "hello world"
        assert ansi_to_oem("hello world") == "hello world"

    def test_oem_to_ansi_fixes_dos_mojibake(self) -> None:
        # CP437 0x94 is 'o with diaeresis (o-umlaut); reinterpreted as text that
        # was actually Windows-1252, it should read back as that glyph.
        dos_bytes = b"Sch\x94n"
        mis_decoded = dos_bytes.decode("cp437")
        assert oem_to_ansi(mis_decoded) == dos_bytes.decode("cp1252")

    def test_ansi_to_oem_is_inverse_of_oem_to_ansi(self) -> None:
        original = "plain ascii text"
        assert ansi_to_oem(oem_to_ansi(original)) == original


class TestBoxDrawingConversion:
    def test_convert_horizontal_and_vertical_lines(self) -> None:
        assert convert_box_drawing_to_ascii("─│") == "-|"

    def test_convert_junction_falls_back_to_plus(self) -> None:
        assert convert_box_drawing_to_ascii("┌┐└┘") == "++++"

    def test_convert_leaves_non_box_drawing_untouched(self) -> None:
        assert convert_box_drawing_to_ascii("hello") == "hello"

    def test_convert_mixed_text_and_box_drawing(self) -> None:
        assert convert_box_drawing_to_ascii("a─b│c") == "a-b|c"

    def test_strip_removes_box_drawing_chars(self) -> None:
        assert strip_box_drawing("┌─┐\n│a│\n└─┘") == "\na\n"

    def test_strip_leaves_plain_text_unchanged(self) -> None:
        assert strip_box_drawing("plain text") == "plain text"


class TestDescribeMinimumEncoding:
    def test_no_current_encoding_given(self) -> None:
        summary = describe_minimum_encoding("hello")
        assert "Minimum required encoding: ASCII." == summary

    def test_current_encoding_already_sufficient(self) -> None:
        summary = describe_minimum_encoding("hello", "ascii")
        assert "saved losslessly as ASCII" in summary

    def test_current_encoding_insufficient_recommends_minimum(self) -> None:
        # 13.9: ISO-8859-1 cannot hold an em dash; recommend the next encoding up.
        summary = describe_minimum_encoding("a—b", "latin-1")
        assert "cannot be saved as ISO-8859-1 / Latin-1" in summary
        assert "Minimum required encoding: Windows-1252 / MS-ANSI." in summary
