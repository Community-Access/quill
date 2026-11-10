"""The bold part of the WordPress Workbench (PRD 15.1 to 15.10; W7).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Copy to Site** (Ctrl+Shift+Y): the selection to another connected site,
  with the plan as the preview (every create, replace and skip), pictures
  uploaded and links pointed at the target.
- **Compare Sites** (Ctrl+Alt+K), **Take a Snapshot** (Ctrl+Alt+S) and
  **Read Site as Document** (Ctrl+Alt+D), which opens the pages as one
  document in the editor, ready for its Word, EPUB and DAISY exports.
- **The editorial queue**: Approve and Schedule, Send Back with a Note and
  Assign a Reviewer on posts and pages waiting for review.
- **Lists in and out**: Export List (CSV or Excel) and Import Posts from a
  Spreadsheet, previewed row by row.
- **The REST Console** and the **Practice Site** (Tools menu).

Every request runs through ``self.background``; every change is previewed
or confirmed by name first; outcomes are one sentence.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.core.wordpress import block_notes as notes
from quill.core.wordpress import sites as st
from quill.core.wordpress.workbench_bold import (
    calendar_days,
    compare_sites,
    fetch_site_file,
    plan_copy,
    run_copy,
    site_document,
    snapshot_counts_words,
    take_snapshot,
)
from quill.core.wordpress.workbench_io import (
    export_rows,
    import_plan,
    read_spreadsheet,
    send_import,
)
from quill.core.wordpress.workbench_practice import (
    PRACTICE_NAME,
    find_cli,
    missing_words,
    practice_dir,
    read_password,
    reset,
    site_url,
    start_command,
)
from quill.core.wordpress.workbench_rows import WbRow, tree_order
from quill.core.workbench.actions import Tier
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchBoldCommands"]


class WorkbenchBoldCommands:
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
        probe = WbRow("item", target, "0", {}, "")
        reason = self.write_refusal(probe, Tier.WRITE)
        if reason:
            self.say(reason)
            return
        source_api, target_api = self.ctx(source).api, self.ctx(target).api
        source_url = self.profile(source).site_url
        target_url = self.profile(target).site_url
        picked = [(r.kind, r.subkind, dict(r.raw)) for r in rows]

        def planned(plan: Any) -> None:
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"Copy to {target}",
                summary=plan.summary,
                lines=[line.sentence for line in plan.lines]
                + [f"Upload the picture {url}" for url in plan.pictures],
                yes="Copy",
            ):
                return

            def done(failed: list[str]) -> None:
                more = f" Not copied: {'; '.join(failed[:3])}" if failed else ""
                self.say(f"Copied to {target}; new items are drafts there.{more}")

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
            ),
            planned,
        )

    def do_compare_sites(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        other = self._other_site(site, "Compare Sites") if site else ""
        if not other:
            return

        def shown(found: list[Any]) -> None:
            lines = [f"{d.kind} {d.slug}: {d.words}" for d in found]
            self._report(
                f"{site} and {other}",
                "\n".join(lines) or "Their posts and pages are the same.",
                "What differs between the two sites, by post or page and its slug.",
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
        if not site or not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Take a Snapshot",
            message=f"Save every post, page, term, menu, pattern and setting of {site} to this "
            "computer? Media files stay on the site.",
            yes_label="Take Snapshot",
        ):
            return
        folder = self._base() / "wordpress_snapshots" / self.profile(site).id

        def done(result: tuple[Path, dict[str, int]]) -> None:
            where, counts = result
            self.say(f"Snapshot of {site} saved: {snapshot_counts_words(counts)}. In {where}.")

        self.background(
            "taking a snapshot",
            lambda: take_snapshot(self.ctx(site).api, folder, site=site),
            done,
        )

    def do_read_site(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        api = self.ctx(site).api

        def work() -> Path:
            raw = list(
                api.iter_collection(
                    "wp/v2/pages",
                    {"status": "publish", "orderby": "menu_order", "order": "asc"},
                    per_page=100,
                    max_pages=20,
                )
            )
            from quill.core.wordpress.workbench_rows import item_row

            ordered = tree_order([item_row(r, "page", site) for r in raw])
            text = site_document(site, [r.raw for r in ordered])
            folder = self._base() / "wordpress_read_site"
            folder.mkdir(parents=True, exist_ok=True)
            safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in site).strip()
            path = folder / f"{safe or 'site'} as a document.md"
            path.write_text(text, encoding="utf-8", newline="\n")
            return path

        def done(path: Path) -> None:
            self.commands.host.open_path(path)
            self.say(
                f"{site} is open as a document, a heading per page. File > Export makes "
                "Word, EPUB or DAISY from it."
            )

        self.background("reading the site", work, done)

    # -- the editorial queue (15.4) -----------------------------------------------

    def _queue_rows(self, row: WbRow | None) -> list[WbRow]:
        rows = [r for r in (self.selected_rows() or ([row] if row else [])) if r.kind == "item"]
        if not rows:
            self.say("Select a post or page waiting for review.")
        return rows

    def do_approve_schedule(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if not rows:
            return
        when = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Approve and Schedule",
            prompt="&Publish on (2026-11-12 09:00), or empty for now:",
            help_text="The site's own time. Empty publishes them now.",
        )
        if when is None:
            return
        text = when.strip().replace(" ", "T")
        body: dict[str, Any] = {"status": "future", "date": text} if text else {"status": "publish"}
        api = self.ctx(rows[0].site).api

        def work() -> None:
            for r in rows:
                api.post(r.route, body)

        said = f"scheduled for {when.strip()}" if text else "published"
        self.background(
            "approving", work, lambda _n: (self.say(f"{len(rows)} {said}."), self.refresh())
        )

    def _note_then(self, rows: Sequence[WbRow], title: str, prompt: str, status: str) -> None:
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt=prompt,
            help_text="A note on the draft, which its writer reads in the editor.",
            multiline=True,
        )
        if not text or not text.strip():
            return
        api = self.ctx(rows[0].site).api

        def work() -> None:
            for r in rows:
                notes.add_note(api, r.object_id, text.strip())
                if status:
                    api.post(r.route, {"status": status})

        self.background(
            "leaving a note", work, lambda _n: (self.say(f"{title}: done."), self.refresh())
        )

    def do_send_back(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if rows:
            self._note_then(rows, "Send Back with a Note", "&What needs changing:", "draft")

    def do_assign_reviewer(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if rows:
            self._note_then(rows, "Assign a Reviewer", "&Reviewer, and a note for them:", "")

    # -- lists in and out (15.10) -------------------------------------------------

    def _file(self, title: str, wildcard: str, *, save: bool) -> Path | None:
        wx = self.frame._wx
        style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT if save else wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dialog = wx.FileDialog(self.parent, title, wildcard=wildcard, style=style)
        try:
            if self.show_modal(dialog, title) != wx.ID_OK:
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()

    def do_export_list(self, _ref: Any, _row: WbRow | None) -> None:
        frame = self.frame
        if frame is None or not frame.rows:
            self.say("There is nothing in the list to export.")
            return
        path = self._file(
            "Export List", "Excel workbook (*.xlsx)|*.xlsx|CSV (*.csv)|*.csv", save=True
        )
        if path is None:
            return
        columns = frame.provider.columns(frame.node(frame.current))
        from quill.core.wordpress.workbench_listing import column_title

        rows = [frame.provider.cells(r, columns) for r in frame.rows]
        count = export_rows(path, [column_title(c) for c in columns], rows)
        self.say(f"Exported {count} rows to {path.name}.")

    def do_import_posts(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        kind = "page" if ref is not None and ref.key.startswith("pages") else "post"
        path = self._file(
            "Import Posts from a Spreadsheet",
            "Spreadsheets (*.xlsx;*.csv)|*.xlsx;*.csv",
            save=False,
        )
        if path is None:
            return
        plan = import_plan(read_spreadsheet(path))
        ready = [r for r in plan if not r.problem]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Import into {site}",
            summary=f"{len(ready)} {kind}s will be made on {site}, as drafts unless their "
            f"Status column says otherwise; {len(plan) - len(ready)} rows are skipped.",
            lines=[r.sentence for r in plan],
            yes="Import",
        ):
            return
        api = self.ctx(site).api

        def done(failed: list[str]) -> None:
            more = f" Not made: {'; '.join(failed[:3])}" if failed else ""
            self.say(f"Imported {len(ready) - len(failed)} {kind}s into {site}.{more}")
            self.refresh()

        self.background("importing", lambda: send_import(api, kind, plan), done)

    # -- the REST Console (15.9) --------------------------------------------------

    def do_rest_console(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        from quill.ui.wordpress_rest_console import RestConsole

        ctx = self.ensure(self.ctx(site))
        RestConsole(self, site, ctx).show()

    # -- the practice site (15.1) -------------------------------------------------

    def do_practice(self, _ref: Any, _row: WbRow | None) -> None:
        tools = find_cli()
        missing = missing_words(tools)
        if missing:
            self.say(missing)
            return
        running = getattr(self, "_practice", None)
        choices = (
            ["Connect It as Practice Site", "Stop the Practice Site"]
            if running is not None
            else ["Start the Practice Site", "Reset the Practice Site"]
        )
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=PRACTICE_NAME,
            prompt="&Do:",
            rows=choices,
            help_text="A WordPress site on this computer only, for learning with nothing at "
            "stake. Reset puts it back as new.",
        )
        if index is None:
            return
        choice = choices[index]
        folder = practice_dir(self._base())
        if choice.startswith("Start"):
            from quill.stability.safe_subprocess import spawn_subprocess_safely

            self._practice = spawn_subprocess_safely(start_command(tools, folder))
            self.say(f"Starting the practice site at {site_url()}. Connect it in a moment.")
        elif choice.startswith("Stop"):
            running.kill()
            self._practice = None
            self.say("The practice site has stopped.")
        elif choice.startswith("Reset"):
            if dlg.confirm(
                self.parent,
                self.show_modal,
                title="Reset the Practice Site",
                message="Put the practice site back as new? Everything made on it is removed.",
                yes_label="Reset",
            ):
                reset(folder)
                self.say("The practice site is new again. Start it to use it.")
        else:
            self._connect_practice(folder)

    def _connect_practice(self, folder: Path) -> None:
        found = read_password(folder)
        if found is None:
            self.say("The practice site is still starting. Try Connect again in a moment.")
            return
        username, secret = found
        store = self.commands.sites()
        profile = next((p for p in store.sites if p.name == PRACTICE_NAME), None)
        if profile is None:
            profile = st.SiteProfile(st.new_site_id(), PRACTICE_NAME, site_url(), username)
        st.save_secret(profile.id, secret)
        store.upsert(profile)
        st.save_sites(store, self._data_dir)
        self.reload_profiles()  # type: ignore[attr-defined]
        self.frame.rebuild_tree()
        self.say(f"{PRACTICE_NAME} is connected. It is under Sites.")

    # -- the calendar (15.3) ------------------------------------------------------

    def calendar_rows(self) -> list[WbRow]:
        """Off the UI thread: each day as a row, and the days kept for the tree."""
        from quill.core.wordpress.workbench_bold import day_words

        since = time.strftime("%Y-%m-%d", time.localtime(time.time() - 14 * 86400))
        sites = [(name, self.ctx(name).api) for name in self._profiles]
        days = calendar_days(sites, since=since)
        self.days = days
        rows: list[WbRow] = []
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
            return fact_rows("", facts)
        tools = find_cli()
        running = getattr(self, "_practice", None) is not None
        return fact_rows(
            "",
            [
                ("Playground's tool", str(tools.cli) if tools.cli else "not in this build"),
                ("Node.js", str(tools.node) if tools.node else "not found"),
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
