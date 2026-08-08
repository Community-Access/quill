from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from quill.core.safe_archive import open_zip
from quill.core.safe_xml import UnsafeXMLError
from quill.core.safe_xml import fromstring as safe_xml_fromstring

_HTML_HEADING_PATTERN = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
#: Block elements we consider as candidate *inferred* headings when a chapter
#: carries no true <h1>-<h6> markup (common in older/hand-made EPUBs).
_BLOCK_PATTERN = re.compile(r"<(p|div)\b([^>]*)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_CLASS_PATTERN = re.compile(r'class\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
#: A block whose entire visible text is wrapped in one bold run is a strong
#: heading signal (a centered/bold standalone line acting as a title).
_ALL_BOLD_PATTERN = re.compile(
    r"^\s*<(?:b|strong)\b[^>]*>(.*?)</(?:b|strong)>\s*$", re.IGNORECASE | re.DOTALL
)
#: Class-name keywords -> inferred heading level, most specific first.
_CLASS_LEVEL_HINTS: tuple[tuple[str, int], ...] = (
    ("h1", 1),
    ("h2", 2),
    ("h3", 3),
    ("h4", 4),
    ("h5", 5),
    ("h6", 6),
    ("chapter", 1),
    ("title", 1),
    ("subtitle", 2),
    ("section", 2),
    ("subhead", 3),
    ("heading", 2),
    ("head", 2),
)
#: An inferred (bold/short) heading must be at most this many words -- longer
#: bold runs are emphasis inside a paragraph, not a title.
_MAX_INFERRED_HEADING_WORDS = 14


@dataclass(frozen=True, slots=True)
class EpubHeading:
    level: int
    title: str


@dataclass(frozen=True, slots=True)
class EpubChapter:
    title: str
    href: str
    text: str
    headings: tuple[EpubHeading, ...] = ()
    #: Reading-order body with (true or inferred) headings kept inline as
    #: Markdown ``#`` lines, so single-key heading navigation reaches them.
    #: Falls back to ``text`` (flattened) when there is nothing to structure.
    body: str = ""
    #: True when ``headings`` were inferred from structure rather than read
    #: from real <h1>-<h6> tags.
    headings_inferred: bool = False


@dataclass(frozen=True, slots=True)
class EpubBook:
    title: str
    chapters: tuple[EpubChapter, ...]


def load_epub_book(path: Path) -> EpubBook:
    with open_zip(path) as archive:
        chapter_files = _chapter_files(archive)
        toc = _read_toc(archive)
        title = _read_book_title(archive) or path.stem
        chapters: list[EpubChapter] = []
        ordered = toc if toc else [(Path(name).stem, name) for name in chapter_files]
        for label, href in ordered:
            matched = _resolve_href(chapter_files, href)
            if matched is None:
                continue
            content = archive.read(matched).decode("utf-8", errors="ignore")
            text = _extract_text(content)
            true_spans = _true_heading_spans(content)
            inferred = False
            spans = true_spans
            if not spans:
                spans = _infer_heading_spans(content)
                inferred = bool(spans)
            headings = tuple(
                EpubHeading(level=level, title=title) for _s, _e, level, title in spans
            )
            body = _render_chapter_body(content, spans) if spans else text
            chapters.append(
                EpubChapter(
                    title=label or Path(matched).stem,
                    href=matched,
                    text=text,
                    headings=headings,
                    body=body,
                    headings_inferred=inferred,
                )
            )
    return EpubBook(title=title, chapters=tuple(chapters))


def render_epub_book(book: EpubBook) -> str:
    lines = [f"# EPUB: {book.title}", ""]
    if not book.chapters:
        lines.append("(no chapters)")
        return "\n".join(lines) + "\n"
    for index, chapter in enumerate(book.chapters, start=1):
        lines.append(f"## {index}. {chapter.title}")
        lines.append(chapter.body or chapter.text or "(empty chapter)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _chapter_files(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name for name in archive.namelist() if name.lower().endswith((".xhtml", ".html", ".htm"))
    )


def _read_toc(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    toc_entries: list[tuple[str, str]] = []
    toc_names = [name for name in archive.namelist() if name.lower().endswith(".ncx")]
    for toc_name in toc_names:
        xml_text = archive.read(toc_name).decode("utf-8", errors="ignore")
        try:
            root = safe_xml_fromstring(xml_text)
        except (ET.ParseError, UnsafeXMLError):
            continue
        namespace = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
        for navpoint in root.findall(".//ncx:navPoint", namespace):
            label = "".join(
                node.text or "" for node in navpoint.findall("./ncx:navLabel/ncx:text", namespace)
            ).strip()
            content = navpoint.find("./ncx:content", namespace)
            if content is None:
                continue
            src = content.attrib.get("src", "").strip()
            if src:
                toc_entries.append((label, src))
    return toc_entries


def _read_book_title(archive: zipfile.ZipFile) -> str | None:
    opf_names = [name for name in archive.namelist() if name.lower().endswith(".opf")]
    for opf_name in opf_names:
        xml_text = archive.read(opf_name).decode("utf-8", errors="ignore")
        try:
            root = safe_xml_fromstring(xml_text)
        except (ET.ParseError, UnsafeXMLError):
            continue
        namespace = {"dc": "http://purl.org/dc/elements/1.1/"}
        title_node = root.find(".//dc:title", namespace)
        if title_node is not None and title_node.text:
            candidate = title_node.text.strip()
            if candidate:
                return candidate
    return None


def _resolve_href(chapter_files: list[str], href: str) -> str | None:
    normalized = href.split("#", 1)[0].replace("\\", "/").strip()
    if not normalized:
        return None
    if normalized in chapter_files:
        return normalized
    for entry in chapter_files:
        if entry.endswith(normalized):
            return entry
    return None


_MATH_TAG_PATTERN = re.compile(r"<math\b[^>]*>.*?</math>", re.DOTALL | re.IGNORECASE)
_LATEX_TAG_PATTERN = re.compile(
    r"<(span|div)\b[^>]*\bclass\s*=\s*['\"][^'\"]*?\b(?:math|latex)\b[^'\"]*?['\"][^>]*>(.*?)</\1>",
    re.DOTALL | re.IGNORECASE,
)


def _strip_latex_delimiters(text: str) -> str:
    t = text.strip()
    if t.startswith("$$") and t.endswith("$$") and len(t) > 4:
        return t[2:-2].strip()
    if t.startswith("\\(") and t.endswith("\\)") and len(t) > 4:
        return t[2:-2].strip()
    if t.startswith("\\[") and t.endswith("\\]") and len(t) > 4:
        return t[2:-2].strip()
    if t.startswith("$") and t.endswith("$") and len(t) > 2:
        return t[1:-1].strip()
    return t


def _convert_mathml_to_speech(mathml_str: str) -> str:
    try:
        mathml_str = html.unescape(mathml_str)
        from quill.core.math.mathml import parse_mathml
        from quill.core.math.navigator import _normalize
        from quill.core.math.speech import speak

        root = parse_mathml(mathml_str)
        normalized = _normalize(root)
        return speak(normalized)
    except Exception:
        without_tags = re.sub(r"<[^>]+>", " ", mathml_str)
        decoded = html.unescape(without_tags)
        return " ".join(decoded.split())


def _convert_latex_to_speech(latex_str: str) -> str:
    try:
        latex_str = html.unescape(latex_str)
        from quill.core.math.latex_bridge import latex_to_mathml

        mathml = latex_to_mathml(latex_str)
        return _convert_mathml_to_speech(mathml)
    except Exception:
        return latex_str


def _extract_math_placeholders(content: str) -> tuple[str, dict[str, str]]:
    placeholders = {}
    counter = 0

    def math_replacer(match):
        nonlocal counter
        mathml_str = match.group(0)
        placeholder = f"___MATH_EQ_PLACEHOLDER_{counter}___"
        spoken = _convert_mathml_to_speech(mathml_str)
        placeholders[placeholder] = f"[Math Equation: {spoken}]"
        counter += 1
        return f" {placeholder} "

    def latex_replacer(match):
        nonlocal counter
        latex_str = match.group(2).strip()
        placeholder = f"___MATH_EQ_PLACEHOLDER_{counter}___"
        clean_latex = _strip_latex_delimiters(latex_str)
        spoken = _convert_latex_to_speech(clean_latex)
        placeholders[placeholder] = f"[Math Equation: {spoken}]"
        counter += 1
        return f" {placeholder} "

    content = _MATH_TAG_PATTERN.sub(math_replacer, content)
    content = _LATEX_TAG_PATTERN.sub(latex_replacer, content)
    return content, placeholders


def _process_embedded_latex_delimiters(text: str) -> str:
    def replace_latex(match):
        latex_str = match.group(1).strip()
        spoken = _convert_latex_to_speech(latex_str)
        return f" [Math Equation: {spoken}] "

    text = re.sub(r"\$\$(.*?)\$\$", replace_latex, text, flags=re.DOTALL)
    text = re.sub(r"\\\[(.*?)\\\]", replace_latex, text, flags=re.DOTALL)
    text = re.sub(r"\\\((.*?)\\\)", replace_latex, text, flags=re.DOTALL)
    return text


def _extract_text(content: str) -> str:
    content, placeholders = _extract_math_placeholders(content)
    without_tags = re.sub(r"<[^>]+>", " ", content)
    for placeholder, math_repr in placeholders.items():
        without_tags = without_tags.replace(placeholder, math_repr)
    without_tags = _process_embedded_latex_delimiters(without_tags)
    decoded = html.unescape(without_tags)
    return " ".join(decoded.split())


def _clean_inline_text(raw: str) -> str:
    """Strip inline tags and collapse whitespace to a single clean line."""
    stripped = _HTML_TAG_PATTERN.sub("", raw)
    return " ".join(html.unescape(stripped).split())


def _extract_headings(content: str) -> list[EpubHeading]:
    """Real <h1>-<h6> headings only (unchanged public behavior)."""
    return [
        EpubHeading(level=level, title=title)
        for _s, _e, level, title in _true_heading_spans(content)
    ]


def _true_heading_spans(content: str) -> list[tuple[int, int, int, str]]:
    """Positions + levels + titles of real <h1>-<h6> headings, in order."""
    spans: list[tuple[int, int, int, str]] = []
    for match in _HTML_HEADING_PATTERN.finditer(content):
        title = _clean_inline_text(match.group(2))
        if title:
            spans.append((match.start(), match.end(), int(match.group(1)), title))
    return spans


def _heading_level_from_class(class_attr: str) -> int | None:
    """Map a block's class attribute to an inferred heading level, or None."""
    lowered = class_attr.lower()
    for keyword, level in _CLASS_LEVEL_HINTS:
        if keyword in lowered:
            return level
    return None


def _infer_heading_spans(content: str) -> list[tuple[int, int, int, str]]:
    """Guess headings from block structure when no true <h1>-<h6> tags exist.

    Two conservative signals, both common in hand-made EPUBs that never used
    real heading tags: (1) a <p>/<div> whose class names it a heading/title/
    chapter/section, and (2) a short <p>/<div> whose entire visible text is one
    bold run (a centered, standalone bold line acting as a title). Body text
    and long bold emphasis are deliberately left alone.
    """
    spans: list[tuple[int, int, int, str]] = []
    for match in _BLOCK_PATTERN.finditer(content):
        attrs, inner = match.group(2), match.group(3)
        title = _clean_inline_text(inner)
        if not title:
            continue
        level: int | None = None
        class_match = _CLASS_PATTERN.search(attrs)
        if class_match:
            level = _heading_level_from_class(class_match.group(1))
        if level is None and _ALL_BOLD_PATTERN.match(inner.strip()):
            if len(title.split()) <= _MAX_INFERRED_HEADING_WORDS:
                level = 2
        if level is not None:
            spans.append((match.start(), match.end(), level, title))
    return spans


def _render_chapter_body(content: str, spans: list[tuple[int, int, int, str]]) -> str:
    """Render chapter text with headings kept inline as Markdown ``#`` lines.

    Headings are emitted two levels below the chapter (whose own title renders
    as ``##``), so the book -> chapter -> in-chapter-heading hierarchy stays
    sane and single-key ``H`` navigation can walk them.
    """
    ordered = sorted(spans, key=lambda span: span[0])
    parts: list[str] = []
    cursor = 0
    for start, end, level, title in ordered:
        pre = _extract_text(content[cursor:start])
        if pre:
            parts.append(pre)
        markers = "#" * min(level + 2, 6)
        parts.append(f"{markers} {title}")
        cursor = end
    tail = _extract_text(content[cursor:])
    if tail:
        parts.append(tail)
    return "\n\n".join(parts)
