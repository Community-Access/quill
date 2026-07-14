"""Text extraction and TTS polishing for batch speech export.

Extracts human-readable text from Markdown, HTML, and Word (.docx) files,
then applies a polish pipeline to improve TTS output quality.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

__all__ = [
    "extract_text",
    "extract_sections",
    "combine_heading_only_sections",
    "DocumentSection",
    "polish_for_tts",
    "UnsupportedFormatError",
]

_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# Abbreviations that trip up TTS (period causes a pause mid-word).
_ABBREV_MAP: dict[str, str] = {
    r"\bDr\.": "Doctor",
    r"\bMr\.": "Mister",
    r"\bMrs\.": "Missus",
    r"\bMs\.": "Miss",
    r"\bProf\.": "Professor",
    r"\bSr\.": "Senior",
    r"\bJr\.": "Junior",
    r"\betc\.": "et cetera",
    r"\bvs\.": "versus",
    r"\be\.g\.": "for example",
    r"\bi\.e\.": "that is",
    r"\ba\.k\.a\.": "also known as",
    r"\bapprox\.": "approximately",
    r"\bmax\.": "maximum",
    r"\bmin\.": "minimum",
    r"\bno\.": "number",
    r"\bvol\.": "volume",
    r"\bfig\.": "figure",
}

# URL pattern — replace with "link" to avoid TTS spelling out h-t-t-p-s.
_URL_RE = re.compile(
    r"https?://\S+|www\.\S+",
    re.IGNORECASE,
)

# Markdown code fence (```...```) — skip the content entirely.
_CODE_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
# Inline code — strip backticks but keep text.
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
# ATX headings — keep the text, drop the # markers.
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
# Bold / italic — keep text.
_BOLD_ITALIC_RE = re.compile(r"\*{1,3}(.+?)\*{1,3}|_{1,3}(.+?)_{1,3}")
# Markdown links — keep the label, drop URL.
_MD_LINK_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)")
# Horizontal rules and setext headings underlines.
_HR_RE = re.compile(r"^[-=*]{3,}\s*$", re.MULTILINE)
# HTML within Markdown.
_HTML_TAG_RE = re.compile(r"<[^>]+>")
# Excess blank lines.
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


class UnsupportedFormatError(ValueError):
    """Raised when a file extension has no extractor."""


class _TextCollector(HTMLParser):
    """Minimal HTMLParser subclass that collects visible text."""

    _SKIP_TAGS = frozenset({"script", "style", "head", "noscript", "template", "svg", "math"})

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def result(self) -> str:
        return "".join(self._parts)


def _clean_markdown(raw: str) -> str:
    # Remove fenced code blocks first (before heading expansion).
    text = _CODE_FENCE_RE.sub("\n", raw)
    # Expand headings to plain text.
    text = _HEADING_RE.sub(r"\1", text)
    # Inline code — keep text only.
    text = _INLINE_CODE_RE.sub(r"\1", text)
    # Images — keep alt text or drop.
    text = _MD_LINK_RE.sub(lambda m: m.group(1) or m.group(2) or "", text)
    # Bold / italic — keep text.
    text = _BOLD_ITALIC_RE.sub(lambda m: m.group(1) or m.group(2) or "", text)
    # Remaining HTML tags.
    text = _HTML_TAG_RE.sub("", text)
    # Horizontal rules.
    text = _HR_RE.sub("", text)
    return text


def _extract_markdown(path: Path) -> str:
    return _clean_markdown(path.read_text(encoding="utf-8", errors="replace"))


def clean_markdown_text(raw: str) -> str:
    """Strip Markdown syntax from *raw*, keeping only its readable text.

    Public entry point to the same sanitizer :func:`_extract_markdown` applies
    to ``.md`` files, for callers that already hold text in memory (a live
    editor buffer, a single sentence) rather than a file path. Synthesis
    engines that phonemize input character-by-character (Piper's espeak-ng
    backend) badly mis-tokenize literal ``#``/``**``/``[text](url)`` syntax,
    so every text-to-speech path should route through this before synthesis.
    """
    return _clean_markdown(raw)


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = _TextCollector()
    parser.feed(raw)
    return parser.result()


def _localname(tag: str) -> str:
    """The local element name without its namespace (``{ns}p`` -> ``p``)."""
    return tag.rsplit("}", 1)[-1]


def _docx_table_rows(tbl: ET.Element) -> list[str]:
    """One spoken line per table row: the row's cell texts joined by ', '."""
    rows: list[str] = []
    for row in tbl.findall(f"{{{_WORD_NS}}}tr"):
        cells: list[str] = []
        for cell in row.findall(f"{{{_WORD_NS}}}tc"):
            cell_text = " ".join(
                t for p in cell.findall(f"{{{_WORD_NS}}}p") if (t := _docx_paragraph_text(p))
            )
            if cell_text:
                cells.append(cell_text)
        if cells:
            rows.append(", ".join(cells))
    return rows


