"""The form model as JSON: reading, writing and upgrading.

The JSON is the stored form. Its shape is fixed by ``schema/form.schema.json``
(:mod:`quill.core.forms.schema_check` checks it). Writing leaves out every
value that equals its default, so a contact form stays short enough to read.

**Versions and migrations.** Every stored form carries ``"version"``. When the
model changes in a way old forms do not fit, ``MODEL_VERSION`` goes up by one
and a migration is registered for the old number::

    @migration(1)
    def _one_to_two(data: dict) -> dict:
        # rename, split or default whatever version 2 needs
        return {**data, "version": 2}

``upgrade`` runs the chain from a form's version to ``MODEL_VERSION``, one
step at a time, so a form written for any earlier version always opens, and
is never changed in place. A form newer than this code is refused with a
sentence saying so, rather than half read.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import fields as dc_fields
from typing import Any, cast

from quill.core.forms.errors import FormModelError, FormVersionError
from quill.core.forms.model import (
    MODEL_VERSION,
    Cascade,
    Choice,
    Columns,
    Field,
    Form,
    Island,
    Item,
    JSONValue,
    Outcome,
    Page,
    Section,
    Settings,
)

#: The value of ``"model"`` in every stored form.
MODEL_NAME = "baf-form"

Migration = Callable[[dict[str, Any]], dict[str, Any]]
#: from-version -> function returning the data one version later.
MIGRATIONS: dict[int, Migration] = {}


def migration(from_version: int) -> Callable[[Migration], Migration]:
    """Register the migration from ``from_version`` to the next version."""

    def register(func: Migration) -> Migration:
        MIGRATIONS[from_version] = func
        return func

    return register


def upgrade(data: dict[str, Any], target: int = MODEL_VERSION) -> dict[str, Any]:
    """Run the registered migrations until ``data`` is at ``target``."""
    version = data.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise FormVersionError(f"The form's version, {version!r}, is not a version number.")
    if version > target:
        raise FormVersionError(
            f"This form was written for form model version {version}; this copy of "
            f"QUILL reads up to version {target}. Update QUILL to open it."
        )
    while version < target:
        step = MIGRATIONS.get(version)
        if step is None:
            raise FormVersionError(f"There is no way to upgrade a version {version} form yet.")
        data = step(dict(data))
        if data.get("version") != version + 1:
            raise FormVersionError(
                f"The upgrade from version {version} did not reach {version + 1}."
            )
        version += 1
    return data


# -- writing -----------------------------------------------------------------


def _compact(obj: Any, skip: tuple[str, ...] = ()) -> dict[str, Any]:
    """A dataclass as a dict, without fields that hold their default."""
    out: dict[str, Any] = {}
    for f in dc_fields(obj):
        if f.name in skip:
            continue
        value = getattr(obj, f.name)
        empty = (
            value is None or value is False or (isinstance(value, (str, list, dict)) and not value)
        )
        if empty and f.name != "kind":
            continue
        out[f.name] = value
    return out


def _choice(choice: Choice) -> dict[str, Any]:
    return _compact(choice) | {"value": choice.value, "label": choice.label}


def _item(item: Item) -> dict[str, Any]:
    if isinstance(item, Field):
        out: dict[str, Any] = {"kind": "field", "id": item.id, "type": item.type}
        out |= _compact(
            item, skip=("choices", "cascade", "fields", "settings", "kind", "id", "type")
        )
        if item.choices:
            out["choices"] = [_choice(c) for c in item.choices]
        if item.cascade is not None:
            out["cascade"] = _compact(item.cascade) | {"source": item.cascade.source}
        if item.settings:
            out["settings"] = dict(item.settings)
        if item.fields:
            out["fields"] = [_item(f) for f in item.fields]
        return out
    if isinstance(item, Section):
        head: dict[str, Any] = {"kind": "section", "id": item.id}
        out = head | _compact(item, skip=("items", "kind", "id"))
        out["items"] = [_item(i) for i in item.items]
        return out
    if isinstance(item, Columns):
        out = {"kind": "columns", "id": item.id}
        if item.count is not None:
            out["count"] = item.count
        if item.visible_when:
            out["visible_when"] = item.visible_when
        out["columns"] = [[_item(i) for i in col] for col in item.columns]
        return out
    return {"kind": "island", "text": item.text} | _compact(item, skip=("kind", "text"))


def to_dict(form: Form) -> dict[str, Any]:
    out: dict[str, Any] = {"model": MODEL_NAME, "version": form.version}
    for key in ("id", "title", "description"):
        if getattr(form, key):
            out[key] = getattr(form, key)
    out["language"] = form.language
    settings = _compact(form.settings, skip=("extra",))
    settings.update(form.settings.extra)
    if settings:
        out["settings"] = settings
    out["pages"] = [
        _compact(page, skip=("items",)) | {"id": page.id, "items": [_item(i) for i in page.items]}
        for page in form.pages
    ]
    if form.translations:
        out["translations"] = {lang: dict(s) for lang, s in form.translations.items()}
    if form.outcomes:
        out["outcomes"] = [{"when": o.when, "message": o.message} for o in form.outcomes]
    return out


def dumps(form: Form, *, indent: int | None = 2) -> str:
    return json.dumps(to_dict(form), indent=indent, ensure_ascii=False) + "\n"


# -- reading -----------------------------------------------------------------


def _need(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise FormModelError(f"{where} has no {key!r}.")
    return data[key]


def _opt_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return None if value is None else str(value)


def _field(data: dict[str, Any]) -> Field:
    where = f"Field {data.get('id', '?')!r}"
    cascade = data.get("cascade")
    score = data.get("score")
    return Field(
        id=str(_need(data, "id", where)),
        type=str(_need(data, "type", where)),
        label=str(data.get("label", "")),
        help=str(data.get("help", "")),
        required=bool(data.get("required", False)),
        placeholder=str(data.get("placeholder", "")),
        default=_opt_str(data, "default"),
        default_expr=_opt_str(data, "default_expr"),
        visible_when=_opt_str(data, "visible_when"),
        calculate=_opt_str(data, "calculate"),
        score=None if score is None else str(score),
        choices=[
            Choice(
                value=str(c["value"]),
                label=str(c.get("label", c["value"])),
                price=_opt_str(c, "price"),
                score=None if c.get("score") is None else float(c["score"]),
            )
            for c in data.get("choices", [])
        ],
        choice_library=_opt_str(data, "choice_library"),
        cascade=None
        if cascade is None
        else Cascade(
            source=str(cascade["source"]),
            library=_opt_str(cascade, "library"),
            empty_message=str(cascade.get("empty_message", "")),
            loading_message=str(cascade.get("loading_message", "")),
        ),
        settings=cast("dict[str, JSONValue]", dict(data.get("settings", {}))),
        fields=[_field(f) for f in data.get("fields", [])],
    )


def _items(raw: list[dict[str, Any]]) -> list[Item]:
    out: list[Item] = []
    for data in raw:
        kind = data.get("kind", "field")
        if kind == "field":
            out.append(_field(data))
        elif kind == "section":
            out.append(
                Section(
                    id=str(_need(data, "id", "A section")),
                    title=str(data.get("title", "")),
                    description=str(data.get("description", "")),
                    visible_when=_opt_str(data, "visible_when"),
                    items=_items(data.get("items", [])),
                )
            )
        elif kind == "columns":
            count = data.get("count")
            out.append(
                Columns(
                    id=str(_need(data, "id", "A columns layout")),
                    count=None if count is None else int(count),
                    columns=[_items(col) for col in data.get("columns", [])],
                    visible_when=_opt_str(data, "visible_when"),
                )
            )
        elif kind == "island":
            out.append(
                Island(
                    text=str(_need(data, "text", "An island")),
                    reason=str(data.get("reason", "")),
                    notation=str(data.get("notation", "bfl")),
                )
            )
        else:
            raise FormModelError(f"An item has the kind {kind!r}, which the model does not have.")
    return out


_SETTING_NAMES = {f.name for f in dc_fields(Settings)} - {"extra"}


def from_dict(data: dict[str, Any]) -> Form:
    """A stored form, upgraded to this version, as the model."""
    if data.get("model", MODEL_NAME) != MODEL_NAME:
        raise FormModelError(f"This is not a form model (model is {data.get('model')!r}).")
    data = upgrade(data)
    raw_settings = dict(data.get("settings", {}))
    settings = Settings(**{
        k: raw_settings.pop(k) for k in list(raw_settings) if k in _SETTING_NAMES
    })
    settings.extra = raw_settings
    pages = [
        Page(
            id=str(_need(p, "id", "A page")),
            title=str(p.get("title", "")),
            description=str(p.get("description", "")),
            visible_when=_opt_str(p, "visible_when"),
            items=_items(p.get("items", [])),
        )
        for p in data.get("pages", [])
    ] or [Page(id="page_1")]
    return Form(
        id=str(data.get("id", "")),
        title=str(data.get("title", "")),
        description=str(data.get("description", "")),
        language=str(data.get("language", "en")),
        settings=settings,
        pages=pages,
        translations={k: dict(v) for k, v in data.get("translations", {}).items()},
        outcomes=[
            Outcome(when=str(o["when"]), message=str(o["message"]))
            for o in data.get("outcomes", [])
        ],
        version=int(data["version"]) if "version" in data else 1,
    )


def loads(text: str) -> Form:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FormModelError(f"The form is not valid JSON: {exc.msg}, line {exc.lineno}.") from exc
    if not isinstance(data, dict):
        raise FormModelError("A form must be a JSON object.")
    return from_dict(data)
