"""Compare Sites, Take a Snapshot and Put Back from a Snapshot (PRD 15.2; W7).

- **Compare Sites** (:func:`compare_sites`): posts, pages, patterns,
  categories, tags and menus, matched by address (slug), read as a list.
  What it does not compare is said in :data:`COMPARE_OMITS`; a kind one site
  would not give is a line saying so, and a kind longer than the bound is
  named as cut short, so an empty list always means "the same".
- **Take a Snapshot** (:func:`take_snapshot`): every post, page, pattern,
  term, menu, menu link and setting to a folder on this computer. Media
  records always; the files themselves only when asked. ``snapshot.json``
  says what was taken, what could not be read and what is never taken.
- **Put Back from a Snapshot** (:func:`restore_plan`, :func:`run_restore`):
  the contract is :data:`RESTORE_TERMS` -- posts, pages, patterns,
  categories and tags changed since are set back (WordPress keeps a revision
  of each post and page it changes, so the putting back is itself undoable
  from Revisions); ones deleted since are made again as drafts at new
  addresses; menus, settings, people, plugins and media files are not put
  back, and the preview says so.

Wx-free; the Workbench runs it off the UI thread.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route, raw_text, rendered

__all__ = [
    "COMPARE_KINDS",
    "COMPARE_OMITS",
    "RESTORE_TERMS",
    "Difference",
    "RestoreLine",
    "compare_sites",
    "restore_plan",
    "run_restore",
    "snapshot_counts_words",
    "snapshot_folders",
    "snapshot_left_out",
    "snapshot_source",
    "take_snapshot",
]

COMPARE_KINDS = ("post", "page", "pattern", "category", "tag", "menu")
COMPARE_OMITS = (
    "Not compared: media files, revisions, menu links, settings, people, plugins and themes."
)
RESTORE_TERMS = (
    "Posts, pages, patterns, categories and tags changed since the snapshot are set back to "
    "it; WordPress keeps a revision of each post and page it changes, so this can be undone "
    "from Revisions. Ones deleted since are made again as drafts, at new addresses. Menus, "
    "settings, people, plugins and media files are not put back."
)
_ROUTES = {
    "pattern": "wp/v2/blocks",
    "category": "wp/v2/categories",
    "tag": "wp/v2/tags",
    "menu": "wp/v2/menus",
}
_PAGES = 20
_PER_PAGE = 100


def _route(kind: str) -> str:
    return _ROUTES.get(kind) or kind_route(kind)


def _title(raw: Mapping[str, Any]) -> str:
    return (
        raw_text(raw.get("title"))
        or rendered(raw.get("title"))
        or str(raw.get("name", "") or raw.get("slug", "") or raw.get("id", ""))
    )


@dataclass(frozen=True)
class Difference:
    kind: str
    slug: str
    words: str


def _by_slug(api: WordPressApi, kind: str) -> dict[str, Mapping[str, Any]]:
    params: dict[str, object] = {"context": "edit"}
    if kind in ("post", "page", "pattern") or kind not in _ROUTES:
        params["status"] = "any"
    found: dict[str, Mapping[str, Any]] = {}
    for raw in api.iter_collection(_route(kind), params, per_page=_PER_PAGE, max_pages=_PAGES):
        found[str(raw.get("slug", "") or raw.get("id", ""))] = raw
    return found


def _differ(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    said: list[str] = []
    if _title(a) != _title(b):
        said.append("titles differ" if "title" in a else "names differ")
    if (raw_text(a.get("content")) or "") != (raw_text(b.get("content")) or ""):
        said.append("text differs")
    if str(a.get("description", "") or "") != str(b.get("description", "") or ""):
        said.append("descriptions differ")
    if a.get("status") != b.get("status"):
        said.append(f"{a.get('status')} here, {b.get('status')} there")
    return said


def compare_sites(
    first: WordPressApi,
    second: WordPressApi,
    *,
    first_name: str,
    second_name: str,
    kinds: Sequence[str] = COMPARE_KINDS,
) -> list[Difference]:
    """Everything (by slug) only one site has, or whose title, text or status differ."""
    found: list[Difference] = []
    bound = _PAGES * _PER_PAGE
    for kind in kinds:
        sides: list[dict[str, Mapping[str, Any]]] = []
        for api, name in ((first, first_name), (second, second_name)):
            try:
                sides.append(_by_slug(api, kind))
            except WordPressApiError as exc:
                found.append(Difference(kind, "", f"not compared: {name} said {exc.plain or exc}"))
                break
        if len(sides) < 2:
            continue
        mine, theirs = sides
        for name, side in ((first_name, mine), (second_name, theirs)):
            if len(side) >= bound:
                found.append(Difference(kind, "", f"only the first {bound} on {name} compared"))
        for slug in sorted(set(mine) | set(theirs)):
            a, b = mine.get(slug), theirs.get(slug)
            if a is None:
                found.append(Difference(kind, slug, f"only on {second_name}"))
            elif b is None:
                found.append(Difference(kind, slug, f"only on {first_name}"))
            else:
                said = _differ(a, b)
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
    ("media", "wp/v2/media"),
)
_NEVER = "people, passwords, plugins, themes, revisions and comments"


def take_snapshot(
    api: WordPressApi,
    folder: Path,
    *,
    site: str,
    media: bool = False,
    fetch: Callable[[str], bytes] | None = None,
    clock: Callable[[], float] = time.time,
    practice: bool = False,
) -> tuple[Path, dict[str, int]]:
    """Every post, page, term, menu, pattern and setting to *folder*/<when>; the counts.

    Media records are always saved; with *media* and *fetch*, the files too,
    into ``media files``. Parts the site would not give are listed in
    ``snapshot.json`` as ``unread`` rather than saved as empty.
    """
    stamp = time.strftime("%Y-%m-%d %H%M%S", time.localtime(clock()))
    where = folder / stamp
    counts: dict[str, int] = {}
    unread: list[str] = []
    files_failed: list[str] = []
    for name, route in _SNAPSHOT_PARTS:
        params: dict[str, object] = {"context": "edit"}
        if name in ("posts", "pages", "patterns"):
            params["status"] = "any"
        try:
            rows = list(api.iter_collection(route, params, per_page=100, max_pages=1000))
        except WordPressApiError as exc:
            unread.append(f"{name.replace('_', ' ')}: {exc.plain or exc}")
            continue
        counts[name] = len(rows)
        write_json_atomic(where / f"{name}.json", rows)
        if name == "media" and media and fetch is not None:
            files_failed += _save_files(rows, where / "media files", fetch)
    try:
        settings = api.get("wp/v2/settings")
    except WordPressApiError as exc:
        settings = None
        unread.append(f"settings: {exc.plain or exc}")
    if isinstance(settings, dict):
        write_json_atomic(where / "settings.json", settings)
        counts["settings"] = len(settings)
    write_json_atomic(
        where / "snapshot.json",
        {
            "site": site,
            "practice": practice,
            "taken": stamp,
            "counts": counts,
            "media_files": bool(media and fetch is not None),
            "media_files_failed": files_failed,
            "unread": unread,
            "never_taken": _NEVER,
            "left_out": _left_out(bool(media and fetch is not None), unread, files_failed),
            "put_back": RESTORE_TERMS,
        },
    )
    return where, counts


def _left_out(media_files: bool, unread: Sequence[str], failed: Sequence[str]) -> list[str]:
    said = [] if media_files else ["the media files themselves (not asked for; records kept)"]
    said.append(f"{_NEVER}: never taken")
    for part in unread:
        name, _sep, why = part.partition(":")
        said.append(f"{name}: the site would not give it ({why.strip()})")
    said += [f"the media file {line}" for line in failed]
    return said


def snapshot_left_out(where: Path) -> list[str]:
    """What the snapshot in *where* left out, as its ``snapshot.json`` records it."""
    told = read_json(where / "snapshot.json", default={})
    listed = told.get("left_out") if isinstance(told, dict) else None
    return [str(line) for line in listed or []]


def _save_files(rows: Sequence[Mapping[str, Any]], folder: Path, fetch: Any) -> list[str]:
    failed: list[str] = []
    for raw in rows:
        url = str(raw.get("source_url", "") or "")
        name = url.rsplit("/", 1)[-1].split("?", 1)[0]
        if not url or not name:
            continue
        try:
            data = fetch(url)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{int(raw.get('id', 0) or 0)}-{name}").write_bytes(data)
        except Exception as exc:  # noqa: BLE001 - one file must not stop the snapshot
            failed.append(f"{url}: {exc}")
    return failed


def snapshot_folders(folder: Path) -> list[Path]:
    """The snapshots under *folder*, newest first."""
    if not folder.is_dir():
        return []
    found = [p for p in folder.iterdir() if (p / "snapshot.json").is_file()]
    return sorted(found, key=lambda p: p.name, reverse=True)


def snapshot_source(snapshot: Path) -> tuple[str, bool]:
    """(the site a snapshot was taken of, whether that was the practice site)."""
    about = read_json(snapshot / "snapshot.json", {})
    if not isinstance(about, dict):
        return "", False
    return str(about.get("site", "") or ""), bool(about.get("practice", False))


def snapshot_counts_words(counts: Mapping[str, int]) -> str:
    said = ", ".join(f"{n} {name.replace('_', ' ')}" for name, n in counts.items() if n)
    return said or "nothing"


# -- put back ------------------------------------------------------------------

_RESTORABLE = (
    ("posts", "post", "wp/v2/posts"),
    ("pages", "page", "wp/v2/pages"),
    ("patterns", "pattern", "wp/v2/blocks"),
    ("categories", "category", "wp/v2/categories"),
    ("tags", "tag", "wp/v2/tags"),
)


@dataclass(frozen=True)
class RestoreLine:
    action: str  # "put back" or "make again"
    kind: str
    title: str
    route: str
    body: Mapping[str, Any] = field(default_factory=dict)

    @property
    def sentence(self) -> str:
        if self.action == "make again":
            return f"Make the {self.kind} {self.title} again, as a draft: it was deleted."
        return f"Put back the {self.kind} {self.title}: it changed since the snapshot."


def _body(kind: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    if kind in ("category", "tag"):
        return {"name": str(raw.get("name", "")), "description": str(raw.get("description", ""))}
    body = {"title": raw_text(raw.get("title")), "content": raw_text(raw.get("content"))}
    if kind != "pattern":
        body["excerpt"] = raw_text(raw.get("excerpt"))
    return body


def restore_plan(api: WordPressApi, snapshot: Path) -> list[RestoreLine]:
    """What putting *snapshot* back on the site would change; reads only."""
    lines: list[RestoreLine] = []
    for part, kind, route in _RESTORABLE:
        saved = read_json(snapshot / f"{part}.json", default=[])
        if not isinstance(saved, list) or not saved:
            continue
        params: dict[str, object] = {"context": "edit"}
        if kind in ("post", "page", "pattern"):
            params["status"] = "any"
        now = {
            int(r.get("id", 0) or 0): r
            for r in api.iter_collection(route, params, per_page=100, max_pages=1000)
        }
        for raw in saved:
            if not isinstance(raw, dict):
                continue
            ident = int(raw.get("id", 0) or 0)
            body = _body(kind, raw)
            current = now.get(ident)
            if current is None:
                lines.append(
                    RestoreLine("make again", kind, _title(raw), route, {**body, "status": "draft"})
                )
            elif _body(kind, current) != body:
                lines.append(RestoreLine("put back", kind, _title(raw), f"{route}/{ident}", body))
    return lines


def run_restore(api: WordPressApi, lines: Sequence[RestoreLine]) -> list[str]:
    """Do *lines*; one sentence per line, saying what happened."""
    said: list[str] = []
    for line in lines:
        try:
            api.post(line.route, dict(line.body))
            done = "Made again" if line.action == "make again" else "Put back"
            said.append(f"{done}: {line.kind} {line.title}.")
        except WordPressApiError as exc:
            said.append(f"Not put back: {line.kind} {line.title}: {exc.plain or exc}")
    return said
