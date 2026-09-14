"""Saving a Word file must not fail on a character you cannot see (#1500).

The report was "I was attempting to save a file after making minor corrections
to it" and the answer was a ValueError out of lxml. One control character
anywhere in the document -- pasted from a terminal, returned by a dictation or
AI bridge, recovered off a damaged disk -- and Save raised instead of saving.

There is no version of this where the character survives: XML 1.0 cannot
represent it, escaped or otherwise. The only question was whether losing it
costs the character or the whole file. These tests fix the answer, and fix the
three control characters that must NOT be lost, because tab, newline and
carriage return are both legal in XML and load-bearing in prose.
"""

from __future__ import annotations

import pytest

from quill.io.xml_text import (
    count_xml_incompatible,
    is_xml_compatible,
    strip_xml_incompatible,
)

NUL = "\x00"
BELL = "\x07"
ESCAPE = "\x1b"


# --------------------------------------------------------------------- #
# What must go


@pytest.mark.parametrize("char", [NUL, BELL, ESCAPE, "\x01", "\x0b", "\x0c", "\x1f"])
def test_a_control_character_is_not_xml_compatible(char: str) -> None:
    assert not is_xml_compatible(char)
    assert strip_xml_incompatible(f"a{char}b") == ("ab", 1)


def test_the_permanently_unassigned_code_points_go_too() -> None:
    """U+FFFE and U+FFFF are not characters at all; lxml rejects them alongside
    the control block."""
    assert strip_xml_incompatible("a￾b￿c") == ("abc", 2)


def test_a_lone_surrogate_goes() -> None:
    """It can exist in a Python string and cannot exist in a document."""
    assert strip_xml_incompatible("a\ud800b") == ("ab", 1)


def test_several_are_counted_individually() -> None:
    text = f"{NUL}start{BELL}middle{ESCAPE}end"
    assert strip_xml_incompatible(text) == ("startmiddleend", 3)
    assert count_xml_incompatible(text) == 3


# --------------------------------------------------------------------- #
# What must stay


@pytest.mark.parametrize("char", ["\t", "\n", "\r"])
def test_the_three_control_characters_xml_allows_are_kept(char: str) -> None:
    """These three carry meaning in prose, and XML permits all three. Stripping
    them would turn a crash into silent reformatting, which is worse."""
    assert is_xml_compatible(char)
    assert strip_xml_incompatible(f"a{char}b") == (f"a{char}b", 0)


def test_ordinary_text_is_returned_unchanged_and_unbuilt() -> None:
    """The common case must not rebuild the string; a document is long."""
    text = "The quick brown fox\tjumps\nover the lazy dog."
    assert strip_xml_incompatible(text) == (text, 0)


def test_only_the_form_feed_in_the_character_picker_cannot_reach_a_word_file() -> None:
    """The picker exists to put unusual characters into documents, so a save
    that dropped them would be a worse bug than the crash this file is about.

    Exactly one of its 357 rows cannot survive: U+000C, the page break, which
    XML has never been able to hold. It stays in the picker because QUILL's own
    formats are plain text and Markdown, where a form feed is both legal and
    meaningful -- it is only the Word export that cannot carry it. This test is
    the record of that, so the day a second row joins it somebody has to decide
    deliberately rather than discover it in a crash report.
    """
    from quill.core.special_characters import CATALOGUE

    lost = [row.code_point for row in CATALOGUE if not is_xml_compatible(row.char)]
    assert lost == ["U+000C"]


def test_emoji_and_accents_survive() -> None:
    text = "café — naïve — 😀 — 中文"
    assert strip_xml_incompatible(text) == (text, 0)


# --------------------------------------------------------------------- #
# The writer itself


def test_a_document_full_of_control_characters_still_writes(tmp_path) -> None:
    """The end-to-end shape of #1500: this exact document used to raise."""
    docx_writer = pytest.importorskip("quill.io.docx_writer")
    if not docx_writer.python_docx_available():
        pytest.skip("python-docx is not installed")
    from quill.core.document import Document

    document = Document()
    document.set_text(f"Hello{NUL} world\n\nSecond{BELL} paragraph\n")
    target = tmp_path / "out.docx"
    docx_writer.write_docx(document, target)
    assert target.exists()
    assert target.stat().st_size > 0


def test_the_written_text_is_the_text_minus_only_what_could_not_be_written(tmp_path) -> None:
    docx_writer = pytest.importorskip("quill.io.docx_writer")
    if not docx_writer.python_docx_available():
        pytest.skip("python-docx is not installed")
    from quill.core.document import Document
    from quill.io.docx_text import read_docx_text

    document = Document()
    document.set_text(f"Keep{NUL} every{BELL} word\n")
    target = tmp_path / "out.docx"
    docx_writer.write_docx(document, target)
    assert "Keep every word" in (read_docx_text(target) or "")
