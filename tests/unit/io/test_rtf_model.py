from quill.io.rtf_model import (
    InlineSpan,
    RichDocument,
    RichParagraph,
    analyze_markdown,
    format_at_markdown_offset,
    markdown_offset_to_plain_offset,
    markdown_to_rich,
    plain_offset_to_markdown_offset,
    rich_to_markdown,
    rich_to_rtf,
    rtf_to_rich,
    scan_rtf_features,
)


def test_markdown_to_rich_paragraph_styles() -> None:
    doc = markdown_to_rich("# Title\n- item\nplain line")
    assert [p.style for p in doc.paragraphs] == ["heading", "bullet", "paragraph"]
    assert doc.paragraphs[0].level == 1
    assert doc.paragraphs[0].text() == "Title"
    assert doc.paragraphs[1].text() == "item"


def test_markdown_to_rich_inline_runs() -> None:
    doc = markdown_to_rich("A **bold** and *italic* word")
    spans = doc.paragraphs[0].spans
    bold = [s for s in spans if s.bold]
    italic = [s for s in spans if s.italic]
    assert bold and bold[0].text == "bold"
    assert italic and italic[0].text == "italic"


def test_markdown_to_rich_link_span() -> None:
    doc = markdown_to_rich("see [QUILL](https://example.com) now")
    link = [s for s in doc.paragraphs[0].spans if s.href]
    assert link and link[0].text == "QUILL"
    assert link[0].href == "https://example.com"


def test_nested_bold_italic() -> None:
    doc = markdown_to_rich("**bold *both* end**")
    spans = doc.paragraphs[0].spans
    both = [s for s in spans if s.bold and s.italic]
    assert both and both[0].text == "both"


def test_rich_to_markdown_round_trip() -> None:
    markdown = "# Heading\n- first\nbody with **bold** and *italic* and [x](u)"
    assert rich_to_markdown(markdown_to_rich(markdown)) == markdown


def test_rich_to_markdown_merges_adjacent_runs() -> None:
    doc = RichDocument(
        paragraphs=[
            RichParagraph(
                spans=[InlineSpan("a", bold=True), InlineSpan("b", bold=True)],
            )
        ]
    )
    assert rich_to_markdown(doc) == "**ab**"


def test_plain_text_excludes_structure() -> None:
    doc = markdown_to_rich("# Title\n- item\nbody")
    assert doc.plain_text() == "Title\nitem\nbody"


def test_rtf_round_trip_through_rich() -> None:
    markdown = "# Heading One\n\nA **bold** word.\n- one\n- two"
    rtf = rich_to_rtf(markdown_to_rich(markdown))
    assert rtf.startswith("{\\rtf1\\ansi")
    restored = rich_to_markdown(rtf_to_rich(rtf))
    assert restored == markdown


def test_analyze_plain_text_matches_model() -> None:
    markdown = "# Title\n**bold** plain"
    analysis = analyze_markdown(markdown)
    assert analysis.plain_text == "Title\nbold plain"


def test_md_to_plain_length_covers_caret_at_end() -> None:
    markdown = "**bold**"
    analysis = analyze_markdown(markdown)
    assert len(analysis.md_to_plain) == len(markdown) + 1
    # Caret after the closing ** lands at the end of the visible word.
    assert analysis.md_to_plain[len(markdown)] == len("bold")


def test_markdown_offset_to_plain_inside_bold() -> None:
    markdown = "x **bold** y"
    # The 'b' of bold is at md offset 4; visible offset should be 2 ("x b").
    assert markdown_offset_to_plain_offset(markdown, 4) == 2


def test_plain_offset_round_trips_to_markdown() -> None:
    markdown = "x **bold** y"
    plain = markdown_offset_to_plain_offset(markdown, 4)
    assert plain_offset_to_markdown_offset(markdown, plain) == 4


def test_heading_prefix_maps_to_first_visible_char() -> None:
    markdown = "## Big"
    # Caret anywhere in "## " maps to the first visible char of "Big".
    assert markdown_offset_to_plain_offset(markdown, 0) == 0
    assert markdown_offset_to_plain_offset(markdown, 2) == 0


def test_format_at_offset_reports_bold() -> None:
    markdown = "a **bold** b"
    fmt = format_at_markdown_offset(markdown, 6)
    assert fmt.bold is True
    assert fmt.italic is False


def test_format_at_offset_reports_heading_level() -> None:
    fmt = format_at_markdown_offset("### Deep", 6)
    assert fmt.heading_level == 3


def test_format_at_offset_reports_link() -> None:
    markdown = "go [here](http://x) now"
    fmt = format_at_markdown_offset(markdown, 5)
    assert fmt.href == "http://x"


def test_format_at_offset_plain_is_empty() -> None:
    fmt = format_at_markdown_offset("plain text", 3)
    assert fmt.bold is False and fmt.italic is False and fmt.href is None
    assert fmt.heading_level == 0 and fmt.bullet is False


def test_scan_rtf_features_flags_tables_and_images() -> None:
    rtf = r"{\rtf1\ansi \trowd \cell \pict\pngblip ffff}"
    found = scan_rtf_features(rtf)
    assert "tables" in found
    assert "images" in found


def test_scan_rtf_features_clean_subset_is_empty() -> None:
    rtf = r"{\rtf1\ansi\pard {\b bold} text\par}"
    assert scan_rtf_features(rtf) == []


