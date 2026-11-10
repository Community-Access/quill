"""Properties sheets for every WordPress object (PRD 8, Appendix A, WP-R-005, WP-R-014).

Each object kind gets a :class:`~quill.core.workbench.properties.SheetSpec`
whose field keys are the REST fields themselves (``title``, ``alt_text``,
``comment_status``), so a save sends exactly what changed under the names
WordPress reads, and the verify after it compares the same names
(:mod:`quill.core.wordpress.workbench_edit`). Pages follow Appendix A.

Two kinds of sheet are built rather than written:

- an item's **Meta** page comes from the registered meta in its route's
  schema (:mod:`~quill.core.wordpress.custom_fields`), and its **Organize**
  page grows a field for every taxonomy the item carries;
- **anything discovered** (section 12) gets a sheet built from its route's
  schema, or failing that from the object itself: strings as text, enums as
  choices, booleans as check boxes, numbers as numbers, dates as dates, lists
  as lists, and anything else read only with its raw field named.

Terms and authors are shown by name with their id ("News (12)"), and read
back by id or by name (:func:`term_ids`). Wx-free and network-free.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.site import friendly_date, human_size, raw_text, rendered
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec, Value

__all__ = [
    "ITEM_STATUSES",
    "SITE_SHEET",
    "labelled",
    "schema_sheet",
    "sheet_for",
    "sheet_title",
    "term_ids",
    "values_for",
]

ITEM_STATUSES = ("publish", "draft", "pending", "future", "private")
_OPEN = ("open", "closed")
_FORMATS = ("standard", "aside", "chat", "gallery", "link", "image", "quote", "status", "video")
_ROLES = ("subscriber", "contributor", "author", "editor", "administrator")
_COMMENT = ("approved", "hold", "spam", "trash")
_CORE_TAXONOMY_FIELDS = {"categories": "Categories", "tags": "Tags"}

_T, _M, _N, _C, _CH, _L, _D, _K = (
    FieldKind.TEXT,
    FieldKind.MULTILINE,
    FieldKind.NUMBER,
    FieldKind.CHECK,
    FieldKind.CHOICE,
    FieldKind.LIST,
    FieldKind.DATE,
    FieldKind.LINK,
)


def _f(key: str, label: str, kind: FieldKind = _T, **more: Any) -> FieldSpec:
    return FieldSpec(key, label, kind, **more)


def _ro(key: str, label: str, kind: FieldKind = _T) -> FieldSpec:
    return FieldSpec(key, label, kind, readonly=True, help=f"{label}, as the site says it.")


def _page(key: str, title: str, *fields: FieldSpec) -> PageSpec:
    return PageSpec(key, title, tuple(fields))


def labelled(name: str, ident: int) -> str:
    """ "News (12)": a term or person by name, with the id that saves it."""
    return f"{name} ({ident})" if name else str(ident)


_ID_AT_END = re.compile(r"\((\d+)\)\s*$")


def term_ids(values: Sequence[str], names: Mapping[str, int]) -> tuple[list[int], list[str]]:
    """Ids for "News (12)", "12" or "News"; and the names that match nothing."""
    ids: list[int] = []
    unknown: list[str] = []
    folded = {name.casefold(): ident for name, ident in names.items()}
    for value in values:
        text = value.strip()
        if not text:
            continue
        match = _ID_AT_END.search(text)
        if match:
            ids.append(int(match.group(1)))
        elif text.isdigit():
            ids.append(int(text))
        elif text.casefold() in folded:
            ids.append(folded[text.casefold()])
        else:
            unknown.append(text)
    return ids, unknown


def _item_sheet(row: WbRow, taxonomies: Mapping[str, str], meta: Mapping[str, Any]) -> SheetSpec:
    kind = row.subkind
    general = _page(
        "general",
        "General",
        _f("title", "Title"),
        _f("slug", "Slug", help="The last part of its address."),
        _f("status", "Status", _CH, choices=ITEM_STATUSES),
        _f(
            "password",
            "Password",
            help="Visitors type this to read it. Write only: what you type replaces it.",
        ),
        _f("author", "Author", _T, help="The person by name and number, such as Jeff (3)."),
        _f("date", "Published", _D, help="When it was or will be published, as 2026-11-09T14:00."),
        _ro("modified", "Last changed"),
        _ro("link", "Address", _K),
    )
    organize: list[FieldSpec] = []
    for field_name, label in taxonomies.items():
        organize.append(
            _f(field_name, label, _L, help=f"{label}, by name or number, separated by commas.")
        )
    if kind == "post":
        organize.append(_f("format", "Format", _CH, choices=_FORMATS))
        organize.append(_f("sticky", "Sticky", _C, help="Kept at the top of the posts page."))
    pages = [general]
    if organize:
        pages.append(_page("organize", "Organize", *organize))
    pages += [
        _page("featured", "Featured Image", _f("featured_media", "Picture number", _N)),
        _page("excerpt", "Excerpt", _f("excerpt", "Excerpt", _M)),
        _page(
            "discussion",
            "Discussion",
            _f("comment_status", "Comments", _CH, choices=_OPEN),
            _f("ping_status", "Pingbacks", _CH, choices=_OPEN),
        ),
    ]
    if kind == "page" or "parent" in row.raw:
        pages.append(
            _page(
                "template",
                "Template and Parent",
                _f("template", "Template"),
                _f("parent", "Parent number", _N, help="0 for a top-level page."),
                _f("menu_order", "Order", _N),
            )
        )
    meta_fields = tuple(
        _schema_field(f"meta.{key}", key, spec) for key, spec in sorted(meta.items())
    )
    if meta_fields:
        pages.append(PageSpec("meta", "Meta", meta_fields))
    return SheetSpec("item", "Item", tuple(pages))


def _schema_field(key: str, name: str, spec: Mapping[str, Any]) -> FieldSpec:
    """One field from a JSON schema property (section 12's mapping)."""
    label = str(spec.get("title") or spec.get("description") or name.replace("_", " ")).strip()
    label = label[:60] or name
    kind_name = spec.get("type")
    kinds = kind_name if isinstance(kind_name, list) else [kind_name]
    readonly = bool(spec.get("readonly"))
    context = spec.get("context")
    if isinstance(context, list) and context and "edit" not in context:
        readonly = True
    help_text = str(spec.get("description") or f"The {name} field.")
    if spec.get("enum"):
        choices = tuple(str(v) for v in spec.get("enum") or [])
        return FieldSpec(key, label, _CH, readonly, help=help_text, choices=choices)
    if "boolean" in kinds:
        return FieldSpec(key, label, _C, readonly, help=help_text)
    if "integer" in kinds or "number" in kinds:
        return FieldSpec(key, label, _N, readonly, help=help_text)
    if spec.get("format") == "date-time":
        return FieldSpec(key, label, _D, readonly, help=help_text)
    if "array" in kinds:
        items = spec.get("items") if isinstance(spec.get("items"), dict) else {}
        scalar = (items or {}).get("type") in ("string", "integer", "number")
        return FieldSpec(key, label, _L, readonly or not scalar, help=help_text)
    if "object" in kinds:
        return FieldSpec(key, label, _M, True, help=f"{help_text} Read only here, as JSON.")
    return FieldSpec(key, label, _T, readonly, help=help_text)


def schema_sheet(kind: str, title: str, properties: Mapping[str, Any]) -> SheetSpec:
    """A sheet built from a route's schema ``properties``: anything discovered (section 12)."""
    fields = tuple(
        _schema_field(name, name, spec)
        for name, spec in properties.items()
        if isinstance(spec, dict) and not name.startswith("_")
    )
    general = tuple(f for f in fields if f.kind is not _M) or fields[:1]
    rest = tuple(f for f in fields if f not in general)
    pages = [PageSpec("general", "General", general or (_ro("id", "Number"),))]
    if rest:
        pages.append(PageSpec("more", "More", rest))
    return SheetSpec(kind, title, tuple(pages))


def _raw_sheet(kind: str, raw: Mapping[str, Any]) -> SheetSpec:
    """A read-only sheet of every field the site sent, for a kind with no schema to hand."""
    fields = tuple(
        _ro(name, name.replace("_", " ").capitalize(), _M if isinstance(value, dict) else _T)
        for name, value in raw.items()
        if not name.startswith("_")
    )
    return SheetSpec(
        kind, kind.title(), (PageSpec("general", "General", fields or (_ro("id", "Number"),)),)
    )


_STATIC: dict[str, SheetSpec] = {
    "media": SheetSpec(
        "media",
        "Media",
        (
            _page(
                "general",
                "General",
                _f("title", "Title"),
                _ro("source_url", "File", _K),
                _ro("mime_type", "Type"),
                _ro("size", "Size"),
                _ro("dimensions", "Dimensions"),
                _ro("date", "Uploaded"),
                _ro("author_name", "Uploaded by"),
            ),
            _page(
                "alt",
                "Alt Text and Caption",
                _f(
                    "alt_text",
                    "Alt text",
                    help="What a picture shows, for people who cannot see it.",
                ),
                _f("caption", "Caption", _M),
            ),
            _page("description", "Description", _f("description", "Description", _M)),
            _page("attached", "Attached To", _f("post", "Attached to number", _N)),
            _page("sizes", "Sizes", _ro("sizes", "Sizes", _M)),
        ),
    ),
    "comment": SheetSpec(
        "comment",
        "Comment",
        (
            _page(
                "general",
                "General",
                _f("author_name", "Author"),
                _f(
                    "author_email",
                    "Email",
                    help="Shown only to people who can moderate comments.",
                ),
                _f("author_url", "Website"),
                _ro("date", "Written"),
                _f("status", "Status", _CH, choices=_COMMENT),
                _ro("type", "Type"),
            ),
            _page("text", "Text", _f("content", "Text", _M)),
            _page("post", "Post", _ro("post", "Post number"), _ro("post_title", "Post")),
            _page("thread", "Thread", _ro("parent", "Reply to comment number")),
        ),
    ),
    "term": SheetSpec(
        "term",
        "Term",
        (
            _page(
                "general",
                "General",
                _f("name", "Name"),
                _f("slug", "Slug"),
                _f("description", "Description", _M),
                _f("parent", "Parent number", _N, help="0 for none. Categories only."),
            ),
            _page("count", "Count", _ro("count", "Items"), _ro("link", "Address", _K)),
        ),
    ),
    "user": SheetSpec(
        "user",
        "User",
        (
            _page(
                "general",
                "General",
                _f("name", "Display name"),
                _ro("username", "Username"),
                _f("email", "Email"),
                _f("nickname", "Nickname"),
                _f("first_name", "First name"),
                _f("last_name", "Last name"),
                _f("url", "Website"),
                _f("description", "Biography", _M),
            ),
            _page(
                "role",
                "Role",
                _f(
                    "roles",
                    "Role",
                    _CH,
                    choices=_ROLES,
                    requirement="promote_users",
                    help="What this person may do on the site.",
                ),
            ),
        ),
    ),
    "plugin": SheetSpec(
        "plugin",
        "Plugin",
        (
            _page(
                "general",
                "General",
                _ro("name", "Name"),
                _ro("version", "Version"),
                _ro("author", "Author"),
                _ro("description", "Description", _M),
                _f(
                    "status",
                    "Status",
                    _CH,
                    choices=("active", "inactive"),
                    requirement="activate_plugins",
                ),
                _ro("requires_wp", "Needs WordPress"),
                _ro("plugin_uri", "Home page", _K),
            ),
        ),
    ),
    "theme": SheetSpec(
        "theme",
        "Theme",
        (
            _page(
                "general",
                "General",
                _ro("name", "Name"),
                _ro("version", "Version"),
                _ro("status", "Status"),
                _ro("author", "Author"),
                _ro("description", "Description", _M),
                _ro("template", "Parent theme"),
            ),
        ),
    ),
    "app_password": SheetSpec(
        "app_password",
        "Application Password",
        (
            _page(
                "general",
                "General",
                _ro("name", "Name"),
                _ro("created", "Made"),
                _ro("last_used", "Last used"),
                _ro("last_ip", "Last address"),
            ),
        ),
    ),
    "setting": SheetSpec(
        "setting",
        "Setting",
        (
            _page(
                "general",
                "General",
                _ro("label", "Setting"),
                _f("value", "Value", requirement="manage_options"),
            ),
        ),
    ),
}


SITE_SHEET = SheetSpec(
    "site",
    "Site",
    (
        _page(
            "general",
            "General",
            _ro("name", "Name"),
            _ro("description", "Tagline"),
            _ro("url", "Address", _K),
            _ro("wp_version", "WordPress version"),
        ),
        _page(
            "role",
            "Your Role",
            _ro("role", "Role"),
            _ro("capabilities", "What your role allows", _M),
        ),
        _page(
            "connection",
            "Connection",
            _ro("username", "Signs in as"),
            _ro("kind", "Kind of site"),
            _ro("access", "Workbench access"),
        ),
        _page("namespaces", "REST Namespaces", _ro("namespaces", "Namespaces", _M)),
        _page(
            "spam",
            "Spam",
            _ro("comment_moderation", "Comments wait for approval"),
            _ro("spam_plugins", "Spam plugins found"),
            _ro("form_plugins", "Form plugins found"),
            _ro("spam_note", "About spam here", _M),
        ),
    ),
)
"""The site's own sheet (Appendix A, Site; 13a.5's Spam page, read only)."""


def sheet_for(
    row: WbRow,
    *,
    taxonomies: Mapping[str, str] | None = None,
    meta: Mapping[str, Any] | None = None,
    schema: Mapping[str, Any] | None = None,
) -> SheetSpec:
    """The sheet for *row*. *taxonomies* maps an item's term fields to their labels."""
    if row.kind == "item":
        found = dict(taxonomies or {})
        if not found:
            found = {k: v for k, v in _CORE_TAXONOMY_FIELDS.items() if k in row.raw}
        return _item_sheet(row, found, meta or {})
    if row.kind in _STATIC:
        return _STATIC[row.kind]
    if schema:
        return schema_sheet(row.kind, row.kind.replace("_", " ").title(), schema)
    return _raw_sheet(row.kind, row.raw or dict(row.cells))


def sheet_title(row: WbRow) -> str:
    """ "Hello World Properties - Community Radio"."""
    return f"{row.title} Properties - {row.site}" if row.site else f"{row.title} Properties"


def _scalar(value: Any) -> Value:
    if isinstance(value, (bool, int, str)) or value is None:
        return value
    if isinstance(value, float):
        return str(value)
    if isinstance(value, dict) and "raw" in value:
        return raw_text(value)
    if isinstance(value, dict) and "rendered" in value:
        return rendered(value)
    if isinstance(value, list) and all(isinstance(v, (str, int)) for v in value):
        return tuple(str(v) for v in value)
    return json.dumps(value, ensure_ascii=False, indent=1)


def values_for(
    row: WbRow,
    raw: Mapping[str, Any] | None = None,
    *,
    term_names: Mapping[int, str] | None = None,
    author_names: Mapping[int, str] | None = None,
) -> dict[str, Value]:
    """What each field of *row*'s sheet shows, from the freshly loaded object *raw*."""
    data = dict(raw if raw is not None else row.raw)
    names = term_names or {}
    values: dict[str, Value] = {key: _scalar(value) for key, value in data.items()}
    if row.kind == "item":
        values["title"] = raw_text(data.get("title")) or rendered(data.get("title"))
        values["excerpt"] = raw_text(data.get("excerpt"))
        values["password"] = ""  # write only: never shown back
        author = int(data.get("author", 0) or 0)
        values["author"] = labelled((author_names or {}).get(author, ""), author) if author else ""
        values["modified"] = friendly_date(str(data.get("modified_gmt", "") or ""))
        values["date"] = str(data.get("date", "") or "")
        values["format"] = str(data.get("format", "") or "standard")
        for field_name, value in data.items():
            if isinstance(value, list) and all(isinstance(v, int) for v in value):
                values[field_name] = tuple(labelled(names.get(v, ""), v) for v in value)
        meta = data.get("meta")
        if isinstance(meta, dict):
            for key, value in meta.items():
                values[f"meta.{key}"] = _scalar(value)
    elif row.kind == "media":
        details = data.get("media_details") if isinstance(data.get("media_details"), dict) else {}
        details = details or {}
        size = int(details.get("filesize", 0) or 0)
        width, height = int(details.get("width", 0) or 0), int(details.get("height", 0) or 0)
        values["size"] = human_size(size) if size else ""
        values["dimensions"] = f"{width} by {height}" if width and height else ""
        values["date"] = friendly_date(str(data.get("date_gmt", "") or ""))
        values["caption"] = raw_text(data.get("caption"))
        values["description"] = raw_text(data.get("description"))
        sizes = details.get("sizes") if isinstance(details.get("sizes"), dict) else {}
        values["sizes"] = "\n".join(
            f"{name}: {s.get('width')} by {s.get('height')}"
            for name, s in (sizes or {}).items()
            if isinstance(s, dict)
        )
    elif row.kind == "comment":
        values["content"] = raw_text(data.get("content"))
        values["date"] = friendly_date(str(data.get("date_gmt", "") or ""))
        values["post_title"] = row.cell("on")
    elif row.kind == "user":
        roles = data.get("roles") or []
        values["roles"] = str(roles[0]) if roles else ""
    elif row.kind == "plugin":
        values["name"] = rendered(data.get("name")) or str(data.get("name", ""))
        values["author"] = rendered(data.get("author"))
        values["description"] = rendered(data.get("description"))
    elif row.kind == "theme":
        values["name"] = rendered(data.get("name"))
        values["author"] = rendered(data.get("author"))
        values["description"] = rendered(data.get("description"))
    elif row.kind == "app_password":
        values["created"] = friendly_date(str(data.get("created", "") or ""))
        last = str(data.get("last_used", "") or "")
        values["last_used"] = friendly_date(last) if last else "never"
    elif row.kind == "setting":
        values["label"] = row.cell("setting")
        values["value"] = _scalar(data.get("value"))
    elif row.kind == "term":
        values["description"] = str(data.get("description", "") or "")
    return values
