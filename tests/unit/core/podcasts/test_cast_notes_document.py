"""The Notes reader's reading of show notes (qc.md 5c): structure, links, timestamps.

Pure: no wx. The reader moves the caret to the positions recorded here, so a
position that is off by one is a heading key that lands mid-word -- every mark is
checked against the text it claims to cover.
"""

from __future__ import annotations

from quill.core import text_links
from quill.core.podcasts.notes_document import (
    BLOCK_HEADING,
    BLOCK_ITEM,
    parse_notes,
    timestamp_spans,
)

NOTES = (
    "<h2>About this episode</h2>"
    "<p>We talk to <b>Ada</b> about the <a href='https://example.com/paper'>paper "
    "<em>we discussed</em></a>.</p>"
    "<h3>Chapters</h3>"
    "<ul><li>0:00 Introduction</li><li>12:34 The interview</li></ul>"
    "<p>Support the show at https://patreon.com/thedaily.</p>"
    "<script>alert('no')</script>"
)


def test_headings_are_found_with_their_level_and_text() -> None:
    doc = parse_notes(NOTES)
    assert [(mark.level, mark.text) for mark in doc.headings] == [
        (2, "About this episode"),
        (3, "Chapters"),
    ]
    for mark in doc.headings:
        assert doc.text[mark.start : mark.end] == mark.text


def test_links_cover_their_own_text_and_keep_one_address() -> None:
    doc = parse_notes(NOTES)
    assert [(mark.text, mark.target) for mark in doc.links] == [
        ("paper we discussed", "https://example.com/paper"),
        ("https://patreon.com/thedaily", "https://patreon.com/thedaily"),
    ]
    for mark in doc.links:
        assert doc.text[mark.start : mark.end].strip() == mark.text


def test_a_typed_address_stops_before_the_full_stop() -> None:
    doc = parse_notes(NOTES)
    typed = doc.links[-1]
    assert doc.text[typed.end] == "."


def test_timestamps_are_links_into_the_episode() -> None:
    doc = parse_notes(NOTES)
    assert [(mark.text, mark.position_ms) for mark in doc.timestamps] == [
        ("0:00", 0),
        ("12:34", 754_000),
    ]


def test_list_items_are_lines_with_their_markers() -> None:
    doc = parse_notes("<ol><li>One</li><li>Two</li></ol><ul><li>Dot</li></ul>")
    assert doc.text == "1. One\n2. Two\n- Dot"
    assert all(block.kind == BLOCK_ITEM for block in doc.blocks)


def test_scripts_and_styles_are_never_text() -> None:
    doc = parse_notes(NOTES + "<style>p{}</style>")
    assert "alert" not in doc.text
    assert "p{}" not in doc.text


def test_unsafe_links_are_plain_text() -> None:
    doc = parse_notes("<p><a href='javascript:alert(1)'>Click</a> here</p>")
    assert doc.links == ()
    assert doc.text == "Click here"


def test_empty_and_image_only_notes_say_which() -> None:
    assert parse_notes("").is_empty
    image_only = parse_notes("<p><img src='https://example.com/art.png' alt='Cover'></p>")
    assert image_only.only_images
    assert image_only.images == ("https://example.com/art.png",)


def test_plain_text_notes_keep_their_paragraphs() -> None:
    doc = parse_notes("First line\nsecond line\n\nAt 5:00 the second part.")
    assert doc.text == "First line\nsecond line\n\nAt 5:00 the second part."
    assert [mark.position_ms for mark in doc.timestamps] == [300_000]


def test_clock_times_and_long_numbers_are_not_timestamps() -> None:
    assert timestamp_spans("Live at 10:30 am, ref 2024:01:02:03") == []
    assert [ms for _s, _e, ms in timestamp_spans("[1:02:03] and (05:00)")] == [3_723_000, 300_000]


def test_moving_between_marks_goes_forward_and_back() -> None:
    doc = parse_notes(NOTES)
    first, second = doc.headings
    assert doc.next_mark(doc.headings, -1, forward=True) == first
    assert doc.next_mark(doc.headings, first.start, forward=True) == second
    assert doc.next_mark(doc.headings, second.start, forward=True) is None
    assert doc.next_mark(doc.headings, second.start, forward=False) == first


def test_the_mark_under_the_caret_includes_its_end() -> None:
    doc = parse_notes(NOTES)
    link = doc.links[0]
    assert doc.link_at(link.start) == link
    assert doc.link_at(link.end) == link
    assert doc.link_at(0) is None


def test_duplicate_addresses_fold_into_one_row_and_the_first_title_wins() -> None:
    doc = parse_notes(
        "<p><a href='https://example.com/a'>The sponsor</a> and later "
        "<a href='https://example.com/a/'>again</a></p>"
    )
    rows = doc.unique_links()
    assert [link.row for link in rows] == ["The sponsor, example.com/a"]


def test_the_row_reads_title_then_where_it_goes() -> None:
    link = text_links.Link(url="https://www.patreon.com/thedaily", text="Support the show")
    assert link.row == "Support the show, patreon.com/thedaily"
    assert text_links.Link(url="https://example.com/").row == "example.com"


def test_headings_are_blocks_too() -> None:
    doc = parse_notes("<h1>Title</h1><p>Body</p>")
    assert doc.blocks[0].kind == BLOCK_HEADING
    assert doc.text == "Title\n\nBody"
    assert (0, 5, "heading") in doc.styles
