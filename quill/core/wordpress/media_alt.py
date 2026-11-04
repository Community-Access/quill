"""Pictures inside a WordPress document: which one, its words, its size (wordpress.md 6.5, 6.8).

wx-free and strict-typed. Builds on :mod:`quill.core.ai.doc_images`, which
already finds every Markdown and HTML image and rewrites one image's alt
text; this adds what the WordPress media commands need on top: the picture
at the caret, the text around it for Suggest Alt Text, the Alt Text Review's
judgement of each one, Decorative, and swapping a picture's address and
width for Image Size and Make a Smaller Copy.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from quill.core.ai.doc_images import DocImage, list_document_images, with_alt_text

__all__ = [
    "DESCRIBE_QUESTION",
    "AltReviewRow",
    "ImageContext",
    "alt_problem",
    "alt_text_question",
    "clean_suggestion",
    "image_at",
    "image_context",
    "is_decorative",
    "mark_decorative",
    "media_id_in",
    "review_rows",
    "set_alt",
    "with_source",
]

#: Longer than this and alt text is probably a description in the wrong place.
LONG_ALT = 150

#: Describe Image's question (6.8): for the writer, not for visitors.
DESCRIBE_QUESTION = (
    "Describe this picture for the person who is about to publish it, who may not be able "
    "to see it. Cover, in plain sentences: the subject; how it is arranged; the colours and "
    "lighting; any visible text, quoted exactly; the mood; and any problems, such as awkward "
    "cropping, distorted hands or faces, garbled lettering, a crowded composition, or a "
    "resolution too low for its size. Do not invent names for people."
)


def image_at(text: str, offset: int) -> DocImage | None:
    """The image whose markup contains *offset*, or the one on the caret's line."""
    images = list_document_images(text)
    for image in images:
        if image.start <= offset <= image.end:
            return image
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    line_end = len(text) if line_end < 0 else line_end
    for image in images:
        if line_start <= image.start <= line_end:
            return image
    return None


def media_id_in(text: str, image: DocImage) -> int:
    """The library id written beside an image (``{id=N}`` or ``wp-image-N``), else 0."""
    markup = text[image.start : image.end]
    match = re.search(r"wp-image-(\d+)", markup)
    if match:
        return int(match.group(1))
    after = re.match(r"\s?\{id=(\d+)\}", text[image.end : image.end + 20])
    if after:
        return int(after.group(1))
    before = text[max(0, image.start - 300) : image.start]
    openers = list(re.finditer(r"<!--\s*wp:image\s+\{[^}]*\"id\":\s*(\d+)", before))
    if not openers or "/wp:image" in before[openers[-1].end() :]:
        return 0
    return int(openers[-1].group(1))


def is_decorative(text: str, image: DocImage) -> bool:
    markup = text[image.start : image.end]
    return (
        image.kind == "html"
        and re.search(r"role\s*=\s*['\"](presentation|none)['\"]", markup, re.I) is not None
    )


def set_alt(text: str, image: DocImage, alt: str) -> str:
    """*text* with *image*'s alt text set, and any Decorative mark taken off."""
    revised = with_alt_text(text, image.number, alt)
    if image.kind == "html" and alt.strip():
        fresh = list_document_images(revised)[image.number - 1]
        markup = revised[fresh.start : fresh.end]
        cleaned = re.sub(r"\s+role\s*=\s*['\"](presentation|none)['\"]", "", markup, flags=re.I)
        revised = revised[: fresh.start] + cleaned + revised[fresh.end :]
    return revised


def mark_decorative(text: str, image: DocImage) -> str:
    """Empty alt text on purpose; HTML also gets ``role="presentation"``."""
    revised = with_alt_text(text, image.number, "")
    if image.kind != "html":
        return revised
    fresh = list_document_images(revised)[image.number - 1]
    markup = revised[fresh.start : fresh.end]
    if re.search(r"\brole\s*=", markup, re.I):
        return revised
    marked = re.sub(r"^<img\b", '<img role="presentation"', markup, count=1, flags=re.I)
    return revised[: fresh.start] + marked + revised[fresh.end :]


def with_source(text: str, image: DocImage, source: str, width: int = 0) -> str:
    """*text* with *image* pointing at *source*, at *width* pixels when HTML says widths."""
    markup = text[image.start : image.end]
    revised = markup.replace(image.source, source, 1)
    if image.kind == "html":
        if re.search(r"\bwidth\s*=", revised, re.I):
            if width:
                revised = re.sub(
                    r"\bwidth\s*=\s*(['\"]).*?\1", f'width="{width}"', revised, count=1, flags=re.I
                )
            else:
                revised = re.sub(r"\s+width\s*=\s*(['\"]).*?\1", "", revised, count=1, flags=re.I)
            revised = re.sub(r"\s+height\s*=\s*(['\"]).*?\1", "", revised, count=1, flags=re.I)
        elif width:
            revised = re.sub(r"^<img\b", f'<img width="{width}"', revised, count=1, flags=re.I)
    return text[: image.start] + revised + text[image.end :]


# --------------------------------------------------------------------------- #
# The Alt Text Review (6.8)


def alt_problem(alt: str, source: str) -> str:
    """What is wrong with *alt* for a picture at *source*, or "" when nothing is."""
    words = alt.strip()
    if not words:
        return "no alternative text"
    name = unquote(urlparse(source).path.rsplit("/", 1)[-1]).lower()
    lowered = words.lower()
    if lowered == name or re.fullmatch(
        r"[\w\-]+\.(jpe?g|png|gif|webp|svg|heic|bmp|tiff?)", lowered
    ):
        return "looks like a file name"
    if re.fullmatch(r"(img|dsc|image|photo|pxl|screenshot)[\s_\-]?\d+.*", lowered):
        return "looks like a file name"
    if len(words) > LONG_ALT:
        return f"long, {len(words)} characters"
    if re.match(r"(an?\s+)?(image|picture|photo|graphic)\s+of\b", lowered):
        return "starts with 'image of'"
    return ""


