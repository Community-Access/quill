"""Copy to Site (PRD 15.2; W7): the selection to another connected site.

Posts, pages, custom types, pictures and files, menus, categories, tags and
custom terms, QUILL Accessible Forms and patterns go to another connected
site. :func:`plan_copy` is the preview, asked of the target (and, for
authors, featured images and menu links, of the source): one line per create,
replace and skip, each saying why.

- **Matching:** by address (slug) first, checked exactly, because a site that
  ignores a ``slug`` query answers with everything; terms and menus fall back
  to their name. A match is replaced; anything else is made.
- **Replace keeps the target's status:** copying a draft over a published
  page never takes the page down. New items arrive as drafts.
- **Authors** are matched on the target by username, then display name. A
  writer with no account there is named in the preview, and the copy belongs
  to the person copying.
- **Pictures and files:** a copied picture or file is uploaded with its alt
  text, caption and title; a picture already on the target (same address) is
  reused rather than uploaded twice; pictures in the content and the
  featured image are uploaded and pointed at.
- **Links:** every link to the source site, in either scheme and in block
  attributes (where slashes are escaped), is pointed at the target.
- **Menus** travel with their links in order and nesting; a link to a post,
  page or term the target lacks becomes a plain link, and the preview says
  replacing a menu replaces its links there.
- **Order:** terms and files are copied before what uses them, and a term the
  target already has is reused, "already there" (``workbench_site_copy_order``).
- **Gravity Forms forms** are read whole from ``gf/v2/forms/<id>`` and made on
  the target (``POST gf/v2/forms``), or replace the target's form of the same
  title (``PUT``). Entries are never copied -- not read, not sent -- and a
  replaced form keeps its own entries there; the preview says both.

Wx-free; the Workbench runs it off the UI thread.
"""

from __future__ import annotations

import mimetypes
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route, raw_text, rendered
from quill.core.wordpress.workbench_site_copy_order import ALREADY_THERE, ordered, term_id

__all__ = [
    "COPYABLE",
    "CopyLine",
    "CopyPlan",
    "fetch_site_file",
    "plan_copy",
    "rewrite_links",
    "run_copy",
]

COPYABLE = frozenset({"item", "term", "pattern", "media", "menu", "form", "gravity_form"})
GRAVITY_DROP = frozenset({"id", "date_created", "date_updated", "is_trash", "entries", "_links"})
"""Row kinds Copy to Site takes."""

_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
_FILE = "picture or file"


def fetch_site_file(api: WordPressApi, url: str) -> bytes:
    """A file from the connected site itself (a picture to copy); never another host."""
    from urllib.request import Request

    from quill.core.wordpress import api as wpapi

    site = urlparse(api.address.site_url).hostname or ""
    if (urlparse(url).hostname or "") != site:
        raise WordPressApiError(f"{url} is not on {api.site_name}, so it is not read.")
    request = Request(url, method="GET")
    with api._opener(request, timeout=max(api.timeout, 60.0), context=wpapi._context(url)) as r:
        return bytes(r.read())


def rewrite_links(text: str, source_url: str, target_url: str) -> str:
    """Every link to *source_url* in *text* pointed at *target_url* instead.

    Both schemes of the source address are rewritten, and so is the escaped
    form (``https:\\/\\/``) that block attributes use.
    """
    source = source_url.rstrip("/")
    target = target_url.rstrip("/")
    if not source or source == target or not text:
        return text
    rest = source.split("://", 1)[-1]
    for scheme in ("https", "http"):
        plain = f"{scheme}://{rest}"
        text = text.replace(plain, target)
        text = text.replace(plain.replace("/", "\\/"), target.replace("/", "\\/"))
    return text


@dataclass(frozen=True)
class CopyLine:
    """One thing Copy to Site will do."""

    action: str  # "create", "replace" or "skip"
    kind: str
    title: str
    why: str = ""
    target_id: int = 0
    source: Mapping[str, Any] = field(default_factory=dict)
    subkind: str = ""

    @property
    def sentence(self) -> str:
        said = {"create": "Make", "replace": "Replace", "skip": "Skip"}[self.action]
        return f"{said} {self.kind} {self.title}" + (f": {self.why}" if self.why else ".")


