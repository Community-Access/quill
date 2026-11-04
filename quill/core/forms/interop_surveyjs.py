"""SurveyJS JSON in and out (https://surveyjs.io/form-library/documentation).

Questions map to fields by type, panels to sections, ``visibleIf`` and
``expression`` to the expression language, and localised strings
(``{"default": "Name", "fr": "Nom"}``) to translations. A property with no
place in the model is kept in ``settings["surveyjs"]`` and named in the
import report.
"""

from __future__ import annotations

import json
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.errors import FormImportError
from quill.core.forms.interop_common import ImportResult, convert_expression, safe_id
from quill.core.forms.model import Choice, Columns, Field, Form, Island, Item, Page, Section

_TYPES = {
    "text": "text", "comment": "textarea", "dropdown": "select", "tagbox": "multiselect",
    "radiogroup": "radio", "checkbox": "checkbox", "boolean": "toggle", "rating": "rating",
    "ranking": "ranking", "matrix": "matrix", "file": "fileupload", "signaturepad": "signature",
    "imagepicker": "image_choice", "html": "html", "expression": "calculation",
    "paneldynamic": "repeater",
}  # fmt: skip
_INPUT_TYPES = {
    "email": "email", "number": "number", "date": "date", "time": "time", "tel": "phone",
    "url": "website", "color": "color", "range": "range", "password": "password",
    "datetime-local": "datetime",
}  # fmt: skip
_BACK = {v: k for k, v in _TYPES.items()} | {"multiselect": "tagbox", "textarea": "comment"}
_KNOWN = {"type", "name", "title", "description", "isRequired", "placeholder", "defaultValue",
          "choices", "visibleIf", "inputType", "expression", "elements", "templateElements",
          "html", "min", "max", "step", "maxLength", "autocomplete"}  # fmt: skip
_REWRITES = [
    (r"\{([A-Za-z0-9_]+)\}", r"#\1"),
    (r"\bnotempty\b", " is filled"),
    (r"\bempty\b", " is empty"),
    (r"<>", "!="),
    (r"\bnotcontains\b", "does not contain"),
    (r"\banyof\s*\[([^\]]*)\]", r"is one of (\1)"),
    (r"\btoday\(\)", "today"),
    (r"\biif\(", "if("),
]


def _text(value: Any, key: str, base: str, translations: dict[str, dict[str, str]]) -> str:
    """A SurveyJS string, which may be localised: keep the default, file the rest."""
    if isinstance(value, dict):
        for lang, text in value.items():
            if lang != "default":
                translations.setdefault(lang, {})[f"{base}{key}"] = str(text)
        return str(value.get("default", next(iter(value.values()), "")))
    return "" if value is None else str(value)


class _Importer:
    def __init__(self) -> None:
        self.report: list[str] = []
        self.taken: set[str] = set()
        self.form = Form()

    def expression(self, raw: str, where: str) -> str | None:
        converted = convert_expression(raw, _REWRITES)
        if converted is None:
            self.report.append(
                f"The rule on {where} could not be converted and is kept as written: {raw}"
            )
        return converted

    def question(self, q: dict[str, Any]) -> Item:
        kind = str(q.get("type", "text"))
        if kind == "panel":
            section = Section(id=safe_id(str(q.get("name", "panel")), self.taken))
            section.title = _text(
                q.get("title", ""), "title", f"section.{section.id}.", self.form.translations
            )
            section.description = _text(
                q.get("description", ""),
                "description",
                f"section.{section.id}.",
                self.form.translations,
            )
            if q.get("visibleIf"):
                section.visible_when = self.expression(
                    str(q["visibleIf"]), section.title or section.id
                )
            section.items = [self.question(e) for e in q.get("elements", [])]
            return section
        model_type = (
            _INPUT_TYPES.get(str(q.get("inputType", "")), _TYPES.get(kind))
            if kind == "text"
            else _TYPES.get(kind)
        )
        if model_type is None:
            self.report.append(
                f"The {kind} question {q.get('name')!r} has no field type in the model; "
                "it is kept as text."
            )
            model_type = "text"
        item = Field(id=safe_id(str(q.get("name", "question")), self.taken), type=model_type)
        base = f"field.{item.id}."
        tr = self.form.translations
        item.label = _text(q.get("title", q.get("name", "")), "label", base, tr)
        item.help = _text(q.get("description", ""), "help", base, tr)
        item.placeholder = _text(q.get("placeholder", ""), "placeholder", base, tr)
        item.required = bool(q.get("isRequired", False))
        if "defaultValue" in q:
            item.default = str(q["defaultValue"])
        for raw in q.get("choices", []):
            if isinstance(raw, dict):
                value = str(raw.get("value", ""))
                item.choices.append(
                    Choice(value, _text(raw.get("text", value), f"choice.{value}", base, tr))
                )
            else:
                item.choices.append(Choice(str(raw), str(raw)))
        if q.get("visibleIf"):
            item.visible_when = self.expression(str(q["visibleIf"]), item.label or item.id)
        if kind == "expression" and q.get("expression"):
            item.calculate = self.expression(str(q["expression"]), item.label or item.id)
        if kind == "html":
            item.settings["html"] = str(q.get("html", ""))
        for key, setting in (
            ("min", "min"),
            ("max", "max"),
            ("step", "step"),
            ("maxLength", "max_length"),
            ("autocomplete", "autocomplete"),
        ):
            if key in q:
                item.settings[setting] = str(q[key])
        if kind == "paneldynamic":
            item.fields = [
                f
                for f in (self.question(e) for e in q.get("templateElements", []))
                if isinstance(f, Field)
            ]
        extra = {k: v for k, v in q.items() if k not in _KNOWN}
        if extra:
            item.settings["surveyjs"] = extra
            self.report.append(
                f"{item.label or item.id}: kept SurveyJS settings the model has no place "
                f"for: {', '.join(sorted(extra))}."
            )
        return item


