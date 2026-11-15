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
    gather_across,
    kind_rows,
    same_everywhere_plan,
    scan_site,
)
from quill.core.wordpress.workbench_across_ops import (
    MAKE_SAME_KINDS,
    compare_styles,
    make_same_edits,
    menu_copy,
    network_refusal,
    network_status,
    revoke_plan,
    run_edits_by_site,
    site_styles,
    theme_screens,
)
from quill.core.wordpress.workbench_by_name import Edit, Outcome, undo_edits
from quill.core.wordpress.workbench_fleet import fleet_fact, fleet_rows, merge_fleet
from quill.core.wordpress.workbench_options import load_options, save_options
from quill.core.wordpress.workbench_permissions import refusal
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_scope_matrix import classify
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg
from quill.ui.wordpress_workbench_by_name import WorkbenchByNameCommands

__all__ = ["WorkbenchAcrossCommands"]

_SCAN_SECONDS = 300
_MAKE_SAME_NEEDS = {
    "terms": "manage_categories",
    "plugins": "activate_plugins",
    "settings": "manage_options",
    "users": "promote_users",
    "patterns": "edit_posts",
    "menus": "edit_theme_options",
    "themes": "switch_themes",
    "role_pages": "edit_others_pages",
    "redirects": "manage_options",
    "spam_senders": "manage_options",
}


