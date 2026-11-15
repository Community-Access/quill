"""Tools > WXR Files in the WordPress Workbench (wp_missing.md, Moving).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Export Site as WXR**: a scope (everything, posts, pages, a date range or
  one category), a file name, then the file written on this computer from
  what QUILL reads (:mod:`quill.core.wordpress.wxr_export`), checked by
  reading it back, and a report ending with what was left out and why.
- **Import WXR as Drafts**: the file read here
  (:mod:`quill.core.wordpress.wxr_read`), matched against the site
  (:mod:`quill.core.wordpress.wxr_import`), previewed line by line, then made
  as drafts. Files named in the export are downloaded only when the person
  chooses to, with the hosts named in the question; Ctrl+Z moves the drafts
  to the Trash.

Every network call runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchWxrCommands"]

_SCOPES = (
    ("everything", "Everything: posts, pages, patterns, other types, files, menus, comments"),
    ("posts", "Posts only"),
    ("pages", "Pages only"),
    ("dates", "Posts and pages in a date range..."),
    ("category", "Posts in one category..."),
)
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WXR_FILES = "WordPress export files (*.xml)|*.xml|All files (*.*)|*.*"


class WorkbenchWxrCommands:
    """Export Site as WXR and Import WXR as Drafts."""

    frame: Any
    parent: Any
    history: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    _site_now: Callable[[Any], str]
    _file: Callable[..., Path | None]

    # -- export -----------------------------------------------------------------------

    def do_export_wxr(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Export Site as WXR",
            prompt="&Export:",
            rows=[label for _k, label in _SCOPES],
            help_text=(
                f"What of {site} goes in the file. A part takes only the people, terms and "
                "files its items use, as WordPress's own exporter does; comments and menus "
                "go only with Everything."
            ),
        )
        if index is None:
            return
        from quill.core.wordpress.wxr_export import Scope

        kind = _SCOPES[index][0]
        if kind == "dates":
            scope = self._ask_dates()
            if scope is not None:
                self._export_to_file(site, scope)
        elif kind == "category":
            self._ask_category(site)
        else:
            self._export_to_file(site, Scope(kind))

    def _ask_dates(self) -> Any:
        from quill.core.wordpress.wxr_export import Scope

        days = []
        for word in ("From", "To"):
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="Export Site as WXR",
                prompt=f"&{word} (year-month-day, or blank):",
                help_text=(
                    "A day written as 2026-01-31. Leave From blank to start at the first post, "
                    "To blank to end today. Both days are included."
                ),
            )
            if text is None:
                return None
            text = text.strip()
            if text and not _DAY.match(text):
                self.say(f"{text} is not a day written as year-month-day, such as 2026-01-31.")
                return None
            days.append(text)
        return Scope("dates", after=days[0], before=days[1])

    def _ask_category(self, site: str) -> None:
        from quill.core.wordpress.wxr_export import Scope

        api = self.ctx(site).api

        def chosen(terms: list[dict[str, Any]]) -> None:
            if not terms:
                self.say(f"{site} has no categories QUILL can read.")
                return
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Export Site as WXR",
                prompt="&Category:",
                rows=[f"{t.get('name', '')} ({t.get('count', 0)} posts)" for t in terms],
                help_text="The posts filed under this category go in the file.",
            )
            if index is not None:
                term = terms[index]
                scope = Scope("category", category=int(term["id"]), category_name=term["name"])
                self._export_to_file(site, scope)

        self.background(
            f"reading {site}'s categories",
            lambda: list(api.iter_collection("wp/v2/categories", {"_fields": "id,name,count"})),
            chosen,
        )

    def _export_to_file(self, site: str, scope: Any) -> None:
        path = self._file("Export Site as WXR", _WXR_FILES, save=True)
        if path is None:
            return
        if not path.suffix:
            path = path.with_suffix(".xml")
        api = self.ctx(site).api

        def work() -> tuple[Any, tuple[bool, str]]:
            from quill.core.wordpress.wxr_export import export_wxr
            from quill.core.wordpress.wxr_read import validate_wxr

            report = export_wxr(api, path, scope)
            return report, validate_wxr(path)

        def done(answer: tuple[Any, tuple[bool, str]]) -> None:
            from quill.core.wordpress.workbench_carry import left_out_section

            report, (good, checked) = answer
            said = f"{report.sentence(path.name)} {checked}"
            self.say(said)
            dlg.show_report(
                self.parent,
                self.show_modal,
                title="Export Site as WXR",
                text="\n".join([
                    f"{site}: {scope.words()}.",
                    said,
                    *left_out_section(report.left_out),
                ]),
                help_text="What went into the WXR file, the check of it, then what was left out.",
            )
            if not good:
                self.say("The file did not pass its check; it is kept so you can look at it.")

        self.background(f"exporting {site} as WXR", work, done)

    # -- import -----------------------------------------------------------------------

    def do_import_wxr(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        path = self._file("Import WXR as Drafts", _WXR_FILES, save=False)
        if path is None:
            return
        api = self.ctx(site).api

        def work() -> Any:
            from quill.core.wordpress.wxr_import import plan_import
            from quill.core.wordpress.wxr_read import read_wxr

            return plan_import(api, read_wxr(path.read_bytes(), path.name))

        def failed(error: BaseException) -> None:
            self.say(str(getattr(error, "plain", "") or error))

        self.frame._run_background(
            f"WordPress Workbench: reading {path.name}",
            work,
            lambda plan: self._import_planned(site, path, plan),
            failed,
        )

    def _import_planned(self, site: str, path: Path, plan: Any) -> None:
        if not plan.items:
            self.say(f"{path.name} has nothing {site} can take as a draft.")
            return
        if plan.unmatched and len(plan.people) > 1:
            ids = [i for i, _n in plan.people]
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Import WXR as Drafts",
                prompt="&Give unmatched authors' items to:",
                rows=[name for _i, name in plan.people],
                initial=ids.index(plan.fallback) if plan.fallback in ids else 0,
                help_text=(
                    f"{len(plan.unmatched)} authors in the file have no account on {site} with "
                    f"the same login or email: {', '.join(plan.unmatched[:5])}."
                ),
            )
            if index is None:
                return
            plan.fallback = ids[index]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Import WXR as Drafts",
            summary=(
                f"Make {len(plan.items)} items from {path.name} on {site}, all as drafts? "
                "Ctrl+Z moves them to the Trash afterwards."
            ),
            lines=plan.lines(),
            yes="Import as Drafts",
        ):
            return
        download = False
        if plan.attachments:
            hosts = ", ".join(plan.hosts)
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Files in the Export",
                prompt="&Files:",
                rows=[
                    f"Download the {len(plan.attachments)} files from {hosts} and upload them "
                    f"to {site}",
                    "Skip the files; the text keeps pointing at the old site",
                ],
                initial=1,
                help_text=(
                    f"Downloading asks {hosts} for each file by the address the export names, "
                    "over HTTPS, up to 64 MB each, sending no password. Skipping leaves the "
                    "pictures where they are."
                ),
            )
            if index is None:
                return
            download = index == 0
        self._send_import(site, path, plan, download=download)

    def _send_import(self, site: str, path: Path, plan: Any, *, download: bool) -> None:
        api = self.ctx(site).api

        def fetch(address: str) -> Any:
            from quill.core.wordpress import media_tools as mt

            return mt.download_file(api._opener, address, timeout=max(api.timeout, 30.0))

        def work() -> Any:
            from quill.core.wordpress.wxr_import import send_import

            here = str(api.address.site_url)
            return send_import(api, plan, here=here, fetch=fetch if download else None)

        def done(result: Any) -> None:
            from quill.core.wordpress.wxr_import import undo_import

            said = (
                f"Imported {result.count} of {len(plan.items)} items from {path.name} into "
                f"{site} as drafts, with {result.uploaded} files. Ctrl+Z moves the drafts to "
                "the Trash."
            )
            self.say(said)
            self.history.record(
                Change(site, said, undo=(lambda: undo_import(api, result)) if result.made else None)
            )
            dlg.show_report(
                self.parent,
                self.show_modal,
                title="Import WXR as Drafts",
                text="\n".join([said, "", *result.lines]),
                help_text="What happened to each term, file and item, then what was left out.",
            )
            self.refresh()

        self.background(f"importing {path.name}", work, done)
