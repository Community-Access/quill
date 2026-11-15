"""Yoast SEO's social fields and its bulk editor, from the Workbench.

Yoast SEO 28 has a bulk editor with REST routes of its own (read from
Yoast's source, ``src/bulk-editor/user-interface``, and the test site's
index), and they are how the Workbench writes an item's SEO when the site
does not register Yoast's post meta for the REST API (the usual case):

- ``yoast/v1/bulk_editor/posts`` (GET; ``content_type``, ``include``,
  ``search``, ``per_page`` up to 100) answers ``{"posts": [...]}``, each with
  ``id``, ``title``, ``seo_title``, ``meta_description``, ``social_title``,
  ``social_description``, ``focus_keyphrase`` and ``editable``;
- ``bulk_editor/update_search`` takes ``{"items": [{"id", "seo_title",
  "meta_description", "focus_keyphrase"}]}`` and ``update_social`` takes
  ``{"items": [{"id", "social_title", "social_description"}]}``; an empty
  string clears a field, a key left out is left alone; each answers
  ``{"results": [{"id", "success", "error"?}]}``.

Both need ``wpseo_manage_options`` (an administrator, or Yoast's SEO
Manager). The social **image** has no bulk route: it is written only where
the site registers ``_yoast_wpseo_opengraph-image`` for REST, else named and
left for the item's Yoast panel. Every save here is read again first (the
conflict check), read again after (verify), and keeps the old values for
Ctrl+Z. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import length_note
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_edit import EditConflict

__all__ = [
    "BULK_POSTS",
    "SEARCH_FIELDS",
    "SOCIAL_FIELDS",
    "SOCIAL_META",
    "bulk_details",
    "bulk_fields_from_meta",
    "bulk_line",
    "change_lines",
    "has_bulk_editor",
    "meta_social",
    "put_back",
    "read_bulk",
    "save_bulk",
    "split_changes",
]

BULK_POSTS = "yoast/v1/bulk_editor/posts"
UPDATE_SEARCH = "yoast/v1/bulk_editor/update_search"
UPDATE_SOCIAL = "yoast/v1/bulk_editor/update_social"

SEARCH_FIELDS: dict[str, str] = {
    "seo_title": "SEO title",
    "meta_description": "Meta description",
    "focus_keyphrase": "Focus keyphrase",
}
SOCIAL_FIELDS: dict[str, str] = {
    "social_title": "Social title",
    "social_description": "Social description",
}

#: The social post meta Yoast can register for REST, with how each is named.
SOCIAL_META: dict[str, str] = {
    "_yoast_wpseo_opengraph-title": "Social title",
    "_yoast_wpseo_opengraph-description": "Social description",
    "_yoast_wpseo_opengraph-image": "Social image",
}

_FIELD_FOR_META = {
    "_yoast_wpseo_title": "seo_title",
    "_yoast_wpseo_metadesc": "meta_description",
    "_yoast_wpseo_focuskw": "focus_keyphrase",
    "_yoast_wpseo_opengraph-title": "social_title",
    "_yoast_wpseo_opengraph-description": "social_description",
}


def has_bulk_editor(ctx: Any) -> bool:
    """Whether the site's index lists the bulk editor's update route (unknown counts as yes)."""
    routes = tuple(getattr(getattr(ctx, "info", None), "routes", ()) or ())
    return not routes or f"/{UPDATE_SEARCH}" in routes


def _refused(exc: WordPressApiError, site: str) -> WordPressApiError:
    if exc.status in (401, 403):
        return WordPressApiError(
            f"Yoast SEO's bulk editor on {site} needs Yoast's manage-options right "
            "(an administrator or Yoast's SEO Manager), and your role does not have it.",
            status=exc.status,
        )
    return exc


def read_bulk(
    api: Any, site: str, content_type: str, *, ids: Sequence[int] = (), search: str = ""
) -> list[dict[str, Any]]:
    """Yoast's own view of *content_type*'s posts (at most 100), or those in *ids*."""
    params: dict[str, Any] = {"content_type": content_type, "per_page": 100}
    if ids:
        params["include"] = list(ids)
    if search:
        params["search"] = search
    try:
        answer = api.get(BULK_POSTS, **params)
    except WordPressApiError as exc:
        raise _refused(exc, site) from exc
    posts = answer.get("posts", []) if isinstance(answer, Mapping) else answer
    return [p for p in posts or [] if isinstance(p, dict)]


def bulk_line(post: Mapping[str, Any]) -> str:
    """One row of the Bulk SEO Editor: the title and how its SEO title and description stand."""
    title = rendered(post.get("title")) or "Untitled"
    seo = str(post.get("seo_title", "") or "")
    desc = str(post.get("meta_description", "") or "")
    locked = "" if post.get("editable", True) else ", locked: your role cannot edit it"
    said_seo = f"SEO title {len(seo)} characters" if seo else "no SEO title"
    said_desc = f"description {len(desc)} characters" if desc else "no description"
    return f"{title}: {said_seo}, {said_desc}{locked}"


def bulk_details(post: Mapping[str, Any]) -> str:
    seo = str(post.get("seo_title", "") or "")
    desc = str(post.get("meta_description", "") or "")
    fallback = str(post.get("seo_title_fallback") or "its template")
    return "\n".join([
        f"SEO title: {seo or 'not set, Yoast uses ' + fallback}",
        length_note("SEO title", seo, 60),
        f"Meta description: {desc or 'not set'}",
        length_note("Meta description", desc, 160),
        f"Social title: {post.get('social_title') or 'not set'}",
        f"Social description: {post.get('social_description') or 'not set'}",
        f"Focus keyphrase: {post.get('focus_keyphrase') or 'not set'}",
    ])


def split_changes(
    old: Mapping[str, Any], wanted: Mapping[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
    """The changed search fields and the changed social fields."""
    changed = {
        k: v.strip()
        for k, v in wanted.items()
        if k in SEARCH_FIELDS | SOCIAL_FIELDS and v.strip() != str(old.get(k, "") or "").strip()
    }
    search = {k: v for k, v in changed.items() if k in SEARCH_FIELDS}
    social = {k: v for k, v in changed.items() if k in SOCIAL_FIELDS}
    return search, social


def change_lines(title: str, old: Mapping[str, Any], changes: Mapping[str, str]) -> list[str]:
    names = SEARCH_FIELDS | SOCIAL_FIELDS
    lines = [f"Yoast SEO for {title}:"]
    for key, value in changes.items():
        lines.append(f"{names[key]}: {old.get(key) or 'not set'} becomes {value or 'not set'}.")
        if key == "seo_title":
            lines.append(length_note("The new SEO title", value, 60) + ".")
        if key == "meta_description":
            lines.append(length_note("The new description", value, 160) + ".")
    return lines


def _post(api: Any, route: str, post_id: int, fields: Mapping[str, str], site: str) -> str:
    """One item to one update route; "" when it worked, else Yoast's error code."""
    try:
        answer = api.post(route, {"items": [{"id": post_id, **fields}]})
    except WordPressApiError as exc:
        raise _refused(exc, site) from exc
    results = answer.get("results", []) if isinstance(answer, Mapping) else []
    mine = next((r for r in results if isinstance(r, Mapping) and r.get("id") == post_id), None)
    if mine is not None and not mine.get("success", True):
        return str(mine.get("error", "") or "refused")
    return ""


