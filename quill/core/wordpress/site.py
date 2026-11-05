"""What QUILL does on a WordPress site, one function per action (wordpress.md 5, 6, 9).

Every function takes a :class:`~quill.core.wordpress.api.WordPressApi` and
returns plain dataclasses, so the dialogs above it never see JSON and the
tests below it never see a network. The routes are the core REST API's; nothing
here needs a plugin.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site_types import writing_types

# --------------------------------------------------------------------------- #
# Content items


#: The statuses Open offers, in the order it offers them (wordpress.md 5.2).
STATUSES: tuple[tuple[str, str], ...] = (
    ("publish", "Published"),
    ("draft", "Drafts"),
    ("pending", "Pending review"),
    ("future", "Scheduled"),
    ("private", "Private"),
    ("trash", "Trash"),
)
STATUS_LABELS = dict(STATUSES)


@dataclass(frozen=True)
class ItemSummary:
    id: int
    kind: str  # "post", "page" or a custom type's slug
    title: str
    status: str
    modified_gmt: str
    link: str

    def spoken(self) -> str:
        status = (
            STATUS_LABELS.get(self.status, self.status).rstrip("s")
            if self.status != "publish"
            else "Published"
        )
        return f"{self.title}, {status}, last changed {friendly_date(self.modified_gmt)}"


@dataclass
class Item:
    """A page or post as QUILL edits it: the raw content, never the rendered."""

    id: int
    kind: str
    title: str
    content: str
    status: str
    slug: str = ""
    excerpt: str = ""
    link: str = ""
    modified_gmt: str = ""
    date_gmt: str = ""
    author: int = 0
    categories: list[int] = field(default_factory=list)
    tags: list[int] = field(default_factory=list)
    featured_media: int = 0
    comment_status: str = ""
    ping_status: str = ""
    sticky: bool = False
    password: str = ""
    parent: int = 0
    menu_order: int = 0
    template: str = ""
    format: str = ""
    #: Custom fields changed in Properties (9.15); only those go back.
    meta: dict[str, Any] = field(default_factory=dict)

    def to_body(self) -> dict[str, Any]:
        """The fields WordPress takes back on create or update."""
        body: dict[str, Any] = {
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "excerpt": self.excerpt,
        }
        if self.slug:
            body["slug"] = self.slug
        if self.kind == "post":
            body["categories"] = list(self.categories)
            body["tags"] = list(self.tags)
            body["sticky"] = self.sticky
            if self.format:
                body["format"] = self.format
        if self.kind == "page":
            body["parent"] = self.parent
            body["menu_order"] = self.menu_order
        if self.featured_media or self.featured_media == 0:
            body["featured_media"] = self.featured_media
        for key in ("comment_status", "ping_status", "template"):
            value = getattr(self, key)
            if value:
                body[key] = value
        if self.password:
            body["password"] = self.password
        if self.author:
            body["author"] = self.author
        if self.meta:
            body["meta"] = dict(self.meta)
        return body


def kind_route(kind: str) -> str:
    """``post`` -> ``wp/v2/posts``; a custom type uses its REST base."""
    return {"post": "wp/v2/posts", "page": "wp/v2/pages"}.get(kind, f"wp/v2/{kind}")


def kind_from_payload(raw: Any, kind: str) -> str:
    """The kind to keep for an item the site sent back.

    WordPress's ``type`` is the post type (``event``), but a custom type's kind
    here is its REST base (``events``), which is the route it is sent back to.
    So the site's word is taken only for a post or a page, and the kind QUILL
    asked with is kept for everything else.
    """
    found = str(raw.get("type", "") or "") if isinstance(raw, dict) else ""
    if found in {"post", "page"} or not kind:
        return found or kind
    return kind


def list_content_types(api: WordPressApi) -> list[tuple[str, str]]:
    """``(kind, plural name)`` for Posts, Pages and the site's own writing types.

    A custom type's kind is its REST base (``events``), which is what
    :func:`kind_route` expects. Posts and Pages always come first.
    """
    found: list[tuple[str, str]] = [("post", "Posts"), ("page", "Pages")]
    found.extend((base, name) for _slug, base, name in writing_types(api))
    return found


def list_items(
    api: WordPressApi,
    kind: str,
    *,
    statuses: Iterable[str] = ("publish", "draft", "pending", "future", "private"),
    search: str = "",
) -> Iterator[ItemSummary]:
    params: dict[str, object] = {
        "context": "edit",
        "status": list(statuses),
        "orderby": "modified",
        "order": "desc",
        "_fields": "id,type,title,status,modified_gmt,link",
    }
    if search.strip():
        params["search"] = search.strip()
    for raw in api.iter_collection(kind_route(kind), params):
        yield ItemSummary(
            id=int(raw.get("id", 0)),
            kind=kind_from_payload(raw, kind),
            title=rendered(raw.get("title")) or "(untitled)",
            status=str(raw.get("status", "")),
            modified_gmt=str(raw.get("modified_gmt", "")),
            link=str(raw.get("link", "")),
        )


def load_item(api: WordPressApi, kind: str, item_id: int) -> Item:
    raw = api.get(f"{kind_route(kind)}/{item_id}", context="edit")
    return item_from_payload(raw, kind)


def item_from_payload(raw: Any, kind: str) -> Item:
    if not isinstance(raw, dict):
        raise WordPressApiError("The site sent back an item QUILL could not read.")
    return Item(
        id=int(raw.get("id", 0)),
        kind=kind_from_payload(raw, kind),
        title=raw_text(raw.get("title")),
        content=raw_text(raw.get("content")),
        status=str(raw.get("status", "draft")),
        slug=str(raw.get("slug", "")),
        excerpt=raw_text(raw.get("excerpt")),
        link=str(raw.get("link", "")),
        modified_gmt=str(raw.get("modified_gmt", "")),
        date_gmt=str(raw.get("date_gmt", "") or ""),
        author=int(raw.get("author", 0) or 0),
        categories=[int(c) for c in raw.get("categories", []) or []],
        tags=[int(t) for t in raw.get("tags", []) or []],
        featured_media=int(raw.get("featured_media", 0) or 0),
        comment_status=str(raw.get("comment_status", "") or ""),
        ping_status=str(raw.get("ping_status", "") or ""),
        sticky=bool(raw.get("sticky", False)),
        password=str(raw.get("password", "") or ""),
        parent=int(raw.get("parent", 0) or 0),
        menu_order=int(raw.get("menu_order", 0) or 0),
        template=str(raw.get("template", "") or ""),
        format=str(raw.get("format", "") or ""),
    )


def create_item(api: WordPressApi, item: Item) -> Item:
    raw = api.post(kind_route(item.kind), item.to_body(), context="edit")
    return item_from_payload(raw, item.kind)


def update_item(api: WordPressApi, item: Item) -> Item:
    raw = api.post(f"{kind_route(item.kind)}/{item.id}", item.to_body(), context="edit")
    return item_from_payload(raw, item.kind)


def trash_item(api: WordPressApi, kind: str, item_id: int) -> Item:
    """WordPress's Trash, never permanent deletion (wordpress.md 5.6)."""
    raw = api.delete(f"{kind_route(kind)}/{item_id}")
    return item_from_payload(raw, kind)


