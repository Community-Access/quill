"""Tests for QUILL Longform rendering, summary, and teasers (PRD 16.4, 20.1)."""

from quill_social.services.longform import (
    Revision,
    make_summary,
    revision,
    to_semantic_html,
    to_teaser_thread,
)


def test_headings_and_paragraphs():
    html = to_semantic_html("# Title\n\nA paragraph here.")
    assert "<h1>Title</h1>" in html
    assert "<p>A paragraph here.</p>" in html


def test_unordered_and_ordered_lists():
    html = to_semantic_html("- one\n- two\n\n1. first\n2. second")
    assert "<ul><li>one</li><li>two</li></ul>" in html
    assert "<ol><li>first</li><li>second</li></ol>" in html


def test_links_and_images():
    html = to_semantic_html("See [the site](https://example.com) now.")
    assert '<a href="https://example.com">the site</a>' in html
    img = to_semantic_html("![a cat](cat.png)")
    assert '<img src="cat.png" alt="a cat" />' in img


def test_table_renders_semantic():
    md = "| Name | Age |\n| --- | --- |\n| Ada | 36 |"
    html = to_semantic_html(md)
    assert "<table>" in html
    assert "<th>Name</th>" in html
    assert "<td>Ada</td>" in html


def test_blockquote_and_code():
    html = to_semantic_html("> quoted text")
    assert "<blockquote><p>quoted text</p></blockquote>" in html
    fenced = to_semantic_html("```python\nprint(1)\n```")
    assert '<pre><code class="language-python">' in fenced
    assert "print(1)" in fenced


def test_html_is_escaped_no_injection():
    html = to_semantic_html("A <script>alert('x')</script> and & symbol.")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_image_alt_present_even_when_empty():
    html = to_semantic_html("![](x.png)")
    assert 'alt=""' in html


def test_inline_emphasis():
    html = to_semantic_html("This is **bold** and *italic* and `code`.")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert "<code>code</code>" in html


def test_make_summary_respects_limit():
    body = "word " * 200
    s = make_summary("# Head\n\n" + body, limit=50)
    assert len(s.text) <= 51  # limit plus a possible ellipsis
    assert s.canonical_url == ""


def test_make_summary_short_text_unchanged():
    s = make_summary("Just a short line.", limit=280)
    assert s.text == "Just a short line."
    assert s.post_text() == "Just a short line."


def test_summary_post_text_with_url():
    s = make_summary("hello", limit=280)
    s.canonical_url = "https://example.com/p"
    assert "https://example.com/p" in s.post_text()


def test_teaser_thread_uses_splitter():
    md = "# Big Idea\n\nHere is the opening line of the article that teases it.\n\n"
    md += "## Second Section\n\nAnd the second section begins right here."
    split = to_teaser_thread(md, char_limit=60)
    assert split.count >= 1
    joined = " ".join(split.texts())
    assert "Big Idea" in joined
    assert "Second Section" in joined
    for seg in split.segments:
        assert seg.length <= 60


def test_revision_chain():
    r1 = revision("v1 text", now=lambda: 1)
    assert r1.version == 1
    assert r1.prior_version is None
    r2 = revision("v2 text", r1, now=lambda: 2)
    assert r2.version == 2
    assert r2.prior_version == 1
    assert r2.changed
    r3 = revision("v2 text", r2, now=lambda: 3)  # unchanged
    assert not r3.changed


def test_revision_round_trip():
    r = revision("body", now=lambda: 5)
    assert Revision.from_dict(r.to_dict()).text == "body"
