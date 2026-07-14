from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.document import Document
from quill.io.export import (
    format_label_for_path,
    markdown_to_html,
    markdown_to_plain_text,
    write_document_as,
    write_html_document,
    write_plain_text_document,
)


# --------------------------------------------------------------------------- #
# markdown_to_plain_text
# --------------------------------------------------------------------------- #
def test_plain_strips_heading_and_emphasis() -> None:
    md = "# Title\n\nThis is **bold** and *italic* and `code`."
    assert markdown_to_plain_text(md) == "Title\n\nThis is bold and italic and code."


def test_plain_strips_links_keeping_text() -> None:
    assert markdown_to_plain_text("See [the site](https://example.com).") == "See the site."


# --------------------------------------------------------------------------- #
# markdown_to_plain_text link_style
# --------------------------------------------------------------------------- #
def test_link_style_text_url_keeps_both() -> None:
    out = markdown_to_plain_text("See [the site](https://example.com).", "text_url")
    assert out == "See the site (https://example.com)."


def test_link_style_url_only() -> None:
    out = markdown_to_plain_text("See [the site](https://example.com).", "url")
    assert out == "See https://example.com."


def test_link_style_markdown_keeps_markup_verbatim() -> None:
    out = markdown_to_plain_text("See [the site](https://example.com).", "markdown")
    assert out == "See [the site](https://example.com)."


def test_link_style_text_url_does_not_mangle_underscore_urls() -> None:
    # The URL must survive emphasis stripping even though it contains underscores.
    out = markdown_to_plain_text("[doc](https://x.com/a_b_c_d)", "text_url")
    assert out == "doc (https://x.com/a_b_c_d)"


def test_link_style_text_url_strips_emphasis_from_label() -> None:
    out = markdown_to_plain_text("[**Docs**](https://x.com)", "text_url")
    assert out == "Docs (https://x.com)"


def test_link_style_text_url_drops_title_keeping_url() -> None:
    out = markdown_to_plain_text('[doc](https://x.com "A Title")', "text_url")
    assert out == "doc (https://x.com)"


def test_link_style_text_url_unwraps_angle_bracket_url() -> None:
    out = markdown_to_plain_text("[doc](<https://x.com>)", "text_url")
    assert out == "doc (https://x.com)"


def test_link_style_text_url_collapses_when_label_equals_url() -> None:
    out = markdown_to_plain_text("[https://x.com](https://x.com)", "text_url")
    assert out == "https://x.com"


def test_link_style_image_text_url() -> None:
    out = markdown_to_plain_text("![a cat](cat.png)", "text_url")
    assert out == "a cat (cat.png)"


def test_link_style_image_empty_alt_text_url_uses_url() -> None:
    out = markdown_to_plain_text("![](cat.png)", "text_url")
    assert out == "cat.png"


def test_link_style_default_is_text_only() -> None:
    assert markdown_to_plain_text("[the site](https://example.com)") == "the site"


def test_link_style_text_url_preserves_code_span_links() -> None:
    out = markdown_to_plain_text("`[x](y)` and [a](b)", "text_url")
    assert out == "[x](y) and a (b)"


def test_plain_unwraps_images_before_links() -> None:
    assert markdown_to_plain_text("![a cat](cat.png)") == "a cat"


def test_plain_preserves_inline_code_contents() -> None:
    # Markup inside a code span must survive untouched.
    assert markdown_to_plain_text("Use `**not bold**` here.") == "Use **not bold** here."


def test_plain_leaves_snake_case_untouched() -> None:
    assert markdown_to_plain_text("call foo_bar_baz and snake_case now") == (
        "call foo_bar_baz and snake_case now"
    )


def test_plain_strips_underscore_emphasis() -> None:
    assert markdown_to_plain_text("_italic_ and __bold__ words") == "italic and bold words"


def test_plain_normalizes_bullets_and_keeps_numbers() -> None:
    md = "* one\n+ two\n- three\n\n1. first\n2. second"
    assert markdown_to_plain_text(md) == "- one\n- two\n- three\n\n1. first\n2. second"


