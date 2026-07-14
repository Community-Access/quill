from quill.core.tagging import (
    HTML_TAG_CHOICES,
    MARKDOWN_TAG_CHOICES,
    build_block_alignment,
    build_block_attributes,
    build_html_code_block,
    build_html_insertion,
    build_html_table,
    build_markdown_code_block,
    build_markdown_insertion,
    build_markdown_table,
    build_span_insertion,
    merge_span_attributes,
    parse_attribute_pairs,
    render_span_attributes,
    search_html_tag_choices,
    search_markdown_tag_choices,
)


def test_parse_attribute_pairs_supports_key_value_and_boolean() -> None:
    parsed = parse_attribute_pairs("class=note; id=main; disabled")
    assert parsed == {"class": "note", "id": "main", "disabled": ""}


def test_build_html_insertion_wraps_selected_text() -> None:
    result = build_html_insertion("strong", "hello", {"class": "callout"})
    assert result.inserted_text == '<strong class="callout">hello</strong>'
    assert result.caret_offset == len(result.inserted_text)


def test_build_html_insertion_for_void_tag() -> None:
    result = build_html_insertion("img", "", {"src": "image.png", "alt": "Sample"})
    assert result.inserted_text == '<img src="image.png" alt="Sample" />'


def test_build_markdown_link_uses_target() -> None:
    result = build_markdown_insertion("Link", "docs", "https://example.com")
    assert result.inserted_text == "[docs](https://example.com)"


def test_build_markdown_table_template() -> None:
    result = build_markdown_insertion("Table", "")
    assert "| Column 1 | Column 2 |" in result.inserted_text


def test_build_markdown_table_with_custom_dimensions() -> None:
    result = build_markdown_table(3, 4, include_header=True)
    assert result.inserted_text.count("| --- | --- | --- | --- |") == 1
    assert result.inserted_text.count("|  |  |  |  |") == 3


def test_build_html_table_with_header() -> None:
    result = build_html_table(2, 3, include_header=True)
    assert "<thead>" in result.inserted_text
    assert result.inserted_text.count("<th>") == 3
    assert result.inserted_text.count("<td></td>") == 6


def test_build_markdown_code_block_with_language_hint() -> None:
    result = build_markdown_code_block("print('hi')", language_hint="python")
    assert result.inserted_text.startswith("```python\n")


def test_build_html_code_block_with_language_hint() -> None:
    result = build_html_code_block("console.log('hi')", language_hint="javascript")
    assert '<code class="language-javascript">' in result.inserted_text


def test_build_markdown_bold_without_selection_inserts_pair() -> None:
    result = build_markdown_insertion("Bold", "")
    assert result.inserted_text == "****"
    assert result.caret_offset == 2


def test_build_markdown_italic_without_selection_inserts_pair() -> None:
    result = build_markdown_insertion("Italic", "")
    assert result.inserted_text == "**"
    assert result.caret_offset == 1


def test_build_markdown_underline_uses_inline_html() -> None:
    # Markdown has no native underline syntax; the insertion uses inline
    # HTML <u>...</u>, which CommonMark viewers that support raw HTML
    # render as underlined text.
    selected = build_markdown_insertion("Underline", "hello")
    assert selected.inserted_text == "<u>hello</u>"
    assert selected.caret_offset == len("<u>hello</u>")
    empty = build_markdown_insertion("Underline", "")
    assert empty.inserted_text == "<u></u>"
    assert empty.caret_offset == 3


def test_markdown_choices_include_heading_levels_four_to_six() -> None:
    assert "Heading 4" in MARKDOWN_TAG_CHOICES
    assert "Heading 5" in MARKDOWN_TAG_CHOICES
    assert "Heading 6" in MARKDOWN_TAG_CHOICES


def test_html_choices_include_form_controls() -> None:
    for tag in ("form", "label", "input", "textarea", "select", "option", "button"):
        assert tag in HTML_TAG_CHOICES


def test_search_html_choices_matches_radio_to_input() -> None:
    results = search_html_tag_choices("radio")
    assert results
    assert results[0] == "input"


