"""Media row > Replace File..., in the WordPress Workbench (wp_missing.md, Media).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`;
what each path means is :mod:`quill.core.wordpress.media_replace`:

- where the site's REST index lists a replace route, the file is replaced in
  place after a preview of both files, then read back to say whether the
  address really stayed the same;
- otherwise the person chooses: upload the new file and point every use of
  the old one at it (previewed item by item; Ctrl+Z puts them back), or,
  where Enable Media Replace is active, open its box in wp-admin, which
  keeps the address. After a repoint QUILL says plainly that the address
  changed, how many places it updated, and that links from other websites
  break unless a redirect is added -- and offers one where the site has
  the Redirection plugin.

Every network call runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress import media_replace as mr
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchMediaReplace"]

_REPOINT = "Upload it as a new file and point every use at it (the address changes)"
_EMR = "Open Enable Media Replace in wp-admin (the address stays the same)"
_KEEP = "Keep the old file in the library"
_DELETE = "Delete the old file permanently once every use is moved (cannot be undone)"


class WorkbenchMediaReplace:
    """Replace File, on a Media Library row."""

    frame: Any
    commands: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    _file: Callable[..., Path | None]

    def do_replace_file(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "media":
            self.say("Replace File works on a file in the Media Library.")
            return
        path = self._file(f"Replace {row.title} with", "All files (*.*)|*.*", save=False)
        if path is None:
            return
        from quill.core.wordpress import media_tools as mt

        size = path.stat().st_size
        if size > mt.MAX_DOWNLOAD_BYTES:
            self.say(f"{path.name} is larger than the 64 MB QUILL sends in one file.")
            return
        kind = mt.content_type_for(path.name)
        if not mt.allowed_content_type(kind):
            self.say(f"{path.name} is a {kind}, which a WordPress Media Library does not take.")
            return
        new = mr.FileFacts(path.name, size, kind)
        api = self.ctx(row.site).api

        def look() -> dict[str, Any]:
            from quill.core.wordpress.api import WordPressApiError
            from quill.core.wordpress.site_features import read_index

            index = read_index(api)
            try:
                plugins = api.get("wp/v2/plugins", context="edit")
            except WordPressApiError:
                plugins = []
            old = api.get(f"wp/v2/media/{int(row.key)}", context="edit")
            return {
                "route": mr.replace_route(index.routes, int(row.key)),
                "emr": mr.emr_active(p for p in plugins or [] if isinstance(p, dict)),
                "redirects": index.supports("redirection/v1"),
                "old": old if isinstance(old, dict) else dict(row.raw),
            }

        self.background(
            f"reading what {row.site} can do with {row.title}",
            look,
            lambda found: self._replace_chosen(row, path, new, found),
        )

    def _replace_chosen(self, row: WbRow, path: Path, new: Any, found: dict[str, Any]) -> None:
        old = found["old"]
        old_url = str(old.get("source_url", "") or row.link)
        facts = mr.file_facts(old)
        if found["route"]:
            self._replace_in_place(row, path, new, facts, old_url, found["route"])
            return
        choices = [_REPOINT] + ([_EMR] if found["emr"] else [])
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Replace File",
            prompt="&How:",
            rows=choices,
            help_text=(
                f"WordPress has no way to swap a file in place over REST, and {row.site} lists "
                "no plugin route that does. Uploading as a new file gives it a new address; "
                "QUILL then points every post, page, pattern and featured image that used the "
                "old file at the new one. Enable Media Replace, where it is active, keeps the "
                "address, but only in wp-admin."
            ),
        )
        if index is None:
            return
        if choices[index] == _EMR:
            self.say(
                f"Opening {row.title}'s edit screen, where Enable Media Replace's Replace Media "
                "box is. You must be signed in to wp-admin in your browser. Press F5 here after."
            )
            site_url = self.ctx(row.site).api.address.site_url
            self.commands.host.open_in_browser(mr.emr_screen(site_url, int(row.key)))
            return
        api = self.ctx(row.site).api
        self.background(
            f"finding where {row.title} is used",
            lambda: mr.plan_repoint(api, row.site, old),
            lambda plan: self._repoint(row, path, new, facts, old_url, plan, found["redirects"]),
        )

    def _replace_in_place(
        self, row: WbRow, path: Path, new: Any, facts: Any, old_url: str, route: str
    ) -> None:
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Replace File",
            summary=f"Replace {row.title} on {row.site} with {path.name}?",
            lines=[
                *mr.preview_lines(facts, new, old_url, in_place=True),
                f"Sent to {route}, a route {row.site}'s plugin lists; QUILL reads the file "
                "back afterwards to check the address.",
                "The old file cannot be put back by QUILL.",
            ],
            yes="Replace File",
        ):
            return
        api = self.ctx(row.site).api

        def work() -> tuple[bool, str]:
            return mr.replace_in_place(
                api, route, int(row.key), path.name, path.read_bytes(), new.kind, old_url
            )

        def done(answer: tuple[bool, str]) -> None:
            _kept, said = answer
            self.say(said)
            self.history.record(Change(row.title, said, undo=None))
            self.refresh()

        self.background(f"replacing {row.title}", work, done)

    def _repoint(
        self,
        row: WbRow,
        path: Path,
        new: Any,
        facts: Any,
        old_url: str,
        plan: mr.Repoint,
        redirects: bool,
    ) -> None:
        lines = [
            *mr.preview_lines(facts, new, old_url, in_place=False),
            f"{len(plan.items)} items use it, and each is pointed at the new file:",
            *plan.lines(),
            "Ctrl+Z puts every item back; the new file stays in the library.",
        ]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Replace File",
            summary=(
                f"Upload {path.name} to {row.site} as a new file and point every use of "
                f"{row.title} at it? The file's address changes."
            ),
            lines=lines,
            yes="Upload and Repoint",
        ):
            return
        fate = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="The Old File",
            prompt="&Old file:",
            rows=[_KEEP, _DELETE],
            help_text=(
                "WordPress's Media Library has no Trash, so the old file is either kept or "
                "deleted for good. Deleting happens only when every use was moved."
            ),
        )
        if fate is None:
            return
        redirect = redirects and dlg.confirm(
            self.parent,
            self.show_modal,
            title="Add a Redirect",
            message=(
                f"Add a redirect on {row.site} from {old_url} to the new file's address, so "
                "links from other websites keep working? It goes through the Redirection plugin."
            ),
            yes_label="Add Redirect",
        )
        self._send_repoint(row, path, new, plan, delete_old=fate == 1, redirect=redirect)

    def _send_repoint(
        self,
        row: WbRow,
        path: Path,
        new: Any,
        plan: mr.Repoint,
        *,
        delete_old: bool,
        redirect: bool,
    ) -> None:
        api = self.ctx(row.site).api

        def work() -> tuple[str, list[Any]]:
            from quill.core.wordpress.workbench_by_name import apply_edits

            made = api.upload("wp/v2/media", path.name, path.read_bytes(), new.kind)
            new_id, new_url = int(made.get("id", 0)), str(made.get("source_url", ""))
            outcomes, sent = apply_edits(api, mr.repoint_edits(plan, new_id, new_url))
            failed = [o.line for o in outcomes if not o.ok]
            kept = True
            if delete_old and not failed and not plan.unread:
                api.delete(f"wp/v2/media/{plan.old_id}", force=True)
                kept = False
            said_redirect = self._add_redirect(api, plan.old_url, new_url) if redirect else ""
            said = mr.said_after_repoint(len(sent), failed, redirect=said_redirect, old_kept=kept)
            return said, sent

        def done(answer: tuple[str, list[Any]]) -> None:
            from quill.core.wordpress.workbench_by_name import undo_edits

            said, sent = answer
            self.say(said)

            def undo() -> str:
                return undo_edits(lambda _site: api, sent) + " The new file stays in the library."

            self.history.record(Change(row.title, said, undo=undo if sent else None))
            self.refresh()

        self.background(f"replacing {row.title}", work, done)

    @staticmethod
    def _add_redirect(api: Any, old_url: str, new_url: str) -> str:
        from quill.core.wordpress.api import WordPressApiError
        from quill.core.wordpress.workbench_redirects import default_group, read_groups

        try:
            group = default_group(read_groups(api))
            if not group:
                return (
                    "No redirect was added: the Redirection plugin has no group to keep it in, "
                    "so links from other websites to the old address will break."
                )
            api.post("redirection/v1/redirect", mr.redirect_for(old_url, new_url, group))
        except WordPressApiError as exc:
            return (
                f"The redirect was not added ({exc.plain or exc}), so links from other websites "
                "to the old address will break."
            )
        return "A redirect now sends the old address to the new one."
