"""Watches (PRD 15.7, W7): what changed on your sites since you last looked.

Every Watch is off until the person turns it on in Workbench Options, which
is the consent: nothing is asked of any site for Watches before that. The
editor's existing two-minute WordPress timer (``start_repeating``, which
already drives autosave and the offline queue) asks :func:`due` whether a
round is due, at most every ``watch_minutes`` of Workbench Options and never
more often than :data:`MIN_MINUTES`, and then runs :func:`check` off the UI
thread. Each round reads a little from every connected site and compares it
with what the last round saw (:class:`WatchState`, kept in
``workbench_watches.json`` beside the site list):

- ``comment``: comments waiting that were not waiting before;
- ``form_response``: form entries newer than the newest seen (QAF, Gravity Forms);
- ``update``: plugins whose answer carries a newer version (a site that says);
- ``published``: scheduled posts and pages that are published now;
- ``site_down``: a site that stops answering, said once, and said again
  once when it answers again;
- ``review``: an item given a reviewer that has left the queue (published,
  scheduled, sent back or trashed);
- ``health``: a Site Health test whose status changed (good, should be
  improved, critical), by test, from the same ``wp-site-health/v1`` routes
  the Site Health node and :mod:`~quill.core.wordpress.workbench_health_info`
  use. Only an administrator can run them; for anyone else it stays quiet.
- ``form_spam``: once a week, QUILL Accessible Forms' question numbers for
  the week that ended, against the week before (``qaf/v1/spam/weeks``); a
  QAF older than that route stays quiet.
- ``order``, ``low_stock``, ``certificate``, ``abandoned``, ``statement`` and
  ``weekly``: the shop, the site's security certificate, plugins that may be
  abandoned, the accessibility statement and a weekly sentence, in
  :mod:`quill.core.wordpress.workbench_watches_more`.

The first sample of each Watch on each site is silent -- turning a Watch on,
or connecting a site, only learns what is there -- and a change is said once,
not every round. A site that does not answer keeps its last state, so its
backlog is not announced as new when it returns. :func:`status_facts` says
where Watches stand: when they last ran, whether that is stale, and each
site's answering state. What comes back are sentences with counts, which are
always spoken (the shared feedback rule: no tone carries a number).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.sites import sites_path
from quill.core.wordpress.workbench_watches_more import MORE_KINDS, WatchContext, more_round

__all__ = [
    "KINDS",
    "MIN_MINUTES",
    "WatchState",
    "check",
    "due",
    "first_sample",
    "load_state",
    "plugin_updates",
    "save_state",
    "status_facts",
    "waiting_comments",
]

MIN_MINUTES = 15
KINDS: Mapping[str, str] = {
    "comment": "New comments waiting",
    "form_response": "New form responses",
    "update": "Plugin updates available",
    "published": "Scheduled posts going live",
    "site_down": "A site not answering, and answering again",
    "review": "Items with a reviewer leaving the queue",
    "health": "Site Health status changes",
    "form_spam": "Form spam questions, once a week",
    **MORE_KINDS,
}
_KIND_STATE = {
    "comment": "waiting",
    "form_response": "newest_entry",
    "update": "updates",
    "published": "scheduled",
}


@dataclass
class WatchState:
    """What the last round saw, by site name."""

    waiting: dict[str, list[int]] = field(default_factory=dict)
    newest_entry: dict[str, int] = field(default_factory=dict)
    updates: dict[str, list[str]] = field(default_factory=dict)
    scheduled: dict[str, list[int]] = field(default_factory=dict)
    last_round: float = 0.0
    #: "site:kind" once that Watch has its first sample there ("site" alone: older files).
    seen: list[str] = field(default_factory=list)
    #: Site -> when it stopped answering.
    down: dict[str, float] = field(default_factory=dict)
    #: Site -> when it last answered.
    answered: dict[str, float] = field(default_factory=dict)
    #: "site:id" -> the status a reviewed item had last round.
    reviews: dict[str, str] = field(default_factory=dict)
    #: Site -> {Site Health test: status} last round.
    health: dict[str, dict[str, str]] = field(default_factory=dict)
    #: Site -> the QAF spam week (2026-W46) that was current last round.
    spam_weeks: dict[str, str] = field(default_factory=dict)
    #: The later Watches' memory (workbench_watches_more): kind -> site -> what was seen.
    extra: dict[str, dict[str, Any]] = field(default_factory=dict)


def _path(base: Path | None) -> Path:
    return sites_path(base).parent / "workbench_watches.json"


def _floats(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    found: dict[str, float] = {}
    for key, value in raw.items():
        try:
            found[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return found


def load_state(base: Path | None = None) -> WatchState:
    raw = read_json(_path(base), default={})
    if not isinstance(raw, dict):
        return WatchState()

    def ints(name: str) -> dict[str, list[int]]:
        got = raw.get(name)
        if not isinstance(got, dict):
            return {}
        return {str(k): [int(i) for i in v] for k, v in got.items() if isinstance(v, list)}

    entries = raw.get("newest_entry")
    updates = raw.get("updates")
    seen = raw.get("seen")
    reviews = raw.get("reviews")
    return WatchState(
        waiting=ints("waiting"),
        newest_entry={str(k): int(v) for k, v in entries.items()}
        if isinstance(entries, dict)
        else {},
        updates={str(k): [str(x) for x in v] for k, v in updates.items() if isinstance(v, list)}
        if isinstance(updates, dict)
        else {},
        scheduled=ints("scheduled"),
        last_round=float(raw.get("last_round", 0.0) or 0.0),
        seen=[str(s) for s in seen] if isinstance(seen, list) else [],
        down=_floats(raw.get("down")),
        answered=_floats(raw.get("answered")),
        reviews={str(k): str(v) for k, v in reviews.items()} if isinstance(reviews, dict) else {},
        health=_health_state(raw.get("health")),
        spam_weeks={str(k): str(v) for k, v in raw["spam_weeks"].items()}
        if isinstance(raw.get("spam_weeks"), dict)
        else {},
        extra={str(k): dict(v) for k, v in raw["extra"].items() if isinstance(v, dict)}
        if isinstance(raw.get("extra"), dict)
        else {},
    )


def _health_state(raw: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    return {
        str(site): {str(k): str(v) for k, v in tests.items()}
        for site, tests in raw.items()
        if isinstance(tests, dict)
    }


def save_state(state: WatchState, base: Path | None = None) -> None:
    write_json_atomic(
        _path(base),
        {
            "waiting": state.waiting,
            "newest_entry": state.newest_entry,
            "updates": state.updates,
            "scheduled": state.scheduled,
            "last_round": state.last_round,
            "seen": state.seen,
            "down": state.down,
            "answered": state.answered,
            "reviews": state.reviews,
            "health": state.health,
            "spam_weeks": state.spam_weeks,
            "extra": state.extra,
        },
    )


def due(state: WatchState, minutes: int, *, now: Callable[[], float] = time.time) -> bool:
    """Whether a round is due: never sooner than :data:`MIN_MINUTES` after the last."""
    return now() - state.last_round >= max(MIN_MINUTES, minutes) * 60


def _ids(api: WordPressApi, route: str, params: Mapping[str, object]) -> list[int]:
    return [
        int(raw.get("id", 0) or 0)
        for raw in api.iter_collection(
            route, {**params, "_fields": "id"}, per_page=100, max_pages=1
        )
    ]


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def first_sample(state: WatchState, site: str, kind: str) -> bool:
    """True the first time a Watch samples a site; marks it sampled."""
    key = f"{site}:{kind}"
    if key in state.seen:
        return False
    older = site in state.seen and site in getattr(state, _KIND_STATE.get(kind, "down"), {})
    state.seen.append(key)
    return not older


_first = first_sample


def waiting_comments(api: WordPressApi) -> list[int]:
    """The ids of the comments waiting for approval (the first hundred)."""
    return _ids(api, "wp/v2/comments", {"status": "hold"})


def check(
    sites: Iterable[tuple[str, WordPressApi, Sequence[str]]],
    state: WatchState,
    kinds: Iterable[str],
    *,
    unreachable: Iterable[str] = (),
    reviews: Sequence[Any] = (),
    now: Callable[[], float] = time.time,
    context: WatchContext | None = None,
) -> list[str]:
    """One round over *sites* ((name, client, namespaces)); the sentences worth saying.

    *unreachable* names the sites that did not answer this round; *reviews*
    are the assignments (:class:`~quill.core.wordpress.workbench_editorial.Review`)
    the ``review`` Watch follows; *context* carries the local check history
    and the certificate and WordPress.org readers the later Watches use.
    """
    wanted = set(kinds)
    said: list[str] = []
    moment = now()
    ctx = context or WatchContext()
    ctx.now = moment
    for site in unreachable:
        if site not in state.down:
            state.down[site] = moment
            if "site_down" in wanted and not _first(state, site, "site_down"):
                said.append(f"{site} is not answering. Watches will try again next round.")
    for site, api, namespaces in sites:
        if site in state.down:
            state.down.pop(site)
            if "site_down" in wanted and not _first(state, site, "site_down"):
                said.append(f"{site} answers again.")
        elif "site_down" in wanted:
            _first(state, site, "site_down")
        state.answered[site] = moment
        try:
            said += _site_round(site, api, namespaces, state, wanted, reviews)
            said += more_round(site, api, namespaces, state, wanted, ctx)
        except WordPressApiError:
            continue
    state.last_round = moment
    return said


def _site_round(
    site: str,
    api: WordPressApi,
    namespaces: Sequence[str],
    state: WatchState,
    wanted: set[str],
    reviews: Sequence[Any],
) -> list[str]:
    said: list[str] = []
    if "comment" in wanted:
        waiting = waiting_comments(api)
        new = set(waiting) - set(state.waiting.get(site, []))
        first = _first(state, site, "comment")
        state.waiting[site] = waiting
        if new and not first:
            said.append(f"{_plural(len(new), 'new comment', 'new comments')} waiting on {site}.")
    if "published" in wanted:
        scheduled = _ids(api, "wp/v2/posts", {"status": "future"}) + _ids(
            api, "wp/v2/pages", {"status": "future"}
        )
        gone = set(state.scheduled.get(site, [])) - set(scheduled)
        first = _first(state, site, "published")
        state.scheduled[site] = scheduled
        if gone and not first:
            live = _published(api, gone)
            if live:
                said.append(f"Now published on {site}: {', '.join(live)}.")
    if "form_response" in wanted:
        newest = _newest_entry(api, namespaces)
        before = state.newest_entry.get(site, 0)
        first = _first(state, site, "form_response")
        state.newest_entry[site] = max(before, newest)
        if newest > before and not first:
            said.append(f"A new form response on {site}.")
    if "update" in wanted:
        updates = plugin_updates(api)
        new_updates = sorted(set(updates) - set(state.updates.get(site, [])))
        first = _first(state, site, "update")
        state.updates[site] = updates
        if new_updates and not first:
            said.append(f"Updates available on {site}: {', '.join(new_updates)}.")
    if "review" in wanted:
        said += _reviews(site, api, state, [r for r in reviews if r.site == site])
    if "health" in wanted:
        said += _health(site, api, state)
    if "form_spam" in wanted:  # QAF's weekly numbers (workbench_qaf_spam_edit.weekly_watch)
        from quill.core.wordpress.workbench_qaf_spam_edit import weekly_watch

        week, spoken = weekly_watch(site, api, namespaces, state.spam_weeks.get(site, ""))
        if week:
            state.spam_weeks[site] = week
        said += spoken
    return said


_HEALTH_WORDS = {"critical": "critical", "recommended": "should be improved", "good": "good"}


def _health(site: str, api: WordPressApi, state: WatchState) -> list[str]:
    """Site Health tests whose status changed since the last round, by test."""
    from quill.core.wordpress.site_health import TEST_NAMES, health_test_names

    index = api.get("")
    index = index if isinstance(index, dict) else {}
    if "wp-site-health/v1" not in [str(n) for n in index.get("namespaces", []) or []]:
        return []
    now: dict[str, str] = {}
    for test in health_test_names(index):
        try:
            raw = api.get(f"wp-site-health/v1/tests/{test}")
        except WordPressApiError as exc:
            if exc.status in (401, 403):
                return []  # only an administrator may run them: nothing to watch
            continue
        status = str(raw.get("status", "")) if isinstance(raw, dict) else ""
        if status in _HEALTH_WORDS:
            now[test] = status
    first = _first(state, site, "health")
    before = state.health.get(site, {})
    state.health[site] = now
    if first:
        return []
    changed = [
        f"{TEST_NAMES.get(test, test.replace('-', ' '))} is now {_HEALTH_WORDS[status]}"
        for test, status in now.items()
        if test in before and before[test] != status
    ]
    return [f"Site Health on {site}: {'; '.join(changed)}."] if changed else []


_LEFT = {
    "publish": "was published",
    "future": "was approved and scheduled",
    "draft": "was sent back to its writer",
    "trash": "was moved to the Trash",
    "private": "was published privately",
}


def _reviews(site: str, api: WordPressApi, state: WatchState, mine: Sequence[Any]) -> list[str]:
    from quill.core.wordpress.workbench_editorial import queue_status

    said: list[str] = []
    for review in mine:
        key = f"{site}:{review.item_id}"
        status = queue_status(api, review)
        if not status:
            continue
        before = state.reviews.get(key)
        state.reviews[key] = status
        if before == "pending" and status in _LEFT:
            said.append(f"{review.title} on {site} {_LEFT[status]}.")
    return said


def status_facts(
    state: WatchState,
    sites: Sequence[str],
    minutes: int,
    *,
    now: Callable[[], float] = time.time,
) -> list[tuple[str, str]]:
    """Where Watches stand: the last round (and whether it is stale), and each site."""
    every = max(MIN_MINUTES, minutes)
    moment = now()
    if not state.last_round:
        facts = [("Last round", "none yet")]
    else:
        ago = int((moment - state.last_round) // 60)
        said = f"{_when(state.last_round)}, {ago} minutes ago"
        if moment - state.last_round > 2 * every * 60:
            said += "; that is stale: QUILL was closed, asleep or offline since"
        facts = [("Last round", said)]
    for site in sites:
        if site in state.down:
            facts.append((site, f"not answering since {_when(state.down[site])}"))
        elif site in state.answered:
            facts.append((site, f"answering; last heard {_when(state.answered[site])}"))
        else:
            facts.append((site, "not checked yet"))
    return facts


def _when(stamp: float) -> str:
    return time.strftime("%d %B, %H:%M", time.localtime(stamp)).lstrip("0")


def _published(api: WordPressApi, ids: Iterable[int]) -> list[str]:
    titles: list[str] = []
    for route in ("wp/v2/posts", "wp/v2/pages"):
        try:
            found = api.get(route, include=sorted(ids), status="publish", _fields="id,title")
        except WordPressApiError:
            continue
        for raw in found if isinstance(found, list) else []:
            title = raw.get("title")
            titles.append(str(title.get("rendered", "") if isinstance(title, dict) else title))
    return titles


def _newest_entry(api: WordPressApi, namespaces: Sequence[str]) -> int:
    clean = {n.strip("/") for n in namespaces}
    for namespace, route in (
        ("qaf/v1", "qaf/v1/entries"),
        ("baf/v1", "baf/v1/entries"),
        ("gf/v2", "gf/v2/entries"),
    ):
        if namespace not in clean:
            continue
        found = api.get(route, per_page=1, orderby="id", order="desc")
        rows: Any = found.get("entries") if isinstance(found, dict) else found
        for raw in rows if isinstance(rows, list) else []:
            return int(raw.get("id", 0) or 0)
    return 0


def plugin_updates(api: WordPressApi) -> list[str]:
    """Plugins whose answer says a newer version waits (sites that report it)."""
    names: list[str] = []
    for raw in api.iter_collection("wp/v2/plugins", {}, per_page=100, max_pages=1):
        update = raw.get("update") or raw.get("new_version")
        if update:
            name = raw.get("name")
            label = name.get("rendered", "") if isinstance(name, dict) else str(name or "")
            names.append(label or str(raw.get("plugin", "")))
    return names
