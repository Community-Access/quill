"""The BAF expression language: reading, canonical text and the tree.

One small language does every job in a form: conditions, calculations, quiz
scoring and smart defaults. Its home is BAF (``docs/expression-language.md``
and ``includes/model/class-baf-expression.php``); this module is a port, so
both programs read every text to the same tree and write the same canonical
text, byte for byte. ``tests/conformance/expressions/cases.json`` in BAF is
the contract.

The tree is plain JSON, as BAF shares it:

- ``{"type": "literal", "value": ...}``, ``{"type": "ref", "field": "id"}``,
  ``{"type": "list", "items": [...]}``, ``{"type": "var", "name": "score"}``,
  ``{"type": "call", "name": "round", "args": [...]}``;
- ``{"type": "op", "op": ..., "args": [...]}``, where ``op`` is one of
  ``or and not neg empty not_empty is is_not lt le gt ge one_of not_one_of
  contains not_contains starts_with ends_with before after within add sub
  mul div mod``.

:mod:`expr_eval` works a tree out and :mod:`expr_sentence` reads one aloud.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms.errors import ExpressionError
from quill.core.forms.expr_text import (
    PRECEDENCE,
    literal_text,
    number_text,
    quote,
    to_text,
)

Node = dict[str, Any]

#: Functions, with their (fewest, most) arguments; -1 is any number.
FUNCTIONS: dict[str, tuple[int, int]] = {
    "today": (0, 0), "date": (1, 1), "days_between": (2, 2), "age": (1, 1),
    "abs": (1, 1), "round": (1, 2), "floor": (1, 1), "ceil": (1, 1),
    "min": (1, -1), "max": (1, -1), "sum": (1, -1), "avg": (1, -1),
    "count": (1, 1), "length": (1, 1), "if": (3, 3), "score": (1, 1),
    "user": (1, 1), "query": (1, 1), "geo": (0, 0),
}  # fmt: skip

RESERVED = frozenset(
    "and or not is contains does contain starts ends with empty filled before after "
    "within days of greater less than true false null score today at least most".split()
)

_ESCAPES = {"n": "\n", "t": "\t", "r": "\r"}


def _alnum(c: str) -> bool:
    return c.isascii() and (c.isalnum() or c == "_")


def _digit(c: str) -> bool:
    return "0" <= c <= "9"


def _alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z")


def scan_string(s: str, i: int) -> tuple[str, int]:
    """A quoted string at ``s[i]``: (its value, the offset after the closing quote)."""
    quote = s[i]
    n = len(s)
    start = i
    i += 1
    out: list[str] = []
    while i < n and s[i] != quote:
        c = s[i]
        if c == "\\" and i + 1 < n:
            e = s[i + 1]
            i += 2
            if e in _ESCAPES:
                out.append(_ESCAPES[e])
            elif e == "u":
                hexa = s[i : i + 4]
                if len(hexa) == 4 and all(h in "0123456789abcdefABCDEF" for h in hexa):
                    cp = int(hexa, 16)
                    i += 4
                    nxt = s[i + 2 : i + 6]
                    if (
                        0xD800 <= cp <= 0xDBFF
                        and s[i : i + 2] == "\\u"
                        and len(nxt) == 4
                        and all(h in "0123456789abcdefABCDEF" for h in nxt)
                    ):
                        lo = int(nxt, 16)
                        if 0xDC00 <= lo <= 0xDFFF:
                            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
                            i += 6
                    out.append(chr(cp) if not 0xD800 <= cp <= 0xDFFF else chr(0xFFFD))
                else:
                    out.append("u")
            else:
                out.append(e)
            continue
        out.append(c)
        i += 1
    if i >= n:
        raise ExpressionError("A quoted value is not closed.", start)
    return "".join(out), i + 1


def tokenize(s: str) -> list[dict[str, Any]]:
    toks: list[dict[str, Any]] = []
    n = len(s)
    i = 0
    while i < n:
        c = s[i]
        if c in " \t\n\r":
            i += 1
            continue
        start = i
        if c in "#{":
            close = c == "{"
            i += 1
            j = i
            while j < n and _alnum(s[j]):
                j += 1
            if j == i:
                raise ExpressionError(f'A field reference needs a field ID after "{c}".', start)
            ident = s[i:j]
            i = j
            if close:
                if i >= n or s[i] != "}":
                    raise ExpressionError(
                        'A field reference that starts with "{" must end with "}".', start
                    )
                i += 1
            toks.append({"type": "ref", "text": ident, "offset": start})
            continue
        if _digit(c) or (c == "." and i + 1 < n and _digit(s[i + 1])):
            j = i
            while j < n and _digit(s[j]):
                j += 1
            if j < n and s[j] == "." and j + 1 < n and _digit(s[j + 1]):
                j += 1
                while j < n and _digit(s[j]):
                    j += 1
            toks.append({"type": "number", "text": s[i:j], "offset": start})
            i = j
            continue
        if c in "\"'":
            value, i = scan_string(s, i)
            toks.append({"type": "string", "text": value, "offset": start})
            continue
        if _alpha(c) or c == "_":
            j = i
            while j < n and _alnum(s[j]):
                j += 1
            toks.append({"type": "word", "text": s[i:j], "offset": start})
            i = j
            continue
        two = s[i : i + 2]
        if two in ("==", "!=", "<>", "<=", ">="):
            toks.append({"type": "punct", "text": two, "offset": start})
            i += 2
            continue
        if c in "()[],+-*/%=<>":
            toks.append({"type": "punct", "text": c, "offset": start})
            i += 1
            continue
        raise ExpressionError(f'The character "{c}" is not part of the expression language.', start)
    toks.append({"type": "eof", "text": "", "offset": n})
    return toks


def op(name: str, args: list[Node]) -> Node:
    return {"type": "op", "op": name, "args": args}


def _to_number(text: str) -> int | float:
    if "." not in text and len(text.lstrip("0")) < 16:
        return int(text)
    return float(text)


class _Parser:
    def __init__(self, text: str) -> None:
        self.toks = tokenize(text)
        self.pos = 0

    def peek(self, ahead: int = 0) -> dict[str, Any]:
        return self.toks[min(self.pos + ahead, len(self.toks) - 1)]

    def is_word(self, word: str, ahead: int = 0) -> bool:
        t = self.peek(ahead)
        return bool(t["type"] == "word" and t["text"].lower() == word)

    def is_punct(self, p: str, ahead: int = 0) -> bool:
        t = self.peek(ahead)
        return bool(t["type"] == "punct" and t["text"] == p)

    def next(self) -> dict[str, Any]:
        t = self.peek()
        if t["type"] != "eof":
            self.pos += 1
        return t

    def _found(self, t: dict[str, Any]) -> str:
        return "the end" if t["type"] == "eof" else f'"{t["text"]}"'

    def expect_word(self, word: str) -> None:
        if not self.is_word(word):
            t = self.peek()
            raise ExpressionError(f'Expected "{word}" but found {self._found(t)}.', t["offset"])
        self.next()

    def expect_punct(self, p: str) -> None:
        if not self.is_punct(p):
            t = self.peek()
            raise ExpressionError(f'Expected "{p}" but found {self._found(t)}.', t["offset"])
        self.next()

    def parse_or(self) -> Node:
        args = [self.parse_and()]
        while self.is_word("or"):
            self.next()
            args.append(self.parse_and())
        return args[0] if len(args) == 1 else flatten("or", args)

    def parse_and(self) -> Node:
        args = [self.parse_not()]
        while self.is_word("and"):
            self.next()
            args.append(self.parse_not())
        return args[0] if len(args) == 1 else flatten("and", args)

    def parse_not(self) -> Node:
        if self.is_word("not"):
            self.next()
            return op("not", [self.parse_not()])
        return self.parse_comparison()

    def parse_comparison(self) -> Node:  # noqa: C901 - one branch per test
        left = self.parse_additive()
        t = self.peek()
        if t["type"] == "punct":
            table = {
                "=": "is",
                "==": "is",
                "!=": "is_not",
                "<>": "is_not",
                "<": "lt",
                "<=": "le",
                ">": "gt",
                ">=": "ge",
            }
            if t["text"] in table:
                self.next()
                return op(table[t["text"]], [left, self.parse_additive()])
            return left
        if t["type"] != "word":
            return left
        w = t["text"].lower()
        if w == "is":
            self.next()
            neg = False
            if self.is_word("not"):
                self.next()
                neg = True
            if self.is_word("one") and self.is_word("of", 1):
                self.next()
                self.next()
                return op("not_one_of" if neg else "one_of", [left, self.parse_list()])
            if self.is_word("empty"):
                self.next()
                return op("not_empty" if neg else "empty", [left])
            if self.is_word("filled"):
                self.next()
                if self.is_word("in"):
                    self.next()
                return op("empty" if neg else "not_empty", [left])
            if not neg:
                for word, name in (("greater", "gt"), ("less", "lt")):
                    if self.is_word(word):
                        self.next()
                        if self.is_word("than"):
                            self.next()
                        return op(name, [left, self.parse_additive()])
                if self.is_word("at") and (self.is_word("least", 1) or self.is_word("most", 1)):
                    self.next()
                    name = "ge" if self.is_word("least") else "le"
                    self.next()
                    return op(name, [left, self.parse_additive()])
                if self.is_word("before") or self.is_word("after"):
                    name = self.next()["text"].lower()
                    return op(name, [left, self.parse_additive()])
                if self.is_word("within"):
                    self.next()
                    return self.parse_within(left)
            return op("is_not" if neg else "is", [left, self.parse_additive()])
        if w == "empty":
            self.next()
            return op("empty", [left])
        if w == "filled":
            self.next()
            return op("not_empty", [left])
        if w == "contains":
            self.next()
            return op("contains", [left, self.parse_additive()])
        if w == "does":
            self.next()
            self.expect_word("not")
            self.expect_word("contain")
            return op("not_contains", [left, self.parse_additive()])
        if w in ("starts", "ends"):
            self.next()
            if self.is_word("with"):
                self.next()
            return op(
                "starts_with" if w == "starts" else "ends_with", [left, self.parse_additive()]
            )
        if w in ("greater", "less"):
            self.next()
            if self.is_word("than"):
                self.next()
            return op("gt" if w == "greater" else "lt", [left, self.parse_additive()])
        if w in ("before", "after"):
            self.next()
            return op(w, [left, self.parse_additive()])
        if w == "within":
            self.next()
            return self.parse_within(left)
        return left

    def parse_within(self, left: Node) -> Node:
        n = self.parse_additive()
        self.expect_word("days")
        args = [left, n]
        if self.is_word("of"):
            self.next()
            args.append(self.parse_additive())
        return op("within", args)

    def parse_list(self) -> Node:
        start = self.peek()
        self.expect_punct("[")
        items: list[Node] = []
        if not self.is_punct("]"):
            items.append(self.parse_additive())
            while self.is_punct(","):
                self.next()
                items.append(self.parse_additive())
        if not self.is_punct("]"):
            raise ExpressionError('A list must end with "]".', start["offset"])
        self.next()
        return {"type": "list", "items": items}

    def parse_additive(self) -> Node:
        left = self.parse_multiplicative()
        while self.is_punct("+") or self.is_punct("-"):
            name = "add" if self.next()["text"] == "+" else "sub"
            left = op(name, [left, self.parse_multiplicative()])
        return left

    def parse_multiplicative(self) -> Node:
        left = self.parse_unary()
        while self.is_punct("*") or self.is_punct("/") or self.is_punct("%"):
            p = self.next()["text"]
            left = op({"*": "mul", "/": "div"}.get(p, "mod"), [left, self.parse_unary()])
        return left

    def parse_unary(self) -> Node:
        if self.is_punct("-"):
            self.next()
            operand = self.parse_unary()
            value = operand.get("value")
            if (
                operand["type"] == "literal"
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                return {"type": "literal", "value": -value}
            return op("neg", [operand])
        return self.parse_primary()

    def parse_primary(self) -> Node:  # noqa: C901
        t = self.peek()
        kind = t["type"]
        if kind == "number":
            self.next()
            return {"type": "literal", "value": _to_number(t["text"])}
        if kind == "string":
            self.next()
            return {"type": "literal", "value": t["text"]}
        if kind == "ref":
            self.next()
            return {"type": "ref", "field": t["text"]}
        if kind == "punct":
            if t["text"] == "(":
                self.next()
                inner = self.parse_or()
                self.expect_punct(")")
                return inner
            if t["text"] == "[":
                return self.parse_list()
            raise ExpressionError(f'Unexpected "{t["text"]}".', t["offset"])
        if kind == "word":
            w = t["text"].lower()
            if self.is_punct("(", 1):
                if w not in FUNCTIONS:
                    raise ExpressionError(
                        f'There is no function called "{t["text"]}".', t["offset"]
                    )
                self.next()
                self.next()
                args: list[Node] = []
                if not self.is_punct(")"):
                    args.append(self.parse_or())
                    while self.is_punct(","):
                        self.next()
                        args.append(self.parse_or())
                self.expect_punct(")")
                low, high = FUNCTIONS[w]
                if len(args) < low or (high >= 0 and len(args) > high):
                    raise ExpressionError(
                        f'The function "{w}" was given {len(args)} value(s).', t["offset"]
                    )
                return {"type": "call", "name": w, "args": args}
            if w in ("true", "false"):
                self.next()
                return {"type": "literal", "value": w == "true"}
            if w == "null":
                self.next()
                return {"type": "literal", "value": None}
            if w == "today":
                self.next()
                return {"type": "call", "name": "today", "args": []}
            if w == "score":
                self.next()
                return {"type": "var", "name": "score"}
            if w in RESERVED:
                raise ExpressionError(f'Expected a value but found "{t["text"]}".', t["offset"])
            self.next()
            return {"type": "literal", "value": t["text"]}
        if kind == "eof":
            raise ExpressionError("The expression ends too early.", t["offset"])
        raise ExpressionError(f'Unexpected "{t["text"]}".', t["offset"])  # pragma: no cover


def flatten(name: str, args: list[Node]) -> Node:
    flat: list[Node] = []
    for a in args:
        if a.get("type") == "op" and a["op"] == name:
            flat.extend(a["args"])
        else:
            flat.append(a)
    return op(name, flat)


def parse(text: str) -> Node:
    """Expression text to its tree. Raises :class:`ExpressionError` with an ``offset``."""
    p = _Parser(str(text))
    if p.peek()["type"] == "eof":
        raise ExpressionError("The expression is empty.", 0)
    node = p.parse_or()
    if p.peek()["type"] != "eof":
        t = p.peek()
        raise ExpressionError(f'Unexpected "{t["text"]}".', t["offset"])
    return node


def check(text: str) -> str | None:
    """None when ``text`` is an expression, else the problem."""
    try:
        parse(text)
    except ExpressionError as exc:
        return exc.args[0] if exc.args else str(exc)
    return None


def canonical(text: str) -> str:
    return to_text(parse(text))


normalise = canonical


def refs(node: Node) -> list[str]:
    """Field IDs a tree reads, in order of first use."""
    out: list[str] = []

    def visit(n: Any) -> None:
        if not isinstance(n, dict):
            return
        if n.get("type") == "ref":
            if n["field"] not in out:
                out.append(n["field"])
            return
        for key in ("args", "items"):
            for child in n.get(key, []):
                visit(child)

    visit(node)
    return out


__all__ = [
    "FUNCTIONS",
    "PRECEDENCE",
    "RESERVED",
    "canonical",
    "check",
    "flatten",
    "literal_text",
    "number_text",
    "op",
    "parse",
    "quote",
    "refs",
    "scan_string",
    "to_text",
    "tokenize",
]
