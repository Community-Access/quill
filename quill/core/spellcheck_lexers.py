"""How spell check finds the words in code and markup: strings, comments, text.

Pygments first, because it has a real lexer for over 500 languages and gets
the hard shapes right -- template strings, heredocs, scripts inside HTML. It
is imported lazily, on the first code file, and a small regex lexer per
family of languages stands in when Pygments or a lexer is missing, or when a
file is too large to lex quickly. Split from :mod:`quill.core.spellcheck_spans`
under GATE-11; that module decides *which* rule applies and owns the caches.
wx-free and pure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

#: Attribute values a person reads or hears, and so are checked.
READABLE_ATTRIBUTES: frozenset[str] = frozenset({
    "alt",
    "title",
    "aria-label",
    "aria-description",
    "placeholder",
})


def _suffix_of(filename: str | Path | None) -> str:
    return Path(str(filename)).suffix.lower() if filename is not None else ""


# --------------------------------------------------------------------------- #
# Code: string literals and comments only
# --------------------------------------------------------------------------- #

#: Skipped inside a string literal or a comment: escapes, placeholders, and
#: words shaped like identifiers rather than language.
_CODE_TEXT_SKIP = re.compile(
    r"""
    # an escape sequence
    \\(?:x[0-9a-fA-F]+|u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|N\{[^}\n]*\}|[0-7]{1,3}|.)
    | \$\{[^}\n]*\}                                   # ${expression}
    | \$\(?[A-Za-z_][\w:]*\)?                         # $variable, $(variable)
    | \{\{|\}\}                                       # doubled braces
    | \{[^{}\s]*\}                                    # {0} {name} {0:N2} {}
    | %\([\w.]+\)[-+\#0]*\d*(?:\.\d+)?[a-zA-Z](?![A-Za-z])         # %(name)s
    | %[-+\#0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLqjzt]{0,2}[diouxXeEfFgGcrsaAp](?![A-Za-z])
    | \b\w*(?:_|\d)\w*\b                              # snake_case, words with digits
    | \b[a-z]+[A-Z]\w*\b                              # camelCase
    | \b[A-Z]{2,}[a-z]+[A-Z]\w*\b                     # HTTPServer-style
    """,
    re.VERBOSE,
)
_STRING_PREFIX = re.compile(r"[A-Za-z0-9_$@]{1,3}(?=[\"'`])")


def _inside_quotes(text: str, start: int, end: int) -> tuple[int, int]:
    """*start*..*end* without the quote marks round a one-line string literal.

    A quote mark is not part of the word beside it, but the word pattern allows
    an apostrophe inside a word ("don't"), so a single-quoted 'vlaue' read
    whole was reported as "vlaue'" -- a word with a stray mark on it that no
    suggestion could fix.
    """
    if end - start >= 2 and text[start] in "\"'`" and text[end - 1] == text[start]:
        return start + 1, end - 1
    return start, end


def _subtract(
    spans: list[tuple[int, int]], text: str, pattern: re.Pattern[str]
) -> list[tuple[int, int]]:
    """*spans* with every match of *pattern* inside them cut out."""
    result: list[tuple[int, int]] = []
    for start, end in spans:
        cursor = start
        for match in pattern.finditer(text, start, end):
            if match.start() > cursor:
                result.append((cursor, match.start()))
            cursor = max(cursor, match.end())
        if cursor < end:
            result.append((cursor, end))
    return result


def _pygments_lexer(filename: str | Path | None, kind: str) -> Any | None:
    """A Pygments lexer for *filename*, or None when Pygments cannot help."""
    suffix = _suffix_of(filename)
    cached = _LEXER_CACHE.get(suffix, _MISSING)
    if cached is not _MISSING:
        return cached
    lexer: Any | None = None
    try:
        from pygments.lexers import get_lexer_for_filename
        from pygments.util import ClassNotFound

        try:
            lexer = get_lexer_for_filename("x" + suffix, stripnl=False, ensurenl=False)
        except ClassNotFound:
            if kind == "markup":
                from pygments.lexers.html import HtmlLexer

                lexer = HtmlLexer(stripnl=False, ensurenl=False)
    except Exception:  # noqa: BLE001 - no Pygments, or a broken one: use the fallback
        lexer = None
    _LEXER_CACHE[suffix] = lexer
    return lexer


_MISSING = object()
_LEXER_CACHE: dict[str, Any] = {}


def _pygments_spans(text: str, lexer: Any, markup: bool) -> list[tuple[int, int]] | None:
    """Checkable token ranges from Pygments, or None if the lexer failed."""
    try:
        from pygments.token import Comment, Name, Operator, String, Text, Whitespace
    except Exception:  # noqa: BLE001
        return None
    skipped_strings = (
        String.Escape,
        String.Interpol,
        String.Regex,
        String.Affix,
        String.Symbol,
        String.Char,
        String.Other,
    )
    skipped_comments = (Comment.Preproc, Comment.PreprocFile, Comment.Hashbang)
    spans: list[tuple[int, int]] = []
    pending_attribute: str | None = None
    try:
        for index, token_type, value in lexer.get_tokens_unprocessed(text):
            if not value:
                continue
            end = index + len(value)
            if markup:
                if token_type in Name.Attribute:
                    pending_attribute = value.strip().rstrip("=").strip().lower()
                    continue
                if pending_attribute is not None:
                    if token_type in Operator or token_type in Whitespace or not value.strip():
                        continue
                    if token_type in String:
                        if pending_attribute in READABLE_ATTRIBUTES:
                            spans.append((index, end))
                        pending_attribute = None
                        continue
                    pending_attribute = None
                if token_type in Text and token_type not in Whitespace:
                    spans.append((index, end))
                    continue
            if token_type in String:
                if any(token_type in skip for skip in skipped_strings):
                    continue
                prefix = _STRING_PREFIX.match(value)
                begin = index + (prefix.end() if prefix else 0)
                spans.append(_inside_quotes(text, begin, end))
            elif token_type in Comment:
                if any(token_type in skip for skip in skipped_comments):
                    continue
                spans.append((index, end))
    except Exception:  # noqa: BLE001 - a lexer bug must not break spell check
        return None
    return spans


# The regex fallback: comment and string shapes per family of languages.
_HASH = r"\#[^\n]*"
_SLASH = r"//[^\n]*"
_BLOCK = r"/\*.*?(?:\*/|\Z)"
_DASH = r"--[^\n]*"
_DQ = r'"(?:\\.|[^"\\\n])*"'
_SQ = r"'(?:\\.|[^'\\\n])*'"
_BQ = r"`(?:\\.|[^`\\])*`"
_TRIPLE = r'"""[\s\S]*?(?:"""|\Z)|\'\'\'[\s\S]*?(?:\'\'\'|\Z)'

_FAMILIES: dict[str, tuple[str, ...]] = {
    "hash": (_TRIPLE, _HASH, _DQ, _SQ),
    "slash": (_BLOCK, _SLASH, _DQ, _SQ, _BQ),
    "css": (_BLOCK, _DQ, _SQ),
    "sql": (_BLOCK, _DASH, _DQ, _SQ),
    "lua": (r"--\[\[[\s\S]*?(?:\]\]|\Z)", _DASH, _DQ, _SQ),
    "json": (_BLOCK, _SLASH, _DQ),
    "vb": (r"'[^\n]*", r"(?im:^\s*rem\b[^\n]*)", _DQ),
    "batch": (r"(?im:^\s*(?:rem\b|::)[^\n]*)", _DQ),
    "ini": (r"(?m:^\s*[;#][^\n]*)", _DQ, _SQ),
}
_SUFFIX_FAMILY: dict[str, str] = {
    **dict.fromkeys(
        (
            ".py",
            ".pyi",
            ".pyw",
            ".rb",
            ".pl",
            ".pm",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".ps1",
            ".psm1",
            ".psd1",
            ".r",
            ".jl",
            ".tcl",
            ".yaml",
            ".yml",
            ".toml",
            ".cmake",
            ".mk",
            ".conf",
            ".properties",
            ".env",
            ".graphql",
            ".gql",
            ".spec",
            ".nim",
            ".cr",
            ".ex",
            ".exs",
        ),
        "hash",
    ),
    **dict.fromkeys((".css", ".scss", ".sass", ".less", ".styl"), "css"),
    ".sql": "sql",
    ".lua": "lua",
    **dict.fromkeys((".json", ".jsonc", ".json5", ".map", ".lock"), "json"),
    **dict.fromkeys((".vb", ".vbs"), "vb"),
    **dict.fromkeys((".bat", ".cmd"), "batch"),
    **dict.fromkeys((".ini", ".cfg", ".reg", ".iss"), "ini"),
}
_FAMILY_PATTERNS: dict[str, re.Pattern[str]] = {
    name: re.compile("|".join(f"(?:{part})" for part in parts), re.DOTALL)
    for name, parts in _FAMILIES.items()
}


def _regex_code_spans(text: str, suffix: str) -> list[tuple[int, int]]:
    pattern = _FAMILY_PATTERNS[_SUFFIX_FAMILY.get(suffix, "slash")]
    spans: list[tuple[int, int]] = []
    for match in pattern.finditer(text):
        start = match.start()
        prefix = _STRING_PREFIX.match(text, start)
        spans.append(_inside_quotes(text, prefix.end() if prefix else start, match.end()))
    return spans


_MARKUP_FALLBACK = re.compile(
    r"""
    (?P<comment><!--.*?(?:-->|\Z))
    | (?P<raw><(?P<rawtag>script|style)\b[^>]*>.*?(?:</(?P=rawtag)\s*>|\Z))
    | (?P<other><[!?][^>]*>)
    | (?P<tag></?[A-Za-z][^>]*>)
    | (?P<entity>&\#?\w+;)
    """,
    re.DOTALL | re.IGNORECASE | re.VERBOSE,
)
_ATTRIBUTE = re.compile(r"""([\w:\-]+)\s*=\s*("[^"]*"|'[^']*')""")


def _regex_markup_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in _MARKUP_FALLBACK.finditer(text):
        if match.start() > cursor:
            spans.append((cursor, match.start()))
        cursor = match.end()
        if match.group("comment"):
            spans.append((match.start(), match.end()))
        elif match.group("raw"):
            open_end = text.index(">", match.start()) + 1
            close = text.rfind("</", open_end, match.end())
            body_end = close if close >= 0 else match.end()
            for start, end in _regex_code_spans(text[open_end:body_end], ".js"):
                spans.append((open_end + start, open_end + end))
        elif match.group("tag"):
            for attribute in _ATTRIBUTE.finditer(text, match.start(), match.end()):
                if attribute.group(1).lower() in READABLE_ATTRIBUTES:
                    spans.append((attribute.start(2) + 1, attribute.end(2) - 1))
    if cursor < len(text):
        spans.append((cursor, len(text)))
    return spans
