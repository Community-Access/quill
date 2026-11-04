"""The form expression language: one small language for every rule.

Conditions ("show this when"), calculations, quiz scoring and smart defaults
are all expressions (wordpress.md 17a.15, point 2). The model stores the
canonical text that :func:`to_text` writes; :mod:`expr_eval` works one out
and :mod:`expr_sentence` reads one aloud.

Grammar (keywords are not case-sensitive)::

    expr     := or
    or       := and ("or" and)*
    and      := not ("and" not)*
    not      := "not" not | test
    test     := sum [tail]
    tail     := ("=" | "!=" | "<" | "<=" | ">" | ">=") sum
              | "is" ["not"] "one" "of" list
              | "is" ["not"] ("empty" | "filled")
              | "is" ["not"] ("before" | "after") sum
              | "is" ["not"] "within" sum "days" ["of" sum]
              | "is" ["not"] sum
              | "contains" sum | "does" "not" "contain" sum
              | "starts" ["with"] sum | "ends" ["with"] sum
              | "before" sum | "after" sum
              | "greater" ["than"] sum | "less" ["than"] sum     (BFL's words)
              | "empty" | "filled"                              (BFL's words)
    sum      := product (("+" | "-") product)*
    product  := unary (("*" | "/" | "%") unary)*
    unary    := "-" unary | atom
    atom     := number | string | "true" | "false" | "today"
              | "#"field_id | name "." name ("." name)*     (user.email, geo.country)
              | name "(" [expr ("," expr)*] ")"             (sum, min, max, round...)
              | "(" expr ")"
    list     := "(" expr ("," expr)* ")"

``#id`` is a field. ``today + 7`` is a date a week from today. Inside BFL an
expression ends at a newline, ``@``, ``{``, ``}``, ``[``, ``]``, ``//`` or the
word ``begin``, which is how ``if #a is 1 {`` and ``@when #a is 1 @required``
both read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from quill.core.forms.errors import ExpressionError

FUNCTIONS = frozenset(("sum", "min", "max", "round", "abs", "count", "days_between", "age", "if"))


@dataclass(frozen=True)
class Num:
    value: Decimal


@dataclass(frozen=True)
class Str:
    value: str


@dataclass(frozen=True)
class Bool:
    value: bool


@dataclass(frozen=True)
class Today:
    pass


@dataclass(frozen=True)
class Ref:
    field: str


@dataclass(frozen=True)
class Ctx:
    path: tuple[str, ...]


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Node, ...]


@dataclass(frozen=True)
class Neg:
    operand: Node


@dataclass(frozen=True)
class Arith:
    op: str  # + - * / %
    left: Node
    right: Node


@dataclass(frozen=True)
class Compare:
    #: = != < <= > >= contains not_contains starts ends before after
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class OneOf:
    value: Node
    options: tuple[Node, ...]
    negate: bool = False


@dataclass(frozen=True)
class Empty:
    value: Node
    negate: bool = False  # True means "is filled"


@dataclass(frozen=True)
class Within:
    value: Node
    days: Node
    of: Node | None = None
    negate: bool = False


@dataclass(frozen=True)
class Logic:
    op: str  # and / or
    items: tuple[Node, ...]


@dataclass(frozen=True)
class Not:
    operand: Node


Node = (
    Num | Str | Bool | Today | Ref | Ctx | Call | Neg
    | Arith | Compare | OneOf | Empty | Within | Logic | Not
)  # fmt: skip


# -- tokens --------------------------------------------------------------------

_TOKEN = re.compile(
    r"""
    (?P<space>[ \t\r]+)
  | (?P<stop>\n|@|\{|\}|\[|\]|//)
  | (?P<num>\d+(?:\.\d+)?|\.\d+)
  | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<ref>\#[A-Za-z0-9_]+)
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
  | (?P<op><=|>=|!=|==|[=<>+\-*/%(),])
    """,
    re.X,
)
_ESC = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}


@dataclass(frozen=True)
class _Tok:
    kind: str
    text: str
    pos: int


def _tokens(text: str, start: int, *, embedded: bool) -> tuple[list[_Tok], int]:
    toks: list[_Tok] = []
    i = start
    while i < len(text):
        m = _TOKEN.match(text, i)
        if m is None:
            raise ExpressionError(f"I cannot read {text[i]!r} in this rule.", i)
        kind = m.lastgroup or ""
        if kind == "space":
            i = m.end()
            continue
        if kind == "stop" or (
            embedded and kind == "word" and m.group().lower() in ("begin", "end")
        ):
            if not embedded:
                raise ExpressionError(f"{m.group()!r} cannot appear in a rule.", i)
            break
        toks.append(_Tok(kind, m.group(), i))
        i = m.end()
    end = i
    while end > start and text[end - 1] in " \t\r":
        end -= 1
    return toks, end


def _unquote(raw: str) -> str:
    return re.sub(r"\\(.)", lambda m: _ESC.get(m.group(1), m.group(1)), raw[1:-1])


# -- parser -----------------------------------------------------------------------


class _Parser:
    def __init__(self, toks: list[_Tok], text: str) -> None:
        self.toks = toks
        self.text = text
        self.i = 0

    def peek(self, ahead: int = 0) -> _Tok | None:
        j = self.i + ahead
        return self.toks[j] if j < len(self.toks) else None

    def word(self, *words: str, ahead: int = 0) -> bool:
        tok = self.peek(ahead)
        return tok is not None and tok.kind == "word" and tok.text.lower() in words

    def op(self, *ops: str) -> bool:
        tok = self.peek()
        return tok is not None and tok.kind == "op" and tok.text in ops

    def take(self) -> _Tok:
        tok = self.peek()
        if tok is None:
            raise ExpressionError("This rule stops before it is finished.", len(self.text))
        self.i += 1
        return tok

    def expect_word(self, word: str) -> None:
        if not self.word(word):
            raise ExpressionError(f"I expected {word!r} here.", self._pos())
        self.i += 1

    def expect_op(self, op: str) -> None:
        if not self.op(op):
            raise ExpressionError(f"I expected {op!r} here.", self._pos())
        self.i += 1

    def _pos(self) -> int:
        tok = self.peek()
        return tok.pos if tok else len(self.text)

    def parse(self) -> Node:
        if not self.toks:
            raise ExpressionError("The rule is empty.", 0)
        node = self.or_()
        if self.peek() is not None:
            extra = self.toks[self.i].text
            raise ExpressionError(f"I did not expect {extra!r} here.", self._pos())
        return node

    def or_(self) -> Node:
        items = [self.and_()]
        while self.word("or"):
            self.i += 1
            items.append(self.and_())
        return items[0] if len(items) == 1 else Logic("or", tuple(items))

    def and_(self) -> Node:
        items = [self.not_()]
        while self.word("and"):
            self.i += 1
            items.append(self.not_())
        return items[0] if len(items) == 1 else Logic("and", tuple(items))

    def not_(self) -> Node:
        if self.word("not"):
            self.i += 1
            return Not(self.not_())
        return self.test()

    def test(self) -> Node:
        left = self.sum_()
        tok = self.peek()
        if tok is None:
            return left
        if tok.kind == "op" and tok.text in ("=", "==", "!=", "<", "<=", ">", ">="):
            self.i += 1
            return Compare("=" if tok.text == "==" else tok.text, left, self.sum_())
        if self.word("is"):
            self.i += 1
            negate = False
            if self.word("not"):
                self.i += 1
                negate = True
            if self.word("one") and self.word("of", ahead=1):
                self.i += 2
                return OneOf(left, self.list_(), negate)
            if self.word("empty", "filled"):
                filled = self.take().text.lower() == "filled"
                return Empty(left, negate != filled)
            if self.word("before", "after"):
                kind = self.take().text.lower()
                node: Node = Compare(kind, left, self.sum_())
                return Not(node) if negate else node
            if self.word("within"):
                self.i += 1
                return self.within(left, negate)
            return Compare("!=" if negate else "=", left, self.sum_())
        if self.word("contains"):
            self.i += 1
            return Compare("contains", left, self.sum_())
        if self.word("does") and self.word("not", ahead=1) and self.word("contain", ahead=2):
            self.i += 3
            return Compare("not_contains", left, self.sum_())
        if self.word("starts", "ends"):
            kind = self.take().text.lower()
            if self.word("with"):
                self.i += 1
            return Compare(kind, left, self.sum_())
        if self.word("before", "after"):
            return Compare(self.take().text.lower(), left, self.sum_())
        if self.word("within"):
            self.i += 1
            return self.within(left, False)
        if self.word("greater", "less"):
            kind = self.take().text.lower()
            if self.word("than"):
                self.i += 1
            return Compare(">" if kind == "greater" else "<", left, self.sum_())
        if self.word("empty", "filled"):
            return Empty(left, self.take().text.lower() == "filled")
        return left

    def within(self, left: Node, negate: bool) -> Node:
        days = self.sum_()
        if not self.word("days", "day"):
            raise ExpressionError("I expected 'days' here.", self._pos())
        self.i += 1
        of = None
        if self.word("of"):
            self.i += 1
            of = self.sum_()
        return Within(left, days, of, negate)

    def list_(self) -> tuple[Node, ...]:
        self.expect_op("(")
        items = [self.or_()]
        while self.op(","):
            self.i += 1
            items.append(self.or_())
        self.expect_op(")")
        return tuple(items)

    def sum_(self) -> Node:
        node = self.product()
        while self.op("+", "-"):
            op = self.take().text
            node = Arith(op, node, self.product())
        return node

    def product(self) -> Node:
        node = self.unary()
        while self.op("*", "/", "%"):
            op = self.take().text
            node = Arith(op, node, self.unary())
        return node

    def unary(self) -> Node:
        if self.op("-"):
            self.i += 1
            return Neg(self.unary())
        return self.atom()

    def atom(self) -> Node:
        tok = self.take()
        if tok.kind == "num":
            try:
                return Num(Decimal(tok.text))
            except InvalidOperation as exc:  # pragma: no cover - the pattern prevents it
                raise ExpressionError(f"{tok.text!r} is not a number.", tok.pos) from exc
        if tok.kind == "str":
            return Str(_unquote(tok.text))
        if tok.kind == "ref":
            return Ref(tok.text[1:])
        if tok.kind == "op" and tok.text == "(":
            node = self.or_()
            self.expect_op(")")
            return node
        if tok.kind == "word":
            low = tok.text.lower()
            if low in ("true", "false"):
                return Bool(low == "true")
            if low == "today":
                return Today()
            if "." in tok.text:
                return Ctx(tuple(tok.text.split(".")))
            if low in FUNCTIONS and self.op("("):
                self.i += 1
                args: list[Node] = []
                if not self.op(")"):
                    args.append(self.or_())
                    while self.op(","):
                        self.i += 1
                        args.append(self.or_())
                self.expect_op(")")
                return Call(low, tuple(args))
            raise ExpressionError(
                f"{tok.text!r} is not something a rule knows. "
                f"A field needs # in front: #{tok.text}.",
                tok.pos,
            )
        raise ExpressionError(f"I did not expect {tok.text!r} here.", tok.pos)


def parse(text: str) -> Node:
    """An expression's text to its tree. Raises :class:`ExpressionError`."""
    toks, _end = _tokens(text, 0, embedded=False)
    return _Parser(toks, text).parse()


def parse_embedded(text: str, start: int) -> tuple[Node, int]:
    """Read an expression inside BFL from ``start``; return it and where it ends."""
    toks, end = _tokens(text, start, embedded=True)
    return _Parser(toks, text).parse(), end


# -- canonical text -------------------------------------------------------------

_LEVEL = {"or": 1, "and": 2, "not": 3, "test": 4, "sum": 5, "product": 6, "unary": 7, "atom": 8}


def _level(node: Node) -> int:
    if isinstance(node, Logic):
        return _LEVEL[node.op]
    if isinstance(node, Not):
        return _LEVEL["not"]
    if isinstance(node, (Compare, OneOf, Empty, Within)):
        return _LEVEL["test"]
    if isinstance(node, Arith):
        return _LEVEL["sum"] if node.op in "+-" else _LEVEL["product"]
    if isinstance(node, Neg):
        return _LEVEL["unary"]
    return _LEVEL["atom"]


def _wrap(node: Node, minimum: int) -> str:
    text = to_text(node)
    return f"({text})" if _level(node) < minimum else text


def quote(value: str) -> str:
    return (
        '"'
        + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
        + '"'
    )


def _number(value: Decimal) -> str:
    """A number as written: 2.50 stays 2.50, because the site compares text."""
    return format(value, "f")


_WORDS = {
    "=": "is", "!=": "is not", "contains": "contains", "not_contains": "does not contain",
    "starts": "starts with", "ends": "ends with", "before": "is before", "after": "is after",
}  # fmt: skip


def to_text(node: Node) -> str:
    """The canonical spelling the model stores."""
    if isinstance(node, Num):
        return _number(node.value)
    if isinstance(node, Str):
        return quote(node.value)
    if isinstance(node, Bool):
        return "true" if node.value else "false"
    if isinstance(node, Today):
        return "today"
    if isinstance(node, Ref):
        return "#" + node.field
    if isinstance(node, Ctx):
        return ".".join(node.path)
    if isinstance(node, Call):
        return node.name + "(" + ", ".join(to_text(a) for a in node.args) + ")"
    if isinstance(node, Neg):
        return "-" + _wrap(node.operand, _LEVEL["unary"])
    if isinstance(node, Arith):
        lvl = _level(node)
        return f"{_wrap(node.left, lvl)} {node.op} {_wrap(node.right, lvl + 1)}"
    if isinstance(node, Compare):
        word = _WORDS.get(node.op, node.op)
        return f"{_wrap(node.left, _LEVEL['sum'])} {word} {_wrap(node.right, _LEVEL['sum'])}"
    if isinstance(node, OneOf):
        neg = "is not one of" if node.negate else "is one of"
        return (
            f"{_wrap(node.value, _LEVEL['sum'])} {neg} ("
            + ", ".join(to_text(o) for o in node.options)
            + ")"
        )
    if isinstance(node, Empty):
        return f"{_wrap(node.value, _LEVEL['sum'])} is {'filled' if node.negate else 'empty'}"
    if isinstance(node, Within):
        neg = "not " if node.negate else ""
        value, days = _wrap(node.value, _LEVEL["sum"]), _wrap(node.days, _LEVEL["sum"])
        text = f"{value} is {neg}within {days} days"
        return text + (f" of {_wrap(node.of, _LEVEL['sum'])}" if node.of is not None else "")
    if isinstance(node, Logic):
        lvl = _LEVEL[node.op]
        return f" {node.op} ".join(_wrap(item, lvl + 1) for item in node.items)
    return "not " + _wrap(node.operand, _LEVEL["not"])


def normalise(text: str) -> str:
    """Any spelling of an expression to its canonical text."""
    return to_text(parse(text))


def field_refs(node: Node) -> list[str]:
    """Every field id an expression reads, in order, without repeats."""
    out: list[str] = []

    def visit(n: Node) -> None:
        if isinstance(n, Ref):
            if n.field not in out:
                out.append(n.field)
            return
        for child in _children(n):
            visit(child)

    visit(node)
    return out


def _children(n: Node) -> tuple[Node, ...]:
    if isinstance(n, Call):
        return n.args
    if isinstance(n, (Neg, Not)):
        return (n.operand,)
    if isinstance(n, (Arith, Compare)):
        return (n.left, n.right)
    if isinstance(n, OneOf):
        return (n.value, *n.options)
    if isinstance(n, Empty):
        return (n.value,)
    if isinstance(n, Within):
        return (n.value, n.days) + ((n.of,) if n.of is not None else ())
    if isinstance(n, Logic):
        return n.items
    return ()
