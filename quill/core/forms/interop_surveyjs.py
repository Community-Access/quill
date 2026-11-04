"""SurveyJS JSON in and out (https://surveyjs.io/form-library/documentation).

Questions become fields by type, panels sections, ``visibleIf`` and
``expression`` the model's expressions, and localised strings
(``{"default": "Name", "fr": "Nom"}``) translations. A property with no place
in the model is kept under ``extensions.surveyjs`` and named in the report.
"""

from __future__ import annotations

import json
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_common import ImportResult, clean, convert_expression, safe_id

_TYPES = {
    "text": "text", "comment": "textarea", "dropdown": "select", "tagbox": "multiselect",
    "radiogroup": "radio", "checkbox": "checkbox", "boolean": "toggle", "rating": "rating",
    "ranking": "ranking", "matrix": "matrix", "file": "fileupload", "signaturepad": "signature",
    "imagepicker": "image_choice", "html": "html", "expression": "calculation",
    "paneldynamic": "repeater",
}  # fmt: skip
_INPUT = {
    "email": "email", "number": "number", "date": "date", "time": "time", "tel": "phone",
    "url": "website", "color": "color", "range": "range", "password": "password",
    "datetime-local": "datetime",
}  # fmt: skip
_BACK = {v: k for k, v in _TYPES.items()}
_KNOWN = {
    "type", "name", "title", "description", "isRequired", "placeholder", "defaultValue",
    "choices", "visibleIf", "inputType", "expression", "elements", "templateElements", "html",
    "min", "max", "maxLength", "autocomplete",
}  # fmt: skip
_REWRITES = [
    (r"\{([A-Za-z0-9_]+)\}", r"#\1"),
    (r"\bnotempty\b", " is filled"),
    (r"(?<![A-Za-z_])empty\b", " is empty"),
    (r"\bnotcontains\b", "does not contain"),
    (r"\banyof\b", "is one of"),
    (r"\biif\(", "if("),
]


def _text(value: Any, put: Any) -> str:
    """A SurveyJS string, which may be localised: keep the default, file the rest."""
    if isinstance(value, dict):
        for lang, text in value.items():
            if lang != "default":
                put(lang, str(text))
        return str(value.get("default", next(iter(value.values()), "")))
    return "" if value is None else str(value)


class _Importer:
    def __init__(self) -> None:
        self.report: list[str] = []
        self.taken: set[str] = set()
        self.translations: dict[str, dict[str, Any]] = {}

    def tr(self, part: str, ident: str, key: str) -> Any:
        def put(lang: str, text: str) -> None:
            t = self.translations.setdefault(lang, {})
            if not part:
                t[key] = text
            elif key.startswith("choices/"):
                t.setdefault(part, {}).setdefault(ident, {}).setdefault("choices", {})[key[8:]] = (
                    text
                )
            else:
                t.setdefault(part, {}).setdefault(ident, {})[key] = text

        return put

    def expression(self, raw: str, where: str) -> str | None:
        converted = convert_expression(raw, _REWRITES)
        if converted is None:
            self.report.append(
                f"The rule on {where} could not be converted and was left out: {raw}"
            )
        return converted

    def question(self, q: dict[str, Any]) -> M.Item:
        kind = str(q.get("type", "text"))
        if kind == "panel":
            ident = safe_id(q.get("name", "panel"), self.taken)
            section: dict[str, Any] = {"id": ident, "type": "section"}
            section["label"] = _text(q.get("title", ""), self.tr("fields", ident, "label"))
            section["help"] = _text(q.get("description", ""), self.tr("fields", ident, "help"))
            if q.get("visibleIf"):
                section["when"] = self.expression(str(q["visibleIf"]), section["label"] or ident)
            section["items"] = [self.question(e) for e in q.get("elements", [])]
            return clean(section)
        mapped = (
            _INPUT.get(str(q.get("inputType", "")), "text") if kind == "text" else _TYPES.get(kind)
        )
        if mapped is None:
            self.report.append(
                f"The {kind} question {q.get('name')!r} has no field type in the model; it is kept as text."  # noqa: E501
            )
            mapped = "text"
        ident = safe_id(q.get("name", "question"), self.taken)
        item: dict[str, Any] = {"id": ident, "type": mapped}
        item["label"] = _text(q.get("title", q.get("name", "")), self.tr("fields", ident, "label"))
        item["help"] = _text(q.get("description", ""), self.tr("fields", ident, "help"))
        item["placeholder"] = _text(
            q.get("placeholder", ""), self.tr("fields", ident, "placeholder")
        )
        if q.get("isRequired"):
            item["required"] = True
        if "defaultValue" in q:
            item["default"] = q["defaultValue"]
        choices = []
        for raw in q.get("choices", []):
            if isinstance(raw, dict):
                value = str(raw.get("value", ""))
                label = _text(raw.get("text", value), self.tr("fields", ident, "choices/" + value))
            else:
                value = label = str(raw)
            choices.append({"value": value, "label": label})
        if choices:
            item["choices"] = choices
        if q.get("visibleIf"):
            item["when"] = self.expression(str(q["visibleIf"]), item["label"] or ident)
        if kind == "expression" and q.get("expression"):
            item["calculation"] = self.expression(str(q["expression"]), item["label"] or ident)
        validation: dict[str, Any] = {k: q[k] for k in ("min", "max") if k in q}
        if "maxLength" in q:
            validation["max_length"] = int(q["maxLength"])
        if validation:
            item["validation"] = validation
        props: dict[str, Any] = {}
        if "autocomplete" in q:
            props["autocomplete"] = q["autocomplete"]
        if kind == "html":
            props["html"] = str(q.get("html", ""))
        if props:
            item["props"] = props
        if kind == "paneldynamic":
            item["items"] = [self.question(e) for e in q.get("templateElements", [])]
        extra = {k: v for k, v in q.items() if k not in _KNOWN}
        if extra:
            item["__surveyjs"] = extra
            self.report.append(
                f"{item['label'] or ident}: kept SurveyJS settings the model has no place for: {', '.join(sorted(extra))}."  # noqa: E501
            )
        out = clean(item)
        if "__surveyjs" in item:
            out["__surveyjs"] = item["__surveyjs"]
        return out


