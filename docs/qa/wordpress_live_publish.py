"""Tests 119 to 122 of the live WordPress run: the four sources, published.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`. Each test takes one kind of document --
Markdown, block markup, HTML, plain text -- through the same core functions
Send This Document and Publish call (``cross_site.prepare_document``, then
``fences.convert_markdown`` for Markdown, then ``site.create_item`` and
``site.update_item``), as a **post and a page**, and then:

1. reads it back in ``context=edit`` and checks the raw content is exactly what
   was sent (WordPress kept the blocks; nothing was re-cut);
2. publishes it, fetches the public page, and checks the rendered HTML has the
   structure the source had: headings, nested lists, the table, the code, the
   quote, the separator, the picture, the link, the emphasis, escaped text;
3. opens it again as QUILL would (as Markdown, ``fences.post_to_markdown``),
   turns that back into blocks, updates the item, and checks nothing drifted.

Everything is titled "QUILL live test" and trashed through ``ctx.later``; the
picture the sources show is uploaded once and deleted afterwards.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA = "Saving and publishing (5.3, 5.4, 9.2)"


def register(harness: Any) -> None:
    """Put tests 119 to 122 on the harness's list."""
    global H
    H = harness
    for ref, name, fn in _TESTS:
        harness.check(AREA, ref, name, who=harness.EDITOR, writes=True)(fn)


# =========================================================================== #
# The four documents, each showing the same picture and link


def _picture(ctx: Any) -> str:
    """The address of one picture on the site, uploaded once for all four tests."""
    if "publish_picture" not in ctx.state:
        from quill.core.wordpress import site_media as sm

        made = sm.upload_media(
            ctx.api(H.EDITOR),
            "quill-live-test-publish.png",
            H.tiny_png(320, 200),
            "image/png",
            title=ctx.title("publish picture"),
            alt_text=f"{H.TAG} picture",
        )
        ctx.later(f"delete media {made.id}", lambda: sm.delete_media(ctx.api(H.ADMIN), made.id))
        ctx.state["publish_picture"] = made.source_url
    return str(ctx.state["publish_picture"])


def _markdown(title: str, picture: str) -> tuple[str, str]:
    return "live.md", (
        f"# {title}\n\n"
        "Opening with *emphasis*, **strength**, `a < b` and a "
        "[link](https://wordpress.org/?a=1&b=2).\n\n"
        "## A heading\n\n"
        "- one\n- two\n  - nested\n\n"
        "1. first\n2. second\n\n"
        "> Quoted words\n\n"
        f"![{H.TAG} picture]({picture})\n\n"
        "| Day | Time |\n| --- | --- |\n| Monday | 9 & 10 |\n\n"
        "```\nif a < b:\n    print('&')\n```\n\n"
        "---\n\nClosing words.\n"
    )


def _blocks(title: str, picture: str) -> tuple[str, str]:
    return "live.html", (
        f'<!-- wp:heading {{"level":1}} -->\n<h1 class="wp-block-heading">{title}</h1>\n'
        "<!-- /wp:heading -->\n\n"
        "<!-- wp:paragraph -->\n<p>Opening with <em>emphasis</em> and a "
        '<a href="https://wordpress.org/?a=1&amp;b=2">link</a>.</p>\n<!-- /wp:paragraph -->\n\n'
        '<!-- wp:heading -->\n<h2 class="wp-block-heading">A heading</h2>\n'
        "<!-- /wp:heading -->\n\n"
        '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>one'
        '<!-- wp:list -->\n<ul class="wp-block-list"><!-- wp:list-item -->\n<li>nested</li>\n'
        "<!-- /wp:list-item --></ul>\n<!-- /wp:list --></li>\n<!-- /wp:list-item --></ul>\n"
        "<!-- /wp:list -->\n\n"
        '<!-- wp:quote -->\n<blockquote class="wp-block-quote"><!-- wp:paragraph -->\n'
        "<p>Quoted words</p>\n<!-- /wp:paragraph --></blockquote>\n<!-- /wp:quote -->\n\n"
        '<!-- wp:image -->\n<figure class="wp-block-image">'
        f'<img src="{picture}" alt="{H.TAG} picture"/></figure>\n<!-- /wp:image -->\n\n'
        '<!-- wp:table -->\n<figure class="wp-block-table"><table class="has-fixed-layout">'
        "<thead><tr><th>Day</th><th>Time</th></tr></thead><tbody><tr><td>Monday</td>"
        "<td>9 &amp; 10</td></tr></tbody></table></figure>\n<!-- /wp:table -->\n\n"
        '<!-- wp:code -->\n<pre class="wp-block-code"><code>if a &lt; b:\n'
        "    print('&amp;')</code></pre>\n<!-- /wp:code -->\n\n"
        '<!-- wp:separator -->\n<hr class="wp-block-separator has-alpha-channel-opacity"/>\n'
        "<!-- /wp:separator -->"
    )