def restore_from_trash(api: WordPressApi, kind: str, item_id: int) -> Item:
    raw = api.post(f"{kind_route(kind)}/{item_id}", {"status": "draft"}, context="edit")
    return item_from_payload(raw, kind)


def modified_gmt(api: WordPressApi, kind: str, item_id: int) -> str:
    """Just the last-changed stamp, for the conflict check (wordpress.md 5.4)."""
    raw = api.get(f"{kind_route(kind)}/{item_id}", context="edit", _fields="modified_gmt")
    return str(raw.get("modified_gmt", "")) if isinstance(raw, dict) else ""


def save_autosave(api: WordPressApi, item: Item) -> None:
    api.post(
        f"{kind_route(item.kind)}/{item.id}/autosaves",
        {"title": item.title, "content": item.content, "excerpt": item.excerpt},
    )


@dataclass(frozen=True)
class Revision:
    id: int
    date_gmt: str
    title: str
    content: str
    author: int
    autosave: bool = False


def list_revisions(api: WordPressApi, kind: str, item_id: int) -> list[Revision]:
    """The site's own history and autosaves, newest first (wordpress.md 5.6, 9.3)."""
    found: list[Revision] = []
    for suffix, is_autosave in (("revisions", False), ("autosaves", True)):
        try:
            rows = api.get(f"{kind_route(kind)}/{item_id}/{suffix}", context="edit")
        except WordPressApiError as exc:
            if exc.status in (401, 403, 404):
                continue
            raise
        for raw in rows if isinstance(rows, list) else []:
            found.append(
                Revision(
                    id=int(raw.get("id", 0)),
                    date_gmt=str(raw.get("modified_gmt") or raw.get("date_gmt") or ""),
                    title=raw_text(raw.get("title")),
                    content=raw_text(raw.get("content")),
                    author=int(raw.get("author", 0) or 0),
                    autosave=is_autosave,
                )
            )
    return sorted(found, key=lambda r: r.date_gmt, reverse=True)


