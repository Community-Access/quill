"""The pieces of BFL reading that are not the reader itself.

The document types (:class:`BflDocument` and the statement markers), the
smart-default conversion, and how a modifier's words become model values.
Split out of :mod:`bfl_read` for GATE-11.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import bfl_lexer as L
from quill.core.forms import expr as E
from quill.core.forms.baf_parser import (
    _FLAGS,
    _ROWS,
    _VALUED,
    is_safe_custom_attribute,
)
from quill.core.forms.bfl_lexer import Token, tokenize
from quill.core.forms.errors import FormError
from quill.core.forms.model import (
    CHOICE_TYPES,
    Cascade,
    Field,
    Form,
)

ALIASES = {
    "dropdown": "select", "paragraph": "textarea", "url": "website", "checkboxes": "checkbox",
    "file": "fileupload", "savebutton": "save", "tel": "phone", "image-choice": "image_choice",
}  # fmt: skip
_BAF_CHOICES = frozenset(("multiselect", "radio", "checkbox", "select", "likert", "ranking"))
CHOICE_KEYWORD_TYPES = CHOICE_TYPES | _BAF_CHOICES
_EXPR_MODIFIERS = frozenset(("when", "calculate", "score"))
_CLOSE = (L.BRACE_CLOSE, L.BRACKET_CLOSE)
_SMART = re.compile(r"\s*today\s*([+-])\s*(\d+)\s*")


def smart_default_expression(value: str) -> str | None:
    """BAF's smart-default text as an expression: ``today+7`` is ``today + 7``."""
    text = value.strip()
    if text == "today":
        return "today"
    m = _SMART.fullmatch(text)
    if m:
        return f"today {m.group(1)} {m.group(2)}"
    if text.startswith("user:") and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text[5:]):
        return "user." + text[5:]
    if text == "geo":
        return "geo.country"
    if text.startswith("geo:") and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text[4:]):
        return "geo." + text[4:]
    return None


@dataclass
class FormHeader:
    """Stands for the ``form`` line in a document's statement list."""


@dataclass
class VersionLine:
    """Stands for the ``// bfl-version N`` first line."""


_VERSION = re.compile(r"//\s*bfl-version\s+(\d+)\s*")


@dataclass
class Stmt:
    """One top-level statement: its text span and the model objects it made."""

    start: int
    end: int
    objs: list[Any]
    gap: str = ""  # the text between the previous statement and this one


@dataclass
class BflDocument:
    text: str
    form: Form
    statements: list[Stmt] = field(default_factory=list)
    tail: str = ""
    snapshots: dict[int, str] = field(default_factory=dict)
    header: FormHeader = field(default_factory=FormHeader)
    version: VersionLine | None = None


class _Malformed(FormError):
    """A statement the reader cannot read; it becomes an island, never escapes."""

    code = "QUILL-FORMS-BFL-UNREADABLE"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _known(  # noqa: C901 - one case per modifier
    name: str, args: list[Token], target: dict[str, Any], values: list[str]
) -> bool:
    """Store a modifier BAF knows under BAF's key; False if it is not one we can hold."""
    kinds = [a.type for a in args]
    if name in _FLAGS and not args:
        key, value = _FLAGS[name]
        target[key] = value
        return True
    if name in _VALUED and len(args) == 1 and kinds[0] in _VALUED[name][1]:
        target[_VALUED[name][0]] = values[0]
        return True
    if name in _ROWS and kinds == [L.NUMBER]:
        target[_ROWS[name]] = int(float(values[0]))
        return True
    if name == "default" and len(args) == 1 and kinds[0] in (L.STRING, L.NUMBER):
        target["default_value"] = values[0]
        return True
    if name == "autocomplete" and len(args) <= 1 and (not args or kinds[0] == L.STRING):
        target["autocomplete"] = values[0] if args else True
        return True
    if name in ("autocomplete_countries", "autocomplete_types"):
        target[name] = values
        return True
    if name == "spellcheck" and len(args) <= 1:
        target["spellcheck"] = (values[0].lower() in ("true", "yes", "1", "on")) if args else True
        return True
    if name == "capture" and len(args) <= 1:
        target["capture"] = values[0] if args else "environment"
        return True
    if name == "attr" and len(args) == 2 and is_safe_custom_attribute(values[0]):
        target.setdefault("custom_attributes", {})[values[0]] = values[1]
        return True
    if name in ("ajax", "honeypot") and not args:
        target[name] = True
        return True
    if name == "captcha" and len(args) <= 1 and (not args or kinds[0] == L.STRING):
        target["captcha"] = True
        if args:
            target["captcha_type"] = values[0]
        return True
    if name in ("save_and_continue", "rate_limit") and not args:
        target[name] = True
        return True
    if name in ("submit_label", "success_message", "redirect_url") and kinds == [L.STRING]:
        target[name] = values[0]
        return True
    if name == "choice_score" and len(args) == 2 and kinds[1] == L.NUMBER:
        target.setdefault("choice_scores", {})[values[0]] = float(values[1])
        return True
    if name == "setting" and kinds == [L.STRING, L.STRING]:
        try:
            target[values[0]] = json.loads(values[1])
        except ValueError:
            return False
        return True
    if name == "translate" and len(args) >= 3 and kinds[-1] == L.STRING:
        target.setdefault("translations", []).append(values)
        return True
    return False