def test_plain_drops_blockquote_marker() -> None:
    assert markdown_to_plain_text("> quoted line") == "quoted line"


def test_plain_horizontal_rule_becomes_blank() -> None:
    assert markdown_to_plain_text("a\n\n---\n\nb") == "a\n\nb"


def test_plain_fenced_code_is_verbatim() -> None:
    md = "```\n# not a heading\n**kept**\n```"
    assert markdown_to_plain_text(md) == "# not a heading\n**kept**"


def test_plain_collapses_excess_blank_lines() -> None:
    assert markdown_to_plain_text("a\n\n\n\nb") == "a\n\nb"


# --------------------------------------------------------------------------- #
# markdown_to_html
# --------------------------------------------------------------------------- #
def test_html_is_standalone_without_refresh_meta() -> None:
    out = markdown_to_html("# Hi\n\nText", "My Doc")
    assert out.startswith("<!doctype html>")
    assert "<title>My Doc</title>" in out
    assert 'charset="utf-8"' in out
    assert "http-equiv" not in out  # no live-preview auto refresh in a saved file
    assert "<h1" in out and "Hi" in out


def test_html_escapes_title() -> None:
    assert "<title>A &amp; B</title>" in markdown_to_html("x", "A & B")


def test_html_renders_run_span_as_styled_span() -> None:
    out = markdown_to_html('[Hi]{font-family="Arial" font-size="14" color="#C00000"}', "Doc")
    assert "font-family: Arial" in out
    assert "font-size: 14pt" in out
    assert "color: #C00000" in out
    assert "<span style=" in out


def test_html_renders_alignment_div() -> None:
    out = markdown_to_html('::: {align="center"}\nCentered.\n:::', "Doc")
    assert '<div style="text-align: center">' in out
    assert "Centered." in out


def test_plain_strips_run_span_and_alignment() -> None:
    md = '[Hi]{font-family="Arial"} there\n::: {align="center"}\nCentered.\n:::'
    assert markdown_to_plain_text(md) == "Hi there\nCentered."


def test_html_renders_strike_super_sub() -> None:
    out = markdown_to_html("[a]{strike} [b]{superscript} [c]{subscript}", "Doc")
    assert "line-through" in out
    assert "vertical-align: super" in out
    assert "vertical-align: sub" in out


def test_html_renders_line_spacing_and_named_style() -> None:
    out = markdown_to_html('::: {line-spacing="2" pstyle="quote"}\nx\n:::', "Doc")
    assert "line-height: 2" in out
    assert "font-style: italic" in out  # quote named style


def test_html_renders_page_break() -> None:
    out = markdown_to_html("a\n::: pagebreak\nb", "Doc")
    assert "page-break-after: always" in out


def test_plain_strips_page_break() -> None:
    assert markdown_to_plain_text("a\n::: pagebreak\nb") == "a\nb"


# --------------------------------------------------------------------------- #
# writers + dispatcher
# --------------------------------------------------------------------------- #
def _doc(text: str) -> Document:
    return Document(text=text, path=None, modified=True, encoding="utf-8", line_ending="\n")


def test_write_plain_text_strips_and_marks_saved(tmp_path: Path) -> None:
    doc = _doc("# H\n\n**b**")
    target = tmp_path / "out.txt"
    result = write_plain_text_document(doc, target)
    assert result == target
    assert target.read_text(encoding="utf-8") == "H\n\nb"
    assert doc.path == target and doc.modified is False


def test_write_plain_text_honors_link_style(tmp_path: Path) -> None:
    doc = _doc("[site](https://example.com)")
    target = tmp_path / "out.txt"
    write_plain_text_document(doc, target, link_style="text_url")
    assert target.read_text(encoding="utf-8") == "site (https://example.com)"


def test_write_document_as_txt_is_verbatim_regardless_of_link_style(tmp_path: Path) -> None:
    # A normal save to .txt round-trips the source verbatim; Markdown stripping
    # (and link-style handling) only happens via the explicit "Save as plain
    # text" command, which calls write_plain_text_document directly (#649).
    doc = _doc("[site](https://example.com)")
    target = tmp_path / "out.txt"
    write_document_as(doc, target, plain_text_link_style="url")
    assert target.read_text(encoding="utf-8") == "[site](https://example.com)"


