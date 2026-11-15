"""The Events Calendar's event categories and tags in the Workbench.

Through ``tribe/events/v1/categories`` and ``/tags``, whose collections answer
with an object (``{"categories": [...], "total_pages": n}``), like the
events. Each is listed with how many events use it; New (Ctrl+N on its node),
Rename and Delete (for good: terms have no Trash, and the events keep
everything else) are previewed. **Categories and Tags** on an event sets which
it has, by name, sending the ids as the event route takes them
(``categories`` and ``tags`` on ``events/{id}``). Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_events import NAMESPACE, EventDateError
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "TERM_KINDS",
    "event_term_ids",
    "load_event_terms",
    "term_names",
    "terms_by_name",
    "terms_preview",
]

TERM_KINDS: dict[str, tuple[str, str]] = {
    "tribe_category": ("categories", "event category"),
    "tribe_tag": ("tags", "event tag"),
}
"""Row kind -> (route under tribe/events/v1, noun)."""


def collect_terms(api: Any, what: str, params: Mapping[str, object]) -> list[dict[str, Any]]:
    from quill.core.wordpress.workbench_events import collect

    return collect(api, what, params)


def term_row(kind: str, raw: Mapping[str, Any], site: str) -> WbRow:
    name = rendered(raw.get("name")) or "Unnamed"
    count = int(raw.get("count", 0) or 0)
    noun = TERM_KINDS[kind][1]
    return WbRow(
        kind=kind,
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "slug": str(raw.get("slug", "") or ""), "events": str(count)},
        detail=f"The {noun} {name}, on {count} event{'s' if count != 1 else ''}.",
        link=str(raw.get("link", "") or ""),
        subkind="events_calendar",
        raw={
            "name": name,
            "slug": str(raw.get("slug", "") or ""),
            "events": str(count),
            "_loaded": {"name": name},
        },
    )


def load_event_terms(ctx: Any, what: str, query: Mapping[str, object]) -> list[WbRow]:
    """``categories`` or ``tags``; the caller has checked the namespace."""
    kind = "tribe_category" if what == "categories" else "tribe_tag"
    params = {"search": query["search"]} if query.get("search") else {}
    try:
        found = collect_terms(ctx.api, what, {"hide_empty": False, **params})
    except WordPressApiError as exc:
        if exc.status in (401, 403):
            raise WordPressApiError(
                f"{ctx.name} does not let your role read The Events Calendar's {what}.",
                status=exc.status,
            ) from exc
        raise
    return [term_row(kind, raw, ctx.name) for raw in found]


def terms_by_name(text: str, known: Iterable[Mapping[str, Any]], noun: str) -> list[int]:
    """``"Music, Kids"`` -> ids, matched without case; an unknown name is refused, named."""
    by_name = {rendered(t.get("name")).casefold(): t for t in known if isinstance(t, Mapping)}
    wanted = [w.strip() for w in text.split(",") if w.strip()]
    missing = [w for w in wanted if w.casefold() not in by_name]
    if missing:
        raise EventDateError(
            f"The calendar has no {noun} called {', '.join(missing)}. Make it first, with "
            "Ctrl+N on its node."
        )
    return [int(by_name[w.casefold()].get("id", 0) or 0) for w in wanted]


def term_names(items: Any) -> str:
    rows = items if isinstance(items, list) else []
    return ", ".join(rendered(i.get("name")) for i in rows if isinstance(i, Mapping))


def event_term_ids(raw: Mapping[str, Any], key: str) -> list[int]:
    rows = raw.get(key) if isinstance(raw.get(key), list) else []
    return sorted(int(i.get("id", 0) or 0) for i in rows or [] if isinstance(i, Mapping))


def terms_preview(
    title: str, site: str, old: Mapping[str, str], new: Mapping[str, str], changed: Sequence[str]
) -> list[str]:
    lines = [f"{title} on {site}:"]
    for key in changed:
        lines.append(
            f"{key.capitalize()}: {old.get(key) or 'none'} become {new.get(key) or 'none'}."
        )
    lines.append("The event's page and the calendar's filters show the change at once.")
    return lines


def route(kind: str, term_id: int | str = "") -> str:
    base = f"{NAMESPACE}/{TERM_KINDS[kind][0]}"
    return f"{base}/{term_id}" if term_id != "" else base
