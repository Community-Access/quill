"""BFL tokens and the low-level reading helpers of QAF's BFL reader.

A port of the lexer and token helpers of QAF's
``includes/model/class-qaf-bfl-reader.php`` (BFL 1). The grammar is in
:mod:`bfl_read`; it was split here for GATE-11. The lexer never fails:
problems become errors and it carries on, so a reader always has a model.

Tokens are dicts, as in the PHP: ``t`` (kind), ``v`` (value), ``line``,
``indent`` (spaces, a tab counting four), ``first`` (first on its line),
``start`` and ``end`` (offsets).
"""

from __future__ import annotations

import json
import re
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.errors import ExpressionError

Token = dict[str, Any]

TYPE_ALIASES = {
    "dropdown": "select", "paragraph": "textarea", "url": "website", "checkboxes": "checkbox",
    "file": "fileupload", "savebutton": "save",
}  # fmt: skip
ELEMENT_TYPES = ("divider", "spacer")
STATEMENTS = (
    "form",
    "page",
    "library",
    "rule",
    "scoring",
    "confirmation",
    "notification",
    "translation",
    "settings",
    "bfl",
)


def _alnum(c: str) -> bool:
    return c.isascii() and (c.isalnum() or c == "_")


def _digit(c: str) -> bool:
    return "0" <= c <= "9"


def _alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z")


def field_type(word: str) -> str | None:
    w = word.lower()
    if w in TYPE_ALIASES:
        return TYPE_ALIASES[w]
    if w in ELEMENT_TYPES:
        return "html"
    return w if M.is_field_type(w) else None


def php_numeric(s: str) -> bool:
    """PHP's ``is_numeric`` for the (trimmed) text after a choice's colon."""
    return re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?", s) is not None


