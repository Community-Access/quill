"""Export a vault as a static, linked HTML site (Accessible Vault, Phase 7) — wx-free.

Every note becomes an accessible ``.html`` page with its `[[wikilinks]]` resolved to
real relative anchors and its `![[embeds]]` inlined, plus a generated ``index.html``
that lists every note. Markdown-to-HTML is **injected** (``markdown_to_html``) so this
core stays wx-free and unit-testable while the app passes QUILL's own preview renderer.

:func:`note_to_html_fragment` renders a single note's body — reused by the *gated*
"Publish note" path (WordPress), which is why publishing an individual note and exporting
the whole site share one link/embed resolution.
"""

from __future__ import annotations

import html
from collections.abc import Callable

from quill.core.vault.render import expand_embeds, relative_site_url, render_links_html
from quill.core.vault.resolve import Resolver
from quill.core.vault.vault import Vault

#: Markdown source -> HTML body. Injected so the core needs no renderer of its own.
MarkdownToHtml = Callable[[str], str]

_PAGE = (
    '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>{title}</title>\n</head>\n<body>\n<main>\n<h1>{heading}</h1>\n{body}\n"
    '</main>\n<nav aria-label="Vault"><a href="{index_href}">All notes</a></nav>\n'
    "</body>\n</html>\n"
)


def _out_path(note_path: str) -> str:
    """``notes/x.md`` -> ``notes/x.html``."""
    return note_path[:-3] + ".html" if note_path.endswith(".md") else note_path + ".html"


def note_to_html_fragment(
    vault: Vault,
    resolver: Resolver,
    note_path: str,
    *,
    markdown_to_html: MarkdownToHtml,
    url_for: Callable[[str, str], str] | None = None,
) -> str:
    """Render one note's body to HTML: embeds inlined, wikilinks resolved, then Markdown.

    ``url_for`` maps a target note + anchor to an href (defaults to a same-directory
    ``<stem>.html#anchor`` suitable for a flat site or a publish preview). Reused by the
    site export and the gated single-note publish.
    """
    resolve_url = url_for or (lambda p, a: relative_site_url(note_path, p, a))
    text = vault.texts.get(note_path, "")
    expanded = expand_embeds(text, vault, resolver, note_path)
    linked = render_links_html(expanded, vault, resolver, note_path, url_for=resolve_url)
    return markdown_to_html(linked)


def build_site(
    vault: Vault,
    resolver: Resolver,
    *,
    markdown_to_html: MarkdownToHtml,
) -> dict[str, str]:
    """Build the whole site as ``{output_relative_path: html}`` (no disk IO).

    Includes one page per note plus ``index.html`` (an alphabetical list of every note,
    linking to its page). The caller writes the mapping to a chosen folder.
    """
    pages: dict[str, str] = {}
    for note_path in sorted(vault.notes):
        title = vault.notes[note_path].title
        out = _out_path(note_path)
        depth = out.count("/")
        index_href = ("../" * depth) + "index.html"
        body = note_to_html_fragment(vault, resolver, note_path, markdown_to_html=markdown_to_html)
        pages[out] = _PAGE.format(
            title=html.escape(title),
            heading=html.escape(title),
            body=body,
            index_href=index_href,
        )
    items = "\n".join(
        f'<li><a href="{html.escape(_out_path(p), quote=True)}">'
        f"{html.escape(vault.notes[p].title)}</a></li>"
        for p in sorted(vault.notes, key=lambda p: vault.notes[p].title.casefold())
    )
    pages["index.html"] = _PAGE.format(
        title="Vault",
        heading="Vault",
        body=f'<ul class="vault-index">\n{items}\n</ul>',
        index_href="index.html",
    )
    return pages


def write_site(pages: dict[str, str], out_dir: str) -> list[str]:
    """Write a built site to ``out_dir``; return the written relative paths. (thin IO)"""
    from pathlib import Path

    root = Path(out_dir)
    written: list[str] = []
    for rel, content in pages.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel)
    return written
