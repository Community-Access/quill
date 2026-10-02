"""Show notes as structure, the four copy formats, and the episode's own note (qc.md 5c)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts import notes_export
from quill.core.podcasts.notes_render import (
    HEADING,
    LIST_ITEM,
    PARAGRAPH,
    empty_sentence,
    parse_timestamp_ms,
    render_notes,
)

HTML = (
    "<h2>This week</h2>"
    '<p>We talk to <a href="https://example.com/guest">Jane &amp; Co</a> at 12:34 '
    "and <b>more</b>.</p>"
    '<ul><li>First point</li><li>Second with <a href="https://x.org">a link</a></li></ul>'
    '<p>Support us: <a href="https://patreon.com/show">patreon.com/show</a> (1:02:03)</p>'
    "<script>alert(1)</script>"
    '<p><a href="https://x.org">the same link again</a></p>'
)


def test_headings_paragraphs_and_lists_survive_with_their_offsets() -> None:
    doc = render_notes(HTML)

    kinds = [block.kind for block in doc.blocks]
    assert kinds == [HEADING, PARAGRAPH, LIST_ITEM, LIST_ITEM, PARAGRAPH, PARAGRAPH]
    assert doc.headings[0].level == 2
    assert doc.headings[0].text == "This week"
    for block in doc.blocks:  # every block's offset points at its own text
        assert doc.text[block.offset : block.offset + len(block.text)] == block.text
    assert "alert" not in doc.text


def test_links_are_spans_into_the_text_with_their_titles_and_duplicates_fold() -> None:
    doc = render_notes(HTML)

    assert [doc.link_title(span) for span in doc.links] == [
        "Jane & Co",
        "a link",
        "patreon.com/show",
        "the same link again",
    ]
    assert [span.url for span in doc.unique_links()] == [
        "https://example.com/guest",
        "https://x.org",
        "https://patreon.com/show",
    ]
    assert doc.link_count == 3


def test_timestamps_become_seekable_spans_but_not_inside_a_link() -> None:
    doc = render_notes(HTML)

    assert [span.ms for span in doc.timestamps] == [754_000, 3_723_000]
    assert doc.text[doc.timestamps[0].start : doc.timestamps[0].end] == "12:34"


@pytest.mark.parametrize(
    ("text", "ms"),
    [
        ("12:34", 754_000),
        ("1:02:03", 3_723_000),
        ("0:05", 5_000),
        ("12:99", -1),
        ("1:99:00", -1),
        ("x", -1),
    ],
)
def test_timestamp_parsing(text: str, ms: int) -> None:
    assert parse_timestamp_ms(text) == ms


def test_empty_and_image_only_notes_say_so() -> None:
    assert render_notes("").is_empty
    assert empty_sentence(render_notes("")) == "This episode has no show notes."
    pictures = render_notes('<p><img src="cover.png"></p>')
    assert pictures.image_only
    assert "View in Browser" in empty_sentence(pictures)


def test_plain_text_notes_split_on_blank_lines() -> None:
    doc = render_notes("One paragraph.\n\nAnother at 3:05.")
    assert [block.text for block in doc.blocks] == ["One paragraph.", "Another at 3:05."]
    assert doc.timestamps[0].ms == 185_000


# -- the four formats ------------------------------------------------------------------------


def test_plain_text_keeps_structure_and_reduces_links_to_their_text() -> None:
    text = notes_export.export(render_notes(HTML), notes_export.PLAIN)
    assert text.startswith("This week\n\nWe talk to Jane & Co at 12:34 and more.\n")
    assert "• First point" in text
    assert "https://" not in text


def test_plain_text_with_links_keeps_every_address_in_brackets() -> None:
    text = notes_export.export(render_notes(HTML), notes_export.PLAIN_LINKS)
    assert "Jane & Co [https://example.com/guest]" in text
    assert "a link [https://x.org]" in text
    # A link whose text is its address is not written twice.
    assert "patreon.com/show [https://patreon.com/show]" in text


def test_markdown_keeps_headings_lists_and_links() -> None:
    text = notes_export.export(render_notes(HTML), notes_export.MARKDOWN)
    assert text.startswith("## This week\n\n")
    assert "[Jane & Co](https://example.com/guest)" in text
    assert "- First point\n- Second with [a link](https://x.org)\n" in text


def test_formatted_is_html_with_an_rtf_beside_it() -> None:
    doc = render_notes(HTML)
    html = notes_export.export(doc, notes_export.FORMATTED)
    assert html.startswith("<h2>This week</h2>")
    assert '<a href="https://x.org">a link</a>' in html
    assert "<ul>\n<li>First point</li>" in html
    rtf = notes_export.to_rtf(doc)
    assert rtf.startswith("{\\rtf1")
    assert 'HYPERLINK "https://x.org"' in rtf
    assert "\\bullet" in rtf


def test_the_spoken_copy_names_the_format_and_counts_words() -> None:
    doc = render_notes("<p>one two three</p>")
    assert (
        notes_export.spoken_copy("markdown", doc) == "Copied the show notes as markdown, 3 words."
    )
    assert notes_export.normalize_format("nonsense") == notes_export.PLAIN


def test_the_browser_page_keeps_images_and_drops_scripts_and_handlers() -> None:
    page = notes_export.browser_page(
        '<p>Hi <img src="a.png" onload="x()"><script>bad()</script></p>',
        title="Ep",
        page_title="Show - Ep",
    )
    assert "<title>Show - Ep</title>" in page
    assert '<img src="a.png">' in page
    assert "onload" not in page and "bad()" not in page


# -- the episode's own note ---------------------------------------------------------------


def test_the_episode_level_note_is_written_replaced_and_removed(
    tmp_path: Path, monkeypatch
) -> None:
    from quill.core.podcasts import episode_notes as notes

    monkeypatch.setattr(notes, "episode_notes_path", lambda: tmp_path / "notes.json")

    assert notes.set_episode_level_note("show", "ep", "") is False  # nothing to remove
    assert notes.set_episode_level_note("show", "ep", "Loved the second half.") is True
    assert (
        notes.set_episode_level_note("show", "ep", "Loved the second half.") is False
    )  # unchanged
    kept = notes.episode_level_note(notes.load_episode_notes(), "show", "ep")
    assert kept is not None and kept.text == "Loved the second half." and kept.position_ms == 0
    assert notes.set_episode_level_note("show", "ep", "Changed my mind.") is True
    assert len([n for n in notes.load_episode_notes() if n.episode_guid == "ep"]) == 1
    assert notes.set_episode_level_note("show", "ep", "") is True
    assert notes.episode_level_note(notes.load_episode_notes(), "show", "ep") is None


def test_history_keeps_the_now_playing_switch_and_the_copy_format(tmp_path: Path) -> None:
    from quill.core.podcasts import history

    kept = history.load_history(tmp_path)
    assert kept.switch_to_now_playing is False
    assert kept.notes_copy_format == "plain"
    kept.switch_to_now_playing = True
    kept.notes_copy_format = "markdown"
    history.save_history(tmp_path, kept)
    again = history.load_history(tmp_path)
    assert again.switch_to_now_playing is True
    assert again.notes_copy_format == "markdown"
