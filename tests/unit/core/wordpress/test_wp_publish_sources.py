"""Markdown, block markup, HTML and plain text, as the block markup WordPress is sent.

Send This Document to WordPress takes any of the four. Each must reach the site
as real blocks -- never raw Markdown, never a whole web page with its head --
and must not drift when it is opened again from the site and sent back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.wordpress import cross_site as xs
from quill.core.wordpress import fences
from quill.core.wordpress import html_blocks as hb
from quill.core.wordpress.blocks import parse, serialize

MARKDOWN = """# Spring News

Intro with *em*, **strong**, `x < y` and a [link](https://example.org/a?b=1&c=2).

## Schedule

- one
- two
  - nested a
  - nested b

1. first
2. second

> A quote

![A microphone](https://example.org/mic.png)

| Day | Time |
| --- | --- |
| Monday | 9 & 10 |

```
if a < b:
    print("&")
```

---

Last words.
"""

BLOCKS = (
    '<!-- wp:heading {"level":1} -->\n<h1 class="wp-block-heading">Block Title</h1>\n'
    "<!-- /wp:heading -->\n\n"
    "<!-- wp:paragraph -->\n<p>Kept <em>exactly</em> as written.</p>\n<!-- /wp:paragraph -->\n\n"
    '<!-- wp:jetpack/contact-form {"to":"a@example.org"} /-->'
)

PAGE = """<!DOCTYPE html>
<html><head><title>Head Title</title><style>p { color: red }</style></head>
<body><main>
<h1>Big &amp; Bold</h1>
<p>Intro <em>em</em> and <a href="https://e.org/?a=1&amp;b=2">a link</a><br>
next line</p>
<h3>Smaller</h3>
<ul><li>one<li>two<ul><li>nested</li></ul></li></ul>
<ol><li><p>para item</p></li></ol>
<blockquote><p>Quoted</p><cite>Someone</cite></blockquote>
<pre><code>if a &lt; b &amp;&amp; c:
    run()</code></pre>
<table><thead><tr><th>A</th><th>B</th></tr></thead>
<tbody><tr><td>1 &lt; 2</td><td>x</td></tr></tbody></table>
<figure><img src="https://e.org/pic.png" alt="A pic"><figcaption>Cap</figcaption></figure>
<p><a href="https://e.org/big.png"><img src="https://e.org/s.png" alt="Small"></a></p>
<hr>
loose <strong>text</strong>
<script>var ok = 1 < 2;</script>
<dl><dt>Term</dt><dd>Meaning</dd></dl>
<table><tr><td colspan="2">merged</td></tr></table>
</main></body></html>"""

TEXT = "First line\nsecond <line> & more\n\n\nNew paragraph with *stars* and # hash\n"


def names(markup: str) -> list[str | None]:
    return [b.name for b in parse(markup) if b.name is not None]


# --------------------------------------------------------------------------- #
# Which source a document is


@pytest.mark.parametrize(
    ("name", "text", "expected"),
    [
        ("notes.md", "# Hi", "markdown"),
        ("notes.markdown", "Hi", "markdown"),
        (None, "Hi", "markdown"),
        ("page.html", "<p>Hi</p>", "html"),
        ("page.htm", "<p>Hi</p>", "html"),
        ("notes.txt", "Hi *there*", "text"),
        ("readme", "Hi", "text"),
        ("post.html", BLOCKS, "blocks"),
        ("post.txt", BLOCKS, "blocks"),
        ("post.md", BLOCKS, "blocks"),
    ],
)
def test_source_kind(name: str | None, text: str, expected: str) -> None:
    assert xs.source_kind(Path(name) if name else None, text) == expected


# --------------------------------------------------------------------------- #
# Markdown: converted, never sent raw


def test_markdown_is_converted_to_blocks_not_sent_as_markdown() -> None:
    prepared = xs.prepare_document(MARKDOWN, Path("spring.md"), "spring")
    assert (prepared.title, prepared.text_format, prepared.source) == (
        "Spring News",
        "markdown",
        "markdown",
    )
    html = fences.convert_markdown(prepared.text).html
    assert "**" not in html and "](" not in html and "\n- " not in html and "```" not in html
    assert "Spring News" not in html
    assert names(html) == [
        "core/paragraph",
        "core/heading",
        "core/list",
        "core/list",
        "core/quote",
        "core/image",
        "core/table",
        "core/code",
        "core/separator",
        "core/paragraph",
    ]
    assert "<em>em</em>" in html and "<strong>strong</strong>" in html
    assert "<code>x &lt; y</code>" in html
    assert '<a href="https://example.org/a?b=1&amp;c=2">link</a>' in html
    nested = [b for b in parse(html) if b.name][2].inner_blocks[1]
    assert nested.inner_blocks[0].name == "core/list"  # the nested list sits in its item
    assert '<ol class="wp-block-list">' in html
    assert '<img src="https://example.org/mic.png" alt="A microphone"/>' in html
    assert "<td>9 &amp; 10</td>" in html
    assert "if a &lt; b:" in html and 'print("&amp;")' in html
    assert '<hr class="wp-block-separator has-alpha-channel-opacity"/>' in html


# --------------------------------------------------------------------------- #
# Block markup: unchanged


def test_block_markup_goes_unchanged_bar_its_title_heading() -> None:
    prepared = xs.prepare_document(BLOCKS, Path("post.html"), "post")
    assert prepared.title == "Block Title"
    assert prepared.text_format == "html"
    assert prepared.text == BLOCKS.split("<!-- /wp:heading -->\n\n", 1)[1]


def test_block_markup_without_an_opening_heading_is_byte_for_byte() -> None:
    body = BLOCKS.split("<!-- /wp:heading -->\n\n", 1)[1]
    prepared = xs.prepare_document(body, Path("post.txt"), "post")
    assert (prepared.title, prepared.text) == ("post", body)


# --------------------------------------------------------------------------- #
# HTML: converted, or kept in a Custom HTML block where blocks would lose meaning


def test_html_document_becomes_blocks() -> None:
    title, html = hb.html_title_and_blocks(PAGE, "fallback")
    assert title == "Big & Bold"
    assert "<head" not in html and "<style" not in html and "Head Title" not in html
    assert names(html) == [
        "core/paragraph",
        "core/heading",
        "core/list",
        "core/list",
        "core/quote",
        "core/code",
        "core/table",
        "core/image",
        "core/image",
        "core/separator",
        "core/paragraph",
        "core/html",
        "core/html",
        "core/html",
    ]
    blocks = [b for b in parse(html) if b.name]
    assert blocks[0].inner_html == (
        '\n<p>Intro <em>em</em> and <a href="https://e.org/?a=1&amp;b=2">a link</a>'
        "<br>next line</p>\n"
    )
    assert blocks[1].attrs == {"level": 3}
    assert blocks[2].inner_blocks[1].inner_blocks[0].name == "core/list"
    assert "<li>para item</li>" in html
    assert "<cite>Someone</cite>" in html
    assert "<code>if a &lt; b &amp;&amp; c:\n    run()</code>" in html
    assert "<thead><tr><th>A</th><th>B</th></tr></thead>" in html
    assert "<td>1 &lt; 2</td>" in html
    assert '<figcaption class="wp-element-caption">Cap</figcaption>' in html
    assert blocks[8].attrs == {"linkDestination": "custom"}
    assert '<a href="https://e.org/big.png"><img src="https://e.org/s.png"' in html
    assert "<script>var ok = 1 < 2;</script>" in html  # kept exactly, not escaped
    assert "<dl><dt>Term</dt><dd>Meaning</dd></dl>" in html
    assert '<td colspan="2">merged</td>' in html


def test_html_without_an_opening_heading_takes_the_page_title() -> None:
    page = "<html><head><title>Page Name</title></head><body><p>Hi</p><h2>Later</h2></body>"
    title, html = hb.html_title_and_blocks(page, "fallback")
    assert title == "Page Name"
    assert names(html) == ["core/paragraph", "core/heading"]
    assert hb.html_title_and_blocks("<p>Hi</p>", "fallback")[0] == "fallback"


def test_an_html_fragment_and_a_table_without_a_header() -> None:
    html = hb.html_to_blocks("<table><tr><td>a</td><td>b</td></tr></table>")
    assert "<thead>" not in html and "<tbody><tr><td>a</td><td>b</td></tr></tbody>" in html


# --------------------------------------------------------------------------- #
# Plain text


def test_plain_text_is_paragraphs_with_breaks_kept_and_markup_escaped() -> None:
    prepared = xs.prepare_document(TEXT, Path("notes.txt"), "notes")
    assert (prepared.title, prepared.text_format, prepared.source) == ("notes", "html", "text")
    assert prepared.text == (
        "<!-- wp:paragraph -->\n<p>First line<br>second &lt;line&gt; &amp; more</p>\n"
        "<!-- /wp:paragraph -->\n\n"
        "<!-- wp:paragraph -->\n<p>New paragraph with *stars* and # hash</p>\n"
        "<!-- /wp:paragraph -->"
    )


def test_plain_text_with_windows_line_endings() -> None:
    assert hb.text_to_blocks("a\r\nb\r\n\r\nc") == hb.text_to_blocks("a\nb\n\nc")


# --------------------------------------------------------------------------- #
# Every result parses back to itself, and reopening it does not drift


def _sent(source: str) -> str:
    prepared = {
        "markdown": xs.prepare_document(MARKDOWN, Path("a.md"), "a"),
        "blocks": xs.prepare_document(BLOCKS, Path("a.html"), "a"),
        "html": xs.prepare_document(PAGE, Path("a.html"), "a"),
        "text": xs.prepare_document(TEXT, Path("a.txt"), "a"),
    }[source]
    if prepared.text_format == "markdown":
        return fences.convert_markdown(prepared.text).html
    return prepared.text


@pytest.mark.parametrize("source", ["markdown", "blocks", "html", "text"])
def test_sent_markup_parses_back_exactly(source: str) -> None:
    sent = _sent(source)
    assert serialize(parse(sent)) == sent


@pytest.mark.parametrize("source", ["markdown", "blocks", "html", "text"])
def test_reopened_as_markdown_and_sent_again_does_not_drift(source: str) -> None:
    sent = _sent(source)
    markdown, islands = fences.post_to_markdown(sent)
    assert fences.convert_markdown(markdown, islands).html == sent


def test_send_a_folder_reads_each_source_as_itself(tmp_path: Path) -> None:
    from quill.core.wordpress import writing_archive as wa

    (tmp_path / "a-notes.txt").write_text(TEXT, encoding="utf-8")
    (tmp_path / "b-page.html").write_text(PAGE, encoding="utf-8")
    (tmp_path / "c-post.md").write_text(MARKDOWN, encoding="utf-8")
    (tmp_path / "d-blocks.html").write_text(BLOCKS, encoding="utf-8")
    files = {f.path.name: f for f in wa.read_folder(tmp_path, site_name="Radio")}
    assert files["a-notes.txt"].title == "a notes"
    assert files["a-notes.txt"].text == xs.prepare_document(TEXT, Path("x.txt"), "x").text
    assert files["b-page.html"].title == "Big & Bold"
    assert "<head" not in files["b-page.html"].text
    assert files["c-post.md"].text_format == "markdown"
    assert files["d-blocks.html"].title == "Block Title"

    class Api:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def post(self, _route: str, body: dict[str, object], **_kw: object) -> dict[str, object]:
            self.sent.append(str(body["content"]))
            return {"id": len(self.sent), "type": "post", "status": "draft"}

    api = Api()
    sent, failed = wa.send_folder(api, list(files.values()))  # type: ignore[arg-type]
    assert len(sent) == 4 and not failed
    for content in api.sent:
        assert names(content), content[:80]
        assert "**" not in content and "<html" not in content