def import_surveyjs(data: dict[str, Any] | str) -> ImportResult:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as exc:
            raise FormImportError(f"This is not SurveyJS JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FormImportError("SurveyJS JSON must be an object with pages or elements.")
    imp = _Importer()
    form = imp.form
    form.title = _text(data.get("title", ""), "title", "", form.translations)
    form.description = _text(data.get("description", ""), "description", "", form.translations)
    form.language = str(data.get("locale") or "en")
    form.settings.submit_label = _text(
        data.get("completeText", ""), "submit_label", "settings.", form.translations
    )
    form.settings.success_message = _text(
        data.get("completedHtml", ""), "success_message", "settings.", form.translations
    )
    raw_pages = data.get("pages") or [{"name": "page1", "elements": data.get("elements", [])}]
    form.pages = []
    for n, raw in enumerate(raw_pages, 1):
        page = Page(id=f"page_{n}")
        page.title = _text(raw.get("title", ""), "title", f"page.{page.id}.", form.translations)
        page.description = _text(
            raw.get("description", ""), "description", f"page.{page.id}.", form.translations
        )
        if raw.get("visibleIf"):
            page.visible_when = imp.expression(str(raw["visibleIf"]), page.title or page.id)
        page.items = [imp.question(q) for q in raw.get("elements", [])]
        form.pages.append(page)
    form.pages = form.pages or [Page(id="page_1")]
    leftover = sorted(
        set(data)
        - {"title", "description", "locale", "completeText", "completedHtml", "pages", "elements"}
    )
    if leftover:
        form.settings.extra["surveyjs"] = {k: data[k] for k in leftover}
        imp.report.append(
            f"Kept survey settings the model has no place for: {', '.join(leftover)}."
        )
    return ImportResult(form, imp.report)


# -- export ------------------------------------------------------------------------


def surveyjs_expression(node: E.Node) -> str:  # noqa: C901
    if isinstance(node, E.Ref):
        return "{" + node.field + "}"
    if isinstance(node, E.Str):
        return "'" + node.value.replace("'", "\\'") + "'"
    if isinstance(node, E.Today):
        return "today()"
    if isinstance(node, E.Compare):
        op = {"=": "=", "!=": "<>", "contains": "contains", "not_contains": "notcontains"}.get(
            node.op, node.op
        )
        if node.op in ("before", "after"):
            op = "<" if node.op == "before" else ">"
        if node.op in ("starts", "ends"):
            op = "contains"
        return f"{surveyjs_expression(node.left)} {op} {surveyjs_expression(node.right)}"
    if isinstance(node, E.Empty):
        return f"{surveyjs_expression(node.value)} {'notempty' if node.negate else 'empty'}"
    if isinstance(node, E.OneOf):
        inner = ", ".join(surveyjs_expression(o) for o in node.options)
        text = f"{surveyjs_expression(node.value)} anyof [{inner}]"
        return f"!({text})" if node.negate else text
    if isinstance(node, E.Logic):
        return f" {node.op} ".join(
            f"({surveyjs_expression(i)})" if isinstance(i, E.Logic) else surveyjs_expression(i)
            for i in node.items
        )
    if isinstance(node, E.Not):
        return f"!({surveyjs_expression(node.operand)})"
    if isinstance(node, E.Arith):
        return f"({surveyjs_expression(node.left)} {node.op} {surveyjs_expression(node.right)})"
    if isinstance(node, E.Call):
        name = "iif" if node.name == "if" else node.name
        return f"{name}(" + ", ".join(surveyjs_expression(a) for a in node.args) + ")"
    if isinstance(node, E.Neg):
        return "-" + surveyjs_expression(node.operand)
    return E.to_text(node)


def _localised(text: str, key: str, form: Form) -> Any:
    others = {lang: t[key] for lang, t in form.translations.items() if key in t}
    return {"default": text, **others} if others else text


def _flat(items: list[Item]) -> list[Item]:
    """Columns laid out one after another; islands left out (SurveyJS has no place for BFL text)."""
    out: list[Item] = []
    for item in items:
        if isinstance(item, Columns):
            for column in item.columns:
                out.extend(_flat(column))
        elif not isinstance(item, Island):
            out.append(item)
    return out


def _question(item: Item, form: Form) -> dict[str, Any]:
    if isinstance(item, Section):
        out: dict[str, Any] = {
            "type": "panel",
            "name": item.id,
            "title": _localised(item.title, f"section.{item.id}.title", form),
        }
        if item.visible_when:
            out["visibleIf"] = surveyjs_expression(E.parse(item.visible_when))
        out["elements"] = [_question(i, form) for i in _flat(item.items)]
        return out
    assert isinstance(item, Field)
    raw = item.settings.get("surveyjs")
    sjs: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    base = f"field.{item.id}."
    out = {"type": _BACK.get(item.type, "text"), "name": item.id}
    inv = {v: k for k, v in _INPUT_TYPES.items()}
    if item.type in inv:
        out["type"], out["inputType"] = "text", inv[item.type]
    if item.label:
        out["title"] = _localised(item.label, base + "label", form)
    if item.help:
        out["description"] = _localised(item.help, base + "help", form)
    if item.placeholder:
        out["placeholder"] = _localised(item.placeholder, base + "placeholder", form)
    if item.required:
        out["isRequired"] = True
    if item.default is not None:
        out["defaultValue"] = item.default
    if item.choices:
        out["choices"] = [
            {"value": c.value, "text": _localised(c.label, f"{base}choice.{c.value}", form)}
            for c in item.choices
        ]
    if item.visible_when:
        out["visibleIf"] = surveyjs_expression(E.parse(item.visible_when))
    if item.calculate:
        out["type"], out["expression"] = "expression", surveyjs_expression(E.parse(item.calculate))
    if item.fields:
        out["templateElements"] = [_question(f, form) for f in item.fields]
    for setting, key in (
        ("min", "min"),
        ("max", "max"),
        ("step", "step"),
        ("max_length", "maxLength"),
        ("autocomplete", "autocomplete"),
    ):
        if setting in item.settings:
            out[key] = item.settings[setting]
    if item.type == "html":
        out["html"] = item.settings.get("html", "")
    out.update(sjs)
    return out


def export_surveyjs(form: Form) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if form.title:
        out["title"] = _localised(form.title, "title", form)
    if form.description:
        out["description"] = _localised(form.description, "description", form)
    if form.language != "en":
        out["locale"] = form.language
    if form.settings.submit_label:
        out["completeText"] = _localised(form.settings.submit_label, "settings.submit_label", form)
    if form.settings.success_message:
        out["completedHtml"] = _localised(
            form.settings.success_message, "settings.success_message", form
        )
    pages = []
    for page in form.pages:
        p: dict[str, Any] = {"name": page.id}
        if page.title:
            p["title"] = _localised(page.title, f"page.{page.id}.title", form)
        if page.visible_when:
            p["visibleIf"] = surveyjs_expression(E.parse(page.visible_when))
        p["elements"] = [_question(i, form) for i in _flat(page.items)]
        pages.append(p)
    out["pages"] = pages
    extra = form.settings.extra.get("surveyjs")
    if isinstance(extra, dict):
        out.update(extra)
    return out
