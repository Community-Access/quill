# ruff: noqa: E501 -- fixtures are exact WordPress markup, kept whole to compare byte for byte.
"""Blocks to readable Markdown fences and back (wordpress.md 8.1)."""

from __future__ import annotations

import pytest

from quill.core.wordpress.blocks import parse, serialize
from quill.core.wordpress.fences import (
    FenceProblem,
    blocks_to_markdown,
    check_markdown,
    convert_markdown,
    markdown_to_blocks,
    post_to_markdown,
)

# WordPress 6.4+ save output for each supported shape, paired with the
# Markdown QUILL shows for it.
SHAPES: dict[str, tuple[str, str]] = {
    "paragraph": (
        "<!-- wp:paragraph -->\n<p>Hello</p>\n<!-- /wp:paragraph -->",
        "Hello",
    ),
    "paragraph_inline": (
        "<!-- wp:paragraph -->\n<p>A <strong>bold</strong>, <em>soft</em> &amp; "
        '<a href="https://example.org/?a=1&amp;b=2">linked</a> <code>x &lt; y</code> line'
        "<br>next</p>\n<!-- /wp:paragraph -->",
        "A **bold**, *soft* & [linked](https://example.org/?a=1&b=2) `x < y` line<br>next",
    ),
    "paragraph_escapes": (
        "<!-- wp:paragraph -->\n<p># not a heading *star* [x] \\ back</p>\n<!-- /wp:paragraph -->",
        "\\# not a heading \\*star\\* \\[x\\] \\\\ back",
    ),
    "paragraph_numbered_text": (
        "<!-- wp:paragraph -->\n<p>1. Not a list</p>\n<!-- /wp:paragraph -->",
        "1\\. Not a list",
    ),
    "paragraph_fence_text": (
        "<!-- wp:paragraph -->\n<p>::: button looks like a fence</p>\n<!-- /wp:paragraph -->",
        "\\::: button looks like a fence",
    ),
    "heading_2": (
        '<!-- wp:heading -->\n<h2 class="wp-block-heading">Opening hours</h2>\n<!-- /wp:heading -->',
        "## Opening hours",
    ),
    "heading_4": (
        '<!-- wp:heading {"level":4} -->\n<h4 class="wp-block-heading">Small</h4>\n<!-- /wp:heading -->',
        "#### Small",
    ),
    "list": (
        '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>One</li>\n'
        "<!-- /wp:list-item -->\n\n<!-- wp:list-item -->\n<li>Two</li>\n<!-- /wp:list-item --></ul>\n"
        "<!-- /wp:list -->",
        "- One\n- Two",
    ),
    "ordered_nested_list": (
        '<!-- wp:list {"ordered":true} -->\n<ol class="wp-block-list"><!-- wp:list-item -->\n'
        '<li>First<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>Inner</li>\n'
        "<!-- /wp:list-item --></ul>\n<!-- /wp:list --></li>\n<!-- /wp:list-item -->\n\n"
        "<!-- wp:list-item -->\n<li>Second</li>\n<!-- /wp:list-item --></ol>\n<!-- /wp:list -->",
        "1. First\n   - Inner\n2. Second",
    ),
    "quote": (
        '<!-- wp:quote -->\n<blockquote class="wp-block-quote"><!-- wp:paragraph -->\n<p>To be.</p>\n'
        "<!-- /wp:paragraph -->\n\n<!-- wp:paragraph -->\n<p>Or not.</p>\n<!-- /wp:paragraph -->"
        "<cite>Hamlet</cite></blockquote>\n<!-- /wp:quote -->",
        "> To be.\n>\n> Or not.\n>\n> -- Hamlet",
    ),
    "quote_without_cite": (
        '<!-- wp:quote -->\n<blockquote class="wp-block-quote"><!-- wp:paragraph -->\n<p>-- dash</p>\n'
        "<!-- /wp:paragraph --></blockquote>\n<!-- /wp:quote -->",
        "> \\-- dash",
    ),
    "image": (
        '<!-- wp:image -->\n<figure class="wp-block-image"><img src="https://example.org/a.jpg" '
        'alt="Volunteers at the fair"/></figure>\n<!-- /wp:image -->',
        "![Volunteers at the fair](https://example.org/a.jpg)",
    ),
    "image_full": (
        '<!-- wp:image {"id":12,"sizeSlug":"large","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-large"><img src="https://example.org/a.jpg" '
        'alt="Tom &amp; &quot;Jerry&quot;" class="wp-image-12"/><figcaption class="wp-element-caption">'
        "At the <em>spring</em> fair</figcaption></figure>\n<!-- /wp:image -->",
        '![Tom & "Jerry"](https://example.org/a.jpg "At the *spring* fair") {id=12 size=large link=none}',
    ),
    "table": (
        '<!-- wp:table -->\n<figure class="wp-block-table"><table class="has-fixed-layout"><thead><tr>'
        "<th>Day</th><th>Hours</th></tr></thead><tbody><tr><td>Mon</td><td>9 | 5</td></tr>"
        "<tr><td>Tue</td><td></td></tr></tbody></table></figure>\n<!-- /wp:table -->",
        "| Day | Hours |\n| --- | --- |\n| Mon | 9 \\| 5 |\n| Tue |  |",
    ),
    "separator": (
        '<!-- wp:separator -->\n<hr class="wp-block-separator has-alpha-channel-opacity"/>\n'
        "<!-- /wp:separator -->",
        "---",
    ),
    "code": (
        '<!-- wp:code -->\n<pre class="wp-block-code"><code>if a &lt; b &amp;&amp; c:\n'
        "    items&#91;0] = 1</code></pre>\n<!-- /wp:code -->",
        "```\nif a < b && c:\n    items[0] = 1\n```",
    ),
    "code_isolated_url": (
        '<!-- wp:code -->\n<pre class="wp-block-code"><code>https:&#47;&#47;example.org</code></pre>\n'
        "<!-- /wp:code -->",
        "```\nhttps://example.org\n```",
    ),
    "preformatted": (
        '<!-- wp:preformatted -->\n<pre class="wp-block-preformatted">  spaced\n   out</pre>\n'
        "<!-- /wp:preformatted -->",
        "::: preformatted\n  spaced\n   out\n::: end preformatted",
    ),
    "buttons": (
        '<!-- wp:buttons -->\n<div class="wp-block-buttons"><!-- wp:button -->\n'
        '<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" '
        'href="https://example.org/book">Book a session</a></div>\n<!-- /wp:button -->\n\n'
        '<!-- wp:button -->\n<div class="wp-block-button"><a class="wp-block-button__link '
        'wp-element-button">No link</a></div>\n<!-- /wp:button --></div>\n<!-- /wp:buttons -->',
        '::: button "Book a session" https://example.org/book\n::: button "No link"',
    ),
    "columns": (
        '<!-- wp:columns -->\n<div class="wp-block-columns"><!-- wp:column -->\n'
        '<div class="wp-block-column"><!-- wp:paragraph -->\n<p>Morning sessions run from nine.</p>\n'
        "<!-- /wp:paragraph --></div>\n<!-- /wp:column -->\n\n"
        '<!-- wp:column {"width":"33.33%"} -->\n<div class="wp-block-column" style="flex-basis:33.33%">'
        "<!-- wp:paragraph -->\n<p>Evening sessions run from six.</p>\n<!-- /wp:paragraph -->\n\n"
        "<!-- wp:paragraph -->\n<p>Bring water.</p>\n<!-- /wp:paragraph --></div>\n"
        "<!-- /wp:column --></div>\n<!-- /wp:columns -->",
        "::: columns\n::: column\nMorning sessions run from nine.\n::: column 33.33%\n"
        "Evening sessions run from six.\n\nBring water.\n::: end columns",
    ),
    "group": (
        '<!-- wp:group {"layout":{"type":"constrained"}} -->\n<div class="wp-block-group">'
        "<!-- wp:paragraph -->\n<p>Inside</p>\n<!-- /wp:paragraph --></div>\n<!-- /wp:group -->",
        "::: group\nInside\n::: end group",
    ),
    "details": (
        '<!-- wp:details -->\n<details class="wp-block-details"><summary>What does it cost?</summary>'
        "<!-- wp:paragraph -->\n<p>The first session is free.</p>\n<!-- /wp:paragraph --></details>\n"
        "<!-- /wp:details -->",
        '::: details "What does it cost?"\nThe first session is free.\n::: end details',
    ),
    "embed": (
        '<!-- wp:embed {"url":"https://www.youtube.com/watch?v=abc","type":"video",'
        '"providerNameSlug":"youtube","responsive":true,"className":"wp-embed-aspect-16-9 '
        'wp-has-aspect-ratio"} -->\n<figure class="wp-block-embed is-type-video is-provider-youtube '
        'wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper">'
        "\nhttps://www.youtube.com/watch?v=abc\n</div></figure>\n<!-- /wp:embed -->",
        "::: embed https://www.youtube.com/watch?v=abc type=video provider=youtube aspect=16-9",
    ),
    "embed_plain": (
        '<!-- wp:embed {"url":"https://example.org/post"} -->\n<figure class="wp-block-embed">'
        '<div class="wp-block-embed__wrapper">\nhttps://example.org/post\n</div></figure>\n'
        "<!-- /wp:embed -->",
        "::: embed https://example.org/post",
    ),
    "spacer": (
        '<!-- wp:spacer -->\n<div style="height:100px" aria-hidden="true" class="wp-block-spacer"></div>\n'
        "<!-- /wp:spacer -->",
        "::: spacer",
    ),
    "spacer_height": (
        '<!-- wp:spacer {"height":"40px"} -->\n<div style="height:40px" aria-hidden="true" '
        'class="wp-block-spacer"></div>\n<!-- /wp:spacer -->',
        "::: spacer 40px",
    ),
}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_block_to_markdown(shape: str) -> None:
    html, md = SHAPES[shape]
    markdown, islands = post_to_markdown(html)
    assert markdown == md + "\n"
    assert islands == {}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_markdown_to_block_matches_wordpress_save(shape: str) -> None:
    html, md = SHAPES[shape]
    result = convert_markdown(md, {})
    assert result.problems == []
    assert result.html == html


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_markdown_round_trip_is_stable(shape: str) -> None:
    _html, md = SHAPES[shape]
    again, islands = post_to_markdown(markdown_to_blocks(md))
    assert again == md + "\n"
    assert islands == {}


