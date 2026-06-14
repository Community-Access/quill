"""Regex-based token navigation for code-aware editing (issue #181).

Pure Python, no ``wx`` imports. Provides forward/backward token movement
and token classification for screen-reader announcements.

Tokens are identified by a greedy regex that prefers longer matches (strings,
hex literals, multi-char operators) over shorter ones. Whitespace is skipped
automatically — callers receive the next non-whitespace token and its position.
"""

from __future__ import annotations

import re

# Tokenizer pattern: matches one token, ordered longest-match first.
_TOKEN_RE = re.compile(
    r'"""[\s\S]*?"""'  # triple-double string
    r"|'''[\s\S]*?'''"  # triple-single string
    r'|"(?:[^"\\]|\\.)*"'  # double-quoted string
    r"|'(?:[^'\\]|\\.)*'"  # single-quoted string
    r"|0x[0-9A-Fa-f]+"  # hex literal
    r"|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"  # number (int, float, sci-notation)
    r"|[A-Za-z_][A-Za-z0-9_]*"  # identifier / keyword
    r"|[+\-*/%=<>!&|^~@]+(?:=)?"  # operators (greedy, optional trailing =)
    r"|[(){}[\].,;:?\\]"  # punctuation / single-char tokens
)


def next_token_position(text: str, cursor: int) -> tuple[int, str]:
    """Return ``(start, token_text)`` of the first token that begins after *cursor*.

    Returns ``(len(text), "")`` if no token follows.
    """
    for m in _TOKEN_RE.finditer(text, max(0, cursor)):
        if m.start() >= cursor:
            return m.start(), m.group()
    return len(text), ""


def prev_token_position(text: str, cursor: int) -> tuple[int, str]:
    """Return ``(start, token_text)`` of the last token that ends at or before *cursor*.

    Returns ``(0, "")`` if no token precedes.
    """
    best_start = -1
    best_text = ""
    for m in _TOKEN_RE.finditer(text):
        if m.end() > cursor:
            break
        best_start = m.start()
        best_text = m.group()
    if best_start < 0:
        return 0, ""
    return best_start, best_text


def classify_token(token: str, keywords: tuple[str, ...] = ()) -> str:
    """Return a short screen-reader label for *token*.

    Examples: ``"keyword: def"``, ``"identifier: my_func"``, ``"number: 42"``,
    ``"open paren"``, ``"operator: +="``.
    """
    if not token:
        return ""
    if token in keywords:
        return f"keyword: {token}"
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
        return f"identifier: {token}"
    if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", token):
        return f"number: {token}"
    _BRACKET_NAMES: dict[str, str] = {
        "(": "open paren",
        ")": "close paren",
        "[": "open bracket",
        "]": "close bracket",
        "{": "open brace",
        "}": "close brace",
        "<": "less than",
        ">": "greater than",
    }
    if token in _BRACKET_NAMES:
        return _BRACKET_NAMES[token]
    if token.startswith(('"""', "'''", '"', "'")):
        return f"string: {token[:20]}{'...' if len(token) > 20 else ''}"
    return f"operator: {token}"
