"""QUILL Site Types: defining post types, taxonomies and field groups over REST (PRD 12b).

WordPress has no REST route that creates a post type, a taxonomy or a field:
each is registered by PHP on every page load. The QUILL Site Types plugin
(``S:\\code\\quill-site-types``, 0.1.0) keeps definitions as data, registers
them on ``init`` with ``show_in_rest``, and serves ``quill-site-types/v1``:

- ``GET/POST /types``, ``/taxonomies``, ``/field-groups``; ``GET/POST/DELETE``
  one by its slug (a field group by its id). A save never changes the slug.
- ``GET /kinds``: the field kinds, built-in and the site's own.
- ``GET /export?format=php|json``: Export as Code.

Every route needs ``manage_options``; filling the fields in follows each
type's own capabilities through ``wp/v2``, so nothing here touches items.
Deleting a definition stops registering it; posts, terms and values stay in
the database, which is why Stop Defining can be undone by defining it again.

This is the contract as the plugin's own code states it; it has not yet met
a live WordPress (its tests run against a stand-in). Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.workbench_edit import EditRefused

__all__ = [
    "BUILTIN_KINDS",
    "KIND_TYPES",
    "add_kind",
    "apply_field",
    "field_preview",
    "field_sheet",
    "field_values",
    "kind_body",
    "kind_preview",
    "save_group",
    "NAMESPACE",
    "WHAT",
    "Definitions",
    "define",
    "define_body",
    "define_preview",
    "export_code",
    "parse_fields",
    "put_back",
    "read_definitions",
    "read_kinds",
    "stop_defining",
    "stop_preview",
]

NAMESPACE = "quill-site-types/v1"

#: What can be defined: (collection route, the key field, the words for one).
WHAT: Mapping[str, tuple[str, str, str]] = {
    "type": ("types", "slug", "post type"),
    "taxonomy": ("taxonomies", "slug", "taxonomy"),
    "field_group": ("field-groups", "id", "field group"),
}

#: The plugin's built-in field kinds (class-qst-fields.php), for a site that
#: will not list its own; the site's ``/kinds`` answer wins when it has one.
BUILTIN_KINDS = (
    "text", "long_text", "rich_text", "number", "money", "date", "time", "datetime",
    "true_false", "choice", "choices", "email", "address", "phone", "link", "colour",
    "picture", "file", "gallery", "related_item", "related_term", "related_user",
    "repeater", "group", "location", "transcript", "captions", "long_description",
    "language_text",
)  # fmt: skip

_SLUG = re.compile(r"^[a-z0-9_-]{1,20}$")


@dataclass(frozen=True)
class Definitions:
    """What QUILL Site Types defines on one site, by kind and key; *reason* when unreadable."""

    types: dict[str, dict[str, Any]] = field(default_factory=dict)
    taxonomies: dict[str, dict[str, Any]] = field(default_factory=dict)
    groups: dict[str, dict[str, Any]] = field(default_factory=dict)
    reason: str = ""

    def of(self, what: str) -> dict[str, dict[str, Any]]:
        return {"type": self.types, "taxonomy": self.taxonomies}.get(what, self.groups)


def _route(what: str, key: str = "") -> str:
    base = f"{NAMESPACE}/{WHAT[what][0]}"
    return f"{base}/{key}" if key else base


def _keyed(raw: Any, key: str) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for one in raw if isinstance(raw, list) else []:
        if isinstance(one, dict) and one.get(key):
            found[str(one[key])] = dict(one)
    return found


def read_definitions(api: WordPressApi) -> Definitions:
    """Every definition the plugin keeps; an account without ``manage_options`` gets the reason."""
    try:
        parts = {what: api.get(_route(what)) for what in WHAT}
    except WordPressApiError as exc:
        if exc.status in (401, 403):
            return Definitions(
                reason="Reading and changing definitions needs the Administrator role "
                "(manage_options)."
            )
        raise
    return Definitions(
        _keyed(parts["type"], "slug"),
        _keyed(parts["taxonomy"], "slug"),
        _keyed(parts["field_group"], "id"),
    )


def read_kinds(api: WordPressApi) -> tuple[str, ...]:
    """The field kinds the site knows, its own included; the built-in ones when it will not say."""
    try:
        raw = api.get(f"{NAMESPACE}/kinds")
    except WordPressApiError:
        return BUILTIN_KINDS
    rows = raw if isinstance(raw, list) else []
    kinds = tuple(str(k["kind"]) for k in rows if isinstance(k, dict) and k.get("kind"))
    return kinds or BUILTIN_KINDS


def _words(text: str) -> list[str]:
    return [w.strip() for w in re.split(r"[,\n]", text or "") if w.strip()]


def parse_fields(text: str, kinds: Sequence[str]) -> list[dict[str, Any]]:
    """``name: kind, name: kind`` (or one per line) as field definitions; a bad one is refused.

    A field without a kind is text. Names follow the plugin's rule: small
    letters, digits, hyphens or underscores, not starting with an underscore.
    """
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for part in _words(text):
        name, _sep, kind = (p.strip() for p in part.partition(":"))
        kind = kind.lower().replace(" ", "_") or "text"
        if not _SLUG.match(name) or name.startswith("_"):
            raise EditRefused(
                f"{name or 'A field'} needs a name of small letters, digits, hyphens or "
                "underscores, not starting with an underscore."
            )
        if name in seen:
            raise EditRefused(f"The field {name} is in the group twice.")
        if kind not in kinds:
            raise EditRefused(f"{name}: this site has no field kind called {kind}.")
        seen.add(name)
        fields.append({"name": name, "label": name.replace("_", " ").capitalize(), "kind": kind})
    return fields


def define_body(
    what: str,
    key: str,
    name: str,
    *,
    attach: str = "",
    fields: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """The request body for a new definition, checked before anything is sent.

    *attach* is the post types a taxonomy or field group belongs to, by slug,
    separated by commas.
    """
    if what not in WHAT:
        raise EditRefused("Choose a post type, a taxonomy or a field group.")
    clean = key.strip().lower()
    if not _SLUG.match(clean):
        raise EditRefused(
            f"{key or 'The key'} needs 1 to 20 small letters, digits, hyphens or underscores."
        )
    title = " ".join(name.split()) or clean.replace("_", " ").title()
    targets = [t.lower() for t in _words(attach)]
    if what == "type":
        return {"slug": clean, "name": title, "singular_name": title}
    if what == "taxonomy":
        return {"slug": clean, "name": title, "object_types": targets or ["post"]}
    if not fields:
        raise EditRefused("A field group needs at least one field.")
    return {
        "id": clean,
        "title": title,
        "attach": {"post_types": targets or ["post"]},
        "fields": [dict(f) for f in fields],
    }


def define_preview(site: str, what: str, body: Mapping[str, Any]) -> tuple[str, list[str]]:
    """(summary, lines) shown before a definition is sent."""
    _base, key, noun = WHAT[what]
    name = body.get("name") or body.get("title") or body.get(key)
    lines = [f"{noun.capitalize()}: {name} ({body.get(key)})"]
    if body.get("object_types"):
        lines.append("For: " + ", ".join(body["object_types"]))
    attach = body.get("attach")
    if isinstance(attach, dict) and attach.get("post_types"):
        lines.append("On: " + ", ".join(attach["post_types"]))
    lines += [f"Field {f['name']}: {f['kind']}" for f in body.get("fields") or []]
    summary = (
        f"Define the {noun} {name} on {site} through QUILL Site Types. It appears in REST "
        "and in this tree after a refresh; Stop Defining takes it away again and keeps its content."
    )
    return summary, lines


def define(api: WordPressApi, what: str, body: Mapping[str, Any]) -> dict[str, Any]:
    raw = api.post(_route(what), dict(body))
    return dict(raw) if isinstance(raw, dict) else dict(body)


def stop_preview(site: str, what: str, key: str, name: str) -> tuple[str, list[str]]:
    noun = WHAT[what][2]
    return (
        f"Stop defining the {noun} {name} on {site}. WordPress stops registering it; posts, "
        "terms and field values already saved stay in the database, and Ctrl+Z defines it again.",
        [f"{noun.capitalize()}: {name} ({key})", "Its content: kept"],
    )


def stop_defining(api: WordPressApi, what: str, key: str) -> dict[str, Any]:
    """Stop defining one; the definition as it was, for Ctrl+Z."""
    raw = api.delete(_route(what, key))
    previous = raw.get("previous") if isinstance(raw, dict) else None
    return dict(previous) if isinstance(previous, dict) else {}


def put_back(api: WordPressApi, what: str, previous: Mapping[str, Any]) -> str:
    """Define *previous* again (Ctrl+Z after Stop Defining)."""
    if not previous:
        return "The site did not send the old definition back, so it cannot be put back."
    define(api, what, previous)
    key = WHAT[what][1]
    return f"{previous.get(key)} is defined again."


def export_code(api: WordPressApi, fmt: str = "php") -> tuple[str, str]:
    """(file name, content) of Export as Code: the ``register_*`` calls, or the definitions."""
    raw = api.get(f"{NAMESPACE}/export", format="php" if fmt == "php" else "json")
    if not isinstance(raw, dict) or not isinstance(raw.get("content"), str):
        raise EditRefused("The site did not send the exported code.")
    default = "quill-site-types-export." + ("php" if fmt == "php" else "json")
    name = str(raw.get("filename") or default)
    return re.sub(r"[^A-Za-z0-9._-]", "-", name) or default, raw["content"]


# -- one field at a time (12b: each field's own sheet) ------------------------------------

_FIELD_KEYS = ("name", "kind", "label", "help", "required", "default", "choices")


def field_sheet(kinds: Sequence[str], *, new: bool) -> Any:
    """The sheet for one field of a group: its kind, label, help, required, default, choices."""
    from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

    fields = (
        FieldSpec(
            "name",
            "Name",
            readonly=not new,
            help="The key the value is saved under, such as isbn. It never changes once made.",
        ),
        FieldSpec(
            "kind",
            "Kind",
            FieldKind.CHOICE,
            choices=tuple(kinds),
            help="How it is edited and checked: text, email, a picture with alt text, and so on.",
        ),
        FieldSpec("label", "Label", help="What people see beside the field, such as ISBN."),
        FieldSpec("help", "Help", FieldKind.MULTILINE, help="One sentence F1 says for it."),
        FieldSpec("required", "Required", FieldKind.CHECK, help="A save without it is refused."),
        FieldSpec("default", "Default", help="The value a new item starts with; empty for none."),
        FieldSpec(
            "choices",
            "Choices",
            FieldKind.LIST,
            help="For Choice and Several choices: the values offered, separated by commas.",
        ),
    )
    return SheetSpec("site_type_field", "Field", (PageSpec("general", "General", fields),))


def field_values(field: Mapping[str, Any]) -> dict[str, Any]:
    """What the field's sheet shows, from the group's definition."""
    default = field.get("default", "")
    return {
        "name": str(field.get("name", "")),
        "kind": str(field.get("kind", "text")),
        "label": str(field.get("label", "")),
        "help": str(field.get("help", "")),
        "required": bool(field.get("required", False)),
        "default": "" if default is None else str(default),
        "choices": tuple(str(c) for c in field.get("choices") or ()),
    }


def _changed_field(field: dict[str, Any], changed: Mapping[str, Any], *, new: bool) -> None:
    for key, value in changed.items():
        if key not in _FIELD_KEYS or (key == "name" and not new):
            continue
        if key == "choices":
            field[key] = [str(v).strip() for v in (value or ()) if str(v).strip()]
        elif key == "required":
            field[key] = bool(value)
        elif key == "default" and value in ("", None):
            field.pop("default", None)
        else:
            field[key] = str(value or "").strip()


def apply_field(
    group: Mapping[str, Any],
    name: str,
    changed: Mapping[str, Any],
    kinds: Sequence[str],
) -> dict[str, Any]:
    """The whole group with field *name* changed (or added when *name* is ""), checked first.

    The plugin replaces a group on save, so the body is the full group: its
    title, where it attaches, and every field, the others untouched.
    """
    fields = [dict(f) for f in group.get("fields") or [] if isinstance(f, Mapping)]
    found = next((f for f in fields if f.get("name") == name), None) if name else None
    if name and found is None:
        raise EditRefused(f"The group no longer has a field called {name}.")
    field = dict(found or {"kind": "text", "required": False, "choices": []})
    _changed_field(field, changed, new=found is None)
    new_name = str(field.get("name", ""))
    if found is None:
        if not _SLUG.match(new_name) or new_name.startswith("_"):
            raise EditRefused(
                "A new field needs a name of small letters, digits, hyphens or underscores, "
                "not starting with an underscore."
            )
        if any(f.get("name") == new_name for f in fields):
            raise EditRefused(f"The field {new_name} is in the group already.")
        field.setdefault("label", new_name.replace("_", " ").capitalize())
        fields.append(field)
    else:
        fields = [field if f.get("name") == name else f for f in fields]
    if field.get("kind") not in kinds:
        raise EditRefused(f"{new_name}: this site has no field kind called {field.get('kind')}.")
    if field.get("kind") == "choice" and "default" in field:
        if field["default"] not in field.get("choices", []):
            raise EditRefused(f"{new_name}: the default must be one of its choices.")
    return {**dict(group), "fields": fields}


def field_preview(
    site: str,
    group: Mapping[str, Any],
    name: str,
    after: Mapping[str, Any],
) -> tuple[str, list[str]]:
    """(summary, lines): what changes in one field of *group* (as it was), before it is sent."""
    title = group.get("title") or group.get("id")
    was: Mapping[str, Any] = {}
    if name:
        was = next((f for f in group.get("fields") or [] if f.get("name") == name), {})
    now_name = name or str((after.get("fields") or [{}])[-1].get("name", ""))
    now: Mapping[str, Any] = next(
        (f for f in after.get("fields") or [] if f.get("name") == now_name), {}
    )

    def shown(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(v) for v in value) or "(none)"
        return "(none)" if value in (None, "") else str(value)

    lines = [
        f"{key}: {shown(was.get(key)) if was else '(new)'} becomes {shown(now.get(key))}"
        for key in _FIELD_KEYS
        if key != "name" and was.get(key) != now.get(key)
    ]
    verb = "Change the field" if name else "Add the field"
    return (
        f"{verb} {now_name} in {title} on {site}. Values already saved stay; Ctrl+Z puts the "
        "group back as it was.",
        lines or ["Nothing changes."],
    )


def save_group(api: WordPressApi, group: Mapping[str, Any]) -> dict[str, Any]:
    """Send the whole group back under its id (the plugin keeps the id)."""
    raw = api.post(_route("field_group", str(group["id"])), dict(group))
    return dict(raw) if isinstance(raw, dict) else dict(group)


# -- a site's own field kind (12b: "Your own kinds") ---------------------------------------

KIND_TYPES = ("string", "number", "integer", "boolean", "array", "object")


def kind_body(key: str, label: str, base: str, pattern: str = "") -> dict[str, Any]:
    """``POST /kinds``: a new kind, its schema, and a pattern values must match."""
    clean = key.strip().lower()
    if not _SLUG.match(clean):
        raise EditRefused(
            f"{key or 'The kind'} needs small letters, digits, hyphens or underscores."
        )
    if clean in BUILTIN_KINDS:
        raise EditRefused(f"{clean} is a built-in kind; give yours its own name.")
    if base not in KIND_TYPES:
        raise EditRefused(f"A kind is stored as one of: {', '.join(KIND_TYPES)}.")
    schema: dict[str, Any] = {"type": base}
    if pattern.strip():
        if base != "string":
            raise EditRefused("Only a kind stored as text can have a pattern.")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise EditRefused(f"The pattern is not a regular expression: {exc}.") from exc
        schema["pattern"] = pattern.strip()
    return {"kind": clean, "label": " ".join(label.split()) or clean, "schema": schema}


def kind_preview(site: str, body: Mapping[str, Any]) -> tuple[str, list[str]]:
    """(summary, lines) shown before a site-defined kind is added."""
    schema = body.get("schema") or {}
    lines = [f"Kind: {body.get('label')} ({body.get('kind')})", f"Stored as: {schema.get('type')}"]
    if schema.get("pattern"):
        lines.append(f"Values must match: {schema['pattern']}")
    return (
        f"Add the field kind {body.get('label')} to {site}. Field groups can use it at once. "
        "QUILL Site Types has no route to remove a kind, so this cannot be undone from here.",
        lines,
    )


def add_kind(api: WordPressApi, body: Mapping[str, Any]) -> dict[str, Any]:
    raw = api.post(f"{NAMESPACE}/kinds", dict(body))
    return dict(raw) if isinstance(raw, dict) else dict(body)
