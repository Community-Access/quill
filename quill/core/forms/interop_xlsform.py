"""XLSForm in and out (https://xlsform.org): the spreadsheet form standard.

The ``survey`` sheet's rows become fields (``begin group``/``end group`` a
section, ``begin repeat`` a repeater), the ``choices`` sheet their choices and
``settings`` the title and language. ``relevant`` becomes ``when`` and
``calculation`` stays a calculation, converted from XLSForm's XPath style
(``${age} > 17``, ``selected(${q}, 'a')``). ``label::French (fr)`` columns
become translations. A constraint is kept under ``extensions.xlsform``.

Workbooks are read and written with ``openpyxl``, which QUILL already depends
on, imported only when an XLSForm is used. Rows can also be passed as lists of
dicts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_common import ImportResult, clean, convert_expression, safe_id

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
    (r"selected\(\s*\$\{([A-Za-z0-9_]+)\}\s*,\s*('[^']*'|\"[^\"]*\")\s*\)", r"#\1 contains \2"),
    (r"\$\{([A-Za-z0-9_]+)\}", r"#\1"),
    (r"\bdiv\b", "/"),
    (r"\bmod\b", "%"),
    (r"\bnot\(", "not ("),
]
_LANG = re.compile(r"^(label|hint)::(.+?)(?:\s*\(([A-Za-z-]+)\))?$")


_LANGUAGE_NAMES = {
    "english": "en", "french": "fr", "spanish": "es", "portuguese": "pt", "german": "de",
    "italian": "it", "arabic": "ar", "swahili": "sw", "hindi": "hi", "chinese": "zh",
}  # fmt: skip


def _lang(name: str, code: str | None) -> str:
    """A BCP 47 tag from XLSForm's ``French (fr)``, or from a common language name."""
    if code:
        return code.strip()
    word = name.strip().lower()
    return _LANGUAGE_NAMES.get(word, word if re.fullmatch(r"[a-z]{2,3}", word) else "und")