def test_write_html_document_writes_html(tmp_path: Path) -> None:
    doc = _doc("# H")
    target = tmp_path / "out.html"
    write_html_document(doc, target)
    body = target.read_text(encoding="utf-8")
    assert body.startswith("<!doctype html>")
    assert doc.modified is False


@pytest.mark.parametrize(
    "name,expected_marker",
    [
        ("a.rtf", "{\\rtf"),
        ("a.html", "<!doctype html>"),
        ("a.htm", "<!doctype html>"),
        ("a.xhtml", "<!doctype html>"),
        ("a.txt", "Bold"),
        ("a.text", "Bold"),
        ("a.md", "**Bold**"),
        ("a.markdown", "**Bold**"),
        ("a.weird", "**Bold**"),
    ],
)
def test_dispatch_by_extension(tmp_path: Path, name: str, expected_marker: str) -> None:
    doc = _doc("**Bold**")
    target = tmp_path / name
    write_document_as(doc, target)
    assert expected_marker in target.read_text(encoding="utf-8", errors="replace")


def test_dispatch_txt_writes_verbatim(tmp_path: Path) -> None:
    # Normal save to .txt no longer strips Markup; it writes the buffer verbatim
    # so opening then saving a plain-text file does not mangle it (#649).
    doc = _doc("**Bold**")
    target = tmp_path / "a.txt"
    write_document_as(doc, target)
    assert target.read_text(encoding="utf-8") == "**Bold**"


def test_dispatch_md_is_verbatim(tmp_path: Path) -> None:
    doc = _doc("# Title\n\n**Bold**")
    target = tmp_path / "a.md"
    write_document_as(doc, target)
    assert target.read_text(encoding="utf-8") == "# Title\n\n**Bold**"


def test_line_ending_preserved_on_export(tmp_path: Path) -> None:
    doc = Document(text="a\n\nb", path=None, modified=True, encoding="utf-8", line_ending="\r\n")
    target = tmp_path / "a.txt"
    write_plain_text_document(doc, target)
    assert target.read_bytes() == b"a\r\n\r\nb"


def test_write_requires_path() -> None:
    with pytest.raises(ValueError):
        write_document_as(_doc("x"), None)


def test_write_document_as_refuses_export_only_suffixes(tmp_path: Path) -> None:
    from quill.io.export import UnsupportedSaveFormatError

    doc = _doc("# Title\nbody")
    for name in (
        "a.pdf",
        "a.epub",
        "a.odt",
        "a.doc",
        "a.ppt",
        "a.pptx",
        "a.xls",
        "a.xlsx",
        "a.pages",
        "a.sqlite",
        "a.db",
    ):
        with pytest.raises(UnsupportedSaveFormatError):
            write_document_as(doc, tmp_path / name)
        # The refusal must be total: nothing written, document state untouched.
        assert not (tmp_path / name).exists()
        assert doc.modified is True
        assert doc.path is None


def test_write_document_as_still_allows_brf_and_unknown_text(tmp_path: Path) -> None:
    doc = _doc("hello")
    write_document_as(doc, tmp_path / "a.brf")
    doc2 = _doc("hello")
    write_document_as(doc2, tmp_path / "a.log")
    assert (tmp_path / "a.brf").read_text(encoding="utf-8") == "hello"
    assert (tmp_path / "a.log").read_text(encoding="utf-8") == "hello"


def test_write_docx_marks_saved(tmp_path: Path) -> None:
    doc = _doc("line one\nline two")
    target = tmp_path / "out.docx"
    result = write_document_as(doc, target)
    assert result == target
    assert doc.path == target
    assert doc.modified is False


