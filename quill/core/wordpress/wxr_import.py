"""Import a WordPress export file as drafts (wp_missing.md, Moving).

From a WXR file read by :mod:`quill.core.wordpress.wxr_read`, written by any
WordPress site, :func:`plan_import` works out against the connected site:

- **authors**: each matched to a person on this site by login, then by
  email; anyone unmatched is given to one person the importer chooses
  (themselves unless they pick another);
- **terms**: categories, tags and terms of taxonomies this site also has,
  matched by slug and created when missing; terms of taxonomies it lacks are
  left out and named;
- **items**: posts, pages, synced patterns and custom types this site also
  has; menu items, and types the site lacks, are left out and counted;
- **attachments**: downloaded from the address the file names and uploaded
  here, only when the person agrees to each host (:attr:`ImportPlan.hosts`);
  otherwise skipped, and the text keeps pointing at the old site.

:func:`send_import` then creates **everything as a draft** -- nothing is ever
published -- rewriting picture and file addresses to the uploaded copies,
links between the imported items to their new drafts, and the old site's
address to this one (Copy to Site's :func:`rewrite_links`). Every item has
its own line in the result. :func:`undo_import` moves the drafts it made to
the Trash; uploaded files and created terms stay and are said to.

Wx-free; requests go through the site's own client, and downloads through an
injected fetcher (Media and Files' capped HTTPS download), off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.media_replace import _stem_pattern, rewrite_uses
from quill.core.wordpress.workbench_site_copy import rewrite_links
from quill.core.wordpress.wxr_read import WxrFile, WxrItem, WxrTerm

__all__ = [
    "MAX_ATTACHMENTS",
    "ImportPlan",
    "ImportResult",
    "plan_import",
    "send_import",
    "undo_import",
]

MAX_ATTACHMENTS = 500
"""At most this many files are downloaded in one import; the rest are named as left out."""
_BUILT_IN_TYPES = {"post": "wp/v2/posts", "page": "wp/v2/pages", "wp_block": "wp/v2/blocks"}
_SKIP_TYPES = frozenset({"nav_menu_item", "attachment", "revision", "customize_changeset"})
META_LEFT_OUT = (
    "custom fields other than the featured image: REST takes only the fields a plugin "
    "registers, so they are not sent"
)


@dataclass
class ImportPlan:
    """What the import will do on this site, line by line, before anything is sent."""

    wxr: WxrFile
    authors: dict[str, int] = field(default_factory=dict)  # login -> user id here
    unmatched: list[str] = field(default_factory=list)
    people: list[tuple[int, str]] = field(default_factory=list)  # (id, name) on this site
    fallback: int = 0
    term_bases: dict[str, str] = field(default_factory=dict)  # taxonomy -> rest base here
    term_ids: dict[tuple[str, str], int] = field(default_factory=dict)  # (taxonomy, slug)
    create_terms: list[WxrTerm] = field(default_factory=list)
    routes: dict[str, str] = field(default_factory=dict)  # post type -> route here
    items: list[WxrItem] = field(default_factory=list)
    attachments: list[WxrItem] = field(default_factory=list)
    left_out: list[str] = field(default_factory=list)

    @property
    def hosts(self) -> list[str]:
        """The hosts attachments would be downloaded from."""
        found = {urlparse(a.attachment_url).hostname or "" for a in self.attachments}
        return sorted(h for h in found if h)

    def person(self, ident: int) -> str:
        return next((name for i, name in self.people if i == ident), f"user {ident}")

    def lines(self) -> list[str]:
        said = [
            f"From {self.wxr.title or 'a WordPress site'} ({self.wxr.blog_url}), WXR "
            f"{self.wxr.version}.",
            "Everything is made as a draft; nothing is published. Each keeps its original date.",
        ]
        for login, ident in self.authors.items():
            said.append(f"Author {login} is {self.person(ident)} here.")
        for login in self.unmatched:
            said.append(
                f"Author {login} is not on this site; given to {self.person(self.fallback)}."
            )
        for term in self.create_terms:
            said.append(f"New {_tax_words(term.taxonomy)}: {term.name or term.slug}.")
        for item in self.items:
            said.append(f"{_type_words(item.post_type)}: {item.title or '(no title)'}.")
        if self.attachments:
            said.append(
                f"{len(self.attachments)} files to download from {', '.join(self.hosts)} "
                "and upload here, if you agree."
            )
        said += [f"Left out: {line}." for line in self.left_out]
        return said


@dataclass
class ImportResult:
    lines: list[str] = field(default_factory=list)
    made: list[tuple[str, str]] = field(default_factory=list)  # (route with id, title)
    uploaded: int = 0
    terms: int = 0

    @property
    def count(self) -> int:
        return len(self.made)


def _tax_words(taxonomy: str) -> str:
    return {"category": "category", "post_tag": "tag"}.get(taxonomy, f"{taxonomy} term")


def _type_words(post_type: str) -> str:
    return {"post": "Post", "page": "Page", "wp_block": "Pattern"}.get(post_type, post_type)


def _rows(api: WordPressApi, route: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    try:
        return list(api.iter_collection(route, dict(params)))
    except WordPressApiError:
        return []


def plan_import(api: WordPressApi, wxr: WxrFile) -> ImportPlan:
    """Match the file against this site: people, terms, types and files."""
    plan = ImportPlan(wxr)
    users = _rows(api, "wp/v2/users", {"context": "edit"}) or _rows(
        api, "wp/v2/users", {"who": "authors"}
    )
    plan.people = [(int(u.get("id", 0)), str(u.get("name") or u.get("slug") or "")) for u in users]
    me = api.get("wp/v2/users/me")
    plan.fallback = int(me.get("id", 0) or 0) if isinstance(me, Mapping) else 0
    if plan.fallback and plan.fallback not in [i for i, _n in plan.people]:
        plan.people.insert(0, (plan.fallback, str(me.get("name", "") or "you")))
    by_login = {str(u.get("username") or u.get("slug") or "").casefold(): u for u in users}
    by_email = {str(u.get("email", "")).casefold(): u for u in users if u.get("email")}
    for author in wxr.authors:
        found = by_login.get(author.login.casefold()) or by_email.get(author.email.casefold())
        if found:
            plan.authors[author.login] = int(found.get("id", 0))
        else:
            plan.unmatched.append(author.login)
    _plan_terms(api, plan)
    _plan_items(api, plan)
    if wxr.beyond_cap:
        plan.left_out.append(
            f"{wxr.beyond_cap} items past the first {len(wxr.items)} the file holds; import "
            "the rest from a smaller export"
        )
    plan.left_out.append(META_LEFT_OUT)
    comments = sum(i.comments for i in plan.items)
    if comments:
        plan.left_out.append(f"{comments} comments: QUILL imports writing, not conversations")
    return plan


def _plan_terms(api: WordPressApi, plan: ImportPlan) -> None:
    plan.term_bases = {"category": "categories", "post_tag": "tags"}
    taxonomies = api.get("wp/v2/taxonomies")
    for slug, tax in taxonomies.items() if isinstance(taxonomies, Mapping) else ():
        if isinstance(tax, Mapping) and tax.get("rest_base") and slug not in plan.term_bases:
            if str(tax.get("rest_namespace", "wp/v2") or "wp/v2") == "wp/v2":
                plan.term_bases[str(slug)] = str(tax["rest_base"])
    wanted = {(t.taxonomy, t.slug): t for t in plan.wxr.terms}
    for item in plan.wxr.items:
        for taxonomy, slug, name in item.terms:
            if taxonomy != "nav_menu" and (taxonomy, slug) not in wanted:
                wanted[(taxonomy, slug)] = WxrTerm(taxonomy, slug, name)
    missing_tax: dict[str, int] = {}
    for taxonomy in {t for t, _s in wanted}:
        if taxonomy == "nav_menu":
            continue
        base = plan.term_bases.get(taxonomy)
        if not base:
            missing_tax[taxonomy] = sum(1 for t, _s in wanted if t == taxonomy)
            continue
        for row in _rows(api, f"wp/v2/{base}", {"context": "view"}):
            plan.term_ids[(taxonomy, str(row.get("slug", "")))] = int(row.get("id", 0))
    for (taxonomy, slug), term in wanted.items():
        if taxonomy in plan.term_bases and (taxonomy, slug) not in plan.term_ids:
            plan.create_terms.append(term)
    plan.create_terms.sort(key=lambda t: bool(t.parent))  # parents first
    for taxonomy, count in sorted(missing_tax.items()):
        plan.left_out.append(f"{count} terms of {taxonomy}, a taxonomy this site does not have")


def _plan_items(api: WordPressApi, plan: ImportPlan) -> None:
    plan.routes = dict(_BUILT_IN_TYPES)
    types = api.get("wp/v2/types")
    for slug, info in types.items() if isinstance(types, Mapping) else ():
        if isinstance(info, Mapping) and info.get("rest_base") and slug not in plan.routes:
            namespace = str(info.get("rest_namespace", "wp/v2") or "wp/v2")
            plan.routes[str(slug)] = f"{namespace}/{info['rest_base']}"
    skipped: dict[str, int] = {}
    for item in plan.wxr.items:
        if item.post_type == "attachment":
            if item.attachment_url and len(plan.attachments) < MAX_ATTACHMENTS:
                plan.attachments.append(item)
            else:
                skipped["attachment"] = skipped.get("attachment", 0) + 1
        elif item.post_type in _SKIP_TYPES or item.post_type not in plan.routes:
            skipped[item.post_type] = skipped.get(item.post_type, 0) + 1
        elif item.status in ("trash", "auto-draft", "inherit"):
            skipped[f"{item.post_type} ({item.status})"] = (
                skipped.get(f"{item.post_type} ({item.status})", 0) + 1
            )
        else:
            plan.items.append(item)
    for kind, count in sorted(skipped.items()):
        plan.left_out.append(f"{count} {kind} items: {_why_skipped(kind)}")


def _why_skipped(kind: str) -> str:
    if kind == "nav_menu_item":
        return "menus are rebuilt in Appearance, Menus, or copied with Copy to Site"
    if kind == "attachment":
        return f"files with no address, or past the first {MAX_ATTACHMENTS}"
    if "(" in kind:
        return "trashed and automatic drafts are not imported"
    return "a type this site does not have"


# -- sending ---------------------------------------------------------------------------


def _make_terms(api: WordPressApi, plan: ImportPlan, result: ImportResult) -> None:
    for term in plan.create_terms:
        base = plan.term_bases[term.taxonomy]
        body: dict[str, Any] = {"name": term.name or term.slug, "slug": term.slug}
        if term.description:
            body["description"] = term.description
        parent = plan.term_ids.get((term.taxonomy, term.parent), 0) if term.parent else 0
        if parent:
            body["parent"] = parent
        try:
            made = api.post(f"wp/v2/{base}", body)
            plan.term_ids[(term.taxonomy, term.slug)] = int(made.get("id", 0))
            result.terms += 1
            result.lines.append(f"Made the {_tax_words(term.taxonomy)} {body['name']}.")
        except WordPressApiError as exc:
            what = _tax_words(term.taxonomy)
            result.lines.append(f"Not made: the {what} {body['name']}: {exc.plain}")


def _upload_files(
    api: WordPressApi, plan: ImportPlan, fetch: Callable[[str], Any], result: ImportResult
) -> dict[int, tuple[str, int, str]]:
    """Old attachment id -> (old address, new id, new address)."""
    moved: dict[int, tuple[str, int, str]] = {}
    for item in plan.attachments:
        try:
            got = fetch(item.attachment_url)
            made = api.upload("wp/v2/media", got.filename, got.content, got.content_type)
            new_id = int(made.get("id", 0))
            body: dict[str, Any] = {}
            if item.title:
                body["title"] = item.title
            if item.meta.get("_wp_attachment_image_alt"):
                body["alt_text"] = item.meta["_wp_attachment_image_alt"]
            if body:
                api.post(f"wp/v2/media/{new_id}", body)
            moved[item.post_id] = (item.attachment_url, new_id, str(made.get("source_url", "")))
            result.uploaded += 1
            result.lines.append(f"Uploaded {got.filename}.")
        except Exception as exc:  # noqa: BLE001 - one file's failure is one line
            reason = getattr(exc, "plain", "") or exc
            result.lines.append(f"Not uploaded: {item.attachment_url}: {reason}")
    return moved


def _body(
    item: WxrItem, plan: ImportPlan, moved: Mapping[int, tuple[str, int, str]], here: str
) -> dict[str, Any]:
    content = item.content
    for old_id, (old_url, new_id, new_url) in moved.items():
        content = rewrite_uses(content, old_id, old_url, new_id, new_url)
    # A file that was not uploaded (skipped, or its download failed) exists only
    # on the old site, so its address must survive the site-address rewrite.
    held: list[str] = []

    def hold(match: re.Match[str]) -> str:
        held.append(match.group(0))
        return f"\x00{len(held) - 1}\x00"

    for attachment in plan.attachments:
        if attachment.post_id not in moved and attachment.attachment_url:
            content = _stem_pattern(attachment.attachment_url).sub(hold, content)
    for base in {plan.wxr.blog_url, plan.wxr.site_url} - {""}:
        content = rewrite_links(content, base, here)
    content = re.sub("\x00(\\d+)\x00", lambda m: held[int(m.group(1))], content)
    body: dict[str, Any] = {
        "title": item.title,
        "content": content,
        "status": "draft",
        "author": plan.authors.get(item.creator, plan.fallback) or None,
    }
    if item.post_type != "wp_block":
        body.update({"excerpt": item.excerpt, "slug": item.slug, "menu_order": item.menu_order})
    if item.date and not item.date.startswith("0000"):
        body["date"] = item.date.replace(" ", "T")
    for taxonomy, slug, _name in item.terms:
        term_base = plan.term_bases.get(taxonomy)
        ident = plan.term_ids.get((taxonomy, slug))
        if term_base and ident:
            body.setdefault(term_base, []).append(ident)
    thumb_text = item.meta.get("_thumbnail_id", "")
    thumb = int(thumb_text) if thumb_text.isdigit() else 0
    if thumb in moved:
        body["featured_media"] = moved[thumb][1]
    return {k: v for k, v in body.items() if v not in (None, "")}


def send_import(
    api: WordPressApi,
    plan: ImportPlan,
    *,
    here: str,
    fetch: Callable[[str], Any] | None = None,
) -> ImportResult:
    """Make the plan on this site, as drafts; a line per term, file and item.

    *here* is this site's address, for rewriting links; *fetch* downloads one
    attachment (None skips them all).
    """
    result = ImportResult()
    _make_terms(api, plan, result)
    moved = _upload_files(api, plan, fetch, result) if fetch and plan.attachments else {}
    if plan.attachments and not fetch:
        plan.left_out.append(
            f"{len(plan.attachments)} files, skipped as you chose: the text still points at "
            f"{', '.join(plan.hosts)}"
        )
    new_ids: dict[int, int] = {}
    links: dict[str, str] = {}
    made_items: list[tuple[WxrItem, dict[str, Any], str]] = []
    for item in plan.items:
        route = plan.routes[item.post_type]
        body = _body(item, plan, moved, here)
        try:
            made = api.post(route, body)
        except WordPressApiError as exc:
            result.lines.append(f"Not made: {item.title or '(no title)'}: {exc.plain or exc}")
            continue
        ident = int(made.get("id", 0))
        new_ids[item.post_id] = ident
        if item.link and made.get("link"):
            links[item.link] = str(made["link"])
        result.made.append((f"{route}/{ident}", item.title or "(no title)"))
        made_items.append((item, {**made, "sent": body.get("content", "")}, route))
        result.lines.append(
            f"Made {_type_words(item.post_type).lower()} {item.title or '(no title)'} as a "
            f"draft, number {ident}."
        )
    _second_pass(api, made_items, new_ids, links, here, plan, result)
    from quill.core.wordpress.workbench_carry import left_out_section

    result.lines += left_out_section(plan.left_out)
    return result


def _second_pass(
    api: WordPressApi,
    made_items: list[tuple[WxrItem, dict[str, Any], str]],
    new_ids: Mapping[int, int],
    links: Mapping[str, str],
    here: str,
    plan: ImportPlan,
    result: ImportResult,
) -> None:
    """Parents, and links between the imported items, once every draft exists."""
    rewritten = {rewrite_links(old, plan.wxr.blog_url, here): new for old, new in links.items()}
    for item, made, route in made_items:
        body: dict[str, Any] = {}
        if item.parent and item.parent in new_ids:
            body["parent"] = new_ids[item.parent]
        content = str(made.get("sent", "") or "")
        linked = content
        for old, new in sorted(rewritten.items(), key=lambda pair: -len(pair[0])):
            linked = linked.replace(f'"{old}"', f'"{new}"').replace(f"'{old}'", f"'{new}'")
        if linked != content:
            body["content"] = linked
        if body:
            try:
                api.post(f"{route}/{made['id']}", body)
            except WordPressApiError as exc:
                result.lines.append(f"{item.title}: its parent or links were not set: {exc.plain}")


def undo_import(api: WordPressApi, result: ImportResult) -> str:
    """Move every draft the import made to the Trash; files and terms stay, and are said."""
    trashed, kept = 0, []
    for route, title in reversed(result.made):
        try:
            api.delete(route)
            trashed += 1
        except WordPressApiError as exc:
            kept.append(f"{title} ({exc.plain or exc})")
    said = f"Moved {trashed} imported drafts to the Trash."
    if kept:
        said += f" Not moved: {'; '.join(kept[:3])}."
    if result.uploaded or result.terms:
        said += (
            f" The {result.uploaded} uploaded files and {result.terms} new terms stay; "
            "remove them from Media and the term lists if you do not want them."
        )
    return said
