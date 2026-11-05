"""Save markup and inline Markdown for :mod:`quill.core.wordpress.fences`.

The pieces both directions share: escaping, inline Markdown to rich-text HTML
and back, line classification, and the block builders that write exactly what
WordPress's own save code writes (WordPress 6.4 and later). Private to the
fences modules; import the public API from ``fences``.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from typing import Any

from quill.core.wordpress.blocks import Block, serialize_block

# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------

_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#[xX][0-9A-Fa-f]+);")
_LOOSE_AMP = re.compile(r"&(?!(?:[a-z0-9]+|#[0-9]+|#x[a-f0-9]+);)", re.I)
_HTML_TAG = re.compile(r"<!--.*?-->|</?[A-Za-z][^<>]*>", re.S)
_ANY_TAG = re.compile(r"<!--.*?-->|<[^<>]*>", re.S)
_MD_PUNCT = frozenset("\\`*_{}[]()#+-.!|:>\"'<&~=/")


def _esc_attr(value: str) -> str:
    """WordPress's ``escapeAttribute``: ampersands, quotes and ``>``."""
    return _LOOSE_AMP.sub("&amp;", value).replace('"', "&quot;").replace(">", "&gt;")


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unquote(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def _md_unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda m: m.group(1) if m.group(1) in _MD_PUNCT else m.group(0), text)


# ---------------------------------------------------------------------------
# Inline Markdown <-> HTML
# ---------------------------------------------------------------------------

_LINK_OPEN = re.compile(r'<a href="([^"]*)">')


def _text_to_md(text: str) -> str:
    text = re.sub(r"[\\`*\[\]]", lambda m: "\\" + m.group(0), text)
    text = re.sub(r"&amp;(?![#A-Za-z0-9]+;)", "&", text)
    return re.sub(r"&lt;(?![A-Za-z/!?])", "<", text)


def _inline_to_md(markup: str) -> str | None:
    """Rich-text HTML to inline Markdown; None when it has no exact Markdown."""
    out: list[str] = []
    links: list[str | None] = []
    pos = 0
    for m in _ANY_TAG.finditer(markup):
        if m.start() < pos:
            continue
        out.append(_text_to_md(markup[pos : m.start()]))
        pos = m.end()
        tag = m.group(0)
        if tag in ("<strong>", "</strong>"):
            out.append("**")
        elif tag in ("<em>", "</em>"):
            out.append("*")
        elif tag == "<code>":
            end = markup.find("</code>", pos)
            if end < 0:
                return None
            code = markup[pos:end].replace("&lt;", "<").replace("&amp;", "&")
            if not code or "`" in code or _ANY_TAG.search(code):
                return None
            out.append("`" + code + "`")
            pos = end + len("</code>")
        elif tag.startswith("<a ") or tag == "<a>":
            link = _LINK_OPEN.fullmatch(tag)
            if link:
                links.append(html.unescape(link.group(1)))
                out.append("[")
            else:
                links.append(None)
                out.append(tag)
        elif tag == "</a>" and links:
            href = links.pop()
            if href is None:
                out.append(tag)
            elif re.search(r"[\s()]", href) or not href:
                return None
            else:
                out.append("](" + href + ")")
        else:
            out.append(tag)
    out.append(_text_to_md(markup[pos:]))
    return "".join(out)


_MD_LINK = re.compile(r"\[((?:\\.|[^\\\[\]])*)\]\(([^\s()]+)\)")


def _esc_text(char: str) -> str:
    if char == "&":
        return "&amp;"
    if char == "<":
        return "&lt;"
    return char


def _inline_to_html(md: str) -> str:
    """Inline Markdown to the HTML WordPress's rich text would save."""
    tokens: list[tuple[str, str]] = []  # ("t", html) or ("d", "**" | "*")
    i = 0
    n = len(md)
    while i < n:
        ch = md[i]
        if ch == "\\" and i + 1 < n and md[i + 1] in _MD_PUNCT:
            tokens.append(("t", _esc_text(md[i + 1])))
            i += 2
        elif ch == "`":
            end = md.find("`", i + 1)
            if end > i + 1:
                code = _LOOSE_AMP.sub("&amp;", md[i + 1 : end]).replace("<", "&lt;")
                tokens.append(("t", f"<code>{code}</code>"))
                i = end + 1
            else:
                tokens.append(("t", "`"))
                i += 1
        elif ch == "*":
            if md.startswith("**", i):
                tokens.append(("d", "**"))
                i += 2
            else:
                tokens.append(("d", "*"))
                i += 1
        elif ch == "[" and (link := _MD_LINK.match(md, i)):
            href = _esc_attr(link.group(2))
            inner = _inline_to_html(link.group(1))
            tokens.append(("t", f'<a href="{href}">{inner}</a>'))
            i = link.end()
        elif ch == "<" and (tag := _HTML_TAG.match(md, i)):
            tokens.append(("t", tag.group(0)))
            i = tag.end()
        elif ch == "&" and (entity := _ENTITY.match(md, i)):
            tokens.append(("t", entity.group(0)))
            i = entity.end()
        else:
            tokens.append(("t", _esc_text(ch)))
            i += 1
    # Pair the emphasis delimiters; an unpaired one is just an asterisk.
    rendered = [value for _kind, value in tokens]
    open_at: dict[str, int] = {}
    for index, (kind, value) in enumerate(tokens):
        if kind != "d":
            continue
        element = "strong" if value == "**" else "em"
        if value in open_at:
            rendered[open_at.pop(value)] = f"<{element}>"
            rendered[index] = f"</{element}>"
        else:
            open_at[value] = index
    return "".join(rendered)