@dataclass
class CopyPlan:
    source_site: str
    target_site: str
    lines: list[CopyLine]
    pictures: list[str] = field(default_factory=list)
    #: Source author id -> target author id (0: the person copying owns it).
    authors: dict[int, int] = field(default_factory=dict)
    #: Source media id -> its address, for featured images.
    featured: dict[int, str] = field(default_factory=dict)
    #: Source file address -> the target's own copy, already there.
    reuse: dict[str, str] = field(default_factory=dict)
    #: One sentence per line done, filled by :func:`run_copy`.
    outcomes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        made = sum(1 for line in self.lines if line.action == "create")
        replaced = sum(1 for line in self.lines if line.action == "replace")
        skipped = sum(1 for line in self.lines if line.action == "skip")
        pics = f", and {len(self.pictures)} pictures uploaded" if self.pictures else ""
        return (
            f"Copy from {self.source_site} to {self.target_site}: {made} made, {replaced} "
            f"replaced, {skipped} skipped{pics}. New items are drafts; a replaced item keeps "
            f"its status on {self.target_site}. Links to {self.source_site} are pointed at "
            f"{self.target_site}."
        )


def _route_for(kind: str, subkind: str, raw: Mapping[str, Any]) -> str:
    if kind == "item":
        return kind_route(subkind or str(raw.get("type", "post")))
    if kind == "pattern":
        return "wp/v2/blocks"
    if kind == "term":
        taxonomy = subkind or str(raw.get("taxonomy", "") or "category")
        return {"category": "wp/v2/categories", "post_tag": "wp/v2/tags"}.get(
            taxonomy, kind_route(taxonomy)
        )
    if kind == "menu":
        return "wp/v2/menus"
    if kind == "form":
        return "qaf/v1/forms"
    if kind == "gravity_form":
        return "gf/v2/forms"
    return "wp/v2/media"


def _title(raw: Mapping[str, Any]) -> str:
    return (
        raw_text(raw.get("title"))
        or rendered(raw.get("title"))
        or str(raw.get("name", "") or raw.get("slug", "") or raw.get("id", ""))
    )


def _content(raw: Mapping[str, Any]) -> str:
    value = raw.get("content")
    if isinstance(value, dict):
        return str(value.get("raw") or value.get("rendered") or "")
    return "" if value is None else str(value)


def _listed(found: Any) -> list[Mapping[str, Any]]:
    return [f for f in found if isinstance(f, dict)] if isinstance(found, list) else []


def _existing(
    target: WordPressApi, route: str, kind: str, raw: Mapping[str, Any]
) -> tuple[Mapping[str, Any] | None, str]:
    """The target's match for *raw* and how it matched ("address", "name" or "title")."""
    if kind == "gravity_form":
        title = str(raw.get("title", "") or "").casefold()
        try:
            found = target.get(route)
        except WordPressApiError:
            return None, ""
        forms = _listed(list(found.values()) if isinstance(found, dict) else found)
        match = next((f for f in forms if str(f.get("title", "")).casefold() == title), None)
        return (match, "title") if match is not None else (None, "")
    slug = str(raw.get("slug", "") or "")
    if slug:
        params: dict[str, object] = {"slug": slug, "context": "edit"}
        if kind in ("item", "pattern"):
            params["status"] = "any"
        try:
            found = _listed(target.get(route, **params))
        except WordPressApiError:
            found = []
        match = next((f for f in found if str(f.get("slug", "")) == slug), None)
        if match is not None:
            return match, "address"
    name = str(raw.get("name", "") or "")
    if kind in ("term", "menu") and name:
        try:
            found = _listed(target.get(route, search=name))
        except WordPressApiError:
            found = []
        match = next(
            (f for f in found if str(f.get("name", "")).casefold() == name.casefold()), None
        )
        if match is not None:
            return match, "name"
    return None, ""


def _person(api: WordPressApi, ident: int) -> Mapping[str, Any]:
    try:
        found = api.get(f"wp/v2/users/{ident}", context="edit")
    except WordPressApiError:
        try:
            found = api.get(f"wp/v2/users/{ident}")
        except WordPressApiError:
            return {}
    return found if isinstance(found, dict) else {}


def _target_author(target: WordPressApi, person: Mapping[str, Any]) -> int:
    username = str(person.get("username", "") or person.get("slug", "") or "")
    name = str(person.get("name", "") or "")
    for query in (username, name):
        if not query:
            continue
        try:
            found = _listed(target.get("wp/v2/users", search=query, context="edit"))
        except WordPressApiError:
            continue
        for there in found:
            same_user = username and username in (
                str(there.get("username", "")),
                str(there.get("slug", "")),
            )
            if same_user or (name and str(there.get("name", "")).casefold() == name.casefold()):
                return int(there.get("id", 0) or 0)
    return 0