def _docx_block_lines(body: ET.Element) -> list[tuple[int, str]]:
    """Walk a body's blocks in order, yielding ``(heading_level, text)`` lines.

    ``heading_level`` is 0 for body text and 1-9 for headings (truthy exactly
    when the line is a heading, so boolean callers keep working). A table
    yields one line per row (cells joined by ``", "``) so a data table reads
    sensibly instead of a jumble of cell fragments. Direct children only, so a
    paragraph inside a table cell is read as part of its row, not twice.
    """
    out: list[tuple[int, str]] = []
    for child in body:
        tag = _localname(child.tag)
        if tag == "p":
            text = _docx_paragraph_text(child)
            if text:
                out.append((_docx_paragraph_heading_level(child), text))
        elif tag == "tbl":
            out.extend((0, row) for row in _docx_table_rows(child))
    return out


def _docx_part_paragraphs(zf: zipfile.ZipFile, name: str) -> list[str]:
    """All non-empty paragraph texts from a docx part (header/footer XML)."""
    try:
        with zf.open(name) as fh:
            tree = ET.parse(fh)
    except (KeyError, ET.ParseError):
        return []
    return [t for p in tree.getroot().iter(f"{{{_WORD_NS}}}p") if (t := _docx_paragraph_text(p))]


def _docx_footnotes(zf: zipfile.ZipFile) -> list[str]:
    """Real footnote texts (skipping the separator/continuation placeholders)."""
    if "word/footnotes.xml" not in zf.namelist():
        return []
    try:
        with zf.open("word/footnotes.xml") as fh:
            tree = ET.parse(fh)
    except ET.ParseError:
        return []
    notes: list[str] = []
    for note in tree.getroot().findall(f"{{{_WORD_NS}}}footnote"):
        if note.get(f"{{{_WORD_NS}}}type") in {"separator", "continuationSeparator"}:
            continue
        text = " ".join(t for p in note.iter(f"{{{_WORD_NS}}}p") if (t := _docx_paragraph_text(p)))
        if text:
            notes.append(text)
    return notes


def _docx_body(root: ET.Element) -> ET.Element:
    body = root.find(f"{{{_WORD_NS}}}body")
    return body if body is not None else root


