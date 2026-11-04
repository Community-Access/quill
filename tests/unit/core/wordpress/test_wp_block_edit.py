"""Finding and changing blocks in both document formats (wordpress.md 8.3, 8.5)."""

from __future__ import annotations

from quill.core.wordpress import block_edit as be
from quill.core.wordpress import block_spans as bs
from quill.core.wordpress.block_settings import apply_settings
from quill.core.wordpress.blocks import parse, serialize
from quill.core.wordpress.fences import check_markdown, convert_markdown

P1 = "<!-- wp:paragraph -->\n<p>First words.</p>\n<!-- /wp:paragraph -->"
H2 = '<!-- wp:heading -->\n<h2 class="wp-block-heading">A heading</h2>\n<!-- /wp:heading -->'
P2 = "<!-- wp:paragraph -->\n<p>Second words.</p>\n<!-- /wp:paragraph -->"
HTML = f"{P1}\n\n{H2}\n\n{P2}\n"

MARKDOWN = (
    "Intro paragraph\nstill the intro.\n\n"
    "## Times\n\n"
    "::: columns\n"
    "::: column\n"
    "Morning sessions run from nine.\n"
    "::: column\n"
    "Evening sessions run from six.\n"
    "::: end columns\n\n"
    '::: button "Book a session" https://example.org/book\n\n'
    "- tea\n- cake\n\n"
    "> Quoted words.\n\n"
    "::: block jetpack/contact-form island-1\n"
)
ISLANDS = {
    "island-1": (
        '<!-- wp:jetpack/contact-form -->\n<div class="wp-block-jetpack-contact-form">'
        "</div>\n<!-- /wp:jetpack/contact-form -->"
    )
}


def _names(spans: list[bs.Span]) -> list[str]:
    return [s.name for s in spans]


# --------------------------------------------------------------------------- #
# spans


def test_html_spans_cover_exactly_each_block() -> None:
    spans = bs.html_spans(HTML)
    assert _names(spans) == ["core/paragraph", "core/heading", "core/paragraph"]
    assert [HTML[s.start : s.end] for s in spans] == [P1, H2, P2]


def test_markdown_spans_mirror_the_fence_reader() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    tops = [s.name for s in spans if s.depth == 0]
    assert tops == [
        "core/paragraph",
        "core/heading",
        "core/columns",
        "core/buttons",
        "core/list",
        "core/quote",
        "jetpack/contact-form",
    ]
    columns = next(s for s in spans if s.name == "core/columns")
    assert MARKDOWN[columns.start : columns.end].endswith("::: end columns")
    assert [spans[c].name for c in columns.children] == ["core/column", "core/column"]
    assert spans[-1].island == "island-1"
    assert check_markdown(MARKDOWN, ISLANDS) == []


def test_markdown_span_offsets_survive_windows_line_endings() -> None:
    text = "One\r\n\r\n## Two\r\n"
    spans = bs.markdown_spans(text)
    assert [text[s.start : s.end] for s in spans] == ["One", "## Two"]


def test_describe_reads_markdown_blocks_through_the_converter() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    said = [bs.describe_span(MARKDOWN, "markdown", spans, i, ISLANDS) for i in bs.stops(spans)]
    assert said[0] == "Paragraph block: Intro paragraph still the intro."
    assert said[1] == "Heading level 2 block: Times"
    assert said[2] == "Columns block: 2 columns"
    assert said[3].startswith("Column block: Morning")
    assert "Button block: Book a session" in said
    assert said[-1] == "Contact form block (from a plugin)"


def test_next_and_previous_stops() -> None:
    spans = bs.html_spans(HTML)
    assert bs.next_stop(spans, 0) == 1
    assert bs.next_stop(spans, spans[2].start) is None
    assert bs.previous_stop(spans, spans[1].start) == 0
    assert bs.previous_stop(spans, 0) is None
    assert bs.previous_stop(spans, spans[1].start + 3) == 1


def test_list_items_are_not_stops() -> None:
    html = (
        '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>a</li>\n'
        "<!-- /wp:list-item --></ul>\n<!-- /wp:list -->"
    )
    spans = bs.html_spans(html)
    assert _names(spans) == ["core/list", "core/list-item"]
    assert bs.stops(spans) == [0]


