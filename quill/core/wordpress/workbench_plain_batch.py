"""Plain language in, a previewed batch out (PRD 15.8; W7).

A small, fixed grammar read without AI, so the same words always mean the
same batch and nothing is guessed:

- ``move all drafts by Sam to pending on Radio`` -- change the status of
  posts (or ``pages``) that have one status, optionally by one author and in
  one category, to another status;
- ``add tag 2026 to posts in category Events on every site``;
- ``remove tag Old from all published posts by Ann``;
- ``move every draft older than a year to Trash`` (or ``trash all drafts
  before March 2024``): into WordPress's Trash, after the same checklist, and
  Undo puts them back with the status each had;
- ``how many drafts are older than six months?``: a question, answered with a
  count from each site, and nothing changed.

Any of them may say how old (``older than a year``, ``newer than two weeks``,
``before March 2024``, ``after 2023``: :mod:`quill.core.wordpress.workbench_plain_age`),
by the item's date. Where it runs is ``on <site>``, ``on <site> and <site>``, ``on every site``
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
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_edit import (
    EditConflict,
    check_conflict,
    restore,
    run_batch,
    trash,
)
from quill.core.wordpress.workbench_plain_age import Age, AgeError, find_age
from quill.core.wordpress.workbench_rows import WbRow, item_row

__all__ = [
    "EXAMPLES",
    "LIMIT",
    "BatchRequest",
    "PhraseError",
    "SitePlan",
    "answer",
    "parse_request",
    "resolve",
    "run_site",
    "undo_trash",
]

LIMIT = 500
EXAMPLES = (
    "move all drafts by Sam to pending on Radio",
    "add tag 2026 to posts in category Events on every site",
    "remove tag Old from all published pages",
    "move every draft older than a year to Trash",
    "how many drafts are older than six months?",
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
_TO = rf"(?P<to>{_STATUS}|(?:the\s+)?trash)"
_MOVE = re.compile(
    rf"^(?:move|set|change|put)\s+(?:all\s+|every\s+)?(?:the\s+)?(?P<status>{_STATUS})?\s*{_KIND}"
    rf"(?P<filters>.*?)\s+(?:to|in|into)\s+{_TO}\b(?P<where>.*)$",
    re.IGNORECASE,
)
_TRASH = re.compile(
    rf"^trash\s+(?:all\s+|every\s+)?(?:the\s+)?(?P<status>{_STATUS})?\s*{_KIND}(?P<rest>.*)$",
    re.IGNORECASE,
)
_COUNT = re.compile(
    rf"^how\s+many\s+(?:of\s+)?(?:the\s+|my\s+)?(?P<status>{_STATUS})?\s*{_KIND}(?P<rest>.*)$",
    re.IGNORECASE,
)
#: "are", "is" or "are there" before a filter or at the end, in a question.
_BE = re.compile(
    rf"(?:^\s*|\s+)(?:are|is|were)(?:\s+there)?(?=\s+(?:by|in|on|older|newer|younger|before|after|since|"
    rf"{_STATUS})\b|\s*$)",
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
    action: str  # "status", "add_tag", "remove_tag", "trash" or "count"
    value: str  # the new status, or the tag's name ("" for trash and count)
    kind: str = "post"
    status: str = ""
    author: str = ""
    category: str = ""
    sites: tuple[str, ...] = ()
    age: Age = field(default_factory=Age)

    @property
    def what(self) -> str:
        """The items in words: "draft posts by Sam older than a year"."""
        what = f"{self.kind}s"
        if self.status:
            what = f"{_said(self.status)} {what}"
        if self.author:
            what += f" by {self.author}"
        if self.category:
            what += f" in the category {self.category}"
        if self.age.words:
            what += f" {self.age.words}"
        return what

    @property
    def changes(self) -> bool:
        return self.action != "count"

    @property
    def words(self) -> str:
        what = self.what
        where = ", ".join(self.sites)
        if self.action == "count":
            return f"How many {what}, on {where}."
        if self.action == "trash":
            return f"Move {what} to the Trash, on {where}."
        if self.action == "status":
            return f"Set {what} to {_said(self.value)}, on {where}."
        verb = "Add the tag" if self.action == "add_tag" else "Remove the tag"
        joint = "to" if self.action == "add_tag" else "from"
        return f"{verb} {self.value} {joint} {what}, on {where}."


def _said(status: str) -> str:
    return {"publish": "published", "future": "scheduled"}.get(status, status)


@dataclass(frozen=True)
class _Filters:
    author: str = ""
    category: str = ""
    where: str = ""
    age: Age = field(default_factory=Age)


def _split_filters(text: str, today: date) -> _Filters:
    """``by Sam in category News older than a year on Radio``, taken apart."""
    where = ""
    match = re.search(r"\bon\s+(every site|all sites|.+)$", text, re.IGNORECASE)
    if match:
        where, text = match.group(1).strip(), text[: match.start()]
    try:
        age, text = find_age(text, today)
    except AgeError as exc:
        raise PhraseError(exc.plain) from None
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
    return _Filters(author, category, where, age)


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


def _status(word: str | None) -> str:
    return _STATUS_WORDS[word.lower()] if word else ""


def _request(
    action: str, value: str, found: re.Match[str], rest: str, known: Sequence[str],
    current: str, today: date,
) -> BatchRequest:  # fmt: skip
    kind = (found.group("kind") or "posts").lower().rstrip("s")
    filters = _split_filters(rest, today)
    return BatchRequest(
        action,
        value,
        kind,
        _status(found.group("status")),
        filters.author,
        filters.category,
        _sites(filters.where, known, current),
        filters.age,
    )


def parse_request(
    text: str, known: Sequence[str], current: str = "", today: date | None = None
) -> BatchRequest:
    """*text* as a :class:`BatchRequest`, or :class:`PhraseError` saying what it reads.

    *today* is the day an age such as "older than a year" counts back from.
    """
    day = today or date.today()
    clean = " ".join(text.strip().rstrip(".?").split())
    move = _MOVE.match(clean)
    if move:
        rest = f"{move.group('filters')}{move.group('where')}"
        to = move.group("to").lower()
        if to.endswith("trash"):
            return _request("trash", "", move, rest, known, current, day)
        return _request("status", _STATUS_WORDS[to], move, rest, known, current, day)
    found = _TRASH.match(clean)
    if found:
        return _request("trash", "", found, found.group("rest"), known, current, day)
    found = _COUNT.match(clean)
    if found:
        rest = _BE.sub("", found.group("rest"))
        said = re.match(rf"^\s*(?P<status>{_STATUS})\b", rest, re.IGNORECASE)
        request = _request("count", "", found, rest[said.end() :] if said else rest, known,
                           current, day)  # fmt: skip
        if said and not request.status:
            return replace(request, status=_status(said.group("status")))
        return request
    tag = _TAG.match(clean)
    if tag:
        if (tag.group("kind") or "posts").lower() != "posts":
            raise PhraseError("Pages have no tags in WordPress; tags are for posts.")
        action = "add_tag" if tag.group("verb").lower() == "add" else "remove_tag"
        return _request(action, tag.group("tag").strip(), tag, tag.group("rest"), known,
                        current, day)  # fmt: skip
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
    count: int = -1  # a question's answer
    #: What a Trash batch moved, with the status each had, for Undo.
    moved: list[tuple[WbRow, str]] = field(default_factory=list)

    @property
    def sentence(self) -> str:
        if self.problem:
            return f"{self.site}: nothing, because {self.problem}"
        if self.count >= 0:
            return f"{self.count} on {self.site}"
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
    if request.age.before:
        query["before"] = request.age.before
    if request.age.after:
        query["after"] = request.age.after
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
        if request.action == "count":
            plan.count = _count(api, kind_route(request.kind), query)
            return plan
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


def _count(api: WordPressApi, route: str, query: Mapping[str, object]) -> int:
    """How many items *query* finds: WordPress's own total, else counted (to 1,000)."""
    ask = {**query, "_fields": "id"}
    request = getattr(api, "request", None)
    if callable(request):
        total = request("GET", route, params={**ask, "per_page": 1}).total
        if total is not None:
            return int(total)
    return sum(1 for _ in api.iter_collection(route, ask, per_page=100, max_pages=10))