def _extract_docx(path: Path) -> str:
    """Extract readable text from a Word .docx: paragraphs, tables (row by row),
    footnotes, and header/footer text — using stdlib only."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            with zf.open("word/document.xml") as fh:
                tree = ET.parse(fh)
            parts = [text for _is_heading, text in _docx_block_lines(_docx_body(tree.getroot()))]
            # Header/footer text (stored once per section, not per page): include
            # distinct, non-trivial lines so running titles/captions are not lost.
            seen: set[str] = set()
            for name in sorted(zf.namelist()):
                base = name.rsplit("/", 1)[-1]
                if base.startswith(("header", "footer")) and base.endswith(".xml"):
                    for line in _docx_part_paragraphs(zf, name):
                        if len(line) > 1 and not line.isdigit() and line not in seen:
                            seen.add(line)
                            parts.append(line)
            parts.extend(_docx_footnotes(zf))
    except (zipfile.BadZipFile, ET.ParseError):
        return ""
    return "\n".join(parts)


def _extract_txt(path: Path) -> str:
    """Plain text is returned as-is (decoded permissively). Has no headings."""
    return path.read_text(encoding="utf-8", errors="replace")


# --- Heading-aware section extraction (§4.8.2) ---------------------------- #


@dataclass(slots=True)
class DocumentSection:
    """One heading-delimited part of a document: the heading and its body text.

    ``title`` is the heading text, or ``""`` for the lead-in before the first
    heading (the caller substitutes the configured intro title) and for formats
    or documents that have no headings (a single whole-document section).
    ``level`` is the heading's outline level (1-6 for Markdown/HTML, 1-9 for
    Word), or 0 for the lead-in/whole-document case — it powers the batch
    export's "chapters start at heading level" choice.
    """

    title: str
    text: str
    level: int = 0


# ATX (``## Heading``) and the heading line as a whole, captured separately.
_ATX_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$", re.MULTILINE)
# Setext heading: a non-blank text line immediately followed by === or --- .
_SETEXT_HEADING_RE = re.compile(r"^(?P<title>[^\n]+)\n(?P<rule>=+|-+)[ \t]*$", re.MULTILINE)


def _sections_from_markdown(raw: str) -> list[DocumentSection]:
    # Normalise setext headings to ATX so a single splitter handles both.
    def _setext_to_atx(m: re.Match[str]) -> str:
        level = "#" if m.group("rule").startswith("=") else "##"
        return f"{level} {m.group('title').strip()}"

    normalised = _SETEXT_HEADING_RE.sub(_setext_to_atx, raw)
    matches = list(_ATX_HEADING_RE.finditer(normalised))
    if not matches:
        return [DocumentSection("", _clean_markdown(normalised))]

    sections: list[DocumentSection] = []
    lead_in = normalised[: matches[0].start()]
    if lead_in.strip():
        sections.append(DocumentSection("", _clean_markdown(lead_in)))
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(normalised)
        body = _clean_markdown(normalised[body_start:body_end])
        sections.append(DocumentSection(title, body, level=len(m.group(1))))
    return sections


class _HtmlSectionizer(HTMLParser):
    """Collects visible text, splitting into sections at h1–h6 boundaries."""

    _SKIP_TAGS = _TextCollector._SKIP_TAGS
    _HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
    _BREAKS = frozenset({"p", "div", "li", "br", "tr"})

    def __init__(self) -> None:
        super().__init__()
        self._sections: list[DocumentSection] = []
        self._cur_title = ""
        self._cur_level = 0
        self._cur_parts: list[str] = []
        self._skip_depth = 0
        self._in_heading = False
        self._heading_parts: list[str] = []

    def _flush(self) -> None:
        text = "".join(self._cur_parts).strip()
        if self._cur_title or text:
            self._sections.append(DocumentSection(self._cur_title, text, level=self._cur_level))
        self._cur_parts = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        t = tag.lower()
        if t in self._SKIP_TAGS:
            self._skip_depth += 1
        elif t in self._HEADINGS:
            self._flush()  # close the previous section
            self._cur_title = ""
            self._cur_level = int(t[1])  # "h3" -> 3
            self._in_heading = True
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif t in self._HEADINGS and self._in_heading:
            self._cur_title = "".join(self._heading_parts).strip()
            self._in_heading = False
        elif t in self._BREAKS:
            self._cur_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_heading:
            self._heading_parts.append(data)
        else:
            self._cur_parts.append(data)

    def result(self) -> list[DocumentSection]:
        self._flush()
        return self._sections


def _sections_from_html(raw: str) -> list[DocumentSection]:
    parser = _HtmlSectionizer()
    parser.feed(raw)
    sections = parser.result()
    if not sections:
        return [DocumentSection("", "")]
    # No headings at all → one whole-document section.
    if all(not s.title for s in sections):
        joined = "\n".join(s.text for s in sections if s.text).strip()
        return [DocumentSection("", joined)]
    return sections


# Word heading paragraphs carry a pStyle whose val is "Heading1".."Heading9",
# "Title", or a localized equivalent; outline level (w:outlineLvl) is the robust
# fallback. We treat any of these as a section boundary.
_WORD_HEADING_STYLE_RE = re.compile(r"^(heading[1-9]|title)$", re.IGNORECASE)


def _docx_paragraph_heading_level(para: ET.Element) -> int:
    """The paragraph's heading level (1-9; "Title" counts as 1), or 0 for body."""
    ppr = para.find(f"{{{_WORD_NS}}}pPr")
    if ppr is None:
        return 0
    style = ppr.find(f"{{{_WORD_NS}}}pStyle")
    if style is not None:
        val = style.get(f"{{{_WORD_NS}}}val", "").replace(" ", "")
        if _WORD_HEADING_STYLE_RE.match(val):
            digits = "".join(ch for ch in val if ch.isdigit())
            return int(digits) if digits else 1
    outline = ppr.find(f"{{{_WORD_NS}}}outlineLvl")
    if outline is not None:
        level = outline.get(f"{{{_WORD_NS}}}val")
        if level is not None and level.isdigit():
            return int(level) + 1  # outlineLvl is 0-based
    return 0