def test_spoken_move_puts_the_position_after_the_name() -> None:
    said = bs.spoken_move("Image block: Volunteers at the fair", 4, 12)
    assert said == "Image block, 4 of 12: Volunteers at the fair"
    assert bs.spoken_move("Separator block", 2, 3) == "Separator block, 2 of 3"


def test_where_am_i_names_the_nesting() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    caret = MARKDOWN.index("Evening") + 3
    said = bs.where_am_i(MARKDOWN, "markdown", spans, caret, ISLANDS)
    assert said == "Paragraph block: Evening sessions run from six., inside column 2 of Columns."


def test_where_am_i_between_blocks_names_the_next_one() -> None:
    text = "One\n\n\n\n## Two\n"
    spans = bs.markdown_spans(text)
    said = bs.where_am_i(text, "markdown", spans, 5)
    assert said == "Not in a block. The next one is Heading level 2 block: Two."


# --------------------------------------------------------------------------- #
# structure


def test_move_up_and_down_keep_every_byte() -> None:
    spans = bs.html_spans(HTML)
    up = be.move(HTML, spans, 1, -1)
    assert isinstance(up, be.Edit)
    assert up.text == f"{H2}\n\n{P1}\n\n{P2}\n"
    assert up.caret == 0
    down = be.move(HTML, spans, 1, 1)
    assert isinstance(down, be.Edit)
    assert down.text == f"{P1}\n\n{P2}\n\n{H2}\n"
    assert down.text[down.caret :].startswith(H2)


def test_move_past_the_ends_says_why() -> None:
    spans = bs.html_spans(HTML)
    assert be.move(HTML, spans, 0, -1) == "This is already the first block here."
    assert be.move(HTML, spans, 2, 1) == "This is already the last block here."


def test_move_in_markdown_swaps_whole_fences() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    columns = next(i for i, s in enumerate(spans) if s.name == "core/columns")
    edit = be.move(MARKDOWN, spans, columns, -1)
    assert isinstance(edit, be.Edit)
    assert edit.text.index("::: columns") < edit.text.index("## Times")
    assert check_markdown(edit.text, ISLANDS) == []


def test_duplicate_markdown_island_gets_a_fresh_token() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    edit = be.duplicate(MARKDOWN, "markdown", spans, len(spans) - 1, ISLANDS)
    assert edit.islands == {"island-2": ISLANDS["island-1"]}
    assert edit.text.endswith(
        "::: block jetpack/contact-form island-1\n\n::: block jetpack/contact-form island-2\n"
    )
    merged = {**ISLANDS, **edit.islands}
    html = convert_markdown(edit.text, merged).html
    assert html.count("wp:jetpack/contact-form") == 4


def test_remove_takes_the_gap_with_it() -> None:
    spans = bs.html_spans(HTML)
    assert be.remove(HTML, spans, 1).text == f"{P1}\n\n{P2}\n"
    assert be.remove(HTML, spans, 2).text == f"{P1}\n\n{H2}\n"
    only = bs.html_spans(P1)
    assert be.remove(P1, only, 0).text == ""


def test_group_and_ungroup_in_html() -> None:
    spans = bs.html_spans(HTML)
    grouped = be.group(HTML, "html", spans, 1)
    assert isinstance(grouped, be.Edit)
    assert (
        '<!-- wp:group {"layout":{"type":"constrained"}} -->\n<div class="wp-block-group">'
        + H2
        + "</div>\n<!-- /wp:group -->"
    ) in grouped.text
    assert serialize(parse(grouped.text)) == grouped.text
    after = bs.html_spans(grouped.text)
    group_index = next(i for i, s in enumerate(after) if s.name == "core/group")
    ungrouped = be.ungroup(grouped.text, after, group_index)
    assert isinstance(ungrouped, be.Edit)
    assert ungrouped.text == HTML


