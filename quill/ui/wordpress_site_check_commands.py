"""Check the Whole Site, Fix in Bulk, Undo Site Fix, Site-wide Find and Replace (wordpress.md 9.5).

The site-wide half of File > WordPress > Checking, a base of
:class:`~quill.ui.wordpress_check_commands.WordPressCheckCommands` split for
size. The same rules as every WordPress command: the host is the only door to
the editor, every network call is a background task, every outcome one
spoken sentence naming the site.

Fixes and replacements are made on fresh copies of each page, after one
confirmation that names the site and the number of pages, and go in
``batch/v1`` requests. What each page said before is kept on this computer
(:class:`~quill.core.wordpress.site_fixes.FixRecordStore`), so Undo Site Fix
can put it all back -- leaving alone any page changed on the site since.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import cdp
from quill.core.wordpress import checks as chk
from quill.core.wordpress import local as lc
from quill.core.wordpress import page_audit as pa
from quill.core.wordpress import site_fixes as sf
from quill.core.wordpress import site_report as rpt
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

_CHUNK = 10
_PREVIEW_PAGES = 30

Key = tuple[str, int]


def plain(exc: BaseException) -> str:
    """The sentence an error was raised with, without its support code."""
    return str(exc.args[0]) if exc.args else str(exc)


def _ref(page: sf.SitePage) -> rpt.PageRef:
    return rpt.PageRef(page.kind, page.item_id, page.title or "(untitled)", page.link)


def _pages(n: int) -> str:
    return f"{n} page" + ("" if n == 1 else "s")


class WordPressSiteCheckCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # plumbing

    def _fix_store(self) -> sf.FixRecordStore:
        return sf.FixRecordStore(self.local.root)

    def _check_history(self) -> rpt.CheckHistory:
        return rpt.CheckHistory(self.local.root)

    def _site_for(self, title: str) -> st.SiteProfile | None:
        """The site of the document in front of the person, else the one they choose."""
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        copy = self.local.copy_for_path(self.host.current_path())
        if copy is not None:
            profile = store.get(copy.site_id)
            if profile is not None:
                return profile  # type: ignore[no-any-return]
        return self.pick_site(store, title)  # type: ignore[attr-defined,no-any-return]

    # ------------------------------------------------------------------ #
    # Check the Whole Site

    def cmd_check_site(self) -> None:
        profile = self._site_for("Check the Whole Site")
        if profile is None:
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> tuple[list[sf.SitePage], list[tuple[rpt.PageRef, list[chk.Finding]]]]:
            pages = sf.fetch_items(api)
            content = [(_ref(p), chk.check_content(p.content, title=p.title)) for p in pages]
            return pages, content

        def loaded(result: tuple[list[sf.SitePage], Any]) -> None:
            pages, content = result
            if not pages:
                self.host.announce(f"{profile.name} has no published pages or posts to check.")
                return
            if not (pa.axe_available() and cdp.find_browser() is not None):
                self._site_checked(profile, pages, content, [], visitor_checked=False)
                return
            choice = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Check the Whole Site",
                prompt="&How thorough:",
                rows=[
                    f"Your content only: fast, {_pages(len(pages))}",
                    "Your content and the visitor's view with axe-core: slower, loads every "
                    "page in a hidden browser",
                ],
                help_text=(
                    "The visitor's view also checks the theme, menus and footer, the way "
                    "Check This Page does. Neither sends anything anywhere."
                ),
            )
            if choice is None:
                return
            if choice == 0:
                self._site_checked(profile, pages, content, [], visitor_checked=False)
                return
            self._visitor_chunk(profile, pages, content, [], 0)

        self.background(f"reading every page on {profile.name}", work, loaded)  # type: ignore[attr-defined]

    def _visitor_chunk(
        self,
        profile: st.SiteProfile,
        pages: list[sf.SitePage],
        content: list[Any],
        visitor: list[Any],
        start: int,
    ) -> None:
        chunk = [p for p in pages[start : start + _CHUNK] if p.link]

        def work() -> list[pa.PageAudit] | BaseException:
            if not chunk:
                return []
            try:
                return pa.audit_urls([p.link for p in chunk])
            except (cdp.CdpError, cdp.BrowserMissingError, pa.AxeMissingError) as exc:
                return exc

        def done(audits: list[pa.PageAudit] | BaseException) -> None:
            if isinstance(audits, BaseException):
                self.host.announce(
                    f"The visitor's view stopped: {plain(audits)} The report has your content "
                    "checks."
                )
                self._site_checked(profile, pages, content, visitor, visitor_checked=False)
                return
            for page, audit in zip(chunk, audits, strict=False):
                rules = [
                    (f.rule, pa.plain_rule(f)[0], f.owner, len(f.nodes))
                    for f in audit.findings
                    if f.outcome == "violation"
                ]
                visitor.append((_ref(page), rules))
            following = start + _CHUNK
            if following < len(pages):
                self.host.announce(f"Checked {following} of {len(pages)} pages on {profile.name}.")
                self._visitor_chunk(profile, pages, content, visitor, following)
                return
            self._site_checked(profile, pages, content, visitor, visitor_checked=True)

        end = min(len(pages), start + _CHUNK)
        self.background(  # type: ignore[attr-defined]
            f"checking pages {start + 1} to {end} on {profile.name}", work, done
        )

    def _site_checked(
        self,
        profile: st.SiteProfile,
        pages: list[sf.SitePage],
        content: list[Any],
        visitor: list[Any],
        *,
        visitor_checked: bool,
    ) -> None:
        problems = rpt.group_problems(content, visitor)
        history = self._check_history()
        previous = history.latest(profile.id)
        history.add(
            profile.id,
            rpt.history_entry(problems, len(pages), visitor_checked=visitor_checked),
        )
        summary = rpt.site_summary(profile.name, problems, len(pages), previous)
        self.host.announce(summary)
        if not problems:
            return
        by_ref = {_ref(p): p for p in pages}

        def details(index: int) -> str:
            problem = problems[index]
            return "\n".join(ref.title for ref in problem.pages)

        def show_pages(index: int | None) -> object:
            if index is not None:
                self._problem_pages(profile, problems[index])
            return None

        def fix(index: int | None) -> object:
            if index is None:
                return None
            return self._fix_in_bulk(profile, problems[index], by_ref)

        purpose = summary
        if not visitor_checked:
            purpose += " Only your content was checked; Check This Page shows the visitor's view."
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Check the Whole Site",
            purpose=purpose,
            list_label="&Problems:",
            list_help=(
                "Each problem, how often it happens and on how many pages, most frequent first."
            ),
            rows=[p.row() for p in problems],
            details=details,
            actions=[
                dlg.Action(
                    "&Pages...", "List the pages with this problem, to open one.", show_pages
                ),
                dlg.Action(
                    "Fix in &Bulk...",
                    "Fix this problem on every page at once, after a preview. Only for fixes "
                    "that need nobody's words.",
                    fix,
                ),
            ],
        )
        window.Destroy()

    def _problem_pages(self, profile: st.SiteProfile, problem: rpt.SiteProblem) -> None:
        refs = list(problem.pages)

        def open_one(index: int | None) -> object:
            if index is None:
                return None
            ref = refs[index]
            self.open_item(profile, ref.kind, ref.item_id)  # type: ignore[attr-defined]
            return dlg.CLOSE

        def browse(index: int | None) -> object:
            if index is not None and refs[index].link:
                self.host.open_in_browser(refs[index].link)
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=problem.label,
            purpose=f"The pages on {profile.name} with this problem.",
            list_label="&Pages:",
            list_help="Each page's title. Open one to fix it in the editor.",
            rows=[ref.title for ref in refs],
            actions=[
                dlg.Action("&Open", "Open this page in the editor.", open_one),
                dlg.Action("Open on the &Site", "Open the public page in your browser.", browse),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Fix in Bulk

    def _fix_in_bulk(
        self,
        profile: st.SiteProfile,
        problem: rpt.SiteProblem,
        by_ref: dict[rpt.PageRef, sf.SitePage],
    ) -> object:
        if not problem.fixable:
            self.host.announce(
                "QUILL cannot fix this one by itself: each needs your words or your eyes. "
                "Choose Pages to open them one at a time."
            )
            return None
        changes: list[tuple[sf.SitePage, str, int]] = []
        for ref in problem.pages:
            page = by_ref.get(ref)
            if page is None:
                continue
            fixed, count = sf.apply_fix(problem.key, page.content)
            if count:
                changes.append((page, fixed, count))
        if not changes:
            self.host.announce("There is nothing left to fix for that problem.")
            return None
        label = sf.SAFE_FIXES[problem.key]
        dlg.show_report(
            self.host.parent,
            self.host.show_modal,
            title="Fix in Bulk: Preview",
            text=preview_text(label, [(p.title, p.content, f, n) for p, f, n in changes]),
            help_text="Every page that will change, and how. Nothing has been sent yet.",
        )
        pages = len(changes)
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=f"Fix in Bulk on {profile.name}",
            message=(
                f"{label} on {_pages(pages)} on {profile.name}? A copy of each page as it is "
                "now is kept on this computer, so Undo Site Fix can put them all back."
            ),
            yes_label=f"Fix {_pages(pages).title()}",
        ):
            return None
        key = problem.key
        self._send_site_fix(
            profile,
            label,
            {(p.kind, p.item_id): None for p, _f, _n in changes},
            lambda page: sf.apply_fix(key, page.content)[0],
            verb="Fixed",
        )
        return dlg.CLOSE

    def _send_site_fix(
        self,
        profile: st.SiteProfile,
        label: str,
        targets: dict[Key, str | None],
        transform: Callable[[sf.SitePage], str],
        *,
        verb: str,
    ) -> None:
        """Re-read each page, change it, send the changes in batches, keep what it said.

        A target with expected content is left alone when the site's copy no
        longer matches it (someone changed it since the search).
        """
        api = self.api(profile)  # type: ignore[attr-defined]
        ids: dict[str, list[int]] = {}
        for kind, item_id in targets:
            ids.setdefault(kind, []).append(item_id)

        def work() -> tuple[sf.SiteFix, int, int]:
            fresh = sf.fetch_items(api, tuple(ids), statuses=sf.ALL_STATUSES, ids=ids)
            changes: list[tuple[str, int, str]] = []
            items: list[sf.FixedItem] = []
            skipped = 0
            for page in fresh:
                expected = targets.get((page.kind, page.item_id))
                if expected is not None and page.content != expected:
                    skipped += 1
                    continue
                changed = transform(page)
                if changed == page.content:
                    continue
                changes.append((page.kind, page.item_id, changed))
                items.append(sf.FixedItem(page.kind, page.item_id, page.title, page.content))
            stamps = (
                sf.batch_outcomes(api.batch(sf.update_requests(changes)), len(changes))
                if changes
                else []
            )
            kept: list[sf.FixedItem] = []
            for item, stamp in zip(items, stamps, strict=True):
                if stamp:
                    item.after_modified_gmt = stamp
                    kept.append(item)
            fix = sf.SiteFix(lc.new_local_id(), profile.id, lc.now_stamp(), label, kept)
            return fix, len(items) - len(kept), skipped

        def done(result: tuple[sf.SiteFix, int, int]) -> None:
            fix, failed, skipped = result
            if fix.items:
                self._fix_store().add(fix)
                said = (
                    f"{verb} {_pages(len(fix.items))} on {profile.name}. "
                    "Undo Site Fix puts them back."
                )
            else:
                said = f"Nothing was changed on {profile.name}."
            if failed:
                said += (
                    f" {_pages(failed).capitalize()} could not be changed; try those again later."
                )
            if skipped:
                was = "were" if skipped != 1 else "was"
                said += (
                    f" {_pages(skipped).capitalize()} changed on the site since and {was} "
                    "left alone."
                )
            self.host.announce(said)

        self.background(f"sending changes to {profile.name}", work, done)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Undo Site Fix

    def cmd_undo_site_fix(self) -> None:
        profile = self._site_for("Undo Site Fix")
        if profile is None:
            return
        fixes = self._fix_store().load(profile.id)
        if not fixes:
            self.host.announce(f"There are no site fixes to undo on {profile.name}.")
            return

        def view(index: int | None) -> object:
            if index is not None:
                fix = fixes[index]
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title="Site Fix",
                    text=f"{fix.label}\n\n" + "\n".join(i.title or "(untitled)" for i in fix.items),
                    help_text="The pages this fix changed.",
                )
            return None

        def undo(index: int | None) -> object:
            if index is None:
                return None
            fix = fixes[index]
            if fix.undone:
                self.host.announce("That fix has already been put back.")
                return None
            self._undo(profile, fix)
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Undo Site Fix",
            purpose=(
                f"Fixes and replacements made across {profile.name}, newest first. Undo puts "
                "each page back as it was, except pages changed on the site since."
            ),
            list_label="&Fixes:",
            list_help="When, what was done, and how many pages it changed.",
            rows=[f.spoken() for f in fixes],
            actions=[
                dlg.Action("&Undo...", "Put back every page this fix changed.", undo),
                dlg.Action("&View...", "List the pages this fix changed.", view),
            ],
        )
        window.Destroy()

    def _undo(self, profile: st.SiteProfile, fix: sf.SiteFix) -> None:
        api = self.api(profile)  # type: ignore[attr-defined]
        ids: dict[str, list[int]] = {}
        for item in fix.items:
            ids.setdefault(item.kind, []).append(item.item_id)

        def current() -> dict[Key, str]:
            fresh = sf.fetch_items(api, tuple(ids), statuses=sf.ALL_STATUSES, ids=ids)
            return {(p.kind, p.item_id): p.modified_gmt for p in fresh}

        def ask(stamps: dict[Key, str]) -> None:
            safe = [i for i in fix.items if stamps.get((i.kind, i.item_id)) == i.after_modified_gmt]
            changed = [i for i in fix.items if i not in safe]
            if not safe:
                self.host.announce(
                    f"Every page in that fix has changed on {profile.name} since, so nothing "
                    "was put back. Previous Versions on each page still has the older text."
                )
                return
            message = (
                f"Put back {_pages(len(safe))} on {profile.name} as they were before: {fix.label}?"
            )
            if changed:
                titles = ", ".join(i.title or "(untitled)" for i in changed[:5])
                message += (
                    f"\n\n{_pages(len(changed)).capitalize()} changed on the site since and will "
                    f"be left alone: {titles}."
                )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title=f"Undo Site Fix on {profile.name}",
                message=message,
                yes_label=f"Put Back {_pages(len(safe)).title()}",
            ):
                return

            def send() -> int:
                requests = sf.update_requests([(i.kind, i.item_id, i.before) for i in safe])
                return sum(1 for s in sf.batch_outcomes(api.batch(requests), len(safe)) if s)

            def sent(count: int) -> None:
                if count:
                    self._fix_store().mark_undone(profile.id, fix.id)
                said = f"Put back {_pages(count)} on {profile.name}."
                if count < len(safe):
                    said += f" {len(safe) - count} could not be changed; try Undo again later."
                self.host.announce(said)

            self.background(f"putting pages back on {profile.name}", send, sent)  # type: ignore[attr-defined]

        self.background(f"checking pages on {profile.name}", current, ask)  # type: ignore[attr-defined]


def preview_text(label: str, changes: list[tuple[str, str, str, int]]) -> str:
    """The Fix in Bulk preview: each page, how many places, and the changed lines."""
    lines = [f"{label}.", ""]
    for title, before, after, count in changes[:_PREVIEW_PAGES]:
        places = f"{count} place" + ("" if count == 1 else "s")
        lines.append(f"{title or '(untitled)'}: {places}")
        diff = difflib.ndiff(before.splitlines(), after.splitlines())
        shown = 0
        for row in diff:
            if row.startswith(("- ", "+ ")) and shown < 4:
                lines.append(
                    ("  Before: " if row[0] == "-" else "  After: ") + row[2:].strip()[:160]
                )
                shown += 1
        lines.append("")
    if len(changes) > _PREVIEW_PAGES:
        lines.append(f"And {len(changes) - _PREVIEW_PAGES} more pages, changed the same way.")
    return "\n".join(lines)