# ---------------------------------------------------------------------------
# Line classification (shared by the reader and the writer's escaping)
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"^:::(?:\s+(.*?))?\s*$")
_HEADING = re.compile(r"^(#{1,6}) (.*)$")
_LIST_ITEM = re.compile(r"^(?:([-*+])|(\d+)([.)])) (.*)$")
_IMAGE = re.compile(
    r'^!\[((?:\\.|[^\\\]])*)\]\(([^\s()]+)(?:\s+"((?:\\.|[^\\"])*)")?\)'
    r"(?:\s+\{([^{}]*)\})?\s*$"
)
_TABLE_RULE = re.compile(r"^\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")
_ARG = re.compile(r'"((?:\\.|[^\\"])*)"|(\S+)')


def _line_kind(line: str) -> str:
    if not line.strip():
        return "blank"
    if _FENCE.match(line):
        return "fence"
    if line.startswith("```"):
        return "code"
    if _HEADING.match(line):
        return "heading"
    if line.rstrip() == "---":
        return "separator"
    if line.startswith(">"):
        return "quote"
    if _LIST_ITEM.match(line):
        return "list"
    if line.startswith("|"):
        return "table"
    if _IMAGE.match(line):
        return "image"
    if line.startswith("-- "):
        return "cite"
    return "text"


def _escape_line(line: str) -> str:
    """Stop a line of ordinary text being read as the start of a block."""
    if _line_kind(line) in ("text", "blank"):
        return line
    digits = re.match(r"^(\d+)([.)])", line)
    if digits:
        return digits.group(1) + "\\" + line[len(digits.group(1)) :]
    return "\\" + line


def _fence_parts(line: str) -> tuple[str, list[tuple[str, bool]]] | None:
    m = _FENCE.match(line)
    if m is None:
        return None
    args = [
        (_unquote(a.group(1)), True) if a.group(1) is not None else (a.group(2), False)
        for a in _ARG.finditer(m.group(1) or "")
    ]
    if not args:
        return "", []
    head = args[0][0].lower()
    return head, args[1:]


def _fence_key(line: str) -> str | None:
    parts = _fence_parts(line)
    if parts is None:
        return None
    head, args = parts
    if head == "end":
        return "end " + (args[0][0].lower() if args else "")
    return head


# ---------------------------------------------------------------------------
# Block builders: WordPress 6.4+ save output
# ---------------------------------------------------------------------------


def _new(name: str, attrs: dict[str, Any] | None, *parts: str | Block) -> Block:
    block = Block(name=name, attrs=dict(attrs or {}))
    for part in parts:
        if isinstance(part, Block):
            block.inner_blocks.append(part)
            block.inner_content.append(None)
        elif part:
            last = block.inner_content[-1] if block.inner_content else None
            if last is not None:
                block.inner_content[-1] = last + part
            else:
                block.inner_content.append(part)
            block.inner_html += part
    return block


def _between(children: Sequence[Block], sep: str = "\n\n") -> list[str | Block]:
    parts: list[str | Block] = []
    for index, child in enumerate(children):
        if index:
            parts.append(sep)
        parts.append(child)
    return parts


def _paragraph(inner: str) -> Block:
    return _new("core/paragraph", None, f"\n<p>{inner}</p>\n")


def _heading(level: int, inner: str) -> Block:
    attrs = None if level == 2 else {"level": level}
    return _new("core/heading", attrs, f'\n<h{level} class="wp-block-heading">{inner}</h{level}>\n')


def _list(ordered: bool, items: Sequence[Block]) -> Block:
    tag = "ol" if ordered else "ul"
    attrs = {"ordered": True} if ordered else None
    return _new(
        "core/list", attrs, f'\n<{tag} class="wp-block-list">', *_between(items), f"</{tag}>\n"
    )


def _list_item(inner: str, nested: Sequence[Block]) -> Block:
    if not nested:
        return _new("core/list-item", None, f"\n<li>{inner}</li>\n")
    return _new("core/list-item", None, f"\n<li>{inner}", *nested, "</li>\n")


def _quote_block(children: Sequence[Block], cite: str | None) -> Block:
    tail = (f"<cite>{cite}</cite>" if cite is not None else "") + "</blockquote>\n"
    return _new(
        "core/quote", None, '\n<blockquote class="wp-block-quote">', *_between(children), tail
    )