def _html(title: str, picture: str) -> tuple[str, str]:
    return "live.html", (
        "<!DOCTYPE html><html><head><title>Not the title</title>"
        "<style>p { color: red }</style></head><body><main>"
        f"<h1>{title}</h1>"
        "<p>Opening with <em>emphasis</em>, <strong>strength</strong>, <code>a &lt; b</code> "
        'and a <a href="https://wordpress.org/?a=1&amp;b=2">link</a>.</p>'
        "<h2>A heading</h2>"
        "<ul><li>one</li><li>two<ul><li>nested</li></ul></li></ul>"
        "<ol><li>first</li><li>second</li></ol>"
        "<blockquote><p>Quoted words</p></blockquote>"
        f'<figure><img src="{picture}" alt="{H.TAG} picture"><figcaption>A caption</figcaption>'
        "</figure>"
        "<table><thead><tr><th>Day</th><th>Time</th></tr></thead>"
        "<tbody><tr><td>Monday</td><td>9 &amp; 10</td></tr></tbody></table>"
        "<pre><code>if a &lt; b:\n    print('&amp;')</code></pre>"
        "<hr><dl><dt>Term</dt><dd>Kept as Custom HTML</dd></dl>"
        "</main></body></html>"
    )


def _text(_title: str, _picture: str) -> tuple[str, str]:
    return "live.txt", (
        "Opening line\nsecond line of the same paragraph\n\n"
        "Special characters: 5 < 6 & 7 > 3, and *not emphasis* or # not a heading.\n"
    )


#: For each source: what the rendered page must contain, as regular expressions.
#: A paragraph is ``<p[^>]*>``: WordPress 6.9 and later render every core/paragraph
#: as ``<p class="wp-block-paragraph">`` (seen live on 7.1.4), whatever was saved.
_RENDERED: dict[str, tuple[str, ...]] = {
    "markdown": (
        r"<em>emphasis</em>",
        r"<strong>strength</strong>",
        r"<code>a &lt; b</code>",
        r'<a href="https://wordpress\.org/\?a=1&(amp;|#038;)b=2"',
        r"<h2[^>]*>A heading</h2>",
        r"<li>two\s*<ul[^>]*>\s*<li>nested</li>",
        r"<ol[^>]*>\s*<li>first</li>",
        r"<blockquote[^>]*>\s*<p[^>]*>Quoted words</p>",
        r"<img [^>]*alt=\"QUILL live test picture\"",
        r"<td>9 &(amp;|#038;) 10</td>",
        r"<pre[^>]*><code>if a &lt; b:",
        r"<hr[^>]*wp-block-separator",
    ),
    "blocks": (
        r"<em>emphasis</em>",
        r"<h2[^>]*>A heading</h2>",
        r"<li>one\s*<ul[^>]*>\s*<li>nested</li>",
        r"<blockquote[^>]*>\s*<p[^>]*>Quoted words</p>",
        r"<img [^>]*alt=\"QUILL live test picture\"",
        r"<td>9 &(amp;|#038;) 10</td>",
        r"<pre[^>]*><code>if a &lt; b:",
        r"<hr[^>]*wp-block-separator",
    ),
    "html": (
        r"<em>emphasis</em>",
        r"<strong>strength</strong>",
        r"<h2[^>]*>A heading</h2>",
        r"<li>two\s*<ul[^>]*>\s*<li>nested</li>",
        r"<blockquote[^>]*>\s*<p[^>]*>Quoted words</p>",
        r"<figcaption[^>]*>A caption</figcaption>",
        r"<td>9 &(amp;|#038;) 10</td>",
        r"<pre[^>]*><code>if a &lt; b:",
        r"<hr[^>]*wp-block-separator",
        r"<dl><dt>Term</dt><dd>Kept as Custom HTML</dd></dl>",
    ),
    "text": (
        r"<p[^>]*>Opening line<br\s*/?>\s*second line of the same paragraph</p>",
        r"5 &lt; 6 &(amp;|#038;) 7 &gt; 3",
        r"\*not emphasis\* or # not a heading",
    ),
}

