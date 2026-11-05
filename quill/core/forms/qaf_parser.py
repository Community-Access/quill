"""What QAF makes of BFL: a faithful port of ``class-qaf-bfl-parser.php``.

This is not QUILL's reader (that is :mod:`quill.core.forms.bfl_read`, which
keeps every byte and builds the form model). It is an oracle: given BFL, it
returns the same nested ``dict`` QAF's PHP parser returns on the site, key for
key, including QAF's quirks (numbers kept as strings, ``field_N`` ids counted
across fields, sections and columns, unknown tokens skipped silently).

Two uses: the conformance tests compare it with QAF's own PHP, and Check This
Form can compare QUILL's reading of a document with QAF's, to say "the site
will ignore this line" before anyone publishes.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from quill.core.forms import bfl_lexer as L
from quill.core.forms.bfl_lexer import Token, tokenize

_CHOICE_FIELDS = frozenset((
    "select",
    "dropdown",
    "multiselect",
    "radio",
    "checkbox",
    "checkboxes",
    "likert",
    "ranking",
))
ALIASES = {
    "dropdown": "select",
    "paragraph": "textarea",
    "url": "website",
    "checkboxes": "checkbox",
    "file": "fileupload",
    "savebutton": "save",
}
OPERATORS = {
    "is": "equals",
    "contains": "contains",
    "starts": "starts_with",
    "ends": "ends_with",
    "greater": "greater_than",
    "less": "less_than",
    "empty": "is_empty",
    "filled": "is_not_empty",
}
_EVENT_HANDLERS = frozenset(
    "onclick ondblclick onmousedown onmouseup onmouseover onmousemove onmouseout "
    "onmouseenter onmouseleave onkeydown onkeyup onkeypress onfocus onblur onchange "
    "oninput onsubmit onreset onload onunload onerror onresize onscroll ondrag "
    "ondragstart ondragend ondragover ondragenter ondragleave ondrop oncopy oncut "
    "onpaste oncontextmenu onwheel ontouchstart ontouchend ontouchmove ontouchcancel "
    "onpointerdown onpointerup onpointermove onpointerenter onpointerleave".split()
)
_BLOCKED_ATTRS = frozenset(
    "style href src action formaction xlink:href srcdoc data dynsrc lowsrc background".split()
)
_ALLOWED_ATTRS = frozenset(
    "title lang dir translate contenteditable draggable spellcheck tabindex "
    "accesskey role slot part".split()
)

# Modifier -> (config key, accepted token types). Value-taking modifiers only.
_S, _N, _K, _I = L.STRING, L.NUMBER, L.KEYWORD, L.IDENTIFIER
_VALUED: dict[str, tuple[str, tuple[str, ...]]] = {
    "placeholder": ("placeholder", (_S,)),
    "description": ("description", (_S,)),
    "desc": ("description", (_S,)),
    "min": ("min", (_N,)),
    "max": ("max", (_N,)),
    "minlength": ("min_length", (_N,)),
    "maxlength": ("max_length", (_N,)),
    "rows": ("rows", (_N,)),
    "size": ("size", (_S,)),
    "class": ("css_class", (_S,)),
    "css": ("css_class", (_S,)),
    "mask": ("input_mask", (_S,)),
    "autocomplete_provider": ("autocomplete_provider", (_S, _K)),
    "smart_default": ("smart_default", (_S,)),
    "unique_scope": ("unique_scope", (_S, _K)),
    "unique_message": ("unique_message", (_S,)),
    "library": ("choice_library", (_S, _K)),
    "cascade_from": ("cascade_from", (_S, _I)),
    "cascadefrom": ("cascade_from", (_S, _I)),
    "cascade_library": ("cascade_library", (_S, _K)),
    "cascadelibrary": ("cascade_library", (_S, _K)),
    "empty_message": ("empty_message", (_S,)),
    "emptymessage": ("empty_message", (_S,)),
    "loading_message": ("loading_message", (_S,)),
    "loadingmessage": ("loading_message", (_S,)),
    "format": ("format", (_S,)),
    "step": ("step", (_N,)),
    "prefix": ("prefix", (_S,)),
    "suffix": ("suffix", (_S,)),
    "pattern": ("pattern", (_S,)),
    "accept": ("accept", (_S,)),
    "cols": ("cols", (_N,)),
    "inputmode": ("inputmode", (_S, _K)),
    "enterkeyhint": ("enterkeyhint", (_S, _K)),
}
_FLAGS: dict[str, tuple[str, Any]] = {
    "required": ("required", True),
    "readonly": ("read_only", True),
    "disabled": ("disabled", True),
    "admin": ("admin_only", True),
    "admin-only": ("admin_only", True),
    "hidden": ("visibility", "hidden"),
    "confirm": ("confirm_email", True),
    "multiple": ("multiple", True),
    "allow-other": ("allow_other", True),
    "allowother": ("allow_other", True),
    "autofocus": ("autofocus", True),
    "unique": ("unique", True),
    "searchable": ("searchable", True),
}
_ROWS = {
    "min_rows": "min_rows",
    "minrows": "min_rows",
    "max_rows": "max_rows",
    "maxrows": "max_rows",
}


def sanitize_title(title: str) -> str:
    """WordPress's ``sanitize_title`` for the strings BFL choices produce.

    Mirrors the stub in ``tests/unit/core/forms/baf_php_harness.php``: accents
    are removed, other non-ASCII is percent-encoded in lower-case hex, and
    anything but letters, digits, spaces, ``_`` and ``-`` is dropped.
    """
    if re.search(r"[^\x00-\x7f]", title):
        title = "".join(
            c for c in unicodedata.normalize("NFKD", title) if unicodedata.category(c) != "Mn"
        )
    title = re.sub(r"<[^>]*>", "", title)
    title = re.sub(r"%([a-fA-F0-9][a-fA-F0-9])", r"---\1---", title)
    title = title.replace("%", "")
    title = re.sub(r"---([a-fA-F0-9][a-fA-F0-9])---", r"%\1", title)
    if re.search(r"[^\x00-\x7f]", title):
        title = "".join(
            c if ord(c) < 128 else "".join(f"%{b:02x}" for b in c.encode("utf-8"))
            for c in title.lower()
        )
    title = title.lower()
    title = re.sub(r"&.+?;", "", title)
    title = title.replace(".", "-")
    title = re.sub(r"[^%a-z0-9 _-]", "", title)
    title = re.sub(r"\s+", "-", title)
    title = re.sub(r"-+", "-", title)
    return title.strip("-")


def split_choice(text: str) -> dict[str, str]:
    """One ``+`` line's value, label and price, as QAF reads them."""
    if "|" in text:
        value, label = text.split("|", 1)
        return {"value": value.strip(), "label": label.strip()}
    if ":" in text:
        label, price = text.split(":", 1)
        return {
            "value": sanitize_title(label.strip()),
            "label": label.strip(),
            "price": price.strip(),
        }
    return {"value": sanitize_title(text), "label": text}