def test_search_html_choices_matches_heading_words() -> None:
    results = search_html_tag_choices("heading 1")
    assert results[0] == "h1"
    assert "h2" in search_html_tag_choices("heading two")


def test_search_markdown_choices_matches_heading_six() -> None:
    results = search_markdown_tag_choices("h6")
    assert "Heading 6" in results


def test_build_markdown_heading_six_without_selection() -> None:
    result = build_markdown_insertion("Heading 6", "")
    assert result.inserted_text == "###### "


# --------------------------------------------------------------------------- #
# Hidden-codes builders: run spans and alignment fenced divs
# --------------------------------------------------------------------------- #
def test_render_span_attributes_fixed_order() -> None:
    rendered = render_span_attributes({
        "color": "#C00000",
        "font-family": "Arial",
        "font-size": "14",
        "underline": "1",
    })
    assert rendered == 'font-family="Arial" font-size="14" color="#C00000" underline'


def test_build_span_insertion_wraps_selection() -> None:
    result = build_span_insertion("Hello", {"font-family": "Arial", "font-size": "14"})
    assert result.inserted_text == '[Hello]{font-family="Arial" font-size="14"}'
    assert result.caret_offset == len(result.inserted_text)


def test_build_span_insertion_merges_existing_span() -> None:
    existing = '[Hello]{font-family="Arial" font-size="14"}'
    result = build_span_insertion(existing, {"color": "#C00000"})
    assert result.inserted_text == '[Hello]{font-family="Arial" font-size="14" color="#C00000"}'


def test_build_span_insertion_empty_selection_places_caret_inside() -> None:
    result = build_span_insertion("", {"underline": "1"})
    assert result.inserted_text == "[]{underline}"
    assert result.caret_offset == 1


def test_build_span_insertion_no_attributes_is_noop() -> None:
    result = build_span_insertion("Hello", {})
    assert result.inserted_text == "Hello"


def test_merge_span_attributes_ignores_empty_updates() -> None:
    merged = merge_span_attributes({"font-family": "Arial"}, {"color": "", "font-size": "12"})
    assert merged == {"font-family": "Arial", "font-size": "12"}


def test_build_block_alignment_wraps_selection() -> None:
    result = build_block_alignment("para", "center")
    assert result.inserted_text == '::: {align="center"}\npara\n:::'


def test_build_block_alignment_rejects_unknown_align() -> None:
    result = build_block_alignment("x", "sideways")
    assert result.inserted_text == "x"


def test_build_block_alignment_empty_selection_uses_placeholder() -> None:
    result = build_block_alignment("", "right")
    assert result.inserted_text == '::: {align="right"}\ntext\n:::'


def test_render_span_flags_order() -> None:
    rendered = render_span_attributes({
        "underline": "1",
        "strike": "1",
        "superscript": "1",
        "subscript": "1",
    })
    assert rendered == "underline strike superscript subscript"


def test_build_block_attributes_multi_and_merge() -> None:
    first = build_block_attributes("para", {"line-spacing": "1.5", "pstyle": "quote"})
    assert first.inserted_text == '::: {pstyle="quote" line-spacing="1.5"}\npara\n:::'
    merged = build_block_attributes(first.inserted_text, {"align": "center"})
    assert merged.inserted_text == (
        '::: {align="center" pstyle="quote" line-spacing="1.5"}\npara\n:::'
    )


def test_build_clear_formatting_keeps_links() -> None:
    from quill.core.tagging import build_clear_formatting

    result = build_clear_formatting('[**b**]{color="red" strike} and *i* and [x](u)')
    assert result.inserted_text == "b and i and [x](u)"


def test_strip_run_formatting_nested_spans() -> None:
    from quill.core.tagging import strip_run_formatting

    assert strip_run_formatting("[[a]{strike}]{underline}") == "a"


def test_build_page_break_marker() -> None:
    from quill.core.tagging import build_page_break

    assert build_page_break().inserted_text == "::: pagebreak"