# --------------------------------------------------------------------------- #
# Hidden-codes: run spans and alignment fenced divs
# --------------------------------------------------------------------------- #
def test_span_attributes_parsed_onto_run() -> None:
    doc = markdown_to_rich('[Hi]{font-family="Arial" font-size="14" color="#C00000" underline}')
    span = doc.paragraphs[0].spans[0]
    assert span.text == "Hi"
    assert span.font_family == "Arial"
    assert span.font_size_pt == 14
    assert span.color == "#C00000"
    assert span.underline is True


def test_span_highlight_parsed() -> None:
    doc = markdown_to_rich('[x]{highlight="yellow"}')
    assert doc.paragraphs[0].spans[0].highlight == "yellow"


def test_span_round_trip_is_identity() -> None:
    md = '[Hello]{font-family="Arial" font-size="14" color="#C00000"} world'
    assert rich_to_markdown(markdown_to_rich(md)) == md


def test_span_wraps_bold_inner() -> None:
    md = "[**bold word**]{underline} after"
    assert rich_to_markdown(markdown_to_rich(md)) == md


def test_fenced_div_alignment_round_trip() -> None:
    md = '::: {align="center"}\nCentered text here.\n:::'
    assert rich_to_markdown(markdown_to_rich(md)) == md
    assert markdown_to_rich(md).paragraphs[0].align == "center"


def test_fenced_div_groups_consecutive_paragraphs() -> None:
    md = '::: {align="right"}\nfirst\nsecond\n:::'
    doc = markdown_to_rich(md)
    assert [p.align for p in doc.paragraphs] == ["right", "right"]
    assert rich_to_markdown(doc) == md


def test_fenced_div_excluded_from_plain_text() -> None:
    analysis = analyze_markdown('::: {align="center"}\nhi there\n:::')
    assert analysis.plain_text == "hi there"


def test_invalid_alignment_ignored() -> None:
    doc = markdown_to_rich('::: {align="sideways"}\nbody\n:::')
    assert doc.paragraphs[0].align is None


def test_format_at_offset_reports_font_and_size() -> None:
    md = '[Hello]{font-family="Arial" font-size="14"} world'
    fmt = format_at_markdown_offset(md, 3)
    assert fmt.font_family == "Arial"
    assert fmt.font_size_pt == 14


def test_format_at_offset_reports_align() -> None:
    md = '::: {align="center"}\nhello\n:::'
    # Caret inside the visible word reports the paragraph alignment.
    fmt = format_at_markdown_offset(md, len('::: {align="center"}\nhe'))
    assert fmt.align == "center"


def test_span_offset_maps_into_label() -> None:
    md = 'x [bold]{color="#FF0000"} y'
    # The 'b' of "bold" sits at md offset 3; its visible offset is 2 ("x b").
    assert markdown_offset_to_plain_offset(md, 3) == 2
    assert analyze_markdown(md).plain_text == "x bold y"


# --------------------------------------------------------------------------- #
# Hidden codes, full vocabulary: strike/super/sub + block + page break
# --------------------------------------------------------------------------- #
def test_strike_super_sub_parsed() -> None:
    doc = markdown_to_rich("[a]{strike} [b]{superscript} [c]{subscript}")
    spans = [s for s in doc.paragraphs[0].spans if s.text in ("a", "b", "c")]
    by = {s.text: s for s in spans}
    assert by["a"].strike and not by["a"].superscript
    assert by["b"].superscript and not by["b"].strike
    assert by["c"].subscript


def test_strike_super_sub_round_trip() -> None:
    for md in ("[a]{strike}", "[b]{superscript}", "[c]{subscript}", "[d]{underline strike}"):
        assert rich_to_markdown(markdown_to_rich(md)) == md


def test_block_attributes_round_trip() -> None:
    md = (
        '::: {align="center" pstyle="quote" line-spacing="2" '
        'space-before="12" space-after="6" indent="36" first-line-indent="18"}\n'
        "body line\n:::"
    )
    doc = markdown_to_rich(md)
    para = doc.paragraphs[0]
    assert para.align == "center"
    assert para.named_style == "quote"
    assert para.line_spacing == "2"
    assert para.space_before == 12
    assert para.indent == 36
    assert para.first_line_indent == 18
    assert rich_to_markdown(doc) == md


def test_invalid_named_style_and_spacing_ignored() -> None:
    doc = markdown_to_rich('::: {pstyle="bogus" line-spacing="3"}\nx\n:::')
    assert doc.paragraphs[0].named_style is None
    assert doc.paragraphs[0].line_spacing is None


def test_page_break_round_trip_and_paragraph() -> None:
    md = "before\n::: pagebreak\nafter"
    doc = markdown_to_rich(md)
    assert [p.style for p in doc.paragraphs] == ["paragraph", "pagebreak", "paragraph"]
    assert rich_to_markdown(doc) == md


def test_page_break_excluded_from_visible_text() -> None:
    analysis = analyze_markdown("a\n::: pagebreak\nb")
    assert analysis.plain_text == "a\nb"


def test_interrogate_reports_block_and_inline() -> None:
    md = '::: {line-spacing="2" pstyle="quote"}\n[x]{strike}\n:::'
    fmt = format_at_markdown_offset(md, len('::: {line-spacing="2" pstyle="quote"}\n[x'))
    assert fmt.strike is True
    assert fmt.line_spacing == "2"
    assert fmt.named_style == "quote"


def test_scan_no_longer_flags_recovered_attributes() -> None:
    rtf = r"{\rtf1\ansi\pard {\ul under}{\cf1 color}\par}"
    assert scan_rtf_features(rtf) == []