def test_whole_post_round_trips_byte_for_byte() -> None:
    post = "\n\n".join(html for html, _md in SHAPES.values())
    markdown, islands = post_to_markdown(post)
    assert islands == {}
    assert markdown_to_blocks(markdown, islands) == post


MIXED = (
    '<!-- wp:heading -->\n<h2 class="wp-block-heading">Spring fair</h2>\n<!-- /wp:heading -->\n\n'
    '<!-- wp:paragraph {"className":"lead"} -->\n<p class="lead">Styled paragraph.</p>\n'
    "<!-- /wp:paragraph -->\n\n"
    '<!-- wp:columns -->\n<div class="wp-block-columns"><!-- wp:column -->\n<div class="wp-block-column">'
    '<!-- wp:columns -->\n<div class="wp-block-columns"><!-- wp:column -->\n<div class="wp-block-column">'
    "<!-- wp:paragraph -->\n<p>Deep</p>\n<!-- /wp:paragraph --></div>\n<!-- /wp:column --></div>\n"
    "<!-- /wp:columns --></div>\n<!-- /wp:column -->\n\n"
    '<!-- wp:column -->\n<div class="wp-block-column"><!-- wp:jetpack/contact-form {"to":"a@b.org",'
    '"subject":"Hi \\u003c3"} -->\n<div class="wp-block-jetpack-contact-form">'
    '<!-- wp:jetpack/field-email {"required":true} /--></div>\n<!-- /wp:jetpack/contact-form --></div>\n'
    "<!-- /wp:column --></div>\n<!-- /wp:columns -->\n\n"
    '<!-- wp:latest-posts {"postsToShow":3,"displayPostDate":true} /-->\n\n'
    "<p>Classic HTML from <b>before</b> blocks.</p>\n\n"
    "<!-- wp:paragraph -->\n<p>Closing words.</p>\n<!-- /wp:paragraph -->"
)


