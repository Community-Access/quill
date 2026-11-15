"""Plain language in, a previewed batch out (PRD 15.8; W7).

A small, fixed grammar read without AI, so the same words always mean the
same batch and nothing is guessed:

- ``move all drafts by Sam to pending on Radio`` -- change the status of
  posts (or ``pages``) that have one status, optionally by one author and in
  one category, to another status;
- ``add tag 2026 to posts in category Events on every site``;
- ``remove tag Old from all published posts by Ann``.

Where it runs is ``on <site>``, ``on <site> and <site>``, ``on every site``
or ``on all sites``; without one, the current site. A site name, author,
category or tag that matches nothing exactly is a sentence, never a guess.
:func:`parse_request` reads the words (:class:`BatchRequest`, or
:class:`PhraseError` with what it understands); :func:`resolve` asks each
site for the exact items (bounded by :data:`LIMIT`) and the body each one
gets; the Workbench shows that as an editable checklist and sends what is
left checked through the shared engine: the permission check, a conflict
check against the time each item was read
(:func:`quill.core.wordpress.workbench_edit.check_conflict`) and
``batch/v1`` (:func:`quill.core.wordpress.workbench_edit.run_batch`).

Wx-free; :func:`resolve` and :func:`run_site` run off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_edit import EditConflict, check_conflict, run_batch
from quill.core.wordpress.workbench_rows import WbRow, item_row

__all__ = [
    "EXAMPLES",
    "LIMIT",
    "BatchRequest",
    "PhraseError",
    "SitePlan",
    "parse_request",
    "resolve",
    "run_site",
]

LIMIT = 500
EXAMPLES = (
    "move all drafts by Sam to pending on Radio",
    "add tag 2026 to posts in category Events on every site",
    "remove tag Old from all published pages",
)
_STATUS_WORDS = {
    "draft": "draft",
    "drafts": "draft",
    "pending": "pending",
    "published": "publish",
    "publish": "publish",
    "private": "private",
    "scheduled": "future",
}
_STATUS = "|".join(sorted(_STATUS_WORDS, key=len, reverse=True))
_KIND = r"(?:(?P<kind>posts|pages)\b)?"
_MOVE = re.compile(
    rf"^(?:move|set|change)\s+(?:all\s+|every\s+)?(?:the\s+)?(?P<status>{_STATUS})?\s*{_KIND}"
    rf"(?P<filters>.*?)\s+to\s+(?P<to>{_STATUS})\b(?P<where>.*)$",
    re.IGNORECASE,
)
_TAG = re.compile(
    rf"^(?P<verb>add|remove)\s+(?:the\s+)?tag\s+(?P<tag>.+?)\s+(?:to|from)\s+"
    rf"(?:all\s+|every\s+)?(?:the\s+)?(?P<status>{_STATUS})?\s*{_KIND}(?P<rest>.*)$",
    re.IGNORECASE,
)


class PhraseError(CodedError):
    """Words the batch grammar does not read, or a name that matches nothing."""

    code = "QUILL-WP-WORKBENCH-PHRASE"

    @property
    def plain(self) -> str:
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class BatchRequest:
    action: str  # "status", "add_tag" or "remove_tag"
    value: str  # the new status, or the tag's name
    kind: str = "post"
    status: str = ""
    author: str = ""
    category: str = ""
    sites: tuple[str, ...] = ()

    @property
    def words(self) -> str:
        what = f"{self.kind}s"
        if self.status:
            what = f"{_said(self.status)} {what}"
        if self.author:
            what += f" by {self.author}"
        if self.category:
            what += f" in the category {self.category}"
        where = ", ".join(self.sites)
        if self.action == "status":
            return f"Set {what} to {_said(self.value)}, on {where}."
        verb = "Add the tag" if self.action == "add_tag" else "Remove the tag"
        joint = "to" if self.action == "add_tag" else "from"
        return f"{verb} {self.value} {joint} {what}, on {where}."


def _said(status: str) -> str:
    return {"publish": "published", "future": "scheduled"}.get(status, status)


def _split_filters(text: str) -> tuple[str, str, str]:
    """``by Sam in category News on Radio`` -> (author, category, where)."""
    where = ""
    match = re.search(r"\bon\s+(every site|all sites|.+)$", text, re.IGNORECASE)
    if match:
        where, text = match.group(1).strip(), text[: match.start()]
    author = category = ""
    found = re.search(r"\bby\s+(.+?)(?=\s+in\s+(?:the\s+)?category\b|$)", text, re.IGNORECASE)
    if found:
        author = found.group(1).strip()
    found = re.search(r"\bin\s+(?:the\s+)?category\s+(.+?)(?=\s+by\b|$)", text, re.IGNORECASE)
    if found:
        category = found.group(1).strip()
    left = re.sub(
        r"\bby\s+.+?(?=\s+in\s|$)|\bin\s+(?:the\s+)?category\s+.+?(?=\s+by\b|$)", "", text
    )
    if left.strip():
        raise PhraseError(f"QUILL does not read {left.strip()!r} here. {_help()}")
    return author, category, where


def _sites(where: str, known: Sequence[str], current: str) -> tuple[str, ...]:
    if not where:
        if not current:
            raise PhraseError("Say which site: on Radio, or on every site.")
        return (current,)
    if where.lower() in ("every site", "all sites", "all my sites"):
        return tuple(known)
    names = [n.strip() for n in re.split(r",|\band\b", where) if n.strip()]
    by_lower = {k.casefold(): k for k in known}
    missing = [n for n in names if n.casefold() not in by_lower]
    if missing:
        raise PhraseError(
            f"No connected site is called {', '.join(missing)}. Yours are: {', '.join(known)}."
        )
    return tuple(by_lower[n.casefold()] for n in names)


def _help() -> str:
    return "It reads phrases like: " + "; ".join(EXAMPLES) + "."


def parse_request(text: str, known: Sequence[str], current: str = "") -> BatchRequest:
    """*text* as a :class:`BatchRequest`, or :class:`PhraseError` saying what it reads."""
    clean = " ".join(text.strip().rstrip(".").split())
    move = _MOVE.match(clean)
    if move:
        author, category, where = _split_filters(f"{move.group('filters')}{move.group('where')}")
        status = _STATUS_WORDS[move.group("status").lower()] if move.group("status") else ""
        kind = (move.group("kind") or "posts").lower().rstrip("s")
        return BatchRequest(
            "status",
            _STATUS_WORDS[move.group("to").lower()],
            kind,
            status,
            author,
            category,
            _sites(where, known, current),
        )
    tag = _TAG.match(clean)
    if tag:
        kind = (tag.group("kind") or "posts").lower().rstrip("s")
        if kind != "post":
            raise PhraseError("Pages have no tags in WordPress; tags are for posts.")
        author, category, where = _split_filters(tag.group("rest"))
        status = _STATUS_WORDS[tag.group("status").lower()] if tag.group("status") else ""
        action = "add_tag" if tag.group("verb").lower() == "add" else "remove_tag"
        return BatchRequest(
            action,
            tag.group("tag").strip(),
            kind,
            status,
            author,
            category,
            _sites(where, known, current),
        )
    raise PhraseError(_help())


@dataclass
class SitePlan:
    """What the request means on one site: the exact items and each one's body."""

    site: str
    rows: list[WbRow] = field(default_factory=list)
    bodies: list[dict[str, Any]] = field(default_factory=list)
    problem: str = ""
    make_tag: str = ""  # a tag to make on the site first (add_tag, when it is missing)
    more: bool = False

    @property
    def sentence(self) -> str:
        if self.problem:
            return f"{self.site}: nothing, because {self.problem}"
        said = f"{self.site}: {len(self.rows)} items"
        if self.make_tag:
            said += f", and the tag {self.make_tag} made first"
        if self.more:
            said += f"; only the first {LIMIT} are listed"
        return said + "."


