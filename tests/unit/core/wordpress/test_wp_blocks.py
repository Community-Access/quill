# ruff: noqa: E501 -- fixtures are exact WordPress markup, kept whole to compare byte for byte.
"""The WordPress block grammar: parse, serialize, describe (wordpress.md 8)."""

from __future__ import annotations

import random

import pytest

from quill.core.wordpress.blocks import (
    CORE_TEXT_BLOCKS,
    Block,
    describe,
    first_words,
    parse,
    serialize,
    serialize_attributes,
    walk,
)

MIXED_POST = (
    "<!-- wp:heading -->\n"
    '<h2 class="wp-block-heading">Spring fair</h2>\n'
    "<!-- /wp:heading -->\n\n"
    "<!-- wp:paragraph -->\n<p>Join us &amp; bring a friend.</p>\n<!-- /wp:paragraph -->\n\n"
    '<!-- wp:columns {"align":"wide"} -->\n'
    '<div class="wp-block-columns alignwide"><!-- wp:column -->\n'
    '<div class="wp-block-column"><!-- wp:paragraph -->\n<p>Morning sessions run from nine.</p>\n'
    "<!-- /wp:paragraph --></div>\n<!-- /wp:column -->\n\n"
    '<!-- wp:column {"width":"33.33%"} -->\n'
    '<div class="wp-block-column" style="flex-basis:33.33%"><!-- wp:columns -->\n'
    '<div class="wp-block-columns"><!-- wp:column -->\n<div class="wp-block-column">'
    "<!-- wp:paragraph -->\n<p>Nested</p>\n<!-- /wp:paragraph --></div>\n<!-- /wp:column --></div>\n"
    "<!-- /wp:columns --></div>\n<!-- /wp:column --></div>\n<!-- /wp:columns -->\n\n"
    '<!-- wp:jetpack/contact-form {"subject":"Hello \\u003c\\u003e","to":"a@example.org"} -->\n'
    '<div class="wp-block-jetpack-contact-form"><!-- wp:jetpack/field-name {"required":true} /-->'
    "</div>\n<!-- /wp:jetpack/contact-form -->\n\n"
    '<!-- wp:latest-posts {"postsToShow":3} /-->\n\n'
    "<p>Some classic HTML left over from before blocks.</p>\n\n"
    "<!-- wp:spacer   -->\n"
    '<div style="height:100px" aria-hidden="true" class="wp-block-spacer"></div>\n'
    "<!--   /wp:spacer -->"
)


def names(blocks: list[Block]) -> list[str | None]:
    return [b.name for b in blocks if not (b.freeform and not b.inner_html.strip())]