def _lift_extras(entries: list[M.Item], store: dict[str, Any]) -> None:
    for item in entries:
        extra = item.pop("__surveyjs", None)
        if extra:
            store[item["id"]] = extra
        _lift_extras(item.get("items") or [], store)


def import_surveyjs(data: dict[str, Any] | str) -> ImportResult:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as exc:
            raise FormImportError(f"This is not SurveyJS JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FormImportError("SurveyJS JSON must be an object with pages or elements.")
    imp = _Importer()
    model: M.Model = {"version": M.MODEL_VERSION}
    model["title"] = _text(data.get("title", ""), imp.tr("", "", "title"))
    description = _text(data.get("description", ""), imp.tr("", "", "description"))
    if description:
        model["description"] = description
    if data.get("locale"):
        model["language"] = str(data["locale"])
    if data.get("completeText"):
        model["settings"] = {"submit_label": _text(data["completeText"], lambda *_: None)}
    pages = []
    raw_pages = data.get("pages") or [{"name": "page1", "elements": data.get("elements", [])}]
    for n, raw in enumerate(raw_pages, 1):
        page: dict[str, Any] = {"id": safe_id(raw.get("name") or f"page_{n}", imp.taken)}
        title = _text(raw.get("title", ""), imp.tr("pages", page["id"], "title"))
        if title:
            page["title"] = title
        if raw.get("visibleIf"):
            when = imp.expression(str(raw["visibleIf"]), title or page["id"])
            if when:
                page["when"] = when
        page["items"] = [imp.question(q) for q in raw.get("elements", [])]
        pages.append(page)
    model["pages"] = pages or [{"id": "page_1", "items": []}]
    if data.get("completedHtml"):
        model["confirmations"] = [
            {
                "id": "confirmation_1",
                "type": "message",
                "message": _text(data["completedHtml"], lambda *_: None),
            }
        ]
    if imp.translations:
        model["translations"] = imp.translations
    extras: dict[str, Any] = {}
    for page in model["pages"]:
        _lift_extras(page["items"], extras)
    leftover = sorted(
        set(data)
        - {"title", "description", "locale", "completeText", "completedHtml", "pages", "elements"}
    )
    if leftover:
        extras["__survey__"] = {k: data[k] for k in leftover}
        imp.report.append(
            f"Kept survey settings the model has no place for: {', '.join(leftover)}."
        )
    if extras:
        model["extensions"] = {"surveyjs": extras}
    return ImportResult(model, imp.report)


# -- export ------------------------------------------------------------------------------------

_OPS = {"is": "=", "is_not": "<>", "lt": "<", "le": "<=", "gt": ">", "ge": ">=", "contains": "contains",  # noqa: E501
        "not_contains": "notcontains", "before": "<", "after": ">", "add": "+", "sub": "-", "mul": "*",  # noqa: E501
        "div": "/", "mod": "%", "starts_with": "contains", "ends_with": "contains"}  # fmt: skip


def surveyjs_expression(node: E.Node) -> str:  # noqa: C901
    kind = node["type"]
    if kind == "ref":
        return "{" + str(node["field"]) + "}"
    if kind == "literal":
        v = node["value"]
        return "'" + v.replace("'", "\\'") + "'" if isinstance(v, str) else E.literal_text(v)
    if kind == "list":
        return "[" + ", ".join(surveyjs_expression(i) for i in node["items"]) + "]"
    if kind == "call":
        name = "iif" if node["name"] == "if" else node["name"]
        return name + "(" + ", ".join(surveyjs_expression(a) for a in node["args"]) + ")"
    if kind == "var":
        return "{score}"
    a, name = node["args"], node["op"]
    if name in ("and", "or"):
        return f" {name} ".join(
            f"({surveyjs_expression(x)})"
            if x.get("op") in ("and", "or")
            else surveyjs_expression(x)
            for x in a
        )
    if name == "not":
        return "!(" + surveyjs_expression(a[0]) + ")"
    if name == "neg":
        return "-" + surveyjs_expression(a[0])
    if name in ("empty", "not_empty"):
        return surveyjs_expression(a[0]) + (" empty" if name == "empty" else " notempty")
    if name in ("one_of", "not_one_of"):
        text = surveyjs_expression(a[0]) + " anyof " + surveyjs_expression(a[1])
        return text if name == "one_of" else "!(" + text + ")"
    if name == "within":
        base = surveyjs_expression(a[2]) if len(a) > 2 else "today()"
        return f"abs(diffDays({surveyjs_expression(a[0])}, {base})) <= {surveyjs_expression(a[1])}"
    text = f"{surveyjs_expression(a[0])} {_OPS[name]} {surveyjs_expression(a[1])}"
    return f"({text})" if name in ("add", "sub") else text


def _localised(text: str, model: M.Model, part: str, ident: str, key: str) -> Any:
    from quill.core.forms.translate import lookup

    others = {}
    for lang in model.get("translations") or {}:
        found = lookup(model, lang, (part, ident, key))
        if found is not None:
            others[lang] = found
    return {"default": text, **others} if others else text


def _question(item: M.Item, model: M.Model, extras: dict[str, Any]) -> list[dict[str, Any]]:
    kind = item["type"]
    if kind == "columns":
        return [
            q
            for col in item.get("columns") or []
            for i in col.get("items") or []
            for q in _question(i, model, extras)
        ]
    out: dict[str, Any] = {
        "type": "panel" if kind == "section" else _BACK.get(kind, "text"),
        "name": item["id"],
    }
    inverse = {v: k for k, v in _INPUT.items()}
    if kind in inverse:
        out["type"], out["inputType"] = "text", inverse[kind]
    if "label" in item:
        out["title"] = _localised(item["label"], model, "fields", item["id"], "label")
    if "help" in item:
        out["description"] = _localised(item["help"], model, "fields", item["id"], "help")
    if "placeholder" in item:
        out["placeholder"] = _localised(
            item["placeholder"], model, "fields", item["id"], "placeholder"
        )
    if item.get("required"):
        out["isRequired"] = True
    if "default" in item:
        out["defaultValue"] = item["default"]
    if "choices" in item:
        out["choices"] = [
            {
                "value": c["value"],
                "text": _localised(
                    c["label"], model, "fields", item["id"], "choices/" + c["value"]
                ),
            }
            for c in item["choices"]
        ]
    if "when" in item:
        out["visibleIf"] = surveyjs_expression(E.parse(item["when"]))
    if "calculation" in item:
        out["type"], out["expression"] = (
            "expression",
            surveyjs_expression(E.parse(item["calculation"])),
        )
    validation = item.get("validation") or {}
    for k in ("min", "max"):
        if k in validation:
            out[k] = validation[k]
    if "max_length" in validation:
        out["maxLength"] = validation["max_length"]
    props = item.get("props") or {}
    if "autocomplete" in props:
        out["autocomplete"] = props["autocomplete"]
    if kind == "html":
        out["html"] = props.get("html", "")
    if kind == "section":
        out["elements"] = [q for i in item.get("items") or [] for q in _question(i, model, extras)]
    elif kind == "repeater":
        out["templateElements"] = [
            q for i in item.get("items") or [] for q in _question(i, model, extras)
        ]
    out.update(extras.get(item["id"], {}))
    return [out]


def export_surveyjs(model: M.Model) -> dict[str, Any]:
    extras = dict((model.get("extensions") or {}).get("surveyjs") or {})
    out: dict[str, Any] = {}
    if model.get("title"):
        out["title"] = _localised(model["title"], model, "", "", "title")
    if model.get("description"):
        out["description"] = _localised(model["description"], model, "", "", "description")
    if "language" in model:
        out["locale"] = model["language"]
    submit = (model.get("settings") or {}).get("submit_label")
    if submit:
        out["completeText"] = submit
    message = next(
        (c.get("message") for c in model.get("confirmations") or [] if c.get("type") == "message"),
        None,
    )
    if message:
        out["completedHtml"] = message
    pages = []
    for page in model["pages"]:
        p: dict[str, Any] = {"name": page["id"]}
        if "title" in page:
            p["title"] = _localised(page["title"], model, "pages", page["id"], "title")
        if "when" in page:
            p["visibleIf"] = surveyjs_expression(E.parse(page["when"]))
        p["elements"] = [q for i in page.get("items") or [] for q in _question(i, model, extras)]
        pages.append(p)
    out["pages"] = pages
    out.update(extras.get("__survey__", {}))
    return out
