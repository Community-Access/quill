"""Unit tests for quill.core.emmet (Emmet-style abbreviation expansion, MVP)."""

from __future__ import annotations

import pytest

from quill.core.emmet import (
    EmmetSyntaxError,
    expand_css_abbreviation,
    expand_html_abbreviation,
    explain_abbreviation,
    extract_abbreviation_before_cursor,
)


class TestChildSiblingClimb:
    def test_simple_child(self) -> None:
        assert expand_html_abbreviation("div>p") == "<div>\n  <p></p>\n</div>"

    def test_sibling(self) -> None:
        assert expand_html_abbreviation("p+p") == "<p></p>\n<p></p>"

    def test_climb_up_one_level(self) -> None:
        result = expand_html_abbreviation("div>p^blockquote")
        assert result == "<div>\n  <p></p>\n</div>\n<blockquote></blockquote>"

    def test_climb_up_two_levels(self) -> None:
        result = expand_html_abbreviation("div>section>article^^footer")
        assert result == (
            "<div>\n  <section>\n    <article></article>\n  </section>\n</div>\n<footer></footer>"
        )

    def test_climb_past_root_is_a_no_op(self) -> None:
        result = expand_html_abbreviation("div^^^span")
        assert result == "<div></div>\n<span></span>"

    def test_deep_chain(self) -> None:
        # "a" picks up its default href attribute (see TestImplicitTagsAndAttrs).
        result = expand_html_abbreviation("span>b>c>d")
        assert result == ("<span>\n  <b>\n    <c>\n      <d></d>\n    </c>\n  </b>\n</span>")


class TestIdClassAttrsText:
    def test_id_and_multiple_classes(self) -> None:
        assert expand_html_abbreviation("div#main.box.active") == (
            '<div id="main" class="box active"></div>'
        )

    def test_attributes_with_quoted_and_bare_values(self) -> None:
        result = expand_html_abbreviation('a[href="#" target=_blank]')
        assert result == '<a href="#" target="_blank"></a>'

    def test_boolean_attribute(self) -> None:
        assert expand_html_abbreviation("input[disabled]") == '<input disabled type="text">'

    def test_text_content_renders_inline(self) -> None:
        assert expand_html_abbreviation("p{Hello world}") == "<p>Hello world</p>"

    def test_combined_id_class_attrs_text(self) -> None:
        result = expand_html_abbreviation('a#main.btn[href="#"]{Click me}')
        assert result == '<a id="main" class="btn" href="#">Click me</a>'


class TestImplicitTagsAndAttrs:
    def test_implicit_tag_inside_ul(self) -> None:
        assert expand_html_abbreviation("ul>.item") == '<ul>\n  <li class="item"></li>\n</ul>'

    def test_implicit_tag_inside_table(self) -> None:
        result = expand_html_abbreviation("table>tr>td*2")
        assert result == ("<table>\n  <tr>\n    <td></td>\n    <td></td>\n  </tr>\n</table>")

    def test_implicit_tag_defaults_to_div_at_top_level(self) -> None:
        assert expand_html_abbreviation(".card") == '<div class="card"></div>'

    def test_anchor_gets_default_href(self) -> None:
        assert expand_html_abbreviation("a") == '<a href=""></a>'

    def test_img_gets_default_src_and_alt(self) -> None:
        assert expand_html_abbreviation("img") == '<img src="" alt="">'

    def test_explicit_attr_overrides_default(self) -> None:
        assert expand_html_abbreviation('a[href="https://example.com"]') == (
            '<a href="https://example.com"></a>'
        )


class TestVoidTags:
    def test_void_tag_self_closes_without_children(self) -> None:
        assert expand_html_abbreviation("br") == "<br>"

    def test_void_tag_with_attrs(self) -> None:
        assert expand_html_abbreviation("hr.divider") == '<hr class="divider">'


class TestMultiplicationAndNumbering:
    def test_simple_multiplier(self) -> None:
        result = expand_html_abbreviation("li*3")
        assert result == "<li></li>\n<li></li>\n<li></li>"

    def test_numbering_with_dollar(self) -> None:
        result = expand_html_abbreviation("ul>li.item$*3")
        assert result == (
            '<ul>\n  <li class="item1"></li>\n  <li class="item2"></li>\n'
            '  <li class="item3"></li>\n</ul>'
        )

    def test_zero_padded_numbering(self) -> None:
        result = expand_html_abbreviation("li.item$$*3")
        assert result == (
            '<li class="item01"></li>\n<li class="item02"></li>\n<li class="item03"></li>'
        )

    def test_numbering_propagates_to_unmultiplied_descendant(self) -> None:
        # The span has no multiplier of its own, so its $ should resolve using
        # the nearest enclosing repetition (the li's), not a fixed "1".
        result = expand_html_abbreviation("ul>li*3>span.label$")
        assert result == (
            '<ul>\n  <li>\n    <span class="label1"></span>\n  </li>\n'
            '  <li>\n    <span class="label2"></span>\n  </li>\n'
            '  <li>\n    <span class="label3"></span>\n  </li>\n</ul>'
        )

    def test_nested_multiplier_does_not_inherit_ancestor_numbering(self) -> None:
        # The span has its OWN multiplier, so it gets its own 1..2 numbering
        # inside each li, rather than continuing the li's count.
        result = expand_html_abbreviation("ul>li*2>span.tag$*2")
        assert result == (
            "<ul>\n"
            '  <li>\n    <span class="tag1"></span>\n    <span class="tag2"></span>\n  </li>\n'
            '  <li>\n    <span class="tag1"></span>\n    <span class="tag2"></span>\n  </li>\n'
            "</ul>"
        )