class TestParse:
    def test_single_paragraph(self) -> None:
        text = "<!-- wp:paragraph -->\n<p>Hi</p>\n<!-- /wp:paragraph -->"
        (block,) = parse(text)
        assert block.name == "core/paragraph"
        assert block.attrs == {}
        assert block.inner_html == "\n<p>Hi</p>\n"
        assert block.inner_content == ["\n<p>Hi</p>\n"]
        assert block.inner_blocks == []
        assert not block.freeform

    def test_unnamespaced_name_means_core(self) -> None:
        (block,) = parse("<!-- wp:separator /-->")
        assert block.name == "core/separator"
        assert block.namespace == "core"

    def test_namespaced_plugin_name(self) -> None:
        (block,) = parse('<!-- wp:jetpack/contact-form {"to":"x"} /-->')
        assert block.name == "jetpack/contact-form"
        assert block.namespace == "jetpack"
        assert block.attrs == {"to": "x"}

    def test_void_block_has_no_content(self) -> None:
        (block,) = parse('<!-- wp:latest-posts {"postsToShow":3} /-->')
        assert block.inner_content == []
        assert block.attrs == {"postsToShow": 3}

    def test_json_attrs_decode_unicode_escapes(self) -> None:
        (block,) = parse('<!-- wp:x {"a":"\\u003cb\\u003e \\u002d\\u002d","n":[1,{"k":true}]} /-->')
        assert block.attrs == {"a": "<b> --", "n": [1, {"k": True}]}

    def test_attrs_may_contain_braces_and_arrows(self) -> None:
        (block,) = parse('<!-- wp:x {"a":"}}","b":"-->"} /-->')
        assert block.attrs == {"a": "}}", "b": "-->"}

    def test_nesting_and_inner_content_markers(self) -> None:
        text = (
            '<!-- wp:group --><div class="g"><!-- wp:paragraph --><p>a</p><!-- /wp:paragraph -->'
            "\n\n<!-- wp:separator /--></div><!-- /wp:group -->"
        )
        (group,) = parse(text)
        assert [c.name for c in group.inner_blocks] == ["core/paragraph", "core/separator"]
        assert group.inner_content == ['<div class="g">', None, "\n\n", None, "</div>"]
        assert group.inner_html == '<div class="g">\n\n</div>'

    def test_whitespace_between_blocks_is_freeform(self) -> None:
        blocks = parse("<!-- wp:separator /-->\n\n<!-- wp:separator /-->")
        assert [b.name for b in blocks] == ["core/separator", None, "core/separator"]
        assert blocks[1].freeform
        assert blocks[1].inner_html == "\n\n"

    def test_plain_html_is_one_freeform_block(self) -> None:
        (block,) = parse("<p>Classic</p>")
        assert block.freeform
        assert block.inner_content == ["<p>Classic</p>"]

    def test_empty_text(self) -> None:
        assert parse("") == []
        assert serialize([]) == ""

    def test_unclosed_opener_degrades_to_text(self) -> None:
        text = "<!-- wp:paragraph -->\n<p>never closed</p>"
        (block,) = parse(text)
        assert block.freeform
        assert serialize([block]) == text

    def test_stray_closer_degrades_to_text(self) -> None:
        text = "before <!-- /wp:paragraph --> after"
        (block,) = parse(text)
        assert block.freeform

    def test_mismatched_closer_stays_inside_parent(self) -> None:
        text = "<!-- wp:group --><!-- wp:quote -->x<!-- /wp:group -->"
        (group,) = parse(text)
        assert group.name == "core/group"
        assert group.inner_blocks == []
        assert group.inner_html == "<!-- wp:quote -->x"

    def test_unclosed_inner_opener_becomes_parent_html(self) -> None:
        text = "<!-- wp:group -->a<!-- wp:quote -->b<!-- wp:separator /-->c<!-- /wp:group -->"
        (group,) = parse(text)
        assert [c.name for c in group.inner_blocks] == ["core/separator"]
        assert serialize([group]) == text

    def test_invalid_json_keeps_block_with_empty_attrs(self) -> None:
        text = "<!-- wp:paragraph {not json} -->\n<p>x</p>\n<!-- /wp:paragraph -->"
        (block,) = parse(text)
        assert block.name == "core/paragraph"
        assert block.attrs == {}
        assert serialize([block]) == text

    @pytest.mark.parametrize(
        "text",
        [
            "<!--wp:paragraph -->x",  # no space after <!--
            "<!-- wp:paragraph-->x",  # no space before -->
            "<!-- wp:Paragraph -->x<!-- /wp:Paragraph -->",  # upper case is not a name
            "<!-- wp:1x -->x<!-- /wp:1x -->",
            "<!-- wp:x {broken -->",
            "<!-- wp:",
            "<!--",
            "-->",
        ],
    )
    def test_malformed_comments_are_text(self, text: str) -> None:
        blocks = parse(text)
        assert all(b.freeform for b in blocks)
        assert serialize(blocks) == text