def save_bulk(
    api: Any,
    site: str,
    content_type: str,
    post_id: int,
    loaded: Mapping[str, Any],
    changes: Mapping[str, str],
) -> tuple[dict[str, Any], tuple[str, ...], dict[str, str]]:
    """Conflict check, write, verify. Returns (the post now, fields not kept, the undo).

    Runs off the UI thread. The undo is the values the post had just before.
    """
    title = rendered(loaded.get("title")) or f"item {post_id}"
    found = read_bulk(api, site, content_type, ids=[post_id])
    current = found[0] if found else {}
    moved = [
        k
        for k in changes
        if k in current and k in loaded and str(current.get(k) or "") != str(loaded.get(k) or "")
    ]
    if moved:
        names = SEARCH_FIELDS | SOCIAL_FIELDS
        raise EditConflict(
            f"{title}'s {', '.join(names[k] for k in moved)} changed on {site} after QUILL "
            "read it. Nothing was sent. F5 reads it again."
        )
    search = {k: v for k, v in changes.items() if k in SEARCH_FIELDS}
    social = {k: v for k, v in changes.items() if k in SOCIAL_FIELDS}
    errors = []
    for route, fields in ((UPDATE_SEARCH, search), (UPDATE_SOCIAL, social)):
        if fields:
            error = _post(api, route, post_id, fields, site)
            if error:
                errors.append(error)
    if errors:
        raise WordPressApiError(f"Yoast SEO refused the change to {title}: {', '.join(errors)}.")
    after = read_bulk(api, site, content_type, ids=[post_id])
    now = after[0] if after else {}
    missed = tuple(
        k for k, v in changes.items() if now and str(now.get(k, "") or "").strip() != v.strip()
    )
    undo = {k: str((current or loaded).get(k, "") or "") for k in changes}
    return now, missed, undo


def meta_social(
    meta: Mapping[str, str], wanted: Mapping[str, str]
) -> tuple[dict[str, str], list[str]]:
    """Social fields through registered meta: the changed ones, and the names not registered."""
    out: dict[str, str] = {}
    unwritable: list[str] = []
    for key, label in SOCIAL_META.items():
        value = wanted.get(key)
        if value is None or value.strip() == str(meta.get(key, "") or "").strip():
            continue
        if key not in meta:
            unwritable.append(label)
            continue
        out[key] = value.strip()
    return out, unwritable


def bulk_fields_from_meta(meta_body: Mapping[str, str]) -> dict[str, str]:
    """Registered-meta names -> the bulk editor's names (the image has none)."""
    return {_FIELD_FOR_META[k]: v for k, v in meta_body.items() if k in _FIELD_FOR_META}


def put_back(api: Any, site: str, post_id: int, fields: Mapping[str, str]) -> None:
    """Ctrl+Z for a bulk-editor save: the old values, each through its own route."""
    for route, names in ((UPDATE_SEARCH, SEARCH_FIELDS), (UPDATE_SOCIAL, SOCIAL_FIELDS)):
        part = {k: v for k, v in fields.items() if k in names}
        if part:
            _post(api, route, post_id, part, site)
