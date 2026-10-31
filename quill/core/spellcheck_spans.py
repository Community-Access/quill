"""Which parts of a document a spell checker should read, by what the file is.

A spell checker that reads every word flags every URL, every email address,
every tag in an HTML file and every identifier in a Python file. In an essay
that is a handful of false alarms; in a web page or a script it is a wall of
them, and for a screen-reader user each one is a spoken interruption. So the
checker reads only what a person wrote *as language*:

* **Prose** (plain text, an unnamed buffer, anything not listed below):
  everything except URLs (``https://...``, ``www.``, a bare domain with a path
  or a well-known ending such as ``example.com``), email addresses and file
  paths.
* **Markdown**: the prose rule, plus inline code spans, fenced code blocks,
  inline HTML tags and link targets are skipped. Link text and image alt text
  are checked, because somebody wrote them to be read.
* **HTML and XML**: the text between tags and comments are checked. Tags,
  attribute names and attribute values are skipped, except the values of
  ``alt``, ``title``, ``aria-label``, ``aria-description`` and ``placeholder``,
  which a person reads or hears. Inside ``<script>`` and ``<style>`` only the
  string literals and comments are checked, as code.
* **Code** (Python, JavaScript and TypeScript, the C family, C#, Java, Go,
  Rust, shell, PowerShell, SQL, JSON, YAML, CSS and the rest of
  :data:`quill.core.spellcheck_filetypes.CODE_SUFFIXES`): only string literals
  and comments are checked. Inside them, URLs, paths, format placeholders
  (``{0}``, ``{name}``, ``%s``, ``${x}``), escape sequences (``\\n``) and
  identifier-shaped words (``snake_case``, ``camelCase``, anything with a digit)
  are still skipped.

The kind is decided by the file's extension -- the same rule
:mod:`quill.core.spellcheck_filetypes` uses for the live-check default, so the
two never disagree about what counts as code.

**One implementation for both editors.** QUILL and QUILL Lite both reach this
through :mod:`quill.core.spellcheck`, whose functions take the document's file
name. Offsets are never shifted: the checker either masks skipped text with
spaces (same length, newlines kept) or tests a word's range against the skipped
ranges, so navigation, live marking, replace and ignore keep the exact offsets
they always had.

Code and markup are lexed with Pygments when it is available and the document
is small enough for that to be quick; otherwise a small regex lexer per family
does the same job less precisely. Pygments is imported lazily, on the first
code file, so it costs nothing at startup. wx-free and pure.
"""

from __future__ import annotations

import bisect
import re
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from quill.core.spellcheck_filetypes import CODE_SUFFIXES
from quill.core.spellcheck_lexers import (
    _CODE_TEXT_SKIP,
    _LEXER_CACHE,
    READABLE_ATTRIBUTES,
    _pygments_lexer,
    _pygments_spans,
    _regex_code_spans,
    _regex_markup_spans,
    _subtract,
)

__all__ = [
    "MARKDOWN_SUFFIXES",
    "READABLE_ATTRIBUTES",
    "MARKUP_SUFFIXES",
    "SpellKind",
    "checkable_spans",
    "masked_for_checking",
    "skipped_prose_ranges",
    "spell_kind_for",
    "word_is_checkable",
]

SpellKind = Literal["prose", "markdown", "markup", "code"]

#: Markdown and its close relatives: prose with code and links inside it.
MARKDOWN_SUFFIXES: frozenset[str] = frozenset({".md", ".markdown", ".mdown", ".mkd", ".mdx"})

#: Tag-based markup, where the words are between the tags.
MARKUP_SUFFIXES: frozenset[str] = frozenset({
    ".html",
    ".htm",
    ".xhtml",
    ".xml",
    ".xsl",
    ".xslt",
    ".svg",
    ".opml",
    ".rss",
    ".atom",
})

#: In CODE_SUFFIXES for the live-check default, but there is no code grammar
#: in them: a log, a table or a diff is read with the prose rule.
_PROSE_WITHIN_CODE: frozenset[str] = frozenset({".log", ".csv", ".tsv", ".diff", ".patch"})

#: Above this many characters a code file is lexed with the regex fallback
#: rather than Pygments. Pygments costs roughly 6 microseconds a character, so
#: this caps one full lex near half a second; the result is cached per text.
PYGMENTS_MAX_CHARS = 100_000


def _suffix(filename: str | Path | None) -> str:
    if filename is None:
        return ""
    return Path(str(filename)).suffix.lower()


def spell_kind_for(filename: str | Path | None) -> SpellKind:
    """What kind of text *filename* holds, for spell checking.

    ``None`` (an unsaved document) and any extension not otherwise claimed is
    prose: a false alarm in a scratch buffer costs less than silence in the
    letter somebody is actually writing.
    """
    suffix = _suffix(filename)
    if suffix in MARKDOWN_SUFFIXES:
        return "markdown"
    if suffix in MARKUP_SUFFIXES:
        return "markup"
    if suffix in CODE_SUFFIXES and suffix not in _PROSE_WITHIN_CODE:
        return "code"
    return "prose"