class TestRoundTrip:
    def test_mixed_post_round_trips_byte_for_byte(self) -> None:
        blocks = parse(MIXED_POST)
        assert serialize(blocks) == MIXED_POST
        assert names(blocks) == [
            "core/heading",
            "core/paragraph",
            "core/columns",
            "jetpack/contact-form",
            "core/latest-posts",
            None,
            "core/spacer",
        ]

    def test_nested_columns_structure(self) -> None:
        columns = parse(MIXED_POST)[4]
        assert columns.name == "core/columns"
        assert [c.name for c in columns.inner_blocks] == ["core/column", "core/column"]
        inner = columns.inner_blocks[1].inner_blocks[0]
        assert inner.name == "core/columns"
        assert inner.inner_blocks[0].inner_blocks[0].name == "core/paragraph"

    @pytest.mark.parametrize(
        "text",
        [
            '<!-- wp:x {"a":1}   /-->',
            '<!-- wp:x   {"a" : 1 ,  "b":[ 1, 2 ]}\n-->y<!-- /wp:x\t-->',
            "<!-- wp:x --><!-- /wp:x -->",
            "<!-- /wp:x /-->",
            "\r\n<!-- wp:p -->\r\n<p>crlf</p>\r\n<!-- /wp:p -->\r\n",
            "<!-- wp:x -->é ü 中文 😀<!-- /wp:x -->",
            '<!-- wp:x {"a":1} --><!-- /wp:x {"ignored":true} -->',
            "<!-- wp:a --><!-- wp:b --><!-- /wp:a --><!-- /wp:b -->",
            "<!-- wp:a -->" * 5 + "<!-- /wp:a -->" * 3,
        ],
    )
    def test_odd_inputs_round_trip(self, text: str) -> None:
        assert serialize(parse(text)) == text

    def test_random_fragments_round_trip(self) -> None:
        pieces = [
            "<!-- wp:paragraph -->",
            "<!-- /wp:paragraph -->",
            '<!-- wp:group {"a":1} -->',
            "<!-- /wp:group -->",
            "<!-- wp:x/y /-->",
            "<!-- wp:",
            "-->",
            "{",
            "}",
            " ",
            "\n",
            "<p>",
            "text",
            "<!--",
            "/-->",
        ]
        rng = random.Random(1234)
        for _ in range(400):
            text = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 25)))
            assert serialize(parse(text)) == text

    def test_unchanged_blocks_keep_original_comment_spacing(self) -> None:
        text = '<!-- wp:x   {"b" : 2}   -->y<!--   /wp:x   -->'
        assert serialize(parse(text)) == text


class TestChangedBlocks:
    def test_changed_attrs_reserialize_the_gutenberg_way(self) -> None:
        (block,) = parse('<!-- wp:heading {"level" : 3} -->\n<h3>x</h3>\n<!-- /wp:heading -->')
        block.attrs["level"] = 4
        assert (
            serialize([block])
            == '<!-- wp:heading {"level":4} -->\n<h3>x</h3>\n<!-- /wp:heading -->'
        )

    def test_removed_attrs_drop_the_json(self) -> None:
        (block,) = parse('<!-- wp:paragraph {"align":"center"} -->x<!-- /wp:paragraph -->')
        block.attrs.clear()
        assert serialize([block]) == "<!-- wp:paragraph -->x<!-- /wp:paragraph -->"

    def test_changed_void_block(self) -> None:
        (block,) = parse("<!-- wp:jetpack/thing  /-->")
        block.attrs["n"] = 1
        assert serialize([block]) == '<!-- wp:jetpack/thing {"n":1} /-->'

    def test_renamed_block_gets_new_comments(self) -> None:
        (block,) = parse("<!-- wp:paragraph -->x<!-- /wp:paragraph   -->")
        block.name = "core/verse"
        assert serialize([block]) == "<!-- wp:verse -->x<!-- /wp:verse -->"

    def test_new_block_serializes(self) -> None:
        block = Block(name="core/paragraph", inner_content=["\n<p>New</p>\n"])
        assert serialize([block]) == "<!-- wp:paragraph -->\n<p>New</p>\n<!-- /wp:paragraph -->"

    def test_new_void_block(self) -> None:
        assert (
            serialize([Block(name="acme/map", attrs={"z": 3})]) == '<!-- wp:acme/map {"z":3} /-->'
        )

    def test_inner_block_edit_reserializes_only_that_block(self) -> None:
        text = (
            '<!-- wp:group  {"x":1} --><div><!-- wp:paragraph {"a":1} -->'
            "<p>x</p><!-- /wp:paragraph --></div><!-- /wp:group -->"
        )
        (group,) = parse(text)
        group.inner_blocks[0].attrs["a"] = 2
        assert serialize([group]) == text.replace('{"a":1}', '{"a":2}')

    def test_serialize_attributes_escapes(self) -> None:
        attrs = {"t": 'a--b <i> & "q"', "u": "é", "f": 2.0, "g": 1.5}
        assert serialize_attributes(attrs) == (
            '{"t":"a\\u002d\\u002db \\u003ci\\u003e \\u0026 \\u0022q\\u0022","u":"é","f":2,"g":1.5}'
        )

    def test_serialized_attributes_parse_back(self) -> None:
        attrs = {"t": '<!-- -- --> & "x" \\ end', "n": None, "l": [True, False]}
        text = f"<!-- wp:x {serialize_attributes(attrs)} /-->"
        (block,) = parse(text)
        assert block.attrs == attrs


