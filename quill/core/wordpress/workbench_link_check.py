"""Check Every Link: the whole site's links, under By Name > Links (wp_missing.md, Tools).

Needs My Attention > Broken Links checks a sample (the first
:data:`~quill.core.wordpress.link_targets.MAX_LINKS` unique links of the
newest published posts and pages) so that opening the node stays quick. This
is the same check with no sample: every published post, page and custom item
is read, page after page, every distinct web address in them is asked of the
site's own ``wp-block-editor/v1/url-details`` route
(:func:`quill.core.wordpress.link_targets.read_target`, the checker behind
Broken Links and Check This Page), and each address that leads nowhere comes
back with every item that holds it.

It runs off the UI thread and can be stopped: *stop* is checked before each
item page and each address, and *progress* hears the count as it goes, so
the status bar can say it. A stopped check keeps what it found. Wx-free.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.link_targets import URL_DETAILS, links_in, read_target
from quill.core.wordpress.site import kind_route, raw_text, rendered

__all__ = [
    "BrokenLink",
    "Holder",
    "LinkCheck",
    "StopFlag",
    "check_links",
    "collect_links",
    "has_link_route",
    "kinds_for",
    "outcome",
]


class StopFlag(Protocol):
    def is_set(self) -> bool: ...


@dataclass(frozen=True)
class Holder:
    """An item that holds a link."""

    item_id: int
    kind: str
    title: str
    link: str


@dataclass(frozen=True)
class BrokenLink:
    url: str
    why: str
    holders: tuple[Holder, ...]

    def spoken(self) -> str:
        where = ", ".join(f"{h.title} ({h.kind})" for h in self.holders[:5])
        more = len(self.holders) - 5
        if more > 0:
            where += f" and {more} more"
        return f"{self.url}, in {where}: {self.why.rstrip('.')}."


@dataclass
class LinkCheck:
    """What a run found; *stopped* when it was stopped before the end."""

    items: int = 0
    links: int = 0
    checked: int = 0
    broken: list[BrokenLink] = field(default_factory=list)
    stopped: bool = False


def has_link_route(api: Any) -> bool:
    """Whether the site offers the link-check route at all."""
    index = api.get("")
    routes = index.get("routes") if isinstance(index, dict) else None
    return isinstance(routes, dict) and f"/{URL_DETAILS}" in routes


def _web(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for link in links_in(text, "html"):
        if link.url.lower().startswith(("http://", "https://")):
            seen.setdefault(link.url, None)
    return list(seen)


def collect_links(
    api: Any, kinds: Sequence[str], *, stop: StopFlag | None = None
) -> tuple[dict[str, list[Holder]], int]:
    """Every web address in the published items of *kinds*, with who holds it; and the count."""
    found: dict[str, list[Holder]] = {}
    items = 0
    for kind in kinds:
        params = {"status": "publish", "context": "edit", "_fields": "id,title,content,link"}
        try:
            for raw in api.iter_collection(kind_route(kind), params):
                if stop is not None and stop.is_set():
                    return found, items
                items += 1
                content = raw.get("content")
                title = raw_text(raw.get("title")) or rendered(raw.get("title")) or "(untitled)"
                holder = Holder(
                    int(raw.get("id", 0) or 0), kind, title, str(raw.get("link", "") or "")
                )
                for url in _web(raw_text(content) or rendered(content)):
                    found.setdefault(url, []).append(holder)
        except WordPressApiError as exc:
            if exc.status not in (401, 403, 404):  # a type this account cannot read is skipped
                raise
    return found, items


def check_links(
    api: Any,
    found: dict[str, list[Holder]],
    *,
    items: int = 0,
    stop: StopFlag | None = None,
    progress: Callable[[int, int, int], None] | None = None,
) -> LinkCheck:
    """Ask the site about each address; *progress* hears (checked, of, broken so far)."""
    result = LinkCheck(items=items, links=len(found))
    for url, holders in found.items():
        if stop is not None and stop.is_set():
            result.stopped = True
            break
        target = read_target(api, url)
        result.checked += 1
        if not target.reachable:
            result.broken.append(BrokenLink(url, target.why, tuple(holders)))
        if progress is not None:
            progress(result.checked, result.links, len(result.broken))
    return result


def outcome(site: str, result: LinkCheck) -> str:
    """The run in one sentence."""
    broken = len(result.broken)
    noun = "link leads" if broken == 1 else "links lead"
    if result.stopped:
        return (
            f"Stopped after {result.checked} of {result.links} links on {site}; "
            f"{broken} {noun} nowhere so far."
        )
    if not result.links:
        return f"{site}'s {result.items} published items link to no other pages."
    if not broken:
        return f"All {result.links} links in {site}'s {result.items} published items work."
    return f"{broken} of {result.links} links on {site} lead nowhere."


def kinds_for(extra: Iterable[str] = ()) -> list[str]:
    """Posts and pages, then any custom types the site has (each once)."""
    kinds = ["post", "page"]
    for kind in extra:
        if kind and kind not in kinds and kind not in ("attachment", "wp_block"):
            kinds.append(kind)
    return kinds
