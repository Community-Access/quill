"""GATE-FIDELITY: every formatting feature survives every format conversion.

The guarantee this file exists to hold: **a document converted between plain
text, Markdown, HTML and Rich Text does not quietly lose formatting.** Not
"mostly", not "the common cases" -- every construct in :data:`RICH_DOCUMENT`,
which is deliberately a rich document containing one of everything QUILL can
express, in both directions, exactly.

It is written as a table rather than as prose assertions because the failure
mode being guarded against is *silent*: the words always arrive, so a lost
underline or a dropped page break reads as a document somebody wrote that way.
The only way to notice is to compare, feature by feature, which is what
:func:`test_every_feature_survives_a_round_trip` does -- and a new construct
that is not in the table is one nobody is checking.

What each direction is allowed to lose is stated here too, in
:data:`PLAIN_TEXT_DROPS`: plain text is *supposed* to lose markup, and a test
that let it lose nothing would be asserting the opposite of the feature.
"""

from __future__ import annotations

import pytest

from quill.core.format_transitions import PlainStyle, convert_text
from quill.io.rtf import markdown_to_rtf
from quill.io.rtf_styles import NAMED_PARAGRAPH_STYLES

#: One of everything, as ``(name, markup)``. The name is what a failure reports,
#: so it is the feature's name and not a description of the sample.
FEATURES: tuple[tuple[str, str], ...] = (
    ("heading levels", "# H1\n\n## H2\n\n###### H6\n"),
    ("bold", "a **bold** b\n"),
    ("italic", "a *italic* b\n"),
    ("underline", "a [under]{underline} b\n"),
    ("strikethrough", "a [gone]{strike} b\n"),
    ("superscript", "a [2]{superscript} b\n"),
    ("subscript", "a [2]{subscript} b\n"),
    ("font family", 'a [x]{font-family="Arial"} b\n'),
    ("font size", 'a [x]{font-size="18"} b\n'),
    ("text colour", 'a [x]{color="#FF0000"} b\n'),
    ("highlight", 'a [x]{highlight="#FFFF00"} b\n'),
    ("bullet list", "- one\n- two\n"),
    ("numbered list", "1. one\n2. two\n"),
    ("link", "see [docs](https://example.com)\n"),
    ("code span", "a `code` b\n"),
    ("code fence", "```\ncode\n```\n"),
    ("block quote", "> quoted\n"),
    ("alignment", '::: {align="center"}\ncentered\n:::\n'),
    ("line spacing", '::: {line-spacing="2"}\nspaced\n:::\n'),
    ("indent", '::: {indent="36"}\nindented\n:::\n'),
    ("first-line indent", '::: {first-line-indent="18"}\nindented\n:::\n'),
    ("space before", '::: {space-before="12"}\nspaced\n:::\n'),
    ("space after", '::: {space-after="6"}\nspaced\n:::\n'),
    ("named style", '::: {pstyle="quote"}\nquoted\n:::\n'),
    ("page break", "before\n\n::: pagebreak\n\nafter\n"),
    ("table", "| a | b |\n|---|---|\n| 1 | 2 |\n"),
    ("image", "![alt text](picture.png)\n"),
    ("horizontal rule", "---\n"),
)

#: Everything above in one document, which is what a person actually has: the
#: constructs interleaved, not one per file. Round-tripping the whole thing
#: catches the failures that only appear in combination -- a span that swallows
#: the rest of the paragraph, a fence that never closes, a list that eats a
#: heading.
#:
#: Joined with a **blank** line between constructs, not a single newline: in
#: Markdown ``text`` followed immediately by ``---`` is a setext heading, not a
#: paragraph and a horizontal rule, so a single newline would make the fixture
#: itself mean something other than the sum of its parts.
RICH_DOCUMENT = "\n\n".join(markup.strip("\n") for _name, markup in FEATURES) + "\n"


@pytest.mark.parametrize(("name", "markup"), FEATURES, ids=[n for n, _ in FEATURES])
@pytest.mark.parametrize("via", ["rtf", "html"])
def test_every_feature_survives_a_round_trip(name: str, markup: str, via: str) -> None:
    """Markdown -> *via* -> Markdown returns exactly what went in.

    Exactly, not approximately. An "almost" here is a document that changes a
    little every time it is converted, and converting back and forth is
    something people do all day without thinking of it as an operation at all.
    """
    assert convert_text(convert_text(markup, "markdown", via), via, "markdown") == markup


