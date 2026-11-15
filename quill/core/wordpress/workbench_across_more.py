"""Across Sites for the six kinds the first pass declined, and merge and remove (WP-R-044).

:mod:`quill.core.wordpress.workbench_across` gathers a kind by name over the
scope; :mod:`~quill.core.wordpress.workbench_across_ops` makes them the same.
This module adds:

- **starter pages** (``wp/v2/block-patterns/patterns`` whose block types
  include ``core/post-content``) and **content types** (``wp/v2/types``):
  read and compared. Both are registered by code on each site, which REST
  cannot do, so neither is copied (the scope matrix says so);
- **forms** (QUILL Accessible Forms, ``qaf/v1/forms``): compared by their
  questions, and made the same as a **draft** where missing, so each site
  checks its own notification addresses; an existing form takes the winner's
  questions and keeps its own settings and entries;
- **pages with a role**: the front page (``page_on_front`` in
  ``wp/v2/settings``) and the privacy policy page. REST does not say which
  page is the privacy page, so it is the page at WordPress's own address for
  it, ``privacy-policy``, and the row says so; "update from one" copies the
  chosen site's text to the others;
- **redirects** (Redirection, ``redirection/v1``): by the address they start
  from; made the same (made where missing, in that site's default group) and
  removed everywhere;
- **spam senders**: QUILL Accessible Forms' blocklist, on the route
  ``qaf/v1/spam/blocklist`` (``GET`` the list, ``POST`` ``{value, kind}`` to
  block, ``DELETE .../<id>`` to unblock). **QAF must offer that route**; a site
  whose QAF does not is "not read", never "missing";
- **merge and remove everywhere** for terms (:func:`term_merge_plan`,
  :func:`removal_plan`), and remove for redirects and spam senders.

A site that does not run the plugin a kind needs is "not read" with the
reason, so Make Them the Same never makes on it what it only failed to read.
Wx-free; every request goes through the site's own client, off the UI thread.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered
from quill.core.wordpress.workbench_by_name import Edit, Outcome

__all__ = [
    "BLOCKLIST_ROUTE",
    "MORE_KINDS",
    "Removal",
    "edit_for_more",
    "gather_more_kinds",
    "removal_plan",
    "resolve_group",
    "run_removals",
    "term_merge_plan",
]

MORE_KINDS = (
    "starter_pages",
    "forms",
    "content_types",
    "role_pages",
    "redirects",
    "spam_senders",
)

BLOCKLIST_ROUTE = "qaf/v1/spam/blocklist"
"""QUILL Accessible Forms' blocklist. QUILL is built against it; QAF must offer it."""

_REDIRECTION = "redirection/v1"
_PRIVACY_SLUG = "privacy-policy"
_NEW_GROUP = 0  # a redirect body's group before the site's default group is known


def _all(
    api: WordPressApi, route: str, params: Mapping[str, object], unread: list[str]
) -> list[Any]:
    try:
        return list(api.iter_collection(route, params, per_page=100, max_pages=5))
    except WordPressApiError as exc:
        unread.append(f"{route}: {exc.plain or exc}")
        return []


def _get(api: WordPressApi, route: str, unread: list[str], **params: Any) -> Any:
    try:
        return api.get(route, **params)
    except WordPressApiError as exc:
        unread.append(f"{route}: {exc.plain or exc}")
        return None


def _offers(api: WordPressApi, namespace: str) -> bool:
    from quill.core.wordpress.site_features import read_index

    try:
        return read_index(api).supports(namespace)
    except WordPressApiError:
        return False


def _version(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]


def _title(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("title")) or rendered(raw.get("title"))


# -- gathering -------------------------------------------------------------------------


