"""Redirects and the 404 log, through the Redirection plugin's REST namespace (PRD 15.11).

Reached only where the site's index lists ``redirection/v1``
(:func:`quill.core.wordpress.workbench_sweep.redirect_offered`); elsewhere the
Redirects node says which plugins keep redirects in their own screens. The
routes and bodies follow the plugin's documented REST API and are **to
verify** against a live install (wordpress.md 19):

- ``GET redirection/v1/redirect`` and ``GET redirection/v1/404``: pages of
  ``{"items": [...], "total": n}``, ``page`` counted from 0, at most 200 a page;
- ``POST redirection/v1/redirect`` makes one, ``POST redirection/v1/redirect/<id>``
  changes one;
- ``POST redirection/v1/bulk/redirect/<enable|disable|delete>`` with
  ``{"items": [ids]}``. The plugin has no Trash, so deleting is tier 3.
- ``GET redirection/v1/group``: ``{"items": [{"id", "name", "module_id",
  "enabled"}], "total": n}``. Every redirect belongs to a group and the plugin
  refuses one without a group it has ("Invalid group", seen live on 5.10.1,
  whose first group was not id 1), so a new redirect goes in the group the
  person picks, :func:`default_group` first.

**Test an Address** (:func:`trace_address`) runs here, on the list as read:
it follows the enabled redirects from an address hop by hop, and names a
chain or a loop. It sends nothing; the plugin's own options (case, trailing
slash, query parameters) decide in the end, which the answer says. Wx-free
and network-free; the reads take an injected API.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "BULK_ACTIONS",
    "MAX_HOPS",
    "default_group",
    "make_first_group",
    "edit_body",
    "group_label",
    "not_found_row",
    "read_groups",
    "read_pages",
    "redirect_row",
    "trace_address",
]

NAMESPACE = "redirection/v1"
MAX_HOPS = 5
BULK_ACTIONS = frozenset({"enable", "disable", "delete"})
_PER_PAGE = 200


def read_pages(api: Any, route: str, *, max_pages: int = 5) -> list[Mapping[str, Any]]:
    """Every item of a Redirection list (``redirect`` or ``404``), page by page from 0."""
    items: list[Mapping[str, Any]] = []
    for page in range(max_pages):
        answer = api.get(f"{NAMESPACE}/{route}", per_page=_PER_PAGE, page=page)
        got = answer.get("items", []) if isinstance(answer, Mapping) else answer
        got = [i for i in got or [] if isinstance(i, Mapping)]
        items.extend(got)
        total = int(answer.get("total", 0) or 0) if isinstance(answer, Mapping) else 0
        if len(got) < _PER_PAGE or (total and len(items) >= total):
            break
    return items


def read_groups(api: Any) -> list[Mapping[str, Any]]:
    """The site's redirect groups, each with an ``id``; disabled ones last."""
    groups = [g for g in read_pages(api, "group", max_pages=2) if g.get("id") not in (None, "")]
    return sorted(groups, key=lambda g: g.get("enabled") is False)


def make_first_group(api: Any) -> int:
    """Make the "Redirections" group the plugin makes on setup, and return its id (0 if not).

    A site whose Redirection setup was never finished has no group, and the plugin
    refuses every redirect without one ("Invalid group"). This is the group its own
    setup would have made: named Redirections, in the WordPress module (1).
    """
    api.post(f"{NAMESPACE}/group", {"name": "Redirections", "moduleId": 1})
    return default_group(read_groups(api))


def default_group(groups: Sequence[Mapping[str, Any]]) -> int:
    """The group a new redirect goes in unless the person picks another; 0 when there is none.

    The first enabled group named "Redirections" (the one the plugin makes on
    install), then the first enabled WordPress-module group, then the first.
    """
    live = [g for g in groups if g.get("enabled") is not False] or list(groups)
    for pick in (
        lambda g: str(g.get("name", "")).strip().casefold() == "redirections",
        lambda g: str(g.get("module_id", "1")) == "1",
        lambda g: True,
    ):
        found = next((g for g in live if pick(g)), None)
        if found is not None:
            return int(found["id"])
    return 0


def group_label(group: Mapping[str, Any]) -> str:
    """A group as a chooser row: its name, and whether it is turned off."""
    name = str(group.get("name", "") or f"Group {group.get('id')}")
    return name + (" (turned off)" if group.get("enabled") is False else "")


def _target(raw: Mapping[str, Any]) -> str:
    data = raw.get("action_data")
    if isinstance(data, Mapping):
        return str(data.get("url", "") or "")
    return str(data or "")


def _enabled(raw: Mapping[str, Any]) -> bool:
    if "enabled" in raw:
        return bool(raw.get("enabled"))
    return str(raw.get("status", "enabled")) != "disabled"


