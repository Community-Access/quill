"""The third sweep in the WordPress Workbench: running a site, core REST first (PRD 15.11).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Privacy Requests**, **Content Audit** and **Media > Housekeeping** list
  their rows from :mod:`quill.core.wordpress.workbench_sweep`, the last two
  from the same site scan By Name reads. A finding's **Show Where It Is
  Used** and **Move to Trash** name its usage before anything is sent, and
  Move to Trash never deletes for good. Opening a privacy screen is said as
  opening it, never as doing the request.
- **Redirects** and its **404 Log**, through the Redirection plugin's
  namespace (:mod:`quill.core.wordpress.workbench_redirects`): add (Ctrl+N
  there), change, turn on or off, delete after a named confirmation, test an
  address on the list as read, and redirect an address from the log. Where
  the namespace is missing, the node holds one row saying where redirects are.
- **A redirect when the address changes**: after a sheet saves a new slug,
  on a site whose index has the Redirection plugin's namespace, the Workbench
  offers to add a redirect from the old address, naming both; nothing is sent
  before Add Redirect. Elsewhere nothing is offered.
- **Search and Upkeep** (:mod:`quill.core.wordpress.workbench_upkeep`) and
  **Administration Areas** (every third-sweep row's disposition, from
  :data:`quill.core.wordpress.workbench_coverage.THIRD_SWEEP`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_coverage import (
    THIRD_SWEEP,
    SweepArea,
    status_words,
    sweep_disposition,
)
from quill.core.wordpress.workbench_redirects import (
    default_group,
    edit_body,
    group_label,
    not_found_row,
    read_groups,
    read_pages,
    redirect_row,
    trace_address,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sweep import (
    REDIRECTION_NAMESPACE,
    content_audit,
    media_housekeeping,
    privacy_rows,
    redirect_body,
    redirect_offered,
    trash_preview,
)
from quill.core.wordpress.workbench_upkeep import (
    certificate_row,
    lock_rows,
    overdue_rows,
    read_certificate,
    sitemap_row,
    visibility_row,
)
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg
from quill.ui.wordpress_workbench_redirect_group import WorkbenchRedirectGroup

__all__ = ["WorkbenchSweepCommands"]

#: Administration Areas whose home is a node of this site.
_AREA_NODES = {
    "Redirects": "redirects",
    "Privacy requests": "privacy_requests",
    "Content audit": "content_audit",
    "Media housekeeping": "media_housekeeping",
    "Search and sitemaps": "site_upkeep",
    "Scheduled tasks": "site_upkeep",
    "SSL and the address": "site_upkeep",
    "Someone else is editing": "site_upkeep",
}
_CODES = ("301, moved for good", "302, found elsewhere for now", "307, for now", "308, for good")
_RECENT_FIELDS = "id,title,status,date_gmt,modified_gmt,link,meta"


class WorkbenchSweepCommands(WorkbenchRedirectGroup):
    """Privacy, Content Audit, Housekeeping, Redirects, Upkeep and Administration Areas."""

    frame: Any
    parent: Any
    commands: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]

    # -- lists --------------------------------------------------------------------

    def sweep_rows(self, site: str, what: str) -> list[WbRow]:
        """Off the UI thread: one of the third sweep's lists."""
        if what in ("audit", "housekeeping"):
            scan = self.site_scan(site)  # type: ignore[attr-defined]
            return content_audit(scan) if what == "audit" else media_housekeeping(scan)
        ctx = self.ensure(self.ctx(site))
        info = ctx.info
        site_url = self.profile(site).site_url
        namespaces = info.namespaces if info is not None else ()
        if what == "privacy":
            routes = info.routes if info is not None else ()
            version = info.wp_version if info is not None else ""
            return privacy_rows(site, site_url, routes, version)
        if what in ("redirects", "not_found"):
            if not redirect_offered(namespaces):
                return [self._area_row(site, site_url, THIRD_SWEEP[0], namespaces)]
            if what == "not_found":
                return [not_found_row(site, r, site_url) for r in read_pages(ctx.api, "404")]
            items = read_pages(ctx.api, "redirect")
            self._redirect_cache()[site] = items
            return [redirect_row(site, r, site_url) for r in items]
        if what == "areas":
            return [self._area_row(site, site_url, area, namespaces) for area in THIRD_SWEEP]
        return self._upkeep(site, site_url, ctx)

    def _redirect_cache(self) -> dict[str, list[Any]]:
        return self.__dict__.setdefault("_redirects", {})

    def _area_row(self, site: str, site_url: str, area: SweepArea, namespaces: Any) -> WbRow:
        place = sweep_disposition(area, namespaces)
        found = [n for n in area.namespaces if n in {s.strip("/") for s in namespaces}]
        where = f"{status_words(place.status)}: {place.home}"
        return WbRow(
            "sweep_area",
            site,
            area.area,
            {"area": area.area, "where": where, "plugins": area.plugins},
            f"{area.area} on {site}: {where}. {area.boundary} Provided by: {area.plugins}.",
            link=f"{site_url.rstrip('/')}/wp-admin/{area.screen}",
            status=place.status,
            raw={
                "node": _AREA_NODES.get(area.area, "") if place.status == "covered" else "",
                "namespace": found[0] if found and place.status == "schema_built" else "",
            },
        )

    def _upkeep(self, site: str, site_url: str, ctx: Any) -> list[WbRow]:
        api = ctx.api
        settings: dict[str, Any] | None
        try:
            got = api.get("wp/v2/settings")
            settings = dict(got) if isinstance(got, dict) else None
        except WordPressApiError:
            settings = None
        body: bytes | None = None
        error = ""
        found: bool | None = None
        try:
            from quill.core.wordpress.workbench_bold import fetch_site_file

            body = fetch_site_file(api, site_url.rstrip("/") + "/wp-sitemap.xml")
            found = True
        except HTTPError as exc:
            error = f"it answered {exc.code}"
            found = False if exc.code in (404, 410) else None
        except (WordPressApiError, OSError, ValueError, AttributeError) as exc:
            error = getattr(exc, "plain", "") or str(exc)
        rows = [
            visibility_row(site, site_url, settings, found),
            sitemap_row(site, site_url, body, error),
        ]
        scheduled: list[Any] = []
        recent: list[Any] = []
        for kind in ("posts", "pages"):
            try:
                scheduled += list(
                    api.iter_collection(
                        f"wp/v2/{kind}",
                        {"status": "future", "context": "edit", "_fields": _RECENT_FIELDS},
                        max_pages=2,
                    )
                )
                recent += list(
                    api.iter_collection(
                        f"wp/v2/{kind}",
                        {
                            "status": "any",
                            "context": "edit",
                            "orderby": "modified",
                            "_fields": _RECENT_FIELDS,
                        },
                        max_pages=1,
                    )
                )
            except WordPressApiError:
                continue
        rows += overdue_rows(site, scheduled)
        rows.append(certificate_row(site, site_url, read_certificate(api)))
        me = int(getattr(ctx.account, "id", 0) or 0) if ctx.account is not None else 0
        rows += lock_rows(site, recent, me=me)
        return rows

    # -- findings -----------------------------------------------------------------

    def do_show_usage(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "finding":
            self.say("Show Where It Is Used works on a Content Audit or Housekeeping row.")
            return
        places = [str(p) for p in row.raw.get("places") or []]
        are = str(row.raw.get("places_are", "uses it"))
        dlg.show_report(
            self.parent,
            self.show_modal,
            title=f"Where {row.raw.get('title') or row.title} Is Used",
            text="\n".join(f"{p} {are}" for p in places)
            or f"Nothing in the posts and pages read {are}.",
            help_text="Each post or page that uses or links to it, one a line.",
        )

    def do_trash_finding(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "finding" or not row.raw.get("route"):
            self.say("Move to Trash here works on a Content Audit or Housekeeping row.")
            return
        summary, lines = trash_preview(row)
        name = str(row.raw.get("title") or row.title)
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Move {name} to the Trash",
            summary=summary,
            lines=lines,
            yes="Move to Trash",
        ):
            return
        api = self.ctx(row.site).api
        route = str(row.raw["route"])
        media = bool(row.raw.get("media"))

        def work() -> str:
            try:
                api.delete(route)
            except WordPressApiError as exc:
                if media and (exc.wp_code == "rest_trash_not_supported" or exc.status == 501):
                    return (
                        f"{row.site} keeps no Trash for media, so {name} was not deleted. "
                        "Delete Permanently on its row in Media does that, after you confirm."
                    )
                raise
            return f"Moved {name} to the Trash on {row.site}. Restore from Trash brings it back."

        def done(said: str) -> None:
            self.say(said)
            self.__dict__.get("_scans", {}).pop(row.site, None)
            self.refresh()

        self.background(f"moving {name} to the Trash", work, done)

    # -- privacy and areas ---------------------------------------------------------

    def do_open_privacy(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "privacy" or not row.link:
            self.say("Choose Export or Erase Personal Data first.")
            return
        self.commands.host.open_in_browser(row.link)
        screen = str(row.raw.get("screen", "") or row.title)
        self.say(
            f"Opened {screen} for {row.site} in your browser. Requests are confirmed and done "
            "there; QUILL cannot see whether they were."
        )

    def do_open_area(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.workbench_frame import NodeRef

        if row is None or row.kind != "sweep_area":
            return
        node = str(row.raw.get("node", "") or "")
        namespace = str(row.raw.get("namespace", "") or "")
        if node and self.frame.select(NodeRef("site", node, row.site)):
            self.frame.tree.SetFocus()
            return
        if namespace:
            from quill.core.wordpress.workbench_tree import DYNAMIC_NAMESPACE
            from quill.ui.wordpress_workbench_window import SEP

            if self.frame.select(NodeRef("site", DYNAMIC_NAMESPACE, f"{row.site}{SEP}{namespace}")):
                self.frame.tree.SetFocus()
                return
        self.commands.host.open_in_browser(row.link)
        self.say(f"Opened {row.link} in your browser.")

    # -- redirects ------------------------------------------------------------------

    def _redirect_site(self, ref: Any, row: WbRow | None) -> str:
        site = (row.site if row is not None else "") or self.site_of(ref) or self.current_site()
        if not site:
            self.say("Choose a site first.")
            return ""
        ctx = self.ctx(site)
        namespaces = ctx.info.namespaces if ctx.info is not None else ()
        if not redirect_offered(namespaces):
            self.say(
                f"{site} does not have the Redirection plugin's REST namespace, so QUILL cannot "
                "change its redirects. Administration Areas says where they are kept."
            )
            return ""
        return site

    def _ask_redirect(
        self, title: str, source: str, target: str, code: int
    ) -> tuple[str, str, int] | None:
        source = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt="Old address, from this site (such as /old-page/):",
            value=source,
            help_text="The address visitors arrive at. A path on this site.",
        )
        if source is None or not source.strip():
            return None
        target = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt="New address it leads to:",
            value=target,
            help_text="Where visitors are sent instead: a path on this site or a full address.",
        )
        if target is None or not target.strip():
            return None
        codes = [301, 302, 307, 308]
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=title,
            prompt="Kind of redirect:",
            rows=_CODES,
            initial=codes.index(code) if code in codes else 0,
            help_text="301 tells search engines the move is for good; 302 and 307 are for now.",
        )
        if index is None:
            return None
        return source.strip(), target.strip(), codes[index]

    def _send_redirect(self, site: str, route: str, body: dict[str, Any], said: str) -> None:
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Redirect Preview",
            summary=f"On {site}: {said}",
            lines=[
                f"From: {body['url']}",
                f"To: {body['action_data']['url']}",
                f"Kind: {body['action_code']}",
            ],
            yes="Save Redirect",
        ):
            return
        api = self.ctx(site).api

        def done(_result: Any) -> None:
            self.say(f"Saved on {site}: {body['url']} now leads to {body['action_data']['url']}.")
            self.refresh()

        self.background("saving a redirect", lambda: api.post(route, body), done)

    def _in_group(self, site: str, title: str, then: Callable[[int], None]) -> None:
        """Read the site's redirect groups, let the person pick one, then call *then* with its id.

        The Redirection plugin refuses a redirect without a group it has
        ("Invalid group"); the first "Redirections" group is offered first.
        """
        api = self.ctx(site).api

        def got(groups: list[Any]) -> None:
            first = default_group(groups)
            if not first:
                self._offer_first_group(site, title, then)
                return
            if len(groups) > 1:
                ids = [int(g["id"]) for g in groups]
                index = dlg.ask_choice(
                    self.parent,
                    self.show_modal,
                    title=title,
                    prompt="Group to keep it in:",
                    rows=[group_label(g) for g in groups],
                    initial=ids.index(first) if first in ids else 0,
                    help_text="The Redirection plugin keeps every redirect in a group. "
                    "Redirections is the usual one.",
                )
                if index is None:
                    return
                first = ids[index]
            then(first)

        self.background("reading the redirect groups", lambda: read_groups(api), got)

    def do_add_redirect(self, ref: Any, row: WbRow | None) -> None:
        site = self._redirect_site(ref, row)
        answer = self._ask_redirect("Add Redirect", "", "", 301) if site else None
        if answer is None:
            return
        self._in_group(
            site,
            "Add Redirect",
            lambda group: self._send_redirect(
                site,
                f"{REDIRECTION_NAMESPACE}/redirect",
                edit_body(answer[0], answer[1], answer[2], group_id=group),
                "add a redirect.",
            ),
        )

    def do_redirect_not_found(self, ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "not_found":
            return
        site = self._redirect_site(ref, row)
        answer = (
            self._ask_redirect("Redirect This Address", row.cell("address"), "", 301)
            if site
            else None
        )
        if answer is None:
            return
        self._in_group(
            site,
            "Redirect This Address",
            lambda group: self._send_redirect(
                site,
                f"{REDIRECTION_NAMESPACE}/redirect",
                edit_body(answer[0], answer[1], answer[2], group_id=group),
                "add a redirect.",
            ),
        )

    def do_edit_redirect(self, ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect":
            return
        site = self._redirect_site(ref, row)
        code = int(row.cell("code") or 301)
        answer = (
            self._ask_redirect("Change Redirect", row.cell("source"), row.cell("target"), code)
            if site
            else None
        )
        if answer is None:
            return

        def send(group: int) -> None:
            body = edit_body(
                answer[0], answer[1], answer[2], regex=bool(row.raw.get("regex")), group_id=group
            )
            self._send_redirect(
                site, f"{REDIRECTION_NAMESPACE}/redirect/{row.key}", body, "change this redirect."
            )

        kept = int(row.raw.get("group_id", 0) or 0)
        if kept:
            send(kept)
            return
        self._in_group(site, "Change Redirect", send)

    def _bulk(self, row: WbRow, action: str, message: str, yes: str, said: str) -> None:
        if not dlg.confirm(self.parent, self.show_modal, title=yes, message=message, yes_label=yes):
            return
        api = self.ctx(row.site).api

        def done(_result: Any) -> None:
            self.say(said)
            self.refresh()

        self.background(
            f"{action} a redirect",
            lambda: api.post(
                f"{REDIRECTION_NAMESPACE}/bulk/redirect/{action}", {"items": [int(row.key)]}
            ),
            done,
        )

    def do_toggle_redirect(self, ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect" or not self._redirect_site(ref, row):
            return
        on = row.status != "disabled"
        action = "disable" if on else "enable"
        verb = "Turn Off" if on else "Turn On"
        self._bulk(
            row,
            action,
            f"{verb} the redirect from {row.cell('source')} on {row.site}?",
            verb,
            f"The redirect from {row.cell('source')} is {'off' if on else 'on'}.",
        )

    def do_delete_redirect(self, ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect" or not self._redirect_site(ref, row):
            return
        self._bulk(
            row,
            "delete",
            f"Delete the redirect from {row.cell('source')} to {row.cell('target')} on "
            f"{row.site}? The Redirection plugin keeps no Trash, so it is gone for good.",
            "Delete Redirect",
            f"Deleted the redirect from {row.cell('source')} on {row.site}.",
        )

    def do_test_address(self, ref: Any, row: WbRow | None) -> None:
        site = self._redirect_site(ref, row)
        if not site:
            return
        start = row.cell("source") or row.cell("address") if row is not None else ""
        address = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Test an Address",
            prompt="Address on this site to follow:",
            value=start,
            help_text="QUILL follows the redirects it read from this site. Nothing is sent.",
        )
        if address is None:
            return
        site_url = self.profile(site).site_url
        cache = self._redirect_cache()

        def work() -> str:
            if site not in cache:
                cache[site] = read_pages(self.ctx(site).api, "redirect")
            return trace_address(address, cache[site], site_url)

        def done(said: str) -> None:
            dlg.show_report(
                self.parent,
                self.show_modal,
                title="Test an Address",
                text=said,
                help_text="Where the address leads through this site's redirects, hop by hop.",
            )

        self.background("following redirects", work, done)

    # -- after a new slug ---------------------------------------------------------

    def offer_redirect(self, row: WbRow, old_link: str) -> None:
        """After a new slug is saved: offer a redirect where the Redirection plugin is."""
        ctx = self.ctx(row.site)
        namespaces = ctx.info.namespaces if ctx.info is not None else ()
        if not old_link or not redirect_offered(namespaces):
            return
        api = ctx.api

        def got(fresh: Any) -> None:
            new_link = str(fresh.get("link", "") if isinstance(fresh, dict) else "")
            if not new_link or new_link == old_link:
                return
            if not dlg.confirm(
                self.parent,
                self.show_modal,
                title="Add a Redirect",
                message=f"{row.title} moved from {old_link} to {new_link}. Add a redirect on "
                f"{row.site}, so links to the old address still arrive?",
                yes_label="Add Redirect",
            ):
                return

            def add() -> str:
                group = default_group(read_groups(api))
                if not group:
                    return (
                        f"No redirect added: the Redirection plugin on {row.site} has no group "
                        "to keep one in."
                    )
                api.post(
                    f"{REDIRECTION_NAMESPACE}/redirect", redirect_body(old_link, new_link, group)
                )
                return f"Redirect added: {old_link} now leads to {new_link}."

            self.background("adding a redirect", add, self.say)

        self.background("reading the new address", lambda: api.get(row.route, _fields="link"), got)
