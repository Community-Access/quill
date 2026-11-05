"""BAF's own BFL formatter, ported exactly from ``class-baf-bfl-formatter.php``.

``baf_format(text)`` returns, byte for byte, what BAF's "Format" action makes
of a BFL document. It is here for conformance and so QUILL can show a person
what BAF would do to their form; QUILL never uses it to write a document,
because BAF's formatter loses things (conditions, columns, most modifiers and
every choice library reference spelled as a keyword). The conformance report
lists them. QUILL's own writer is :mod:`quill.core.forms.bfl_write`.

BAF's parser never reports an error, so its fallback ``basic_format`` is
unreachable and is not ported.
"""

from __future__ import annotations

import re
from typing import Any

from quill.core.forms.baf_parser import baf_parse, sanitize_title

_SETTING_MAP = (
    ("enable_honeypot", "honeypot"),
    ("enable_captcha", "captcha"),
    ("ajax_submission", "ajax"),
    ("save_continue_enabled", "saveAndContinue"),
    ("rate_limit_enabled", "rateLimit"),
    ("captcha_type", "captchaType"),
)


def php_empty(value: Any) -> bool:
    """PHP's ``empty()``: None, False, 0, "", "0" and empty arrays."""
    return (
        value is None
        or value is False
        or value == 0
        or value in ("", "0")
        or value == []
        or value == {}
    )


def php_str(value: Any) -> str:
    """PHP's string conversion: True is "1", False is ""."""
    if value is True:
        return "1"
    if value is False or value is None:
        return ""
    return str(value)


