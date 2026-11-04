"""The form model: BAF's one JSON definition of a form (wordpress.md 17a.15).

A form is a JSON document, described by ``schema/form.schema.json`` and BAF's
``docs/form-model.md``; this module is a port of ``BAF_Form_Model``. QUILL
holds a form exactly as that JSON (plain dicts and lists), so nothing can be
lost or renamed between the two programs: the model QUILL reads is the model
BAF stores, key for key.

This module holds the facts code needs about the model (the 64 field types,
which take choices, the names a prop may not use), walks a form's items, and
checks the rules a schema cannot state (:func:`semantic_errors`). Scoring and
visibility are in :mod:`rules`.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator
from typing import Any

from quill.core.forms import expr as E

#: The model version this code reads and writes. See ``model_json``.
MODEL_VERSION = 1

Model = dict[str, Any]
Item = dict[str, Any]

#: Every field type, in the order BAF's builder lists them.
FIELD_TYPES: tuple[str, ...] = (
    "text", "textarea", "number", "email", "phone", "website", "hidden", "password",
    "color", "range", "slider", "currency", "otp", "toggle",
    "select", "multiselect", "radio", "checkbox", "consent", "image_choice",
    "likert", "matrix", "ranking", "rating", "nps", "quiz",
    "date", "time", "datetime", "daterange", "appointment",
    "name", "address", "fileupload", "signature", "typed_signature", "rich_text",
    "map", "social", "table", "captcha", "repeater", "calculation",
    "payment", "product", "quantity", "price", "total", "coupon",
    "html", "progress", "summary", "submit", "save",
    "post_title", "post_content", "post_excerpt", "post_category", "post_tags", "post_image",
    "post_custom", "user_login", "user_email", "user_password",
)  # fmt: skip
LAYOUT_TYPES = ("section", "columns")
CHOICE_TYPES = ("select", "multiselect", "radio", "checkbox", "ranking", "image_choice", "quiz")
OPTIONAL_CHOICE_TYPES = ("product", "likert", "consent", "toggle")

#: Fixed property names of objects with props; a prop may not reuse them.
FIXED_NAMES: dict[str, tuple[str, ...]] = {
    "page": ("id", "title", "description", "when", "items", "props"),
    "confirmation": ("id", "type", "message", "url", "page_id", "when", "props"),
    "notification": (
        "id", "enabled", "to", "cc", "bcc", "from_name", "from_email", "reply_to",
        "subject", "message", "when", "props",
    ),
    "settings": ("description", "desc", "language", "extensions", "ajax", "honeypot", "captcha"),
}  # fmt: skip

#: Spoken names for field types, for summaries and the outline.
TYPE_NAMES: dict[str, str] = {
    "text": "text", "textarea": "long text", "number": "number", "email": "email",
    "phone": "phone number", "website": "web address", "hidden": "hidden",
    "password": "password", "color": "colour", "range": "range", "slider": "slider",
    "currency": "amount of money", "otp": "one-time code", "toggle": "on or off",
    "select": "drop-down list", "multiselect": "multiple-choice list", "radio": "choose one",
    "checkbox": "check boxes", "consent": "agreement check box", "image_choice": "picture choice",
    "likert": "agreement scale", "matrix": "grid of questions", "ranking": "ranking",
    "rating": "rating", "nps": "0 to 10 score", "quiz": "quiz question", "date": "date",
    "time": "time", "datetime": "date and time", "daterange": "date range",
    "appointment": "appointment", "name": "name", "address": "address",
    "fileupload": "file upload", "signature": "signature", "typed_signature": "typed signature",
    "rich_text": "formatted text", "map": "map location", "social": "social sign-in",
    "table": "table", "captcha": "CAPTCHA", "repeater": "repeating group",
    "calculation": "calculation", "payment": "payment", "product": "product",
    "quantity": "quantity", "price": "price", "total": "total", "coupon": "coupon code",
    "html": "HTML block", "progress": "progress bar", "summary": "summary",
    "submit": "submit button", "save": "save and continue button", "post_title": "post title",
    "post_content": "post content", "post_excerpt": "post excerpt",
    "post_category": "post category", "post_tags": "post tags", "post_image": "post image",
    "post_custom": "custom post field", "user_login": "user name", "user_email": "user email",
    "user_password": "user password", "section": "section", "columns": "columns",
}  # fmt: skip
#: Families, for Insert Field and summaries ("Email address, email field").
INPUT_FAMILY = frozenset(
    "text textarea number email phone website hidden password color range slider currency "
    "otp date time datetime daterange name address".split()
)


def create(title: str = "") -> Model:
    """A new, empty form."""
    return {"version": MODEL_VERSION, "title": str(title), "pages": [{"id": "page_1", "items": []}]}


def is_field_type(kind: Any) -> bool:
    return kind in FIELD_TYPES


def slug(text: str) -> str:
    """BAF's choice value for a label: lower case, other runs to one hyphen, trimmed."""
    s = "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in str(text))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# -- walking -------------------------------------------------------------------