class TestGrouping:
    def test_group_with_sibling_no_multiplier_is_transparent(self) -> None:
        result = expand_html_abbreviation("(header>h1)+(footer>small)")
        assert result == (
            "<header>\n  <h1></h1>\n</header>\n<footer>\n  <small></small>\n</footer>"
        )

    def test_multiplied_group_repeats_whole_sequence(self) -> None:
        result = expand_html_abbreviation("(div.row>span.a$+span.b$)*2")
        assert result == (
            '<div class="row">\n  <span class="a1"></span>\n  <span class="b1"></span>\n</div>\n'
            '<div class="row">\n  <span class="a2"></span>\n  <span class="b2"></span>\n</div>'
        )

    def test_chaining_after_group_is_rejected(self) -> None:
        with pytest.raises(EmmetSyntaxError, match="Chaining children"):
            expand_html_abbreviation("(a+b)>c")


class TestCannedSnippets:
    def test_html5_boilerplate(self) -> None:
        result = expand_html_abbreviation("!")
        assert result.startswith("<!DOCTYPE html>")
        assert "<html lang=" in result

    def test_a11y_boilerplate_has_skip_link_and_landmarks(self) -> None:
        result = expand_html_abbreviation("!a11y")
        assert "skip-link" in result
        assert "<main id=" in result

    def test_skiplink_snippet(self) -> None:
        result = expand_html_abbreviation("skiplink")
        assert "Skip to main content" in result

    def test_form_a11y_snippet_links_label_to_input(self) -> None:
        result = expand_html_abbreviation("form:a11y")
        assert 'for="field1"' in result
        assert 'id="field1"' in result

    def test_table_a11y_snippet_has_caption_and_scope(self) -> None:
        result = expand_html_abbreviation("table:a11y")
        assert "<caption>" in result
        assert 'scope="col"' in result


class TestSyntaxErrors:
    def test_empty_abbreviation(self) -> None:
        with pytest.raises(EmmetSyntaxError):
            expand_html_abbreviation("")

    def test_unterminated_attributes(self) -> None:
        with pytest.raises(EmmetSyntaxError):
            expand_html_abbreviation("div[")

    def test_unterminated_text(self) -> None:
        with pytest.raises(EmmetSyntaxError):
            expand_html_abbreviation("p{no closing brace")

    def test_stray_whitespace_is_rejected(self) -> None:
        with pytest.raises(EmmetSyntaxError):
            expand_html_abbreviation("div > p")

    def test_outer_whitespace_is_tolerated(self) -> None:
        assert expand_html_abbreviation("  div>p  ") == "<div>\n  <p></p>\n</div>"


class TestExtractAbbreviationBeforeCursor:
    def test_finds_token_immediately_before_cursor(self) -> None:
        text = "ul>li.item$*3"
        start, end = extract_abbreviation_before_cursor(text, len(text))
        assert (start, end) == (0, len(text))

    def test_stops_at_whitespace(self) -> None:
        text = "hello world ul>li*3"
        start, end = extract_abbreviation_before_cursor(text, len(text))
        assert text[start:end] == "ul>li*3"

    def test_stops_at_newline(self) -> None:
        text = "first line\nul>li*3"
        start, end = extract_abbreviation_before_cursor(text, len(text))
        assert text[start:end] == "ul>li*3"

    def test_nothing_before_cursor_returns_empty_span(self) -> None:
        assert extract_abbreviation_before_cursor("", 0) == (0, 0)

    def test_cursor_right_after_whitespace_returns_empty_span(self) -> None:
        text = "word "
        assert extract_abbreviation_before_cursor(text, len(text)) == (5, 5)


class TestExplainAbbreviation:
    def test_describes_tag_and_repetition(self) -> None:
        explanation = explain_abbreviation("ul>li.item$*3>a[href]{Item $}")
        assert "- ul" in explanation
        assert "li.item$" in explanation
        assert "repeated 3 times" in explanation
        assert "attributes: href" in explanation
        assert 'text: "Item $"' in explanation

    def test_describes_group(self) -> None:
        explanation = explain_abbreviation("(span.a+span.b)*2")
        assert "- group (repeated 2 times)" in explanation

    def test_snippet_gets_a_one_line_explanation(self) -> None:
        explanation = explain_abbreviation("!a11y")
        assert "built-in snippet" in explanation


class TestCssAbbreviations:
    def test_bare_abbreviation(self) -> None:
        assert expand_css_abbreviation("d:f") == "display: flex;"

    def test_unknown_bare_abbreviation_returns_none(self) -> None:
        assert expand_css_abbreviation("not-a-real-abbrev") is None

    def test_single_numeric_value(self) -> None:
        assert expand_css_abbreviation("m10") == "margin: 10px;"

    def test_zero_has_no_unit(self) -> None:
        assert expand_css_abbreviation("m0") == "margin: 0;"

    def test_multiple_numeric_values(self) -> None:
        assert expand_css_abbreviation("m10-20") == "margin: 10px 20px;"

    def test_negative_value_via_leading_sign(self) -> None:
        assert expand_css_abbreviation("mt-10") == "margin-top: -10px;"

    def test_negative_second_value_via_double_dash(self) -> None:
        assert expand_css_abbreviation("m10--20") == "margin: 10px -20px;"

    def test_unrecognized_property_prefix_returns_none(self) -> None:
        assert expand_css_abbreviation("xyz10") is None
