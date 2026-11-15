"""Site to site, a local snapshot, the calendar, Read Site as Document (PRD 15.2 to 15.5; W7).

The bold workflows' wx-free entry point, which the Workbench calls off the UI
thread. Each workflow lives in its own module and is re-exported here:

- **Copy to Site** (:mod:`~quill.core.wordpress.workbench_site_copy`):
  matched by address or name, authors mapped, pictures uploaded, links
  pointed at the target, every create, replace and skip in the preview.
- **Compare Sites, Take a Snapshot, Put Back from a Snapshot**
  (:mod:`~quill.core.wordpress.workbench_snapshot`), each stating what it
  covers and what it does not.
- **The calendar** (:func:`calendar_days`, below): each day with scheduled and
  published content, across every site and every type the site names,
  "Tuesday 12 November: 2 scheduled, 1 published"; a site that would not
  answer is named, not dropped.
- **Read Site as Document** (:mod:`~quill.core.wordpress.workbench_read_site`):
  the whole site, a menu or a category as one Markdown document.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_read_site import site_document
from quill.core.wordpress.workbench_site_copy import (
    COPYABLE,
    CopyLine,
    CopyPlan,
    fetch_site_file,
    plan_copy,
    rewrite_links,
    run_copy,
)
from quill.core.wordpress.workbench_snapshot import (
    Difference,
    compare_sites,
    snapshot_counts_words,
    take_snapshot,
)

__all__ = [
    "COPYABLE",
    "CopyLine",
    "CopyPlan",
    "Difference",
    "as_json",
    "calendar_days",
    "compare_sites",
    "day_words",
    "fetch_site_file",
    "plan_copy",
    "rewrite_links",
    "run_copy",
    "site_document",
    "snapshot_counts_words",
    "take_snapshot",
]


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
    kinds_by_site: dict[str, Sequence[str]] | None = None,
    failures: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Each day (``2026-11-12``) with its scheduled and published items, from every site.

    *since* is the first day (ISO date) published items count from; every
    scheduled item counts, however far ahead. The day is the site's own date
    (WordPress's ``date``), so a post at 11 PM on the site falls on the site's
    day whatever this computer's zone is. *kinds_by_site* gives a site's own
    types (custom ones included); a site or type that would not answer is a
    sentence in *failures*.
    """
    days: dict[str, list[dict[str, Any]]] = {}
    for site, api in sites:
        for kind in (kinds_by_site or {}).get(site, kinds):
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
                except WordPressApiError as exc:
                    if failures is not None:
                        failures.append(f"{site}, {kind}: {exc.plain or exc}")
                    break
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


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)
