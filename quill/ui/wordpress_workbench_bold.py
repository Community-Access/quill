"""The bold part of the WordPress Workbench (PRD 15.1 to 15.10; W7).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Copy to Site** (Ctrl+Shift+Y): the selection to another connected site,
  with the plan as the preview (every create, replace and skip), pictures
  uploaded and links pointed at the target.
- **Compare Sites** (Ctrl+Alt+K), **Take a Snapshot** (Ctrl+Alt+S) and
  **Read Site as Document** (Ctrl+Alt+D), which opens the whole site, a menu
  or a category as one document in the editor, ready for its Word, EPUB and
  DAISY exports.
- **Put Back from a Snapshot** (Ctrl+Alt+Shift+S): a snapshot set back on
  the site, after a preview that states what is and is not put back.
- **The editorial queue and Move to Another Day**, in
  :mod:`quill.ui.wordpress_workbench_bold_queue`.
- **Lists in and out**: Export List, Import Posts from a Spreadsheet and
  Import a Folder of Documents, in :mod:`quill.ui.wordpress_workbench_bold_lists`.
- **The REST Console** and the **Practice Site** (Tools menu; the Practice Site
  in :mod:`quill.ui.wordpress_workbench_bold_practice`).
- **Changing a global style**, in :mod:`quill.ui.wordpress_workbench_bold_styles`.

Every request runs through ``self.background``; every change is previewed
or confirmed by name first; outcomes are one sentence.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress import sites as st
from quill.core.wordpress.workbench_bold import (
    calendar_days,
    fetch_site_file,
    plan_copy,
    run_copy,
)
from quill.core.wordpress.workbench_carry import copy_left_out, left_out_section
from quill.core.wordpress.workbench_practice import find_cli, missing_words, site_url
from quill.core.wordpress.workbench_read_site import ReadScope, document_pages, site_document
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_snapshot import (
    COMPARE_OMITS,
    RESTORE_TERMS,
    compare_sites,
    restore_plan,
    run_restore,
    snapshot_counts_words,
    snapshot_folders,
    snapshot_left_out,
    snapshot_source,
    take_snapshot,
)
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg
from quill.ui.wordpress_workbench_bold_lists import WorkbenchListCommands
from quill.ui.wordpress_workbench_bold_more import WorkbenchMoreCommands
from quill.ui.wordpress_workbench_bold_practice import WorkbenchPracticeCommands
from quill.ui.wordpress_workbench_bold_queue import WorkbenchQueueCommands
from quill.ui.wordpress_workbench_bold_styles import WorkbenchGlobalStyleCommands

__all__ = ["WorkbenchBoldCommands"]


class WorkbenchBoldCommands(
    WorkbenchQueueCommands,
    WorkbenchListCommands,
    WorkbenchMoreCommands,
    WorkbenchPracticeCommands,
    WorkbenchGlobalStyleCommands,
):
    """Copy, compare, snapshot, read, the queue, lists in and out, console, practice."""

    frame: Any
    parent: Any
    commands: Any
    history: Any
    _data_dir: Any
    _profiles: dict[str, Any]
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    selected_rows: Callable[[], list[WbRow]]
    write_refusal: Callable[[WbRow, Tier], str]
    access_for: Callable[[str], Any]

    # -- helpers ------------------------------------------------------------------

    def _base(self) -> Path:
        return Path(self._data_dir) if self._data_dir else st.sites_path().parent

    def _other_site(self, site: str, title: str) -> str:
        others = [name for name in self._profiles if name != site]
        if not others:
            self.say("Connect a second site first: File > WordPress > Connect a Site.")
            return ""
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=title,
            prompt="&Site:",
            rows=others,
            help_text="Which of your other connected sites.",
        )
        return "" if index is None else others[index]

    def _site_now(self, ref: Any) -> str:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Connect a site first: File > WordPress > Connect a Site, in the editor.")
        return site

    def _report(self, title: str, text: str, help_text: str) -> None:
        dlg.show_report(self.parent, self.show_modal, title=title, text=text, help_text=help_text)

    # -- site to site (15.2) ------------------------------------------------------

    def do_copy_to_site(self, ref: Any, row: WbRow | None) -> None:
        rows = self.selected_rows() or ([row] if row is not None else [])
        if not rows:
            self.say("Select what to copy first.")
            return
        source = rows[0].site
        target = self._other_site(source, "Copy to Site")
        if not target:
            return
        if not self.practice_crossing_ok("Copy to Site", [source], [target]):  # type: ignore[attr-defined]
            return
        probe = WbRow(rows[0].kind, target, "0", {}, "")
        reason = self.write_refusal(probe, Tier.WRITE)
        if reason:
            self.say(reason)
            return
        source_api, target_api = self.ctx(source).api, self.ctx(target).api
        source_url = self.profile(source).site_url
        target_url = self.profile(target).site_url
        picked = [(r.kind, r.subkind, dict(r.raw)) for r in rows]
        left_out = copy_left_out(raw for _k, _s, raw in picked)

        def planned(plan: Any) -> None:
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"Copy from {source} to {target}",
                summary=plan.summary,
                lines=[line.sentence for line in plan.lines]
                + [f"Upload the picture {url}" for url in plan.pictures]
                + [f"Left out: {line}" for line in left_out],
                yes="Copy",
            ):
                return

            def done(failed: list[str]) -> None:
                self.history.record(
                    Change(target, f"Copied {len(plan.lines)} from {source} to {target}.")
                )
                if failed:
                    self.say(f"Copied to {target}, except {len(failed)}; the report says which.")
                    self._report(
                        f"Copy to {target}",
                        "\n".join([
                            *plan.outcomes,
                            *(f"Not copied: {f}" for f in failed if f.startswith("the picture")),
                            *left_out_section(left_out),
                        ]),
                        "What happened to each thing copied.",
                    )
                else:
                    self.say(f"Copied to {target}; new items are drafts there.")

            self.background(
                f"copying to {target}",
                lambda: run_copy(
                    source_api,
                    target_api,
                    plan,
                    source_url=source_url,
                    target_url=target_url,
                    fetch=lambda url: fetch_site_file(source_api, url),
                ),
                done,
            )

        self.background(
            f"planning the copy to {target}",
            lambda: plan_copy(
                target_api,
                picked,
                source_site=source,
                target_site=target,
                source_url=source_url,
                source=source_api,
            ),
            planned,
        )

    def do_compare_sites(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        other = self._other_site(site, "Compare Sites") if site else ""
        if not other:
            return

        def shown(found: list[Any]) -> None:
            lines = [f"{d.kind} {d.slug}: {d.words}".replace(" : ", ": ") for d in found]
            same = "Their posts, pages, patterns, categories, tags and menus are the same."
            self._report(
                f"{site} and {other}",
                "\n".join([*(lines or [same]), "", COMPARE_OMITS]),
                "What differs between the two sites, by kind and address (slug), and what "
                "is not compared.",
            )

        self.background(
            "comparing sites",
            lambda: compare_sites(
                self.ctx(site).api, self.ctx(other).api, first_name=site, second_name=other
            ),
            shown,
        )

    def do_snapshot(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        choices = ["Everything but the media files", "Everything, with the media files too"]
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Take a Snapshot",
            prompt="&Save:",
            rows=choices,
            help_text=f"Every post, page, pattern, term, menu, setting and media record of "
            f"{site}, to this computer. The media files themselves only if you choose; people, "
            "passwords, plugins, themes, revisions and comments are never saved.",
        )
        if index is None:
            return
        media = index == 1
        api = self.ctx(site).api
        folder = self._snapshots(site)

        def done(result: tuple[Path, dict[str, int]]) -> None:
            where, counts = result
            left_out = "; ".join(snapshot_left_out(where))
            self.say(
                f"Snapshot of {site} saved: {snapshot_counts_words(counts)}. In {where}. "
                f"Left out: {left_out}."
            )

        self.background(
            "taking a snapshot",
            lambda: take_snapshot(
                api,
                folder,
                site=site,
                media=media,
                fetch=(lambda url: fetch_site_file(api, url)) if media else None,
                practice=self.is_practice(site),  # type: ignore[attr-defined]
            ),
            done,
        )

    def _snapshots(self, site: str) -> Path:
        profile = self.profile(site)
        return self._base() / "wordpress_snapshots" / (profile.id if profile else site)

    def do_restore_snapshot(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        found = snapshot_folders(self._snapshots(site))
        if not found:
            self.say(f"There is no snapshot of {site} yet: Site > Take a Snapshot makes one.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Put Back from a Snapshot",
            prompt="&Snapshot:",
            rows=[p.name for p in found],
            help_text="The snapshots of this site, newest first. The next step previews "
            "exactly what would be put back.",
        )
        if index is None:
            return
        chosen = found[index]
        taken_on, practice = snapshot_source(chosen)
        is_practice = self.is_practice  # type: ignore[attr-defined]
        practice = practice or bool(taken_on and is_practice(taken_on))
        if practice and not self.practice_crossing_ok(  # type: ignore[attr-defined]
            "Put Back from a Snapshot", [taken_on or site], [site], from_practice=True
        ):
            return
        api = self.ctx(site).api

        def planned(lines: list[Any]) -> None:
            if not lines:
                self.say(f"{site} already matches the snapshot of {chosen.name}.")
                return
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"Put Back {chosen.name}",
                summary=f"{len(lines)} changes on {site}. {RESTORE_TERMS}",
                lines=[line.sentence for line in lines],
                yes="Put Back",
            ):
                return

            def done(said: list[str]) -> None:
                self.history.record(Change(site, f"Put back the snapshot {chosen.name}."))
                missed = sum(1 for line in said if line.startswith("Not"))
                self.say(f"Put back {len(said) - missed} of {len(said)} on {site}.")
                if missed:
                    self._report("Put Back from a Snapshot", "\n".join(said), RESTORE_TERMS)
                self.refresh()

            self.background("putting back", lambda: run_restore(api, lines), done)

        self.background("comparing with the snapshot", lambda: restore_plan(api, chosen), planned)

    def do_read_site(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Read Site as Document",
            prompt="&Read:",
            rows=["The whole site", "The pages in one menu", "The posts in one category"],
            help_text="Every published page in page order, a menu's pages in its order, or a "
            "category's posts oldest first, as one document in the editor.",
        )
        if index is None:
            return
        if index == 0:
            self._read_scope(site, ReadScope())
            return
        kind, route = ("menu", "wp/v2/menus") if index == 1 else ("category", "wp/v2/categories")
        api = self.ctx(site).api

        def listed() -> list[tuple[int, str]]:
            found = api.iter_collection(route, {"_fields": "id,name"}, per_page=100, max_pages=5)
            return [(int(r.get("id", 0) or 0), str(r.get("name", ""))) for r in found]

        def chosen(options: list[tuple[int, str]]) -> None:
            if not options:
                self.say(f"{site} has no {kind}s to read.")
                return
            picked = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Read Site as Document",
                prompt=f"&{kind.capitalize()}:",
                rows=[name for _ident, name in options],
                help_text=f"Which {kind} to read as one document.",
            )
            if picked is not None:
                ident, name = options[picked]
                self._read_scope(site, ReadScope(kind, ident, name))

        self.background(f"listing {kind}s", listed, chosen)

    def _read_scope(self, site: str, scope: ReadScope) -> None:
        api = self.ctx(site).api
        address = self.profile(site).site_url if self.profile(site) else ""

        def work() -> Path:
            pages, notes = document_pages(api, scope, site=site)
            text = site_document(
                site,
                pages,
                address=address,
                scope=scope.words,
                made=time.strftime("%Y-%m-%d %H:%M"),
                notes=notes,
            )
            folder = self._base() / "wordpress_read_site"
            folder.mkdir(parents=True, exist_ok=True)
            safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in site).strip()
            extra = f" {scope.name}" if scope.name else ""
            path = folder / f"{safe or 'site'}{extra} as a document.md"
            path.write_text(text, encoding="utf-8", newline="\n")
            return path

        def done(path: Path) -> None:
            self.commands.host.open_path(path)
            self.say(
                f"{site} is open as a document, a heading per page. File > Export makes "
                "Word, EPUB or DAISY from it."
            )

        self.background("reading the site", work, done)

    # -- the REST Console (15.9) --------------------------------------------------

    def do_rest_console(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        from quill.ui.wordpress_rest_console import RestConsole

        ctx = self.ensure(self.ctx(site))
        RestConsole(self, site, ctx).show()

    # -- the calendar (15.3) ------------------------------------------------------

    def calendar_rows(self) -> list[WbRow]:
        """Off the UI thread: each day as a row, and the days kept for the tree."""
        from quill.core.wordpress.workbench_bold import day_words

        since = time.strftime("%Y-%m-%d", time.localtime(time.time() - 14 * 86400))
        sites = [(name, self.ctx(name).api) for name in self._profiles]
        found = getattr(self, "_types", {})
        kinds = {
            name: [
                "post",
                "page",
                *(k for k, _n in found.get(name, []) if k not in ("post", "page")),
            ]
            for name in self._profiles
        }
        failures: list[str] = []
        days = calendar_days(sites, since=since, kinds_by_site=kinds, failures=failures)
        self.days = days
        rows: list[WbRow] = [
            WbRow("fact", "", f"failed:{i}", {"day": f"Could not ask {said}"}, said)
            for i, said in enumerate(failures)
        ]
        for day, items in days.items():
            scheduled = sum(1 for i in items if i["status"] == "future")
            published = len(items) - scheduled
            rows.append(
                WbRow(
                    "day",
                    "",
                    day,
                    {
                        "day": day_words(day, scheduled, published).split(":")[0],
                        "scheduled": str(scheduled),
                        "published": str(published),
                    },
                    day_words(day, scheduled, published) + ". Enter lists them.",
                )
            )
        return rows

    def day_rows(self, day: str) -> list[WbRow]:
        from quill.core.wordpress.workbench_rows import item_row

        rows: list[WbRow] = []
        for entry in getattr(self, "days", {}).get(day, []):
            row = item_row(entry["raw"], entry["kind"], entry["site"])
            rows.append(row)
        return rows

    def day_children(self) -> list[tuple[str, str]]:
        from quill.core.wordpress.workbench_bold import day_words

        found: list[tuple[str, str]] = []
        for day, items in getattr(self, "days", {}).items():
            scheduled = sum(1 for i in items if i["status"] == "future")
            found.append((day, day_words(day, scheduled, len(items) - scheduled)))
        return found

    def fixed_rows(self, family: str, what: str, instance: str) -> list[WbRow]:
        """Off the UI thread: the Calendar, Watches and Practice Site lists."""
        from quill.core.wordpress.workbench_rows import fact_rows
        from quill.core.wordpress.workbench_watches import KINDS

        if family == "calendar":
            if what == "day":
                return self.day_rows(instance)
            before = set(getattr(self, "days", {}))
            rows = self.calendar_rows()
            if set(self.days) != before:
                import wx

                wx.CallAfter(self._days_changed)
            return rows
        if family == "watches":
            options = self.options()  # type: ignore[attr-defined]
            facts = [
                (label, "on" if kind in options.watches else "off") for kind, label in KINDS.items()
            ]
            facts.append((
                "How often",
                f"at most every {max(15, options.watch_minutes)} minutes, while QUILL is open; "
                "Tools > Workbench Options turns each on or off",
            ))
            if options.watches:
                from quill.core.wordpress.workbench_watches import load_state, status_facts

                state = load_state(self._data_dir)
                facts += status_facts(state, list(self._profiles), options.watch_minutes)
            return fact_rows("", facts)
        tools = find_cli()
        process = getattr(self, "_practice", None)
        running = process is not None and process.poll() is None
        return fact_rows(
            "",
            [
                ("Playground's tool", str(tools.cli) if tools.cli else "not in this build"),
                ("Node.js", str(tools.node) if tools.node else "not found"),
                ("WordPress core", str(tools.wordpress) if tools.wordpress else "not bundled"),
                ("Running", f"yes, at {site_url()}" if running else "no"),
                ("What to do", missing_words(tools) or "Tools > Practice Site starts it."),
            ],
        )

    def _days_changed(self) -> None:
        if self.frame is not None:
            self.frame.rebuild_tree()

    def do_open_day(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.workbench_frame import NodeRef

        if row is not None and self.frame.select(NodeRef("", "calendar_day", row.key)):
            self.frame.tree.SetFocus()
