"""The site's own writing types (an Event, a Product), apart from posts and pages (WP-R-032).

Split from :mod:`quill.core.wordpress.site` for size. ``wp/v2/types`` says, for
every post type the site shows in REST, its route, its names and the
taxonomies it uses; from that QUILL lists a type's items by status (the
plugins' statuses included), counts them, and makes a new one with its terms,
for any type, with no QUILL release for each plugin.

A type's *kind* is its REST base (``tribe_events``), which is what
:func:`~quill.core.wordpress.site.kind_route` expects; a type served outside
``wp/v2`` has its whole route as its kind (``library/v1/books``).

Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site_taxonomies as taxonomies
from quill.core.wordpress.api import WordPressApi, WordPressApiError

if TYPE_CHECKING:
    from quill.core.wordpress.site import Item, ItemSummary

__all__ = [
    "WritingType",
    "count_by_status",
    "discover_writing_types",
    "list_by_status",
    "new_item",
    "statuses_for",
    "type_taxonomies",
    "writing_types",
]

#: Types WordPress lists that are not pages or posts a person writes.
_NOT_WRITING_TYPES = frozenset({
    "attachment",
    "nav_menu_item",
    "wp_block",
    "wp_template",
    "wp_template_part",
    "wp_navigation",
    "wp_global_styles",
    "wp_font_family",
    "wp_font_face",
})


@dataclass(frozen=True)
class WritingType:
    """One of the site's own writing types, as ``wp/v2/types`` describes it."""

    slug: str
    rest_base: str
    name: str
    singular: str = ""
    rest_namespace: str = "wp/v2"
    hierarchical: bool = False
    #: The taxonomies (their slugs) this type uses.
    taxonomies: tuple[str, ...] = ()

    @property
    def kind(self) -> str:
        """What the rest of QUILL calls this type: its REST base, or its route outside wp/v2."""
        if self.rest_namespace in ("", "wp/v2"):
            return self.rest_base
        return f"{self.rest_namespace}/{self.rest_base}"


def discover_writing_types(api: WordPressApi) -> list[WritingType]:
    """Every writing type the site shows in REST, apart from posts and pages, in its order."""
    raw = api.get("wp/v2/types", context="edit")
    found: list[WritingType] = []
    if not isinstance(raw, dict):
        return found
    for slug, info in raw.items():
        if slug in {"post", "page"} or slug in _NOT_WRITING_TYPES or not isinstance(info, dict):
            continue
        base = str(info.get("rest_base") or "").strip("/")
        if not base or not info.get("viewable", True):
            continue
        labels = info.get("labels")
        singular = labels.get("singular_name") if isinstance(labels, dict) else ""
        names = info.get("taxonomies")
        found.append(
            WritingType(
                slug=str(slug),
                rest_base=base,
                name=str(info.get("name") or base.title()),
                singular=str(singular or info.get("name") or base.title()),
                rest_namespace=str(info.get("rest_namespace") or "wp/v2").strip("/"),
                hierarchical=bool(info.get("hierarchical", False)),
                taxonomies=tuple(str(n) for n in names) if isinstance(names, list) else (),
            )
        )
    return found


def writing_types(api: WordPressApi) -> list[tuple[str, str, str]]:
    """``(post type, kind, plural name)`` for the site's own writing types."""
    return [(t.slug, t.kind, t.name) for t in discover_writing_types(api)]


def type_taxonomies(api: WordPressApi, wtype: WritingType) -> list[taxonomies.TaxonomyInfo]:
    """The taxonomies *wtype* uses, with their routes, in the order the type names them.

    A taxonomy that names the type but that the type does not name (or the other
    way round) still counts: sites register them from either side.
    """
    known = taxonomies.discover_taxonomies(api)
    order = list(wtype.taxonomies)
    order += [slug for slug, t in known.items() if wtype.slug in t.types and slug not in order]
    return [known[slug] for slug in order if slug in known]


def statuses_for(api: WordPressApi) -> list[tuple[str, str]]:
    """``(status, label)`` to offer: the core six first, then every status the site adds.

    A site that will not list its statuses still gets the core six.
    """
    from quill.core.wordpress.site import STATUSES

    offered = list(STATUSES)
    try:
        found = taxonomies.discover_statuses(api)
    except WordPressApiError:
        return offered
    have = {slug for slug, _label in offered}
    offered += [(s.slug, s.name) for s in found.values() if s.slug not in have]
    return offered


def list_by_status(
    api: WordPressApi, kind: str, status: str, *, search: str = ""
) -> Iterator[ItemSummary]:
    """The items of *kind* in one *status*, newest change first."""
    from quill.core.wordpress.site import list_items

    return list_items(api, kind, statuses=[status], search=search)


def count_by_status(api: WordPressApi, kind: str, statuses: Iterable[str]) -> dict[str, int]:
    """How many items of *kind* each status holds, from one small request per status.

    A status the site will not list for this type (or this account) is left
    out rather than counted as none.
    """
    from quill.core.wordpress.site import kind_route

    counts: dict[str, int] = {}
    for status in statuses:
        try:
            response = api.request(
                "GET",
                kind_route(kind),
                params={"context": "edit", "status": status, "per_page": 1, "_fields": "id"},
            )
        except WordPressApiError:
            continue
        total = response.total
        if total is None:
            total = len(response.payload) if isinstance(response.payload, list) else 0
        counts[status] = total
    return counts


def new_item(
    api: WordPressApi,
    wtype: WritingType,
    title: str,
    *,
    content: str = "",
    status: str = "draft",
    terms: Mapping[str, Sequence[int]] | None = None,
) -> Item:
    """Make a new item of *wtype* on the site, with its terms by taxonomy slug."""
    from quill.core.wordpress.site import Item, item_from_payload, kind_route, taxonomy_field

    body: dict[str, Any] = Item(0, wtype.kind, title, content, status).to_body()
    for taxonomy, ids in (terms or {}).items():
        body[taxonomy_field(taxonomy, api)] = [int(i) for i in ids]
    raw = api.post(kind_route(wtype.kind), body, context="edit")
    return item_from_payload(raw, wtype.kind)