# --------------------------------------------------------------------------- #
# Prose: what to skip inside ordinary sentences
# --------------------------------------------------------------------------- #

_TLDS = (
    "com|org|net|edu|gov|mil|int|io|dev|app|ai|co|uk|us|ca|au|nz|ie|de|fr|es|it|"
    "nl|se|no|dk|fi|jp|cn|in|br|ru|info|biz|me|tv|ly|gg|xyz|tech|site|online"
)
_PROSE_SKIP = re.compile(
    r"""
    (?:[a-z][a-z0-9+.\-]*://|www\.)[^\s<>"'`]+          # scheme URL or www. host
    | (?:mailto|tel|urn|file|data):[^\s<>"'`]+           # schemeless URI forms
    | [\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+                     # email address
    | (?<![\w@.])(?:[a-z0-9\-]+\.)+[a-z]{2,}/[^\s<>"'`]*  # bare domain with a path
    | (?<![\w@.])(?:[a-z0-9\-]+\.)+(?:"""
    + _TLDS
    + r""")\b(?![\w\-])                                  # bare domain, known ending
    | [a-z]:\\[^\s<>"'`|*?]*                             # Windows drive path
    | \\\\[\w.\-$]+(?:\\[^\s<>"'`|*?]*)?                 # UNC path
    | (?<![\w/.~])(?:~|\.{1,2})/[\w.\-]+(?:/[\w.\-]*)*     # ~/x, ./x, ../x
    | (?<![\w/.~:])/[\w.\-]+(?:/[\w.\-]+)+/?             # /usr/local/bin
    | (?<![\w\\])[\w.\-]+(?:\\[\w.\-]+)+\\?              # relative backslash path
    """,
    re.IGNORECASE | re.VERBOSE,
)

#: A file name with an extension somebody would recognise: ``readme.txt``.
_FILE_NAME = re.compile(
    r"(?<![\w.])[\w\-]+(?:\.[\w\-]+)*\.(?:"
    + "|".join(
        sorted(
            {s.lstrip(".") for s in CODE_SUFFIXES if len(s) > 2}
            | {"c", "h"}
            | {
                "txt",
                "md",
                "rtf",
                "doc",
                "docx",
                "pdf",
                "epub",
                "png",
                "jpg",
                "jpeg",
                "gif",
                "mp3",
                "mp4",
                "wav",
                "zip",
                "exe",
                "dll",
                "msi",
                "odt",
                "xlsx",
            },
            key=len,
            reverse=True,
        )
    )
    + r")\b(?![\w\-])",
    re.IGNORECASE,
)

_MD_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_MD_INLINE_SKIP = re.compile(
    r"""
    (`+)[^`\n].*?\1(?!`)                 # inline code span, any backtick count
    | \]\([^)\n]*\)                      # link or image target: ](target "title")
    | ^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*\S+  # reference definition target
    | </?[A-Za-z][^<>\n]*>               # inline HTML tag
    | <!--.*?-->                         # HTML comment on one line
    """,
    re.VERBOSE | re.MULTILINE,
)


def _prose_line_skips(text: str, lo: int, hi: int, markdown: bool) -> Iterator[tuple[int, int]]:
    for pattern in (_PROSE_SKIP, _FILE_NAME):
        for match in pattern.finditer(text, lo, hi):
            yield match.start(), match.end()
    if markdown:
        for match in _MD_INLINE_SKIP.finditer(text, lo, hi):
            yield match.start(), match.end()