class WorkbenchAcrossCommands(WorkbenchByNameCommands):
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
    account_for: Callable[[str], Any]
    history: Any

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
            latest: dict[str, dict[str, Any]] = {}
            for site, api in pairs:
                try:
                    ctx = self.ensure(self.ctx(site))
                    info = ctx.info
                    latest[site] = fleet_fact(
                        api,
                        info.wp_version if info else "",
                        info.namespaces if info else (),
                    )
                except Exception as exc:  # noqa: BLE001 - one row says the site did not answer
                    latest[site] = {"error": getattr(exc, "plain", "") or str(exc)}
            kept: dict[str, Any] = self.__dict__.setdefault("_fleet", {})
            merged = merge_fleet(kept, latest)
            kept.update({s: f for s, f in merged.items() if not f.get("stale")})
            return fleet_rows(list(merged.items()))
        unread: dict[str, list[str]] = {}
        found = gather_across(what, pairs, unread)
        rows = across_rows(what, found, sites, unread)
        if what == "plugins" and hasattr(self, "across_plugin_facts"):
            return list(self.across_plugin_facts(rows))  # WordPress.org's facts, as on a site
        return rows

    def across_sheet(self, row: WbRow) -> tuple[SheetSpec, dict[str, Any]]:
        variants: dict[str, list[str]] = row.raw.get("variants") or {}
        missing: list[str] = row.raw.get("missing") or []
        not_read: dict[str, list[str]] = row.raw.get("unread") or {}
        missing_lines = [
            *missing,
            *(f"Not read on {s}: {'; '.join(r)}" for s, r in not_read.items()),
        ]
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
            "missing": "\n".join(missing_lines) or "Every site in scope has it.",
        }
        return sheet, values

    # -- Make Them the Same -------------------------------------------------------

    def _across_refusal(self, site: str, kind: str) -> str:
        """Why *site* may not be changed for *kind* ("" when it may)."""
        reason = self.write_refusal(WbRow("item", site, "0", {}, ""), Tier.WRITE)
        account = self.account_for(site)
        if reason or account is None:
            return reason
        return refusal(_MAKE_SAME_NEEDS.get(kind, ""), account, site)

    def _across_report(self, title: str, said: str, outcomes: list[Outcome]) -> None:
        self.say(said)
        if any(not o.ok for o in outcomes):
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"{title}: Each Site",
                text="\n".join(("Done. " if o.ok else "Not done. ") + o.line for o in outcomes),
                help_text="What happened on each site, one a line; Not done says why.",
            )

    def do_make_same(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "across":
            return
        if row.subkind not in MAKE_SAME_KINDS:
            self.say(classify("across", row.subkind, "all_sites", "make_same").reason)
            return
        variants = list((row.raw.get("variants") or {}).keys())
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
        # Practice work reaches a real site only by an explicit, named choice.
        holders = list((row.raw.get("variants") or {}).get(winner, []))
        targets = [s for s, words in plan if not words.startswith("already")]
        if (
            holders
            and all(self.is_practice(h) for h in holders)  # type: ignore[attr-defined]
            and not self.practice_crossing_ok(  # type: ignore[attr-defined]
                f"Make {row.key} the Same", holders, targets
            )
        ):
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        source = next(
            (objects[s] for s in (row.raw.get("variants") or {}).get(winner, []) if s in objects),
            {},
        )
        refused: list[Outcome] = []
        for site, words in plan:
            if words.startswith("already"):
                reason = ""
            elif words.startswith("not read"):
                reason = words  # never make on a site what QUILL only failed to read there
            else:
                reason = self._across_refusal(site, row.subkind)
            if reason:
                refused.append(Outcome(site, row.key, False, reason))
        blocked = {o.site for o in refused}
        plan = [(s, w) for s, w in plan if s not in blocked]
        if row.subkind == "themes":
            self._make_themes_same(row, plan, objects, source, refused)
            return
        if row.subkind == "menus":
            self._make_menus_same(row, plan, objects, source, refused)
            return
        edits, cannot = make_same_edits(row.subkind, row.key, plan, objects, source)
        refused += cannot
        if not edits:
            self.say(
                f"Nothing to send: {refused[0].line}." if refused else "Every site already matches."
            )
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Make {row.key} the Same",
            summary=f"{len(edits)} sites get {row.key} as {winner}.",
            lines=[e.line for e in edits] + [f"Not changed. {o.line}" for o in refused],
            yes="Make Them the Same",
        ):
            return

        def done(result: tuple[list[Outcome], list[Edit]]) -> None:
            outcomes, sent = result
            outcomes = outcomes + refused
            good = sum(1 for o in outcomes if o.ok)
            said = f"{row.key}: {good} of {len(outcomes)} sites changed to {winner}."
            self._across_report(f"Make {row.key} the Same", said, outcomes)
            restorable = [e for e in sent if e.before is not None]
            self.history.record(
                Change(
                    row.key,
                    said,
                    undo=(lambda: undo_edits(lambda s: self.ctx(s).api, sent))
                    if restorable
                    else None,
                )
            )
            self.refresh()

        self.background(
            "making them the same",
            lambda: run_edits_by_site(lambda s: self.ctx(s).api, edits),
            done,
        )

    def _make_themes_same(
        self,
        row: WbRow,
        plan: list[tuple[str, str]],
        objects: Any,
        source: Any,
        refused: list[Outcome],
    ) -> None:
        stylesheet = str(source.get("stylesheet") or row.key)
        open_on, cannot = theme_screens(plan, objects, stylesheet)
        refused = refused + cannot
        if not open_on:
            self.say(
                f"Nothing to open: {refused[0].line}." if refused else "Every site already matches."
            )
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Make {row.key} the Same",
            summary=(
                "WordPress's REST API cannot activate a theme, so QUILL opens each site's "
                f"Themes screen in your browser, to activate {row.key} there."
            ),
            lines=[f"{s}: opens Appearance > Themes for {stylesheet}" for s in open_on]
            + [f"Not changed. {o.line}" for o in refused],
            yes="Open Them",
        ):
            return
        for site in open_on:
            self._open_screen(site, "theme_activate", theme=stylesheet)  # type: ignore[attr-defined]
        self.say(f"Opened {len(open_on)} Themes screens; activate {row.key} on each.")

    def _make_menus_same(
        self,
        row: WbRow,
        plan: list[tuple[str, str]],
        objects: Any,
        source: Any,
        refused: list[Outcome],
    ) -> None:
        targets = [s for s, w in plan if not w.startswith("already")]
        if not targets:
            self.say("Every site already matches.")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Make {row.key} the Same",
            summary=(
                f"{len(targets)} sites get the {row.key} menu's items as links, pointed at each "
                "site's own address. Their items are replaced, and this cannot be undone."
            ),
            lines=[
                f"{s}: {'replaces its items' if s in objects else 'makes the menu'}"
                for s in targets
            ]
            + [f"Not changed. {o.line}" for o in refused],
            yes="Make Them the Same",
        ):
            return

        def work() -> list[Outcome]:
            out = []
            for site in targets:
                api = self.ctx(site).api
                home = getattr(getattr(api, "address", None), "site_url", "")
                out.append(menu_copy(api, site, row.key, source, objects.get(site), home))
            return out

        def done(outcomes: list[Outcome]) -> None:
            outcomes = outcomes + refused
            good = sum(1 for o in outcomes if o.ok)
            said = f"{row.key}: {good} of {len(outcomes)} sites now have the same menu."
            self._across_report(f"Make {row.key} the Same", said, outcomes)
            self.history.record(Change(row.key, said, undo=None))
            self.refresh()

        self.background("copying a menu", work, done)

    # -- global styles ----------------------------------------------------------------

    def do_compare_styles(self, _ref: Any, row: WbRow | None) -> None:
        if row is not None and row.kind == "across" and row.subkind != "themes":
            self.say(classify("across", row.subkind, "all_sites", "compare_styles").reason)
            return
        sites = self.scope_sites()

        def work() -> tuple[str, list[str]]:
            return compare_styles({s: site_styles(self.ctx(s).api) for s in sites})

        def done(result: tuple[str, list[str]]) -> None:
            summary, lines = result
            self.say(summary)
            dlg.show_report(
                self.parent,
                self.show_modal,
                title="Compare Global Styles",
                text="\n".join([summary, *lines]),
                help_text="Each style that differs, with each site's value; unread sites say why.",
            )

        self.background("comparing global styles", work, done)

    # -- the network ----------------------------------------------------------------

    def do_promote_network(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "across" or row.subkind != "plugins":
            kind = row.subkind if row is not None and row.kind == "across" else "terms"
            self.say(
                "Promote to Network works on a plugin, in Across Sites > Plugins. "
                + classify("across", kind, "network", "promote_network").reason
            )
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}

        def check() -> dict[str, str]:
            reasons: dict[str, str] = {}
            for site in objects:
                account = self.account_for(site)
                can = account is None or account.can("activate_plugins")
                reasons[site] = network_refusal(site, network_status(self.ctx(site).api), can)
            return reasons

        def checked(reasons: dict[str, str]) -> None:
            network = [s for s, why in reasons.items() if not why]
            if not network:
                self.say(next(iter(reasons.values()), f"{row.key} is on no site in scope."))
                return
            if not self.practice_crossing_ok(  # type: ignore[attr-defined]
                "Promote to Network", network, network, together=True
            ):
                return
            lines = [f"{s}: becomes network-active" for s in network] + [
                f"Not changed. {why}" for why in reasons.values() if why
            ]
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Promote to Network",
                summary=(
                    f"{row.key} runs on every site of each network below, and no single site "
                    "can deactivate it. WordPress refuses unless you are a super admin."
                ),
                lines=lines,
                yes="Promote",
            ):
                return

            def work() -> list[Outcome]:
                out = []
                for site in network:
                    raw = objects[site]
                    try:
                        self.ctx(site).api.post(
                            f"wp/v2/plugins/{raw.get('plugin')}", {"status": "network-active"}
                        )
                        out.append(Outcome(site, row.key, True, "network-active"))
                    except Exception as exc:  # noqa: BLE001 - said per site
                        said = getattr(exc, "plain", "") or str(exc)
                        out.append(Outcome(site, row.key, False, said))
                return out

            def done(outcomes: list[Outcome]) -> None:
                good = sum(1 for o in outcomes if o.ok)
                said = f"{row.key}: network-active on {good} of {len(outcomes)} networks."
                self._across_report("Promote to Network", said, outcomes)
                self.history.record(Change(row.key, said, undo=None))
                self.refresh()

            self.background("promoting to the network", work, done)

        self.background("checking for a network", check, checked)

    # -- application passwords ----------------------------------------------------

    def do_revoke_everywhere(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "across" or row.subkind != "app_passwords":
            self.say("Revoke Everywhere works on a row of Across Sites > Application Passwords.")
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        refusals: dict[str, str] = {}
        for site, raw in objects.items():
            reason = self.write_refusal(WbRow("item", site, "0", {}, ""), Tier.WRITE)
            account = self.account_for(site)
            if not reason and account is not None and raw.get("user") != "me":
                reason = refusal("edit_users", account, site)
            refusals[site] = reason
        plan, refused = revoke_plan(row.key, objects, refusals)
        if not plan:
            self.say(f"Nothing to revoke: {refused[0].line}." if refused else "No site has it.")
            return
        changed = [site for site, _route in plan]
        if not self.practice_crossing_ok(  # type: ignore[attr-defined]
            "Revoke Everywhere", changed, changed, together=True
        ):
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Revoke Everywhere",
            summary=(
                f"{row.key} is revoked on {len(plan)} sites. Anything signing in with it stops "
                "working, and this cannot be undone: a revoked password cannot be restored."
            ),
            lines=[f"{site}: revokes {row.key}" for site, _route in plan]
            + [f"Not changed. {o.line}" for o in refused],
            yes="Revoke",
        ):
            return

        def work() -> list[Outcome]:
            out = []
            for site, route in plan:
                try:
                    self.ctx(site).api.delete(route)
                    out.append(Outcome(site, row.key, True, "revoked"))
                except Exception as exc:  # noqa: BLE001 - said per site
                    said = getattr(exc, "plain", "") or str(exc)
                    out.append(Outcome(site, row.key, False, said))
            return out

        def done(outcomes: list[Outcome]) -> None:
            outcomes = outcomes + refused
            good = sum(1 for o in outcomes if o.ok)
            said = f"{row.key}: revoked on {good} of {len(outcomes)} sites. It cannot be undone."
            self._across_report("Revoke Everywhere", said, outcomes)
            self.history.record(Change(row.key, said, undo=None))
            self.refresh()

        self.background("revoking a password", work, done)

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
