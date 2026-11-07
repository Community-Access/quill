"""Export as HTML: one accessible page, no scripts, notes out unless asked."""

from __future__ import annotations

import pytest

from quill.io.html_page import (
    embed_flag,
    has_remote_resources,
    normalise_language,
    pandoc_html_args,
    pandoc_version,
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
        "--mathml",
        "--metadata=title:Plan",
        "--metadata=lang:fr-CA",
        "--include-in-header=style.html",
    )
    assert "quill-note" not in prepare_for_pandoc(MD, False)
    assert prepare_for_pandoc(MD, True).count("<aside") == 1
    assert normalise_language("not a tag!") == "en"


@pytest.mark.parametrize(
    ("version_text", "flag"),
    [
        ("pandoc 3.1.9", "--embed-resources"),
        ("pandoc.exe 3.12.1", "--embed-resources"),
        ("pandoc 2.19.2", "--self-contained"),
        (None, None),
        ("pandoc", None),
    ],
)
def test_pictures_are_embedded_with_the_flag_this_pandoc_knows(version_text, flag) -> None:
    version = pandoc_version(version_text)
    assert embed_flag(version) == flag
    args = pandoc_html_args("P", "en", "s.html", resource_dir=r"C:\notes", version=version)
    assert args[5] == r"--resource-path=C:\notes"
    assert args[6:] == ((flag,) if flag else ())


def test_no_embedding_when_asked_not_to_and_no_resource_path_without_a_folder() -> None:
    args = pandoc_html_args("P", "en", "s.html", version=(3, 1), embed=False)
    assert not any(a.startswith(("--resource-path", "--embed", "--self")) for a in args)


def test_a_picture_from_the_web_is_never_downloaded_to_embed_it() -> None:
    assert has_remote_resources("![logo](https://example.com/a.png)")
    assert has_remote_resources('<img alt="x" src="//cdn.example.com/a.png">')
    assert not has_remote_resources("![logo](pics/a.png) and [site](https://example.com)")
