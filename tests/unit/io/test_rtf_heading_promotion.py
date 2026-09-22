r"""Headings saved from the editor have to be headings in Word.

Reported by a user: "I added three headings, saved it, opened it in Word and the
text does not have headings." The file they sent back is the fixture below --
RichEdit's own RTF, which is all the control can produce. A heading there is a
point size and bold, because that is the only way the Text Object Model can be
told to make one, and it is exactly how the editor finds its own headings again
on reopening. Word has nothing to go on: no stylesheet, no ``\\sN``, no
``\\outlinelevel``, so it shows three bold paragraphs whose style box says Normal
and a navigation pane with nothing in it.

The Markdown writer had been emitting the stylesheet since headings first gained
sizes, which is why this survived: one of the two writers was already right.
"""

from __future__ import annotations

from quill.core.heading_ladder import HEADING_POINT_SIZES
from quill.io.rtf_heading_promotion import promote_heading_styles

#: The user's d:\\demo.rtf, byte for byte: three headings and the blank body
#: paragraphs the editor leaves between them.
SAVED_BY_THE_CONTROL = (
    "{\\rtf1\\ansi\\deff0\\nouicompat"
    "{\\fonttbl{\\f0\\fnil Calibri;}{\\f1\\fnil\\fcharset0 Calibri;}}\\n"
    "{\\*\\generator Riched20 10.0.26100}\\viewkind4\\uc1 \\n"
    "\\pard\\b\\f0\\fs40\\lang1033 This is a test.\\par\\n"
    "\\b0\\fs24\\par\\n"
    "\\b\\f1\\fs32 This is a test 2.\\par\\n"
    "\\b0\\f0\\fs24\\par\\n"
    "\\b\\f1\\fs28 This is a test 3.\\par\\n"
    "\\b0\\f0\\fs24\\par\\n"
    "}\\n"
)


#: Written out rather than escaped: this file is almost entirely backslashes,
#: and a helper that got one of them wrong would quietly compare nothing.
_BACKSLASH = chr(92)


def _plain_text(rtf: str) -> str:
    r"""The characters a reader would see: no control words, no groups.

    Groups are dropped whole. A ``{\stylesheet ...}`` is full of the word
    "heading", and a comparison that counted it would pass whatever happened
    to the document itself.
    """
    body = rtf.strip().removeprefix("{").removesuffix("}")
    visible: list[str] = []
    depth = 0
    index = 0
    while index < len(body):
        char = body[index]
        if char == _BACKSLASH:
            index += 1
            if index < len(body) and body[index].isalpha():
                while index < len(body) and body[index].isalpha():
                    index += 1
                while index < len(body) and (body[index].isdigit() or body[index] == "-"):
                    index += 1
                if index < len(body) and body[index] == " ":
                    index += 1
            else:
                index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0 and char.isprintable():
            visible.append(char)
        index += 1
    return "".join(visible).strip()


def test_word_is_given_a_stylesheet_to_read() -> None:
    promoted = promote_heading_styles(SAVED_BY_THE_CONTROL)
    assert "\\stylesheet" in promoted
    for level in HEADING_POINT_SIZES:
        assert f"heading {level};" in promoted


def test_each_heading_paragraph_points_at_its_style() -> None:
    promoted = promote_heading_styles(SAVED_BY_THE_CONTROL)
    # 20, 16 and 14 point bold: Heading 1, 2 and 3 on the editor's ladder.
    assert "\\s1\\outlinelevel0" in promoted
    assert "\\s2\\outlinelevel1" in promoted
    assert "\\s3\\outlinelevel2" in promoted


def test_the_body_paragraphs_are_not_promoted() -> None:
    r"""Twelve-point bold is Heading 4's size, and these paragraphs are not bold."""
    promoted = promote_heading_styles(SAVED_BY_THE_CONTROL)
    assert "\\s4" not in promoted.split("\\stylesheet", 1)[1].split("\\n", 1)[-1]


def test_not_one_character_of_the_document_changes() -> None:
    """Only structure is added: the words, and nothing but the words, survive."""
    before = _plain_text(SAVED_BY_THE_CONTROL)
    after = _plain_text(promote_heading_styles(SAVED_BY_THE_CONTROL))
    assert after == before
    assert "This is a test." in after


def test_a_document_with_no_headings_is_returned_untouched() -> None:
    plain = (
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}\\n\\pard\\fs22 just a paragraph\\par\\n}"
    )
    assert promote_heading_styles(plain) == plain


def test_a_font_name_that_looks_like_a_heading_is_not_one() -> None:
    """The scan must not read the font table as document text."""
    with_tables = (
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0\\fs40\\b Calibri;}}\\n"
        "\\pard\\fs22 just a paragraph\\par\\n}"
    )
    assert promote_heading_styles(with_tables) == with_tables


def test_a_document_that_already_has_a_stylesheet_keeps_it() -> None:
    already = (
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}"
        "{\\stylesheet{\\s0\\ql Normal;}}\\n"
        "\\pard\\b\\fs40 Title\\par\\n}"
    )
    promoted = promote_heading_styles(already)
    assert promoted.count("\\stylesheet") == 1
    assert "\\s1\\outlinelevel0" in promoted


def test_bold_alone_is_not_a_heading() -> None:
    """Ctrl+B on a body line must not make Word call it a heading either."""
    bold_body = (
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}\\n"
        "\\pard\\b\\fs22 emphatic, not a heading\\par\\n}"
    )
    assert promote_heading_styles(bold_body) == bold_body


def test_a_heading_size_without_bold_is_not_a_heading() -> None:
    big_body = (
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}\\n"
        "\\pard\\fs40 large, not a heading\\par\\n}"
    )
    assert promote_heading_styles(big_body) == big_body
