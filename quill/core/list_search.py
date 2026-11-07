"""Find a named text by the words in it, in any order -- or by a small query.

The snippet picker, the Abbreviations manager and the Copy Tray search each
matched the search box as **one** piece of text: "meeting notes" found a
snippet called "Meeting notes for Tuesday" and missed "Notes from the
meeting", and "reply thanks" found nothing at all although one snippet is
named "Thanks" and replies. The command palette has matched the other way since
it shipped ("add url" finds "URL Add"); this is the same rule, shared, so the
lists that hold somebody's own text answer the way the palette does.

The plain rule: the whole search, as typed, anywhere in the row -- or else every
word of it somewhere in the row, in any order. Case is ignored. An empty search
matches everything. Callers still rank the exact and starts-with matches first;
this only decides what is *in* the list.

**The query syntax.** A search holding any of ``* ? & | ! "`` is read as a
query instead, by the same filter in every list that uses this module:

* a word matches anywhere in the row, case ignored, as before;
* ``*`` inside a word stands for any run of letters, ``?`` for exactly one
  (neither crosses a space: ``c*t`` finds "cart", not "cat food tin");
* ``a & b`` (or just ``a b``) needs both, ``a | b`` either, ``!a`` not a;
* ``"exact text"`` matches those characters, spaces and all, with nothing
  inside the quotes treated as an operator.

``!`` binds tightest, then ``&`` (and plain adjacency), then ``|``: ``draft |
notes !old`` is ``draft | (notes & !old)``. The parser never raises -- somebody
typing ``notes |`` is half way through a word, not making a mistake -- so a
dangling operator or an unclosed quote is read as far as it makes sense. A
query with no characters from that set never reaches the parser, which is what
keeps every plain search answering exactly as it did before the syntax existed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

__all__ = [
    "QUERY_SYNTAX_CHARACTERS",
    "QueryNode",
    "QueryTerm",
    "SearchTerms",
    "has_query_syntax",
    "matches_search",
    "parse_query",
]

_ROW_JOIN = "\n"

#: Any one of these in a search turns it from plain words into a query.
QUERY_SYNTAX_CHARACTERS = frozenset('*?&|!"')

_OPERATORS = frozenset("&|!")


def has_query_syntax(query: str) -> bool:
    """True when *query* uses any query character and so is parsed, not split."""
    return any(char in QUERY_SYNTAX_CHARACTERS for char in query)


@dataclass(frozen=True, slots=True)
class QueryTerm:
    """One word or one quoted phrase, already case-folded."""

    text: str
    exact: bool = False

    @property
    def has_wildcards(self) -> bool:
        return not self.exact and ("*" in self.text or "?" in self.text)

    def found_in(self, folded: str) -> bool:
        """Is this term somewhere in *folded* (a case-folded row)?"""
        if not self.has_wildcards:
            return self.text in folded
        return _wildcard_pattern(self.text).search(folded) is not None


def _wildcard_pattern(text: str) -> re.Pattern[str]:
    parts = []
    for char in text:
        if char == "*":
            parts.append(r"\S*")
        elif char == "?":
            parts.append(r"\S")
        else:
            parts.append(re.escape(char))
    return re.compile("".join(parts))


@dataclass(frozen=True, slots=True)
class QueryNode:
    """A parsed query: a term, or ``not`` / ``all`` / ``any`` over children."""

    kind: str  # "term", "not", "all", "any"
    term: QueryTerm | None = None
    children: tuple[QueryNode, ...] = ()

    def test(self, term_test: Callable[[QueryTerm], bool]) -> bool:
        """Evaluate with *term_test* deciding each term (file names use globs)."""
        if self.kind == "term":
            assert self.term is not None
            return term_test(self.term)
        if self.kind == "not":
            return not self.children[0].test(term_test)
        if self.kind == "all":
            return all(child.test(term_test) for child in self.children)
        return any(child.test(term_test) for child in self.children)

    def found_in(self, folded: str) -> bool:
        """Does a case-folded row satisfy the query, terms matched anywhere?"""
        return self.test(lambda term: term.found_in(folded))


def _tokenize(query: str) -> list[str | QueryTerm]:
    """Operators as one-character strings; words and phrases as terms."""
    tokens: list[str | QueryTerm] = []
    word: list[str] = []

    def end_word() -> None:
        if word:
            tokens.append(QueryTerm("".join(word).casefold()))
            word.clear()

    index = 0
    while index < len(query):
        char = query[index]
        if char.isspace():
            end_word()
        elif char == '"':
            end_word()
            close = query.find('"', index + 1)
            if close < 0:
                close = len(query)
            phrase = query[index + 1 : close]
            if phrase.strip():
                tokens.append(QueryTerm(phrase.casefold(), exact=True))
            index = close
        elif char in _OPERATORS:
            end_word()
            tokens.append(char)
        else:
            word.append(char)
        index += 1
    end_word()
    return tokens


class _Parser:
    def __init__(self, tokens: list[str | QueryTerm]) -> None:
        self.tokens = tokens
        self.at = 0

    def peek(self) -> str | QueryTerm | None:
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def parse_any(self) -> QueryNode | None:
        options: list[QueryNode] = []
        while True:
            node = self.parse_all()
            if node is not None:
                options.append(node)
            if self.peek() != "|":
                break
            self.at += 1
        return _combine("any", options)

    def parse_all(self) -> QueryNode | None:
        needed: list[QueryNode] = []
        while True:
            token = self.peek()
            if token is None or token == "|":
                break
            if token == "&":
                self.at += 1
                continue
            node = self.parse_not()
            if node is not None:
                needed.append(node)
        return _combine("all", needed)

    def parse_not(self) -> QueryNode | None:
        token = self.peek()
        if token == "!":
            self.at += 1
            inner = self.parse_not()
            return QueryNode("not", children=(inner,)) if inner is not None else None
        if isinstance(token, QueryTerm):
            self.at += 1
            return QueryNode("term", term=token)
        return None  # "&" or "|": the caller's loop deals with it


def _combine(kind: str, nodes: list[QueryNode]) -> QueryNode | None:
    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]
    return QueryNode(kind, children=tuple(nodes))


def parse_query(query: str) -> QueryNode | None:
    """Parse *query*; ``None`` when nothing in it constrains (match everything)."""
    return _Parser(_tokenize(query)).parse_any()


class SearchTerms:
    """A search prepared once, for asking of many rows (a keystroke's worth)."""

    __slots__ = ("is_query", "needle", "query", "words")

    def __init__(self, query: str) -> None:
        self.needle = " ".join(query.casefold().split())
        self.words = tuple(self.needle.split(" ")) if " " in self.needle else ()
        self.is_query = has_query_syntax(query)
        self.query = parse_query(query) if self.is_query else None

    def found_in(self, folded: str) -> bool:
        """*folded* is the row's text, already case-folded."""
        if self.is_query:
            return self.query is None or self.query.found_in(folded)
        if not self.needle or self.needle in folded:
            return True
        return bool(self.words) and all(word in folded for word in self.words)

    def found_in_fields(self, fields: Iterable[str]) -> bool:
        """The same question over separate fields, folded and joined here."""
        return self.found_in(_ROW_JOIN.join(str(field).casefold() for field in fields))


def matches_search(query: str, fields: Iterable[str]) -> bool:
    """True when *query* (whole, word by word, or as a query) is found across *fields*."""
    return SearchTerms(query).found_in_fields(fields)
