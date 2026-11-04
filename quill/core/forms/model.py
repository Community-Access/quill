"""The form model: the one definition of a form (wordpress.md 17a.15).

A form is pages of items. An item is a field, a section (a heading that owns
the items under it), a columns layout, or an island (text from a notation
QUILL could not read, kept exactly). Everything a form *does* — when it shows
a field, what it calculates, how it scores, what it fills in — is an
expression in the one expression language (:mod:`quill.core.forms.expr`),
stored as text.

The JSON spelling of this model, checked by ``schema/form.schema.json``, is
what BAF stores and what every notation (BFL, SurveyJS, XLSForm, HTML) maps
to and from. :mod:`quill.core.forms.model_json` reads and writes it.

Field ``settings`` hold the per-type options under BAF's own configuration
names (``min_length``, ``input_mask``, ``autocomplete``...), so the model and
BAF's builder never need a translation table for them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The model version this code writes. See ``model_json.MIGRATIONS``.
MODEL_VERSION = 1

JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

#: Every field type the model holds, with its family. The families are
#: input, choice, date, contact, file, layout, pricing, payment, post, user
#: and helper. ``CHOICE_TYPES`` take choices or a choice library.
FIELD_TYPES: dict[str, str] = {
    "text": "input", "textarea": "input", "number": "input", "password": "input",
    "hidden": "input", "color": "input", "range": "input", "slider": "input",
    "toggle": "input", "otp": "input", "rich_text": "input", "currency": "input",
    "email": "contact", "phone": "contact", "website": "contact", "name": "contact",
    "address": "contact", "map": "contact",
    "select": "choice", "multiselect": "choice", "radio": "choice", "checkbox": "choice",
    "consent": "choice", "likert": "choice", "ranking": "choice", "rating": "choice",
    "nps": "choice", "matrix": "choice", "image_choice": "choice", "quiz": "choice",
    "date": "date", "time": "date", "datetime": "date", "daterange": "date",
    "appointment": "date",
    "fileupload": "file", "signature": "file", "typed_signature": "file",
    "captcha": "helper", "repeater": "helper", "calculation": "helper",
    "submit": "helper", "save": "helper", "progress": "helper", "summary": "helper",
    "social": "helper", "table": "helper",
    "html": "layout", "divider": "layout", "spacer": "layout",
    "product": "pricing", "quantity": "pricing", "price": "pricing", "total": "pricing",
    "coupon": "pricing", "payment": "payment",
    "post_title": "post", "post_content": "post", "post_excerpt": "post",
    "post_category": "post", "post_tags": "post", "post_image": "post", "post_custom": "post",
    "user_login": "user", "user_email": "user", "user_password": "user",
}  # fmt: skip

CHOICE_TYPES: frozenset[str] = frozenset(
    ("select", "multiselect", "radio", "checkbox", "likert", "ranking",
     "matrix", "image_choice", "quiz")
)  # fmt: skip

#: Spoken names for field types, for summaries and the outline.
TYPE_NAMES: dict[str, str] = {
    "text": "text", "textarea": "long text", "number": "number", "password": "password",
    "hidden": "hidden", "color": "colour", "range": "range", "slider": "slider",
    "toggle": "on or off", "otp": "one-time code", "rich_text": "formatted text",
    "currency": "amount of money", "email": "email", "phone": "phone number",
    "website": "web address", "name": "name", "address": "address", "map": "map location",
    "select": "drop-down list", "multiselect": "multiple-choice list",
    "radio": "choose one", "checkbox": "check boxes", "consent": "agreement check box",
    "likert": "agreement scale", "ranking": "ranking", "rating": "rating",
    "nps": "0 to 10 score", "matrix": "grid of questions", "image_choice": "picture choice",
    "quiz": "quiz question", "date": "date", "time": "time", "datetime": "date and time",
    "daterange": "date range", "appointment": "appointment", "fileupload": "file upload",
    "signature": "signature", "typed_signature": "typed signature", "captcha": "CAPTCHA",
    "repeater": "repeating group", "calculation": "calculation", "submit": "submit button",
    "save": "save and continue button", "progress": "progress bar", "summary": "summary",
    "social": "social sign-in", "table": "table", "html": "HTML block", "divider": "divider",
    "spacer": "spacer", "product": "product", "quantity": "quantity", "price": "price",
    "total": "total", "coupon": "coupon code", "payment": "payment",
    "post_title": "post title", "post_content": "post content", "post_excerpt": "post excerpt",
    "post_category": "post category", "post_tags": "post tags", "post_image": "post image",
    "post_custom": "custom post field", "user_login": "user name", "user_email": "user email",
    "user_password": "user password",
}  # fmt: skip


@dataclass
class Choice:
    value: str
    label: str
    price: str | None = None
    score: float | None = None


@dataclass
class Cascade:
    """A list whose choices depend on another field (Country, then State)."""

    source: str  # the id of the field it follows
    library: str | None = None
    empty_message: str = ""
    loading_message: str = ""


@dataclass
class Field:
    id: str
    type: str
    label: str = ""
    help: str = ""
    required: bool = False
    placeholder: str = ""
    default: str | None = None
    #: A smart default, as an expression: ``today + 7``, ``user.email``.
    default_expr: str | None = None
    visible_when: str | None = None
    calculate: str | None = None
    #: Quiz scoring: an expression worth points, such as ``#q1 is "Paris"``.
    score: str | None = None
    choices: list[Choice] = field(default_factory=list)
    choice_library: str | None = None
    cascade: Cascade | None = None
    settings: dict[str, JSONValue] = field(default_factory=dict)
    #: The fields inside a repeater.
    fields: list[Field] = field(default_factory=list)
    kind: str = "field"


@dataclass
class Island:
    """Text QUILL could not read, kept byte for byte and written back as is."""

    text: str
    reason: str = ""
    notation: str = "bfl"
    kind: str = "island"


@dataclass
class Columns:
    id: str
    count: int | None = None
    columns: list[list[Item]] = field(default_factory=list)
    visible_when: str | None = None
    kind: str = "columns"


@dataclass
class Section:
    id: str
    title: str = ""
    description: str = ""
    visible_when: str | None = None
    items: list[Item] = field(default_factory=list)
    kind: str = "section"


Item = Field | Section | Columns | Island


@dataclass
class Page:
    id: str
    title: str = ""
    description: str = ""
    visible_when: str | None = None
    items: list[Item] = field(default_factory=list)


@dataclass
class Outcome:
    """Quiz or survey outcome: a message shown when an expression holds."""

    when: str
    message: str


@dataclass
class Settings:
    submit_label: str = ""
    success_message: str = ""
    redirect_url: str = ""
    ajax: bool = False
    honeypot: bool = False
    captcha: bool = False
    captcha_type: str = ""
    save_and_continue: bool = False
    rate_limit: bool = False
    #: Anything else BAF stores (notifications, limits, schedule...), by BAF's name.
    extra: dict[str, JSONValue] = field(default_factory=dict)


@dataclass
class Form:
    title: str = ""
    description: str = ""
    language: str = "en"
    settings: Settings = field(default_factory=Settings)
    pages: list[Page] = field(default_factory=lambda: [Page(id="page_1")])
    #: language -> translation key -> text. Keys are listed by
    #: :func:`quill.core.forms.translate.translatable_strings`.
    translations: dict[str, dict[str, str]] = field(default_factory=dict)
    outcomes: list[Outcome] = field(default_factory=list)
    version: int = MODEL_VERSION
    id: str = ""


def walk_items(items: list[Item]) -> list[Item]:
    """Every item, depth first, in document order (sections, columns, repeaters)."""
    out: list[Item] = []
    for item in items:
        out.append(item)
        if isinstance(item, Section):
            out.extend(walk_items(item.items))
        elif isinstance(item, Columns):
            for column in item.columns:
                out.extend(walk_items(column))
        elif isinstance(item, Field) and item.fields:
            out.extend(walk_items(list(item.fields)))
    return out


def all_fields(form: Form) -> list[Field]:
    """Every field in the form, in order."""
    return [i for page in form.pages for i in walk_items(page.items) if isinstance(i, Field)]


def find_field(form: Form, field_id: str) -> Field | None:
    for item in all_fields(form):
        if item.id == field_id:
            return item
    return None


def islands(form: Form) -> list[Island]:
    return [i for page in form.pages for i in walk_items(page.items) if isinstance(i, Island)]
