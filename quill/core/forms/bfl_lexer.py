"""BFL tokens: a faithful port of BAF's ``class-baf-bfl-lexer.php``.

BITS Accessible Forms (BAF) is the WordPress plugin whose form language, BFL
(BITS Form Language), QUILL reads and writes. This module turns BFL text into
exactly the tokens BAF's PHP lexer makes, in the same order, with the same
values, so that the parser ports built on it agree with BAF byte for byte.

Two things are added and change nothing BAF sees: every token records ``pos``
and ``end``, its offsets in the source, which is what lets QUILL's reader keep
every byte of a document; and the keyword tables are exposed as constants.

BAF works on bytes and QUILL on characters. The only visible difference is the
``column`` of a token after a non-ASCII character, which nothing in the forms
core uses.
"""

from __future__ import annotations

from dataclasses import dataclass

KEYWORD = "KEYWORD"
IDENTIFIER = "IDENTIFIER"
STRING = "STRING"
NUMBER = "NUMBER"
MODIFIER = "MODIFIER"
CHOICE = "CHOICE"
COMMENT = "COMMENT"
INDENT = "INDENT"
NEWLINE = "NEWLINE"
COLON = "COLON"
PIPE = "PIPE"
COMMA = "COMMA"
BRACKET_OPEN = "BRACKET_OPEN"
BRACKET_CLOSE = "BRACKET_CLOSE"
BRACE_OPEN = "BRACE_OPEN"
BRACE_CLOSE = "BRACE_CLOSE"
PAREN_OPEN = "PAREN_OPEN"
PAREN_CLOSE = "PAREN_CLOSE"
EQUALS = "EQUALS"
ARROW = "ARROW"
EOF = "EOF"

#: The choice-library names BAF's lexer treats as keywords (and its parser
#: accepts straight after a choice field's label).
LIBRARY_KEYWORDS: tuple[str, ...] = (
    "countries", "states", "provinces", "us_states", "ca_provinces",
    "uk_counties", "au_states", "currencies", "timezones",
    "languages", "months", "days", "years", "salutations",
    "gender", "age_ranges", "education", "employment_status",
    "industries", "company_sizes",
)  # fmt: skip

#: Field types BAF's parser reads (``is_field_type``), in its order.
BAF_FIELD_TYPES: tuple[str, ...] = (
    "text", "textarea", "paragraph", "number", "email", "phone", "website", "url",
    "hidden", "password", "select", "dropdown", "multiselect", "radio", "checkbox",
    "checkboxes", "consent", "likert", "ranking", "rating", "date", "time",
    "datetime", "daterange", "name", "address", "file", "fileupload", "signature",
    "captcha", "repeater", "calculation", "product", "quantity", "price", "total",
    "coupon", "html", "divider", "spacer", "submit", "save", "savebutton",
    "post_title", "post_content", "post_excerpt", "post_category", "post_tags",
    "post_image", "post_custom", "user_login", "user_email", "user_password",
    "section",
)  # fmt: skip

KEYWORDS: frozenset[str] = frozenset(
    ("form", "page", "section", "columns", "column", "group", "conditional")
    + tuple(t for t in BAF_FIELD_TYPES if t != "section")
    + LIBRARY_KEYWORDS
    + ("if", "else", "then", "and", "or", "not", "is", "contains",
       "starts", "ends", "greater", "less", "between", "empty", "filled",
       "begin", "end")
)  # fmt: skip

_SINGLE = {
    ":": COLON, "|": PIPE, ",": COMMA, "[": BRACKET_OPEN, "]": BRACKET_CLOSE,
    "{": BRACE_OPEN, "}": BRACE_CLOSE, "(": PAREN_OPEN, ")": PAREN_CLOSE,
}  # fmt: skip
_PHP_TRIM = " \t\n\r\0\x0b"
_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}


@dataclass(slots=True)
class Token:
    type: str
    value: str
    line: int
    column: int
    pos: int = 0
    end: int = 0
    level: int = 0


