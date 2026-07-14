"""Resolve wikilinks (and, later, embeds) to HTML for preview and export.

wx-free, strict-typed. The in-app preview and every export path (single-note HTML and
the Phase 7 "export vault as a linked site") share this one resolver so `[[Note]]`,
`[[Note|alias]]`, and `[[Note#Heading]]` become real anchors, and a broken link is a
visible, announced marker rather than a silent literal. The destination URL is produced
by an injected ``url_for`` callable, so the same code serves the in-app preview (a
custom scheme the app intercepts) and a static site (relative ``.html`` paths).

Embed (`![[...]]`) expansion (Phase 5) layers on top via :func:`expand_embeds` /
:func:`resolve_embed_content`: it pulls a block, a heading section, or a whole note into
preview/compile/export with an announced boundary and cycle detection, while the
plain-text buffer keeps the literal `![[...]]`.
"""

from __future__ import annotations

import html
from collections.abc import Callable

from quill.core.vault.links import WikiLink, parse_links
from quill.core.vault.resolve import Resolver, resolve_link
from quill.core.vault.vault import Vault

#: ``(target_path, anchor) -> href``. ``anchor`` is a heading slug / block id or "".
UrlFor = Callable[[str, str], str]


def _display(link: WikiLink) -> str:
    """The visible link text: the alias, else the target (with a heading hint)."""
    if link.alias:
        return link.alias
    if link.heading:
        return f"{link.target} › {link.heading}" if link.target else link.heading
    return link.target or (link.block or "")


def _anchor(link: WikiLink) -> str:
    if link.heading:
        return _slug(link.heading)
    if link.block:
        return link.block
    return ""


def _slug(heading: str) -> str:
    """A stable, URL-safe heading anchor (lowercase words joined by hyphens)."""
    return "-".join(ch for ch in heading.lower().split())


def render_links_html(
    text: str,
    vault: Vault,
    resolver: Resolver,
    current_path: str,
    *,
    url_for: UrlFor,
) -> str:
    """Return ``text`` with every non-embed wikilink replaced by an HTML anchor.

    A resolved link becomes ``<a class="vault-link" href="…">display</a>``; an
    unresolved one becomes ``<span class="vault-link-broken" title="…">display</span>``
    so it is visible and screen-reader-announceable, never a silent literal. Only the
    `[[...]]` spans are touched — surrounding text is preserved byte-for-byte (callers
    that also convert Markdown run this before/after their Markdown pass as they prefer).
    Embeds (`![[...]]`) are left untouched (Phase 5).
    """
    pieces: list[str] = []
    cursor = 0
    for link in parse_links(text):
        if link.embed:
            continue
        pieces.append(text[cursor : link.start])
        display = html.escape(_display(link))
        target = resolve_link(vault, resolver, link, current_path)
        if target is None:
            pieces.append(
                f'<span class="vault-link-broken" title="No note named '
                f'{html.escape(link.target)}">{display}</span>'
            )
        else:
            href = html.escape(url_for(target.path, _anchor(link)), quote=True)
            pieces.append(f'<a class="vault-link" href="{href}">{display}</a>')
        cursor = link.end
    pieces.append(text[cursor:])
    return "".join(pieces)


def resolve_embed_content(
    vault: Vault, target_path: str, heading: str | None, block: str | None
) -> str:
    """The text an `![[...]]` embed pulls in: a block, a heading section, or the whole note.

    A *block* embed is the line carrying the `^id` marker (marker stripped). A *heading*
    embed is that heading down to the next heading of the same-or-higher level. Otherwise
    the whole note. Returns "" when the target/anchor is missing.
    """
    text = vault.texts.get(target_path, "")
    info = vault.notes.get(target_path)
    if info is None or not text:
        return ""
    if block:
        offset = info.block_ids.get(block)
        if offset is None:
            return ""
        line_start = text.rfind("\n", 0, offset) + 1
        line_end = text.find("\n", offset)
        line = text[line_start : (line_end if line_end != -1 else len(text))]
        return line.rsplit("^", 1)[0].strip()  # drop the ^id marker
    if heading:
        wanted = _slug(heading)
        headings = list(info.headings)
        for i, h in enumerate(headings):
            if _slug(h.title) == wanted:
                end = len(text)
                for later in headings[i + 1 :]:
                    if later.level <= h.level:
                        end = later.offset
                        break
                return text[h.offset : end].strip()
        return ""
    return text.strip()


def expand_embeds(
    text: str,
    vault: Vault,
    resolver: Resolver,
    current_path: str,
    *,
    _seen: frozenset[str] = frozenset(),
) -> str:
    """Replace `![[...]]` embeds with the target's content, recursively (cycle-safe).

    Each embed is wrapped in an announced boundary comment; a cycle emits a note instead
    of recursing forever. Non-embed `[[...]]` links are left untouched (they are resolved
    separately by :func:`render_links_html`). Feeds preview, compile/export, and
    "speak embed at cursor".
    """
    pieces: list[str] = []
    cursor = 0
    for link in parse_links(text):
        if not link.embed:
            continue
        pieces.append(text[cursor : link.start])
        target = resolve_link(vault, resolver, link, current_path)
        if target is None:
            pieces.append(f"[missing embed: {link.target}]")
        elif target.path in _seen or target.path == current_path:
            pieces.append(f"[circular embed: {link.target}]")
        else:
            title = vault.notes[target.path].title if target.path in vault.notes else link.target
            content = resolve_embed_content(vault, target.path, link.heading, link.block)
            inner = expand_embeds(
                content, vault, resolver, target.path, _seen=_seen | {current_path, target.path}
            )
            pieces.append(f"<!-- embedded from {title} -->\n{inner}\n<!-- end embed -->")
        cursor = link.end
    pieces.append(text[cursor:])
    return "".join(pieces)


def relative_site_url(from_path: str, to_path: str, anchor: str) -> str:
    """A relative ``.html`` href from one note to another for a static export site.

    ``a/b.md`` linking to ``c/d.md`` → ``../c/d.html`` (+ ``#anchor``). Pure string math
    over posix-style relative paths, so it is deterministic and unit-testable.
    """
    from_parts = from_path.split("/")[:-1]  # drop the filename
    to_parts = to_path.split("/")
    to_file = to_parts[-1]
    to_dir = to_parts[:-1]
    # Common prefix length.
    common = 0
    for a, b in zip(from_parts, to_dir, strict=False):
        if a != b:
            break
        common += 1
    up = [".."] * (len(from_parts) - common)
    down = to_dir[common:]
    stem = to_file[:-3] if to_file.endswith(".md") else to_file
    rel = "/".join([*up, *down, f"{stem}.html"]) or f"{stem}.html"
    return f"{rel}#{anchor}" if anchor else rel