def _merge(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def _markdown_fence_ranges(text: str) -> list[tuple[int, int]]:
    """Every fenced code block, fence lines included."""
    if "```" not in text and "~~~" not in text:
        return []
    ranges: list[tuple[int, int]] = []
    open_at: int | None = None
    fence = ""
    position = 0
    for line in text.splitlines(keepends=True):
        match = _MD_FENCE.match(line)
        if match is not None:
            marker = match.group(1)
            if open_at is None:
                open_at, fence = position, marker[0] * len(marker)
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                ranges.append((open_at, position + len(line)))
                open_at = None
        position += len(line)
    if open_at is not None:
        ranges.append((open_at, len(text)))
    return ranges


def skipped_prose_ranges(text: str, filename: str | Path | None = None) -> list[tuple[int, int]]:
    """Every range the prose (or Markdown) rule skips, merged and sorted."""
    markdown = spell_kind_for(filename) == "markdown"
    ranges = list(_prose_line_skips(text, 0, len(text), markdown))
    if markdown:
        ranges.extend(_markdown_fence_ranges(text))
    return _merge(ranges)


def _inside_markdown_fence(text: str, line_start: int) -> bool:
    before = text[:line_start]
    if "```" not in before and "~~~" not in before:
        return False
    return any(start < line_start < end for start, end in _markdown_fence_ranges(text))


def word_is_checkable(text: str, start: int, end: int, filename: str | Path | None = None) -> bool:
    """Should the word at ``text[start:end]`` be spell checked at all?

    The cheap, local question the as-you-type check and the next/previous keys
    ask: for prose it looks only at the line the word is on (and, in Markdown,
    whether that line sits inside a fence), so it never scans the document per
    keystroke. For code and markup the answer comes from the cached mask.
    """
    kind = spell_kind_for(filename)
    if kind in ("code", "markup"):
        masked = masked_for_checking(text, filename)
        return masked[start:end] == text[start:end]
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    markdown = kind == "markdown"
    for skip_start, skip_end in _prose_line_skips(text, line_start, line_end, markdown):
        if skip_start < end and start < skip_end:
            return False
    return not (markdown and _inside_markdown_fence(text, line_start))


_SPAN_CACHE: dict[tuple[str, str], list[tuple[int, int]]] = {}
_MASK_CACHE: dict[tuple[str, str], str] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_SIZE = 4


def _remember(cache: dict[Any, Any], key: Any, value: Any) -> None:
    with _CACHE_LOCK:
        cache[key] = value
        while len(cache) > _CACHE_SIZE:
            cache.pop(next(iter(cache)))


def checkable_spans(text: str, filename: str | Path | None = None) -> list[tuple[int, int]]:
    """The ``(start, end)`` ranges of *text* a spell checker should read.

    Sorted, non-overlapping and in the original offsets. For prose this is the
    whole text minus :func:`skipped_prose_ranges`; for code and markup it is the
    lexed string literals, comments and text nodes, minus what is skipped
    inside them.
    """
    kind = spell_kind_for(filename)
    suffix = _suffix(filename)
    key = (kind + suffix, text)
    cached = _SPAN_CACHE.get(key)
    if cached is not None:
        return list(cached)
    if kind in ("prose", "markdown"):
        spans: list[tuple[int, int]] = []
        cursor = 0
        for start, end in skipped_prose_ranges(text, filename):
            if start > cursor:
                spans.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < len(text):
            spans.append((cursor, len(text)))
    else:
        raw: list[tuple[int, int]] | None = None
        lexer = _pygments_lexer(filename, kind) if len(text) <= PYGMENTS_MAX_CHARS else None
        if lexer is not None:
            raw = _pygments_spans(text, lexer, markup=kind == "markup")
        if raw is None:
            raw = _regex_markup_spans(text) if kind == "markup" else _regex_code_spans(text, suffix)
        raw = _merge(raw)
        if kind == "markup":
            # Text nodes are prose; the strings and comments of embedded
            # scripts are code. The prose rule applies to both, and the code
            # rule (escapes, placeholders, identifiers) is harmless in text.
            spans = _subtract(_subtract(raw, text, _PROSE_SKIP), text, _FILE_NAME)
        else:
            spans = _subtract(raw, text, _PROSE_SKIP)
            spans = _subtract(spans, text, _FILE_NAME)
            spans = _subtract(spans, text, _CODE_TEXT_SKIP)
        spans = [(start, end) for start, end in spans if end > start]
    _remember(_SPAN_CACHE, key, spans)
    return list(spans)


_NOT_NEWLINE = re.compile(r"[^\n]+")


def masked_for_checking(text: str, filename: str | Path | None = None) -> str:
    """*text* with every character outside :func:`checkable_spans` blanked.

    Same length, newlines kept, so every offset in the result is an offset in
    the document. The word scanner runs over this unchanged.
    """
    kind = spell_kind_for(filename)
    key = (kind + _suffix(filename), text)
    cached = _MASK_CACHE.get(key)
    if cached is not None:
        return cached
    pieces: list[str] = []
    cursor = 0
    for start, end in checkable_spans(text, filename):
        if start > cursor:
            pieces.append(_NOT_NEWLINE.sub(lambda m: " " * len(m.group(0)), text[cursor:start]))
        pieces.append(text[start:end])
        cursor = end
    if cursor < len(text):
        pieces.append(_NOT_NEWLINE.sub(lambda m: " " * len(m.group(0)), text[cursor:]))
    masked = "".join(pieces)
    _remember(_MASK_CACHE, key, masked)
    return masked


def overlaps_any(ranges: list[tuple[int, int]], start: int, end: int) -> bool:
    """True when ``[start, end)`` overlaps one of the sorted, merged *ranges*."""
    index = bisect.bisect_right(ranges, (start, float("inf"))) - 1
    for candidate in ranges[max(0, index) : index + 2]:
        if candidate[0] < end and start < candidate[1]:
            return True
    return False


def reset_caches() -> None:
    """Forget cached spans, masks and lexers (tests and benchmarks)."""
    with _CACHE_LOCK:
        _SPAN_CACHE.clear()
        _MASK_CACHE.clear()
        _LEXER_CACHE.clear()
