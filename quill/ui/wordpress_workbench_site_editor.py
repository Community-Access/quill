"""Site Editor writing and wp-admin's map, in the Workbench (wordpress.md 9.18, 6, 7 and 14).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.
What each command means is :mod:`quill.core.wordpress.workbench_site_editor`
and :mod:`quill.core.wordpress.workbench_admin_map`; the context-menu rows,
with why none has a chord, are
:mod:`quill.core.wordpress.workbench_dashboard_places`.

- **Edit Block Markup**, **Earlier Versions**, **Reset to the Theme's
  Version** and **New Template** on a template or part, and **Edit
  Additional CSS**: every write is read back line by line in a preview,
  re-reads the site first and stops on a conflict, and records its undo
  (Ctrl+Z). The site's role decides who may; the window refuses with the
  reason before any dialog opens.
- **Open in Dashboard**, **Go to Its Place** and **wp-admin for This Place**:
  the screen's reason is said, then the exact address opens in the browser.

Every network call runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_site_editor as se
from quill.core.wordpress.workbench_admin_map import screen_link, screens_for
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchSiteEditorCommands"]

_TEMPLATE_HELP = (
    "The block markup, as WordPress stores it: each block is an HTML comment that opens and "
    "closes it. Change the text, then OK reads the change back before anything is sent."
)
_CSS_HELP = (
    "The site's Additional CSS. It applies to every page of the site; OK reads the change "
    "back before anything is sent."
)


class WorkbenchSiteEditorCommands:
    """Templates, parts and Additional CSS; wp-admin's screens by place."""

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
    split: Callable[[str], tuple[str, str]]

    def _undoable(self, summary: str, undo: Callable[[], str]) -> None:
        self.history.record(Change(summary, summary, undo=undo))

    # -- templates and parts -------------------------------------------------------

    def _template_row(self, row: WbRow | None) -> bool:
        if row is None or row.kind != "template" or not row.route:
            self.say("Choose a template or template part first.")
            return False
        return True

    def do_edit_template(self, _ref: Any, row: WbRow | None) -> None:
        if not self._template_row(row):
            return
        assert row is not None
        api = self.ctx(row.site).api
        self.background(
            f"reading {row.title}",
            lambda: se.load_template(api, row.route),
            lambda loaded: self._edit_template(row.site, loaded),
        )

    def _edit_template(self, site: str, loaded: se.TemplateText) -> None:
        title = f"{loaded.noun.capitalize()}: {loaded.title}"
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt="&Block markup:",
            value=loaded.content,
            help_text=_TEMPLATE_HELP,
            multiline=True,
        )
        if text is None or text == loaded.content:
            if text is not None:
                self.say(f"{loaded.title} is unchanged, so nothing was sent.")
            return
        becomes = (
            ""
            if loaded.customized
            else " It comes from the theme, so the site keeps its own copy; Reset to the "
            "Theme's Version goes back."
        )
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Save {title}",
            summary=f"Save the {loaded.noun} {loaded.title} on {site}?{becomes}",
            lines=se.change_lines(loaded.content, text),
            yes="Save",
        ):
            return
        api = self.ctx(site).api

        def done(saved: se.TemplateText) -> None:
            summary = f"Saved the {loaded.noun} {loaded.title} on {site}."

            def undo() -> str:
                self._template_put_back(api, saved, loaded)
                return f"{loaded.title} is back as it was on {site}."

            self._undoable(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(f"saving {loaded.title}", lambda: se.save_template(api, loaded, text), done)

    @staticmethod
    def _template_put_back(api: Any, now: se.TemplateText, before: se.TemplateText) -> None:
        """Undo: the theme's own version comes back by a reset, a custom one by its text."""
        if before.customized:
            se.restore_template(api, now, before.content)
        else:
            se.reset_template(api, se.load_template(api, now.route))

    def do_template_revisions(self, _ref: Any, row: WbRow | None) -> None:
        if not self._template_row(row):
            return
        assert row is not None
        api = self.ctx(row.site).api

        def work() -> tuple[se.TemplateText, list[se.Revision]]:
            loaded = se.load_template(api, row.route)
            return loaded, (se.template_revisions(api, loaded) if loaded.customized else [])

        self.background(
            f"reading {row.title}'s earlier versions",
            work,
            lambda found: self._template_versions(row.site, found),
        )

    def _template_versions(
        self, site: str, found: tuple[se.TemplateText, list[se.Revision]]
    ) -> None:
        loaded, revisions = found
        earlier = [r for r in revisions if r.content != loaded.content]
        if not earlier:
            self.say(f"{loaded.title} has no earlier versions on the site.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Earlier Versions of {loaded.title}",
            prompt="&Versions:",
            rows=[f"Saved {r.when}" for r in earlier],
            help_text="Each earlier version the site kept, newest first. OK previews it.",
        )
        if index is None:
            return
        chosen = earlier[index]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Restore {loaded.title}",
            summary=f"Put back the version of {loaded.title} saved {chosen.when}?",
            lines=se.change_lines(loaded.content, chosen.content),
            yes="Restore",
        ):
            return
        api = self.ctx(site).api

        def done(saved: se.TemplateText) -> None:
            summary = f"Restored {loaded.title} to its version of {chosen.when}."

            def undo() -> str:
                se.restore_template(api, saved, loaded.content)
                return f"{loaded.title} is back as it was."

            self._undoable(summary, undo)
            self.say(summary)
            self.refresh()

        def work() -> se.TemplateText:
            se.check_template(api, loaded)
            return se.restore_template(api, loaded, chosen.content)

        self.background(f"restoring {loaded.title}", work, done)

    def do_reset_template(self, _ref: Any, row: WbRow | None) -> None:
        if not self._template_row(row):
            return
        assert row is not None
        api = self.ctx(row.site).api

        def work() -> tuple[se.TemplateText, str]:
            loaded = se.load_template(api, row.route)
            return loaded, se.theme_version(api, loaded)

        self.background(
            f"reading {row.title}", work, lambda got: self._template_reset(row.site, *got)
        )

    def _template_reset(self, site: str, loaded: se.TemplateText, theirs: str) -> None:
        if not loaded.customized:
            self.say(f"{loaded.title} already is the theme's version; nothing to reset.")
            return
        if loaded.has_theme_file:
            verb, summary = "Reset", f"Reset {loaded.title} to the theme's version on {site}?"
            lines = (
                se.change_lines(loaded.content, theirs)
                if theirs
                else ["The theme's version could not be read for this preview."]
            )
        else:
            verb = "Delete"
            summary = (
                f"The theme has no {loaded.title}, so resetting deletes this {loaded.noun} from "
                f"{site}. Pages that use it fall back to the theme's own."
            )
            lines = [f"{len(loaded.content.splitlines())} lines of block markup are removed."]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"{verb} {loaded.title}",
            summary=summary,
            lines=lines,
            yes=verb,
        ):
            return
        api = self.ctx(site).api

        def done(_gone: se.TemplateText) -> None:
            said = f"{loaded.title} on {site} is the theme's version again."
            if not loaded.has_theme_file:
                said = f"Deleted the {loaded.noun} {loaded.title} from {site}."

            def undo() -> str:
                se.restore_template(api, loaded, loaded.content)
                return f"{loaded.title} is the site's own copy again."

            self._undoable(said, undo)
            self.say(said)
            self.refresh()

        self.background(f"resetting {loaded.title}", lambda: se.reset_template(api, loaded), done)

    def do_new_template(self, ref: Any, row: WbRow | None) -> None:
        site = (row.site if row is not None else "") or self.site_of(ref)
        if not site:
            self.say("Choose a site's Templates or Template Parts first.")
            return
        part = row is not None and row.subkind == "wp_template_part"
        kind = "wp_template_part" if part else "wp_template"
        slug = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="New Template Part" if part else "New Template",
            prompt="&Name (slug):",
            value="",
            help_text=(
                "Lowercase letters, numbers and hyphens: single-post-news for one post, "
                "page-about for one page, category-news for a category. It starts from the "
                "template WordPress would use for that name today."
            ),
        )
        if not slug or not slug.strip():
            return
        api = self.ctx(site).api
        clean = slug.strip().lower()

        def work() -> se.TemplateText | None:
            return None if part else se.lookup_template(api, clean)

        self.background(
            f"looking up {clean}",
            work,
            lambda base: self._template_create(site, kind, clean, base),
        )

    def _template_create(
        self, site: str, kind: str, slug: str, base: se.TemplateText | None
    ) -> None:
        noun = "template part" if kind == "wp_template_part" else "template"
        start = f"It starts as a copy of {base.title}." if base else "It starts empty."
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"New {noun.capitalize()}",
            summary=f"Make the {noun} {slug} on {site}? {start}",
            lines=se.change_lines("", base.content if base else ""),
            yes="Make It",
        ):
            return
        api = self.ctx(site).api
        content = base.content if base else ""

        def done(made: se.TemplateText) -> None:
            summary = f"Made the {noun} {made.slug or slug} on {site}."

            def undo() -> str:
                api.delete(made.route, force=True)
                return f"Deleted the {noun} {slug} again."

            self._undoable(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(
            f"making {slug}", lambda: se.create_template(api, kind, slug, slug, content), done
        )

    def do_open_site_editor(self, _ref: Any, row: WbRow | None) -> None:
        if not self._template_row(row):
            return
        assert row is not None
        profile = self.profile(row.site)
        base = str(getattr(profile, "site_url", "") or "").rstrip("/")
        if not base:
            self.say(f"{row.site} has no address QUILL knows.")
            return
        from urllib.parse import urlencode

        query = urlencode({"postType": row.subkind or "wp_template", "postId": row.key})
        self.commands.host.open_in_browser(f"{base}/wp-admin/site-editor.php?{query}")
        self.say(f"Opened {row.title} in the Site Editor on {row.site}, in your browser.")

    # -- Additional CSS --------------------------------------------------------------

    def do_edit_css(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "custom_css":
            self.say("Choose the Additional CSS row of a block theme first.")
            return
        styles_id = int(row.raw.get("styles_id", 0) or 0)
        api = self.ctx(row.site).api
        self.background(
            "reading the Additional CSS",
            lambda: se.load_css(api, styles_id),
            lambda loaded: self._edit_css(row.site, loaded),
        )

    def _edit_css(self, site: str, loaded: se.CssText) -> None:
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Additional CSS: {site}",
            prompt="&CSS:",
            value=loaded.css,
            help_text=_CSS_HELP,
            multiline=True,
        )
        if text is None or text == loaded.css:
            if text is not None:
                self.say("The Additional CSS is unchanged, so nothing was sent.")
            return
        problem = se.css_problem(text)
        if problem:
            self.say(f"Nothing was sent. {problem}")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Save Additional CSS",
            summary=(
                f"Save the Additional CSS of {site}? CSS changes how every page of the site "
                "looks. WordPress keeps the version it replaces in Previous Looks."
            ),
            lines=se.change_lines(loaded.css, text),
            yes="Save",
        ):
            return
        api = self.ctx(site).api

        def done(saved: se.CssText) -> None:
            summary = f"Saved the Additional CSS of {site}."

            def undo() -> str:
                se.save_css(api, saved, loaded.css)
                return f"The Additional CSS of {site} is back as it was."

            self._undoable(summary, undo)
            self.say(summary)
            self.refresh()

        self.background("saving the Additional CSS", lambda: se.save_css(api, loaded, text), done)

    # -- wp-admin, by place --------------------------------------------------------

    def _open_screen_row(self, site: str, name: str, why: str, link: str) -> None:
        if not link:
            self.say(f"{site} has no address QUILL knows, so {name} cannot be opened.")
            return
        self.say(f"{why} Opening {name} on {site} in your browser.")
        self.commands.host.open_in_browser(link)

    def do_open_admin_screen(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "admin_screen":
            self.say("Choose a wp-admin screen first.")
            return
        why = str(row.raw.get("why", "") or "")
        self._open_screen_row(row.site, str(row.raw.get("name", "") or row.title), why, row.link)

    def do_go_to_place(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.workbench_frame import NodeRef

        node = str(row.raw.get("node", "") or "") if row is not None else ""
        if row is None or not node:
            self.say("Choose a wp-admin screen first.")
            return
        if self.frame.select(NodeRef("site", node, row.site)):
            self.frame.tree.SetFocus()
            return
        self.say(f"{row.title} has no place in the Workbench on {row.site}.")

    def do_admin_here(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref)
        if not site or ref is None:
            self.say("wp-admin for This Place works on a site's nodes.")
            return
        ctx = self.ctx(site)
        namespaces = ctx.info.namespaces if ctx.info is not None else ()
        screens = screens_for(ref.key, namespaces)
        if not screens:
            self.say(
                "No wp-admin screen is nearer to this place than the Workbench itself. "
                "Overview > wp-admin Screens lists them all."
            )
            return
        index: int | None = 0
        if len(screens) > 1:
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="wp-admin for This Place",
                prompt="&Screens:",
                rows=[f"{s.name}: {s.rest_words}" for s in screens],
                help_text="The wp-admin screens nearest here. OK opens the one chosen.",
            )
        if index is None:
            return
        screen = screens[index]
        profile = self.profile(site)
        link = screen_link(str(getattr(profile, "site_url", "") or ""), screen)
        self._open_screen_row(site, screen.name, screen.says, link)