def _starter_pages(api: WordPressApi, unread: list[str]) -> dict[str, Mapping[str, Any]]:
    found: dict[str, Mapping[str, Any]] = {}
    answer = _get(api, "wp/v2/block-patterns/patterns", unread)
    for raw in answer if isinstance(answer, list) else ():
        if not isinstance(raw, Mapping) or "core/post-content" not in (raw.get("blockTypes") or []):
            continue
        content = str(raw.get("content", "") or "")
        found[str(raw.get("title") or raw.get("name") or "")] = {
            "name": raw.get("name", ""),
            "value": f"version {_version(content)}, {len(content)} characters",
        }
    return found


def _content_types(api: WordPressApi, unread: list[str]) -> dict[str, Mapping[str, Any]]:
    found: dict[str, Mapping[str, Any]] = {}
    answer = _get(api, "wp/v2/types", unread)
    for slug, raw in answer.items() if isinstance(answer, Mapping) else ():
        if not isinstance(raw, Mapping):
            continue
        taxonomies = ", ".join(sorted(str(t) for t in raw.get("taxonomies") or [])) or "none"
        shape = "with parents" if raw.get("hierarchical") else "without parents"
        found[f"{raw.get('name') or slug} ({slug})"] = {
            "slug": slug,
            "value": f"{shape}; taxonomies {taxonomies}; at {raw.get('rest_base') or 'no REST'}",
        }
    return found


def _forms(api: WordPressApi, site: str, unread: list[str]) -> dict[str, Mapping[str, Any]]:
    from quill.core.forms import model as M
    from quill.core.forms import qaf_site

    namespace = qaf_site.site_namespace(api)
    if not namespace:
        unread.append(f"qaf/v1/forms: {site} does not run QUILL Accessible Forms")
        return {}
    found: dict[str, Mapping[str, Any]] = {}
    for listed in _all(api, f"{namespace}/forms", {}, unread)[:50]:
        ident = int(listed.get("id", 0) or 0) if isinstance(listed, Mapping) else 0
        raw = _get(api, f"{namespace}/forms/{ident}", unread) if ident else None
        form = qaf_site.form_from_payload(raw)
        model = form.model()
        if model is None:
            continue
        questions = [v for v in M.labels(model).values() if v]
        found[form.title or f"Form {form.id}"] = {
            "id": form.id,
            "namespace": namespace,
            "model": model,
            "config": form.config,
            "status": form.status,
            "updated_at": form.updated_at,
            "value": f"{len(questions)} questions, version {_version('|'.join(questions))}",
        }
    return found


def _page(api: WordPressApi, ident: int, role: str, unread: list[str]) -> Mapping[str, Any]:
    raw = _get(api, f"wp/v2/pages/{ident}", unread, context="edit")
    if not isinstance(raw, Mapping):
        return {}
    content = raw_text(raw.get("content")) or rendered(raw.get("content"))
    when = str(raw.get("modified_gmt", "") or "")
    return {
        "id": int(raw.get("id", ident) or ident),
        "title": _title(raw),
        "content": content,
        "modified_gmt": raw.get("modified_gmt"),
        "role": role,
        "value": f"last updated {when[:10] or 'on a day not said'}, version {_version(content)}",
    }


def _role_pages(api: WordPressApi, unread: list[str]) -> dict[str, Mapping[str, Any]]:
    found: dict[str, Mapping[str, Any]] = {}
    settings = _get(api, "wp/v2/settings", unread)
    front = int(settings.get("page_on_front", 0) or 0) if isinstance(settings, Mapping) else 0
    if front and isinstance(settings, Mapping) and settings.get("show_on_front") == "page":
        page = _page(api, front, "front page", unread)
        if page:
            found["Front page"] = page
    params = {"slug": _PRIVACY_SLUG, "status": "any", "context": "edit", "_fields": "id"}
    privacy = _all(api, "wp/v2/pages", params, unread)
    if privacy:
        page = _page(api, int(privacy[0].get("id", 0) or 0), "privacy policy", unread)
        if page:
            found["Privacy policy page (the privacy-policy address)"] = page
    return found


