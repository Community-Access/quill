"""Earlier Versions, Check for Updates on WordPress.org and Check Every Link (wp_missing.md).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`;
what each step means is in the wx-free core, and the context-menu rows, with
why none has a chord, are :mod:`quill.core.wordpress.workbench_gap_actions`.

- **Earlier Versions...** on a post, page or custom item's row: the site's
  revisions and autosaves (:mod:`quill.core.wordpress.workbench_item_versions`),
  newest first; the one chosen is compared with the item now in a preview,
  and restored only from that preview, after the item is read again. Ctrl+Z
  puts the item back.
- **Check for Updates on WordPress.org...** on plugin, theme and Needs My
  Attention > Updates rows: after the same consent Check on WordPress.org
  asks, the current versions (:mod:`quill.core.wordpress.workbench_update_check`)
  mark every plugin, theme and Updates row for this window.
- **Check Every Link...** on a row of By Name > Links: the whole site
  (:mod:`quill.core.wordpress.workbench_link_check`) in the background, its
  running count in the status bar's Link check cell, stopped by choosing it
  again or Enter on that cell; the broken links are listed with what holds each.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import workbench_item_versions as iv
from quill.core.wordpress import workbench_link_check as lk
from quill.core.wordpress import workbench_update_check as uc
from quill.core.wordpress.site import Revision
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_updates import update_rows
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchGapCommands"]

_UPDATE_ROWS = frozenset({"plugin", "theme", "update"})


def _refresh_status(frame: Any) -> None:
    status = getattr(frame, "status", None)
    if status is not None:
        try:
            status.refresh()
        except RuntimeError:  # the window closed while the check ran
            pass


class WorkbenchGapCommands:
    """Earlier Versions on items, the update check and the whole-site link check."""

    frame: Any
    commands: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    _types: dict[str, list[tuple[str, str]]]
    _dotorg_agreed: Callable[[str], bool]

    # -- Earlier Versions -------------------------------------------------------------

    def do_item_versions(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "item" or not row.route:
            self.say("Earlier Versions works on a post, page or custom item.")
            return
        api = self.ctx(row.site).api

        def work() -> tuple[iv.ItemText, list[Revision]]:
            now = iv.load_item(api, row.route)
            return now, iv.earlier_versions(api, row.subkind, row.object_id, now)

        self.background(
            f"reading {row.title}'s earlier versions",
            work,
            lambda found: self._item_versions(row, api, *found),
        )

    def _item_versions(
        self, row: WbRow, api: Any, now: iv.ItemText, versions: list[Revision]
    ) -> None:
        if not versions:
            self.say(f"{row.title} has no earlier versions on {row.site}.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Earlier Versions of {row.title}",
            prompt="&Versions:",
            rows=[iv.version_label(v) for v in versions],
            help_text=(
                "Each version the site kept, newest first. OK compares it with the item now, "
                "and that preview is where it is restored."
            ),
        )
        if index is None:
            return
        chosen = versions[index]
        when = iv.version_label(chosen).removeprefix("Saved ").split(",", 1)[0]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Restore {row.title}",
            summary=(
                f"Put back the version of {row.title} saved {when} on {row.site}? WordPress keeps "
                "the version it has now as a revision too."
            ),
            lines=iv.compare_lines(now, chosen),
            yes="Restore",
        ):
            return

        def done(saved: iv.ItemText) -> None:
            summary = f"Restored {row.title} to its version of {when}."

            def undo() -> str:
                iv.put_back(api, saved, now)
                return f"{row.title} is back as it was."

            self.history.record(Change(row.title, summary, undo=undo))
            self.say(summary)
            self.refresh()

        self.background(
            f"restoring {row.title}", lambda: iv.restore_version(api, now, chosen), done
        )

    # -- Check for Updates on WordPress.org ---------------------------------------------

    def _update_latest(self) -> uc.Latest | None:
        found: uc.Latest | None = self.__dict__.get("_wp_latest")
        return found

    def with_update_facts(self, rows: Sequence[Any]) -> list[Any]:
        """Rows marked with what WordPress.org said, once Check for Updates has asked."""
        latest = self._update_latest()
        return uc.mark_rows(rows, latest) if latest is not None else list(rows)

    def do_check_updates(self, ref: Any, row: WbRow | None) -> None:
        site = row.site if row is not None and row.kind in _UPDATE_ROWS else ""
        site = site or (self.site_of(ref) if ref is not None else "")
        if not site:
            self.say("Choose a plugin, a theme or a row under Needs My Attention > Updates first.")
            return
        if not self._dotorg_agreed("updates"):
            return

        def work() -> tuple[uc.Latest, list[WbRow]]:
            ctx = self.ensure(self.ctx(site))
            listed = update_rows(ctx)
            plugins = [uc.slug_of(r)[1] for r in listed if r.key.startswith("update:plugin:")]
            themes = [uc.slug_of(r)[1] for r in listed if r.key.startswith("update:theme:")]
            logs: dict[str, str] = {}  # each plugin's changelog, read with its version (D3)
            core = uc.latest_core()
            versions = uc.latest_plugins(plugins, changelogs=logs)
            latest = uc.Latest(core, versions, uc.latest_themes(themes), logs)
            return latest, uc.mark_rows(listed, latest)

        def done(found: tuple[uc.Latest, list[WbRow]]) -> None:
            latest, marked = found
            before = self._update_latest()
            self.__dict__["_wp_latest"] = before.merged(latest) if before else latest
            waiting, unknown = uc.waiting_count(marked)
            names = [r.title for r in marked if r.cell("update").startswith("Update waiting")]
            if waiting:
                said = f"{waiting} update{'s' if waiting != 1 else ''} waiting on {site}: "
                said += ", ".join(names[:6]) + (" and more" if len(names) > 6 else "") + "."
            else:
                said = f"Nothing on {site} has an update waiting on WordPress.org."
            if unknown:
                said += f" {unknown} not on WordPress.org, so unknown."
            self.say(said)
            self.refresh()

        self.background("asking WordPress.org for current versions", work, done)

    # -- Check Every Link ---------------------------------------------------------------

    def link_check_status(self) -> str:
        """The status bar's Link check cell ("" when no check runs)."""
        state = self.__dict__.get("_link_state")
        if not state:
            return ""
        site, checked, total, broken = state
        if not total:
            return f"Reading {site}'s published items"
        return f"{checked} of {total} links on {site}, {broken} broken. Enter stops"

    def stop_link_check(self) -> None:
        stop: threading.Event | None = self.__dict__.get("_link_stop")
        if stop is None or stop.is_set():
            self.say("No link check is running.")
            return
        stop.set()
        self.say("Stopping the link check; what it found so far is kept.")

    def _link_tick(self, site: str, checked: int, total: int, broken: int) -> None:
        """Off the UI thread: keep the count, and repaint the status bar now and then."""
        self.__dict__["_link_state"] = (site, checked, total, broken)
        if checked == total or checked % 5 == 0:
            import wx

            wx.CallAfter(_refresh_status, self.frame)

    def do_check_every_link(self, _ref: Any, row: WbRow | None) -> None:
        stop: threading.Event | None = self.__dict__.get("_link_stop")
        if stop is not None and not stop.is_set():
            self.stop_link_check()
            return
        if row is None or row.kind != "value" or row.subkind != "links":
            self.say("Check Every Link works on a row of By Name > Links.")
            return
        site = row.site
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Check Every Link",
            message=(
                f"Check every link in {site}'s published posts, pages and items? The site "
                "fetches each address itself, which can take some minutes; it runs in the "
                "background, the status bar counts, and choosing this again stops it."
            ),
            yes_label="Check",
        ):
            return
        stop = threading.Event()
        self.__dict__["_link_stop"] = stop
        self.__dict__["_link_state"] = (site, 0, 0, 0)
        _refresh_status(self.frame)
        extra = [kind for kind, _label in getattr(self, "_types", {}).get(site, [])]

        def work() -> lk.LinkCheck | None:
            api = self.ensure(self.ctx(site)).api
            if not lk.has_link_route(api):
                return None
            found, items = lk.collect_links(api, lk.kinds_for(extra), stop=stop)
            self._link_tick(site, 0, len(found), 0)
            return lk.check_links(
                api,
                found,
                items=items,
                stop=stop,
                progress=lambda done, total, bad: self._link_tick(site, done, total, bad),
            )

        def done(result: lk.LinkCheck | None) -> None:
            self.__dict__["_link_stop"] = None
            self.__dict__["_link_state"] = None
            _refresh_status(self.frame)
            if result is None:
                self.say(
                    f"{site} does not offer WordPress's link-check route, so its links cannot "
                    "be checked from here. Check This Page still works."
                )
                return
            self.say(lk.outcome(site, result))
            if result.broken:
                self._show_broken(site, result)

        self.background(f"checking every link on {site}", work, done)

    def _show_broken(self, site: str, result: lk.LinkCheck) -> None:
        broken = result.broken

        def open_holder(index: int | None) -> object:
            if index is None:
                return None
            holder = broken[index].holders[0]
            profile = self.profile(site)
            if profile is None:
                self.say(f"{site} is no longer in your list of sites.")
                return None
            self.commands.open_item(profile, holder.kind, holder.item_id)
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.parent,
            self.show_modal,
            title=f"Broken Links on {site}",
            purpose=lk.outcome(site, result),
            list_label="&Broken links:",
            list_help="Each address that leads nowhere, the items that hold it, and why.",
            rows=[b.spoken() for b in broken],
            details=lambda index: "\n".join(
                [broken[index].url, broken[index].why, ""]
                + [f"{h.title} ({h.kind}): {h.link}" for h in broken[index].holders]
            ),
            actions=[
                dlg.Action(
                    "&Open in Editor",
                    "Open the first item that holds this link in the editor, to fix it.",
                    open_holder,
                )
            ],
        )
        window.Destroy()