def _plan_author(
    source: WordPressApi, target: WordPressApi, plan: CopyPlan, raw: Mapping[str, Any]
) -> str:
    ident = int(raw.get("author", 0) or 0)
    if not ident:
        return ""
    person = _person(source, ident)
    if ident not in plan.authors:
        plan.authors[ident] = _target_author(target, person) if person else 0
    name = str(person.get("name", "") or f"author {ident}")
    if plan.authors[ident]:
        return f"by {name}, who has an account there"
    return f"{name} has no account on {plan.target_site}, so the copy will be yours"


def plan_copy(
    target: WordPressApi,
    rows: Sequence[tuple[str, str, Mapping[str, Any]]],
    *,
    source_site: str,
    target_site: str,
    source_url: str,
    source: WordPressApi | None = None,
) -> CopyPlan:
    """What copying *rows* ((kind, subkind, raw)) to *target* will do. Reads only."""
    plan = CopyPlan(source_site, target_site, [])
    base = source_url.rstrip("/")
    for kind, subkind, raw in rows:
        title = _title(raw)
        if kind not in COPYABLE:
            plan.lines.append(
                CopyLine("skip", kind, title, "this kind does not copy between sites")
            )
            continue
        route = _route_for(kind, subkind, raw)
        match, how = _existing(target, route, kind, raw)
        if kind == "media":
            url = str(raw.get("source_url", "") or "")
            if match is not None:
                there = str(match.get("source_url", "") or "")
                if url and there:
                    plan.reuse[url] = there
                why = f"{target_site} has it already, so the copy uses theirs"
                plan.lines.append(CopyLine("skip", _FILE, title, why, int(match.get("id", 0))))
            else:
                why = "uploaded with its alt text, caption and title"
                plan.lines.append(CopyLine("create", _FILE, title, why, source=raw))
            continue
        notes: list[str] = []
        if kind == "item" and source is not None:
            said = _plan_author(source, target, plan, raw)
            if said:
                notes.append(said)
            featured = int(raw.get("featured_media", 0) or 0)
            if featured:
                media = _person_media(source, featured)
                if media:
                    plan.featured[featured] = media
                    if media not in plan.pictures:
                        plan.pictures.append(media)
                    notes.append("its featured image uploaded")
        if kind == "menu" and source is not None:
            count = len(_menu_items(source, int(raw.get("id", 0) or 0)))
            notes.append(f"with its {count} links")
        if kind == "gravity_form":
            notes.append("its fields, confirmations and notifications; never its entries")
        if match is not None:
            lead = f"{target_site} has one with the same {how}"
            lead += {
                "menu": "; its links there are replaced",
                "gravity_form": "; its entries there are kept",
            }.get(kind, ", whose status is kept")
            why = "; ".join([lead, *notes])
            ident = int(match.get("id", 0) or 0)
            plan.lines.append(CopyLine("replace", kind, title, why, ident, raw, subkind))
        else:
            lead = "as a draft" if kind in ("item",) else ""
            why = "; ".join(n for n in [lead, *notes] if n)
            plan.lines.append(CopyLine("create", kind, title, why, source=raw, subkind=subkind))
        for src in _IMG.findall(_content(raw)):
            if base and src.startswith(base) and src not in plan.pictures:
                plan.pictures.append(src)
    return plan


def _person_media(api: WordPressApi, ident: int) -> str:
    try:
        found = api.get(f"wp/v2/media/{ident}", _fields="id,source_url")
    except WordPressApiError:
        return ""
    return str(found.get("source_url", "") or "") if isinstance(found, dict) else ""


def _menu_items(api: WordPressApi, menu_id: int) -> list[dict[str, Any]]:
    if not menu_id:
        return []
    try:
        items = list(
            api.iter_collection(
                "wp/v2/menu-items", {"menus": menu_id, "context": "edit"}, per_page=100
            )
        )
    except WordPressApiError:
        return []
    return sorted(items, key=lambda i: int(i.get("menu_order", 0) or 0))


