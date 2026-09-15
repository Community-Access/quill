"""What the caret is standing in, when what it is standing in is a list.

These tests are written against the *sentence a listener would hear* rather than
against the parse tree, because the parse tree is not the product: the counts
here are the ones spoken aloud, and a count that is off by one is a document
somebody reorganises wrongly.
"""

from __future__ import annotations

import pytest

from quill.core.list_structure import (
    BULLET,
    DEFINITION,
    NUMBERED,
    list_context_at,
    supports_lists,
)


def at(text: str, needle: str, *, markup_kind: str = "markdown"):
    """The context where *needle* first appears -- readable positions in tests."""
    offset = text.index(needle)
    return list_context_at(text, offset, markup_kind=markup_kind)


# -- the markup gate --------------------------------------------------------- #


@pytest.mark.parametrize("kind", ["markdown", "html"])
def test_markdown_and_html_can_hold_lists(kind: str) -> None:
    assert supports_lists(kind)


@pytest.mark.parametrize("kind", ["plain", "yaml", "", None])
def test_no_other_language_is_searched_for_lists(kind: str | None) -> None:
    assert not supports_lists(kind)


def test_a_hyphen_in_a_plain_letter_is_a_dash_not_a_bullet() -> None:
    # The whole reason the language is passed in rather than sniffed: prose is
    # full of hyphens, and a cue that fired on them would be superstition.
    text = "Dear Kate,\n- and this is the bit I meant -\nyours, Sam\n"
    assert list_context_at(text, text.index("and this"), markup_kind="plain") is None


# -- Markdown: the basics ----------------------------------------------------- #


def test_a_flat_bullet_list_knows_its_kind_and_its_size() -> None:
    text = "Shopping\n\n- bread\n- milk\n- jam\n"
    context = at(text, "milk")
    assert context is not None
    assert (context.kind, context.depth, context.size, context.index) == (BULLET, 1, 3, 2)
    assert context.label == "Bulleted list"


def test_a_numbered_list_is_a_different_kind_because_order_is_meaning() -> None:
    text = "1. wake up\n2. get out of bed\n3. drag a comb\n"
    context = at(text, "drag")
    assert context is not None
    assert (context.kind, context.size, context.index) == (NUMBERED, 3, 3)


def test_a_paren_numbered_list_counts_too() -> None:
    context = at("1) one\n2) two\n", "two")
    assert context is not None and context.kind == NUMBERED


@pytest.mark.parametrize("marker", ["-", "*", "+"])
def test_every_bullet_marker_markdown_allows_is_a_bullet(marker: str) -> None:
    context = at(f"{marker} only item\n", "only")
    assert context is not None and context.kind == BULLET


def test_body_text_outside_a_list_is_not_in_one() -> None:
    text = "- bread\n\nA paragraph that follows.\n"
    assert at(text, "paragraph") is None


def test_a_heading_between_two_lists_ends_the_first_one() -> None:
    text = "- bread\n- milk\n\n## Later\n\n- jam\n"
    first = at(text, "bread")
    second = at(text, "jam")
    assert first is not None and second is not None
    assert first.size == 2
    assert second.size == 1
    assert first.key != second.key


# -- Markdown: nesting -------------------------------------------------------- #


NESTED = """\
- fruit
    - apple
    - pear
    - plum
- veg
    - leek
"""


def test_a_nested_item_reports_its_own_level() -> None:
    context = at(NESTED, "pear")
    assert context is not None
    assert (context.depth, context.size, context.index) == (2, 3, 2)


def test_the_outer_level_counts_only_the_outer_items() -> None:
    # Six item lines in the document; two of them are level one. "6 items" here
    # would be the single most misleading thing this module could say.
    context = at(NESTED, "fruit")
    assert context is not None
    assert (context.depth, context.size) == (1, 2)


def test_two_sub_lists_under_two_bullets_are_two_lists() -> None:
    apple = at(NESTED, "apple")
    leek = at(NESTED, "leek")
    assert apple is not None and leek is not None
    assert apple.size == 3
    assert leek.size == 1
    assert apple.key != leek.key


def test_three_levels_deep_is_level_three() -> None:
    text = "- one\n    - two\n        - three\n"
    context = at(text, "three")
    assert context is not None and context.depth == 3


def test_a_tab_indent_nests_the_same_as_spaces() -> None:
    context = at("- one\n\t- two\n", "two")
    assert context is not None and context.depth == 2


def test_a_mixed_nest_takes_its_kind_from_its_own_level() -> None:
    text = "1. steps\n    - a note\n    - another\n"
    outer = at(text, "steps")
    inner = at(text, "a note")
    assert outer is not None and inner is not None
    assert outer.kind == NUMBERED
    assert inner.kind == BULLET