class TestWalk:
    def test_walk_depths_and_paths(self) -> None:
        blocks = parse(MIXED_POST)
        rows = [(depth, path, block.name) for depth, path, block in walk(blocks)]
        assert rows[0] == (0, (0,), "core/heading")
        assert (1, (4, 1), "core/column") in rows
        assert (3, (4, 1, 0, 0), "core/column") in rows
        assert (4, (4, 1, 0, 0, 0), "core/paragraph") in rows
        assert all(name is not None for _d, _p, name in rows)

    def test_path_addresses_the_block(self) -> None:
        blocks = parse(MIXED_POST)
        for _depth, path, block in walk(blocks):
            node = blocks[path[0]]
            for index in path[1:]:
                node = node.inner_blocks[index]
            assert node is block

    def test_walk_can_include_freeform(self) -> None:
        blocks = parse(MIXED_POST)
        freeform = [b for _d, _p, b in walk(blocks, include_freeform=True) if b.freeform]
        assert len(freeform) == 1
        assert "classic HTML" in freeform[0].inner_html


class TestDescribe:
    def test_button(self) -> None:
        (block,) = parse(
            '<!-- wp:button -->\n<div class="wp-block-button"><a class="wp-block-button__link">'
            "Book a session</a></div>\n<!-- /wp:button -->"
        )
        assert describe(block) == "Button block: Book a session"

    def test_plugin_block(self) -> None:
        (block,) = parse('<!-- wp:jetpack/contact-form {"to":"x"} /-->')
        assert describe(block) == "Contact form block (from a plugin)"

    def test_heading_level(self) -> None:
        (block,) = parse(
            '<!-- wp:heading {"level":3} --><h3>Hours &amp; prices</h3><!-- /wp:heading -->'
        )
        assert describe(block) == "Heading level 3 block: Hours & prices"

    def test_default_heading_level_is_two(self) -> None:
        (block,) = parse("<!-- wp:heading --><h2>Hi</h2><!-- /wp:heading -->")
        assert describe(block) == "Heading level 2 block: Hi"

    def test_image_uses_alt_then_reports_missing_alt(self) -> None:
        (with_alt,) = parse(
            '<!-- wp:image --><figure><img src="a" alt="Volunteers"/></figure><!-- /wp:image -->'
        )
        (without,) = parse(
            '<!-- wp:image --><figure><img src="a" alt=""/></figure><!-- /wp:image -->'
        )
        assert describe(with_alt) == "Image block: Volunteers"
        assert describe(without) == "Image block: no alt text"

    def test_columns_count(self) -> None:
        columns = parse(MIXED_POST)[4]
        assert describe(columns) == "Columns block: 2 columns"

    def test_separator_has_no_detail(self) -> None:
        assert describe(parse("<!-- wp:separator /-->")[0]) == "Separator block"

    def test_embed_uses_url(self) -> None:
        (block,) = parse('<!-- wp:embed {"url":"https://youtu.be/x"} /-->')
        assert describe(block) == "Embed block: https://youtu.be/x"

    def test_unknown_core_block_name_is_derived(self) -> None:
        assert describe(parse("<!-- wp:post-featured-image /-->")[0]) == "Post featured image block"

    def test_freeform(self) -> None:
        (block,) = parse("<p>Old <b>classic</b> text</p>")
        assert describe(block) == "Classic content: Old classic text"

    def test_first_words_limits_and_strips(self) -> None:
        (block,) = parse(
            "<!-- wp:paragraph --><p>One <em>two</em> three<script>no()</script> four five six"
            " seven eight nine ten</p><!-- /wp:paragraph -->"
        )
        assert first_words(block) == "One two three four five six seven eight"
        assert first_words(block, 2) == "One two"

    def test_first_words_include_inner_blocks(self) -> None:
        columns = parse(MIXED_POST)[4]
        assert first_words(columns, 4) == "Morning sessions run from"


def test_core_text_blocks() -> None:
    assert "core/paragraph" in CORE_TEXT_BLOCKS
    assert "core/list-item" in CORE_TEXT_BLOCKS
    assert "core/button" not in CORE_TEXT_BLOCKS
    assert len(CORE_TEXT_BLOCKS) == 10