_FIELD_KEYS = {
    "required": "required", "placeholder": "placeholder", "description": "help",
    "default_value": "default",
}  # fmt: skip


def _apply(item: Field, target: dict[str, Any]) -> None:
    for key, attr in _FIELD_KEYS.items():
        if key in target:
            setattr(item, attr, target.pop(key))
    if "choice_library" in target:
        item.choice_library = str(target.pop("choice_library"))
    for attr in ("visible_when", "calculate", "score", "default_expr"):
        if attr in target:
            setattr(item, attr, target.pop(attr))
    if "smart_default" in target:
        raw = str(target.pop("smart_default"))
        expression = smart_default_expression(raw)
        if expression is None:
            item.settings["smart_default"] = raw
        else:
            item.default_expr = expression
    if "cascade_from" in target or "cascade_library" in target:
        item.cascade = Cascade(
            source=str(target.pop("cascade_from", "")),
            library=target.pop("cascade_library", None),
            empty_message=str(target.pop("empty_message", "")),
            loading_message=str(target.pop("loading_message", "")),
        )
    for value, score in target.pop("choice_scores", {}).items():
        for choice in item.choices:
            if choice.value == value:
                choice.score = score
    item.settings.update(target)


def _and(a: str | None, b: str | None) -> str | None:
    if not a:
        return b
    if not b:
        return a
    return E.to_text(E.Logic("and", (E.parse(a), E.parse(b))))


class Cursor:
    """Where the reader is in the tokens, and the source lines around them."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.toks = tokenize(text)
        self.i = 0
        self.counter = 0
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", text)]

    # -- positions ------------------------------------------------------------
    def tok(self) -> Token:
        return self.toks[self.i]

    def at(self, kind: str, value: str | None = None) -> bool:
        t = self.toks[self.i]
        return t.type == kind and (value is None or t.value == value)

    def eof(self) -> bool:
        return self.toks[self.i].type == L.EOF

    def is_close(self) -> bool:
        return self.tok().type in _CLOSE or self.at(L.KEYWORD, "end")

    def is_open(self) -> bool:
        return self.tok().type in (L.BRACE_OPEN, L.BRACKET_OPEN) or self.at(L.KEYWORD, "begin")

    def line_of(self, pos: int) -> int:
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def indent_of(self, pos: int) -> int:
        start = self.line_starts[self.line_of(pos)]
        level = 0
        while start < len(self.text) and self.text[start] in " \t":
            level += 4 if self.text[start] == "\t" else 1
            start += 1
        return level

    def line_start(self, pos: int) -> int:
        return self.line_starts[self.line_of(pos)]

    def start_of(self, t: Token) -> int:
        """Where a statement starting at ``t`` begins: its line, unless it is mid-line."""
        start = self.line_start(t.pos)
        return start if not self.text[start : t.pos].strip() else t.pos

    def line_end(self, pos: int) -> int:
        end = self.text.find("\n", pos)
        end = len(self.text) if end < 0 else end
        return end - 1 if end > 0 and self.text[end - 1] == "\r" else end

    def skip_blank(self) -> None:
        while self.tok().type in (L.NEWLINE, L.INDENT):
            self.i += 1

    def same_line(self, a: int, b: int) -> bool:
        return self.line_of(a) == self.line_of(b)

    def new_id(self) -> str:
        self.counter += 1
        return f"field_{self.counter}"

    def span_end(self) -> int:
        prev = self.toks[self.i - 1] if self.i else self.toks[0]
        return self.line_end(prev.end - 1 if prev.end > prev.pos else prev.pos)

    def first_content(self) -> int:
        n = 0
        while self.toks[n].type in (L.NEWLINE, L.INDENT):
            n += 1
        return n

    def bare(self, t: Token) -> bool:
        return t.type == L.KEYWORD or self.text[t.pos] not in "\"'"

    def end_of_line_or_comment(self) -> bool:
        while self.at(L.COMMENT):
            self.i += 1
        return self.tok().type in (L.NEWLINE, L.EOF)

    # -- form, page, section, outcome -------------------------------------------