def items(model: Model) -> list[dict[str, Any]]:
    """Every item, depth first: ``{"item", "path", "page"}`` with its JSON pointer."""
    out: list[dict[str, Any]] = []
    for pi, page in enumerate(model.get("pages") or []):
        _walk(page.get("items") or [], f"/pages/{pi}/items", page.get("id", ""), out)
    return out


def _walk(entries: list[Item], path: str, page: str, out: list[dict[str, Any]]) -> None:
    for i, item in enumerate(entries):
        p = f"{path}/{i}"
        out.append({"item": item, "path": p, "page": page})
        if item.get("type") == "columns":
            for ci, col in enumerate(item.get("columns") or []):
                _walk(col.get("items") or [], f"{p}/columns/{ci}/items", page, out)
        elif isinstance(item.get("items"), list):
            _walk(item["items"], f"{p}/items", page, out)


def iter_items(model: Model) -> Iterator[Item]:
    for entry in items(model):
        yield entry["item"]


def fields(model: Model) -> dict[str, Item]:
    """Fields only (no sections or columns), by ID."""
    return {i["id"]: i for i in iter_items(model) if is_field_type(i.get("type"))}


def find(model: Model, item_id: str) -> Item | None:
    for item in iter_items(model):
        if item.get("id") == item_id:
            return item
    return None


def labels(model: Model) -> dict[str, str]:
    return {i["id"]: i.get("label", "") for i in iter_items(model) if "id" in i}


def choice_labels(model: Model) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    libs = model.get("choice_libraries") or {}
    for fid, field in fields(model).items():
        choices = field.get("choices")
        if choices is None and "choice_library" in field:
            choices = libs.get(field["choice_library"], [])
        for c in choices or []:
            out.setdefault(fid, {})[c["value"]] = c["label"]
    return out


def sentence(model: Model, text: str) -> str:
    """An expression as a sentence, with this form's labels."""
    from quill.core.forms.expr_sentence import sentence as say

    return say(E.parse(text), labels(model), choice_labels(model))


# -- the rules beyond the schema --------------------------------------------------------


