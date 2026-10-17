"""Property-based round trips for the format readers and writers (todo P3).

Example tests pin the cases somebody thought of; these ask Hypothesis for the
ones nobody did -- an emoji at the end of a line, a CRLF document with one
line, a paragraph that is only a digit. Each property is a promise the editor
makes when it saves: what you wrote is what you get back.

Where a format cannot carry something (a bare carriage return in plain text,
a control character in Word's XML), the strategy leaves it out and the
docstring says so, because a property that quietly excludes a case is a
different promise from one that states the exclusion.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from quill.core.document import Document  # noqa: E402
from quill.io.rtf_model import (  # noqa: E402
    InlineSpan,
    RichDocument,
    RichParagraph,
    rich_to_rtf,
    rtf_to_rich,
)
from quill.io.text import read_text_document, write_text_document  # noqa: E402

# --------------------------------------------------------------------------- #
# Plain text
# --------------------------------------------------------------------------- #

#: Any text a person can type, as the editor holds it: LF line breaks only (the
#: reader turns every CR into LF by design) and no leading U+FEFF (a leading BOM
#: is the encoding's mark, stripped on open by design, #648).
_editor_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r"),
    max_size=200,
).filter(lambda text: not text.startswith("﻿"))


@given(
    text=_editor_text,
    line_ending=st.sampled_from(["\n", "\r\n"]),
    encoding=st.sampled_from(["utf-8", "utf-8-sig", "utf-16"]),
)
def test_plain_text_comes_back_exactly_with_its_line_ending(
    text: str, line_ending: str, encoding: str
) -> None:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "note.txt"
        write_text_document(Document(text=text, encoding=encoding, line_ending=line_ending), path)
        back = read_text_document(path)
    assert back.text == text
    if "\n" in text:
        assert back.line_ending == line_ending


# --------------------------------------------------------------------------- #
# Rich text: RTF and Word
# --------------------------------------------------------------------------- #

#: Words: letters and digits from any script, emoji included, and the
#: punctuation of ordinary prose. Spaces are added between words, so no run
#: starts or ends with one, and none doubles one (Word and RTF readers keep
#: those, but the writer of a paragraph never makes them).
_word = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Lo", "Nd", "So"),
        whitelist_characters=".,;:!?'\"-()&%$@/",
    ),
    min_size=1,
    max_size=12,
)
_run_text = st.lists(_word, min_size=1, max_size=6).map(" ".join)


@st.composite
def _paragraph(draw: st.DrawFn) -> RichParagraph:
    style = draw(st.sampled_from(["paragraph", "heading", "bullet"]))
    level = draw(st.integers(1, 6)) if style == "heading" else 0
    runs = draw(
        st.lists(st.tuples(_run_text, st.booleans(), st.booleans()), min_size=1, max_size=3)
    )
    spans: list[InlineSpan] = []
    for index, (text, bold, italic) in enumerate(runs):
        spans.append(InlineSpan(text=(" " if index else "") + text, bold=bold, italic=italic))
    return RichParagraph(spans=spans, style=style, level=level)


_document = st.lists(_paragraph(), min_size=1, max_size=5).map(
    lambda paragraphs: RichDocument(paragraphs=paragraphs)
)


def _shape(
    document: RichDocument, *, bold_in_headings: bool = True
) -> list[tuple[str, int, str, list[tuple[str, bool, bool]]]]:
    """Paragraph style, level, text, and the bold/italic of each character run,
    with adjacent runs of the same formatting merged (a reader may split them).

    ``bold_in_headings=False`` reads every heading run as not bold: RTF marks a
    heading with ``\b`` itself, so bold *inside* a heading cannot be told
    apart from the heading and the reader drops it on purpose (``rtf.py``)."""
    shaped = []
    for paragraph in document.paragraphs:
        runs: list[tuple[str, bool, bool]] = []
        for span in paragraph.spans:
            if not span.text:
                continue
            bold = bool(span.bold) and (bold_in_headings or paragraph.style != "heading")
            key = (bold, bool(span.italic))
            if runs and runs[-1][1:] == key:
                runs[-1] = (runs[-1][0] + span.text, *key)
            else:
                runs.append((span.text, *key))
        shaped.append((paragraph.style, paragraph.level, paragraph.text(), runs))
    return shaped


def _emphasis_touches(document: RichDocument) -> bool:
    """Two neighbouring runs, both emphasised, differently: "*a*" then "***b***".

    RTF goes through QUILL's Markdown on the way in and out, and there the two
    sets of asterisks meet ("*a**** b***") and cannot be told apart. A known
    limit, pinned by the xfail test below rather than hidden.
    """
    for paragraph in document.paragraphs:
        keys = [(s.bold, s.italic) for s in paragraph.spans]
        for left, right in zip(keys, keys[1:], strict=False):
            if left != right and any(left) and any(right):
                return True
    return False


@given(document=_document)
def test_rtf_keeps_text_styles_and_bold_italic(document: RichDocument) -> None:
    hypothesis.assume(not _emphasis_touches(document))
    back = rtf_to_rich(rich_to_rtf(document))
    assert _shape(back, bold_in_headings=False) == _shape(document, bold_in_headings=False)


@given(document=_document)
def test_word_keeps_text_styles_and_bold_italic(document: RichDocument) -> None:
    pytest.importorskip("docx")
    from quill.io.docx_reader import read_docx_rich
    from quill.io.docx_writer import rich_to_docx_bytes

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "round.docx"
        path.write_bytes(rich_to_docx_bytes(document))
        back = read_docx_rich(path)
    assert _shape(back) == _shape(document)


@pytest.mark.xfail(
    strict=True,
    reason="known limit: neighbouring runs with different emphasis share asterisks in Markdown",
)
def test_italic_next_to_bold_italic_survives_rtf() -> None:
    document = RichDocument(
        paragraphs=[
            RichParagraph(
                spans=[InlineSpan("a", italic=True), InlineSpan(" b", bold=True, italic=True)]
            )
        ]
    )
    back = rtf_to_rich(rich_to_rtf(document))
    assert _shape(back) == _shape(document)


def test_a_bold_italic_word_survives_rtf() -> None:
    """The bug the property found (2026-10-17): "***x***" was read as bold "*x"
    and a stray asterisk, both writing RTF and reading QUILL's Markdown."""
    document = RichDocument(
        paragraphs=[RichParagraph(spans=[InlineSpan("word", bold=True, italic=True)])]
    )
    assert _shape(rtf_to_rich(rich_to_rtf(document))) == _shape(document)
