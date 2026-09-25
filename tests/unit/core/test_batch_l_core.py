"""The wx-free half of bad.md P2.8: byte order, chooser rows, dead keys.

F8 -- a UTF-16 **big-endian** file round-tripped little-endian on a save that
changed nothing else, because both byte orders decoded to the one ``utf-16``
codec and that codec always writes little-endian. A byte-order swap is invisible
in the editor and visible to everything downstream. The same row also covers the
chooser arithmetic: selecting the index of a value the chooser does not offer
fell back to 0, which is UTF-8 and CRLF, so a big-endian or classic-Mac CR file
opened the File Format dialog describing itself wrongly and OK converted it.

R9 -- every document is a Rich Edit control, so the control's own chords
(Ctrl+U, Ctrl+L/R/E/J, Ctrl+Shift+=) format documents that have no formatting:
not dirty, not announced, not saved, but on the undo stack and on the screen.
"""

from __future__ import annotations

from quill.core.lite.textfile import (
    ENCODING_CHOICES,
    NEWLINE_CHOICES,
    UTF16_BE_BOM_CODEC,
    decode_text,
    encode_text,
    encoding_rows,
    newline_rows,
)
from quill.core.native_richedit_keys import (
    native_formatting_effect,
    native_formatting_notice,
    notice_kind_label,
)

# -- F8: byte order ------------------------------------------------------------


def _round_trip(data: bytes) -> bytes:
    decoded = decode_text(data)
    return encode_text(decoded.text, encoding=decoded.encoding, newline=decoded.newline)


def test_a_big_endian_file_is_still_big_endian_after_a_save() -> None:
    data = b"\xfe\xff" + "hello\r\nthere".encode("utf-16-be")
    assert _round_trip(data) == data


def test_a_little_endian_file_is_still_little_endian() -> None:
    data = b"\xff\xfe" + "hello\r\nthere".encode("utf-16-le")
    assert _round_trip(data) == data


def test_the_two_byte_orders_are_told_apart_at_read_time() -> None:
    assert decode_text(b"\xfe\xff" + "x".encode("utf-16-be")).encoding == UTF16_BE_BOM_CODEC
    assert decode_text(b"\xff\xfe" + "x".encode("utf-16-le")).encoding == "utf-16"


def test_the_other_encodings_still_round_trip() -> None:
    for data in (
        b"\xef\xbb\xbfcaf\xc3\xa9",  # UTF-8 with BOM
        "café".encode(),  # UTF-8
        "café".encode("cp1252"),  # Windows-1252
    ):
        assert _round_trip(data) == data


# -- F8: the chooser rows ------------------------------------------------------


def test_a_format_the_chooser_offers_adds_no_row() -> None:
    assert encoding_rows("utf-8") == ENCODING_CHOICES
    assert newline_rows("\r\n") == NEWLINE_CHOICES


def test_a_format_the_chooser_does_not_offer_becomes_the_first_row() -> None:
    rows = encoding_rows(UTF16_BE_BOM_CODEC)
    assert rows[0][0] == UTF16_BE_BOM_CODEC
    assert "big-endian" in rows[0][1]
    assert "keep as is" in rows[0][1]
    assert rows[1:] == ENCODING_CHOICES


def test_a_classic_mac_file_shows_its_own_line_ending() -> None:
    rows = newline_rows("\r")
    assert rows[0][0] == "\r"
    assert "classic Mac" in rows[0][1]
    assert rows[1:] == NEWLINE_CHOICES


def test_the_added_row_is_always_at_index_zero() -> None:
    """Which is the whole fix: index 0 is what an unmatched selection falls to."""
    for value, rows in (
        (UTF16_BE_BOM_CODEC, encoding_rows(UTF16_BE_BOM_CODEC)),
        ("\r", newline_rows("\r")),
    ):
        assert rows[0][0] == value


# -- R9: the native control's own chords ---------------------------------------


def test_the_chords_the_control_claims_are_recognised() -> None:
    assert native_formatting_effect(ctrl=True, shift=False, alt=False, key="u") == "Underline"
    assert native_formatting_effect(ctrl=True, shift=False, alt=False, key="L") == "Left alignment"
    assert native_formatting_effect(ctrl=True, shift=True, alt=False, key="=") == "Superscript"
    assert native_formatting_effect(ctrl=True, shift=False, alt=False, key="=") == "Subscript"


def test_a_chord_without_control_is_not_one_of_them() -> None:
    assert native_formatting_effect(ctrl=False, shift=False, alt=False, key="u") is None


def test_alt_means_the_chord_belongs_to_somebody_else() -> None:
    assert native_formatting_effect(ctrl=True, shift=False, alt=True, key="u") is None


def test_an_ordinary_editing_chord_is_left_alone() -> None:
    """Ctrl+C, Ctrl+V, Ctrl+B and Ctrl+I must never be swallowed here."""
    for key in ("C", "V", "X", "Z", "S", "B", "I"):
        assert native_formatting_effect(ctrl=True, shift=False, alt=False, key=key) is None


def test_the_notice_names_the_effect_and_the_kind() -> None:
    assert (
        native_formatting_notice("Underline", "Markdown")
        == "Underline has no meaning in a Markdown document."
    )
    assert "an HTML document" in native_formatting_notice("Superscript", "HTML")
    assert "a plain text document" in native_formatting_notice("Centre alignment", "plain text")


def test_both_editors_name_a_kind_of_document_the_same_way() -> None:
    """One dead key, one sentence -- whichever editor's label it starts from.

    QUILL asks its markup kind, which is lower case ("html"); QUILL Lite asks its
    own status cell, which is title case ("Plain text"). Before the shared table
    QUILL Lite lower-cased its answer on the way in, so an HTML document heard "a
    html document" in one editor and "an HTML document" in the other -- the same
    key, the same file, two explanations.
    """
    for quill_side, lite_side in (
        ("html", "HTML"),
        ("markdown", "Markdown"),
        ("", "Plain text"),
        ("text", "Plain text"),
    ):
        assert notice_kind_label(quill_side) == notice_kind_label(lite_side)


def test_the_article_survives_every_label_either_editor_can_produce() -> None:
    spoken = {
        kind: native_formatting_notice("Underline", notice_kind_label(kind))
        for kind in ("html", "HTML", "markdown", "Markdown", "Plain text", "rich text", "")
    }
    assert "an HTML document" in spoken["html"]
    assert "an HTML document" in spoken["HTML"]
    assert "a Markdown document" in spoken["markdown"]
    assert "a plain text document" in spoken["Plain text"]
    assert "a rich text document" in spoken["rich text"]
    # Anything unrecognised is the kind with no formatting, which is the kind
    # this sentence is about.
    assert "a plain text document" in spoken[""]
