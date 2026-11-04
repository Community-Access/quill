"""Sending, properties, versions, checks, media, comments and terms (wordpress.md 5 to 9).

The mixin half of :class:`~quill.ui.wordpress_commands.WordPressCommands`,
split for size. Same rules: the host is the only door to the editor, every
network call is a background task, every outcome is one spoken sentence.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import checks as chk
from quill.core.wordpress import local as lc
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui.wordpress_check_commands import reading_level_line

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressMoreCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # the three saves (5.3) and conflict protection (5.4)

    def cmd_save_draft(self) -> None:
        self._send(publish=False)

    def cmd_publish(self) -> None:
        self._send(publish=True)

    def _send(self, *, publish: bool) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        if not self.host.save_current():
            return
        copy, profile = found
        copy = self.local.copy_for_path(self.host.current_path()) or copy
        html, problems = self.to_html(copy)  # type: ignore[attr-defined]
        if problems:
            self.host.announce(
                f"{len(problems)} lines could not be turned into blocks; Check Before "
                f"Publishing lists them."
            )
        if publish and not self._confirm_publish(copy, profile, html):
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def done(result: tuple[str, Any]) -> None:
            kind, value = result
            if kind == "conflict":
                self._conflict(copy, profile, value, publish)
                return
            self._sent(copy, profile, value)

        # A failure on the way re-reads the site, then offers Try Again or
        # queues the send (5.10; wordpress_offline_commands.py).
        self.send_in_background(  # type: ignore[attr-defined]
            copy, profile, publish, lambda: self.send_work(api, copy, publish), done
        )

    def send_work(self, api: Any, copy: lc.WorkingCopy, publish: bool) -> tuple[str, Any]:
        """The send itself, off the UI thread: conflict check, uploads, create or update.

        Shared by the menu's send and the offline queue, so a queued publish
        gets exactly the same conflict check (5.4).
        """
        account = wp.load_account(api)
        if copy.remote_id:
            site_stamp = wp.modified_gmt(api, copy.kind, copy.remote_id)
            conflict = lc.conflict_between(copy.base_modified_gmt, site_stamp)
            if conflict is not None:
                return "conflict", conflict
            before = wp.load_item(api, copy.kind, copy.remote_id)
            self.local.add_version(
                copy, lc.REASON_SITE_BEFORE_UPDATE, text=before.content, title=before.title
            )
        self._upload_pending(api, copy)
        item = item_from_copy(
            copy, self.to_html(copy)[0], status=target_status(copy, publish, account)
        )  # type: ignore[attr-defined]
        saved = wp.update_item(api, item) if copy.remote_id else wp.create_item(api, item)
        return "saved", saved

    def _confirm_publish(self, copy: lc.WorkingCopy, profile: st.SiteProfile, html: str) -> bool:
        findings = chk.check_content(
            html, title=copy.title, site_name=profile.name, default_site_name=self._default_name()
        )
        summary = chk.summary_line(findings)
        verb = "Update" if copy.remote_id and copy.status == "publish" else "Publish"
        message = f"{verb} '{copy.title or 'untitled'}' on {profile.name}?\n\n{summary}"
        if findings:
            message += "\n\n" + "\n".join(f"- {f.message}" for f in findings[:8])
        return dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=f"{verb} on {profile.name}",
            message=message,
            yes_label=f"{verb} Anyway" if findings else verb,
        )

    def _default_name(self) -> str:
        default = self.sites().default  # type: ignore[attr-defined]
        return default.name if default else ""

    def _conflict(
        self, copy: lc.WorkingCopy, profile: st.SiteProfile, conflict: lc.Conflict, publish: bool
    ) -> None:
        self.host.announce(conflict.spoken(profile.name))
        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="The Site Copy Changed",
            prompt="&What now:",
            rows=["Compare the two", "Open the site's copy", "Send mine anyway"],
            help_text=(
                "Someone changed the copy on the site after you opened yours. Nothing was sent."
            ),
        )
        if choice == 0:
            self.cmd_compare()  # type: ignore[attr-defined]
        elif choice == 1:
            self.local.add_version(copy, lc.REASON_SAVED)
            self.local.discard(copy.key)
            self.open_item(profile, copy.kind, copy.remote_id)  # type: ignore[attr-defined]
        elif choice == 2 and dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Send Mine Anyway",
            message=(
                f"Replace the newer copy on {profile.name} with yours? "
                "The site's copy is kept in Previous Versions."
            ),
            yes_label="Send Mine",
        ):
            copy.base_modified_gmt = conflict.site_modified_gmt
            self.local.save(copy)
            self._send(publish=publish)

    def _sent(self, copy: lc.WorkingCopy, profile: st.SiteProfile, saved: wp.Item) -> None:
        was_public = copy.status == "publish" and bool(copy.remote_id)
        if not copy.remote_id:
            self.local.rekey(copy, saved.id)
        copy.base_modified_gmt = saved.modified_gmt
        copy.link = saved.link
        copy.status = saved.status
        self.local.save(copy)
        if saved.status == "publish":
            self.local.add_version(copy, lc.REASON_PUBLISHED)
            self.host.set_clipboard_text(saved.link)
            self.host.announce(f"Published on {profile.name}. The address is on the clipboard.")
        elif saved.status == "pending":
            self.host.announce(f"Submitted for review on {profile.name}.")
        else:
            self.host.announce(f"Draft saved to {profile.name}. It is not public.")
        # The queue, the autosave timer, and "Add it to a menu?" (5.9).
        self.after_sent(copy, profile, saved, was_public=was_public)  # type: ignore[attr-defined]

    def _upload_pending(self, api: Any, copy: lc.WorkingCopy) -> None:
        """Upload pictures inserted from this computer, and swap in their addresses (6.4)."""
        for pending in list(copy.pending_uploads):
            path = Path(pending["path"])
            if not path.exists():
                continue
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            media = wpm.upload_media(
                api,
                path.name,
                path.read_bytes(),
                content_type,
                alt_text=str(pending.get("alt", "")),
                caption=str(pending.get("caption", "")),
            )
            copy.text = copy.text.replace(path.as_uri(), media.source_url)
            if pending.get("featured"):
                copy.properties["featured_media"] = media.id
            copy.pending_uploads.remove(pending)
        if not copy.pending_uploads:
            self.local.write_document(copy)

    # ------------------------------------------------------------------ #
    # properties (5.5)

    def cmd_properties(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        api = self.api(profile)  # type: ignore[attr-defined]

        def show(terms: tuple[list[wp.Term], list[wp.Term]]) -> None:
            categories, tags = terms
            props = copy.properties
            facts = (
                f"Site: {profile.name}\nKind: {copy.kind}\n"
                f"Status: {wp.STATUS_LABELS.get(copy.status, copy.status)}\n"
                f"Address: {copy.link or 'not on the site yet'}\nLast changed on the site: "
                + (
                    wp.friendly_date(copy.base_modified_gmt)
                    if copy.base_modified_gmt
                    else "never sent"
                )
                + "\n"
                + reading_level_line(copy.text, is_html=copy.text_format == "html")
            )
            answer = idlg.ask_properties(
                self.host.parent,
                self.host.show_modal,
                kind=copy.kind,
                title=copy.title,
                slug=str(props.get("slug", "")),
                status=copy.status,
                excerpt=str(props.get("excerpt", "")),
                categories=[(t.id, t.name) for t in categories],
                tags=[(t.id, t.name) for t in tags],
                chosen_categories=list(props.get("categories", [])),
                chosen_tags=list(props.get("tags", [])),
                comments_open=props.get("comment_status", "open") != "closed",
                sticky=bool(props.get("sticky")),
                facts=facts,
            )
            if answer is None:
                return
            copy.title = answer.title
            copy.status = answer.status
            props.update(
                slug=answer.slug,
                excerpt=answer.excerpt,
                categories=answer.category_ids,
                tags=answer.tag_ids,
                comment_status="open" if answer.comments_open else "closed",
                sticky=answer.sticky,
            )
            if answer.password:
                props["password"] = answer.password
            self.local.save(copy)
            self.host.announce(
                f"Kept with your copy: {len(answer.category_ids)} categories, "
                f"{len(answer.tag_ids)} tags. They go to the site when you next send."
            )
            # The site's own custom fields, when it registers any (9.15).
            custom = getattr(self, "custom_fields_after_properties", None)
            if custom is not None:
                custom(copy, profile)

        if copy.kind == "post":
            self.background(  # type: ignore[attr-defined]
                "loading categories and tags",
                lambda: (wp.list_terms(api, "category"), wp.list_terms(api, "post_tag")),
                show,
            )
        else:
            show(([], []))

    # ------------------------------------------------------------------ #
    # previous versions (5.6)

    def cmd_versions(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> list[wp.Revision]:
            return wp.list_revisions(api, copy.kind, copy.remote_id) if copy.remote_id else []

        self.background(
            "reading the site's history", work, lambda revs: self._show_versions(copy, revs)
        )  # type: ignore[attr-defined]

    def _show_versions(self, copy: lc.WorkingCopy, revisions: list[wp.Revision]) -> None:
        local = self.local.versions(copy.key)
        rows: list[tuple[str, str, str]] = [(v.spoken(), v.title, v.text) for v in local]
        for rev in revisions:
            label = "Autosave on the site" if rev.autosave else "On the site"
            rows.append((
                f"{wp.friendly_date(rev.date_gmt)}, {rev.title or '(untitled)'}, {label}",
                rev.title,
                rev.content,
            ))
        if not rows:
            self.host.announce("There are no earlier versions of this yet.")
            return

        def view(index: int | None) -> object:
            if index is not None:
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title="Version",
                    text=f"{rows[index][1]}\n\n{rows[index][2]}",
                    help_text=(
                        "The full text of this version. Copy a paragraph from it, or close and "
                        "choose Restore."
                    ),
                )
            return None

        def restore(index: int | None) -> object:
            if index is None:
                return None
            self.local.add_version(copy, lc.REASON_BEFORE_RESTORE)
            self.host.replace_text(rows[index][2])
            self.host.announce(
                "Version put in the editor. Nothing was sent; your text before is in Previous "
                "Versions."
            )
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Previous Versions",
            purpose=(
                "Earlier versions of this document, newest first: the ones QUILL kept and the "
                "site's own history."
            ),
            list_label="&Versions:",
            list_help="Each row says when, the title, and why it was kept.",
            rows=[r[0] for r in rows],
            actions=[
                dlg.Action("&View...", "Read the whole version before deciding.", view),
                dlg.Action(
                    "&Restore", "Put this version in the editor. It never publishes.", restore
                ),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # check before publishing (7)

    def cmd_check(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        html, problems = self.to_html(copy)  # type: ignore[attr-defined]
        findings = chk.check_content(
            html, title=copy.title, site_name=profile.name, default_site_name=self._default_name()
        )
        lines = [f.message for f in findings] + problems
        summary = chk.summary_line(findings)
        self.host.announce(summary)
        if not lines:
            return
        excerpts = [f.excerpt for f in findings] + ["" for _ in problems]

        def go(index: int | None) -> object:
            if index is None:
                return None
            needle = excerpts[index]
            text = self.host.current_text()
            offset = text.find(needle) if needle else -1
            if offset >= 0:
                self.host.go_to_offset(offset)
                return dlg.CLOSE
            self.host.announce(
                "QUILL could not find that spot in the text; it may be inside a block line."
            )
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Check Before Publishing",
            purpose=summary,
            list_label="&Things to look at:",
            list_help="Each one says what to look at and why. None of them stops you publishing.",
            rows=lines,
            actions=[
                dlg.Action("&Go to It", "Close this and go to that place in the document.", go)
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # media (6)

    # ------------------------------------------------------------------ #
    # comments (9.8) and categories and tags (9.13)


# --------------------------------------------------------------------------- #
# helpers with no wx in them


def target_status(copy: lc.WorkingCopy, publish: bool, account: wp.Account) -> str:
    """What status a send asks for (5.3, 9.2)."""
    if not publish:
        return (
            copy.status
            if copy.status in {"draft", "pending", "private", "future"} and copy.remote_id
            else "draft"
        )
    if copy.status in {"private", "future"}:
        return copy.status  # a Private or Scheduled item keeps that status
    allowed = account.can_publish_pages if copy.kind == "page" else account.can_publish_posts
    return "publish" if allowed else "pending"


def item_from_copy(copy: lc.WorkingCopy, html: str, *, status: str) -> wp.Item:
    p = copy.properties
    return wp.Item(
        id=copy.remote_id,
        kind=copy.kind,
        title=copy.title,
        content=html,
        status=status,
        slug=str(p.get("slug", "")),
        excerpt=str(p.get("excerpt", "")),
        categories=[int(x) for x in p.get("categories", [])],
        tags=[int(x) for x in p.get("tags", [])],
        featured_media=int(p.get("featured_media", 0) or 0),
        comment_status=str(p.get("comment_status", "")),
        sticky=bool(p.get("sticky", False)),
        password=str(p.get("password", "")),
        parent=int(p.get("parent", 0) or 0),
        template=str(p.get("template", "")),
        format=str(p.get("format", "")),
        meta=dict(p.get("meta") or {}),
    )
