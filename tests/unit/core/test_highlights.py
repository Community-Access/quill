"""Highlighted passages: the palette, finding them, placing them, walking them.

Item 39 (2026-10-16). The palette tests are the round-trip bugs this found:
the RTF writer knew six colour names, so pink and turquoise highlights were
written as nothing; and the Word writer could not read the ``#RRGGBB`` values a
Rich Edit control hands back, so every highlight saved from rich mode came out
yellow.
"""

from __future__ import annotations

import pytest

from quill.core.highlights import (
    HIGHLIGHT_COLOURS,
    HighlightPassage,
    HighlightRun,
    align_runs,
    docx_highlight_member,
    highlight_hex,
    highlight_name,
    list_label,
    next_passage,
    passage_index_at,
    passages_from_markdown,
    previous_passage,
    runs_from_markdown,
    spoken_passage,
)


@pytest.mark.parametrize(
    ("spelling", "name"),
    [
        ("yellow", "yellow"),
        ("YELLOW", "yellow"),
        ("#FFFF00", "yellow"),
        ("#ffff00", "yellow"),
        ("BRIGHT_GREEN", "green"),
        ("bright green", "green"),
        ("#00FF00", "green"),
        ("cyan", "turquoise"),
        ("magenta", "pink"),
        ("darkCyan", "teal"),
        ("TEAL", "teal"),
        ("darkGreen", "dark green"),
        ("#008000", "dark green"),  # what the RTF writer used to write for "green"
        ("lightGray", "gray"),
        ("GRAY_25", "gray"),
        ("grey", "gray"),
        ("GRAY_50", "dark gray"),
        ("#FEFE01", "yellow"),  # nearest, not exact
    ],
)
def test_every_spelling_folds_to_one_name(spelling: str, name: str) -> None:
    assert highlight_name(spelling) == name


@pytest.mark.parametrize("value", [None, "", "none", "auto", "#zzzzzz", "plaid"])
def test_no_highlight_is_none(value: object) -> None:
    assert highlight_name(value) is None


def test_the_palette_has_wordss_fifteen_colours_once_each() -> None:
    assert len(HIGHLIGHT_COLOURS) == 15
    assert len({c.name for c in HIGHLIGHT_COLOURS}) == 15
    assert len({c.rgb for c in HIGHLIGHT_COLOURS}) == 15
    for colour in HIGHLIGHT_COLOURS:
        assert highlight_name(colour.name) == colour.name
        assert highlight_name(colour.ooxml) == colour.name
        assert highlight_name(highlight_hex(colour.name)) == colour.name
        assert docx_highlight_member(colour.name) == colour.docx_member


def test_writers_get_what_they_need() -> None:
    assert highlight_hex("pink") == "#FF00FF"
    assert highlight_hex("turquoise") == "#00FFFF"
    assert docx_highlight_member("#00FFFF") == "TURQUOISE"
    assert docx_highlight_member("#C0C0C0") == "GRAY_25"
    assert docx_highlight_member("none") is None


def test_the_rtf_writer_now_writes_pink_and_turquoise() -> None:
    from quill.io.rtf import markdown_to_rtf, rtf_to_markdown

    rtf = markdown_to_rtf('a [b]{highlight="pink"} c [d]{highlight="turquoise"}')
    assert "\\highlight" in rtf
    back = rtf_to_markdown(rtf)
    assert highlight_name(back.split('highlight="')[1].split('"')[0]) == "pink"
    assert highlight_name(back.split('highlight="')[2].split('"')[0]) == "turquoise"


MD = (
    "# Notes\n\n"
    'The [budget is final]{highlight="yellow"} unless the [board]{highlight="green"} objects.\n\n'
    '- [**Pink**]{highlight="pink"} item\n'
)


def test_markdown_passages_are_offsets_into_the_buffer() -> None:
    passages = passages_from_markdown(MD)
    assert [(p.colour, p.text) for p in passages] == [
        ("yellow", "budget is final"),
        ("green", "board"),
        ("pink", "Pink"),
    ]
    first = passages[0]
    assert MD[first.start : first.end] == "budget is final"
    assert first.context == "The budget is final unless the board objects."
    # The caret is put on the first visible character, not on the bracket.
    assert MD[passages[2].start] == "P"


def test_an_edit_above_moves_the_passages_and_a_removal_drops_one() -> None:
    before = passages_from_markdown(MD)
    edited = "Intro line.\n" + MD
    after = passages_from_markdown(edited)
    assert [p.start - b.start for p, b in zip(after, before, strict=True)] == [12, 12, 12]
    removed = edited.replace('[board]{highlight="green"}', "board")
    assert [p.text for p in passages_from_markdown(removed)] == ["budget is final", "Pink"]


def test_runs_are_placed_by_words_and_paragraph() -> None:
    text = "- The cat sat. The cat ran.\n\nOther the cat."
    runs = [
        HighlightRun("yellow", "cat", "The cat sat. The cat ran.", 17),
        HighlightRun("pink", "the cat", "Other the cat.", 6),
    ]
    placed = align_runs(runs, text)
    assert [text[p.start : p.end] for p in placed] == ["cat", "the cat"]
    assert placed[0].start == text.index("cat ran")  # the second "cat", not the first
    assert placed[1].start == text.index("the cat.")


def test_a_run_whose_words_are_gone_is_left_out() -> None:
    runs = [HighlightRun("yellow", "vanished words", "Para with vanished words", 10)]
    assert align_runs(runs, "Para with other words") == []


def test_runs_from_rtf_markdown_round_trip() -> None:
    runs = runs_from_markdown(MD)
    plain = "Notes\nThe budget is final unless the board objects.\nPink item"
    placed = align_runs(runs, plain)
    assert [(p.colour, plain[p.start : p.end]) for p in placed] == [
        ("yellow", "budget is final"),
        ("green", "board"),
        ("pink", "Pink"),
    ]


def _passages() -> list[HighlightPassage]:
    return [
        HighlightPassage(5, 9, "yellow", "one"),
        HighlightPassage(20, 25, "green", "two"),
        HighlightPassage(40, 44, "pink", "three"),
    ]


def test_next_and_previous_wrap() -> None:
    passages = _passages()
    assert next_passage(passages, 0) == 0
    assert next_passage(passages, 5) == 1, "on a passage, Next moves on"
    assert next_passage(passages, 40) == 0, "wraps"
    assert previous_passage(passages, 20) == 0, "on a passage, Previous moves back"
    assert previous_passage(passages, 3) == 2, "wraps"
    assert next_passage([], 0) is None
    assert previous_passage([], 0) is None


def test_the_list_opens_where_the_caret_is() -> None:
    passages = _passages()
    assert passage_index_at(passages, 22) == 1
    assert passage_index_at(passages, 10) == 1
    assert passage_index_at(passages, 50) == 2


def test_what_is_said_and_listed() -> None:
    passage = HighlightPassage(0, 6, "yellow", "budget", "The budget is final.")
    assert spoken_passage(passage, 0, 3) == "Yellow highlight, 1 of 3: budget"
    assert list_label(passage) == "budget, yellow highlight, in: The budget is final."
    alone = HighlightPassage(0, 4, "pink", "Note", "Note")
    assert list_label(alone) == "Note, pink highlight"