def redirect_row(site: str, raw: Mapping[str, Any], site_url: str) -> WbRow:
    """One redirect: from, to, the code, hits and whether it is on."""
    source = str(raw.get("url", "") or "")
    target = _target(raw)
    code = str(raw.get("action_code", "") or "")
    hits = str(raw.get("hits", raw.get("last_count", 0)) or 0)
    on = _enabled(raw)
    regex = bool(raw.get("regex"))
    last = str(raw.get("last_access", "") or "")
    detail = (
        f"{source} leads to {target or 'nowhere set'} with a {code or 'default'} redirect, "
        f"{'on' if on else 'turned off'}; used {hits} times"
        + (f", last on {friendly_date(last)}" if last and not last.startswith("-") else "")
        + "."
        + (" The source is a pattern (regular expression)." if regex else "")
    )
    link = "" if regex else site_url.rstrip("/") + (source if source.startswith("/") else "")
    return WbRow(
        "redirect",
        site,
        str(raw.get("id", "")),
        {
            "source": source,
            "target": target,
            "code": code,
            "hits": hits,
            "state": "on" if on else "off",
            "title": str(raw.get("title", "") or "") or source,
        },
        detail,
        link=link,
        status="enabled" if on else "disabled",
        raw=dict(raw),
    )


def not_found_row(site: str, raw: Mapping[str, Any], site_url: str) -> WbRow:
    """One 404: the address asked for, when, and where the visitor came from."""
    address = str(raw.get("url", "") or "")
    when = str(raw.get("created", "") or "")
    referrer = str(raw.get("referrer", raw.get("referer", "")) or "")
    detail = (
        f"{address} was asked for and not found"
        + (f" on {friendly_date(when)}" if when else "")
        + (f", from {referrer}" if referrer else ", with no page it came from")
        + ". Redirect This Address makes a redirect from it."
    )
    return WbRow(
        "not_found",
        site,
        str(raw.get("id", "")),
        {"address": address, "when": friendly_date(when) if when else "", "from": referrer},
        detail,
        link=site_url.rstrip("/") + address if address.startswith("/") else address,
        raw=dict(raw),
    )


def edit_body(
    source: str, target: str, code: int = 301, *, group_id: int, regex: bool = False
) -> dict[str, Any]:
    """The Redirection plugin's body for a redirect from *source* to *target*.

    *group_id* is required: a group the site has (:func:`read_groups`).
    """
    path = source.strip()
    if not regex:
        parsed = urlparse(path)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
    return {
        "url": path,
        "action_type": "url",
        "action_code": int(code),
        "action_data": {"url": target.strip()},
        "match_type": "url",
        "group_id": int(group_id),
        "regex": bool(regex),
    }


def _norm(path: str) -> str:
    parsed = urlparse(path.strip())
    value = parsed.path or "/"
    if parsed.query:
        value += f"?{parsed.query}"
    return value.rstrip("/").casefold() or "/"


def _matches(raw: Mapping[str, Any], path: str) -> bool:
    source = str(raw.get("url", "") or "")
    if raw.get("regex"):
        try:
            return re.search(source, path) is not None
        except re.error:
            return False
    return _norm(source) == _norm(path)


def trace_address(address: str, redirects: Sequence[Mapping[str, Any]], site_url: str) -> str:
    """Where *address* ends up through the enabled redirects read, in one sentence or two."""
    host = urlparse(site_url).hostname or ""
    live = [r for r in redirects if _enabled(r)]
    current = address.strip()
    if not current:
        return "Give an address on the site, such as /old-page/."
    hops: list[str] = []
    seen: set[str] = set()
    while len(hops) <= MAX_HOPS:
        parsed = urlparse(current)
        if parsed.hostname and parsed.hostname != host:
            break
        path = (
            current
            if not parsed.scheme
            else (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
        )
        key = _norm(path)
        if key in seen:
            return (
                f"{address} goes round in a loop: {' then '.join(hops)}. Visitors get an "
                "error; change one of these redirects."
            )
        seen.add(key)
        rule = next((r for r in live if _matches(r, path)), None)
        if rule is None:
            break
        target = _target(rule)
        hops.append(f"{rule.get('url')} to {target} ({rule.get('action_code', 301)})")
        current = target
    limit = (
        " Tested here on the list as read; the plugin's own options, such as case, trailing "
        "slashes and query parameters, decide in the end. Open on the Site tries it live."
    )
    if not hops:
        return f"No redirect read from this site matches {address}.{limit}"
    if len(hops) > MAX_HOPS:
        hops_said = " then ".join(hops)
        return f"{address} passes through more than {MAX_HOPS} redirects: {hops_said}.{limit}"
    chain = " A chain: one redirect straight to the end is faster." if len(hops) > 1 else ""
    return f"{address} leads to {current}: {' then '.join(hops)}.{chain}{limit}"