def _image(
    src: str,
    alt: str,
    caption: str | None,
    image_id: int | None,
    size: str | None,
    link: str | None,
) -> Block:
    attrs: dict[str, Any] = {}
    if image_id is not None:
        attrs["id"] = image_id
    if size:
        attrs["sizeSlug"] = size
    if link:
        attrs["linkDestination"] = link
    css = "wp-block-image" + (f" size-{size}" if size else "")
    img = f'<img src="{_esc_attr(src)}" alt="{_esc_attr(alt)}"'
    if image_id is not None:
        img += f' class="wp-image-{image_id}"'
    img += "/>"
    cap = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ""
    return _new("core/image", attrs, f'\n<figure class="{css}">{img}{cap}</figure>\n')


def _separator() -> Block:
    return _new(
        "core/separator", None, '\n<hr class="wp-block-separator has-alpha-channel-opacity"/>\n'
    )


def _code_escape(text: str) -> str:
    text = _LOOSE_AMP.sub("&amp;", text).replace("<", "&lt;").replace("[", "&#91;")
    return re.sub(r"^(\s*https?:)//([^\s<>\"]+\s*)$", r"\1&#47;&#47;\2", text, count=1, flags=re.M)


def _code_unescape(text: str) -> str:
    return (
        text.replace("&#47;", "/").replace("&#91;", "[").replace("&lt;", "<").replace("&amp;", "&")
    )


def _code(text: str) -> Block:
    return _new(
        "core/code", None, f'\n<pre class="wp-block-code"><code>{_code_escape(text)}</code></pre>\n'
    )


def _preformatted(text: str) -> Block:
    return _new("core/preformatted", None, f'\n<pre class="wp-block-preformatted">{text}</pre>\n')


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> Block:
    head = "".join(f"<th>{cell}</th>" for cell in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    markup = '\n<figure class="wp-block-table"><table class="has-fixed-layout">'
    markup += f"<thead><tr>{head}</tr></thead>"
    if rows:
        markup += f"<tbody>{body}</tbody>"
    markup += "</table></figure>\n"
    return _new("core/table", None, markup)


def _button(text: str, url: str | None) -> Block:
    href = f' href="{_esc_attr(url)}"' if url else ""
    link = f'<a class="wp-block-button__link wp-element-button"{href}>{text}</a>'
    return _new("core/button", None, f'\n<div class="wp-block-button">{link}</div>\n')


def _buttons(children: Sequence[Block]) -> Block:
    return _new(
        "core/buttons", None, '\n<div class="wp-block-buttons">', *_between(children), "</div>\n"
    )


def _columns(children: Sequence[Block]) -> Block:
    return _new(
        "core/columns", None, '\n<div class="wp-block-columns">', *_between(children), "</div>\n"
    )


def _column(width: str | None, children: Sequence[Block]) -> Block:
    attrs = {"width": width} if width else None
    style = f' style="flex-basis:{_esc_attr(width)}"' if width else ""
    return _new(
        "core/column",
        attrs,
        f'\n<div class="wp-block-column"{style}>',
        *_between(children),
        "</div>\n",
    )


_GROUP_LAYOUT: dict[str, Any] = {"layout": {"type": "constrained"}}


def _group(children: Sequence[Block]) -> Block:
    return _new(
        "core/group",
        _GROUP_LAYOUT,
        '\n<div class="wp-block-group">',
        *_between(children),
        "</div>\n",
    )


def _details(summary: str, children: Sequence[Block]) -> Block:
    head = f'\n<details class="wp-block-details"><summary>{summary}</summary>'
    return _new("core/details", None, head, *_between(children), "</details>\n")


def _embed(url: str, kind: str | None, provider: str | None, aspect: str | None) -> Block:
    attrs: dict[str, Any] = {"url": url}
    classes = ["wp-block-embed"]
    if kind:
        attrs["type"] = kind
        classes.append(f"is-type-{kind}")
    if provider:
        attrs["providerNameSlug"] = provider
        classes += [f"is-provider-{provider}", f"wp-block-embed-{provider}"]
    if aspect:
        attrs["responsive"] = True
        attrs["className"] = f"wp-embed-aspect-{aspect} wp-has-aspect-ratio"
        classes.append(attrs["className"])
    markup = (
        f'\n<figure class="{_esc_attr(" ".join(classes))}">'
        f'<div class="wp-block-embed__wrapper">\n{url}\n</div></figure>\n'
    )
    return _new("core/embed", attrs, markup)


def _spacer(height: str | None) -> Block:
    value = height or "100px"
    attrs = {"height": value} if value != "100px" else None
    style = f"height:{_esc_attr(value)}"
    markup = f'\n<div style="{style}" aria-hidden="true" class="wp-block-spacer"></div>\n'
    return _new("core/spacer", attrs, markup)


def _emit(blocks: Sequence[Block]) -> str:
    return "\n\n".join(serialize_block(block) for block in blocks)
