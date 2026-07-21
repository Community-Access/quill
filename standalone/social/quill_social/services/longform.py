"""QUILL Longform: accessible semantic HTML and teasers (PRD 16.4, 20.1).

QUILL Longform turns QUILL Markdown into a canonical, accessible page, posts a
short summary with a link, spins up a teaser thread, and keeps a simple revision
history (PRD 16.4). This module ships a small, dependency-free Markdown-subset
renderer that emits semantic HTML -- real headings, lists, tables, links, images
with alt text, blockquotes, and code -- and escapes every piece of user text so
a document can never inject script (PRD 16.4 "accessible page", plus the
project's security rule against injection).

Deliberately a *subset*: it covers the block and inline constructs QUILL
Longform promises without pulling in a Markdown library. Anything it does not
recognize is emitted as an escaped paragraph, so unknown input degrades to safe,
readable text rather than raw HTML.

The teaser thread reuses :func:`quill_social.services.thread_splitter.split_thread`
so teaser segmentation matches the composer exactly. This module is wx-free, has
no I/O, and uses no wall-clock except through an injected ``now``.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from quill_social.model import now_ms
from quill_social.services.thread_splitter import ThreadSplit, split_thread

Counter = Callable[[str], int]

# Inline patterns, applied to already-HTML-escaped text so the replacements
# themselves are the only tags that ever appear.
_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;([^&]*)&quot;)?\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def _render_inline(text: str) -> str:
    """Escape ``text`` then apply inline Markdown, keeping output injection-safe.

    Order matters: escape first so any ``<`` in the source becomes ``&lt;``;
    then images before links (an image is a link with a leading ``!``); then
    code, bold, italic. Because we escape before matching, the only tags in the
    result are the ones we insert.
    """
    escaped = html.escape(text, quote=True)

    def img_sub(m: re.Match[str]) -> str:
        alt = m.group(1)
        src = m.group(2)
        title = m.group(3)
        title_attr = f' title="{title}"' if title else ""
        return f'<img src="{src}" alt="{alt}"{title_attr} />'

    def link_sub(m: re.Match[str]) -> str:
        label = m.group(1)
        href = m.group(2)
        return f'<a href="{href}">{label}</a>'

    escaped = _IMG.sub(img_sub, escaped)
    escaped = _LINK.sub(link_sub, escaped)
    escaped = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    escaped = _ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", escaped)
    return escaped


def _render_table(rows: list[str]) -> str:
    """Render a GitHub-style pipe table (header, divider, body) as ``<table>``."""

    def cells(line: str) -> list[str]:
        line = line.strip().strip("|")
        return [c.strip() for c in line.split("|")]

    header = cells(rows[0])
    body = rows[2:]  # rows[1] is the |---|---| divider
    out = ["<table>", "<thead>", "<tr>"]
    out.extend(f"<th>{_render_inline(c)}</th>" for c in header)
    out.append("</tr>")
    out.append("</thead>")
    out.append("<tbody>")
    for line in body:
        out.append("<tr>")
        out.extend(f"<td>{_render_inline(c)}</td>" for c in cells(line))
        out.append("</tr>")
    out.append("</tbody>")
    out.append("</table>")
    return "".join(out)


def _is_table_start(lines: list[str], i: int) -> bool:
    return (
        "|" in lines[i]
        and i + 1 < len(lines)
        and bool(re.match(r"^\s*\|?[\s:-]*-[\s:|-]*$", lines[i + 1]))
        and "|" in lines[i + 1]
    )


def to_semantic_html(markdown: str) -> str:
    """Render a QUILL Markdown subset to accessible semantic HTML (PRD 16.4).

    Supports ATX headings (``#``..``######``), unordered (``-``/``*``) and
    ordered (``1.``) lists, pipe tables, ``>`` blockquotes, fenced code blocks
    (```` ``` ````), horizontal rules, images with alt text, links, inline
    code/bold/italic, and paragraphs. All text is HTML-escaped, so raw HTML or a
    ``<script>`` in the source is rendered inert.
    """
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank line: paragraph separator, nothing to emit.
        if not stripped:
            i += 1
            continue

        # Fenced code block.
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            cls = f' class="language-{html.escape(lang, quote=True)}"' if lang else ""
            body = html.escape("\n".join(code_lines), quote=True)
            out.append(f"<pre><code{cls}>{body}</code></pre>")
            continue

        # Horizontal rule.
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            out.append("<hr />")
            i += 1
            continue

        # Heading.
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_render_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # Table.
        if _is_table_start(lines, i):
            table_rows: list[str] = []
            while i < n and "|" in lines[i] and lines[i].strip():
                table_rows.append(lines[i])
                i += 1
            out.append(_render_table(table_rows))
            continue

        # Blockquote.
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote><p>{_render_inline(' '.join(quote_lines))}</p></blockquote>")
            continue

        # Unordered list.
        if re.match(r"^[-*]\s+", stripped):
            items: list[str] = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_render_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # Ordered list.
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_render_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # Paragraph: gather consecutive non-blank, non-structural lines.
        para: list[str] = []
        while i < n and lines[i].strip() and not _breaks_paragraph(lines, i):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_render_inline(' '.join(para))}</p>")
    return "\n".join(out)


def _breaks_paragraph(lines: list[str], i: int) -> bool:
    s = lines[i].strip()
    return bool(
        s.startswith("#")
        or s.startswith(">")
        or s.startswith("```")
        or re.match(r"^[-*]\s+", s)
        or re.match(r"^\d+\.\s+", s)
        or re.match(r"^(-{3,}|\*{3,}|_{3,})$", s)
        or _is_table_start(lines, i)
    )


# -- summary + teaser -------------------------------------------------------


@dataclass
class Summary:
    """A short summary plus a canonical-link placeholder (PRD 16.4)."""

    text: str = ""
    canonical_url: str = ""  # filled when the page is published

    def to_dict(self) -> dict:
        return {"text": self.text, "canonical_url": self.canonical_url}

    def post_text(self) -> str:
        """The summary plus its link, ready to post (PRD 16.4 'post a summary')."""
        if self.canonical_url:
            return f"{self.text}\n\n{self.canonical_url}"
        return self.text


def _strip_markdown(markdown: str) -> str:
    """Reduce Markdown to plain text for summarizing/teasing."""
    text = markdown
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # code fences
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> label
    text = re.sub(r"[#>*_`|-]", " ", text)  # residual markers
    text = re.sub(r"[ \t]+", " ", text)
    return text


def make_summary(markdown: str, limit: int = 280) -> Summary:
    """Summarize a longform document to at most ``limit`` characters (PRD 16.4).

    Deterministic: takes the leading prose and truncates on a word boundary,
    appending an ellipsis when it had to cut. Leaves ``canonical_url`` empty --
    the publisher fills it once the accessible page has a URL.
    """
    flat = " ".join(_strip_markdown(markdown).split())
    if len(flat) <= limit:
        return Summary(text=flat)
    cut = flat[:limit].rstrip()
    if " " in cut:
        cut = cut[: cut.rfind(" ")].rstrip()
    return Summary(text=cut + "…")


def _teaser_source(markdown: str) -> str:
    """Derive teaser text: headings plus the first line of each section (PRD 16.4)."""
    lines = markdown.replace("\r\n", "\n").split("\n")
    picked: list[str] = []
    expect_body = False
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        heading = re.match(r"^#{1,6}\s+(.*)$", s)
        if heading:
            picked.append(heading.group(1).strip())
            expect_body = True
            continue
        if expect_body:
            picked.append(_strip_markdown(s).strip())
            expect_body = False
    if not picked:
        picked = [_strip_markdown(s).strip() for s in lines if s.strip()][:3]
    return "\n\n".join(p for p in picked if p)


def to_teaser_thread(
    markdown: str, char_limit: int = 280, *, counter: Counter = len
) -> ThreadSplit:
    """Build a teaser thread from a longform document (PRD 16.4, 20.1).

    Derives a teaser (each heading plus the first line beneath it) and runs it
    through the shared thread splitter, so teaser segmentation matches the
    composer's threading exactly.
    """
    teaser = _teaser_source(markdown)
    return split_thread(teaser, char_limit, counter=counter)


# -- revisions --------------------------------------------------------------


@dataclass
class Revision:
    """One revision record in a longform document's history (PRD 16.4)."""

    version: int = 1
    text: str = ""
    prior_version: int | None = None
    changed: bool = True
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "text": self.text,
            "prior_version": self.prior_version,
            "changed": self.changed,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Revision:
        return cls(
            version=int(d.get("version", 1) or 1),
            text=d.get("text", ""),
            prior_version=d.get("prior_version"),
            changed=bool(d.get("changed", True)),
            created=int(d.get("created", 0) or 0),
        )


def revision(
    markdown: str, prior: Revision | None = None, *, now: Callable[[], int] = now_ms
) -> Revision:
    """Create a revision record for ``markdown`` following ``prior`` (PRD 16.4).

    Deterministic and side-effect-free: bumps the version, links to the prior
    version, and flags whether the text actually changed so an unchanged save
    does not masquerade as an edit.
    """
    if prior is None:
        return Revision(version=1, text=markdown, prior_version=None, changed=True, created=now())
    changed = markdown != prior.text
    return Revision(
        version=prior.version + 1,
        text=markdown,
        prior_version=prior.version,
        changed=changed,
        created=now(),
    )
