"""The one query: every collection argument a WordPress route takes, as a filter (WP-R-030).

The REST API's own query arguments are the filter language here, so a filter
reaches the whole site rather than the loaded rows (wordpress PRD 10). This
module is the attribute table the Filter Builder reads and the builder that
turns conditions into request parameters:

- **The table** (:data:`ATTRIBUTES`) names every ``wp/v2`` collection
  argument the test site's index lists: its spoken label, its kind (text,
  ids, a date, true or false, one or several of a list), the operators that
  kind offers, its exclude partner (``categories`` and
  ``categories_exclude`` are one attribute with "any of" and "none of"), and
  the values core defines.
- **Taxonomies** are attributes by rule rather than by row: any argument
  that is a taxonomy's ``rest_base`` (``product_cat``, ``tribe_events_cat``)
  or that plus ``_exclude`` is a terms attribute, so a plugin's taxonomy is
  filterable with no release (:func:`attribute_for`).
- **A route's own enums** add to the table's values (:func:`attributes_for_route`):
  a site's plugin statuses (``wc-processing``) and orderings (``price``) are
  offered because the route says so.
- **Anything else with a type** becomes a schema-built attribute with the
  operator its type implies; it works, and the combination test lists it
  until it gets a label of its own.

:func:`build` turns :class:`Condition` rows into the parameters, including
the ones nothing in QUILL sent before: ``tax_relation``, the ``_exclude``
pairs, ``modified_after`` and ``modified_before``, ``search_columns``,
``search_semantics``, ``ignore_sticky``, and terms "all of" through the
taxonomy object's ``operator``.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "ATTRIBUTES",
    "OPERATORS",
    "PAGING",
    "SITE_LABELLED",
    "VALUE_LABELS",
    "Attribute",
    "Condition",
    "QueryError",
    "attribute_for",
    "attributes_for_route",
    "build",
    "classify_arg",
    "enum_values",
    "kind_for_schema",
    "value_label",
]

#: The operators each kind of attribute offers, in the order the builder lists them.
OPERATORS: Mapping[str, tuple[str, ...]] = {
    "text": ("contains",),
    "exact": ("is",),
    "number": ("is",),
    "id": ("is",),
    "ids": ("is any of", "is none of"),
    "slugs": ("is any of",),
    "date": ("before", "after", "between", "in the last days"),
    "boolean": ("is", "is not"),
    "choice": ("is",),
    "choices": ("is any of",),
    "terms": ("is any of", "is all of", "is none of"),
}

#: Arguments that page or shape the answer rather than filter it.
PAGING = frozenset({
    "context",
    "page",
    "per_page",
    "offset",
    "_fields",
    "_embed",
    "_envelope",
    "_jsonp",
    "_method",
})


@dataclass(frozen=True)
class Attribute:
    """One filter: a REST argument, how it is spoken, and how it is asked."""

    name: str
    label: str
    kind: str
    help: str = ""
    #: The argument that carries "is none of" (``author_exclude`` for ``author``).
    exclude: str = ""
    #: For ``choice`` and ``choices``: the values offered.
    values: tuple[str, ...] = ()
    #: True when the attribute was built from a schema, not from this table.
    schema_built: bool = False

    @property
    def operators(self) -> tuple[str, ...]:
        return OPERATORS.get(self.kind, ("is",))


def _a(name: str, label: str, kind: str, help_text: str, **more: Any) -> Attribute:
    return Attribute(name, label, kind, help_text, **more)


_CORE_STATUSES = ("publish", "future", "draft", "pending", "private", "trash", "any")
_ORDERBY = (
    "author", "date", "id", "include", "modified", "parent", "relevance", "slug",
    "include_slugs", "title", "menu_order", "name", "count", "term_group", "description",
    "email", "url", "registered_date", "post", "type", "date_gmt",
)  # fmt: skip

#: Every wp/v2 collection argument the test site lists, by name (Appendix D).
ATTRIBUTES: Mapping[str, Attribute] = {
    a.name: a
    for a in (
        _a("search", "Words", "text", "Items whose text holds these words."),
        _a(
            "search_columns",
            "Search in",
            "choices",
            "Where the words are looked for: the title, the content, the excerpt, or a name.",
            values=("post_title", "post_content", "post_excerpt"),
        ),
        _a(
            "search_semantics",
            "Match the words",
            "choice",
            "Exact matches the whole phrase only, rather than each word.",
            values=("exact",),
        ),
        _a("after", "Published", "date", "When it was published."),
        _a("before", "Published before", "date", "Published before this date."),
        _a("modified_after", "Changed", "date", "When it last changed."),
        _a("modified_before", "Changed before", "date", "Last changed before this date."),
        _a("author", "Author", "ids", "Who wrote it.", exclude="author_exclude"),
        _a("author_email", "Author's email", "exact", "The commenter's email address."),
        _a("include", "Only these", "ids", "Only the items with these ids.", exclude="exclude"),
        _a("slug", "Slug", "slugs", "The items with these slugs, the last part of the address."),
        _a(
            "status",
            "Status",
            "choices",
            "Published, draft, scheduled and the rest, the site's own statuses included.",
            values=_CORE_STATUSES,
        ),
        _a("sticky", "Sticky", "boolean", "Posts kept at the top of the blog."),
        _a(
            "ignore_sticky",
            "Leave sticky posts in date order",
            "boolean",
            "Sticky posts take their place by date instead of coming first.",
        ),
        _a(
            "tax_relation",
            "Match the categories, tags and other terms",
            "choice",
            "AND means every term row must match; OR means any one is enough.",
            values=("AND", "OR"),
        ),
        _a("categories", "Category", "terms", "Its categories.", exclude="categories_exclude"),
        _a("tags", "Tag", "terms", "Its tags.", exclude="tags_exclude"),
        _a(
            "format",
            "Format",
            "choices",
            "The post format a theme shows it in.",
            values=(
                "standard",
                "aside",
                "chat",
                "gallery",
                "link",
                "image",
                "quote",
                "status",
                "video",
                "audio",
            ),
        ),  # fmt: skip
        _a("order", "Order", "choice", "Oldest or newest first.", values=("asc", "desc")),
        _a("orderby", "Sort by", "choice", "What the list is sorted by.", values=_ORDERBY),
        _a("parent", "Parent", "ids", "Items under this parent.", exclude="parent_exclude"),
        _a("post", "On the post", "ids", "Comments or media on this post."),
        _a("hide_empty", "Hide unused terms", "boolean", "Leave out terms no item uses."),
        _a("menu_order", "Menu order", "number", "Its position among its siblings."),
        _a(
            "media_type",
            "Media type",
            "choices",
            "Pictures, audio, video, documents or other files.",
            values=("image", "video", "text", "application", "audio"),
        ),
        _a("mime_type", "File type", "exact", "A file type such as image/png."),
        _a("roles", "Role", "choices", "People with these roles."),
        _a("capabilities", "Can", "choices", "People who have these capabilities."),
        _a("who", "Authors only", "choice", "Only people who can write.", values=("authors",)),
        _a(
            "has_published_posts",
            "Has published",
            "choices",
            "People who have published items of these types.",
        ),
        _a("type", "Kind", "choice", "What kind of result: an item, a term or a format."),
        _a("subtype", "Type", "choices", "Which post types or taxonomies to look in."),
        _a("password", "Post password", "exact", "The password of a protected post."),
        _a("term", "Search for", "text", "Words to find a block plugin by."),
        _a("collection", "Collection", "exact", "A font collection's slug."),
        _a("category", "Pattern category", "id", "A pattern directory category."),
        _a("keyword", "Keyword", "id", "A pattern directory keyword."),
        _a("font_family_id", "Font family", "id", "The font family a face belongs to."),
        _a("brand", "Brand", "exact", "A product brand's slug."),
        _a("menus", "Menu", "terms", "The menu items belong to.", exclude="menus_exclude"),
    )
}

#: Arguments whose values the site names itself at run time: statuses from
#: ``wp/v2/statuses``, post types and taxonomies from ``wp/v2/types`` and
#: ``wp/v2/taxonomies``. No spoken label is kept for them here.
SITE_LABELLED = frozenset({"status", "subtype", "has_published_posts"})

#: The spoken words for each value an argument offers, where WordPress's own
#: word is not one a person would say.
VALUE_LABELS: Mapping[str, Mapping[str, str]] = {
    "order": {"asc": "Oldest or A first", "desc": "Newest or Z first"},
    "orderby": {
        "author": "Author",
        "date": "Date published",
        "date_gmt": "Date published",
        "id": "Id",
        "include": "The order asked for",
        "include_slugs": "The order of the slugs asked for",
        "modified": "Date changed",
        "parent": "Parent",
        "relevance": "Best match for the words",
        "slug": "Slug",
        "title": "Title",
        "menu_order": "Menu order",
        "name": "Name",
        "count": "How many items use it",
        "term_group": "Term group",
        "description": "Description",
        "email": "Email address",
        "url": "Web address",
        "registered_date": "Date registered",
        "post": "Post",
        "type": "Type",
    },
    "search_columns": {
        "post_title": "Title",
        "post_content": "Content",
        "post_excerpt": "Excerpt",
        "email": "Email address",
        "name": "Name",
        "id": "Id",
        "username": "Username",
        "slug": "Slug",
    },
    "search_semantics": {"exact": "The exact phrase"},
    "tax_relation": {"AND": "All of these", "OR": "Any of these"},
    "format": {
        "standard": "Standard",
        "aside": "Aside",
        "chat": "Chat",
        "gallery": "Gallery",
        "link": "Link",
        "image": "Image",
        "quote": "Quote",
        "status": "Status",
        "video": "Video",
        "audio": "Audio",
    },
    "media_type": {
        "image": "Pictures",
        "video": "Video",
        "audio": "Audio",
        "text": "Text files",
        "application": "Documents and other files",
    },
    "type": {"post": "Items", "term": "Terms", "post-format": "Formats"},
    "who": {"authors": "Authors"},
    "context": {"view": "As visitors see it", "embed": "Embedded", "edit": "For editing"},
}


def value_label(argument: str, value: str) -> str:
    """The spoken word for one value of *argument*; the value itself when none is kept."""
    return VALUE_LABELS.get(argument, {}).get(value, value)


#: The ``_exclude`` arguments, each the "is none of" half of an attribute above.
_EXCLUDE_OF: Mapping[str, str] = {a.exclude: a.name for a in ATTRIBUTES.values() if a.exclude}


class QueryError(CodedError):
    """A condition the builder cannot turn into a request, said as a sentence."""

    code = "QUILL-WP-QUERY-UNUSABLE"


@dataclass(frozen=True)
class Condition:
    """One row of a filter: an attribute, an operator, and the value(s)."""

    attribute: str
    operator: str
    value: Any = None
    #: For a hierarchical taxonomy: count items in child terms too.
    include_children: bool = False


def kind_for_schema(schema: Mapping[str, Any]) -> str:
    """The attribute kind a schema implies, or ``""`` when it has no usable type."""
    kind = schema.get("type")
    kinds = set(kind) if isinstance(kind, list) else {kind}
    items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
    item_type = items.get("type") if items else None
    has_enum = bool(schema.get("enum") or (items or {}).get("enum"))
    if "object" in kinds and "array" in kinds:
        return "terms"
    if "array" in kinds:
        if has_enum or item_type == "string":
            return "choices" if has_enum else "slugs"
        return "ids"
    if "boolean" in kinds:
        return "boolean"
    if "integer" in kinds or "number" in kinds:
        return "number"
    if "string" in kinds:
        if schema.get("format") == "date-time":
            return "date"
        return "choice" if has_enum else "text"
    return ""


def enum_values(schema: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not schema:
        return ()
    found = schema.get("enum")
    items = schema.get("items")
    if not found and isinstance(items, dict):
        found = items.get("enum")
    return tuple(str(v) for v in found) if isinstance(found, list) else ()


def _merge_values(known: Sequence[str], more: Iterable[str]) -> tuple[str, ...]:
    out = list(known)
    out += [v for v in more if v not in out]
    return tuple(out)


def attribute_for(
    name: str,
    schema: Mapping[str, Any] | None = None,
    taxonomy_bases: Iterable[str] = (),
) -> Attribute | None:
    """The attribute for one argument, by table, by taxonomy, or by schema; ``None`` if none.

    An ``_exclude`` argument answers with the attribute it belongs to.
    """
    bases = set(taxonomy_bases)
    base_name = _EXCLUDE_OF.get(name, name)
    if name.endswith("_exclude") and base_name == name and name.removesuffix("_exclude") in bases:
        base_name = name.removesuffix("_exclude")
    found = ATTRIBUTES.get(base_name)
    if found is None and base_name in bases:
        words = base_name.replace("_", " ").replace("-", " ")
        found = Attribute(
            base_name,
            words[:1].upper() + words[1:],
            "terms",
            "Its terms in this taxonomy.",
            exclude=f"{base_name}_exclude",
        )
    if found is None and schema is not None and name not in PAGING:
        kind = kind_for_schema(schema)
        if kind:
            words = name.replace("_", " ")
            found = Attribute(name, words[:1].upper() + words[1:], kind, "", schema_built=True)
    if found is None:
        return None
    values = _merge_values(found.values, enum_values(schema)) if base_name == name else found.values
    return replace(found, values=values) if values != found.values else found


def classify_arg(
    name: str, schema: Mapping[str, Any] | None, taxonomy_bases: Iterable[str] = ()
) -> str:
    """``paging``, ``known``, ``taxonomy``, ``schema_built`` or ``missing`` for one argument."""
    if name in PAGING:
        return "paging"
    found = attribute_for(name, schema, taxonomy_bases)
    if found is None:
        return "missing"
    if found.schema_built:
        return "schema_built"
    if found.name in ATTRIBUTES:
        return "known"
    return "taxonomy"


def attributes_for_route(
    args: Mapping[str, Mapping[str, Any]], taxonomy_bases: Iterable[str] = ()
) -> dict[str, Attribute]:
    """Every filter one route offers, its enums merged in; exclude halves fold into their pair."""
    bases = tuple(taxonomy_bases)
    out: dict[str, Attribute] = {}
    for name, schema in args.items():
        if name in PAGING:
            continue
        found = attribute_for(name, schema, bases)
        if found is None:
            continue
        have = out.get(found.name)
        if have is not None:
            found = replace(have, values=_merge_values(have.values, found.values))
        out[found.name] = found
    return out


# --------------------------------------------------------------------------- #
# Conditions into parameters


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        stamp = value if value.tzinfo else value.replace(tzinfo=UTC)
        return stamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    text = str(value or "").strip()
    if not text:
        raise QueryError("A date filter needs a date.")
    return text


def _ids(value: Any, label: str) -> list[int]:
    items = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
    try:
        return [int(v) for v in items if str(v).strip()]
    except (TypeError, ValueError) as exc:
        raise QueryError(f"{label} needs ids, which are numbers.") from exc


def _strings(value: Any) -> list[str]:
    items = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
    return [str(v).strip() for v in items if str(v).strip()]


@dataclass
class _Params:
    out: dict[str, object] = field(default_factory=dict)
    taxonomies: set[str] = field(default_factory=set)


def _check_values(attr: Attribute, values: Sequence[str]) -> None:
    if not attr.values:
        return
    wrong = [v for v in values if v not in attr.values]
    if wrong:
        raise QueryError(f"{attr.label} cannot be {wrong[0]} here.")


def _apply(attr: Attribute, cond: Condition, params: _Params, now: datetime) -> None:
    op, name, out = cond.operator, attr.name, params.out
    if op not in attr.operators:
        raise QueryError(f"{attr.label} cannot be filtered with '{op}'.")
    if attr.kind == "date":
        # The table names the "after" argument; its "before" partner is its pair.
        before = {"after": "before", "modified_after": "modified_before"}.get(name, name)
        after = {"before": "after", "modified_before": "modified_after"}.get(name, name)
        if op == "before":
            out[before] = _iso(cond.value)
        elif op == "after":
            out[after] = _iso(cond.value)
        elif op == "between":
            start, end = cond.value
            out[after], out[before] = _iso(start), _iso(end)
        else:
            out[after] = _iso(now - timedelta(days=int(cond.value)))
        return
    if attr.kind == "terms":
        ids = _ids(cond.value, attr.label)
        params.taxonomies.add(name)
        if op == "is none of":
            out[attr.exclude or f"{name}_exclude"] = ids
        elif op == "is all of" or cond.include_children:
            out[f"{name}[terms]"] = ids
            out[f"{name}[operator]"] = "AND" if op == "is all of" else "OR"
            if cond.include_children:
                out[f"{name}[include_children]"] = True
        else:
            out[name] = ids
        return
    if attr.kind == "ids":
        ids = _ids(cond.value, attr.label)
        if op == "is none of":
            if not attr.exclude:
                raise QueryError(f"{attr.label} cannot be filtered with 'is none of'.")
            out[attr.exclude] = ids
        else:
            out[name] = ids
        return
    if attr.kind == "boolean":
        wanted = bool(cond.value)
        out[name] = wanted if op == "is" else not wanted
        return
    if attr.kind in ("choices", "slugs"):
        values = _strings(cond.value)
        _check_values(attr, values)
        out[name] = values
        return
    if attr.kind == "choice":
        (value,) = _strings(cond.value) or [""]
        _check_values(attr, [value])
        out[name] = value
        return
    if attr.kind in ("number", "id"):
        out[name] = _ids(cond.value, attr.label)[0]
        return
    text = str(cond.value or "").strip()
    if text:
        out[name] = text


def build(
    conditions: Iterable[Condition],
    *,
    attributes: Mapping[str, Attribute] | None = None,
    taxonomies_match: str = "all",
    now: datetime | None = None,
) -> dict[str, object]:
    """The request parameters for *conditions*, ready for ``api.iter_collection``.

    *attributes* is the route's own table (:func:`attributes_for_route`), so a
    plugin's taxonomy or status is accepted; it defaults to :data:`ATTRIBUTES`.
    *taxonomies_match* is ``all`` or ``any``, sent as ``tax_relation`` when two
    or more taxonomies are filtered. Raises :class:`QueryError` with a sentence
    for a condition the route cannot take.
    """
    table = dict(ATTRIBUTES if attributes is None else attributes)
    params = _Params()
    moment = now or datetime.now(UTC)
    for cond in conditions:
        attr = table.get(cond.attribute) or table.get(_EXCLUDE_OF.get(cond.attribute, ""))
        if attr is None:
            raise QueryError(f"This list cannot be filtered by {cond.attribute}.")
        if cond.attribute != attr.name and cond.operator == "is any of":
            # A row naming the exclude argument itself means "none of".
            cond = replace(cond, operator="is none of")
        _apply(attr, cond, params, moment)
    if len(params.taxonomies) > 1 and "tax_relation" not in params.out:
        if taxonomies_match not in ("all", "any"):
            raise QueryError("Terms must match all of the rows or any one of them.")
        params.out["tax_relation"] = "AND" if taxonomies_match == "all" else "OR"
    return params.out
