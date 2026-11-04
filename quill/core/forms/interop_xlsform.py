"""XLSForm in and out (https://xlsform.org): the spreadsheet form standard.

The ``survey`` sheet's rows become fields (``begin group`` / ``end group``
become sections, ``begin repeat`` a repeater), the ``choices`` sheet their
choices, and ``settings`` the title and language. ``relevant`` becomes
``visible_when`` and ``calculation`` becomes ``calculate``, converted from
XLSForm's XPath style (``${age} > 17``, ``selected(${q}, 'a')``). Columns
such as ``label::French (fr)`` become translations.

The workbook is read and written with ``openpyxl``, which QUILL already
depends on for spreadsheets; it is imported only when an XLSForm is used.
Rows are also accepted as plain lists of dicts, which is what the tests use.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_common import ImportResult, convert_expression, safe_id
from quill.core.forms.model import Choice, Columns, Field, Form, Island, Item, Section

_TYPES = {
    "text": "text", "integer": "number", "decimal": "number", "date": "date", "time": "time",
    "datetime": "datetime", "note": "html", "calculate": "calculation", "image": "fileupload",
    "file": "fileupload", "audio": "fileupload", "video": "fileupload", "geopoint": "map",
    "acknowledge": "consent", "range": "range", "hidden": "hidden", "barcode": "text",
    "select_one": "radio", "select_multiple": "checkbox", "rank": "ranking",
}  # fmt: skip
_BACK = {
    "text": "text", "textarea": "text", "number": "decimal", "date": "date", "time": "time",
    "datetime": "datetime", "html": "note", "calculation": "calculate", "fileupload": "file",
    "map": "geopoint", "consent": "acknowledge", "range": "range", "hidden": "hidden",
    "radio": "select_one", "select": "select_one", "checkbox": "select_multiple",
    "multiselect": "select_multiple", "ranking": "rank", "email": "text", "phone": "text",
    "website": "text",
}  # fmt: skip
_REWRITES = [
    (r"selected\(\s*\$\{([A-Za-z0-9_]+)\}\s*,\s*('[^']*'|\"[^\"]*\")\s*\)", r"#\1 is \2"),
    (r"\$\{([A-Za-z0-9_]+)\}", r"#\1"),
    (r"\btoday\(\)", "today"),
    (r"\bdiv\b", "/"),
    (r"\bmod\b", "%"),
    (r"\bnot\(", "not ("),
]
_LANG = re.compile(r"^(label|hint)::(.+?)(?:\s*\(([A-Za-z-]+)\))?$")


def _lang_code(name: str, code: str | None) -> str:
    return (code or name).strip().lower()[:8] or "und"


def import_rows(
    survey: list[dict[str, Any]],
    choices: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> ImportResult:
    report: list[str] = []
    form = Form()
    settings = settings or {}
    form.title = str(settings.get("form_title", ""))
    form.id = str(settings.get("form_id", ""))
    lists: dict[str, list[dict[str, Any]]] = {}
    for row in choices:
        if row.get("list_name"):
            lists.setdefault(str(row["list_name"]).strip(), []).append(row)
    taken: set[str] = set()
    page = form.pages[0]
    stack: list[list[Item]] = [page.items]
    repeat: list[Field] = []

    def convert(raw: Any, where: str) -> str | None:
        if raw in (None, ""):
            return None
        out = convert_expression(str(raw), _REWRITES)
        if out is None:
            report.append(f"The rule on {where} could not be converted: {raw}")
        return out

    for number, row in enumerate(survey, 2):
        raw_type = str(row.get("type") or "").strip()
        if not raw_type:
            continue
        head, _, list_name = raw_type.partition(" ")
        name = str(row.get("name") or f"row_{number}")
        if head in ("begin", "end"):
            what = list_name.strip().replace("_", " ")
            if head == "begin" and what == "group":
                section = Section(id=safe_id(name, taken), title=str(row.get("label") or ""))
                section.visible_when = convert(row.get("relevant"), section.title or name)
                stack[-1].append(section)
                stack.append(section.items)
            elif head == "begin" and what == "repeat":
                rep = Field(
                    id=safe_id(name, taken), type="repeater", label=str(row.get("label") or "")
                )
                stack[-1].append(rep)
                repeat.append(rep)
                stack.append(rep.fields)  # type: ignore[arg-type]
            elif len(stack) > 1:
                stack.pop()
                if what == "repeat" and repeat:
                    repeat.pop()
            continue
        model_type = _TYPES.get(head)
        if model_type is None:
            report.append(
                f"Row {number}: the type {raw_type!r} has no field type in the model; kept as text."
            )
            model_type = "text"
        item = Field(id=safe_id(name, taken), type=model_type, label=str(row.get("label") or ""))
        if head == "text" and "multiline" in str(row.get("appearance") or ""):
            item.type = "textarea"
        if head == "select_one" and "minimal" in str(row.get("appearance") or ""):
            item.type = "select"
        item.help = str(row.get("hint") or "")
        item.required = str(row.get("required") or "").strip().lower() in (
            "yes",
            "true",
            "true()",
            "1",
        )
        if row.get("default") not in (None, ""):
            item.default = str(row["default"])
        item.visible_when = convert(row.get("relevant"), item.label or name)
        item.calculate = convert(row.get("calculation"), item.label or name)
        if row.get("constraint"):
            item.settings["xlsform_constraint"] = str(row["constraint"])
            report.append(
                f"{item.label or name}: the constraint is kept as written; "
                "the model has no constraints yet."
            )
        if list_name:
            for c in lists.get(list_name.strip(), []):
                value = str(c.get("name", ""))
                item.choices.append(Choice(value, str(c.get("label") or value)))
                for key, text in c.items():
                    m = _LANG.match(str(key))
                    if m and m.group(1) == "label" and text:
                        lang = _lang_code(m.group(2), m.group(3))
                        form.translations.setdefault(lang, {})[
                            f"field.{item.id}.choice.{value}"
                        ] = str(text)
        for key, text in row.items():
            m = _LANG.match(str(key))
            if m and text:
                lang = _lang_code(m.group(2), m.group(3))
                what = "label" if m.group(1) == "label" else "help"
                form.translations.setdefault(lang, {})[f"field.{item.id}.{what}"] = str(text)
        stack[-1].append(item)
    if settings.get("default_language"):
        form.language = _lang_code(str(settings["default_language"]), None)
    return ImportResult(form, report)


def import_xlsform(path: str | Path) -> ImportResult:
    try:
        import openpyxl  # noqa: PLC0415 - only when an XLSForm is opened
    except ImportError as exc:  # pragma: no cover - a declared dependency
        raise FormImportError("Reading XLSForm needs openpyxl, which is missing.") from exc
    try:
        book = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises many kinds
        raise FormImportError(f"This workbook could not be read: {exc}") from exc

    def rows(name: str) -> list[dict[str, Any]]:
        if name not in book.sheetnames:
            return []
        values = list(book[name].iter_rows(values_only=True))
        if not values:
            return []
        header = [str(h).strip() if h is not None else "" for h in values[0]]
        return [{h: v for h, v in zip(header, r, strict=False) if h} for r in values[1:]]

    if "survey" not in book.sheetnames:
        raise FormImportError("An XLSForm needs a sheet called survey.")
    settings = rows("settings")
    return import_rows(rows("survey"), rows("choices"), settings[0] if settings else None)


# -- export -------------------------------------------------------------------------


def xpath(node: E.Node) -> str:
    if isinstance(node, E.Ref):
        return "${" + node.field + "}"
    if isinstance(node, E.Str):
        return "'" + node.value + "'"
    if isinstance(node, E.Today):
        return "today()"
    if isinstance(node, E.Compare) and node.op in ("=", "!=", "<", "<=", ">", ">="):
        return f"{xpath(node.left)} {node.op} {xpath(node.right)}"
    if isinstance(node, E.Compare) and node.op in ("before", "after"):
        return f"{xpath(node.left)} {'<' if node.op == 'before' else '>'} {xpath(node.right)}"
    if isinstance(node, E.Compare) and node.op == "contains":
        return f"contains({xpath(node.left)}, {xpath(node.right)})"
    if isinstance(node, E.Empty):
        return f"{xpath(node.value)} {'!=' if node.negate else '='} ''"
    if isinstance(node, E.OneOf):
        text = " or ".join(f"selected({xpath(node.value)}, {xpath(o)})" for o in node.options)
        return f"not({text})" if node.negate else f"({text})"
    if isinstance(node, E.Logic):
        return f" {node.op} ".join(
            f"({xpath(i)})" if isinstance(i, E.Logic) else xpath(i) for i in node.items
        )
    if isinstance(node, E.Not):
        return f"not({xpath(node.operand)})"
    if isinstance(node, E.Arith):
        op = {"/": "div", "%": "mod"}.get(node.op, node.op)
        return f"({xpath(node.left)} {op} {xpath(node.right)})"
    return E.to_text(node)


def export_rows(form: Form) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """(survey rows, choices rows, settings row) for an XLSForm."""
    survey: list[dict[str, Any]] = []
    choices: list[dict[str, Any]] = []

    def walk(items: list[Item]) -> None:
        for item in items:
            if isinstance(item, Columns):
                for column in item.columns:
                    walk(column)
            elif isinstance(item, Section):
                row = {"type": "begin group", "name": item.id, "label": item.title}
                if item.visible_when:
                    row["relevant"] = xpath(E.parse(item.visible_when))
                survey.append(row)
                walk(item.items)
                survey.append({"type": "end group", "name": item.id})
            elif isinstance(item, Field):
                field_row(item)
            elif isinstance(item, Island):
                continue

    def field_row(item: Field) -> None:
        if item.type == "repeater":
            survey.append({"type": "begin repeat", "name": item.id, "label": item.label})
            walk(list(item.fields))
            survey.append({"type": "end repeat", "name": item.id})
            return
        kind = _BACK.get(item.type, "text")
        if item.choices:
            kind += f" {item.id}"
            choices.extend(
                {"list_name": item.id, "name": c.value, "label": c.label} for c in item.choices
            )
        row: dict[str, Any] = {"type": kind, "name": item.id, "label": item.label}
        if item.type == "textarea":
            row["appearance"] = "multiline"
        if item.type == "select":
            row["appearance"] = "minimal"
        if item.help:
            row["hint"] = item.help
        if item.required:
            row["required"] = "yes"
        if item.default is not None:
            row["default"] = item.default
        if item.visible_when:
            row["relevant"] = xpath(E.parse(item.visible_when))
        if item.calculate:
            row["calculation"] = xpath(E.parse(item.calculate))
        if "xlsform_constraint" in item.settings:
            row["constraint"] = item.settings["xlsform_constraint"]
        survey.append(row)

    for page in form.pages:
        walk(page.items)
    settings = {
        "form_title": form.title,
        "form_id": form.id or safe_id(form.title.lower(), set()),
        "default_language": form.language,
    }
    return survey, choices, settings


def export_xlsform(form: Form, path: str | Path) -> None:
    import openpyxl  # noqa: PLC0415

    survey, choices, settings = export_rows(form)
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "survey"
    for name, rows in (("survey", survey), ("choices", choices), ("settings", [settings])):
        ws = sheet if name == "survey" else book.create_sheet(name)
        header: list[str] = []
        for r in rows:
            header.extend(k for k in r if k not in header)
        ws.append(header or ["type", "name", "label"])
        for r in rows:
            ws.append([r.get(h, "") for h in header])
    book.save(str(path))