def import_rows(  # noqa: C901
    survey: list[dict[str, Any]],
    choices: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> ImportResult:
    report: list[str] = []
    settings = settings or {}
    model: M.Model = {"version": M.MODEL_VERSION, "title": str(settings.get("form_title") or "")}
    if settings.get("form_id"):
        model["id"] = safe_id(settings["form_id"], set())
    if settings.get("default_language"):
        m = _LANG.match("label::" + str(settings["default_language"]))
        language = _lang(m.group(2), m.group(3)) if m else "und"
        if language == "und":
            report.append(
                f"The default language {settings['default_language']!r} has no language code; it was left out."  # noqa: E501
            )
        else:
            model["language"] = language
    lists: dict[str, list[dict[str, Any]]] = {}
    for row in choices:
        if row.get("list_name"):
            lists.setdefault(str(row["list_name"]).strip(), []).append(row)
    taken: set[str] = set()
    top: list[M.Item] = []
    stack: list[list[M.Item]] = [top]
    translations: dict[str, dict[str, Any]] = {}
    constraints: dict[str, str] = {}

    def tr(lang: str, ident: str, key: str, text: str) -> None:
        entry = translations.setdefault(lang, {}).setdefault("fields", {}).setdefault(ident, {})
        if key.startswith("choices/"):
            entry.setdefault("choices", {})[key[8:]] = text
        else:
            entry[key] = text

    def convert(raw: Any, where: str) -> str | None:
        if raw in (None, ""):
            return None
        out = convert_expression(str(raw), _REWRITES)
        if out is None:
            report.append(f"The rule on {where} could not be converted and was left out: {raw}")
        return out

    for number, row in enumerate(survey, 2):
        raw_type = str(row.get("type") or "").strip()
        if not raw_type:
            continue
        head, _, list_name = raw_type.partition(" ")
        name = str(row.get("name") or f"row_{number}")
        if head in ("begin", "end"):
            what = list_name.strip().replace("_", " ")
            if head == "begin" and what in ("group", "repeat"):
                kind = "section" if what == "group" else "repeater"
                item: dict[str, Any] = {
                    "id": safe_id(name, taken),
                    "type": kind,
                    "label": str(row.get("label") or ""),
                }
                item["when"] = convert(row.get("relevant"), item["label"] or name)
                item["items"] = []
                stack[-1].append(clean(item) | {"items": item["items"]})
                stack.append(item["items"])
            elif len(stack) > 1:
                stack.pop()
            continue
        mapped = _TYPES.get(head)
        if mapped is None:
            report.append(
                f"Row {number}: the type {raw_type!r} has no field type in the model; kept as text."
            )
            mapped = "text"
        appearance = str(row.get("appearance") or "")
        if head == "text" and "multiline" in appearance:
            mapped = "textarea"
        if head == "select_one" and "minimal" in appearance:
            mapped = "select"
        ident = safe_id(name, taken)
        item = {
            "id": ident,
            "type": mapped,
            "label": str(row.get("label") or ""),
            "help": str(row.get("hint") or ""),
        }
        if str(row.get("required") or "").strip().lower() in ("yes", "true", "true()", "1"):
            item["required"] = True
        if row.get("default") not in (None, ""):
            item["default"] = str(row["default"])
        item["when"] = convert(row.get("relevant"), item["label"] or name)
        item["calculation"] = convert(row.get("calculation"), item["label"] or name)
        if mapped == "calculation" and not item["calculation"]:
            item["calculation"] = "0"
        if row.get("constraint"):
            constraints[ident] = str(row["constraint"])
            report.append(
                f"{item['label'] or name}: the constraint is kept as written; the model has no constraints yet."  # noqa: E501
            )
        if list_name:
            item["choices"] = []
            for c in lists.get(list_name.strip(), []):
                value = str(c.get("name", ""))
                item["choices"].append({"value": value, "label": str(c.get("label") or value)})
                for key, text in c.items():
                    m = _LANG.match(str(key))
                    if m and m.group(1) == "label" and text:
                        tr(_lang(m.group(2), m.group(3)), ident, "choices/" + value, str(text))
        for key, text in row.items():
            m = _LANG.match(str(key))
            if m and text:
                tr(
                    _lang(m.group(2), m.group(3)),
                    ident,
                    "label" if m.group(1) == "label" else "help",
                    str(text),
                )
        stack[-1].append(clean(item))
    model["pages"] = [{"id": "page_1", "items": top}]
    if translations:
        model["translations"] = translations
    if constraints:
        model["extensions"] = {"xlsform": {"constraints": constraints}}
    return ImportResult(model, report)


def import_xlsform(path: str | Path) -> ImportResult:
    try:
        import openpyxl  # noqa: PLC0415 - only when an XLSForm is opened
    except ImportError as exc:  # pragma: no cover - a declared dependency
        raise FormImportError("Reading XLSForm needs openpyxl, which is missing.") from exc
    try:
        book = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises many kinds  # noqa: BLE001
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


# -- export -------------------------------------------------------------------------------

_XOPS = {"is": "=", "is_not": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">=", "before": "<", "after": ">",  # noqa: E501
         "add": "+", "sub": "-", "mul": "*", "div": "div", "mod": "mod"}  # fmt: skip


def xpath(node: E.Node) -> str:  # noqa: C901
    kind = node["type"]
    if kind == "ref":
        return "${" + str(node["field"]) + "}"
    if kind == "literal":
        v = node["value"]
        return "'" + v + "'" if isinstance(v, str) else E.literal_text(v)
    if kind == "call":
        return str(node["name"]) + "(" + ", ".join(xpath(a) for a in node["args"]) + ")"
    if kind == "list":
        return " ".join(xpath(i) for i in node["items"])
    if kind == "var":
        return "${score}"
    a, name = node["args"], node["op"]
    if name in ("and", "or"):
        return f" {name} ".join(
            f"({xpath(x)})" if x.get("op") in ("and", "or") else xpath(x) for x in a
        )
    if name == "not":
        return f"not({xpath(a[0])})"
    if name == "neg":
        return "-" + xpath(a[0])
    if name in ("empty", "not_empty"):
        return f"{xpath(a[0])} {'=' if name == 'empty' else '!='} ''"
    if name in ("one_of", "not_one_of"):
        options = a[1]["items"] if a[1]["type"] == "list" else [a[1]]
        text = " or ".join(f"selected({xpath(a[0])}, {xpath(o)})" for o in options)
        return f"not({text})" if name == "not_one_of" else f"({text})"
    if name in ("contains", "not_contains"):
        text = f"selected({xpath(a[0])}, {xpath(a[1])})"
        return text if name == "contains" else f"not({text})"
    if name in ("starts_with", "ends_with"):
        return f"{name.replace('_with', '-with')}({xpath(a[0])}, {xpath(a[1])})"
    if name == "within":
        base = xpath(a[2]) if len(a) > 2 else "today()"
        return f"abs(decimal-date-time({xpath(a[0])}) - decimal-date-time({base})) <= {xpath(a[1])}"
    text = f"{xpath(a[0])} {_XOPS[name]} {xpath(a[1])}"
    return f"({text})" if name in ("add", "sub") else text


def export_rows(
    model: M.Model,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """(survey rows, choices rows, settings row) for an XLSForm."""
    survey: list[dict[str, Any]] = []
    choice_rows: list[dict[str, Any]] = []
    constraints = ((model.get("extensions") or {}).get("xlsform") or {}).get("constraints") or {}

    def walk(entries: list[M.Item]) -> None:
        for item in entries:
            kind = item["type"]
            if kind == "columns":
                for col in item.get("columns") or []:
                    walk(col.get("items") or [])
                continue
            if kind in ("section", "repeater"):
                word = "group" if kind == "section" else "repeat"
                row = {"type": f"begin {word}", "name": item["id"], "label": item.get("label", "")}
                if "when" in item:
                    row["relevant"] = xpath(E.parse(item["when"]))
                survey.append(row)
                walk(item.get("items") or [])
                survey.append({"type": f"end {word}", "name": item["id"]})
                continue
            row = {
                "type": _BACK.get(kind, "text"),
                "name": item["id"],
                "label": item.get("label", ""),
            }
            if item.get("choices"):
                row["type"] += " " + item["id"]
                choice_rows.extend(
                    {"list_name": item["id"], "name": c["value"], "label": c["label"]}
                    for c in item["choices"]
                )
            if kind == "textarea":
                row["appearance"] = "multiline"
            if kind == "select":
                row["appearance"] = "minimal"
            if item.get("help"):
                row["hint"] = item["help"]
            if item.get("required"):
                row["required"] = "yes"
            if "default" in item:
                row["default"] = item["default"]
            if "when" in item:
                row["relevant"] = xpath(E.parse(item["when"]))
            if "calculation" in item:
                row["calculation"] = xpath(E.parse(item["calculation"]))
            if item["id"] in constraints:
                row["constraint"] = constraints[item["id"]]
            survey.append(row)

    for page in model["pages"]:
        walk(page.get("items") or [])
    settings = {
        "form_title": model.get("title", ""),
        "form_id": model.get("id") or safe_id(model.get("title", "form").lower(), set()),
    }
    if "language" in model:
        settings["default_language"] = model["language"]
    return survey, choice_rows, settings


def export_xlsform(model: M.Model, path: str | Path) -> None:
    import openpyxl  # noqa: PLC0415

    survey, choice_rows, settings = export_rows(model)
    book = openpyxl.Workbook()
    first = book.active
    for name, rows in (("survey", survey), ("choices", choice_rows), ("settings", [settings])):
        ws = first if name == "survey" else book.create_sheet(name)
        ws.title = name
        header: list[str] = []
        for r in rows:
            header.extend(k for k in r if k not in header)
        ws.append(header or ["type", "name", "label"])
        for r in rows:
            ws.append([r.get(h, "") for h in header])
    book.save(str(path))