def _exact(api: WordPressApi, route: str, name: str, field_name: str = "name") -> int:
    found = api.get(route, search=name, _fields=f"id,{field_name}")
    for raw in found if isinstance(found, list) else []:
        if str(raw.get(field_name, "")).casefold() == name.casefold():
            return int(raw.get("id", 0) or 0)
    return 0


def resolve(request: BatchRequest, site: str, api: WordPressApi) -> SitePlan:
    """The exact items *request* means on *site*, and what each one is sent."""
    plan = SitePlan(site)
    query: dict[str, object] = {"context": "edit", "status": request.status or "any"}
    try:
        if request.author:
            ident = _exact(api, "wp/v2/users", request.author)
            if not ident:
                plan.problem = f"{request.author} has no account there."
                return plan
            query["author"] = ident
        if request.category:
            ident = _exact(api, "wp/v2/categories", request.category)
            if not ident:
                plan.problem = f"it has no category called {request.category}."
                return plan
            query["categories"] = ident
        tag_id = 0
        if request.action != "status":
            tag_id = _exact(api, "wp/v2/tags", request.value)
            if not tag_id and request.action == "remove_tag":
                plan.problem = f"it has no tag called {request.value}."
                return plan
            plan.make_tag = "" if tag_id else request.value
        items = api.iter_collection(kind_route(request.kind), query, per_page=100, max_pages=6)
        for raw in items:
            if len(plan.rows) >= LIMIT:
                plan.more = True
                break
            body = _body(request, raw, tag_id)
            if body is not None:
                plan.rows.append(item_row(raw, request.kind, site))
                plan.bodies.append(body)
    except WordPressApiError as exc:
        plan.problem = f"the site said {exc.plain or exc}"
    return plan


def _body(request: BatchRequest, raw: Mapping[str, Any], tag_id: int) -> dict[str, Any] | None:
    if request.action == "status":
        return None if raw.get("status") == request.value else {"status": request.value}
    tags = [int(t) for t in raw.get("tags", []) or []]
    if request.action == "add_tag":
        return None if tag_id and tag_id in tags else {"tags": [*tags, tag_id]}
    return {"tags": [t for t in tags if t != tag_id]} if tag_id in tags else None


def run_site(api: WordPressApi, plan: SitePlan, keep: Sequence[int]) -> list[str]:
    """Send the kept items of *plan*: conflict check, then the batch; a sentence each."""
    rows = [plan.rows[i] for i in keep]
    bodies = [dict(plan.bodies[i]) for i in keep]
    if not rows:
        return []
    if plan.make_tag:
        made = api.post("wp/v2/tags", {"name": plan.make_tag})
        new = int(made.get("id", 0) or 0) if isinstance(made, dict) else 0
        for body in bodies:
            body["tags"] = [new if t == 0 else t for t in body.get("tags", [])]
    said: list[str] = []
    sendable: list[tuple[WbRow, dict[str, Any]]] = []
    for row, body in zip(rows, bodies, strict=True):
        try:
            check_conflict(api, row, row.modified_gmt)
            sendable.append((row, body))
        except EditConflict as exc:
            said.append(f"{plan.site}, {exc}")
        except WordPressApiError as exc:
            said.append(f"{plan.site}, {row.title}: {exc.plain or exc}")
    if sendable:
        results = run_batch(api, [r for r, _b in sendable], [b for _r, b in sendable])
        said += [f"{plan.site}, {result.sentence}" for result in results]
    return said