class TestIslands:
    def test_mixed_post_markdown(self) -> None:
        markdown, islands = post_to_markdown(MIXED)
        lines = markdown.splitlines()
        assert lines[0] == "## Spring fair"
        assert lines[2].startswith("::: block core/paragraph island-")
        assert "::: columns" in lines
        assert "Deep" in lines
        assert any(line.startswith("::: block jetpack/contact-form island-") for line in lines)
        assert any(line.startswith("::: block core/latest-posts island-") for line in lines)
        assert any(line.startswith("::: block core/freeform island-") for line in lines)
        assert lines[-1] == "Closing words."
        assert len(islands) == 4

    def test_mixed_post_round_trips_exactly(self) -> None:
        markdown, islands = post_to_markdown(MIXED)
        assert markdown_to_blocks(markdown, islands) == MIXED

    def test_island_text_is_the_original_bytes(self) -> None:
        _markdown, islands = post_to_markdown(MIXED)
        form = next(text for text in islands.values() if "contact-form" in text)
        assert form in MIXED
        assert form.startswith(
            '<!-- wp:jetpack/contact-form {"to":"a@b.org","subject":"Hi \\u003c3"} -->'
        )
        assert form.endswith("<!-- /wp:jetpack/contact-form -->")

    def test_islands_survive_edits_around_them(self) -> None:
        markdown, islands = post_to_markdown(MIXED)
        edited = markdown.replace("Closing words.", "New closing words.")
        out = markdown_to_blocks(edited, islands)
        assert out == MIXED.replace("Closing words.", "New closing words.")

    def test_moved_island_is_restored_where_it_now_sits(self) -> None:
        markdown, islands = post_to_markdown(MIXED)
        lines = markdown.splitlines()
        posts = next(line for line in lines if "latest-posts" in line)
        lines.remove(posts)
        out = markdown_to_blocks("\n".join([posts, "", *lines]), islands)
        assert out.startswith(
            '<!-- wp:latest-posts {"postsToShow":3,"displayPostDate":true} /-->\n\n'
        )

    def test_unsupported_attrs_make_an_island_not_a_loss(self) -> None:
        text = '<!-- wp:heading {"level":2} -->\n<h2 class="wp-block-heading">Explicit</h2>\n<!-- /wp:heading -->'
        markdown, islands = post_to_markdown(text)
        assert markdown.startswith("::: block core/heading island-")
        assert markdown_to_blocks(markdown, islands) == text

    def test_odd_button_inside_buttons_is_an_inner_island(self) -> None:
        text = (
            '<!-- wp:buttons -->\n<div class="wp-block-buttons"><!-- wp:button -->\n'
            '<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" '
            'href="/a">Plain</a></div>\n<!-- /wp:button -->\n\n<!-- wp:button {"backgroundColor":"accent"} -->\n'
            '<div class="wp-block-button"><a class="wp-block-button__link has-accent-background-color '
            'has-background wp-element-button" href="/b">Fancy</a></div>\n<!-- /wp:button --></div>\n'
            "<!-- /wp:buttons -->"
        )
        markdown, islands = post_to_markdown(text)
        lines = markdown.splitlines()
        assert lines[0] == "::: buttons"
        assert lines[1] == '::: button "Plain" /a'
        assert lines[2].startswith("::: block core/button island-")
        assert lines[3] == "::: end buttons"
        assert markdown_to_blocks(markdown, islands) == text

    def test_malformed_comments_round_trip_through_islands(self) -> None:
        text = (
            "<!-- wp:paragraph -->\n<p>ok</p>\n<!-- /wp:paragraph -->\n\n"
            "<!-- wp:group -->\n<div>never closed\n\n"
            "<!-- /wp:quote --> stray"
        )
        markdown, islands = post_to_markdown(text)
        assert markdown.splitlines()[0] == "ok"
        assert markdown_to_blocks(markdown, islands) == text

    def test_whitespace_between_blocks_normalises_to_one_blank_line(self) -> None:
        text = '<!-- wp:separator -->\n<hr class="wp-block-separator has-alpha-channel-opacity"/>\n<!-- /wp:separator -->'
        markdown, islands = post_to_markdown("\n\n\n" + text + "\n" + text + "  ")
        assert markdown == "---\n\n---\n"
        assert markdown_to_blocks(markdown, islands) == text + "\n\n" + text

    def test_blocks_to_markdown_accepts_parsed_blocks(self) -> None:
        markdown, islands = blocks_to_markdown(parse(MIXED))
        assert markdown_to_blocks(markdown, islands) == serialize(parse(MIXED))

    def test_empty_post(self) -> None:
        assert post_to_markdown("") == ("", {})
        assert markdown_to_blocks("") == ""


