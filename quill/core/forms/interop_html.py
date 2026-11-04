"""Plain HTML forms in and out, with nothing but the standard library.

Export writes the accessible patterns BAF's renderer uses: every control has
a ``<label for>``; a choice group is a ``<fieldset>`` with its question as the
``<legend>``; help is tied to its control with ``aria-describedby``; required
is the ``required`` attribute and the word "(required)" in the label, never a
colour or an asterisk alone; autofill hints are ``autocomplete``. Conditions
are written as ``data-visible-when`` for a script to use; with no script the
whole form shows, which is the safe failure.

Import reads ``<label>``, ``<input>``, ``<select>``, ``<textarea>`` and
``<fieldset>``/``<legend>`` from any page, and reports anything it skipped.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from typing import Any

from quill.core.forms.interop_common import ImportResult, safe_id
from quill.core.forms.model import Choice, Columns, Field, Form, Island, Item, Section

_INPUT = {
    "email": "email", "number": "number", "tel": "phone", "url": "website", "date": "date",
    "time": "time", "datetime-local": "datetime", "password": "password", "color": "color",
    "range": "range", "file": "fileupload", "hidden": "hidden", "text": "text", "search": "text",
}  # fmt: skip
_OUT = {v: k for k, v in _INPUT.items() if k != "search"}
_ATTRS = {
    "min": "min", "max": "max", "step": "step", "minlength": "min_length",
    "maxlength": "max_length", "pattern": "pattern", "autocomplete": "autocomplete",
    "inputmode": "inputmode",
}  # fmt: skip


def _a(name: str, value: Any) -> str:
    return f' {name}="{escape(str(value), quote=True)}"'


def _control(item: Field) -> list[str]:
    s = item.settings
    help_id = f"{item.id}-help"
    describe = _a("aria-describedby", help_id) if item.help else ""
    required = " required" if item.required else ""
    note = ' <span class="required">(required)</span>' if item.required else ""
    extra = "".join(
        _a(attr, s[key]) for attr, key in _ATTRS.items() if key in s and s[key] is not True
    )
    if item.placeholder:
        extra += _a("placeholder", item.placeholder)
    if item.default is not None:
        extra += _a("value", item.default)
    help_html = [f'<p id="{help_id}" class="help">{escape(item.help)}</p>'] if item.help else []
    if item.type in ("radio", "checkbox") and item.choices:
        kind = "radio" if item.type == "radio" else "checkbox"
        lines = [
            "<fieldset>",
            f"<legend>{escape(item.label)}{note}</legend>",
            *help_html,
        ]
        for n, c in enumerate(item.choices, 1):
            cid = f"{item.id}-{n}"
            lines.append(
                f'<div><input type="{kind}"{_a("id", cid)}{_a("name", item.id)}'
                f"{_a('value', c.value)}{required if kind == 'radio' else ''}{describe}> "
                f'<label for="{cid}">{escape(c.label)}</label></div>'
            )
        return lines + ["</fieldset>"]
    label = f'<label for="{item.id}">{escape(item.label)}{note}</label>'
    if item.type in ("select", "multiselect"):
        multiple = " multiple" if item.type == "multiselect" else ""
        options = [
            f"<option{_a('value', c.value)}>{escape(c.label)}</option>" for c in item.choices
        ]
        if item.choice_library:
            options = [f"<!-- choices from the {escape(item.choice_library)} library -->"]
        return [
            label,
            *help_html,
            f"<select{_a('id', item.id)}{_a('name', item.id)}{multiple}{required}{describe}>",
            *options,
            "</select>",
        ]
    if item.type == "textarea":
        return [
            label,
            *help_html,
            f"<textarea{_a('id', item.id)}{_a('name', item.id)}{required}{describe}{extra}>"
            "</textarea>",
        ]
    if item.type == "consent":
        return [
            f'<div><input type="checkbox"{_a("id", item.id)}{_a("name", item.id)} '
            f'value="yes"{required}{describe}> {label}</div>',
            *help_html,
        ]
    if item.type in ("html", "divider", "spacer"):
        return [str(item.settings.get("html", "<hr>" if item.type == "divider" else ""))]
    if item.type in ("submit",):
        return [f'<button type="submit">{escape(item.label or "Submit")}</button>']
    kind = _OUT.get(item.type, "text")
    return [
        label,
        *help_html,
        f'<input type="{kind}"{_a("id", item.id)}{_a("name", item.id)}{required}{describe}{extra}>',
    ]


def _items(items: list[Item], out: list[str]) -> None:
    for item in items:
        if isinstance(item, Island):
            out.append(
                "<!-- kept from the source, not shown: "
                f"{escape(item.text.splitlines()[0] if item.text else '')} -->"
            )
            continue
        cond = getattr(item, "visible_when", None)
        wrap = f"<div{_a('data-visible-when', cond)}>" if cond else ""
        if wrap:
            out.append(wrap)
        if isinstance(item, Section):
            out.append(f"<section{_a('aria-labelledby', item.id + '-title')}>")
            out.append(f'<h3 id="{item.id}-title">{escape(item.title)}</h3>')
            if item.description:
                out.append(f"<p>{escape(item.description)}</p>")
            _items(item.items, out)
            out.append("</section>")
        elif isinstance(item, Columns):
            out.append('<div class="columns">')
            for column in item.columns:
                out.append('<div class="column">')
                _items(column, out)
                out.append("</div>")
            out.append("</div>")
        elif isinstance(item, Field):
            out.append('<div class="field">')
            out.extend(_control(item))
            out.append("</div>")
        if wrap:
            out.append("</div>")


def export_html(form: Form, *, action: str = "", standalone: bool = True) -> str:
    """The form as HTML. ``action`` is where it submits; empty submits nowhere."""
    out = [
        f'<form{_a("action", action) if action else ""} method="post"{_a("lang", form.language)}>'
    ]
    if form.title:
        out.append(f"<h1>{escape(form.title)}</h1>")
    if form.description:
        out.append(f"<p>{escape(form.description)}</p>")
    for n, page in enumerate(form.pages, 1):
        out.append(f'<fieldset class="page"{_a("id", page.id)}>')
        out.append(f"<legend>{escape(page.title or f'Page {n} of {len(form.pages)}')}</legend>")
        _items(page.items, out)
        out.append("</fieldset>")
    out.append(f'<button type="submit">{escape(form.settings.submit_label or "Submit")}</button>')
    out.append("</form>")
    body = "\n".join(out)
    if not standalone:
        return body + "\n"
    return (
        f'<!doctype html>\n<html lang="{escape(form.language)}">\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(form.title or 'Form')}</title>\n</head>\n"
        + f"<body>\n<main>\n{body}\n</main>\n</body>\n</html>\n"
    )


class _HtmlReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.form = Form()
        self.report: list[str] = []
        self.taken: set[str] = set()
        self.labels: dict[str, str] = {}
        self.label_for: str | None = None
        self.text: list[str] = []
        self.capture: str | None = None  # "label", "legend", "option", "title"
        self.groups: list[Section] = []
        self.select: Field | None = None
        self.option_value = ""
        self.by_name: dict[str, Field] = {}
        self.pending: list[tuple[Field, str]] = []

    def sink(self) -> list[Item]:
        return self.groups[-1].items if self.groups else self.form.pages[0].items

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag in ("label", "legend", "option", "title", "h1"):
            self.capture, self.text = tag, []
            self.label_for = a.get("for") if tag == "label" else None
            self.option_value = a.get("value", "")
        if tag == "fieldset":
            section = Section(id=safe_id(a.get("id") or "group", self.taken))
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

    def new_field(self, a: dict[str, str], kind: str) -> Field:
        name = a.get("name") or a.get("id") or kind
        item = Field(id=safe_id(name, self.taken), type=kind, required="required" in a)
        item.placeholder = a.get("placeholder", "")
        for attr, key in _ATTRS.items():
            if a.get(attr):
                item.settings[key] = a[attr]
        if a.get("value") and kind not in ("radio", "checkbox"):
            item.default = a["value"]
        self.pending.append((item, "" if kind in ("radio", "checkbox") else a.get("id", "")))
        self.sink().append(item)
        self.by_name[name] = item
        return item

    def input(self, a: dict[str, str]) -> None:
        kind = a.get("type", "text").lower()
        if kind in ("submit", "button", "reset", "image"):
            if kind == "submit" and a.get("value"):
                self.form.settings.submit_label = a["value"]
            return
        if kind in ("radio", "checkbox"):
            name = a.get("name") or a.get("id") or kind
            group = self.by_name.get(name)
            if group is None:
                group = self.new_field(a, kind)
            group.choices.append(Choice(a.get("value", "on"), a.get("value", "on")))
            if a.get("id"):
                self.pending.append((group, f"choice:{len(group.choices) - 1}:{a['id']}"))
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
                self.groups[-1].title = text
            elif tag == "option" and self.select is not None:
                self.select.choices.append(Choice(self.option_value or text, text))
            elif tag in ("title", "h1") and not self.form.title:
                self.form.title = text
            self.capture = None
        if tag == "fieldset" and self.groups:
            self.groups.pop()
        if tag == "select":
            self.select = None

    def finish(self) -> ImportResult:
        for item, key in self.pending:
            if key.startswith("choice:"):
                _tag, index, control = key.split(":", 2)
                label = self.labels.get(control)
                if label:
                    item.choices[int(index)].label = label
            elif key and key in self.labels:
                item.label = self.labels[key]
        self._fold_groups(self.form.pages[0].items)
        for item, _key in self.pending:
            if not item.label and item.type not in ("hidden",):
                self.report.append(f"{item.id} has no label; Check This Form will ask for one.")
        return ImportResult(self.form, self.report)

    def _fold_groups(self, items: list[Item]) -> None:
        """A fieldset holding one radio or check-box group is that group's question."""
        for n, item in enumerate(items):
            if isinstance(item, Section):
                inner = [i for i in item.items if isinstance(i, Field)]
                if (
                    len(item.items) == 1
                    and inner
                    and inner[0].type in ("radio", "checkbox")
                    and not inner[0].label
                ):
                    inner[0].label = item.title
                    items[n] = inner[0]
                else:
                    self._fold_groups(item.items)


def import_html(text: str) -> ImportResult:
    reader = _HtmlReader()
    reader.feed(text)
    reader.close()
    return reader.finish()
