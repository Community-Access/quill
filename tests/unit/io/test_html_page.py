"""Export as HTML: one accessible page, no scripts, notes out unless asked."""

from __future__ import annotations

from quill.io.html_page import (
    normalise_language,
    pandoc_html_args,
    prepare_for_pandoc,
    standalone_html,
)

MD = "# Plan\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n- [ ] open\n<!-- quill-note: hidden -->\n"


def test_a_whole_page_with_language_title_and_styles() -> None:
    page = standalone_html(MD, "markdown", "My <Plan>", lang="en_GB")
    assert page.startswith('<!doctype html>\n<html lang="en-GB">')
    assert "<title>My &lt;Plan&gt;</title>" in page
    assert "<style>" in page and "<script" not in page
    assert "<th>A</th>" in page
    assert '<input type="checkbox" disabled>' in page
    assert "hidden" not in page
    assert "<main>" in page


def test_notes_are_included_only_when_asked() -> None:
    page = standalone_html(MD, "markdown", "t", include_notes=True)
    assert '<aside class="quill-note" aria-label="Note"><p><strong>Note:</strong> hidden' in page


def test_plain_text_becomes_paragraphs_and_a_full_html_page_is_kept() -> None:
    assert "<p>one<br>two</p>\n<p>three</p>" in standalone_html("one\ntwo\n\nthree", "plain", "t")
    whole = "<html><body><p>x</p>\n<!-- quill-note: n -->\n</body></html>"
    assert standalone_html(whole, "html", "t") == "<html><body><p>x</p>\n</body></html>"


def test_pandoc_gets_a_standalone_page_and_clean_input() -> None:
    args = pandoc_html_args("Plan", "fr_CA", "style.html")
    assert args == (
        "--standalone",
        "--metadata=title:Plan",
        "--metadata=lang:fr-CA",
        "--include-in-header=style.html",
    )
    assert "quill-note" not in prepare_for_pandoc(MD, False)
    assert prepare_for_pandoc(MD, True).count("<aside") == 1
    assert normalise_language("not a tag!") == "en"