def test_group_in_markdown_is_a_fence() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    edit = be.group(MARKDOWN, "markdown", spans, 1)
    assert isinstance(edit, be.Edit)
    assert "::: group\n## Times\n::: end group" in edit.text
    assert check_markdown(edit.text, ISLANDS) == []
    again = bs.markdown_spans(edit.text)
    group_index = next(i for i, s in enumerate(again) if s.name == "core/group")
    back = be.ungroup(edit.text, again, group_index)
    assert isinstance(back, be.Edit)
    assert back.text == MARKDOWN


def test_parts_of_a_parent_cannot_be_grouped_or_ungrouped_wrongly() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    column = next(i for i, s in enumerate(spans) if s.name == "core/column")
    assert isinstance(be.group(MARKDOWN, "markdown", spans, column), str)
    assert be.ungroup(MARKDOWN, spans, 0) == "Only a Group block can be ungrouped."


# --------------------------------------------------------------------------- #
# change to


def test_change_targets() -> None:
    assert ("heading-2", "Heading level 2") in be.change_targets("core/paragraph")
    assert be.change_targets("core/list") == [("paragraphs", "Paragraphs")]
    assert be.change_targets("core/image") == []


def test_paragraph_to_heading_and_back_in_html() -> None:
    spans = bs.html_spans(HTML)
    edit = be.change_to(HTML, "html", spans, 0, "heading-3")
    assert isinstance(edit, be.Edit)
    assert edit.text.startswith(
        '<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">First words.</h3>\n'
        "<!-- /wp:heading -->\n\n"
    )
    assert edit.text.endswith(f"{H2}\n\n{P2}\n")
    back = be.change_to(edit.text, "html", bs.html_spans(edit.text), 0, "paragraph")
    assert isinstance(back, be.Edit)
    assert back.text == HTML


def test_list_to_paragraphs_in_html_flattens_nested_items() -> None:
    html = (
        '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>Tea</li>\n'
        "<!-- /wp:list-item -->\n\n<!-- wp:list-item -->\n<li>Cake<!-- wp:list -->\n"
        '<ul class="wp-block-list"><!-- wp:list-item -->\n<li>Lemon</li>\n'
        "<!-- /wp:list-item --></ul>\n<!-- /wp:list --></li>\n<!-- /wp:list-item --></ul>\n"
        "<!-- /wp:list -->"
    )
    edit = be.change_to(html, "html", bs.html_spans(html), 0, "paragraphs")
    assert isinstance(edit, be.Edit)
    assert [b.name for b in parse(edit.text) if not b.freeform] == ["core/paragraph"] * 3
    assert "<p>Lemon</p>" in edit.text


def test_quote_to_paragraphs_keeps_the_citation() -> None:
    html = (
        '<!-- wp:quote -->\n<blockquote class="wp-block-quote"><!-- wp:paragraph -->\n'
        "<p>Words.</p>\n<!-- /wp:paragraph --><cite>Someone</cite></blockquote>\n"
        "<!-- /wp:quote -->"
    )
    edit = be.change_to(html, "html", bs.html_spans(html), 0, "paragraphs")
    assert isinstance(edit, be.Edit)
    assert edit.text == (
        "<!-- wp:paragraph -->\n<p>Words.</p>\n<!-- /wp:paragraph -->\n\n"
        "<!-- wp:paragraph -->\n<p>Someone</p>\n<!-- /wp:paragraph -->"
    )


def test_markdown_changes() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    heading = be.change_to(MARKDOWN, "markdown", spans, 0, "heading-2")
    assert isinstance(heading, be.Edit)
    assert heading.text.startswith("## Intro paragraph still the intro.\n\n## Times")
    para = be.change_to(MARKDOWN, "markdown", spans, 1, "paragraph")
    assert isinstance(para, be.Edit)
    assert "\n\nTimes\n\n" in para.text
    lst = next(i for i, s in enumerate(spans) if s.name == "core/list")
    paras = be.change_to(MARKDOWN, "markdown", spans, lst, "paragraphs")
    assert isinstance(paras, be.Edit)
    assert "\n\ntea\n\ncake\n\n" in paras.text
    quote = next(i for i, s in enumerate(spans) if s.name == "core/quote")
    unquoted = be.change_to(MARKDOWN, "markdown", spans, quote, "paragraphs")
    assert isinstance(unquoted, be.Edit)
    assert "\n\nQuoted words.\n\n" in unquoted.text
    as_list = be.change_to(MARKDOWN, "markdown", spans, 0, "list")
    assert isinstance(as_list, be.Edit)
    assert as_list.text.startswith("- Intro paragraph\n- still the intro.\n\n")
    as_quote = be.change_to(MARKDOWN, "markdown", spans, 0, "quote")
    assert isinstance(as_quote, be.Edit)
    assert as_quote.text.startswith("> Intro paragraph\n> still the intro.\n\n")