class Lexed:
    """The tokens of a source, a cursor over them, and the problems found."""

    def __init__(self) -> None:
        self.src = ""
        self.toks: list[Token] = []
        self.p = 0
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def error(self, line: int, message: str) -> None:
        self.errors.append({"line": line, "message": message})

    def warn(self, line: int, message: str) -> None:
        self.warnings.append({"line": line, "message": message})

    def lex(self, s: str) -> list[Token]:  # noqa: C901 - one case per token kind
        toks: list[Token] = []
        n = len(s)
        i = 0
        line = 1
        indent = 0
        line_first = True
        at_line = True
        while i < n:
            c = s[i]
            if at_line:
                indent = 0
                while i < n and s[i] in " \t":
                    indent += 4 if s[i] == "\t" else 1
                    i += 1
                at_line = False
                continue
            if c == "\n":
                line += 1
                i += 1
                at_line = True
                line_first = True
                continue
            if c in " \t":
                i += 1
                continue
            if c == "/" and i + 1 < n and s[i + 1] == "/":
                while i < n and s[i] != "\n":
                    i += 1
                continue
            if c == "/" and i + 1 < n and s[i + 1] == "*":
                end = s.find("*/", i + 2)
                end = n if end < 0 else end + 2
                line += s.count("\n", i, end)
                i = end
                continue
            start = i
            tok: Token = {"line": line, "indent": indent, "first": line_first, "start": start}
            if c in "\"'":
                try:
                    value, i = E.scan_string(s, i)
                except ExpressionError:
                    self.error(line, "A quoted value is not closed.")
                    eol = s.find("\n", i)
                    eol = n if eol < 0 else eol
                    value = s[i + 1 : eol]
                    i = eol
                line += s.count("\n", start, i)
                tok["t"], tok["v"] = "STRING", value
            elif c == "#" and i + 1 < n and _alnum(s[i + 1]):
                j = i + 1
                while j < n and _alnum(s[j]):
                    j += 1
                tok["t"], tok["v"] = "ID", s[i + 1 : j]
                i = j
            elif c == "@":
                j = i + 1
                while j < n and (_alnum(s[j]) or s[j] == "-"):
                    j += 1
                tok["t"], tok["v"] = "MOD", s[i + 1 : j]
                i = j
            elif c == "+" and (
                line_first
                or (toks and toks[-1]["line"] == line and toks[-1]["t"] in ("LBRACE", "LBRACKET"))
            ):
                eol = s.find("\n", i)
                eol = n if eol < 0 else eol
                tok["t"], tok["v"] = "CHOICE", s[i + 1 : eol].strip(" \t\n\r\0\x0b")
                i = eol
            elif _digit(c) or (c == "-" and i + 1 < n and _digit(s[i + 1])):
                j = i + 1
                while j < n and _digit(s[j]):
                    j += 1
                if j + 1 < n and s[j] == "." and _digit(s[j + 1]):
                    j += 1
                    while j < n and _digit(s[j]):
                        j += 1
                text = s[i:j]
                tok["t"], tok["v"] = "NUMBER", (float(text) if "." in text else int(text))
                i = j
            elif _alpha(c) or c == "_":
                j = i + 1
                while j < n and (_alnum(s[j]) or (s[j] == "-" and j + 1 < n and _alnum(s[j + 1]))):
                    j += 1
                tok["t"], tok["v"] = "WORD", s[i:j]
                i = j
            else:
                tok["t"] = {"{": "LBRACE", "}": "RBRACE", "[": "LBRACKET", "]": "RBRACKET"}.get(
                    c, "OTHER"
                )
                tok["v"] = c
                i += 1
            tok["end"] = i
            toks.append(tok)
            line_first = False
        toks.append({
            "t": "EOF",
            "v": "",
            "line": line,
            "indent": 0,
            "first": True,
            "start": n,
            "end": n,
        })
        return toks

    # -- cursor -------------------------------------------------------------------
    def peek(self, ahead: int = 0) -> Token:
        return self.toks[min(self.p + ahead, len(self.toks) - 1)]

    def next(self) -> Token:
        t = self.peek()
        if t["t"] != "EOF":
            self.p += 1
        return t

    def at_end(self) -> bool:
        return bool(self.peek()["t"] == "EOF")

    @staticmethod
    def is_word(t: Token, word: str | None = None) -> bool:
        return bool(t["t"] == "WORD" and (word is None or str(t["v"]).lower() == word))

    def is_open(self, t: Token) -> bool:
        return t["t"] in ("LBRACE", "LBRACKET") or self.is_word(t, "begin")

    def is_close(self, t: Token) -> bool:
        return t["t"] in ("RBRACE", "RBRACKET") or self.is_word(t, "end")

    def starts_item(self, t: Token) -> bool:
        if t["t"] != "WORD":
            return False
        w = str(t["v"]).lower()
        return field_type(w) is not None or w in ("section", "columns", "if", "conditional")

    def starts_statement(self, t: Token) -> bool:
        return bool(t["t"] == "WORD" and str(t["v"]).lower() in STATEMENTS)

    def raw_to_eol(self, after: Token, header: bool = False) -> str:  # noqa: C901
        """The text after ``after`` to the end of its line, for an expression."""
        s = self.src
        n = len(s)
        i = after["end"]
        depth = 0
        quote: str | None = None
        stop = n
        while i < n:
            c = s[i]
            if quote is not None:
                if c == "\\":
                    i += 1
                elif c == quote:
                    quote = None
                elif c == "\n":
                    stop = i
                    break
                i += 1
                continue
            if c == "\n" or (c == "/" and i + 1 < n and s[i + 1] == "/"):
                stop = i
                break
            if c in "\"'":
                quote = c
            elif c in "{[(":
                depth += 1
            elif c in "}])":
                if depth == 0:
                    stop = i
                    break
                depth -= 1
            i += 1
        text = s[after["end"] : stop]
        end = stop
        if header:
            trim = text.rstrip(" \t\n\r\0\x0b")
            if trim and trim[-1] in "{[":
                end = after["end"] + len(trim) - 1
                text = trim[:-1]
            elif (
                len(trim) >= 5
                and trim[-5:].lower() == "begin"
                and len(trim) > 5
                and trim[-6] in " \t\n\r\x0b\x0c"
            ):
                end = after["end"] + len(trim) - 5
                text = trim[:-5]
        while not self.at_end() and self.peek()["start"] < end:
            self.p += 1
        return text.strip(" \t\n\r\0\x0b")

    def try_json(self) -> tuple[bool, Any]:
        t = self.peek()
        s = self.src
        n = len(s)
        depth = 0
        quote = False
        i = t["start"]
        while i < n:
            c = s[i]
            if quote:
                if c == "\\":
                    i += 1
                elif c == '"':
                    quote = False
                i += 1
                continue
            if c == '"':
                quote = True
            elif c in "{[":
                depth += 1
            elif c in "}]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if i >= n:
            return False, None
        try:
            value = json.loads(s[t["start"] : i + 1])
        except ValueError:
            return False, None
        end = i + 1
        while not self.at_end() and self.peek()["start"] < end:
            self.p += 1
        return True, value

    def mod_value(self, mod: Token) -> tuple[bool, Any]:  # noqa: C901
        """A modifier's value from the rest of its line, if it has one."""
        t = self.peek()
        if t["line"] != mod["line"] or t["t"] == "EOF":
            return False, None
        kind = t["t"]
        if kind in ("STRING", "NUMBER", "ID"):
            self.next()
            return True, t["v"]
        if kind == "WORD":
            w = str(t["v"]).lower()
            if w not in ("true", "false", "null") and (
                self.starts_item(t)
                or self.starts_statement(t)
                or self.is_open(t)
                or self.is_close(t)
                or w in ("column", "else")
            ):
                return False, None
            self.next()
            if w in ("true", "false"):
                return True, w == "true"
            if w == "null":
                return True, None
            return True, t["v"]
        if kind == "LBRACE":
            rest = self.src[t["start"] + 1 : t["start"] + 65].lstrip(" \t\n\r\0\x0b")
            if rest and rest[0] in '"}':
                ok, value = self.try_json()
                if ok:
                    return True, value
            return False, None
        if kind == "LBRACKET":
            save = self.p
            ok, value = self.try_json()
            if ok:
                return True, value
            self.p = save
            items: list[Any] = []
            i = 1
            while True:
                x = self.peek(i)
                if x["line"] != t["line"] or x["t"] == "EOF":
                    return False, None
                if x["t"] == "RBRACKET":
                    break
                if x["t"] in ("STRING", "WORD", "NUMBER"):
                    items.append(x["v"])
                elif not (x["t"] == "OTHER" and x["v"] == ","):
                    return False, None
                i += 1
            self.p += i + 1
            return True, items
        return False, None

    def expression(self, text: str, line: int) -> str | None:
        """Canonical text of an expression, or None after recording an error."""
        try:
            return E.canonical(text)
        except ExpressionError as exc:
            self.error(
                line, f'The expression "{text}" is not valid: {exc.args[0] if exc.args else exc}'
            )
            return None


def _php_string(v: Any) -> str:
    """PHP's ``(string)`` of a decoded value."""
    if v is True:
        return "1"
    if v is False or v is None:
        return ""
    if isinstance(v, float):
        from quill.core.forms.expr_eval import to_str

        return to_str(v)
    if isinstance(v, (list, dict)):
        return "Array"
    return str(v)
