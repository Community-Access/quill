"""Every kind of widget, not only Text (wordpress.md 9.17, gap 8).

A classic theme's widget areas hold block widgets (``id_base`` ``block``,
whose content is block markup) and *legacy* widgets, each a PHP class with
its own form: Search, Categories, Recent Posts, a plugin's widget. WordPress
(5.8 and later, ``edit_theme_options``) reaches those through
``wp/v2/widget-types``:

- ``widget-types`` lists every type the site has;
- ``widget-types/{id}/encode`` answers with the type's own **form**, as HTML,
  for an instance (or for none, a new one), and turns that form's answers
  (``form_data``) into an encoded **instance** to save, with a preview;
- ``widget-types/{id}/render`` renders an instance as the visitor sees it.

So QUILL never guesses a widget's fields: :func:`form_fields` reads the
controls out of the form WordPress sends (text, number, address, check box,
choice, text area), labelled by their own ``<label>``, and
:func:`encode_answers` sends them back under the names the form used. A
preview is the rendered widget as plain text (:func:`preview_text`).

A change re-reads the widget first and stops when it changed on the site
(:func:`check_widget`); the undo of a save puts the earlier instance back,
of an add removes the widget, and of a remove moves it back from Inactive
Widgets, where WordPress keeps it. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import plain_text
from quill.core.wordpress.workbench_edit import EditConflict

__all__ = [
    "INACTIVE",
    "Encoded",
    "FormControl",
    "WidgetType",
    "check_widget",
    "encode_answers",
    "encode_form",
    "form_fields",
    "list_widget_types",
    "load_widget",
    "new_form",
    "preview_text",
    "render_instance",
    "save_instance",
]

INACTIVE = "wp_inactive_widgets"
"""Where WordPress keeps a removed widget, so it can come back."""


@dataclass(frozen=True)
class WidgetType:
    id: str
    name: str
    description: str

    def row(self) -> str:
        return f"{self.name}: {self.description}" if self.description else self.name


def list_widget_types(api: WordPressApi) -> list[WidgetType]:
    """Every widget type, Block first (it holds any block), the rest by name."""
    raw = api.get("wp/v2/widget-types", context="edit")
    types = [
        WidgetType(
            str(r.get("id", "")),
            plain_text(str(r.get("name") or r.get("id") or "")),
            plain_text(str(r.get("description") or "")),
        )
        for r in (raw if isinstance(raw, list) else [])
        if isinstance(r, dict) and r.get("id")
    ]
    return sorted(types, key=lambda t: (t.id != "block", t.name.casefold()))


@dataclass
class FormControl:
    """One control of a legacy widget's own form, as WordPress drew it."""

    name: str  # the form's own field name, sent back as it is
    label: str
    kind: str  # text, multiline, check, choice
    value: str = ""
    checked: bool = False
    choices: list[tuple[str, str]] = field(default_factory=list)  # (value, words)

    @property
    def key(self) -> str:
        """The setting's own name ("title" in ``widget-search[2][title]``)."""
        return self.name.rstrip("]").rsplit("[", 1)[-1] if "[" in self.name else self.name


class _FormReader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.controls: list[FormControl] = []
        self.ids: dict[str, FormControl] = {}
        self.labels: dict[str, str] = {}
        self._label_for = ""
        self._label_words: list[str] = []
        self._in_label = False
        self._select: FormControl | None = None
        self._option: tuple[str, list[str]] | None = None
        self._textarea: FormControl | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "label":
            self._in_label, self._label_for, self._label_words = True, a.get("for", ""), []
        elif tag == "input" and a.get("name"):
            kind = a.get("type", "text").lower()
            if kind in ("hidden", "submit", "button", "image", "file", "reset"):
                return
            if kind == "radio":
                return  # radios are rare in widget forms; left as WordPress has them
            control = FormControl(
                a["name"],
                "",
                "check" if kind == "checkbox" else "text",
                a.get("value", "") if kind != "checkbox" else a.get("value", "on") or "on",
                checked="checked" in a,
            )
            self._add(control, a.get("id", ""))
        elif tag == "textarea" and a.get("name"):
            self._textarea = FormControl(a["name"], "", "multiline")
            self._add(self._textarea, a.get("id", ""))
        elif tag == "select" and a.get("name"):
            self._select = FormControl(a["name"], "", "choice")
            self._add(self._select, a.get("id", ""))
        elif tag == "option" and self._select is not None:
            self._option = (a.get("value", ""), [])
            if "selected" in a:
                self._select.value = a.get("value", "")

    def _add(self, control: FormControl, element_id: str) -> None:
        self.controls.append(control)
        if element_id:
            self.ids[element_id] = control
        if self._in_label and not self._label_for:
            self._label_for = f"#{len(self.controls)}"
            self.ids[self._label_for] = control

    def handle_endtag(self, tag: str) -> None:
        if tag == "label":
            self._in_label = False
            if self._label_for:
                self.labels[self._label_for] = " ".join("".join(self._label_words).split())
        elif tag == "option" and self._select is not None and self._option is not None:
            value, words = self._option
            self._select.choices.append((value, " ".join("".join(words).split()) or value))
            self._option = None
        elif tag == "select":
            self._select = None
        elif tag == "textarea":
            self._textarea = None

    def handle_data(self, data: str) -> None:
        if self._in_label:
            self._label_words.append(data)
        if self._option is not None:
            self._option[1].append(data)
        if self._textarea is not None:
            self._textarea.value += data