def test_write_docx_keeps_line_breaks(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")

    doc = _doc("one\ntwo\nthree")
    target = tmp_path / "breaks.docx"
    write_document_as(doc, target)
    paragraphs = [p.text for p in docx.Document(str(target)).paragraphs]
    assert paragraphs == ["one", "two", "three"]


def test_write_docx_engine_native_forced(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    from quill.io.export import write_docx_document

    doc = _doc("one\ntwo")
    target = tmp_path / "native.docx"
    write_docx_document(doc, target, engine="native")
    paragraphs = [p.text for p in docx.Document(str(target)).paragraphs]
    assert paragraphs == ["one", "two"]
    assert doc.path == target and doc.modified is False


def test_write_docx_engine_pandoc_forced(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    from quill.core.external_tools import get_external_tool_status
    from quill.io.export import write_docx_document

    if not get_external_tool_status("pandoc").installed:
        pytest.skip("pandoc not installed")
    doc = _doc("alpha\nbeta")
    target = tmp_path / "pandoc.docx"
    write_docx_document(doc, target, engine="pandoc")
    text = "\n".join(p.text for p in docx.Document(str(target)).paragraphs)
    assert "alpha" in text and "beta" in text
    assert doc.path == target and doc.modified is False


def test_write_docx_engine_invalid_rejected(tmp_path: Path) -> None:
    from quill.io.export import write_docx_document

    with pytest.raises(ValueError, match="engine"):
        write_docx_document(_doc("x"), tmp_path / "a.docx", engine="bogus")


def test_write_document_as_forwards_docx_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.io.export as export_mod

    recorded: list[str] = []

    def _fake(document: Document, path: Path | None = None, *, engine: str = "auto") -> Path:
        recorded.append(engine)
        return Path(path or "")

    monkeypatch.setattr(export_mod, "write_docx_document", _fake)
    write_document_as(_doc("x"), tmp_path / "a.docx", docx_engine="pandoc")
    assert recorded == ["pandoc"]


def test_format_label_for_path() -> None:
    assert format_label_for_path(Path("a.rtf")) == "rich text"
    assert format_label_for_path(Path("a.html")) == "HTML"
    assert format_label_for_path(Path("a.txt")) == "plain text"
    assert format_label_for_path(Path("a.md")) == "Markdown"
    assert format_label_for_path(Path("a.unknown")) == "Markdown"


def test_export_module_is_wx_free() -> None:
    import quill.io.export as export_module

    source = Path(export_module.__file__).read_text(encoding="utf-8")
    assert "import wx" not in source


# --------------------------------------------------------------------------- #
# Word (.docx) export (#204)
# --------------------------------------------------------------------------- #


def test_format_label_for_docx_is_word() -> None:
    assert format_label_for_path(Path("report.docx")) == "Word"


def _pandoc_available() -> bool:
    from quill.core.external_tools import get_external_tool_status

    return get_external_tool_status("pandoc").installed


@pytest.mark.skipif(not _pandoc_available(), reason="Pandoc not installed")
def test_write_document_as_docx_produces_a_word_file(tmp_path: Path) -> None:
    import zipfile

    doc = Document(text="# Title\n\nSome **bold** text.\n\n- one\n- two\n")
    target = tmp_path / "out.docx"
    result = write_document_as(doc, target)
    assert result == target
    assert target.exists() and target.stat().st_size > 0
    # A .docx is an OOXML zip; the body lives in word/document.xml.
    with zipfile.ZipFile(target) as archive:
        assert "word/document.xml" in archive.namelist()


# --------------------------------------------------------------------------- #
# write_document_as: .txt saves verbatim, not through Markdown stripping (#649)
# --------------------------------------------------------------------------- #
def test_write_document_as_txt_preserves_blank_lines(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    # Three+ consecutive line breaks and a Markdown-looking line must survive a
    # normal save to .txt unchanged (the bug collapsed them and stripped markup).
    text = "para one\n\n\n\npara two\n# not a heading here\n"
    document = Document(text=text, path=target, line_ending="\n", encoding="utf-8")

    write_document_as(document, target)

    assert target.read_bytes() == text.encode("utf-8")


def test_write_document_as_txt_preserves_crlf(tmp_path: Path) -> None:
    target = tmp_path / "crlf.txt"
    document = Document(text="a\nb\n\n\nc\n", path=target, line_ending="\r\n", encoding="utf-8")

    write_document_as(document, target)

    assert target.read_bytes() == b"a\r\nb\r\n\r\n\r\nc\r\n"