def is_safe_custom_attribute(name: str) -> bool:
    name = name.strip().lower()
    if name in _EVENT_HANDLERS or name in _BLOCKED_ATTRS:
        return False
    return name.startswith(("data-", "aria-")) or name in _ALLOWED_ATTRS


class BafParser:
    """BFL to QAF's form configuration, exactly as the PHP does it."""

    def __init__(self) -> None:
        self.toks: list[Token] = []
        self.p = 0
        self.page = 0
        self.counter = 0
        self.form: dict[str, Any] = {}

    # -- token helpers (names follow the PHP) --------------------------------
    def at_end(self) -> bool:
        return self.p >= len(self.toks) or self.toks[self.p].type == L.EOF

    def peek(self) -> Token:
        return self.toks[self.p]

    def check(self, kind: str) -> bool:
        return not self.at_end() and self.toks[self.p].type == kind

    def check_kw(self, word: str) -> bool:
        return self.check(L.KEYWORD) and self.peek().value == word

    def advance(self) -> Token:
        if not self.at_end():
            self.p += 1
        return self.toks[self.p - 1]

    def skip_trivia(self) -> None:
        while not self.at_end() and self.peek().type in (L.NEWLINE, L.INDENT, L.COMMENT):
            self.advance()

    def skip_ws(self) -> None:
        while not self.at_end() and self.peek().type in (L.NEWLINE, L.COMMENT):
            self.advance()

    def skip_to_next_line(self) -> None:
        while not self.at_end() and self.peek().type != L.NEWLINE:
            self.advance()
        if self.check(L.NEWLINE):
            self.advance()

    def indent(self) -> int:
        return self.peek().level if self.check(L.INDENT) else 0

    def try_open(self) -> bool:
        if self.check(L.BRACE_OPEN) or self.check(L.BRACKET_OPEN) or self.check_kw("begin"):
            self.advance()
            return True
        return False

    def is_close(self) -> bool:
        return self.check(L.BRACE_CLOSE) or self.check(L.BRACKET_CLOSE) or self.check_kw("end")

    def consume_close(self) -> None:
        if self.is_close():
            self.advance()

    def field_start(self) -> bool:
        return self.check(L.KEYWORD) and self.peek().value in L.QAF_FIELD_TYPES

    def next_id(self) -> str:
        self.counter += 1
        return f"field_{self.counter}"

    def page_id(self) -> str:
        return f"page_{self.page + 1}"

    # -- grammar --------------------------------------------------------------
    def parse(self, source: str) -> dict[str, Any]:
        self.toks = tokenize(source)
        self.p = self.page = self.counter = 0
        self.form = {
            "title": "",
            "description": "",
            "fields": [],
            "pages": [{"id": "page_1", "title": ""}],
            "settings": {},
            "conditional_logic": [],
        }
        while not self.at_end():
            self.skip_ws()
            if self.at_end():
                break
            tok = self.peek()
            if tok.type == L.COMMENT:
                self.advance()
            elif self.check_kw("form"):
                self.form_declaration()
            elif self.check_kw("page"):
                self.page_break()
            elif self.check_kw("section"):
                self.section()
            elif self.check_kw("columns"):
                self.columns()
            elif self.check_kw("if") or self.check_kw("conditional"):
                self.conditional()
            elif self.field_start():
                field = self.field()
                field["page"] = self.page_id()
                self.form["fields"].append(field)
            else:
                self.advance()
        return {"form": self.form, "errors": []}

    def form_declaration(self) -> None:
        self.advance()
        if self.check(L.STRING):
            self.form["title"] = self.advance().value
        self.skip_ws()
        settings = self.form["settings"]
        while self.check(L.MODIFIER):
            name = self.advance().value
            self.skip_ws()
            if name in ("description", "desc"):
                if self.check(L.STRING):
                    self.form["description"] = self.advance().value
            elif name == "ajax":
                settings["ajax_submission"] = True
            elif name == "honeypot":
                settings["enable_honeypot"] = True
            elif name == "captcha":
                settings["enable_captcha"] = True
                if self.check(L.STRING):
                    settings["captcha_type"] = self.advance().value

    def page_break(self) -> None:
        self.advance()
        self.page += 1
        page: dict[str, Any] = {"id": self.page_id(), "title": ""}
        if self.check(L.STRING):
            page["title"] = self.advance().value
        self.skip_ws()
        while self.check(L.MODIFIER):
            name = self.advance().value
            if name in ("description", "desc"):
                self.skip_ws()
                if self.check(L.STRING):
                    page["description"] = self.advance().value
        self.form["pages"].append(page)

    def section(self) -> None:
        self.advance()
        field: dict[str, Any] = {"id": self.next_id(), "type": "section"}
        if self.check(L.STRING):
            field["label"] = self.advance().value
        field = self.modifiers(field)
        field["page"] = self.page_id()
        self.form["fields"].append(field)

    def columns(self) -> None:
        self.advance()
        field: dict[str, Any] = {"id": self.next_id(), "type": "columns", "columns": []}
        if self.check(L.NUMBER):
            field["column_count"] = _php_int(self.advance().value)
        self.skip_trivia()
        if self.try_open():
            while not self.at_end():
                self.skip_trivia()
                if self.is_close():
                    self.consume_close()
                    break
                if self.check_kw("column"):
                    self.advance()
                    if self.try_open():
                        fields = self.field_list_in_block()
                        self.consume_close()
                    else:
                        fields = self.column_content(self.indent())
                    field["columns"].append(fields)
                    continue
                self.advance()
        else:
            self.skip_to_next_line()
            base = self.indent()
            while not self.at_end():
                self.skip_ws()
                if self.is_close():
                    break
                level = self.indent()
                if level <= base:
                    break
                if self.check_kw("column"):
                    self.advance()
                    field["columns"].append(self.column_content(level))
                else:
                    break
        field["page"] = self.page_id()
        self.form["fields"].append(field)

    def column_content(self, base: int) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        self.skip_to_next_line()
        while not self.at_end():
            self.skip_ws()
            if self.is_close() or self.indent() <= base or not self.field_start():
                break
            fields.append(self.field())
        return fields

    def field_list_in_block(self) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        while not self.at_end():
            self.skip_trivia()
            if self.is_close():
                break
            if self.field_start():
                fields.append(self.field())
                continue
            self.advance()
        return fields

    def _conditional_field(self, rules: list[dict[str, Any]]) -> None:
        field = self.field()
        field["conditional_logic"] = {
            "enabled": True,
            "action": "show",
            "logic": "all",
            "rules": rules,
        }
        field["page"] = self.page_id()
        self.form["fields"].append(field)

    def conditional(self) -> None:
        self.advance()
        rules = self.condition()
        self.skip_trivia()
        if self.try_open():
            while not self.at_end():
                self.skip_trivia()
                if self.is_close():
                    self.consume_close()
                    break
                if self.field_start():
                    self._conditional_field(rules)
                    continue
                self.advance()
            return
        self.skip_to_next_line()
        base = self.indent()
        while not self.at_end():
            self.skip_ws()
            if self.is_close() or self.indent() <= base:
                break
            if self.field_start():
                self._conditional_field(rules)
            else:
                self.advance()

    def condition(self) -> list[dict[str, Any]]:
        if not self.check(L.IDENTIFIER):
            return []
        field_id = self.advance().value
        self.skip_ws()
        operator = "is"
        if self.check(L.KEYWORD):
            operator = OPERATORS.get(self.advance().value, operator)
        value = ""
        self.skip_ws()
        if operator not in ("is_empty", "is_not_empty") and (
            self.check(L.STRING) or self.check(L.NUMBER)
        ):
            value = self.advance().value
        return [{"field": field_id, "operator": operator, "value": value}]

    def field(self) -> dict[str, Any]:
        kind = self.advance().value
        kind = ALIASES.get(kind, kind)
        field: dict[str, Any] = {"id": self.next_id(), "type": kind}
        self.skip_ws()
        if self.check(L.IDENTIFIER):
            field["id"] = self.advance().value
        self.skip_ws()
        if self.check(L.STRING):
            field["label"] = self.advance().value
        if kind in _CHOICE_FIELDS:
            field["choices"] = self.choices()
        return self.modifiers(field)

    def _list(self) -> list[str]:
        items: list[str] = []
        if self.check(L.BRACKET_OPEN):
            self.advance()
            while not self.at_end() and not self.check(L.BRACKET_CLOSE):
                if self.check(L.STRING) or self.check(L.KEYWORD):
                    items.append(self.advance().value)
                    continue
                self.advance()
            if self.check(L.BRACKET_CLOSE):
                self.advance()
        return items

    def modifiers(self, field: dict[str, Any]) -> dict[str, Any]:
        self.skip_trivia()
        explicit = self.try_open()
        while not self.at_end():
            self.skip_trivia()
            if explicit and self.is_close():
                self.consume_close()
                break
            if not explicit and not (
                self.check(L.MODIFIER) or self.check(L.INDENT) or self.check(L.NEWLINE)
            ):
                break
            if self.check(L.INDENT) or self.check(L.NEWLINE):
                self.advance()
                continue
            if not self.check(L.MODIFIER):
                if explicit:
                    self.advance()
                    continue
                break
            name = self.advance().value
            self.skip_trivia()
            self.modifier(field, name)
            self.skip_trivia()
        return field

    def modifier(self, field: dict[str, Any], name: str) -> None:
        if name in _FLAGS:
            key, value = _FLAGS[name]
            field[key] = value
        elif name in _VALUED:
            key, kinds = _VALUED[name]
            if any(self.check(k) for k in kinds):
                field[key] = self.advance().value
        elif name == "default":
            self.skip_ws()
            if self.check(L.STRING) or self.check(L.NUMBER):
                field["default_value"] = self.advance().value
        elif name == "autocomplete":
            field["autocomplete"] = self.advance().value if self.check(L.STRING) else True
        elif name in ("autocomplete_countries", "autocomplete_types"):
            field[name] = self._list()
        elif name == "spellcheck":
            if self.check(L.STRING) or self.check(L.KEYWORD):
                value = self.advance().value.lower()
                field["spellcheck"] = value in ("true", "yes", "1", "on")
            else:
                field["spellcheck"] = True
        elif name == "capture":
            if self.check(L.STRING) or self.check(L.KEYWORD):
                field["capture"] = self.advance().value
            else:
                field["capture"] = "environment"
        elif name == "attr":
            self._attr(field)
        elif name in _ROWS:
            if self.check(L.NUMBER):
                field[_ROWS[name]] = _php_int(self.advance().value)

    def _attr(self, field: dict[str, Any]) -> None:
        attr_name: str | None = None
        attr_value: Any = None
        if self.check(L.STRING) or self.check(L.KEYWORD) or self.check(L.IDENTIFIER):
            attr_name = self.advance().value
        self.skip_ws()
        if self.check(L.STRING) or self.check(L.NUMBER):
            attr_value = self.advance().value
        elif self.check(L.KEYWORD) and self.peek().value.lower() in ("true", "false"):
            attr_value = self.advance().value.lower() == "true"  # unreachable in QAF
        if attr_name is not None and attr_value is not None and is_safe_custom_attribute(attr_name):
            field.setdefault("custom_attributes", {})[attr_name] = attr_value

    def choices(self) -> Any:
        self.skip_ws()
        if self.check(L.KEYWORD) and self.peek().value in L.LIBRARY_KEYWORDS:
            return {"library": self.advance().value}
        out: list[dict[str, str]] = []
        if self.try_open():
            while not self.at_end():
                self.skip_trivia()
                if self.is_close():
                    self.consume_close()
                    break
                if not self.check(L.CHOICE):
                    self.advance()
                    continue
                out.append(split_choice(self.advance().value))
            return out
        self.skip_to_next_line()
        while self.check(L.CHOICE) or self.check(L.INDENT) or self.check(L.NEWLINE):
            tok = self.advance()
            if tok.type == L.CHOICE:
                out.append(split_choice(tok.value))
        return out


def _php_int(text: str) -> int:
    """PHP's ``(int)`` of a numeric token: leading integer part."""
    match = re.match(r"-?\d+", text)
    return int(match.group(0)) if match else 0


def qaf_parse(source: str) -> dict[str, Any]:
    """QAF's ``QAF_BFL_Parser::parse``: ``{"form": {...}, "errors": []}``."""
    return BafParser().parse(source)