def _docx_paragraph_text(para: ET.Element) -> str:
    return "".join(node.text for node in para.iter(f"{{{_WORD_NS}}}t") if node.text).strip()


def _sections_from_docx(path: Path) -> list[DocumentSection]:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return [DocumentSection("", "")]
            with zf.open("word/document.xml") as fh:
                tree = ET.parse(fh)
    except (zipfile.BadZipFile, ET.ParseError):
        return [DocumentSection("", "")]

    sections: list[DocumentSection] = []
    cur_title = ""
    cur_level = 0
    cur_lines: list[str] = []
    started = False

    def flush() -> None:
        text = "\n".join(cur_lines).strip()
        if cur_title or text:
            sections.append(DocumentSection(cur_title, text, level=cur_level))

    # Structured walk: headings start sections; tables read row by row.
    for heading_level, line in _docx_block_lines(_docx_body(tree.getroot())):
        if heading_level:
            flush()
            cur_title = line
            cur_level = heading_level
            cur_lines = []
            started = True
        else:
            cur_lines.append(line)
    flush()

    # Footnotes become a trailing section so an audiobook still reads them.
    try:
        with zipfile.ZipFile(path, "r") as zf:
            footnotes = _docx_footnotes(zf)
    except zipfile.BadZipFile:
        footnotes = []
    if footnotes:
        sections.append(DocumentSection("Footnotes", "\n".join(footnotes)))
        started = True

    if not sections:
        return [DocumentSection("", "")]
    if not started:  # no heading paragraphs at all
        return [DocumentSection("", "\n".join(s.text for s in sections if s.text).strip())]
    return sections


def combine_heading_only_sections(sections: list[DocumentSection]) -> list[DocumentSection]:
    """Merge heading-only sections into the next section that has body text.

    Mirrors the ACB audio-pipeline rule ("combine consecutive headings; only create
    an article when body text is found"): a heading with no body folds into the next
    article that does have body, and the combined title joins the run of headings
    (``"Part One: Chapter 1"``). A trailing run of bodyless headings becomes one
    heading-only section so nothing is lost. Used when the user enables
    *combine empty headings* for a batch run.
    """
    out: list[DocumentSection] = []
    pending: list[str] = []  # heading titles still awaiting a body
    for section in sections:
        if not section.text.strip():
            if section.title.strip():
                pending.append(section.title.strip())
            continue
        if pending:
            parts = [p for p in (*pending, section.title.strip()) if p]
            out.append(DocumentSection(": ".join(parts), section.text))
            pending = []
        else:
            out.append(section)
    if pending:
        out.append(DocumentSection(": ".join(pending), ""))
    return out