# --------------------------------------------------------------------------- #
# The account: who you are and what you may do (wordpress.md 9.2)


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    username: str
    roles: tuple[str, ...]
    capabilities: frozenset[str]

    def can(self, capability: str) -> bool:
        return capability in self.capabilities

    @property
    def role_name(self) -> str:
        if not self.roles:
            return "no role"
        return self.roles[0].replace("_", " ").title()

    @property
    def can_publish_posts(self) -> bool:
        return self.can("publish_posts")

    @property
    def can_publish_pages(self) -> bool:
        return self.can("publish_pages")

    @property
    def can_upload(self) -> bool:
        return self.can("upload_files")

    @property
    def can_manage_options(self) -> bool:
        return self.can("manage_options")

    @property
    def can_moderate(self) -> bool:
        return self.can("moderate_comments")

    @property
    def can_manage_categories(self) -> bool:
        return self.can("manage_categories")

    @property
    def can_manage_users(self) -> bool:
        return self.can("list_users")

    @property
    def can_manage_plugins(self) -> bool:
        return self.can("activate_plugins")

    def publish_label(self, kind: str) -> str:
        """What Publish becomes for this account (a Contributor submits for review)."""
        allowed = self.can_publish_pages if kind == "page" else self.can_publish_posts
        return "Publish or Update" if allowed else "Submit for Review"


def load_account(api: WordPressApi) -> Account:
    raw = api.get("wp/v2/users/me", context="edit")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not say who this account is.")
    caps = raw.get("capabilities", {}) or {}
    return Account(
        id=int(raw.get("id", 0)),
        name=str(raw.get("name", "")),
        username=str(raw.get("username", "") or raw.get("slug", "")),
        roles=tuple(str(r) for r in raw.get("roles", []) or []),
        capabilities=frozenset(k for k, v in caps.items() if v)
        if isinstance(caps, dict)
        else frozenset(),
    )


@dataclass(frozen=True)
class SiteInfo:
    name: str
    description: str
    url: str
    wp_version: str
    namespaces: tuple[str, ...]
    authorize_url: str
    routes: tuple[str, ...] = ()

    def supports(self, namespace: str) -> bool:
        """Whether the site offers *namespace* (``wp/v2``) or route (``batch/v1``).

        Both are checked because WordPress registers some endpoints as a bare
        route rather than a namespace: ``/batch/v1`` is in the index's
        ``routes`` and never in ``namespaces`` (found on a live 7.1 site), so a
        namespace-only check would say a batch-capable site cannot batch.
        """
        clean = namespace.strip("/")
        return clean in self.namespaces or f"/{clean}" in self.routes


def load_site_info(api: WordPressApi) -> SiteInfo:
    """The REST index: the site's name, its routes, and the authorize URL."""
    raw = api.get("")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not describe itself. The REST API may be turned off.")
    auth = raw.get("authentication", {}) if isinstance(raw.get("authentication"), dict) else {}
    app_pw = auth.get("application-passwords", {}) if isinstance(auth, dict) else {}
    endpoints = app_pw.get("endpoints", {}) if isinstance(app_pw, dict) else {}
    generator = str(raw.get("generator", "") or "")
    version_match = re.search(r"\?v=([\d.]+)", generator)
    home = str(raw.get("home", "") or raw.get("url", ""))
    version = version_match.group(1) if version_match else ""
    if not version and home:
        # WordPress 7.1's REST index carries no generator (seen on the live test
        # site), but the feed still says the version. Without it QUILL cannot
        # tell the site takes the automatic password handback (4.2, tier 1).
        version = feed_version(api, home)
    return SiteInfo(
        name=html.unescape(str(raw.get("name", "") or "")),
        description=html.unescape(str(raw.get("description", "") or "")),
        url=home,
        wp_version=version,
        namespaces=tuple(str(n) for n in raw.get("namespaces", []) or []),
        authorize_url=str(
            endpoints.get("authorization", "") if isinstance(endpoints, dict) else ""
        ),
        routes=tuple(str(r) for r in (raw.get("routes") or {}))
        if isinstance(raw.get("routes"), dict)
        else (),
    )


def feed_version(api: WordPressApi, home: str) -> str:
    """The WordPress version from the site's feed ``<generator>``; "" if hidden.

    Read with the site's own signed opener, so the same HTTPS rules apply. A
    security plugin may remove the generator, in which case QUILL simply falls
    back to the paste route rather than guessing.
    """
    from urllib.request import Request

    url = home.rstrip("/") + "/?feed=rss2"
    try:
        with api._opener(
            Request(url, headers={"User-Agent": "QUILL"}), timeout=api.timeout
        ) as response:
            text = response.read(65536).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - no version is an answer, not a failure
        return ""
    match = re.search(r"wordpress\.org/\?v=([\d.]+)", text)
    return match.group(1) if match else ""


# --------------------------------------------------------------------------- #
# Categories, tags and other taxonomies (wordpress.md 5.5, 9.13)


@dataclass(frozen=True)
class Term:
    id: int
    taxonomy: str
    name: str
    slug: str
    count: int
    parent: int = 0
    description: str = ""


