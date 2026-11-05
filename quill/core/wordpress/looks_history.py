"""Previous Looks for site styles, and undoing a menu change (wordpress.md 9.16).

* **Previous Looks:** the site's styles are one ``wp_global_styles`` post
  whose id the active theme links to (``wp:user-global-styles``); its
  ``revisions`` are the earlier looks, each dated, each with its own palette.
  Going back sends that revision's styles and settings as the current ones,
  which WordPress keeps as a new revision, so going back can itself be undone.
* **Menu history:** a Navigation block is a post with ``revisions`` too. A
  classic menu has none, so QUILL keeps its own: a snapshot each time the Menus
  window reads the menu (:class:`MenuSnapshots`), and Bring Back adds the items
  a later change removed.

Wx-free.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress import navigation as nav
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import friendly_date, raw_text
from quill.core.wordpress.site_report import palette_from_global_styles

# --------------------------------------------------------------------------- #
# Previous Looks


@dataclass(frozen=True)
class Look:
    id: int
    date_gmt: str
    styles: dict[str, Any]
    settings: dict[str, Any]

    def palette(self) -> list[tuple[str, str]]:
        return palette_from_global_styles({"settings": self.settings})[0]

    def spoken(self) -> str:
        colours = len(self.palette())
        return f"{friendly_date(self.date_gmt)}, {colours} colours"

    def palette_report(self) -> str:
        palette = self.palette()
        if not palette:
            return f"The look from {friendly_date(self.date_gmt)} names no colours of its own."
        lines = [f"The look from {friendly_date(self.date_gmt)} has {len(palette)} colours:"]
        lines += [f"{name}: {value}" for name, value in palette]
        return "\n".join(lines)


def styles_id(api: WordPressApi) -> int:
    """The site's own styles post id, from the active theme's links (0 when none)."""
    themes = api.get("wp/v2/themes", status="active")
    for theme in themes if isinstance(themes, list) else []:
        links = theme.get("_links", {}) if isinstance(theme, dict) else {}
        for link in links.get("wp:user-global-styles", []) if isinstance(links, dict) else []:
            href = str(link.get("href", "")) if isinstance(link, dict) else ""
            tail = href.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
            if tail.isdigit():
                return int(tail)
    return 0


def list_looks(api: WordPressApi, styles: int) -> list[Look]:
    rows = api.get(f"wp/v2/global-styles/{styles}/revisions", context="edit")
    looks = [
        Look(
            id=int(raw.get("id", 0)),
            date_gmt=str(raw.get("modified_gmt") or raw.get("date_gmt") or ""),
            styles=_mapping(raw.get("styles")),
            settings=_mapping(raw.get("settings")),
        )
        for raw in (rows if isinstance(rows, list) else [])
        if isinstance(raw, dict)
    ]
    return sorted(looks, key=lambda look: look.date_gmt, reverse=True)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def restore_look(api: WordPressApi, styles: int, look: Look) -> None:
    api.post(f"wp/v2/global-styles/{styles}", {"styles": look.styles, "settings": look.settings})


# --------------------------------------------------------------------------- #
# Navigation block revisions


@dataclass(frozen=True)
class MenuVersion:
    """An earlier state of a menu: a Navigation revision or a QUILL snapshot."""

    stamp: str
    nodes: tuple[tuple[str, str, int, str], ...]  # (title, kind, object id, url), flattened
    content: str = ""  # a Navigation revision's block markup
    revision_id: int = 0

    def spoken(self, current: nav.Menu) -> str:
        now = {_flat(r.node) for r in nav.rows(current.nodes)}
        gone = [n for n in self.nodes if n not in now]
        change = f", {len(gone)} items since removed" if gone else ", same items as now"
        return f"{friendly_date(self.stamp)}, {len(self.nodes)} items{change}"

    def missing_from(self, current: nav.Menu) -> list[tuple[str, str, int, str]]:
        now = {_flat(r.node) for r in nav.rows(current.nodes)}
        return [n for n in self.nodes if n not in now]


def _flat(node: nav.MenuNode) -> tuple[str, str, int, str]:
    return (node.title, node.kind, node.object_id, node.url)


def flatten(nodes: list[nav.MenuNode]) -> tuple[tuple[str, str, int, str], ...]:
    return tuple(_flat(r.node) for r in nav.rows(nodes) if r.node.kind != "other")


def navigation_versions(api: WordPressApi, menu: nav.Menu) -> list[MenuVersion]:
    try:
        rows = api.get(f"wp/v2/navigation/{menu.id}/revisions", context="edit")
    except WordPressApiError as exc:
        if exc.status in (401, 403, 404):
            return []
        raise
    out: list[MenuVersion] = []
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        content = raw_text(raw.get("content"))
        out.append(
            MenuVersion(
                stamp=str(raw.get("modified_gmt") or raw.get("date_gmt") or ""),
                nodes=flatten(nav.navigation_nodes(content)),
                content=content,
                revision_id=int(raw.get("id", 0)),
            )
        )
    return sorted(out, key=lambda v: v.stamp, reverse=True)


def restore_navigation(api: WordPressApi, menu: nav.Menu, version: MenuVersion) -> None:
    api.post(f"wp/v2/navigation/{menu.id}", {"content": version.content})


def bring_back(api: WordPressApi, menu: nav.Menu, version: MenuVersion) -> list[str]:
    """Add back, at the end, every item *version* had that the menu has lost."""
    added: list[str] = []
    for title, kind, object_id, url in version.missing_from(menu):
        nav.add_item(api, menu, nav.MenuNode(title, kind, object_id, url=url))
        added.append(title)
    return added


# --------------------------------------------------------------------------- #
# QUILL's own snapshots of classic menus


class MenuSnapshots:
    """Each classic menu as the Menus window last read it, newest first, at most 20."""

    LIMIT = 20

    def __init__(self, base: Path | None = None) -> None:
        self.path = (base or app_data_dir()) / "wordpress" / "menu-history.json"

    def _all(self) -> dict[str, list[dict[str, Any]]]:
        raw = read_json(self.path, default={})
        return raw if isinstance(raw, dict) else {}

    def remember(self, site_id: str, menu: nav.Menu, stamp: str) -> bool:
        """Keep *menu* as it is now, unless it is the same as the last one kept."""
        if menu.source != "classic":
            return False
        nodes = [list(n) for n in flatten(menu.nodes)]
        digest = hashlib.sha1(json.dumps(nodes).encode(), usedforsecurity=False).hexdigest()
        every = self._all()
        key = f"{site_id}/{menu.id}"
        kept = every.get(key, [])
        if kept and kept[0].get("digest") == digest:
            return False
        kept.insert(0, {"stamp": stamp, "digest": digest, "nodes": nodes})
        every[key] = kept[: self.LIMIT]
        write_json_atomic(self.path, every)
        return True

    def versions(self, site_id: str, menu: nav.Menu) -> list[MenuVersion]:
        kept = self._all().get(f"{site_id}/{menu.id}", [])
        out: list[MenuVersion] = []
        for entry in kept:
            nodes = tuple(
                (str(n[0]), str(n[1]), int(n[2]), str(n[3]))
                for n in entry.get("nodes", [])
                if isinstance(n, list) and len(n) == 4
            )
            out.append(MenuVersion(stamp=str(entry.get("stamp", "")), nodes=nodes))
        return out