# -- Markdown: continuation lines --------------------------------------------- #


def test_a_wrapped_item_is_still_inside_its_item() -> None:
    text = "- a long item that\n  wraps onto a second line\n- another\n"
    context = at(text, "wraps")
    assert context is not None
    assert (context.size, context.index) == (2, 1)


def test_a_second_paragraph_indented_under_an_item_is_still_in_the_list() -> None:
    text = "- first\n\n  still the first item\n\n- second\n"
    context = at(text, "still the first")
    assert context is not None and context.index == 1


def test_a_loose_list_with_blank_lines_between_items_is_one_list() -> None:
    text = "- one\n\n- two\n\n- three\n"
    context = at(text, "two")
    assert context is not None and context.size == 3


# -- Markdown: the things that look like lists and are not --------------------- #


@pytest.mark.parametrize("rule", ["---", "***", "___", "- - -"])
def test_a_thematic_break_is_a_rule_not_a_one_item_list(rule: str) -> None:
    text = f"Above\n\n{rule}\n\nBelow\n"
    assert list_context_at(text, text.index(rule), markup_kind="markdown") is None


def test_a_bullet_inside_a_fenced_code_block_is_a_code_sample() -> None:
    text = "Example:\n\n```sh\n- not a bullet\n```\n"
    assert at(text, "not a bullet") is None


def test_a_tilde_fence_hides_a_bullet_too() -> None:
    text = "~~~\n- sample\n~~~\n"
    assert at(text, "sample") is None


def test_a_real_list_after_a_fence_is_still_found() -> None:
    text = "```\n- sample\n```\n\n- real\n- also real\n"
    context = at(text, "also real")
    assert context is not None and context.size == 2


# -- Markdown: definition lists ------------------------------------------------ #


DEFS = """\
Quill
: the editor

Lite
: the small one
"""


def test_a_definition_term_says_it_is_a_term() -> None:
    context = at(DEFS, "Quill")
    assert context is not None
    assert (context.kind, context.role) == (DEFINITION, "term")


def test_a_definition_body_says_it_is_a_definition() -> None:
    context = at(DEFS, "the editor")
    assert context is not None
    assert (context.kind, context.role) == (DEFINITION, "definition")
    assert context.item_noun == "term"


# -- HTML ---------------------------------------------------------------------- #


HTML_LIST = """\
<h1>Shopping</h1>
<ul>
  <li>bread</li>
  <li>milk</li>
  <li>jam</li>
</ul>
<p>after</p>
"""


def test_an_html_bullet_list_reads_like_the_markdown_one() -> None:
    context = at(HTML_LIST, "milk", markup_kind="html")
    assert context is not None
    assert (context.kind, context.depth, context.size, context.index) == (BULLET, 1, 3, 2)


def test_text_after_the_closing_tag_is_out_of_the_list() -> None:
    assert at(HTML_LIST, "after", markup_kind="html") is None


def test_text_before_the_list_is_not_in_it() -> None:
    assert at(HTML_LIST, "Shopping", markup_kind="html") is None


def test_an_ordered_list_is_numbered() -> None:
    text = "<ol><li>one</li><li>two</li></ol>"
    context = at(text, "two", markup_kind="html")
    assert context is not None and context.kind == NUMBERED


HTML_NESTED = """\
<ul>
  <li>fruit
    <ul>
      <li>apple</li>
      <li>pear</li>
    </ul>
  </li>
  <li>veg</li>
</ul>
"""


def test_a_nested_html_list_reports_its_level() -> None:
    context = at(HTML_NESTED, "pear", markup_kind="html")
    assert context is not None
    assert (context.depth, context.size, context.index) == (2, 2, 2)


def test_a_nested_html_list_does_not_inflate_its_parent_count() -> None:
    context = at(HTML_NESTED, "fruit", markup_kind="html")
    assert context is not None
    assert (context.depth, context.size) == (1, 2)


def test_html_definition_lists_name_terms_and_definitions() -> None:
    text = "<dl>\n<dt>Quill</dt>\n<dd>the editor</dd>\n<dt>Lite</dt>\n<dd>small</dd>\n</dl>"
    term = at(text, "Quill", markup_kind="html")
    body = at(text, "the editor", markup_kind="html")
    assert term is not None and body is not None
    assert (term.kind, term.role) == (DEFINITION, "term")
    assert body.role == "definition"
    assert term.size == 2  # two terms, counted; the definitions are not items


