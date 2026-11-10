"""Things by name within a site, and Across Sites (PRD 15.12; W8).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Sites > site > By Name**: terms, field values, authors, media usage,
  patterns, links, blocks and shortcodes, and forms, each a node whose rows
  are values, read from one pass over the site
  (:func:`quill.core.wordpress.workbench_across.scan_site`, kept five minutes).
- **Across Sites** (Ctrl+0): tags and categories, plugins, themes, people and
  settings by name over every site or a **Site Set**, each row saying where the
  copies differ; its sheet has **Variants** and **Missing From** pages.
  **Make Them the Same** chooses the variant that wins and previews every
  site's change before anything is sent; on a multisite network a plugin can
  be **Promoted to Network**. **Fleet** reads every site in one list.

Every request runs through ``self.background``; nothing is sent before the
preview's button.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_across import (
    across_rows,
    fleet_rows,
    gather_across,
    kind_rows,
    same_everywhere_plan,
    scan_site,
)
from quill.core.wordpress.workbench_options import load_options, save_options
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchAcrossCommands"]

_SCAN_SECONDS = 300


class WorkbenchAcrossCommands:
    """By Name, Across Sites, Site Sets, Make Them the Same, Promote to Network, Fleet."""

    frame: Any
    parent: Any
    _data_dir: Any
    _profiles: dict[str, Any]
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    write_refusal: Callable[[WbRow, Tier], str]

    # -- within a site --------------------------------------------------------------

    def site_scan(self, site: str) -> Any:
        """Off the UI thread: the site's scan, read again after five minutes."""
        scans: dict[str, tuple[float, Any]] = self.__dict__.setdefault("_scans", {})
        kept = scans.get(site)
        if kept is None or time.time() - kept[0] > _SCAN_SECONDS:
            kept = (time.time(), scan_site(self.ctx(site).api, site))
            scans[site] = kept
        return kept[1]

    def scan_rows(self, site: str, kind: str) -> list[WbRow]:
        """Off the UI thread: one within-site kind."""
        return kind_rows(self.site_scan(site), kind)

    def do_where_used(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "value":
            return
        places = list(row.raw.get("places") or [])
        dlg.show_report(
            self.parent,
            self.show_modal,
            title=f"Where {row.cell('value')} Is Used",
            text="\n".join(places) or "Nowhere in the posts and pages read.",
            help_text="Each post or page that uses it, one a line.",
        )

    # -- across sites ---------------------------------------------------------------

    def scope_sites(self) -> list[str]:
        """The sites Across Sites covers: every site, or the chosen Site Set."""
        options = load_options(self._data_dir)
        chosen = getattr(self, "scope", "")
        members = options.site_sets.get(chosen) if chosen else None
        return [s for s in self._profiles if members is None or s in members]

    def across_list(self, what: str) -> list[WbRow]:
        """Off the UI thread: Across Sites rows for *what*, over the scope."""
        sites = self.scope_sites()
        pairs = [(s, self.ctx(s).api) for s in sites]
        if what == "fleet":
            facts = []
            for site, api in pairs:
                try:
                    ctx = self.ensure(self.ctx(site))
                    waiting = sum(
                        1
                        for _c in api.iter_collection(
                            "wp/v2/comments", {"status": "hold", "_fields": "id"}, max_pages=1
                        )
                    )
                    facts.append((
                        site,
                        {"version": ctx.info.wp_version if ctx.info else "", "waiting": waiting},
                    ))
                except Exception as exc:  # noqa: BLE001 - one row says the site did not answer
                    facts.append((site, {"error": getattr(exc, "plain", "") or str(exc)}))
            return fleet_rows(facts)
        return across_rows(what, gather_across(what, pairs), sites)

    def across_sheet(self, row: WbRow) -> tuple[SheetSpec, dict[str, Any]]:
        variants: dict[str, list[str]] = row.raw.get("variants") or {}
        missing: list[str] = row.raw.get("missing") or []
        sheet = SheetSpec(
            "across",
            row.key,
            (
                PageSpec(
                    "general",
                    "General",
                    (FieldSpec("about", "About", FieldKind.MULTILINE, readonly=True),),
                ),
                PageSpec(
                    "variants",
                    "Variants",
                    (FieldSpec("variants", "Variants", FieldKind.MULTILINE, readonly=True),),
                ),
                PageSpec(
                    "missing",
                    "Missing From",
                    (FieldSpec("missing", "Missing from", FieldKind.MULTILINE, readonly=True),),
                ),
            ),
        )
        values = {
            "about": row.detail,
            "variants": "\n".join(f"{w}: {', '.join(sorted(s))}" for w, s in variants.items()),
            "missing": "\n".join(missing) or "Every site in scope has it.",
        }
        return sheet, values

    def do_make_same(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "across":
            return
        variants = list((row.raw.get("variants") or {}).keys())
        if row.subkind not in ("terms", "plugins", "settings"):
            self.say("Make Them the Same works on terms, plugins and settings in this release.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Make {row.key} the Same",
            prompt="&Which version wins:",
            rows=variants,
            help_text="Every site in scope is changed to match the version you choose.",
        )
        if index is None:
            return
        winner = variants[index]
        plan = same_everywhere_plan(row, winner)
        for site, _words in plan:
            reason = self.write_refusal(WbRow("item", site, "0", {}, ""), Tier.WRITE)
            if reason:
                self.say(reason)
                return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Make {row.key} the Same",
            summary=f"Every site in scope gets {row.key} as {winner}.",
            lines=[f"{site}: {words}" for site, words in plan],
            yes="Make Them the Same",
        ):
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        source = next(
            (objects[s] for s in (row.raw.get("variants") or {}).get(winner, []) if s in objects),
            {},
        )

        def work() -> list[str]:
            failed: list[str] = []
            for site, words in plan:
                if words.startswith("already"):
                    continue
                api = self.ctx(site).api
                mine = objects.get(site)
                try:
                    self._match(api, row.subkind, row.key, source, mine)
                except Exception as exc:  # noqa: BLE001 - one site must not stop the rest
                    failed.append(f"{site}: {getattr(exc, 'plain', '') or exc}")
            return failed

        def done(failed: list[str]) -> None:
            more = f" Not changed: {'; '.join(failed[:3])}" if failed else ""
            self.say(f"{row.key} is the same on every site in scope.{more}")
            self.refresh()

        self.background("making them the same", work, done)

    @staticmethod
    def _match(api: Any, kind: str, name: str, source: Any, mine: Any) -> None:
        if kind == "terms":
            route = "wp/v2/categories" if name.endswith("(category)") else "wp/v2/tags"
            body = {"name": source.get("name"), "slug": source.get("slug")}
            if source.get("description"):
                body["description"] = source["description"]
            if mine is None:
                api.post(route, body)
            else:
                api.post(f"{route}/{mine.get('id')}", body)
        elif kind == "plugins":
            if mine is None:
                raise RuntimeError("installing a plugin is planned; it is not on this site")
            api.post(f"wp/v2/plugins/{mine.get('plugin')}", {"status": source.get("status")})
        elif kind == "settings":
            api.post("wp/v2/settings", {name: source.get("value")})

    def do_promote_network(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "across" or row.subkind != "plugins":
            self.say("Promote to Network works on a plugin, in Across Sites > Plugins.")
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        network = {s: o for s, o in objects.items() if "network_only" in o}
        if not network:
            self.say(f"None of these sites is a multisite network, so {row.key} stays per site.")
            return
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Promote to Network",
            message=f"Activate {row.key} for the whole network on {', '.join(network)}?",
            yes_label="Promote",
        ):
            return

        def work() -> None:
            for site, raw in network.items():
                self.ctx(site).api.post(
                    f"wp/v2/plugins/{raw.get('plugin')}", {"status": "network-active"}
                )

        self.background("promoting to the network", work, lambda _n: self.say("Promoted."))

    # -- Site Sets ----------------------------------------------------------------------

    def do_site_sets(self, _ref: Any, _row: WbRow | None) -> None:
        name = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Site Sets",
            prompt="&Name of the set:",
            help_text="Such as Client sites. A name you have used before changes that set.",
        )
        if not name or not name.strip():
            return
        sites = list(self._profiles)
        options = load_options(self._data_dir)
        current = options.site_sets.get(name.strip(), [])
        picked = wdlg.ask_checks(
            self.parent,
            self.show_modal,
            title=f"Site Set: {name.strip()}",
            prompt="&Sites in the set:",
            rows=sites,
            checked=[i for i, s in enumerate(sites) if s in current],
            help_text="Check each site that belongs to the set. None checked removes the set.",
        )
        if picked is None:
            return
        sets = dict(options.site_sets)
        if picked:
            sets[name.strip()] = [sites[i] for i in picked]
        else:
            sets.pop(name.strip(), None)
        options.site_sets = sets
        save_options(options, self._data_dir)
        self.say(f"{name.strip()}: {len(picked)} sites." if picked else f"Removed {name.strip()}.")

    def do_scope(self, _ref: Any, _row: WbRow | None) -> None:
        sets = list(load_options(self._data_dir).site_sets)
        rows = ["Every site", *sets]
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Across Sites Scope",
            prompt="&Across:",
            rows=rows,
            help_text="Which sites Across Sites and the Fleet cover. Site Sets makes a set.",
        )
        if index is None:
            return
        self.scope = "" if index == 0 else sets[index - 1]
        self.say(f"Across Sites covers {rows[index].lower() if index == 0 else rows[index]}.")
        self.refresh()