#: For each source: the blocks the raw content must hold, in order.
_BLOCKS: dict[str, tuple[str, ...]] = {
    "markdown": (
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
    ),
    "blocks": (
        "core/paragraph",
        "core/heading",
        "core/list",
        "core/quote",
        "core/image",
        "core/table",
        "core/code",
        "core/separator",
    ),
    "html": (
        "core/paragraph",
        "core/heading",
        "core/list",
        "core/list",
        "core/quote",
        "core/image",
        "core/table",
        "core/code",
        "core/separator",
        "core/html",
    ),
    "text": ("core/paragraph", "core/paragraph"),
}

_SOURCES = {"markdown": _markdown, "blocks": _blocks, "html": _html, "text": _text}


# =========================================================================== #
# One source, as a post and a page


def _publish_source(ctx: Any, source: str) -> str:
    from quill.core.wordpress import cross_site as xs
    from quill.core.wordpress import fences
    from quill.core.wordpress import site as wp
    from quill.core.wordpress.blocks import parse

    api = ctx.api(H.EDITOR)
    title = ctx.title(f"publish {source}")
    name, text = _SOURCES[source](title, _picture(ctx))
    # Plain text has no heading: like Send This Document, its title is the file's name.
    prepared = xs.prepare_document(text, Path(name), title)
    H.expect(prepared.source == source, f"read as {prepared.source}, not {source}")
    H.expect(prepared.title == title, f"title is {prepared.title!r}")
    content = (
        fences.convert_markdown(prepared.text).html
        if prepared.text_format == "markdown"
        else prepared.text
    )
    names = tuple(b.name for b in parse(content) if b.name)
    H.expect(names == _BLOCKS[source], f"blocks sent: {names}")
    said: list[str] = []
    for kind in ("post", "page"):
        made = wp.create_item(api, wp.Item(0, kind, title, content, "draft"))
        ctx.later(
            f"trash {kind} {made.id}",
            lambda kind=kind, item_id=made.id: wp.trash_item(api, kind, item_id),
        )
        H.expect(made.status == "draft" and made.kind == kind, f"{made.kind} {made.status}")
        loaded = wp.load_item(api, kind, made.id)
        H.expect(loaded.title == title, f"{kind} title came back as {loaded.title!r}")
        H.expect(loaded.content == content, f"{kind} draft: the site changed the content")
        published = wp.update_item(api, H._with(loaded, status="publish"))
        H.expect(published.status == "publish", f"{kind} is {published.status}")
        status, _headers, body = H.fetch(published.link)
        page = body.decode("utf-8", errors="replace")
        H.expect(status == 200, f"{kind} page answered {status}")
        missing = [p for p in _RENDERED[source] if not re.search(p, page)]
        H.expect(not missing, f"{kind} page lacks {missing}")
        for raw in ("```", "<!-- wp:", "Not the title"):
            H.expect(raw not in page, f"{kind} page shows {raw!r} as text")
        # Opened again as Markdown, sent back: no drift.
        markdown, islands = fences.post_to_markdown(wp.load_item(api, kind, made.id).content)
        again = fences.convert_markdown(markdown, islands).html
        H.expect(again == content, f"{kind}: reopening as Markdown changed the blocks")
        wp.update_item(api, H._with(published, content=again))
        final = wp.load_item(api, kind, made.id)
        H.expect(final.content == content and final.status == "publish", f"{kind} drifted")
        said.append(f"{kind} {made.id}")
    return f"{', '.join(said)}: {len(names)} blocks, published, read back, no drift"


def _markdown_test(ctx: Any) -> str:
    return _publish_source(ctx, "markdown")


def _blocks_test(ctx: Any) -> str:
    return _publish_source(ctx, "blocks")


def _html_test(ctx: Any) -> str:
    return _publish_source(ctx, "html")


def _text_test(ctx: Any) -> str:
    return _publish_source(ctx, "text")


_TESTS: tuple[tuple[str, str, Any], ...] = (
    ("119", "Publish Markdown as a post and a page", _markdown_test),
    ("120", "Publish block markup as a post and a page", _blocks_test),
    ("121", "Publish an HTML document as a post and a page", _html_test),
    ("122", "Publish plain text as a post and a page", _text_test),
)