@pytest.mark.parametrize("via", ["rtf", "html"])
def test_the_whole_rich_document_survives(via: str) -> None:
    """All of it at once, interleaved, as a real document is."""
    assert convert_text(convert_text(RICH_DOCUMENT, "markdown", via), via, "markdown") == (
        RICH_DOCUMENT
    )


@pytest.mark.parametrize("via", ["rtf", "html"])
def test_converting_twice_changes_nothing_more(via: str) -> None:
    """Stability, which is a stronger property than fidelity and the one that
    matters when somebody switches format repeatedly over an afternoon."""
    once = convert_text(convert_text(RICH_DOCUMENT, "markdown", via), via, "markdown")
    twice = convert_text(convert_text(once, "markdown", via), via, "markdown")
    assert twice == once


# -- plain text: what it is *supposed* to lose ------------------------------ #

#: Markers that must not survive into strictly plain text. Plain text losing
#: markup is the feature; this is the list of things that failing to lose would
#: be the bug -- ``<u>`` and ``~~`` both used to arrive intact.
PLAIN_TEXT_DROPS: tuple[str, ...] = ("#", "**", "~~", "<u>", "</u>", ":::", "]{")


def test_plain_text_is_strictly_plain() -> None:
    plain = convert_text(RICH_DOCUMENT, "markdown", "plain")
    for marker in PLAIN_TEXT_DROPS:
        assert marker not in plain, f"{marker!r} survived into plain text"


def test_plain_text_keeps_every_word() -> None:
    """Losing the markers must not mean losing the text they marked."""
    plain = convert_text(RICH_DOCUMENT, "markdown", "plain")
    for word in ("bold", "italic", "under", "centered", "quoted", "docs", "alt text"):
        assert word in plain, f"{word!r} was lost on the way to plain text"


def test_plain_text_can_keep_the_markers_when_asked() -> None:
    kept = convert_text(RICH_DOCUMENT, "markdown", "plain", plain_style=PlainStyle.KEEP)
    assert "# H1" in kept
    assert "**bold**" in kept


# -- what Word needs to open the file correctly ----------------------------- #


def test_headings_are_real_word_styles() -> None:
    """``\\sN`` plus the lower-case name plus ``\\outlinelevel``. Without all
    three a heading is large bold text: Word's style box says Normal and its
    navigation pane is empty."""
    rtf = markdown_to_rtf("# Title\n")
    assert "\\s1" in rtf
    assert "heading 1;" in rtf
    assert "\\outlinelevel0" in rtf


@pytest.mark.parametrize("token", sorted(NAMED_PARAGRAPH_STYLES))
def test_named_styles_are_declared_with_words_own_name(token: str) -> None:
    """Word matches a stylesheet entry to its built-in style *by name*, so the
    entry has to be spelled the way Word spells it. Named anything else it is a
    new user-defined style that merely looks similar."""
    index, name, _controls = NAMED_PARAGRAPH_STYLES[token]
    rtf = markdown_to_rtf(f'::: {{pstyle="{token}"}}\ntext\n:::\n')
    assert f"{name};" in rtf, f"{name} is not declared in the stylesheet"
    assert f"\\s{index}" in rtf, f"the paragraph does not use \\s{index}"


def test_the_stylesheet_declares_every_style_it_uses() -> None:
    """A ``\\sN`` pointing at an entry that does not exist is a style Word
    silently renders as Normal."""
    rtf = markdown_to_rtf(RICH_DOCUMENT)
    for _token, (index, name, _controls) in NAMED_PARAGRAPH_STYLES.items():
        if f"\\s{index}" in rtf:
            assert f"{name};" in rtf


def test_rtf_is_balanced() -> None:
    """Braces matched and the header present -- an unbalanced RTF is a file Word
    opens as one long run of control words, or refuses outright."""
    rtf = markdown_to_rtf(RICH_DOCUMENT)
    assert rtf.startswith("{\\rtf1")
    assert rtf.endswith("}")
    depth = 0
    previous = ""
    for char in rtf:
        if char == "{" and previous != "\\":
            depth += 1
        elif char == "}" and previous != "\\":
            depth -= 1
            assert depth >= 0, "a closing brace with nothing open"
        previous = char
    assert depth == 0, "unbalanced braces"
