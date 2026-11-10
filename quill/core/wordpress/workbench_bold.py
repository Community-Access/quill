"""Site to site, a local snapshot, the calendar, Read Site as Document (PRD 15.2 to 15.5; W7).

Wx-free functions over each site's own client, which the Workbench calls
off the UI thread:

- **Copy to Site** (:func:`plan_copy`, :func:`run_copy`): posts, pages,
  terms and patterns to another connected site, each matched there by slug
  (replace) or made (create); terms matched by name or made, the author
  mapped by name or left to the person copying, links to the source site
  rewritten to the target's address, and pictures in the content uploaded to
  the target, so nothing points back at the old site. The plan is the
  preview: one line per create, replace and skip.
- **Compare Sites** (:func:`compare_sites`): what differs between two sites,
  by kind and slug, read as a list.
- **Take a Snapshot** (:func:`take_snapshot`): every post, page, term, menu
  and setting to a folder on this computer, so a bad batch can be put back
  after revisions are trimmed. Media files stay on the site unless asked.
- **The calendar** (:func:`calendar_days`): each day with scheduled and
  published content, across every site, "Tuesday 12 November: 2 scheduled,
  1 published".
- **Read Site as Document** (:func:`site_document`): the pages as one
  Markdown document, a heading per page in menu or page order, each with its
  address, for the editor's own Word, EPUB and DAISY exports.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.storage import write_json_atomic
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route, raw_text, rendered

__all__ = [
    "COPYABLE",
    "CopyLine",
    "CopyPlan",
    "Difference",
    "calendar_days",
    "compare_sites",
    "day_words",
    "fetch_site_file",
    "plan_copy",
    "rewrite_links",
    "run_copy",
    "site_document",
    "take_snapshot",
]

COPYABLE = frozenset({"item", "term", "pattern", "media", "menu", "form"})
"""Row kinds Copy to Site takes."""

_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def fetch_site_file(api: WordPressApi, url: str) -> bytes:
    """A file from the connected site itself (a picture to copy); never another host."""
    from urllib.parse import urlparse
    from urllib.request import Request

    from quill.core.wordpress import api as wpapi

    site = urlparse(api.address.site_url).hostname or ""
    if (urlparse(url).hostname or "") != site:
        raise WordPressApiError(f"{url} is not on {api.site_name}, so it is not read.")
    request = Request(url, method="GET")
    with api._opener(request, timeout=max(api.timeout, 60.0), context=wpapi._context(url)) as r:
        return bytes(r.read())


def rewrite_links(text: str, source_url: str, target_url: str) -> str:
    """Every link to *source_url* in *text* pointed at *target_url* instead."""
    source = source_url.rstrip("/")
    target = target_url.rstrip("/")
    if not source or source == target:
        return text
    return text.replace(source, target)


@dataclass(frozen=True)
class CopyLine:
    """One thing Copy to Site will do."""

    action: str  # "create", "replace" or "skip"
    kind: str
    title: str
    why: str = ""
    target_id: int = 0
    source: Mapping[str, Any] = field(default_factory=dict)

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

    @property
    def summary(self) -> str:
        made = sum(1 for line in self.lines if line.action == "create")
        replaced = sum(1 for line in self.lines if line.action == "replace")
        skipped = sum(1 for line in self.lines if line.action == "skip")
        pics = f", and {len(self.pictures)} pictures uploaded" if self.pictures else ""
        return (
            f"Copy from {self.source_site} to {self.target_site}: {made} made, {replaced} "
            f"replaced, {skipped} skipped{pics}. Links to {self.source_site} are pointed at "
            f"{self.target_site}."
        )


def _route_for(kind: str, subkind: str, raw: Mapping[str, Any]) -> str:
    if kind == "item":
        return kind_route(subkind or str(raw.get("type", "post")))
    if kind == "pattern":
        return "wp/v2/blocks"
    if kind == "term":
        return {"category": "wp/v2/categories", "post_tag": "wp/v2/tags"}.get(
            subkind, f"wp/v2/{subkind}"
        )
    if kind == "menu":
        return "wp/v2/menus"
    if kind == "form":
        return "qaf/v1/forms"
    return "wp/v2/media"


def _title(raw: Mapping[str, Any]) -> str:
    return (
        raw_text(raw.get("title"))
        or rendered(raw.get("title"))
        or str(raw.get("name", "") or raw.get("slug", "") or raw.get("id", ""))
    )


def plan_copy(
    target: WordPressApi,
    rows: Sequence[tuple[str, str, Mapping[str, Any]]],
    *,
    source_site: str,
    target_site: str,
    source_url: str,
) -> CopyPlan:
    """What copying *rows* ((kind, subkind, raw)) to *target* will do, asked of *target* only."""
    lines: list[CopyLine] = []
    pictures: list[str] = []
    for kind, subkind, raw in rows:
        title = _title(raw)
        if kind not in COPYABLE:
            lines.append(CopyLine("skip", kind, title, "this kind does not copy between sites"))
            continue
        if kind == "media":
            lines.append(CopyLine("create", "picture or file", title, source=raw))
            continue
        slug = str(raw.get("slug", "") or "")
        route = _route_for(kind, subkind, raw)
        existing: list[Any] = []
        if slug:
            try:
                found = target.get(route, slug=slug, context="edit", status="any")
                existing = found if isinstance(found, list) else []
            except WordPressApiError:
                existing = []
        if existing:
            target_id = int(existing[0].get("id", 0) or 0)
            lines.append(
                CopyLine("replace", kind, title, f"{target_site} has it already", target_id, raw)
            )
        else:
            lines.append(CopyLine("create", kind, title, source=raw))
        content = raw_text(raw.get("content")) or rendered(raw.get("content"))
        for src in _IMG.findall(content or ""):
            if src.startswith(source_url.rstrip("/")) and src not in pictures:
                pictures.append(src)
    return CopyPlan(source_site, target_site, lines, pictures)


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
        if not name:
            continue
        there = target.get(route, search=name, _fields="id,name")
        match = next(
            (t for t in there or [] if str(t.get("name", "")).casefold() == name.casefold()), None
        )
        if match is None:
            made = target.post(route, {"name": name, "slug": str(term.get("slug", "") or "")})
            match = made if isinstance(made, dict) else None
        if match is not None:
            found.append(int(match.get("id", 0) or 0))
    return found


def _upload_picture(
    source: WordPressApi, target: WordPressApi, url: str, fetch: Callable[[str], bytes]
) -> str:
    import mimetypes

    data = fetch(url)
    name = url.rsplit("/", 1)[-1].split("?", 1)[0] or "picture"
    kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
    made = target.upload("wp/v2/media", name, data, kind)
    return str(made.get("source_url", "") if isinstance(made, dict) else "")


def run_copy(
    source: WordPressApi,
    target: WordPressApi,
    plan: CopyPlan,
    *,
    source_url: str,
    target_url: str,
    fetch: Callable[[str], bytes] | None = None,
) -> list[str]:
    """Do *plan*; return a sentence for each thing that could not be copied."""
    failed: list[str] = []
    moved: dict[str, str] = {}
    for url in plan.pictures:
        if fetch is None:
            failed.append(f"the picture {url} (no way to read it here)")
            continue
        try:
            new = _upload_picture(source, target, url, fetch)
            if new:
                moved[url] = new
        except Exception as exc:  # noqa: BLE001 - one picture must not stop the rest
            failed.append(f"the picture {url}: {exc}")
    for line in plan.lines:
        if line.action == "skip":
            continue
        raw = line.source
        try:
            _copy_one(source, target, line, raw, source_url, target_url, moved)
        except Exception as exc:  # noqa: BLE001 - one item must not stop the rest
            failed.append(f"{line.title}: {getattr(exc, 'plain', '') or exc}")
    return failed


def _copy_one(
    source: WordPressApi,
    target: WordPressApi,
    line: CopyLine,
    raw: Mapping[str, Any],
    source_url: str,
    target_url: str,
    moved: Mapping[str, str],
) -> None:
    kind = line.kind
    if kind == "picture or file":
        url = str(raw.get("source_url", "") or "")
        if url in moved:
            return
        raise WordPressApiError("pictures and files copy with the item that uses them")
    route = _route_for(kind, str(raw.get("taxonomy", "") or ""), raw)
    if kind == "item":
        route = kind_route(str(raw.get("type", "post")))
        content = raw_text(raw.get("content")) or rendered(raw.get("content"))
        for old, new in moved.items():
            content = content.replace(old, new)
        body: dict[str, Any] = {
            "title": _title(raw),
            "content": rewrite_links(content, source_url, target_url),
            "excerpt": raw_text(raw.get("excerpt")),
            "slug": str(raw.get("slug", "") or ""),
            "status": "draft" if line.action == "create" else str(raw.get("status", "draft")),
        }
        for base in ("categories", "tags"):
            ids = raw.get(base)
            if isinstance(ids, list) and ids:
                body[base] = _term_ids_by_name(source, target, f"wp/v2/{base}", ids)
    elif kind == "term":
        route = _route_for("term", str(raw.get("taxonomy", "category")), raw)
        body = {
            "name": str(raw.get("name", "")),
            "slug": str(raw.get("slug", "") or ""),
            "description": str(raw.get("description", "") or ""),
        }
    elif kind == "pattern":
        content = raw_text(raw.get("content")) or rendered(raw.get("content"))
        body = {
            "title": _title(raw),
            "content": rewrite_links(content, source_url, target_url),
            "status": "publish",
        }
    elif kind == "menu":
        body = {"name": str(raw.get("name", "")), "description": str(raw.get("description", ""))}
    else:  # a QAF form travels whole, as its JSON definition
        body = {k: v for k, v in raw.items() if k not in ("id", "_links")}
    if line.action == "replace" and line.target_id:
        target.post(f"{route}/{line.target_id}", body)
    else:
        target.post(route, body)


# -- compare -------------------------------------------------------------------


@dataclass(frozen=True)
class Difference:
    kind: str
    slug: str
    words: str


def _by_slug(api: WordPressApi, route: str) -> dict[str, Mapping[str, Any]]:
    found: dict[str, Mapping[str, Any]] = {}
    for raw in api.iter_collection(
        route,
        {
            "context": "edit",
            "status": "any",
            "_fields": "id,slug,title,modified_gmt,content,status",
        },
        per_page=100,
        max_pages=20,
    ):
        found[str(raw.get("slug", "") or raw.get("id", ""))] = raw
    return found


def compare_sites(
    first: WordPressApi,
    second: WordPressApi,
    *,
    first_name: str,
    second_name: str,
    kinds: Sequence[str] = ("post", "page"),
) -> list[Difference]:
    """Every post and page (by slug) only one site has, or whose title or text differ."""
    found: list[Difference] = []
    for kind in kinds:
        route = kind_route(kind)
        mine, theirs = _by_slug(first, route), _by_slug(second, route)
        for slug in sorted(set(mine) | set(theirs)):
            a, b = mine.get(slug), theirs.get(slug)
            if a is None:
                found.append(Difference(kind, slug, f"only on {second_name}"))
            elif b is None:
                found.append(Difference(kind, slug, f"only on {first_name}"))
            else:
                said: list[str] = []
                if _title(a) != _title(b):
                    said.append("titles differ")
                if (raw_text(a.get("content")) or "") != (raw_text(b.get("content")) or ""):
                    said.append("text differs")
                if a.get("status") != b.get("status"):
                    said.append(f"{a.get('status')} here, {b.get('status')} there")
                if said:
                    found.append(Difference(kind, slug, ", ".join(said)))
    return found


# -- snapshot ------------------------------------------------------------------

_SNAPSHOT_PARTS: tuple[tuple[str, str], ...] = (
    ("posts", "wp/v2/posts"),
    ("pages", "wp/v2/pages"),
    ("categories", "wp/v2/categories"),
    ("tags", "wp/v2/tags"),
    ("menus", "wp/v2/menus"),
    ("menu_items", "wp/v2/menu-items"),
    ("patterns", "wp/v2/blocks"),
)


def take_snapshot(
    api: WordPressApi,
    folder: Path,
    *,
    site: str,
    media: bool = False,
    clock: Callable[[], float] = time.time,
) -> tuple[Path, dict[str, int]]:
    """Every post, page, term, menu, pattern and setting to *folder*/<when>; the counts."""
    stamp = time.strftime("%Y-%m-%d %H%M%S", time.localtime(clock()))
    where = folder / stamp
    counts: dict[str, int] = {}
    parts = list(_SNAPSHOT_PARTS) + ([("media", "wp/v2/media")] if media else [])
    for name, route in parts:
        params: dict[str, object] = {"context": "edit"}
        if name in ("posts", "pages", "patterns"):
            params["status"] = "any"
        try:
            rows = list(api.iter_collection(route, params, per_page=100, max_pages=1000))
        except WordPressApiError:
            rows = []
        counts[name] = len(rows)
        write_json_atomic(where / f"{name}.json", rows)
    try:
        settings = api.get("wp/v2/settings")
    except WordPressApiError:
        settings = {}
    write_json_atomic(where / "settings.json", settings if isinstance(settings, dict) else {})
    counts["settings"] = len(settings) if isinstance(settings, dict) else 0
    write_json_atomic(
        where / "snapshot.json",
        {"site": site, "taken": stamp, "counts": counts, "media_files": False},
    )
    return where, counts


# -- calendar ------------------------------------------------------------------


def day_words(day: str, scheduled: int, published: int) -> str:
    """ "Tuesday 12 November: 2 scheduled, 1 published"."""
    when = datetime.strptime(day, "%Y-%m-%d")
    parts = []
    if scheduled:
        parts.append(f"{scheduled} scheduled")
    if published:
        parts.append(f"{published} published")
    return f"{when:%A} {when.day} {when:%B}: {', '.join(parts) or 'nothing'}"


def calendar_days(
    sites: Iterable[tuple[str, WordPressApi]],
    *,
    since: str,
    kinds: Sequence[str] = ("post", "page"),
) -> dict[str, list[dict[str, Any]]]:
    """Each day (``2026-11-12``) with its scheduled and published items, from every site.

    *since* is the first day (ISO date) published items count from; every
    scheduled item counts, however far ahead.
    """
    days: dict[str, list[dict[str, Any]]] = {}
    for site, api in sites:
        for kind in kinds:
            route = kind_route(kind)
            for status, extra in (("future", {}), ("publish", {"after": f"{since}T00:00:00"})):
                try:
                    raw_rows = list(
                        api.iter_collection(
                            route,
                            {"status": status, "orderby": "date", "order": "asc", **extra},
                            per_page=100,
                            max_pages=3,
                        )
                    )
                except WordPressApiError:
                    continue
                for raw in raw_rows:
                    day = str(raw.get("date", "") or "")[:10]
                    if day:
                        days.setdefault(day, []).append({
                            "site": site,
                            "kind": kind,
                            "status": status,
                            "raw": raw,
                        })
    return dict(sorted(days.items()))


# -- read the site like a book -------------------------------------------------

_TAG = re.compile(r"<[^>]+>")


def _plain(html: str) -> str:
    text = re.sub(r"</(p|h\d|li|div|blockquote)>", "\n\n", html or "", flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = _TAG.sub("", text)
    import html as html_module

    lines = [line.strip() for line in html_module.unescape(text).splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def site_document(site: str, pages: Sequence[Mapping[str, Any]]) -> str:
    """The pages (already in reading order) as one Markdown document."""
    parts = [f"# {site}", ""]
    for page in pages:
        title = _title(page) or "(untitled)"
        link = str(page.get("link", "") or "")
        parts.append(f"## {title}")
        if link:
            parts.append(f"Address: {link}")
        parts.append("")
        parts.append(_plain(rendered(page.get("content")) or raw_text(page.get("content"))))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def snapshot_counts_words(counts: Mapping[str, int]) -> str:
    said = ", ".join(f"{n} {name.replace('_', ' ')}" for name, n in counts.items() if n)
    return said or "nothing"


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)
