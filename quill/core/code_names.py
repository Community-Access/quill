"""Layer 1 of IntelliSense: the names in this file, for its language.

Word Prediction (Ctrl+.) offers dictionary words in prose. In a code file it
offers the file's own names instead: every identifier and keyword that starts
with what you have typed, nearest to the caret first, each with its kind
("function", "class", "keyword", "name"...), which the list says aloud.

Speed is the constraint (the plan's budget: the list within 100 ms on a 1 MB
file). Pygments lexes about half a megabyte a second, so lexing the whole file
on every key press is out. Instead:

* the names come from ``str.find`` over a lower-cased copy, in C, so Python
  only looks at the places where what you typed occurs;
* each of those places is checked for a definition word before it (``def``,
  ``class``, ``function``, ``fn``, ``func``, ``struct``...), so a function
  defined far away is still called a function;
* Pygments lexes only a window around the caret, which gives the precise kind
  of names near you, and the language's keywords.

Pure, no ``wx``. Pygments is already shipped (spell checking lexes code with
it), so this layer adds no dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = [
    "CODE_KINDS",
    "CodeName",
    "code_language_for",
    "complete_code_names",
    "is_code_file",
]

#: The kinds a code suggestion can have, as they are said.
CODE_KINDS = frozenset({
    "function",
    "class",
    "keyword",
    "builtin",
    "name",
    "attribute",
    "constant",
    "tag",
    "type",
})

#: How much text either side of the caret Pygments reads.
LEX_WINDOW = 2_500

#: How far either side of the caret a one-letter fragment is looked for.
_SHORT_REACH = 100_000

#: Extensions that are prose, where Word Prediction keeps offering words.
_PROSE_SUFFIXES = frozenset({
    "",
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".mdown",
    ".rst",
    ".rtf",
    ".docx",
    ".odt",
    ".log",
})

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CLASS_WORDS = frozenset({"class", "struct", "interface", "enum", "trait"})


@dataclass(frozen=True, slots=True)
class CodeName:
    """One suggestion: the name, and what kind of thing it is."""

    name: str
    kind: str


def is_code_file(path: Path | str | None) -> bool:
    """True when *path* names a file Pygments knows and that is not prose."""
    return code_language_for(path) is not None


def code_language_for(path: Path | str | None) -> str | None:
    """The Pygments lexer alias for *path*, or ``None`` for prose or unknown."""
    if path is None:
        return None
    name = Path(path).name
    if Path(name).suffix.lower() in _PROSE_SUFFIXES:
        return None
    return _alias_for_filename(name)


@lru_cache(maxsize=256)
def _alias_for_filename(name: str) -> str | None:
    try:
        from pygments.lexers import get_lexer_for_filename
        from pygments.util import ClassNotFound
    except ImportError:  # pragma: no cover - Pygments ships with QUILL
        return None
    try:
        lexer = get_lexer_for_filename(name)
    except ClassNotFound:
        return None
    aliases = getattr(lexer, "aliases", None) or [lexer.name.lower()]
    return str(aliases[0])


@lru_cache(maxsize=64)
def _lexer(alias: str) -> Any:
    from pygments.lexers import get_lexer_by_name

    return get_lexer_by_name(alias, stripnl=False, ensurenl=False)


def _kind_of(token_type: Any) -> str | None:
    from pygments import token as t

    if token_type in t.Keyword.Constant:
        return "constant"
    if token_type in t.Keyword.Type:
        return "type"
    if token_type in t.Keyword:
        return "keyword"
    if token_type in t.Name.Function:
        return "function"
    if token_type in t.Name.Class:
        return "class"
    if token_type in t.Name.Builtin:
        return "builtin"
    if token_type in t.Name.Constant:
        return "constant"
    if token_type in t.Name.Attribute:
        return "attribute"
    if token_type in t.Name.Tag:
        return "tag"
    if token_type in t.Name:
        return "name"
    return None


def _window_kinds(text: str, caret: int, alias: str) -> dict[str, str]:
    """Names near the caret, with the kind Pygments gives them."""
    start = max(0, caret - LEX_WINDOW)
    # Start the window at a line, so the lexer is not dropped mid-string.
    newline = text.rfind("\n", 0, start)
    start = newline + 1 if newline >= 0 else 0
    window = text[start : caret + LEX_WINDOW]
    kinds: dict[str, str] = {}
    try:
        tokens = _lexer(alias).get_tokens(window)
        for token_type, value in tokens:
            kind = _kind_of(token_type)
            if kind is None or not _IDENTIFIER.fullmatch(value):
                continue
            # A definition beats a later use of the same name.
            if kinds.get(value) in (None, "name"):
                kinds[value] = kind
    except Exception:  # noqa: BLE001 - a lexer bug must not break typing
        return {}
    return kinds


#: A definition keyword right before a name: ``def name``, ``class Name``.
_DEFINED_BY = re.compile(
    r"(?<![A-Za-z0-9_])(def|class|function|fn|func|struct|interface|enum|trait|sub|procedure)"
    r"\s+\*?\s*$"
)
_TAIL = re.compile(r"[a-z0-9_]*")


def complete_code_names(
    text: str,
    caret: int,
    fragment: str,
    alias: str,
    *,
    limit: int = 8,
) -> list[CodeName]:
    """Names in *text* that start with *fragment*, nearest the caret first.

    The fragment itself, where it sits under the caret, is never offered:
    completing a word to itself is noise. Case-sensitive matches come before
    case-insensitive ones, because in code ``count`` and ``Count`` differ.

    The scan is ``str.find`` over a lower-cased copy, which runs in C; Python
    only looks at the places the fragment occurs.
    """
    if not fragment:
        return []
    lowered = fragment.lower()
    fragment_start = caret - len(fragment)
    # Search a lower-cased copy with str.find, in C: an IGNORECASE regex is
    # several times slower over a megabyte. str.lower can change the length of
    # a few non-ASCII letters; then only ASCII is folded, so offsets stay true.
    folded = text.lower()
    if len(folded) != len(text):
        folded = "".join(ch.lower() if ch.isascii() else ch for ch in text)
    low, high = 0, len(folded)
    if len(fragment) == 1:
        # One letter matches nearly everything; the nearest are what you want,
        # and reading the whole of a large file for them misses the budget.
        low, high = max(0, caret - _SHORT_REACH), min(high, caret + _SHORT_REACH)
    distance: dict[str, int] = {}
    definitions: dict[str, str] = {}
    begin = folded.find(lowered, low, high)
    while begin != -1:
        if begin and (folded[begin - 1].isalnum() or folded[begin - 1] == "_"):
            begin = folded.find(lowered, begin + 1, high)
            continue
        end = _TAIL.match(folded, begin + len(lowered)).end()  # type: ignore[union-attr]
        next_begin = folded.find(lowered, end, high)
        name = text[begin:end]
        if name != fragment and begin != fragment_start:
            gap = abs(begin - caret)
            if gap < distance.get(name, gap + 1):
                distance[name] = gap
            if name not in definitions:
                defined = _DEFINED_BY.search(text, max(0, begin - 12), begin)
                if defined is not None:
                    word = defined.group(1)
                    definitions[name] = "class" if word in _CLASS_WORDS else "function"
        begin = next_begin
    kinds = _window_kinds(text, caret, alias)
    for keyword, kind in kinds.items():
        # Keywords near the caret are offered even if the rest of the file
        # never uses them.
        if kind == "keyword" and keyword.lower().startswith(lowered) and keyword != fragment:
            distance.setdefault(keyword, len(text) + 1)

    def rank(name: str) -> tuple[int, int, str]:
        exact_case = 0 if name.startswith(fragment) else 1
        return (exact_case, distance[name], name)

    ordered = sorted(distance, key=rank)[:limit]
    return [CodeName(name, definitions.get(name) or kinds.get(name) or "name") for name in ordered]