def taxonomy_route(taxonomy: str) -> str:
    return {"category": "wp/v2/categories", "post_tag": "wp/v2/tags"}.get(
        taxonomy, f"wp/v2/{taxonomy}"
    )


def list_terms(api: WordPressApi, taxonomy: str, *, search: str = "") -> list[Term]:
    params: dict[str, object] = {"context": "edit", "orderby": "name", "hide_empty": False}
    if search.strip():
        params["search"] = search.strip()
    return [_term(raw, taxonomy) for raw in api.iter_collection(taxonomy_route(taxonomy), params)]


def create_term(
    api: WordPressApi,
    taxonomy: str,
    name: str,
    *,
    slug: str = "",
    parent: int = 0,
    description: str = "",
) -> Term:
    body: dict[str, object] = {"name": name}
    if slug:
        body["slug"] = slug
    if parent:
        body["parent"] = parent
    if description:
        body["description"] = description
    return _term(api.post(taxonomy_route(taxonomy), body), taxonomy)


def update_term(api: WordPressApi, term: Term) -> Term:
    body: dict[str, object] = {
        "name": term.name,
        "slug": term.slug,
        "description": term.description,
    }
    if term.taxonomy == "category":
        body["parent"] = term.parent
    return _term(api.post(f"{taxonomy_route(term.taxonomy)}/{term.id}", body), term.taxonomy)


def delete_term(api: WordPressApi, taxonomy: str, term_id: int) -> None:
    # Terms have no Trash; WordPress insists on force=true.
    api.delete(f"{taxonomy_route(taxonomy)}/{term_id}", force=True)


def merge_terms(api: WordPressApi, taxonomy: str, source: int, target: int) -> int:
    """Move every post from *source* to *target*, then delete *source*.

    The API has no merge, so this is one batch of post updates and a delete.
    Returns how many posts moved (wordpress.md 9.13).
    """
    field_name = (
        "categories" if taxonomy == "category" else "tags" if taxonomy == "post_tag" else taxonomy
    )
    requests: list[dict[str, Any]] = []
    for raw in api.iter_collection(
        "wp/v2/posts",
        {"context": "edit", "status": "any", field_name: source, "_fields": f"id,{field_name}"},
    ):
        terms = [int(t) for t in raw.get(field_name, []) or []]
        moved = [target if t == source else t for t in terms]
        requests.append({
            "method": "POST",
            "path": f"/wp/v2/posts/{int(raw['id'])}",
            "body": {field_name: sorted(set(moved))},
        })
    if requests:
        api.batch(requests)
    delete_term(api, taxonomy, source)
    return len(requests)


def _term(raw: Any, taxonomy: str) -> Term:
    return Term(
        id=int(raw.get("id", 0)),
        taxonomy=str(raw.get("taxonomy", taxonomy) or taxonomy),
        name=html.unescape(str(raw.get("name", ""))),
        slug=str(raw.get("slug", "")),
        count=int(raw.get("count", 0) or 0),
        parent=int(raw.get("parent", 0) or 0),
        description=str(raw.get("description", "") or ""),
    )


# --------------------------------------------------------------------------- #
# Text helpers


def raw_text(value: Any) -> str:
    """The editable form of a WordPress field: ``raw`` when edit context gave it."""
    if isinstance(value, dict):
        if "raw" in value and value["raw"] is not None:
            return str(value["raw"])
        return html.unescape(str(value.get("rendered", "") or ""))
    return "" if value is None else str(value)


def rendered(value: Any) -> str:
    if isinstance(value, dict):
        text = value.get("rendered") if value.get("rendered") is not None else value.get("raw", "")
        return html.unescape(plain_text(str(text or "")))
    return "" if value is None else html.unescape(str(value))


def plain_text(markup: str) -> str:
    no_comments = re.sub(r"<!--.*?-->", "", markup, flags=re.S)
    no_tags = re.sub(r"<[^>]+>", " ", no_comments)
    return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()


def friendly_date(stamp: str) -> str:
    """``2026-11-03T16:12:00`` -> ``3 November 2026, 4:12 PM`` (UTC as given)."""
    from datetime import datetime

    if not stamp:
        return "at an unknown time"
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", ""))
    except ValueError:
        return stamp
    hour = moment.hour % 12 or 12
    suffix = "AM" if moment.hour < 12 else "PM"
    return f"{moment.day} {moment.strftime('%B %Y')}, {hour}:{moment.minute:02d} {suffix}"


def human_size(size: int) -> str:
    if size < 1024:
        return f"{size} bytes"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def slugify(title: str) -> str:
    """The slug WordPress would suggest for *title* (wordpress.md 5.1)."""
    import unicodedata

    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", text).strip("-")