def test_change_to_something_not_offered_is_refused() -> None:
    spans = bs.html_spans(HTML)
    assert be.change_to(HTML, "html", spans, 0, "paragraphs") == "This block cannot change to that."


def test_heading_text_that_looks_like_a_list_is_escaped() -> None:
    text = "## - not a list\n"
    edit = be.change_to(text, "markdown", bs.markdown_spans(text), 0, "paragraph")
    assert isinstance(edit, be.Edit)
    assert edit.text == "\\- not a list\n"


# --------------------------------------------------------------------------- #
# insert


def test_insert_goes_after_the_block_the_caret_is_in() -> None:
    spans = bs.html_spans(HTML)
    caret = HTML.index("First") + 2
    at, inserted, caret_after, added = be.insert_markup(HTML, "html", spans, caret, P2)
    assert at == spans[0].end
    assert inserted == "\n\n" + P2
    assert caret_after == at + 2
    assert added == {}
    new = HTML[:at] + inserted + HTML[at:]
    assert serialize(parse(new)) == new
    assert len(bs.html_spans(new)) == 4


def test_insert_in_markdown_converts_and_pads() -> None:
    text = "One\n## Two\n"
    spans = bs.markdown_spans(text)
    at, inserted, caret_after, added = be.insert_markup(text, "markdown", spans, 1, H2)
    assert (at, inserted) == (3, "\n\n## A heading\n")
    assert caret_after == 5
    assert added == {}
    new = text[:at] + inserted + text[at:]
    assert new == "One\n\n## A heading\n\n## Two\n"


def test_insert_in_markdown_islands_what_markdown_cannot_say() -> None:
    markup = '<!-- wp:latest-posts {"postsToShow":3} /-->'
    at, inserted, _caret, added = be.insert_markup(
        MARKDOWN, "markdown", bs.markdown_spans(MARKDOWN), len(MARKDOWN), markup, ISLANDS
    )
    assert inserted.strip() == "::: block core/latest-posts island-2"
    assert added == {"island-2": markup}
    assert at == len(MARKDOWN)


def test_insert_into_an_empty_document() -> None:
    at, inserted, caret, _added = be.insert_markup("", "html", [], 0, P1)
    assert (at, inserted, caret) == (0, P1 + "\n", 0)


# --------------------------------------------------------------------------- #
# replace_block


def test_replace_block_in_html_touches_only_that_block() -> None:
    spans = bs.html_spans(HTML)

    def change(block):
        block.attrs = {"level": 3}

    edit = be.replace_block(HTML, "html", spans, 1, change)
    assert isinstance(edit, be.Edit)
    assert edit.text == HTML.replace("<!-- wp:heading -->", '<!-- wp:heading {"level":3} -->')


def test_replace_block_in_markdown_islands_what_it_cannot_write() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    edit = be.replace_block(
        MARKDOWN, "markdown", spans, 0, lambda b: b.attrs.update(dropCap=True), ISLANDS
    )
    assert isinstance(edit, be.Edit)
    assert edit.text.startswith("::: block core/paragraph island-2\n\n## Times")
    assert '{"dropCap":true}' in edit.islands["island-2"]


def test_replace_block_inside_a_markdown_container() -> None:
    spans = bs.markdown_spans(MARKDOWN)
    second = [i for i, s in enumerate(spans) if s.name == "core/column"][1]
    edit = be.replace_block(
        MARKDOWN,
        "markdown",
        spans,
        second,
        lambda b: apply_settings(b, {"width": "25%"}),
        ISLANDS,
    )
    assert isinstance(edit, be.Edit)
    assert "::: column 25%\nEvening" in edit.text
    assert check_markdown(edit.text, {**ISLANDS, **edit.islands}) == []