def _redirects(api: WordPressApi, site: str, unread: list[str]) -> dict[str, Mapping[str, Any]]:
    from quill.core.wordpress.workbench_redirects import read_pages

    if not _offers(api, _REDIRECTION):
        unread.append(f"{_REDIRECTION}/redirect: {site} does not run the Redirection plugin")
        return {}
    try:
        items = read_pages(api, "redirect")
    except WordPressApiError as exc:
        unread.append(f"{_REDIRECTION}/redirect: {exc.plain or exc}")
        return {}
    found: dict[str, Mapping[str, Any]] = {}
    for raw in items:
        data = raw.get("action_data")
        target = str(data.get("url", "") if isinstance(data, Mapping) else data or "")
        code = raw.get("action_code", "") or ""
        found[str(raw.get("url", "") or "")] = {
            **dict(raw),
            "target": target,
            "value": f"to {target or 'nowhere set'}, code {code or 'default'}",
        }
    return found


def _spam_senders(api: WordPressApi, site: str, unread: list[str]) -> dict[str, Mapping[str, Any]]:
    from quill.core.forms import qaf_site

    if qaf_site.site_namespace(api) != qaf_site.NAMESPACE:
        unread.append(f"{BLOCKLIST_ROUTE}: {site} does not run QUILL Accessible Forms (qaf/v1)")
        return {}
    missed: list[str] = []
    answer = _get(api, BLOCKLIST_ROUTE, missed)
    if missed:
        unread.append(
            f"{BLOCKLIST_ROUTE}: {site}'s QUILL Accessible Forms did not give its blocklist "
            f"({missed[0].partition(': ')[2]}); it needs a version that offers this route"
        )
        return {}
    items = answer.get("items") if isinstance(answer, Mapping) else answer
    found: dict[str, Mapping[str, Any]] = {}
    for raw in items if isinstance(items, list) else ():
        if isinstance(raw, Mapping) and raw.get("value"):
            kind = str(raw.get("kind", "") or "sender")
            found[str(raw["value"])] = {
                "id": raw.get("id"),
                "kind": kind,
                "value": f"blocked {kind}",
            }
    return found


def gather_more_kinds(
    kind: str, site: str, api: WordPressApi, unread: list[str]
) -> dict[str, Mapping[str, Any]]:
    """One of :data:`MORE_KINDS` on one site: name -> what it has, its variant as ``value``."""
    if kind == "starter_pages":
        return _starter_pages(api, unread)
    if kind == "content_types":
        return _content_types(api, unread)
    if kind == "forms":
        return _forms(api, site, unread)
    if kind == "role_pages":
        return _role_pages(api, unread)
    if kind == "redirects":
        return _redirects(api, site, unread)
    if kind == "spam_senders":
        return _spam_senders(api, site, unread)
    return {}


# -- Make Them the Same ------------------------------------------------------------------


def _form_edit(
    site: str, name: str, winner: Mapping[str, Any], mine: Mapping[str, Any] | None
) -> Edit:
    from quill.core.forms import qaf_site
    from quill.core.forms.bfl_write import to_bfl

    model = dict(winner.get("model") or {})
    bfl = str(to_bfl(model))
    if mine is None:
        body = qaf_site.publish_body(model, bfl, status="draft")
        words = "made as a draft with the winner's questions; check its notification addresses"
        return Edit(site, f"{qaf_site.NAMESPACE}/forms", name, body, None, words=words)
    existing = qaf_site.SiteForm(
        int(mine.get("id", 0) or 0),
        name,
        str(mine.get("status", "draft")),
        config=dict(mine.get("config") or {}),
    )
    body = qaf_site.publish_body(model, bfl, status=existing.status, existing=existing)
    before = qaf_site.publish_body(
        dict(mine.get("model") or {}),
        str(to_bfl(dict(mine.get("model") or {}))),
        status=existing.status,
        existing=existing,
    )
    return Edit(
        site,
        f"{mine.get('namespace') or qaf_site.NAMESPACE}/forms/{existing.id}",
        name,
        body,
        before,
        "updated_at",
        mine.get("updated_at") or None,
        "takes the winner's questions; keeps its own settings and entries",
    )