def _escape(value: Any) -> str:
    text = php_str(value)
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return (
        isinstance(value, str)
        and re.fullmatch(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", value) is not None
    )


class BafFormatter:
    def __init__(
        self,
        *,
        use_tabs: bool = False,
        indent_size: int | None = None,
        add_spacing: bool = True,
        align_values: bool = True,
    ) -> None:
        self.indent = "\t" if use_tabs else "  "
        if indent_size is not None and not use_tabs:
            self.indent = " " * indent_size
        self.add_spacing = add_spacing
        self.align_values = align_values
        self.level = 0

    def line(self, content: str) -> str:
        return self.indent * self.level + content

    def format(self, source: str) -> str:
        return self.compile(baf_parse(source)["form"])

    def compile(self, form: dict[str, Any]) -> str:
        self.level = 0
        out = ['form "' + _escape(form.get("title", "Untitled Form")) + '"']
        if not php_empty(form.get("description")):
            self.level = 1
            out.append(self.line('@description "' + _escape(form["description"]) + '"'))
            self.level = 0
        if not php_empty(form.get("settings")):
            settings = self.settings(form["settings"])
            if settings:
                if self.add_spacing:
                    out.append("")
                out.append(settings)
        pages = form.get("pages") or [{"id": "page_1", "title": ""}]
        by_page: dict[str, list[dict[str, Any]]] = {}
        for field in form.get("fields", []):
            by_page.setdefault(field.get("page", "page_1"), []).append(field)
        for page in pages:
            if self.add_spacing:
                out.append("")
            out.append(self.page(page, by_page))
        return "\n".join(out)

    def settings(self, settings: dict[str, Any]) -> str:
        relevant = {
            bfl: settings[key]
            for key, bfl in _SETTING_MAP
            if key in settings and not php_empty(settings[key])
        }
        if not relevant:
            return ""
        self.level = 1
        lines = [self.line("settings")]
        self.level = 2
        width = max(len(k) for k in relevant)
        for key, value in relevant.items():
            pad = " " * (width - len(key)) if self.align_values else ""
            lines.append(self.line(key + pad + " " + self.value(value)))
        self.level = 0
        return "\n".join(lines)

    @staticmethod
    def value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if _is_numeric(value):
            return str(value)
        if isinstance(value, str):
            return '"' + _escape(value) + '"'
        return "null"

    def page(self, page: dict[str, Any], by_page: dict[str, list[dict[str, Any]]]) -> str:
        title = page.get("title", "")
        lines: list[str] = []
        if not php_empty(title):
            self.level = 1
            lines.append(self.line('page "' + _escape(title) + '"'))
            self.level = 2
        else:
            self.level = 1
        current = None
        for field in by_page.get(page.get("id", "page_1"), []):
            if field.get("type", "") == "section":
                if current is not None and self.add_spacing:
                    lines.append("")
                lines.append(self.section(field))
                current = field
                self.level += 1
            else:
                lines.append(self.field(field))
        return "\n".join(x for x in lines if not php_empty(x))

    def section(self, section: dict[str, Any]) -> str:
        text = self.line('section "' + _escape(section.get("label", "Section")) + '"')
        if not php_empty(section.get("description")):
            self.level += 1
            text += "\n" + self.line('@description "' + _escape(section["description"]) + '"')
            self.level -= 1
        return text

    def field(self, field: dict[str, Any]) -> str:
        kind = field.get("type", "text")
        if kind in ("section", "page"):
            return ""
        head = php_str(kind)
        ident = php_str(field.get("id", ""))
        if ident and not re.fullmatch(r"field_\d+", ident):
            head += " #" + ident
        if not php_empty(field.get("label")):
            head += ' "' + _escape(field["label"]) + '"'
        lines = [self.line(head)]
        self.level += 1
        for modifier in self.modifiers(field):
            lines.append(self.line(modifier))
        choices = field.get("choices")
        if not php_empty(choices) and isinstance(choices, (list, dict)):
            for choice_line in self.choices(choices):
                lines.append(self.line(choice_line))
        self.level -= 1
        return "\n".join(x for x in lines if not php_empty(x))

    @staticmethod
    def modifiers(field: dict[str, Any]) -> list[str]:
        out: list[str] = []

        def present(key: str) -> bool:
            return key in field and field[key] is not None and field[key] != ""

        if not php_empty(field.get("required")):
            out.append("@required")
        if not php_empty(field.get("placeholder")):
            out.append('@placeholder "' + _escape(field["placeholder"]) + '"')
        if present("default_value"):
            out.append('@default "' + _escape(field["default_value"]) + '"')
        if not php_empty(field.get("description")):
            out.append('@description "' + _escape(field["description"]) + '"')
        for key, word in (
            ("min", "min"),
            ("max", "max"),
            ("min_length", "minlength"),
            ("max_length", "maxlength"),
        ):
            if present(key):
                out.append(f"@{word} " + php_str(field[key]))
        if not php_empty(field.get("rows")):
            out.append("@rows " + php_str(field["rows"]))
        if not php_empty(field.get("read_only")):
            out.append("@readonly")
        if not php_empty(field.get("disabled")):
            out.append("@disabled")
        for key, word in (
            ("css_class", "class"),
            ("input_mask", "mask"),
            ("autocomplete", "autocomplete"),
        ):
            if not php_empty(field.get(key)):
                out.append(f'@{word} "' + _escape(field[key]) + '"')
        return out

    @staticmethod
    def choices(choices: Any) -> list[str]:
        if isinstance(choices, dict) and "library" in choices:
            return ["@library " + php_str(choices["library"])]
        lines: list[str] = []
        for choice in choices.values() if isinstance(choices, dict) else choices:
            if isinstance(choice, dict):
                label = php_str(choice.get("label", ""))
                value = php_str(choice.get("value", ""))
                price = choice.get("price", "")
                if not php_empty(price):
                    lines.append("+ " + label + ":" + php_str(price))
                elif not php_empty(value) and value != sanitize_title(label):
                    lines.append("+ " + value + "|" + label)
                else:
                    lines.append("+ " + label)
            else:
                lines.append("+ " + php_str(choice))
        return lines


def baf_format(source: str, **options: Any) -> str:
    """``BAF_BFL_Formatter::format``: BFL text as BAF re-prints it."""
    return BafFormatter(**options).format(source)


def baf_minify(source: str) -> str:
    """``BAF_BFL_Formatter::minify``: trimmed lines, no blanks or comments."""
    out = []
    for line in source.split("\n"):
        text = line.strip(" \t\n\r\0\x0b")
        if php_empty(text) or text.startswith(("//", "#")):
            continue
        out.append(text)
    return "\n".join(out)
