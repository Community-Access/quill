"""Reading BFL into the form model: a port of QAF's ``QAF_BFL_Reader``.

BFL 1 is a readable notation of the model (QAF's ``docs/bfl-and-the-model.md``).
This reads it exactly as QAF does, statement for statement and key for key,
including every older spelling: the four block styles, inline and indented
modifiers, flat sections, the older type names and modifier spellings, the
older compiler's ``settings`` block, and the eight single-test conditions.
QAF's ``tests/conformance/qaf`` cases are the contract.

QUILL adds one thing QAF does not keep: **where each top-level statement
came from**, and the lines QAF skipped at the top level, which QUILL calls
*islands*. :mod:`bfl_document` uses both to write an edited document back
with every untouched byte unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.bfl_lex import ELEMENT_TYPES, Token, _php_string, field_type, php_numeric
from quill.core.forms.bfl_read_parts import (
    ITEM_ORDER,
    ReaderBase,
    legacy_smart_default,
    order,
)

VERSION = 1
_NOT_A_LIBRARY = (
    "form", "page", "library", "rule", "scoring", "confirmation", "notification",
    "translation", "settings", "if", "else", "end", "begin", "column",
)  # fmt: skip
SETTING_ALIASES = {
    "ajax": "ajax_submission",
    "honeypot": "enable_honeypot",
    "captcha": "enable_captcha",
}
TOP_ORDER = (
    "version", "id", "title", "description", "language", "settings", "choice_libraries", "pages",
    "rules", "scoring", "confirmations", "notifications", "translations", "extensions",
)  # fmt: skip


@dataclass
class Statement:
    """One top-level statement: its text span and what it made."""

    kind: str  # bfl, form, page, items, library, rule, scoring, confirmation, notification, translation, settings, mod, island  # noqa: E501
    start: int
    end: int
    #: page index (page), item ids (items), name (library), index (rule...), lang (translation)
    key: Any = None
    page: int | None = None
    indent: str = ""


@dataclass
class ReadResult:
    model: M.Model
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    source: str = ""
    statements: list[Statement] = field(default_factory=list)


def both(a: str, b: str) -> str:
    return E.canonical(E.to_text(E.op("and", [E.parse(a), E.parse(b)])))


class Reader(ReaderBase):
    def __init__(self) -> None:
        super().__init__()
        self.counter = 0
        self.model: M.Model = {}
        self.page: int | None = None
        self.page_declared = False
        self.owner = "form"
        self.statements: list[Statement] = []

    # -- whole document -----------------------------------------------------------
    def run(self, source: str) -> ReadResult:
        src = source.replace("\r\n", "\n").replace("\r", "\n")
        if src.startswith("﻿"):
            src = src[1:]
        self.src = src
        self.toks = self.lex(src)
        self.p = 0
        self.model = {"version": M.MODEL_VERSION, "title": "", "pages": []}
        self.parse_top()
        if not self.model["pages"]:
            self.model["pages"].append({"id": "page_1", "items": []})
        for page in self.model["pages"]:
            page["items"] = self.finish_items(page["items"])
        model = order(self.model, TOP_ORDER)
        return ReadResult(model, self.errors, self.warnings, src, self.statements)

    def current_page(self) -> int:
        if self.page is None:
            pages = self.model["pages"]
            pages.append({"id": f"page_{len(pages) + 1}", "items": []})
            self.page = len(pages) - 1
            self.page_declared = False
        return self.page

    def _record(self, kind: str, first: Token, key: Any = None, page: int | None = None) -> None:
        prev = self.toks[self.p - 1] if self.p > 0 else first
        line_start = self.src.rfind("\n", 0, first["start"]) + 1
        start = line_start if not self.src[line_start : first["start"]].strip() else first["start"]
        eol = self.src.find("\n", max(prev["end"] - 1, prev["start"]))
        end = len(self.src) if eol < 0 else eol
        if prev["t"] == "EOF" or end < start:
            end = max(start, prev["start"])
        indent = self.src[line_start : first["start"]] if start == line_start else ""
        self.statements.append(Statement(kind, start, end, key, page, indent))

    def parse_top(self) -> None:  # noqa: C901
        first = True
        while not self.at_end():
            t = self.peek()
            if first and self.is_word(t, "bfl") and t["first"]:
                self.next()
                v = self.peek()
                if v["t"] == "NUMBER" and v["line"] == t["line"]:
                    self.next()
                    if v["v"] > VERSION:
                        self.error(
                            t["line"],
                            f"This form is written in version {v['v']} of the QAF form language; "
                            f"this copy of QUILL reads version {VERSION} and older. Update QUILL "
                            "to open it.",
                        )
                        return
                else:
                    self.error(t["line"], 'The bfl line needs a version number, such as "bfl 1".')
                self._record("bfl", t)
                first = False
                continue
            first = False
            if self.is_close(t):
                self.next()
                self._record("close", t)
                continue
            if t["t"] == "MOD":
                self.next()
                if self.owner == "page" and self.page is not None:
                    self.page_mod(self.model["pages"][self.page], t)
                    self._record("page", t, self.page)
                else:
                    self.form_mod(t)
                    self._record("form", t)
                continue
            if t["t"] != "WORD":
                self.warn(
                    t["line"],
                    f'Skipped "{t["v"]}", which the QAF form language does not expect here.',
                )
                self.next()
                self._record("island", t)
                continue
            w = str(t["v"]).lower()
            simple: dict[str, Callable[[], Any]] = {
                "form": self.parse_form, "page": self.parse_page, "library": self.parse_library,
                "rule": self.parse_rule, "scoring": self.parse_scoring,
                "translation": self.parse_translation, "settings": self.parse_settings_block,
            }  # fmt: skip
            if w in simple:
                key = simple[w]()
                self._record(w, t, key, self.page if w == "page" else None)
                continue
            if w in ("confirmation", "notification"):
                key = self.parse_message_object(w)
                self._record(w, t, key)
                continue
            if self.starts_item(t):
                found = self.parse_item_statement(None)
                pi = self.current_page()
                self.model["pages"][pi]["items"].extend(found)
                self._record("items", t, [i["id"] for i in found], pi)
                continue
            self.warn(t["line"], f'Skipped "{t["v"]}", which the QAF form language does not know.')
            self.next()
            self._record("island", t)

    # -- form and pages --------------------------------------------------------------
    def parse_form(self) -> None:
        header = self.next()
        if self.peek()["t"] == "ID" and self.peek()["line"] == header["line"]:
            self.model["id"] = self.next()["v"]
        if self.peek()["t"] == "STRING" and self.peek()["line"] == header["line"]:
            self.model["title"] = self.next()["v"]
        self.owner = "form"
        self.header_with_open_block(header, self.form_mod)

    def header_with_open_block(self, header: Token, mod: Callable[[Token], None]) -> None:
        while not self.at_end():
            t = self.peek()
            if t["t"] == "MOD" and (
                t["line"] == header["line"]
                or (t["first"] and t["indent"] > header["indent"])
                or not t["first"]
            ):
                self.next()
                mod(t)
                continue
            if self.is_open(t) and (t["line"] == header["line"] or t["first"]):
                self.next()
            return

    def form_mod(self, mod: Token) -> None:
        name = str(mod["v"])
        has, value = self.mod_value(mod)
        if name in ("description", "desc"):
            self.model["description"] = _php_string(value)
            return
        if name == "language":
            self.model["language"] = _php_string(value)
            return
        if name == "extensions":
            if isinstance(value, (dict, list)):
                self.model["extensions"] = value
            else:
                self.error(mod["line"], "@extensions needs a JSON object.")
            return
        settings = self.model.setdefault("settings", {})
        if name in SETTING_ALIASES:
            settings[SETTING_ALIASES[name]] = True
            if name == "captcha" and has and isinstance(value, str):
                settings["captcha_type"] = value
            return
        settings[name.replace("-", "_")] = value if has else True

    def parse_page(self) -> int:
        header = self.next()
        pages = self.model["pages"]
        reuse = (
            self.page is not None
            and not self.page_declared
            and not pages[self.page]["items"]
            and len(pages) == 1
        )
        if not reuse:
            pages.append({"id": f"page_{len(pages) + 1}", "items": []})
            self.page = len(pages) - 1
        self.page_declared = True
        assert self.page is not None
        page = pages[self.page]
        if self.peek()["t"] == "ID" and self.peek()["line"] == header["line"]:
            page["id"] = self.next()["v"]
        if self.peek()["t"] == "STRING" and self.peek()["line"] == header["line"]:
            page["title"] = self.next()["v"]
        self.owner = "page"
        self.header_with_open_block(header, lambda m: self.page_mod(page, m))
        page["items"] = page.pop("items")
        return self.page

    def page_mod(self, page: dict[str, Any], mod: Token) -> None:
        name = str(mod["v"])
        if name == "when":
            expr = self.expression(self.raw_to_eol(mod), mod["line"])
            if expr is not None:
                page["when"] = expr
            return
        has, value = self.mod_value(mod)
        if name in ("description", "desc"):
            page["description"] = _php_string(value)
        elif name == "title":
            page["title"] = _php_string(value)
        else:
            page.setdefault("props", {})[name.replace("-", "_")] = value if has else True

    # -- items -------------------------------------------------------------------------
    def parse_item_statement(self, condition: str | None) -> list[M.Item]:
        w = str(self.peek()["v"]).lower()
        if w in ("if", "conditional"):
            return self.parse_if(condition)
        item = (
            self.parse_section()
            if w == "section"
            else self.parse_columns()
            if w == "columns"
            else self.parse_field()
        )
        if condition is not None:
            item["when"] = both(condition, item["when"]) if "when" in item else condition
            item = order(item, ITEM_ORDER)
        return [item]

    def parse_if(self, outer: str | None) -> list[M.Item]:
        header = self.next()
        text = self.raw_to_eol(header, True)
        cond = self.expression(text, header["line"]) or "false"
        full = cond if outer is None else both(outer, cond)

        def skip_mod(t: Token) -> None:
            self.warn(t["line"], f"An if block holds items, not modifiers; @{t['v']} was skipped.")
            self.mod_value(t)

        found, _ = self.container(header, full, skip_mod)
        t = self.peek()
        if self.is_word(t, "else") and (not t["first"] or t["indent"] == header["indent"]):
            self.next()
            negated = E.canonical(E.to_text(E.op("not", [E.parse(cond)])))
            other = negated if outer is None else both(outer, negated)
            more, _ = self.container(t, other, lambda m: self.mod_value(m) and None)
            found.extend(more)
        return found

    def auto_id(self) -> str:
        self.counter += 1
        return f"field_{self.counter}"

    def header_id_label(
        self, header: Token, item: dict[str, Any], label_key: str = "label"
    ) -> None:
        auto = self.auto_id()
        if self.peek()["t"] == "ID" and self.peek()["line"] == header["line"]:
            item["id"] = self.next()["v"]
        else:
            item["id"] = auto
        if self.peek()["t"] == "STRING" and self.peek()["line"] == header["line"]:
            item[label_key] = self.next()["v"]

    def parse_section(self) -> M.Item:
        header = self.next()
        section: dict[str, Any] = {"type": "section"}
        self.header_id_label(header, section)
        found, mode = self.container(header, None, lambda m: self.item_mod(section, m))
        section["items"] = found
        if mode != "explicit" and not found:
            section["__flat"] = True
        return order(section, ITEM_ORDER)

    def parse_columns(self) -> M.Item:
        header = self.next()
        item: dict[str, Any] = {"type": "columns"}
        self.header_id_label(header, item)
        item.pop("label", None)
        count = None
        if self.peek()["t"] == "NUMBER" and self.peek()["line"] == header["line"]:
            count = self.next()["v"]
        columns: list[dict[str, Any]] = []

        def column(t: Token) -> bool:
            self.next()
            col: dict[str, Any] = {}

            def col_mod(m: Token) -> None:
                _has, value = self.mod_value(m)
                if m["v"] == "width":
                    col["width"] = _php_string(value)
                else:
                    self.warn(m["line"], f"A column has only a width; @{m['v']} was skipped.")

            col["items"], _ = self.container(t, None, col_mod)
            columns.append(col)
            return True

        stray, _ = self.container(
            header, None, lambda m: self.item_mod(item, m), {"column": column}
        )
        if stray:
            self.warn(
                header["line"],
                "Fields directly inside columns belong in a column; they were put in the last column.",  # noqa: E501
            )
            if not columns:
                columns.append({"items": []})
            columns[-1]["items"].extend(stray)
        if not columns:
            columns.append({"items": []})
        if count is not None and count != len(columns):
            self.warn(
                header["line"], f"This columns layout says {count} columns and has {len(columns)}."
            )
        item["columns"] = columns
        return order(item, ITEM_ORDER)

    def parse_field(self) -> M.Item:
        header = self.next()
        word = str(header["v"]).lower()
        item: dict[str, Any] = {"type": field_type(word)}
        self.header_id_label(header, item)
        if word in ELEMENT_TYPES:
            item.setdefault("props", {})["element"] = word
        nxt = self.peek()
        if (
            item["type"] in (*M.CHOICE_TYPES, "likert")
            and nxt["t"] == "WORD"
            and nxt["line"] == header["line"]
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(nxt["v"]))
            and not self.starts_item(nxt)
            and str(nxt["v"]).lower() not in _NOT_A_LIBRARY
        ):
            # The language guide's spelling of a library: select "Country" countries.
            item["choice_library"] = self.next()["v"]
        choices: list[dict[str, Any]] = []
        children: list[M.Item] = []

        def on(kind: str, t: Token) -> bool:
            if kind == "mod":
                self.item_mod(item, t)
                return True
            if kind == "choice":
                c = self.choice(t)
                if c:
                    choices.append(c)
                return True
            if item["type"] == "repeater" and self.starts_item(t):
                children.extend(self.parse_item_statement(None))
                return True
            return False

        self.body(header, on)
        if choices:
            item["choices"] = choices
        if item["type"] == "repeater":
            item["items"] = children
        if item["type"] == "checkbox" and not any(
            k in item for k in ("choices", "choice_library", "cascade")
        ):
            item["choices"] = [{"value": "yes", "label": "Yes"}]
        return order(item, ITEM_ORDER)


def read(source: str) -> ReadResult:
    """BFL text to ``ReadResult(model, errors, warnings, ...)``; never raises."""
    return Reader().run(str(source))


def to_model(source: str) -> M.Model:
    """BFL text to the model; raises :class:`FormError` on the first error."""
    from quill.core.forms.errors import BflError

    result = read(source)
    if result.errors:
        first = result.errors[0]
        raise BflError(f"Line {first['line']}: {first['message']}", first["line"])
    return result.model


__all__ = [
    "Reader",
    "ReadResult",
    "Statement",
    "legacy_smart_default",
    "php_numeric",
    "read",
    "to_model",
]