def _term_ids_by_name(
    source: WordPressApi, target: WordPressApi, route: str, ids: Iterable[int]
) -> list[int]:
    found: list[int] = []
    for ident in ids:
        try:
            term = source.get(f"{route}/{int(ident)}", _fields="id,name,slug")
        except WordPressApiError:
            continue
        name = str(term.get("name", "")) if isinstance(term, dict) else ""
        made = (
            term_id(target, route, {"name": name, "slug": term.get("slug", "")})[0] if name else 0
        )
        if made:
            found.append(made)
    return found


def _upload(
    target: WordPressApi, url: str, fetch: Callable[[str], bytes], extra: Mapping[str, Any]
) -> tuple[str, int]:
    data = fetch(url)
    name = url.rsplit("/", 1)[-1].split("?", 1)[0] or "picture"
    kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
    made = target.upload("wp/v2/media", name, data, kind)
    made = made if isinstance(made, dict) else {}
    ident = int(made.get("id", 0) or 0)
    fields = {k: v for k, v in extra.items() if v}
    if ident and fields:
        target.post(f"wp/v2/media/{ident}", fields)
    return str(made.get("source_url", "") or ""), ident


def run_copy(
    source: WordPressApi,
    target: WordPressApi,
    plan: CopyPlan,
    *,
    source_url: str,
    target_url: str,
    fetch: Callable[[str], bytes] | None = None,
) -> list[str]:
    """Do *plan*; return a sentence for each thing that could not be copied.

    :attr:`CopyPlan.outcomes` gets one sentence per line, done or not.
    """
    failed: list[str] = []
    moved: dict[str, str] = dict(plan.reuse)
    ids: dict[str, int] = {}
    for url in plan.pictures:
        if fetch is None:
            failed.append(f"the picture {url} (no way to read it here)")
            continue
        try:
            new, ident = _upload(target, url, fetch, {})
            if new:
                moved[url] = new
                ids[url] = ident
        except Exception as exc:  # noqa: BLE001 - one picture must not stop the rest
            failed.append(f"the picture {url}: {exc}")
    for line in ordered(plan.lines):  # terms and files before the items that use them
        if line.action == "skip":
            plan.outcomes.append(f"Skipped {line.kind} {line.title}.")
            continue
        try:
            said = _copy_one(source, target, plan, line, source_url, target_url, moved, ids, fetch)
            done = said or ("Made" if line.action == "create" else "Replaced")
            plan.outcomes.append(f"{done} {line.kind} {line.title}.")
        except Exception as exc:  # noqa: BLE001 - one item must not stop the rest
            said = f"{line.title}: {getattr(exc, 'plain', '') or exc}"
            failed.append(said)
            plan.outcomes.append(f"Not copied: {said}")
    return failed


def _copy_one(
    source: WordPressApi,
    target: WordPressApi,
    plan: CopyPlan,
    line: CopyLine,
    source_url: str,
    target_url: str,
    moved: dict[str, str],
    ids: dict[str, int],
    fetch: Callable[[str], bytes] | None,
) -> str:
    """Copy one line; "" when done as planned, or ALREADY_THERE for a term found there."""
    raw = line.source
    if line.kind == _FILE:
        url = str(raw.get("source_url", "") or "")
        if url in moved:
            return ""
        if fetch is None or not url:
            raise WordPressApiError("there is no way to read the file here")
        extra = {
            "alt_text": str(raw.get("alt_text", "") or ""),
            "caption": raw_text(raw.get("caption")),
            "title": _title(raw),
            "description": raw_text(raw.get("description")),
        }
        moved[url], ids[url] = _upload(target, url, fetch, extra)
        return ""
    route = _route_for(line.kind, line.subkind, raw)
    if line.kind == "item":
        content = _content(raw)
        for old, new in moved.items():
            content = content.replace(old, new)
        body: dict[str, Any] = {
            "title": _title(raw),
            "content": rewrite_links(content, source_url, target_url),
            "excerpt": raw_text(raw.get("excerpt")),
            "slug": str(raw.get("slug", "") or ""),
        }
        if line.action == "create":
            body["status"] = "draft"
        author = plan.authors.get(int(raw.get("author", 0) or 0), 0)
        if author:
            body["author"] = author
        featured = plan.featured.get(int(raw.get("featured_media", 0) or 0), "")
        if featured and ids.get(featured):
            body["featured_media"] = ids[featured]
        for base in ("categories", "tags"):
            listed = raw.get(base)
            if isinstance(listed, list) and listed:
                body[base] = _term_ids_by_name(source, target, f"wp/v2/{base}", listed)
    elif line.kind == "term":
        body = {
            "name": str(raw.get("name", "")),
            "slug": str(raw.get("slug", "") or ""),
            "description": str(raw.get("description", "") or ""),
        }
        if line.action == "create":  # an earlier line may have made it: reuse, never fail
            return ALREADY_THERE if term_id(target, route, body)[1] else ""
    elif line.kind == "pattern":
        body = {
            "title": _title(raw),
            "content": rewrite_links(_content(raw), source_url, target_url),
            "status": "publish",
        }
    elif line.kind == "menu":
        body = {"name": str(raw.get("name", "")), "description": str(raw.get("description", ""))}
    elif line.kind == "gravity_form":
        _copy_gravity_form(source, target, line, raw, source_url, target_url)
        return ""
    else:  # a QAF form travels whole, as its JSON definition
        body = {k: v for k, v in raw.items() if k not in ("id", "_links")}
    if line.action == "replace" and line.target_id:
        answer = target.post(f"{route}/{line.target_id}", body)
    else:
        answer = target.post(route, body)
    if line.kind == "menu":
        made = int(answer.get("id", 0) or 0) if isinstance(answer, dict) else 0
        _copy_menu_links(source, target, raw, made or line.target_id, line, source_url, target_url)
    return ""


