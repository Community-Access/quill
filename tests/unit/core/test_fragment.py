"""Tests for the Fragment spine shared by Look Up (#897), Clip Library (#895),
and Email hand-off (#900)."""

from __future__ import annotations

from quill.core.fragment import Fragment, FragmentFormat, render_fragment


def test_render_markdown_is_verbatim() -> None:
    frag = Fragment(markup="**bold** text")
    assert render_fragment(frag, FragmentFormat.MARKDOWN) == "**bold** text"


def test_render_text_strips_markup() -> None:
    frag = Fragment(markup="**bold** text")
    assert render_fragment(frag, FragmentFormat.TEXT) == "bold text"


def test_render_html_wraps_as_a_snippet_not_a_full_document() -> None:
    frag = Fragment(markup="**bold** text")
    html = render_fragment(frag, FragmentFormat.HTML)
    assert "<strong>" in html or "<b>" in html
    assert "<!doctype html>" not in html.lower()


def test_citation_appended_in_each_format_when_source_url_present() -> None:
    frag = Fragment(
        markup="Ada Lovelace was a mathematician.",
        title="Ada Lovelace",
        source="Wikipedia",
        source_url="https://en.wikipedia.org/wiki/Ada_Lovelace",
    )
    text = render_fragment(frag, FragmentFormat.TEXT)
    markdown = render_fragment(frag, FragmentFormat.MARKDOWN)
    html = render_fragment(frag, FragmentFormat.HTML)
    assert "en.wikipedia.org" in text
    assert "[Source: Wikipedia](https://en.wikipedia.org/wiki/Ada_Lovelace)" in markdown
    assert 'href="https://en.wikipedia.org/wiki/Ada_Lovelace"' in html


def test_no_citation_when_source_url_absent() -> None:
    frag = Fragment(markup="plain text")
    assert "Source:" not in render_fragment(frag, FragmentFormat.TEXT)
    assert "Source:" not in render_fragment(frag, FragmentFormat.MARKDOWN)
    assert "Source:" not in render_fragment(frag, FragmentFormat.HTML)


def test_fragment_defaults() -> None:
    frag = Fragment(markup="x")
    assert frag.title == ""
    assert frag.source == ""
    assert frag.source_url == ""
    assert frag.kind == "text"
    assert frag.created_at == ""
