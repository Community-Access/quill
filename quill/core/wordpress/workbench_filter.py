"""The WordPress Workbench's filter: the shared query string, sent as REST parameters (PRD 10).

The filter box, the Filter Builder, Show Only and Hide all write one query
string in the shared engine's ``key:value`` syntax
(:mod:`quill.core.workbench.filters`). Here that query becomes the site's own
query arguments through :func:`quill.core.wordpress.query.build`, so a filter
reaches the whole site rather than the rows already loaded (WP-R-009):

- ``status:draft``, ``author:3``, ``-author:3``, ``category:news``,
  ``-tag:12``, ``sticky:yes``, ``after:2026-01-01``, ``modified:>2026-10-01``,
  ``parent:0``, ``format:audio``, ``type:image``, and every other argument the
  route takes, by its own name (``tax_relation:OR``, ``search_columns:post_title``);
- plain words are the route's ``search`` argument.

A list the API cannot filter (plugins, themes, settings) is filtered here, on
the rows already loaded, and :func:`describe_scope` says so honestly
("Filtered on this computer, 12 rows loaded").

Terms may be given by slug or name; :func:`resolve_terms` asks the
taxonomy's route for their ids. Wx-free; :func:`resolve_terms` is the only
call that reaches the network.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from quill.core.wordpress import query as wq
from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.filters import Condition, Operator, Query

__all__ = [
    "ALIASES",
    "FILTER_HELP",
    "describe_scope",
    "local_matches",
    "params_for",
    "resolve_terms",
]

FILTER_HELP = (
    "Type words to search the whole site, or qualifiers such as status:draft, "
    "category:news, -tag:old, author:3, after:2026-01-01 or modified:>2026-10-01. "
    "Enter runs it, Escape clears it, and Ctrl+Shift+F opens the Filter Builder."
)

ALIASES: dict[str, str] = {
    "category": "categories",
    "tag": "tags",
    "published": "after",
    "modified": "modified_after",
    "changed": "modified_after",
    "type": "media_type",
    "mime": "mime_type",
    "role": "roles",
    "words": "search",
}
"""Shorter names a person types, and the REST argument each means."""

_TRUE = {"yes", "true", "1", "on"}


def _attribute(condition: Condition) -> str:
    name = ALIASES.get(condition.attribute, condition.attribute)
    if condition.operator is Operator.BEFORE and name == "after":
        return "before"
    if condition.operator is Operator.BEFORE and name == "modified_after":
        return "modified_before"
    return name


Resolver = Callable[[str, list[str]], list[str]]
"""Turns a terms attribute's slugs or names into ids (as text), asking the site."""


def _translate(condition: Condition, attr: wq.Attribute, resolve: Resolver | None) -> wq.Condition:
    op, value = condition.operator, condition.value
    values = [v.strip() for v in value.split(",") if v.strip()]
    negated = op is Operator.IS_NOT
    if attr.kind in ("terms", "ids"):
        if attr.kind == "terms" and resolve is not None and not all(v.isdigit() for v in values):
            values = resolve(attr.name, values)
        return wq.Condition(attr.name, "is none of" if negated else "is any of", values)
    if attr.kind == "date":
        return wq.Condition(attr.name, "before" if op is Operator.BEFORE else "after", value)
    if attr.kind == "boolean":
        return wq.Condition(attr.name, "is not" if negated else "is", value.lower() in _TRUE)
    if attr.kind in ("choices", "slugs"):
        return wq.Condition(attr.name, "is any of", values)
    if attr.kind == "text":
        return wq.Condition(attr.name, "contains", value)
    return wq.Condition(attr.name, "is", value)


def params_for(
    query: Query,
    *,
    attributes: Mapping[str, wq.Attribute] | None = None,
    words_remote: bool = True,
    resolve: Resolver | None = None,
    taxonomy_bases: Sequence[str] = (),
) -> dict[str, object]:
    """The REST parameters for *query*. Raises :class:`~quill.core.wordpress.query.QueryError`.

    *attributes* is the route's own table when known (so a plugin's taxonomy
    is accepted); the shared table otherwise.
    """
    table = dict(wq.ATTRIBUTES if attributes is None else attributes)
    rows: list[wq.Condition] = []
    relation = "all"
    for condition in query.conditions:
        name = _attribute(condition)
        if name == "tax_relation":
            relation = "any" if condition.value.upper() == "OR" else "all"
            continue
        attr = table.get(name) or wq.attribute_for(name, None, tuple(taxonomy_bases))
        if attr is None:
            raise wq.QueryError(f"This list cannot be filtered by {condition.attribute}.")
        table.setdefault(attr.name, attr)
        rows.append(_translate(condition, attr, resolve))
    params = wq.build(rows, attributes=table, taxonomies_match=relation)
    if words_remote and query.words:
        params["search"] = " ".join(query.words)
    return params


def resolve_terms(api: WordPressApi) -> Resolver:
    """A resolver that finds terms by slug, then by name, on *api*'s site."""

    def resolve(base: str, values: list[str]) -> list[str]:
        known = tx.cached_taxonomies(api) or {}
        route = next((t.route for t in known.values() if t.rest_base == base), f"wp/v2/{base}")
        ids: list[str] = []
        for text in values:
            if text.isdigit():
                ids.append(text)
                continue
            try:
                found = api.get(route, slug=text, _fields="id") or api.get(
                    route, search=text, _fields="id"
                )
            except WordPressApiError:
                found = []
            if not isinstance(found, list) or not found or not isinstance(found[0], dict):
                raise wq.QueryError(f"There is no {base} called {text} on this site.")
            ids.append(str(found[0].get("id", 0)))
        return ids

    return resolve


def local_matches(row: WbRow, conditions: Sequence[Condition]) -> bool:
    """Whether a loaded row passes *conditions*, matched against its cells and raw fields."""
    for condition in conditions:
        name = ALIASES.get(condition.attribute, condition.attribute)
        have = row.cells.get(condition.attribute) or row.cells.get(name)
        if have is None:
            value = row.raw.get(name, row.raw.get(condition.attribute))
            have = "" if value is None else str(value)
        hit = condition.value.casefold() in have.casefold()
        if condition.operator is Operator.IS_NOT:
            hit = not hit
        if not hit:
            return False
    return True


def describe_scope(remote: bool, loaded: int) -> str:
    """What the filter reached, for the status bar: the site, or the rows here."""
    if remote:
        return "Filtered on the site"
    return f"Filtered on this computer, {loaded} rows loaded"
