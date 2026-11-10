"""Watches (PRD 15.7, W7): what changed on your sites since you last looked.

The editor's existing two-minute WordPress timer (``start_repeating``, which
already drives autosave and the offline queue) asks :func:`due` whether a
watch round is due, at most every ``watch_minutes`` of Workbench Options
(never more often than fifteen), and then runs :func:`check` off the
UI thread. Each round reads a little from every connected site and compares
it with what the last round saw (:class:`WatchState`, kept in
``workbench_watches.json`` beside the site list):

- ``comment``: comments waiting that were not waiting before;
- ``form_response``: form entries newer than the newest seen (QAF, Gravity Forms);
- ``update``: plugins whose answer carries a newer version (a site that says);
- ``published``: scheduled posts and pages that are published now.

The first round only learns what is there, so turning Watches on does not
announce a site's whole history. A site that does not answer is skipped
quietly and tried next round. What comes back are sentences with counts,
which are always spoken (the shared feedback rule: no tone carries a number).
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

__all__ = [
    "KINDS",
    "MIN_MINUTES",
    "WatchState",
    "check",
    "due",
    "load_state",
    "save_state",
]

MIN_MINUTES = 15
KINDS: Mapping[str, str] = {
    "comment": "New comments waiting",
    "form_response": "New form responses",
    "update": "Plugin updates available",
    "published": "Scheduled posts going live",
}


@dataclass
class WatchState:
    """What the last round saw, by site name."""

    waiting: dict[str, list[int]] = field(default_factory=dict)
    newest_entry: dict[str, int] = field(default_factory=dict)
    updates: dict[str, list[str]] = field(default_factory=dict)
    scheduled: dict[str, list[int]] = field(default_factory=dict)
    last_round: float = 0.0
    seen: list[str] = field(default_factory=list)


def _path(base: Path | None) -> Path:
    return sites_path(base).parent / "workbench_watches.json"


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
    )


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


def check(
    sites: Iterable[tuple[str, WordPressApi, Sequence[str]]],
    state: WatchState,
    kinds: Iterable[str],
    *,
    now: Callable[[], float] = time.time,
) -> list[str]:
    """One round over *sites* ((name, client, namespaces)); the sentences worth saying."""
    wanted = set(kinds)
    said: list[str] = []
    for site, api, namespaces in sites:
        first = site not in state.seen
        try:
            if "comment" in wanted:
                waiting = _ids(api, "wp/v2/comments", {"status": "hold"})
                new = set(waiting) - set(state.waiting.get(site, []))
                state.waiting[site] = waiting
                if new and not first:
                    said.append(
                        f"{_plural(len(new), 'new comment', 'new comments')} waiting on {site}."
                    )
            if "published" in wanted:
                scheduled = _ids(api, "wp/v2/posts", {"status": "future"}) + _ids(
                    api, "wp/v2/pages", {"status": "future"}
                )
                gone = set(state.scheduled.get(site, [])) - set(scheduled)
                state.scheduled[site] = scheduled
                if gone and not first:
                    live = _published(api, gone)
                    if live:
                        said.append(f"Now published on {site}: {', '.join(live)}.")
            if "form_response" in wanted:
                newest = _newest_entry(api, namespaces)
                before = state.newest_entry.get(site, 0)
                state.newest_entry[site] = max(before, newest)
                if newest > before and not first:
                    said.append(f"A new form response on {site}.")
            if "update" in wanted:
                updates = _updates(api)
                new_updates = sorted(set(updates) - set(state.updates.get(site, [])))
                state.updates[site] = updates
                if new_updates and not first:
                    said.append(f"Updates available on {site}: {', '.join(new_updates)}.")
        except WordPressApiError:
            continue
        if first:
            state.seen.append(site)
    state.last_round = now()
    return said


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


def _updates(api: WordPressApi) -> list[str]:
    """Plugins whose answer says a newer version waits (sites that report it)."""
    names: list[str] = []
    for raw in api.iter_collection("wp/v2/plugins", {}, per_page=100, max_pages=1):
        update = raw.get("update") or raw.get("new_version")
        if update:
            name = raw.get("name")
            label = name.get("rendered", "") if isinstance(name, dict) else str(name or "")
            names.append(label or str(raw.get("plugin", "")))
    return names