def edit_for_more(
    kind: str, site: str, name: str, winner: Mapping[str, Any], mine: Mapping[str, Any] | None
) -> Edit | str:
    """The edit that makes *site* match *winner* for a :data:`MORE_KINDS` kind, or why not."""
    from quill.core.wordpress.workbench_scope_matrix import classify

    if kind in ("starter_pages", "content_types"):
        return classify("across", kind, "all_sites", "make_same").reason.rstrip(".")
    if kind == "forms":
        return _form_edit(site, name, winner, mine)
    if kind == "role_pages":
        if mine is None:
            return (
                "no page has this role here; make one and choose it in Settings > Reading or "
                "Privacy on this site first"
            )
        content = str(winner.get("content", ""))
        return Edit(
            site,
            f"wp/v2/pages/{mine.get('id')}",
            f"{name}: {mine.get('title', '')}",
            {"content": content},
            {"content": mine.get("content", "")},
            "modified_gmt",
            mine.get("modified_gmt"),
            f"its text becomes the chosen one's, {len(content)} characters",
        )
    if kind == "redirects":
        from quill.core.wordpress.workbench_redirects import edit_body

        code = int(winner.get("action_code", 301) or 301)
        target = str(winner.get("target", ""))
        regex = bool(winner.get("regex"))
        if mine is None:
            body = edit_body(name, target, code, group_id=_NEW_GROUP, regex=regex)
            words = f"made, leading to {target}, in this site's default group"
            return Edit(site, f"{_REDIRECTION}/redirect", name, body, None, words=words)
        group = int(mine.get("group_id", 0) or 0)
        return Edit(
            site,
            f"{_REDIRECTION}/redirect/{mine.get('id')}",
            name,
            edit_body(name, target, code, group_id=group, regex=regex),
            edit_body(
                name,
                str(mine.get("target", "")),
                int(mine.get("action_code", 301) or 301),
                group_id=group,
                regex=bool(mine.get("regex")),
            ),
            words=f"leads to {target} instead of {mine.get('target') or 'nowhere'}",
        )
    if kind == "spam_senders":
        if mine is not None:
            return "already blocked here"
        body = {"value": name, "kind": str(winner.get("kind", "") or "sender")}
        return Edit(site, BLOCKLIST_ROUTE, name, body, None, words="blocked here too")
    return f"{kind} are not changed by an edit here"


def resolve_group(api: WordPressApi, edit: Edit) -> Edit:
    """A new redirect's edit with the site's default Redirection group filled in."""
    if edit.route != f"{_REDIRECTION}/redirect" or edit.body.get("group_id") != _NEW_GROUP:
        return edit
    from quill.core.wordpress.workbench_redirects import (
        default_group,
        make_first_group,
        read_groups,
    )

    group = default_group(read_groups(api)) or make_first_group(api)
    if not group:
        raise WordPressApiError("The site has no redirect group, and would not make one.")
    return replace(edit, body={**edit.body, "group_id": group})


# -- remove and merge everywhere ---------------------------------------------------------


@dataclass(frozen=True)
class Removal:
    """One thing deleted on one site: how, and what the preview says."""

    site: str
    name: str
    method: str  # DELETE, or POST for Redirection's bulk delete
    route: str
    body: Any
    words: str

    @property
    def line(self) -> str:
        return f"{self.site}: {self.name}: {self.words}"


def _term_route(name: str) -> str:
    return "wp/v2/categories" if name.endswith("(category)") else "wp/v2/tags"