def test_an_unclosed_list_still_reports_rather_than_giving_up() -> None:
    # An editor buffer mid-typing is the normal case, not the exception. A
    # parser that refused here would take the cue out at the moment it is most
    # wanted -- while the list is being written.
    context = at("<ul>\n  <li>one</li>\n  <li>half typed", "half", markup_kind="html")
    assert context is not None and context.kind == BULLET


def test_a_list_tag_inside_a_comment_is_prose() -> None:
    text = "<!-- <ul><li>example</li></ul> -->\n<p>real text</p>"
    assert at(text, "real text", markup_kind="html") is None


def test_a_list_tag_inside_a_script_is_a_string() -> None:
    text = '<script>var x = "<ul><li>";</script>\n<p>real</p>'
    assert at(text, "real", markup_kind="html") is None


def test_between_two_items_is_still_inside_the_list() -> None:
    text = "<ul>\n<li>one</li>\nGAP\n<li>two</li>\n</ul>"
    context = at(text, "GAP", markup_kind="html")
    assert context is not None and context.role == "item"


def test_uppercase_tags_are_the_same_tags() -> None:
    context = at("<UL><LI>one</LI></UL>", "one", markup_kind="html")
    assert context is not None and context.kind == BULLET


def test_attributes_on_the_list_tag_do_not_hide_it() -> None:
    context = at('<ul class="tidy" id="x"><li>one</li></ul>', "one", markup_kind="html")
    assert context is not None and context.kind == BULLET


# -- boundaries ----------------------------------------------------------------- #


def test_an_empty_document_has_no_list() -> None:
    assert list_context_at("", 0, markup_kind="markdown") is None


@pytest.mark.parametrize("offset", [-50, 0, 10_000])
def test_an_offset_outside_the_text_is_clamped_not_crashed(offset: int) -> None:
    list_context_at("- one\n", offset, markup_kind="markdown")


# -- the pickers can insert what the announcer can read ------------------------
#
# Here rather than in a tagging test file because it is *this* module's
# contract: an editor that announces a definition list and cannot insert one is
# backwards, and the same goes for every list shape read above.


def test_every_list_shape_this_module_reads_can_also_be_inserted() -> None:
    from quill.core.tagging import (
        HTML_TAG_CHOICES,
        MARKDOWN_TAG_CHOICES,
        build_markdown_insertion,
    )

    # HTML: all three containers and all three item kinds.
    for tag in ("ul", "ol", "dl", "li", "dt", "dd"):
        assert tag in HTML_TAG_CHOICES, tag

    # Markdown: the three list kinds, by the names the picker shows.
    for kind in ("Bullet List", "Numbered List", "Definition List"):
        assert kind in MARKDOWN_TAG_CHOICES, kind

    # And what the definition-list builder writes is what the reader recognises.
    written = build_markdown_insertion("Definition List", "Quill").inserted_text
    context = list_context_at(written, written.index("Quill"), markup_kind="markdown")
    assert context is not None
    assert (context.kind, context.role) == (DEFINITION, "term")


def test_nothing_the_markdown_picker_offers_is_missing_a_builder() -> None:
    # The gap this catches is the quiet one: Underline and Horizontal Rule had
    # builders and no menu row for months, and a row with no builder would be
    # the same dead end facing the other way.
    from quill.core.tagging import MARKDOWN_TAG_CHOICES, build_markdown_insertion

    for kind in MARKDOWN_TAG_CHOICES:
        result = build_markdown_insertion(kind, "sample")
        assert result.inserted_text, kind
        assert result.inserted_text != "sample", f"{kind} wrote its input back unchanged"
        assert 0 <= result.caret_offset <= len(result.inserted_text), kind


def test_every_void_element_offered_is_written_self_closing() -> None:
    from quill.core.tagging import HTML_TAG_CHOICES, VOID_HTML_TAGS, build_html_insertion

    for tag in VOID_HTML_TAGS & set(HTML_TAG_CHOICES):
        written = build_html_insertion(tag, "", {}).inserted_text
        assert written == f"<{tag} />", written


def test_the_html_picker_is_searched_by_what_a_tag_does() -> None:
    # Nobody types "dl" when what they want is a glossary, and nobody types
    # "abbr" when what they want is an acronym.
    from quill.core.tagging import search_html_tag_choices

    for query, expected in (
        ("glossary", "dl"),
        ("acronym", "abbr"),
        ("image caption", "figcaption"),
        ("table header", "thead"),
        ("subtitles", "track"),
        ("divider", "hr"),
        ("dropdown", "select"),
    ):
        assert expected in search_html_tag_choices(query)[:5], (query, expected)