def semantic_errors(model: Model) -> list[dict[str, str]]:  # noqa: C901 - one rule per block
    """What a schema cannot say: unique IDs, expressions naming real fields..."""
    errors: list[dict[str, str]] = []
    ids: dict[str, str] = {}
    page_ids: set[str] = set()
    found_fields: dict[str, Item] = {}

    def err(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    for k in model.get("settings") or {}:
        if k in FIXED_NAMES["settings"]:
            err(f"/settings/{k}", f'A setting cannot be called "{k}".')
    for pi, page in enumerate(model["pages"]):
        if page["id"] in page_ids:
            err(f"/pages/{pi}/id", f'The page ID "{page["id"]}" is used twice.')
        page_ids.add(page["id"])
        for k in page.get("props") or {}:
            if k in FIXED_NAMES["page"]:
                err(f"/pages/{pi}/props/{k}", f'A page prop cannot be called "{k}".')
    for entry in items(model):
        item = entry["item"]
        if item["id"] in ids or item["id"] in page_ids:
            err(entry["path"] + "/id", f'The ID "{item["id"]}" is used twice.')
        ids[item["id"]] = item["type"]
        if is_field_type(item["type"]):
            found_fields[item["id"]] = item

    def check_expr(text: str, path: str) -> None:
        for ref in E.refs(E.parse(text)):
            if ref not in ids:
                err(path, f"The expression refers to #{ref}, which is not in this form.")

    for pi, page in enumerate(model["pages"]):
        if "when" in page:
            check_expr(page["when"], f"/pages/{pi}/when")
    for entry in items(model):
        item = entry["item"]
        for k in ("when", "calculation", "smart_default"):
            if k in item:
                check_expr(item[k], f"{entry['path']}/{k}")
        source = (item.get("cascade") or {}).get("from")
        if source is not None and source not in found_fields:
            err(
                entry["path"] + "/cascade/from",
                f"The cascade comes from #{source}, which is not in this form.",
            )
        if "choices" in item:
            seen: set[str] = set()
            for ci, c in enumerate(item["choices"]):
                if c["value"] in seen:
                    err(
                        f"{entry['path']}/choices/{ci}/value",
                        f'The choice value "{c["value"]}" is used twice.',
                    )
                seen.add(c["value"])
        correct = (item.get("scoring") or {}).get("correct")
        if correct is not None and "choices" in item:
            values = [c["value"] for c in item["choices"]]
            for v in correct:
                if v not in values:
                    err(
                        entry["path"] + "/scoring/correct",
                        f'The correct answer "{v}" is not one of the choices.',
                    )
    for ri, rule in enumerate(model.get("rules") or []):
        check_expr(rule["when"], f"/rules/{ri}/when")
        if "value" in rule:
            check_expr(rule["value"], f"/rules/{ri}/value")
        for ti, target in enumerate(rule["targets"]):
            known = (
                target in page_ids
                if rule["action"] == "skip_to"
                else target in ids or target in page_ids
            )
            if not known:
                err(
                    f"/rules/{ri}/targets/{ti}",
                    f"The rule names #{target}, which is not in this form.",
                )
    for oi, outcome in enumerate((model.get("scoring") or {}).get("outcomes") or []):
        check_expr(outcome["when"], f"/scoring/outcomes/{oi}/when")
    for key, kind in (("confirmations", "confirmation"), ("notifications", "notification")):
        seen_ids: set[str] = set()
        for i, obj in enumerate(model.get(key) or []):
            if obj["id"] in seen_ids:
                err(f"/{key}/{i}/id", f'The ID "{obj["id"]}" is used twice.')
            seen_ids.add(obj["id"])
            if "when" in obj:
                check_expr(obj["when"], f"/{key}/{i}/when")
            for k in obj.get("props") or {}:
                if k in FIXED_NAMES[kind]:
                    err(f"/{key}/{i}/props/{k}", f'A {kind} prop cannot be called "{k}".')
    for lang, t in (model.get("translations") or {}).items():
        for fid in t.get("fields") or {}:
            if fid not in ids:
                err(
                    f"/translations/{lang}/fields/{fid}",
                    f"The translation names #{fid}, which is not in this form.",
                )
        for pid in t.get("pages") or {}:
            if pid not in page_ids:
                err(
                    f"/translations/{lang}/pages/{pid}",
                    f"The translation names page #{pid}, which is not in this form.",
                )
    return errors


def validate(model: Model) -> list[dict[str, str]]:
    """The schema's problems, or (when it fits) the rules beyond it. Empty when valid."""
    from quill.core.forms.schema_check import problems

    return problems(model)


def is_valid(model: Model) -> bool:
    return not validate(model)


# -- comparing and writing ------------------------------------------------------------------


def _norm(v: Any) -> Any:
    """For comparison: sorted keys, and booleans kept apart from numbers."""
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in sorted(v.items())}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, (int, float)):
        return ("num", float(v))
    return v


def same(a: Any, b: Any) -> bool:
    """Whether two models are the same document (key order ignored; true is not 1)."""
    return bool(_norm(a) == _norm(b))


def encode(v: Any, *, pretty: bool = False) -> str:
    """JSON as BAF writes it: UTF-8 as itself, slashes unescaped, ``.0`` kept."""
    if pretty:
        return json.dumps(v, ensure_ascii=False, indent=4)
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def to_json(model: Model) -> str:
    return encode(model, pretty=True) + "\n"


def clone(model: Model) -> Model:
    return copy.deepcopy(model)