class TestWritingNewMarkdown:
    def test_section_8_1_example(self) -> None:
        md = (
            '::: button "Book a session" https://example.org/book\n\n'
            "::: columns\n::: column\nMorning sessions run from nine.\n::: column\n"
            "Evening sessions run from six.\n::: end columns\n\n"
            '::: details "What does it cost?"\nThe first session is free.\n::: end details\n'
        )
        result = convert_markdown(md)
        assert result.problems == []
        names = [b.name for b in parse(result.html) if not b.freeform]
        assert names == ["core/buttons", "core/columns", "core/details"]
        assert 'href="https://example.org/book">Book a session</a>' in result.html

    def test_unquoted_button_text(self) -> None:
        out = markdown_to_blocks("::: button Book now https://example.org")
        assert (
            '<a class="wp-block-button__link wp-element-button" href="https://example.org">Book now</a>'
            in out
        )

    def test_separate_button_groups(self) -> None:
        out = markdown_to_blocks('::: button "A" /a\n\n::: button "B" /b')
        assert [b.name for b in parse(out) if not b.freeform] == ["core/buttons", "core/buttons"]

    def test_soft_wrapped_paragraph_keeps_its_lines(self) -> None:
        out = markdown_to_blocks("one\ntwo")
        assert out == "<!-- wp:paragraph -->\n<p>one\ntwo</p>\n<!-- /wp:paragraph -->"

    def test_paragraph_ends_at_a_heading(self) -> None:
        out = markdown_to_blocks("text\n## Head")
        assert [b.name for b in parse(out) if not b.freeform] == ["core/paragraph", "core/heading"]

    def test_bare_ampersand_and_angle_are_escaped(self) -> None:
        out = markdown_to_blocks("Fish & chips < 5")
        assert "<p>Fish &amp; chips &lt; 5</p>" in out

    def test_unpaired_asterisk_is_literal(self) -> None:
        assert "<p>2 * 3 = 6</p>" in markdown_to_blocks("2 * 3 = 6")

    def test_nested_details_inside_columns(self) -> None:
        md = '::: columns\n::: column\n::: details "More"\nHidden\n::: end details\n::: column\nRight\n::: end columns'
        result = convert_markdown(md)
        assert result.problems == []
        (columns,) = [b for b in parse(result.html) if not b.freeform]
        assert columns.inner_blocks[0].inner_blocks[0].name == "core/details"

    def test_quote_with_inner_list(self) -> None:
        out = markdown_to_blocks("> - a\n> - b")
        (quote,) = [b for b in parse(out) if not b.freeform]
        assert quote.inner_blocks[0].name == "core/list"

    def test_crlf_markdown(self) -> None:
        assert markdown_to_blocks("## Hi\r\n\r\nThere") == markdown_to_blocks("## Hi\n\nThere")