@dataclass(frozen=True)
class AltReviewRow:
    image: DocImage
    problem: str
    decorative: bool

    def spoken(self) -> str:
        if self.decorative:
            said = "decorative"
        elif self.problem:
            said = self.problem
            if self.image.alt_text.strip():
                said += f": {self.image.alt_text.strip()}"
        else:
            said = self.image.alt_text.strip()
        return f"{self.image.number}. {self.image.name}: {said}"


def review_rows(text: str) -> list[AltReviewRow]:
    rows = []
    for image in list_document_images(text):
        decorative = is_decorative(text, image)
        problem = "" if decorative else alt_problem(image.alt_text, image.source)
        rows.append(AltReviewRow(image, problem, decorative))
    return rows


# --------------------------------------------------------------------------- #
# Suggest Alt Text (6.8)


@dataclass(frozen=True)
class ImageContext:
    heading: str = ""
    before: str = ""
    after: str = ""
    caption: str = ""
    link: str = ""


_HEADING_MD = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.M)
_HEADING_HTML = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.I | re.S)


def _plain(markup: str) -> str:
    no_comments = re.sub(r"<!--.*?-->", " ", markup, flags=re.S)
    no_images = re.sub(r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>", " ", no_comments, flags=re.I)
    no_tags = re.sub(r"<[^>]+>", " ", no_images)
    return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()


def _paragraphs(chunk: str) -> list[str]:
    parts = re.split(r"\n\s*\n|</p>|<p[^>]*>", chunk, flags=re.I)
    return [p for p in (_plain(x) for x in parts) if p and not p.startswith("#")]


def image_context(text: str, image: DocImage) -> ImageContext:
    """The heading above *image*, a paragraph either side, its caption and link."""
    before_text = text[: image.start]
    after_text = re.sub(r"^\s?\{id=\d+\}", "", text[image.end :])
    headings = [(m.start(), m.group(1)) for m in _HEADING_MD.finditer(before_text)]
    headings += [(m.start(), m.group(1)) for m in _HEADING_HTML.finditer(before_text)]
    heading = _plain(max(headings)[1]) if headings else ""
    before = _paragraphs(before_text)
    after = _paragraphs(re.sub(r"^.*?</figure>", "", after_text, count=1, flags=re.S))
    caption = ""
    markup = text[image.start : image.end]
    title = re.search(r'\s"([^"]+)"\)$', markup)
    if title:
        caption = title.group(1)
    figcaption = re.match(
        r"\s*(?:</a>)?\s*<figcaption[^>]*>(.*?)</figcaption>", after_text, re.I | re.S
    )
    if figcaption:
        caption = _plain(figcaption.group(1))
    link = ""
    opener = re.search(r"<a\b[^>]*href\s*=\s*(['\"])(.*?)\1[^>]*>\s*$", before_text, re.I)
    if opener:
        link = opener.group(2)
    return ImageContext(
        heading=heading[:200],
        before=(before[-1] if before else "")[:800],
        after=(after[0] if after else "")[:800],
        caption=caption[:300],
        link=link,
    )


def alt_text_question(context: ImageContext) -> str:
    """The instruction Suggest Alt Text gives the AI, with the words around the picture."""
    lines = [
        "Propose alternative text for this picture on a web page, for visitors using a screen "
        "reader. Answer with the alternative text only.",
        "Rules: one or two sentences on what the picture contributes here, not a list of its "
        "pixels. Read out any visible text exactly. Do not begin with 'image of' or 'picture "
        "of'. Do not invent names: if a person is shown and the page does not name them, say "
        "'a person'. If it is a chart or diagram, give a short summary and end with the line "
        "'FULLER DESCRIPTION:' followed by a paragraph that gives the data. If the picture is "
        "purely decorative, such as a divider or a texture, answer exactly 'DECORATIVE'.",
    ]
    if context.heading:
        lines.append(f"The heading above it: {context.heading}")
    if context.before:
        lines.append(f"The paragraph before it: {context.before}")
    if context.after:
        lines.append(f"The paragraph after it: {context.after}")
    if context.caption:
        lines.append(f"Its caption: {context.caption}")
    if context.link:
        lines.append(
            f"It is a link to {context.link}, so the alternative text must say where it goes."
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class Suggestion:
    alt: str
    decorative: bool = False
    fuller: str = ""


def clean_suggestion(answer: str) -> Suggestion:
    """The AI's answer as a proposal: quotes and 'image of' taken off, markers read."""
    text = answer.strip()
    fuller = ""
    marker = re.search(r"FULLER DESCRIPTION:\s*", text, re.I)
    if marker:
        fuller = text[marker.end() :].strip()
        text = text[: marker.start()].strip()
    if re.fullmatch(r"['\"]?decorative['\".]?", text, re.I):
        return Suggestion("", decorative=True)
    text = re.sub(r"^(alt(ernative)? text|alt)\s*:\s*", "", text, flags=re.I)
    text = text.strip().strip("\"'").strip()
    text = re.sub(r"^(an?\s+)?(image|picture|photo|photograph)\s+of\s+", "", text, flags=re.I)
    if text:
        text = text[0].upper() + text[1:]
    return Suggestion(" ".join(text.split()), fuller=fuller)