def is_alpha(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ch == "_"


def is_digit(ch: str) -> bool:
    return "0" <= ch <= "9" and len(ch) == 1


def is_alnum(ch: str) -> bool:
    return is_alpha(ch) or is_digit(ch)


class _Lexer:
    def __init__(self, source: str) -> None:
        self.src = source
        self.n = len(source)
        self.i = 0
        self.line = 1
        self.col = 1
        self.out: list[Token] = []

    def peek(self) -> str:
        return self.src[self.i] if self.i < self.n else "\0"

    def peek_next(self) -> str:
        return self.src[self.i + 1] if self.i + 1 < self.n else "\0"

    def adv(self) -> None:
        self.i += 1
        self.col += 1

    def emit(self, kind: str, value: str, start: int, level: int = 0) -> None:
        # BAF stamps line/column when the token is created, after scanning.
        self.out.append(Token(kind, value, self.line, self.col, start, self.i, level))

    def run(self) -> list[Token]:
        while self.i < self.n:
            self.scan()
        self.out.append(Token(EOF, "", self.line, self.col, self.n, self.n))
        return self.out

    def scan(self) -> None:
        ch = self.peek()
        start = self.i
        if ch == "\n":
            self.out.append(Token(NEWLINE, "\n", self.line, self.col, start, start + 1))
            self.adv()
            self.line += 1
            self.col = 1
            self.indentation()
            return
        if ch == "\r":
            self.adv()
            return
        if ch in " \t":
            if self.col == 1:
                self.indentation()
            else:
                self.adv()
            return
        if ch == "/" and self.peek_next() in "/*":
            self.comment(block=self.peek_next() == "*")
            return
        if ch in "\"'":
            self.string(ch)
            return
        if is_digit(ch) or (ch == "-" and is_digit(self.peek_next())):
            self.number()
            return
        if ch == "#":
            self.adv()
            s = self.i
            while self.i < self.n and is_alnum(self.peek()):
                self.adv()
            self.emit(IDENTIFIER, self.src[s : self.i], start)
            return
        if ch == "@":
            self.adv()
            s = self.i
            while self.i < self.n and (is_alnum(self.peek()) or self.peek() == "-"):
                self.adv()
            self.emit(MODIFIER, self.src[s : self.i], start)
            return
        if ch == "+":
            self.adv()
            while self.i < self.n and self.peek() in " \t":
                self.adv()
            s = self.i
            while self.i < self.n and self.peek() != "\n":
                self.adv()
            self.emit(CHOICE, self.src[s : self.i].strip(_PHP_TRIM), start)
            return
        if ch in _SINGLE:
            self.out.append(Token(_SINGLE[ch], ch, self.line, self.col, start, start + 1))
            self.adv()
            return
        if ch == "=":
            if self.peek_next() == ">":
                self.out.append(Token(ARROW, "=>", self.line, self.col, start, start + 2))
                self.adv()
                self.adv()
            else:
                self.out.append(Token(EQUALS, "=", self.line, self.col, start, start + 1))
                self.adv()
            return
        if is_alpha(ch):
            while self.i < self.n and is_alnum(self.peek()):
                self.adv()
            value = self.src[start : self.i]
            lower = value.lower()
            if lower in KEYWORDS:
                self.emit(KEYWORD, lower, start)
            else:
                self.emit(STRING, value, start)
            return
        self.adv()  # unknown character: skipped, as in BAF

    def indentation(self) -> None:
        start = self.i
        level = 0
        while self.i < self.n and self.peek() in " \t":
            level += 4 if self.peek() == "\t" else 1
            self.adv()
        if self.i > start:
            self.emit(INDENT, self.src[start : self.i], start, level)

    def comment(self, *, block: bool) -> None:
        start = self.i
        self.adv()
        self.adv()
        if not block:
            while self.i < self.n and self.peek() != "\n":
                self.adv()
        else:
            while self.i < self.n:
                if self.peek() == "*" and self.peek_next() == "/":
                    self.adv()
                    self.adv()
                    break
                if self.peek() == "\n":
                    self.line += 1
                    self.col = 0
                self.adv()
        self.emit(COMMENT, self.src[start : self.i], start)

    def string(self, quote: str) -> None:
        start = self.i
        self.adv()
        parts: list[str] = []
        while self.i < self.n and self.peek() != quote:
            ch = self.peek()
            if ch == "\\":
                self.adv()
                esc = self.peek()
                parts.append(_ESCAPES.get(esc, esc))
                self.adv()
                continue
            if ch == "\n":
                self.line += 1
                self.col = 0
            parts.append(ch)
            self.adv()
        if self.i < self.n:
            self.adv()
        self.i = min(self.i, self.n)
        self.emit(STRING, "".join(parts), start)

    def number(self) -> None:
        start = self.i
        if self.peek() == "-":
            self.adv()
        while self.i < self.n and is_digit(self.peek()):
            self.adv()
        if self.i < self.n and self.peek() == "." and is_digit(self.peek_next()):
            self.adv()
            while self.i < self.n and is_digit(self.peek()):
                self.adv()
        self.emit(NUMBER, self.src[start : self.i], start)


def tokenize(source: str) -> list[Token]:
    """BFL source to BAF's tokens, ending with one EOF token."""
    return _Lexer(source).run()