def answer(request: BatchRequest, plans: Sequence[SitePlan]) -> str:
    """A question's answer: "Draft posts older than six months: 12 on Radio, 3 on Shop."."""
    counted = [p for p in plans if p.count >= 0]
    said = f"{request.what[0].upper()}{request.what[1:]}: "
    said += "; ".join(p.sentence.rstrip(".") for p in plans)
    if len(counted) > 1:
        said += f"; {sum(p.count for p in counted)} in all"
    return said + "."


def _body(request: BatchRequest, raw: Mapping[str, Any], tag_id: int) -> dict[str, Any] | None:
    if request.action == "trash":
        return None if raw.get("status") == "trash" else {"status": "trash"}
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
    if sendable and bodies[0].get("status") == "trash":
        for row, _body in sendable:
            try:
                trash(api, row)
            except (WordPressApiError, CodedError) as exc:
                said.append(f"{plan.site}, {row.title}: {getattr(exc, 'plain', '') or exc}")
                continue
            plan.moved.append((row, row.status))
            said.append(f"{plan.site}, {row.title}: moved to the Trash")
        return said
    if sendable:
        results = run_batch(api, [r for r, _b in sendable], [b for _r, b in sendable])
        said += [f"{plan.site}, {result.sentence}" for result in results]
    return said


def undo_trash(api_for: Any, plans: Sequence[SitePlan]) -> str:
    """Out of the Trash again, each with the status it had; the sentence to say."""
    back = 0
    for plan in plans:
        api = api_for(plan.site)
        for row, status in plan.moved:
            restore(api, row, status)
            back += 1
    return f"Restored {back} item{'' if back == 1 else 's'} from the Trash."