def _copy_gravity_form(
    source: WordPressApi,
    target: WordPressApi,
    line: CopyLine,
    raw: Mapping[str, Any],
    source_url: str,
    target_url: str,
) -> None:
    """The whole form from the source, without its entries, to the target."""
    import json

    whole = source.get(f"gf/v2/forms/{int(raw.get('id', 0) or 0)}")
    if not isinstance(whole, dict) or not whole:
        raise WordPressApiError("the source site did not give the whole form")
    form = {k: v for k, v in whole.items() if k not in GRAVITY_DROP}
    text = rewrite_links(json.dumps(form), source_url, target_url)
    body = json.loads(text)
    if line.action == "replace" and line.target_id:
        target.request(
            "PUT", f"gf/v2/forms/{line.target_id}", json_body={**body, "id": line.target_id}
        )
    else:
        target.post("gf/v2/forms", body)


def _copy_menu_links(
    source: WordPressApi,
    target: WordPressApi,
    raw: Mapping[str, Any],
    menu_id: int,
    line: CopyLine,
    source_url: str,
    target_url: str,
) -> None:
    if not menu_id:
        return
    if line.action == "replace":
        for old in _menu_items(target, menu_id):
            target.delete(f"wp/v2/menu-items/{int(old.get('id', 0))}", force=True)
    made: dict[int, int] = {}
    for item in _menu_items(source, int(raw.get("id", 0) or 0)):
        body: dict[str, Any] = {
            "title": _title(item),
            "menus": menu_id,
            "menu_order": int(item.get("menu_order", 0) or 0),
            "status": "publish",
            "parent": made.get(int(item.get("parent", 0) or 0), 0),
        }
        there = _menu_object(source, target, item)
        if there:
            body.update({
                "type": item.get("type"),
                "object": item.get("object"),
                "object_id": there,
            })
        else:
            body.update({
                "type": "custom",
                "url": rewrite_links(str(item.get("url", "") or ""), source_url, target_url),
            })
        answer = target.post("wp/v2/menu-items", body)
        if isinstance(answer, dict):
            made[int(item.get("id", 0) or 0)] = int(answer.get("id", 0) or 0)


def _menu_object(source: WordPressApi, target: WordPressApi, item: Mapping[str, Any]) -> int:
    """The target's id for what a menu link points at, matched by address; 0 if none."""
    kind = str(item.get("type", "") or "")
    obj = str(item.get("object", "") or "")
    ident = int(item.get("object_id", 0) or 0)
    if kind not in ("post_type", "taxonomy") or not obj or not ident:
        return 0
    route = kind_route(obj) if kind == "post_type" else _route_for("term", obj, {})
    try:
        mine = source.get(f"{route}/{ident}", _fields="id,slug")
    except WordPressApiError:
        return 0
    slug = str(mine.get("slug", "") or "") if isinstance(mine, dict) else ""
    match, _how = _existing(
        target, route, "item" if kind == "post_type" else "term", {"slug": slug}
    )
    return int(match.get("id", 0) or 0) if match is not None else 0
