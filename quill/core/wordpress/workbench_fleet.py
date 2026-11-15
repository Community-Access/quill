"""The Fleet: every site in one list, with what is known, unknown, unavailable or stale (15.12).

Each site's row reads its WordPress version, comments waiting, and four
columns -- **health, backups, security, updates** -- and each of those is in
one of four states, never a guess:

- **known**: the site said it (Site Health's tests, run on request);
- **unknown**: a plugin that might know is on the site (its REST namespace is
  in the index), and QUILL does not read that plugin's data;
- **unavailable**: WordPress has no API for it (core has no backups or
  security API, and its REST API does not report waiting updates), or the
  person's role may not read it;
- **stale**: the site did not answer this time, so the row keeps what it said
  last, with when (:func:`merge_fleet`).

Wx-free; :func:`fleet_fact` runs off the UI thread.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable, Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow

__all__ = ["ASPECTS", "fleet_fact", "fleet_rows", "merge_fleet"]

ASPECTS = ("health", "backups", "security", "updates")

_HEALTH_TESTS = ("background-updates", "loopback-requests", "https-status", "authorization-header")
_BACKUP = re.compile(r"backup|updraft|vaultpress|wpvivid|duplicator|blogvault", re.I)
_SECURITY = re.compile(r"wordfence|security|sucuri|solid|defender|all-in-one-wp", re.I)
_RANK = {"good": 0, "recommended": 1, "critical": 2}
_WORDS = {"good": "good", "recommended": "should be improved", "critical": "critical"}


def _health(api: WordPressApi, namespaces: Iterable[str]) -> str:
    if "wp-site-health/v1" not in set(namespaces):
        return "unavailable: this site has no Site Health API"
    worst = ""
    for test in _HEALTH_TESTS:
        try:
            raw = api.get(f"wp-site-health/v1/tests/{test}")
        except WordPressApiError as exc:
            if exc.status in (401, 403):
                return "unavailable: Site Health needs an administrator"
            continue
        status = str(raw.get("status", "")) if isinstance(raw, dict) else ""
        if status in _RANK and (not worst or _RANK[status] > _RANK[worst]):
            worst = status
    return _WORDS[worst] if worst else "unknown: no Site Health test answered"


def _plugin_state(namespaces: Iterable[str], pattern: re.Pattern[str], what: str) -> str:
    found = sorted(n for n in namespaces if pattern.search(n))
    if found:
        return f"unknown: {', '.join(found)} is on the site; QUILL does not read its {what}"
    return f"unavailable: WordPress has no {what} API"


def fleet_fact(
    api: WordPressApi, version: str, namespaces: Iterable[str], *, now: float | None = None
) -> dict[str, Any]:
    """What one site says for the Fleet, each aspect in its state."""
    spaces = list(namespaces)
    waiting = sum(
        1
        for _c in api.iter_collection(
            "wp/v2/comments", {"status": "hold", "_fields": "id"}, max_pages=1
        )
    )
    return {
        "version": version,
        "waiting": waiting,
        "health": _health(api, spaces),
        "backups": _plugin_state(spaces, _BACKUP, "backups"),
        "security": _plugin_state(spaces, _SECURITY, "security"),
        "updates": "unavailable: WordPress's REST API does not report waiting updates",
        "read_at": time.time() if now is None else now,
    }


def merge_fleet(
    previous: Mapping[str, Mapping[str, Any]], latest: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """The latest facts; a site that did not answer keeps its last answer, marked stale."""
    merged: dict[str, dict[str, Any]] = {}
    for site, fact in latest.items():
        last = previous.get(site)
        if fact.get("error") and last and not last.get("error"):
            merged[site] = {**last, "stale": str(fact["error"])}
        else:
            merged[site] = dict(fact)
    return merged


def _ago(read_at: float, now: float) -> str:
    minutes = max(0, int((now - read_at) // 60))
    if minutes < 1:
        return "under a minute ago"
    if minutes < 120:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    return f"{minutes // 60} hours ago"


def fleet_rows(
    facts: Iterable[tuple[str, Mapping[str, Any]]], *, now: float | None = None
) -> list[WbRow]:
    """The Fleet view, a row a site, with every aspect's state."""
    when = time.time() if now is None else now
    rows: list[WbRow] = []
    for site, fact in facts:
        if fact.get("error"):
            state = f"not answering: {fact['error']}"
            cells = {a: "unknown: the site did not answer" for a in ASPECTS}
        else:
            parts = [f"WordPress {fact.get('version') or 'version not said'}"]
            if fact.get("waiting") is not None:
                parts.append(f"{fact['waiting']} comments waiting")
            if fact.get("stale"):
                read = _ago(float(fact.get("read_at") or when), when)
                parts.insert(0, f"stale, as read {read}; not answering now: {fact['stale']}")
            state = ", ".join(parts)
            cells = {a: str(fact.get(a) or "unknown: not read") for a in ASPECTS}
        detail = f"{site}: {state}." + "".join(f" {a.title()}: {cells[a]}." for a in ASPECTS)
        rows.append(WbRow("fleet", site, site, {"site": site, "state": state, **cells}, detail))
    return rows