class TestProblems:
    def test_unknown_fence_is_kept_as_text_and_reported(self) -> None:
        result = convert_markdown("Intro\n\n::: carousel fast\n")
        assert result.problems == [
            FenceProblem(3, "QUILL does not know a 'carousel' block, so this line is kept as text.")
        ]
        assert "<p>::: carousel fast</p>" in result.html

    def test_missing_island(self) -> None:
        problems = check_markdown("::: block acme/form island-9", {})
        assert len(problems) == 1
        assert problems[0].line == 1
        assert "missing" in problems[0].message

    def test_unclosed_container(self) -> None:
        result = convert_markdown('::: details "Q"\nAnswer\n')
        assert [p.line for p in result.problems] == [1]
        assert "end details" in result.problems[0].message
        assert "<p>Answer</p>" in result.html

    def test_unclosed_inner_container_reported_and_outer_closes(self) -> None:
        md = "::: columns\n::: column\n::: group\nx\n::: column\ny\n::: end columns"
        result = convert_markdown(md)
        assert [p.line for p in result.problems] == [3]
        (columns,) = [b for b in parse(result.html) if not b.freeform]
        assert len(columns.inner_blocks) == 2

    def test_stray_end_line(self) -> None:
        problems = check_markdown("Text\n::: end columns")
        assert [p.line for p in problems] == [2]

    def test_column_outside_columns(self) -> None:
        result = convert_markdown("::: column")
        assert len(result.problems) == 1
        assert "<p>::: column</p>" in result.html

    def test_text_before_first_column(self) -> None:
        result = convert_markdown("::: columns\nStray\n::: column\nOk\n::: end columns")
        assert [p.line for p in result.problems] == [1]
        (columns,) = [b for b in parse(result.html) if not b.freeform]
        assert len(columns.inner_blocks) == 2

    def test_unclosed_code_fence(self) -> None:
        result = convert_markdown("```\nprint(1)")
        assert [p.line for p in result.problems] == [1]
        assert "<code>print(1)</code>" in result.html

    def test_embed_without_address(self) -> None:
        result = convert_markdown("::: embed")
        assert len(result.problems) == 1

    def test_empty_fence(self) -> None:
        assert len(check_markdown(":::")) == 1

    def test_bad_image_option(self) -> None:
        problems = check_markdown("![a](b.png) {zoom=2}")
        assert [p.line for p in problems] == [1]

    def test_never_raises_on_junk(self) -> None:
        junk = '::: "\n::: end\n> \n- \n|\n| a |\n```\n:::columns\n::: block\n![](x'
        result = convert_markdown(junk)
        assert isinstance(result.html, str)

    def test_problem_lines_inside_quotes_keep_document_numbers(self) -> None:
        problems = check_markdown("Intro\n\n> ::: wobble")
        assert [p.line for p in problems] == [3]
