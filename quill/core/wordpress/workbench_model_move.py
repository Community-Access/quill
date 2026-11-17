"""Moving a definition into QUILL Site Types, as a previewed copy (WP-R-038).

A post type, taxonomy or field-plugin field group listed in the Content Model
(:mod:`~quill.core.wordpress.workbench_model_sources`) can be copied into QUILL
Site Types under the same key (:func:`move_body`, :func:`move_preview`). The
original is never deleted or changed: its plugin keeps it.

Two facts of the QUILL Site Types plugin shape what the preview says. It will
not take a post type or taxonomy something else still registers
(``qst_taken``, status 409), so the preview says to turn the original off at
its source first; its content stays in the database. And a field group only
registers field names as meta, so values a plugin already saved under those
names (ACF, Meta Box and CMB2 save each field as meta of its own name, Pods
does when the pod's storage is meta) show as custom fields at once.

A field's kind is chosen from its plugin's own field type where the plugin
says it, else from its JSON schema (:func:`kind_for`). Wx-free and network-free.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = ["kind_for", "move_body", "move_preview"]


def kind_for(spec: Mapping[str, Any], plugin_type: str = "") -> str:
    """The QUILL Site Types field kind closest to a field's schema (and its plugin's type)."""
    named = {
        "textarea": "long_text", "paragraph": "long_text", "wysiwyg": "rich_text",
        "email": "email", "url": "link", "website": "link", "phone": "phone",
        "true_false": "true_false", "boolean": "true_false", "number": "number",
        "currency": "money", "date_picker": "date", "date": "date", "time_picker": "time",
        "time": "time", "date_time_picker": "datetime", "datetime": "datetime",
        "color_picker": "colour", "color": "colour", "colorpicker": "colour", "image": "picture",
        "file": "file", "gallery": "gallery", "post_object": "related_item",
        "relationship": "related_item", "pick": "related_item", "taxonomy": "related_term",
        "user": "related_user", "repeater": "repeater", "group": "group",
        "google_map": "location", "select": "choice", "radio": "choice",
        "checkbox": "choices", "multicheck": "choices",
    }  # fmt: skip
    if plugin_type in named:
        return named[plugin_type]
    kind = spec.get("type")
    kind = next((k for k in kind if k != "null"), "") if isinstance(kind, list) else kind
    if spec.get("enum"):
        return "choice"
    if kind == "boolean":
        return "true_false"
    if kind in ("integer", "number"):
        return "number"
    if kind == "array":
        items = spec.get("items") if isinstance(spec.get("items"), dict) else {}
        if (items or {}).get("enum"):
            return "choices"
        return "repeater" if (items or {}).get("type") == "object" else "text"
    if kind == "object":
        return "group"
    return {"email": "email", "uri": "link", "date-time": "datetime"}.get(
        str(spec.get("format", "")), "text"
    )


_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def move_body(what: str, key: str, info: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The QUILL Site Types body for a copy of one definition, and what does not come across.

    *info* is what WordPress says about a type or taxonomy (``wp/v2/types``,
    ``context=edit``), or a field group row's ``movable`` record.
    """
    skipped: list[str] = []
    if what == "type":
        labels = info.get("labels") if isinstance(info.get("labels"), dict) else {}
        supports = info.get("supports")
        body: dict[str, Any] = {
            "slug": key,
            "name": str(info.get("name") or key),
            "singular_name": str((labels or {}).get("singular_name") or info.get("name") or key),
            "description": str(info.get("description") or ""),
            "hierarchical": bool(info.get("hierarchical")),
            "has_archive": bool(info.get("has_archive")),
            "taxonomies": [str(t) for t in info.get("taxonomies") or []],
        }
        if isinstance(supports, dict):
            body["supports"] = [k for k, on in supports.items() if on]
        if isinstance(info.get("icon"), str) and info["icon"]:
            body["menu_icon"] = info["icon"]
        if labels:
            body["labels"] = {str(k): str(v) for k, v in labels.items() if isinstance(v, str)}
        return body, skipped
    if what == "taxonomy":
        labels = info.get("labels") if isinstance(info.get("labels"), dict) else {}
        return {
            "slug": key,
            "name": str(info.get("name") or key),
            "singular_name": str((labels or {}).get("singular_name") or info.get("name") or key),
            "hierarchical": bool(info.get("hierarchical")),
            "object_types": [str(t) for t in info.get("types") or []] or ["post"],
        }, skipped
    fields: list[dict[str, Any]] = []
    for one in info.get("fields") or []:
        name = str(one.get("name", ""))
        if not _NAME.match(name):
            skipped.append(f"{name}: QUILL Site Types needs small letters, digits, - or _")
            continue
        spec = one.get("schema") if isinstance(one.get("schema"), dict) else {}
        kind = kind_for(spec or {}, str(one.get("plugin_type", "")))
        entry: dict[str, Any] = {
            "name": name,
            "label": str(one.get("label") or name.replace("_", " ").capitalize()),
            "kind": kind,
            "help": str((spec or {}).get("description") or ""),
            "required": False,
            "choices": [str(c) for c in (spec or {}).get("enum") or []],
        }
        fields.append(entry)
    attach = [str(a) for a in info.get("attach") or []]
    post_types: list[str] = []
    taxonomies: list[str] = []
    for one in attach:
        if one.startswith("taxonomy:"):
            taxonomies.append(one.removeprefix("taxonomy:"))
        elif one in ("term", "options-page", "pod", "settings"):
            skipped.append(f"attached to {one}, which QUILL Site Types cannot attach to")
        elif one not in ("user", "comment"):
            post_types.append(one)
    group_id = re.sub(r"[^a-z0-9_-]", "_", str(info.get("key") or key).lower()).strip("_")
    return {
        "id": group_id or "moved_fields",
        "title": str(info.get("name") or key),
        "attach": {
            "post_types": post_types,
            "taxonomies": taxonomies,
            "users": "user" in attach,
            "comments": "comment" in attach,
        },
        "fields": fields,
    }, skipped


def move_preview(
    site: str, what: str, body: Mapping[str, Any], owner: str, skipped: Sequence[str]
) -> tuple[str, list[str]]:
    """(summary, lines) shown before a definition is copied to QUILL Site Types."""
    from quill.core.wordpress.site_types_plugin import WHAT, define_preview

    _summary, lines = define_preview(site, what, body)
    lines += [f"Not copied: {s}" for s in skipped]
    noun = WHAT[what][2]
    name = body.get("name") or body.get("title") or body.get(WHAT[what][1])
    if what == "field_group":
        tail = (
            "Values already saved under these field names stay where they are, and QUILL Site "
            "Types shows them as custom fields too. Nothing is removed from "
            f"{owner}: its fields go on working until you turn them off there."
        )
    else:
        tail = (
            f"Nothing is removed from {owner}. QUILL Site Types will not take a {noun} that "
            f"something else still registers, so turn it off in {owner} first (its content "
            "stays in the database), then copy it here; until then the site refuses and nothing "
            "changes."
        )
    summary = f"Copy the {noun} {name} on {site} into QUILL Site Types, under the same key. {tail}"
    return summary, lines