def form_fields(form_html: str) -> list[FormControl]:
    """The controls of a widget's own form, each named by its label."""
    reader = _FormReader()
    reader.feed(form_html)
    reader.close()
    for element_id, words in reader.labels.items():
        control = reader.ids.get(element_id)
        if control is not None and words:
            control.label = words.rstrip(":").strip()
    for control in reader.controls:
        if control.kind == "choice" and not control.value and control.choices:
            control.value = control.choices[0][0]
        if not control.label:
            control.label = control.key.replace("_", " ").replace("-", " ").capitalize()
    return reader.controls


def encode_answers(controls: list[FormControl], answers: Mapping[str, Any]) -> str:
    """The form's answers as WordPress's form would post them (unchecked boxes left out)."""
    pairs: list[tuple[str, str]] = []
    for control in controls:
        unanswered = control.checked if control.kind == "check" else control.value
        given = answers.get(control.name, unanswered)  # a control not asked keeps its value
        if control.kind == "check":
            if given:
                pairs.append((control.name, control.value or "on"))
            continue
        pairs.append((control.name, str(given)))
    return urlencode(pairs)


@dataclass(frozen=True)
class Encoded:
    form: str
    instance: Mapping[str, Any]
    preview: str


def _encode(api: WordPressApi, type_id: str, body: Mapping[str, Any]) -> Encoded:
    raw = api.post(f"wp/v2/widget-types/{type_id}/encode", dict(body))
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not send the widget's form.")
    found = raw.get("instance")
    instance: dict[str, Any] = dict(found) if isinstance(found, dict) else {}
    return Encoded(str(raw.get("form") or ""), instance, preview_text(raw.get("preview")))


def new_form(api: WordPressApi, type_id: str, instance: Mapping[str, Any] | None = None) -> Encoded:
    """The type's form, empty or filled from *instance* (an encoded one, as the site sent it)."""
    return _encode(api, type_id, {"instance": dict(instance)} if instance else {})


def encode_form(api: WordPressApi, type_id: str, form_data: str) -> Encoded:
    """The form's answers as an instance to save, with its preview."""
    return _encode(api, type_id, {"form_data": form_data})


def preview_text(html: Any) -> str:
    return " ".join(plain_text(str(html or "")).split())


def render_instance(api: WordPressApi, type_id: str, instance: Mapping[str, Any]) -> str:
    """The widget as a visitor sees it, in words."""
    raw = api.post(f"wp/v2/widget-types/{type_id}/render", {"instance": dict(instance)})
    return preview_text(raw.get("preview") if isinstance(raw, dict) else "")


def load_widget(api: WordPressApi, widget_id: str) -> dict[str, Any]:
    raw = api.get(f"wp/v2/widgets/{widget_id}", context="edit")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not send the widget.")
    return raw


def check_widget(api: WordPressApi, loaded: Mapping[str, Any]) -> dict[str, Any]:
    """Read the widget again; refuse when its instance or area changed since *loaded*."""
    now = load_widget(api, str(loaded.get("id", "")))
    if now.get("instance") != loaded.get("instance") or now.get("sidebar") != loaded.get("sidebar"):
        raise EditConflict(
            "That widget was changed on the site after QUILL read it. Nothing was sent; read "
            "the widgets again."
        )
    return now


def save_instance(
    api: WordPressApi, loaded: Mapping[str, Any], instance: Mapping[str, Any]
) -> dict[str, Any]:
    """Conflict-checked save of a widget's new instance."""
    check_widget(api, loaded)
    answer = api.post(
        f"wp/v2/widgets/{loaded.get('id', '')}", {"instance": dict(instance)}, context="edit"
    )
    return answer if isinstance(answer, dict) else {}