def fold_sections_below_level(
    sections: list[DocumentSection], max_level: int
) -> list[DocumentSection]:
    """Fold sections deeper than *max_level* into the chapter above them.

    Powers "chapters start at heading level N": a section whose heading level
    is known (non-zero) and deeper than *max_level* stops being its own
    chapter — its heading line and body are appended to the preceding
    section's text, so nothing is lost, only the boundary. ``max_level <= 0``
    means "every heading is a chapter" (the historical behavior). A deep
    section with nothing before it (document starts at h3) keeps its own
    chapter rather than vanishing.
    """
    if max_level <= 0:
        return sections
    folded: list[DocumentSection] = []
    for section in sections:
        if folded and section.level > max_level:
            prev = folded[-1]
            addition = f"{section.title}\n{section.text}".strip()
            prev.text = f"{prev.text}\n\n{addition}".strip()
        else:
            folded.append(DocumentSection(section.title, section.text, level=section.level))
    return folded


def extract_sections(
    path: Path, *, combine_headings: bool = False, max_heading_level: int = 0
) -> list[DocumentSection]:
    """Split a document into heading-delimited sections (§4.8.2).

    Markdown, HTML, and Word headings become section boundaries; the heading text
    becomes the section title. Plain text (and any document without headings)
    returns a single section with an empty title. Each section's ``text`` is the
    same cleaned plain text :func:`extract_text` produces, scoped to that section.

    When *combine_headings* is set, heading-only sections are folded into the next
    section with body via :func:`combine_heading_only_sections` (an opt-in batch
    setting), so an article is only emitted where there is something to speak.
    When *max_heading_level* is positive, deeper headings stop starting chapters
    (:func:`fold_sections_below_level`); the two folds compose, level first.
    """
    suffix = path.suffix.lower()
    if suffix == ".txt":
        sections = [DocumentSection("", _extract_txt(path))]
    elif suffix == ".md":
        sections = _sections_from_markdown(path.read_text(encoding="utf-8", errors="replace"))
    elif suffix in {".html", ".htm"}:
        sections = _sections_from_html(path.read_text(encoding="utf-8", errors="replace"))
    elif suffix == ".docx":
        sections = _sections_from_docx(path)
    else:
        raise UnsupportedFormatError(f"No extractor for {suffix!r}")
    sections = fold_sections_below_level(sections, max_heading_level)
    return combine_heading_only_sections(sections) if combine_headings else sections


def preview_chapter_titles(
    paths: list[Path],
    *,
    combine_headings: bool = False,
    max_heading_level: int = 0,
    limit: int = 20,
    intro_title: str = "Introduction",
) -> list[str]:
    """The first *limit* chapter titles a batch run over *paths* would produce.

    Powers the wizard's "Preview chapter titles" audit: the user hears how the
    heading-level choice will carve their real documents before committing to
    a long run. Unreadable documents are skipped (the run itself reports them).
    """
    titles: list[str] = []
    for path in paths:
        try:
            sections = extract_sections(
                path, combine_headings=combine_headings, max_heading_level=max_heading_level
            )
        except (OSError, UnsupportedFormatError):
            continue
        for section in sections:
            titles.append(section.title or intro_title)
            if len(titles) >= limit:
                return titles
    return titles


def extract_text(path: Path) -> str:
    """Return raw text from a plain-text, Markdown, HTML, or Word file."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _extract_txt(path)
    if suffix == ".md":
        return _extract_markdown(path)
    if suffix in {".html", ".htm"}:
        return _extract_html(path)
    if suffix == ".docx":
        return _extract_docx(path)
    raise UnsupportedFormatError(f"No extractor for {suffix!r}")


def polish_for_tts(text: str) -> str:
    """Apply TTS-quality improvements to extracted text."""
    # Replace URLs before any other substitution.
    text = _URL_RE.sub("link", text)
    # Expand abbreviations.
    for pattern, replacement in _ABBREV_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Collapse excess whitespace within lines.
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(lines)
    # Collapse 3+ blank lines to 2 (paragraph pause).
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()
