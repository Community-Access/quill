"""Check Before Publishing: local content checks on a post's HTML.

wordpress.md section 7 and 9.11. Publish runs these, speaks one line
(:func:`summary_line`), and opens the list; each :class:`Finding` carries the
offset Go to It jumps to. None of them blocks publishing.

Two severities: a ``problem`` is something a visitor using assistive technology
will meet (an image with no alt text, a skipped heading); a ``check`` is worth a
look but may be right (a GIF that might not be animated, the post going to a
site other than the default). ``fixable`` means QUILL can offer a one-step
fix -- add "(opens in a new tab)", turn off autoplay, make the Heading 1 a
Heading 2 -- rather than needing the writer's words.

Stdlib only (``html.parser``); WordPress block comments (``<!-- wp:... -->``)
are comments to the parser and never count as content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Literal

__all__ = [
    "Finding",
    "Severity",
    "check_content",
    "has_decorative_symbol",
    "summary_line",
]

Severity = Literal["problem", "check"]

_EXCERPT_LIMIT = 60

_VAGUE_LINK_TEXT = frozenset({"click here", "here", "read more", "more", "link", "this link"})
_NEW_TAB_PHRASES = ("opens in a new tab", "opens in a new window")
_FILENAME_ALT_RE = re.compile(
    r"^(?:[\w\- .]+\.(?:jpe?g|png|gif|webp|bmp|tiff?|svg|heic|avif)"
    r"|(?:img|dsc|dscn|dcim|pxl|image|photo|screenshot|screen shot)[_\- ]?\d[\w\- ]*)$",
    re.IGNORECASE,
)
_REDUNDANT_ALT_RE = re.compile(
    r"^(?:an?\s+)?(?:image|picture|photo|photograph|graphic)\s+of\b", re.IGNORECASE
)
_COLOR_PROPERTY_RE = re.compile(r"(?:^|;)\s*color\s*:", re.IGNORECASE)
# Bold or italic is a second marker; a <mark> highlight is colour again.
_EMPHASIS_TAGS = frozenset({"strong", "b", "em", "i"})
_HEADING_TAGS = {f"h{n}": n for n in range(1, 7)}
_SKIP_TAGS = frozenset({"script", "style", "template"})
_COLOUR_ALONE_MAX_WORDS = 4


@dataclass(frozen=True)
class Finding:
    """One thing Check Before Publishing found."""

    kind: str
    severity: Severity
    message: str
    offset: int
    excerpt: str
    fixable: bool = False


def has_decorative_symbol(text: str) -> bool:
    """True when ``text`` holds an emoji or a decorative symbol (stars, arrows,
    dingbats, check marks) that a screen reader reads out by name."""
    for ch in text:
        cp = ord(ch)
        if (
            0x1F000 <= cp <= 0x1FAFF  # emoji, pictographs, symbols
            or 0x2600 <= cp <= 0x27BF  # miscellaneous symbols, dingbats
            or 0x2190 <= cp <= 0x21FF  # arrows
            or 0x2300 <= cp <= 0x23FF  # miscellaneous technical (watch, hourglass)
            or 0x25A0 <= cp <= 0x25FF  # geometric shapes
            or 0x2B00 <= cp <= 0x2BFF  # more arrows and stars
            or cp in (0xFE0F, 0x200D, 0x20E3)  # emoji presentation, joiner, keycap
        ):
            return True
    return False


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= _EXCERPT_LIMIT:
        return text
    return text[: _EXCERPT_LIMIT - 3].rstrip() + "..."


def _normalise_url(url: str) -> str:
    url = url.strip().lower()
    url = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", url)
    url = url.removeprefix("www.").removeprefix("mailto:")
    return url.rstrip("/")


def _looks_like_address(text: str, href: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if href and _normalise_url(t) == _normalise_url(href):
        return True
    return bool(re.match(r"^(?:https?://|www\.)\S+$", t, re.IGNORECASE))


def _src_is_gif(src: str) -> bool:
    path = src.split("#", 1)[0].split("?", 1)[0]
    return path.lower().endswith(".gif")


def _attrs(raw: list[tuple[str, str | None]]) -> dict[str, str | None]:
    return {name.lower(): value for name, value in raw}


@dataclass
class _Image:
    offset: int
    alt: str | None
    decorative: bool
    src: str


@dataclass
class _Link:
    offset: int
    href: str
    target: str
    aria_label: str
    text: list[str] = field(default_factory=list)
    images: list[_Image] = field(default_factory=list)


@dataclass
class _Heading:
    offset: int
    level: int
    text: list[str] = field(default_factory=list)


@dataclass
class _Table:
    offset: int
    has_header: bool = False
    has_caption: bool = False


@dataclass
class _ColourSpan:
    offset: int
    tag: str
    emphasised: bool
    text: list[str] = field(default_factory=list)
    depth: int = 1


class _Checker(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self._line_starts = [0]
        for index, ch in enumerate(html):
            if ch == "\n":
                self._line_starts.append(index + 1)
        self.findings: list[Finding] = []
        self._links: list[_Link] = []
        self._heading: _Heading | None = None
        self._last_heading_level = 1  # the theme prints the title as Heading 1
        self._tables: list[_Table] = []
        self._colour_spans: list[_ColourSpan] = []
        self._emphasis_depth = 0
        self._skip = 0

    # -- plumbing ------------------------------------------------------------

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def _add(
        self,
        kind: str,
        severity: Severity,
        message: str,
        offset: int,
        excerpt: str,
        *,
        fixable: bool = False,
    ) -> None:
        self.findings.append(Finding(kind, severity, message, offset, _excerpt(excerpt), fixable))

    # -- parser callbacks ----------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1
            return
        a = _attrs(attrs)
        offset = self._offset()
        if tag == "img":
            self._image(a, offset)
        elif tag == "a":
            self._links.append(
                _Link(
                    offset=offset,
                    href=a.get("href") or "",
                    target=(a.get("target") or "").strip().lower(),
                    aria_label=(a.get("aria-label") or "").strip(),
                )
            )
        elif tag in _HEADING_TAGS:
            self._heading = _Heading(offset, _HEADING_TAGS[tag])
        elif tag == "table":
            self._tables.append(_Table(offset))
        elif tag == "th" and self._tables:
            self._tables[-1].has_header = True
        elif tag == "caption" and self._tables:
            self._tables[-1].has_caption = True
        elif tag == "video":
            self._video(a, offset)
        if tag in _EMPHASIS_TAGS:
            self._emphasis_depth += 1
            for span in self._colour_spans:
                span.emphasised = True
        if tag in ("span", "mark"):
            for span in self._colour_spans:
                if span.tag == tag:
                    span.depth += 1
            style = a.get("style") or ""
            if _COLOR_PROPERTY_RE.search(style):
                self._colour_spans.append(
                    _ColourSpan(offset, tag, emphasised=self._emphasis_depth > 0)
                )

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._links:
            self._end_link(self._links.pop())
        elif tag in _HEADING_TAGS and self._heading is not None:
            heading, self._heading = self._heading, None
            self._end_heading(heading)
        elif tag == "table" and self._tables:
            self._end_table(self._tables.pop())
        if tag in _EMPHASIS_TAGS:
            self._emphasis_depth = max(0, self._emphasis_depth - 1)
        if tag in ("span", "mark") and self._colour_spans:
            for span in self._colour_spans:
                if span.tag == tag:
                    span.depth -= 1
            while self._colour_spans and self._colour_spans[-1].depth <= 0:
                self._end_colour_span(self._colour_spans.pop())

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        for link in self._links:
            link.text.append(data)
        if self._heading is not None:
            self._heading.text.append(data)
        for span in self._colour_spans:
            span.text.append(data)

    def close(self) -> None:
        super().close()
        # Anything left open at the end is judged as it stands.
        while self._links:
            self._end_link(self._links.pop())
        if self._heading is not None:
            heading, self._heading = self._heading, None
            self._end_heading(heading)
        while self._tables:
            self._end_table(self._tables.pop())
        self._colour_spans.clear()

    # -- the checks ----------------------------------------------------------

    def _image(self, a: dict[str, str | None], offset: int) -> None:
        alt = a.get("alt")
        role = (a.get("role") or "").strip().lower()
        decorative = (
            alt is not None
            and not alt.strip()
            and (role in ("presentation", "none") or "data-quill-decorative" in a)
        )
        image = _Image(offset, alt, decorative, a.get("src") or "")
        label = image.src.rsplit("/", 1)[-1] or "image"
        if self._links:
            # Missing or empty alt inside a link is judged with the link: it may
            # be the link's only content, or the link's text may already name it.
            self._links[-1].images.append(image)
        elif alt is None:
            self._add("image-no-alt", "problem", "An image has no alt text.", offset, label)
        elif not alt.strip():
            if not decorative:
                self._add(
                    "image-empty-alt",
                    "problem",
                    "An image has empty alt text but is not marked decorative.",
                    offset,
                    label,
                )
        if alt is not None and alt.strip():
            text = alt.strip()
            if _FILENAME_ALT_RE.match(text):
                self._add(
                    "alt-is-filename",
                    "problem",
                    f"An image's alt text is a file name, {text}, not a description.",
                    offset,
                    text,
                )
            elif _REDUNDANT_ALT_RE.match(text):
                self._add(
                    "alt-says-image",
                    "check",
                    "An image's alt text begins by saying it is an image, "
                    "which a screen reader already says.",
                    offset,
                    text,
                    fixable=True,
                )
        if _src_is_gif(image.src):
            self._add(
                "animated-gif",
                "check",
                "This image is a GIF, which may move; moving images distract some readers.",
                offset,
                label,
                fixable=True,
            )

    def _video(self, a: dict[str, str | None], offset: int) -> None:
        if "autoplay" in a:
            src = (a.get("src") or "").rsplit("/", 1)[-1] or "video"
            self._add(
                "video-autoplay",
                "problem",
                "A video plays by itself when the page opens.",
                offset,
                src,
                fixable=True,
            )

    def _end_link(self, link: _Link) -> None:
        text = " ".join("".join(link.text).split())
        alts = " ".join(i.alt.strip() for i in link.images if i.alt and i.alt.strip())
        name = link.aria_label or " ".join(p for p in (text, alts) if p)
        excerpt = text or link.href
        if not name:
            if link.images:
                self._add(
                    "linked-image-no-alt",
                    "problem",
                    "A linked image has no alt text, so the link has no name.",
                    link.offset,
                    link.href,
                )
            else:
                self._add("link-no-text", "problem", "A link has no text.", link.offset, link.href)
            return
        for image in link.images:
            if image.alt is None:
                label = image.src.rsplit("/", 1)[-1] or "image"
                self._add(
                    "image-no-alt", "problem", "An image has no alt text.", image.offset, label
                )
        if not link.aria_label and _looks_like_address(text, link.href) and not alts:
            self._add(
                "link-text-is-address",
                "problem",
                "A link's text is the web address, which a screen reader spells out.",
                link.offset,
                excerpt,
            )
        elif not link.aria_label and text.casefold().strip(" .:!>»→") in _VAGUE_LINK_TEXT:
            self._add(
                "link-vague-text",
                "problem",
                f'A link says only "{text}", which means nothing out of context.',
                link.offset,
                excerpt,
            )
        if link.target == "_blank" and not any(p in name.casefold() for p in _NEW_TAB_PHRASES):
            self._add(
                "link-new-tab-unsaid",
                "check",
                'A link opens a new tab without saying "(opens in a new tab)".',
                link.offset,
                excerpt,
                fixable=True,
            )
        if has_decorative_symbol(text):
            self._add(
                "link-has-emoji",
                "check",
                "A link's text has an emoji or symbol, which a screen reader reads out by name.",
                link.offset,
                excerpt,
            )

    def _end_heading(self, heading: _Heading) -> None:
        text = " ".join("".join(heading.text).split())
        level = heading.level
        if level == 1:
            self._add(
                "heading-1-in-body",
                "problem",
                "There is a Heading 1 in the post; the theme already shows the title as one.",
                heading.offset,
                text,
                fixable=True,
            )
        elif level > self._last_heading_level + 1:
            previous = self._last_heading_level
            source = "the title" if previous == 1 else f"Heading {previous}"
            self._add(
                "heading-skips-level",
                "problem",
                f"A heading jumps from {source} to Heading {level}, skipping a level.",
                heading.offset,
                text,
                fixable=True,
            )
        self._last_heading_level = level
        if has_decorative_symbol(text):
            self._add(
                "heading-has-emoji",
                "check",
                "A heading has an emoji or symbol, which a screen reader reads out by name.",
                heading.offset,
                text,
            )

    def _end_table(self, table: _Table) -> None:
        if not table.has_header:
            self._add(
                "table-no-header",
                "problem",
                "A table has no header row, so its cells cannot be read with their headings.",
                table.offset,
                "table",
            )
        if not table.has_caption:
            self._add(
                "table-no-caption",
                "check",
                "A table has no caption to say what it is.",
                table.offset,
                "table",
            )

    def _end_colour_span(self, span: _ColourSpan) -> None:
        text = " ".join("".join(span.text).split())
        words = text.split()
        if span.emphasised or not words or len(words) > _COLOUR_ALONE_MAX_WORDS:
            return
        self._add(
            "colour-alone",
            "check",
            f'The words "{text}" are set apart only by colour; '
            "consider saying it in words or making it bold too.",
            span.offset,
            text,
        )


def check_content(
    html: str, *, title: str, site_name: str = "", default_site_name: str = ""
) -> list[Finding]:
    """Run every Check Before Publishing check over a post's HTML body.

    ``title`` is the post title (an empty one is a problem). When both site
    names are given and differ, a ``check`` names the site the post is going
    to. Findings come back in document order, document-wide ones first.
    """
    findings: list[Finding] = []
    if not title.strip():
        findings.append(Finding("title-empty", "problem", "The post has no title.", 0, ""))
    site = site_name.strip()
    default = default_site_name.strip()
    if site and default and site.casefold() != default.casefold():
        findings.append(
            Finding(
                "site-not-default",
                "check",
                f"This goes to {site}, not your default site, {default}.",
                0,
                site,
            )
        )
    checker = _Checker(html)
    checker.feed(html)
    checker.close()
    findings.extend(sorted(checker.findings, key=lambda f: f.offset))
    return findings


def _count(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def summary_line(findings: list[Finding]) -> str:
    """The one line Publish speaks: "Ready to publish: no problems found", or
    "2 things to look at: 1 problem, 1 to check"."""
    if not findings:
        return "Ready to publish: no problems found"
    problems = sum(1 for f in findings if f.severity == "problem")
    checks = len(findings) - problems
    parts: list[str] = []
    if problems:
        parts.append(_count(problems, "problem", "problems"))
    if checks:
        parts.append(f"{checks} to check")
    return f"{_count(len(findings), 'thing', 'things')} to look at: {', '.join(parts)}"
