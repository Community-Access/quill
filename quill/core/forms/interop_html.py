"""Plain HTML forms in and out, with nothing but the standard library.

Export writes the accessible patterns BAF's renderer uses: every control has a
``<label for>``; a choice group is a ``<fieldset>`` whose ``<legend>`` is the
question; help is tied to its control with ``aria-describedby``; required is
the ``required`` attribute and the word "(required)" in the label, never a
colour or an asterisk alone; autofill hints are ``autocomplete``. Conditions
are written as ``data-when`` for a script to use; with no script the whole
form shows, which is the safe failure.

Import reads ``<label>``, ``<input>``, ``<select>``, ``<textarea>`` and
``<fieldset>``/``<legend>`` from any page, and reports what it skipped.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from typing import Any

from quill.core.forms import model as M
from quill.core.forms.interop_common import ImportResult, safe_id

_INPUT = {
    "email": "email", "number": "number", "tel": "phone", "url": "website", "date": "date",
    "time": "time", "datetime-local": "datetime", "password": "password", "color": "color",
    "range": "range", "file": "fileupload", "hidden": "hidden", "text": "text", "search": "text",
}  # fmt: skip
_OUT = {v: k for k, v in _INPUT.items() if k != "search"}
_VALIDATION = {
    "min": "min",
    "max": "max",
    "minlength": "min_length",
    "maxlength": "max_length",
    "pattern": "pattern",
}
_PROPS = ("autocomplete", "inputmode", "step")


def _a(name: str, value: Any) -> str:
    return f' {name}="{escape(str(value), quote=True)}"'


def _control(item: M.Item) -> list[str]:  # noqa: C901
    ident = item["id"]
    kind = item["type"]
    label_text = escape(item.get("label", ""))
    validation = item.get("validation") or {}
    props = item.get("props") or {}
    help_id = f"{ident}-help"
    describe = _a("aria-describedby", help_id) if item.get("help") else ""
    required = " required" if item.get("required") else ""
    note = ' <span class="required">(required)</span>' if item.get("required") else ""
    extra = "".join(
        _a(attr, validation[key]) for attr, key in _VALIDATION.items() if key in validation
    )
    extra += "".join(_a(k, props[k]) for k in _PROPS if k in props and props[k] is not True)
    if "placeholder" in item:
        extra += _a("placeholder", item["placeholder"])
    if isinstance(item.get("default"), (str, int, float)) and not isinstance(
        item.get("default"), bool
    ):
        extra += _a("value", item["default"])
    help_html = (
        [f'<p id="{help_id}" class="help">{escape(item["help"])}</p>'] if item.get("help") else []
    )
    choices = item.get("choices") or []
    if kind in ("radio", "checkbox") and choices:
        lines = ["<fieldset>", f"<legend>{label_text}{note}</legend>", *help_html]
        for n, c in enumerate(choices, 1):
            cid = f"{ident}-{n}"
            lines.append(
                f'<div><input type="{kind}"{_a("id", cid)}{_a("name", ident)}{_a("value", c["value"])}'  # noqa: E501
                f"{required if kind == 'radio' else ''}{describe}> "
                f'<label for="{cid}">{escape(c["label"])}</label></div>'
            )
        return lines + ["</fieldset>"]
    label = f'<label for="{ident}">{label_text}{note}</label>'
    if kind in ("select", "multiselect"):
        multiple = " multiple" if kind == "multiselect" else ""
        options = [
            f"<option{_a('value', c['value'])}>{escape(c['label'])}</option>" for c in choices
        ]
        if "choice_library" in item:
            options = [f"<!-- choices from the {escape(item['choice_library'])} library -->"]
        return [
            label,
            *help_html,
            f"<select{_a('id', ident)}{_a('name', ident)}{multiple}{required}{describe}>",
            *options,
            "</select>",
        ]
    if kind == "textarea":
        return [
            label,
            *help_html,
            f"<textarea{_a('id', ident)}{_a('name', ident)}{required}{describe}{extra}></textarea>",
        ]
    if kind == "consent":
        box = f'<input type="checkbox"{_a("id", ident)}{_a("name", ident)} value="yes"{required}{describe}>'  # noqa: E501
        return [f"<div>{box} {label}</div>", *help_html]
    if kind == "html":
        return [str(props.get("html", "<hr>" if props.get("element") == "divider" else ""))]
    if kind == "submit":
        return [f'<button type="submit">{escape(item.get("label") or "Submit")}</button>']
    kind_out = _OUT.get(kind, "text")
    return [
        label,
        *help_html,
        f'<input type="{kind_out}"{_a("id", ident)}{_a("name", ident)}{required}{describe}{extra}>',
    ]


def _items(entries: list[M.Item], out: list[str]) -> None:
    for item in entries:
        wrap = f"<div{_a('data-when', item['when'])}>" if "when" in item else ""
        if wrap:
            out.append(wrap)
        kind = item["type"]
        if kind == "section":
            out.append(f"<section{_a('aria-labelledby', item['id'] + '-title')}>")
            out.append(f'<h3 id="{item["id"]}-title">{escape(item.get("label", ""))}</h3>')
            if item.get("help"):
                out.append(f"<p>{escape(item['help'])}</p>")
            _items(item.get("items") or [], out)
            out.append("</section>")
        elif kind == "columns":
            out.append('<div class="columns">')
            for col in item.get("columns") or []:
                out.append('<div class="column">')
                _items(col.get("items") or [], out)
                out.append("</div>")
            out.append("</div>")
        else:
            out.append('<div class="field">')
            out.extend(_control(item))
            out.append("</div>")
        if wrap:
            out.append("</div>")


def export_html(model: M.Model, *, action: str = "", standalone: bool = True) -> str:
    """The form as HTML. ``action`` is where it submits; empty submits nowhere."""
    lang = model.get("language", "en")
    out = [f'<form{_a("action", action) if action else ""} method="post"{_a("lang", lang)}>']
    if model.get("title"):
        out.append(f"<h1>{escape(model['title'])}</h1>")
    if model.get("description"):
        out.append(f"<p>{escape(model['description'])}</p>")
    pages = model.get("pages") or []
    for n, page in enumerate(pages, 1):
        out.append(f'<fieldset class="page"{_a("id", page["id"])}>')
        out.append(f"<legend>{escape(page.get('title') or f'Page {n} of {len(pages)}')}</legend>")
        _items(page.get("items") or [], out)
        out.append("</fieldset>")
    submit = (model.get("settings") or {}).get("submit_label") or "Submit"
    out.append(f'<button type="submit">{escape(str(submit))}</button>')
    out.append("</form>")
    body = "\n".join(out)
    if not standalone:
        return body + "\n"
    head = (
        f'<!doctype html>\n<html lang="{escape(lang)}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(model.get('title') or 'Form')}</title>\n</head>\n"
    )
    return head + f"<body>\n<main>\n{body}\n</main>\n</body>\n</html>\n"


class _HtmlReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[M.Item] = []
        self.title = ""
        self.submit = ""
        self.report: list[str] = []
        self.taken: set[str] = {"page_1"}
        self.labels: dict[str, str] = {}
        self.label_for: str | None = None
        self.text: list[str] = []
        self.capture: str | None = None
        self.groups: list[M.Item] = []
        self.select: M.Item | None = None
        self.option_value = ""
        self.by_name: dict[str, M.Item] = {}
        self.pending: list[tuple[M.Item, str]] = []

    def sink(self) -> list[M.Item]:
        return self.groups[-1]["items"] if self.groups else self.items

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag in ("label", "legend", "option", "title", "h1"):
            self.capture, self.text = tag, []
            self.label_for = a.get("for") if tag == "label" else None
            self.option_value = a.get("value", "")
        if tag == "fieldset":
            section: M.Item = {
                "id": safe_id(a.get("id") or "group", self.taken),
                "type": "section",
                "items": [],
            }
            self.sink().append(section)
            self.groups.append(section)
        elif tag == "input":
            self.input(a)
        elif tag in ("select", "textarea"):
            kind = (
                "textarea"
                if tag == "textarea"
                else ("multiselect" if "multiple" in a else "select")
            )
            item = self.new_field(a, kind)
            if tag == "select":
                self.select = item
        elif tag in ("script", "iframe", "canvas"):
            self.report.append(
                f"A <{tag}> was skipped; a form model holds questions, not page code."
            )

    def new_field(self, a: dict[str, str], kind: str) -> M.Item:
        name = a.get("name") or a.get("id") or kind
        item: M.Item = {"id": safe_id(name, self.taken), "type": kind}
        if "required" in a:
            item["required"] = True
        if a.get("placeholder"):
            item["placeholder"] = a["placeholder"]
        for attr, key in _VALIDATION.items():
            if a.get(attr):
                value: Any = a[attr]
                if key in ("min_length", "max_length") and value.isdigit():
                    value = int(value)
                item.setdefault("validation", {})[key] = value
        for key in _PROPS:
            if a.get(key):
                item.setdefault("props", {})[key] = a[key]
        if a.get("value") and kind not in ("radio", "checkbox"):
            item["default"] = a["value"]
        self.pending.append((item, "" if kind in ("radio", "checkbox") else a.get("id", "")))
        self.sink().append(item)
        self.by_name[name] = item
        return item

    def input(self, a: dict[str, str]) -> None:
        kind = a.get("type", "text").lower()
        if kind in ("submit", "button", "reset", "image"):
            if kind == "submit" and a.get("value"):
                self.submit = a["value"]
            return
        if kind in ("radio", "checkbox"):
            name = a.get("name") or a.get("id") or kind
            group = self.by_name.get(name) or self.new_field(a, kind)
            value = a.get("value", "on")
            group.setdefault("choices", []).append({"value": value, "label": value})
            if a.get("id"):
                self.pending.append((group, f"choice:{len(group['choices']) - 1}:{a['id']}"))
            return
        if kind not in _INPUT:
            self.report.append(f"An input of type {kind!r} was read as text.")
        self.new_field(a, _INPUT.get(kind, "text"))

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.capture:
            text = " ".join("".join(self.text).split()).replace("(required)", "").strip()
            if tag == "label" and self.label_for:
                self.labels[self.label_for] = text
            elif tag == "legend" and self.groups:
                self.groups[-1]["label"] = text
            elif tag == "option" and self.select is not None:
                self.select.setdefault("choices", []).append({
                    "value": self.option_value or text,
                    "label": text,
                })
            elif tag in ("title", "h1") and not self.title:
                self.title = text
            self.capture = None
        if tag == "fieldset" and self.groups:
            self.groups.pop()
        if tag == "select":
            self.select = None

    def finish(self) -> ImportResult:
        for item, key in self.pending:
            if key.startswith("choice:"):
                _tag, index, control = key.split(":", 2)
                if control in self.labels:
                    item["choices"][int(index)]["label"] = self.labels[control]
            elif key and key in self.labels:
                item["label"] = self.labels[key]
        self._fold(self.items)
        for item, _key in self.pending:
            if not item.get("label") and item["type"] != "hidden":
                self.report.append(f"{item['id']} has no label; Check This Form will ask for one.")
        model: M.Model = {
            "version": M.MODEL_VERSION,
            "title": self.title,
            "pages": [{"id": "page_1", "items": self.items}],
        }
        if self.submit:
            model["settings"] = {"submit_label": self.submit}
        return ImportResult(model, self.report)

    def _fold(self, entries: list[M.Item]) -> None:
        """A fieldset holding just one radio or check-box group is that group's question."""
        for n, item in enumerate(entries):
            if item["type"] != "section":
                continue
            inner = item["items"]
            if (
                len(inner) == 1
                and inner[0]["type"] in ("radio", "checkbox")
                and not inner[0].get("label")
            ):
                inner[0]["label"] = item.get("label", "")
                entries[n] = inner[0]
            else:
                self._fold(inner)


def import_html(text: str) -> ImportResult:
    reader = _HtmlReader()
    reader.feed(text)
    reader.close()
    return reader.finish()