def removal_plan(
    kind: str, name: str, objects: Mapping[str, Mapping[str, Any]]
) -> tuple[list[Removal], list[Outcome]]:
    """What Remove Everywhere deletes on each site that has *name*, and the sites it cannot."""
    plan: list[Removal] = []
    refused: list[Outcome] = []
    for site, raw in sorted(objects.items()):
        ident = raw.get("id")
        if ident in (None, ""):
            refused.append(Outcome(site, name, False, "the site did not say its number"))
        elif kind == "terms":
            count = int(raw.get("count", 0) or 0)
            word = "category" if name.endswith("(category)") else "tag"
            after = (
                "; posts in no other category go to the default one" if word == "category" else ""
            )
            words = f"the {word} is deleted from {count} posts{after}"
            plan.append(Removal(site, name, "DELETE", f"{_term_route(name)}/{ident}", None, words))
        elif kind == "redirects":
            route = f"{_REDIRECTION}/bulk/redirect/delete"
            plan.append(
                Removal(site, name, "POST", route, {"items": [ident]}, "the redirect is deleted")
            )
        elif kind == "spam_senders":
            route = f"{BLOCKLIST_ROUTE}/{ident}"
            plan.append(Removal(site, name, "DELETE", route, None, "unblocked"))
        else:
            refused.append(Outcome(site, name, False, f"{kind} are not removed everywhere"))
    return plan, refused


def run_removals(api_for: Callable[[str], WordPressApi], plan: Sequence[Removal]) -> list[Outcome]:
    """Send each removal; one site refusing does not stop the rest."""
    outcomes: list[Outcome] = []
    for step in plan:
        try:
            api = api_for(step.site)
            if step.method == "DELETE":
                api.delete(step.route, force=True)
            else:
                api.post(step.route, dict(step.body or {}))
        except Exception as exc:  # noqa: BLE001 - one site's failure is that site's outcome
            outcomes.append(
                Outcome(step.site, step.name, False, getattr(exc, "plain", "") or str(exc))
            )
            continue
        outcomes.append(Outcome(step.site, step.name, True, step.words))
    return outcomes


def term_merge_plan(
    api: WordPressApi, site: str, name: str, source: Mapping[str, Any], target_name: str
) -> tuple[list[Edit], int, str]:
    """On one site: the edits moving every post from term *name* to *target_name*.

    Returns (edits, the source term's id to delete once every edit is sent, and
    why not -- "" when the merge can go ahead). The target is found by name,
    in the same taxonomy; a site without it is refused, never given a new one.
    """
    route = _term_route(name)
    base = route.rpartition("/")[2]
    wanted = target_name.strip().casefold()
    missed: list[str] = []
    terms = _all(api, route, {"search": target_name.strip(), "hide_empty": False}, missed)
    if missed:
        return [], 0, missed[0]
    target = next((t for t in terms if str(t.get("name", "")).strip().casefold() == wanted), None)
    source_id = int(source.get("id", 0) or 0)
    if target is None:
        return [], 0, f"has no {base[:-1] if base == 'tags' else 'category'} named {target_name}"
    target_id = int(target.get("id", 0) or 0)
    if target_id == source_id:
        return [], 0, "the two are the same term here"
    params = {
        base: source_id,
        "status": "any",
        "context": "edit",
        "_fields": f"id,title,{base},modified_gmt",
    }
    posts = _all(api, "wp/v2/posts", params, missed)
    if missed:
        return [], 0, missed[0]
    edits: list[Edit] = []
    for raw in posts:
        terms_now = [int(t) for t in raw.get(base) or []]
        moved = [t for t in terms_now if t != source_id]
        if target_id not in moved:
            moved.append(target_id)
        edits.append(
            Edit(
                site,
                f"wp/v2/posts/{raw.get('id')}",
                _title(raw) or f"#{raw.get('id')}",
                {base: moved},
                {base: terms_now},
                "modified_gmt",
                raw.get("modified_gmt"),
                f"moves from {name.rpartition(' (')[0]} to {target_name}",
            )
        )
    return edits, source_id, ""
