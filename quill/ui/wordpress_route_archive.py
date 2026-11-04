"""Download My Writing, Send a Folder as Drafts, Coming Up, What Changed (wordpress.md 9.16).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_route_commands.WordPressRouteCommands`), shared by
QUILL and QUILL Lite.

* **Download My Writing:** every page and post of a site to a folder of
  Markdown files with their pictures and a contents page; runs in the
  background and resumes where it stopped.
* **Send a Folder as Drafts:** a folder of Markdown, text or web-page files
  becomes drafts, each checked first, after one confirmation that gives the
  count.
* **Coming Up** and **What Changed on My Sites:** one list across every
  connected site, read on request.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import across_sites as ac
from quill.core.wordpress import writing_archive as wa
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_route_dialogs as rdlg

if TYPE_CHECKING:
    from pathlib import Path

    from quill.core.wordpress import sites as st


class WordPressRouteArchive:
    host: Any
    _data_dir: Any

    # ------------------------------------------------------------------ #
    # Download My Writing

    def cmd_download_writing(self) -> None:
        profile = self.route_site("Download My Writing")  # type: ignore[attr-defined]
        if profile is None:
            return
        folder = rdlg.pick_folder(
            self.host.parent,
            self.host.show_modal,
            title=f"Download My Writing from {profile.name}",
            must_exist=False,
        )
        if folder is None:
            return
        resuming = (folder / wa.MANIFEST).exists()
        self.host.announce(
            f"{'Carrying on saving' if resuming else 'Saving'} your writing on {profile.name} to "
            f"{folder.name}, in the background. QUILL says when it is done."
        )
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "writing",
            f"saving your writing on {profile.name}",
            lambda api: wa.download_writing(api, folder, profile.site_url),
            lambda result: self.host.announce(wa.archive_sentence(profile.name, folder, result)),
        )

    # ------------------------------------------------------------------ #
    # Send a Folder as Drafts

    def cmd_send_folder(self) -> None:
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return
        profile = self.pick_site(store, "Send a Folder as Drafts")  # type: ignore[attr-defined]
        if profile is None:
            return
        folder = rdlg.pick_folder(
            self.host.parent, self.host.show_modal, title="Send a Folder as Drafts"
        )
        if folder is None:
            return
        files = wa.read_folder(folder, site_name=profile.name)
        if not files:
            self.host.announce(
                f"{folder.name} has no Markdown, text or web-page files to send. Nothing was sent."
            )
            return
        self._confirm_folder(profile, folder, files)

    def _confirm_folder(
        self, profile: st.SiteProfile, folder: Path, files: list[wa.FolderFile]
    ) -> None:
        lines = [
            f"- {f.path.name}: {f.title}"
            + (f" ({len(f.findings)} things to look at)" if f.findings else "")
            for f in files[:12]
        ]
        if len(files) > 12:
            lines.append(f"- and {len(files) - 12} more")
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Send a Folder as Drafts",
            message=wa.folder_sentence(files, profile.name) + "\n\n" + "\n".join(lines),
            yes_label=f"Send {len(files)} Drafts",
        ):
            return

        def sent(result: tuple[list[Any], list[str]]) -> None:
            drafts, failed = result
            said = f"{len(drafts)} drafts from {folder.name} are on {profile.name}."
            if failed:
                said += f" {len(failed)} could not be sent: {failed[0]}"
            self.host.announce(said)

        self.with_route(  # type: ignore[attr-defined]
            profile,
            "writing",
            f"sending {len(files)} drafts to {profile.name}",
            lambda api: wa.send_folder(api, files),
            sent,
        )

    # ------------------------------------------------------------------ #
    # Across every site

    def _every_site(self) -> list[ac.SiteCall] | None:
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        return [
            (s.id, s.name, lambda s=s: self.api(s))  # type: ignore[attr-defined,misc]
            for s in store.sites
        ]

    def cmd_coming_up(self) -> None:
        sites = self._every_site()
        if sites is None:
            return

        def show(result: tuple[list[ac.Scheduled], list[str]]) -> None:
            items, failed = result
            self.host.announce(ac.coming_up_sentence(items, failed, len(sites)))
            if not items:
                return

            def open_it(index: int | None) -> object:
                if index is None:
                    return None
                item = items[index]
                profile = self.sites().get(  # type: ignore[attr-defined]
                    next(s[0] for s in sites if s[1] == item.site)
                )
                opener = getattr(self, "open_item", None)
                if profile is not None and opener is not None:
                    self.then_next(lambda: opener(profile, item.kind, item.id))  # type: ignore[attr-defined]
                return dlg.CLOSE

            window = dlg.show_list_window(
                self.host.parent,
                self.host.show_modal,
                title="Coming Up",
                purpose="Everything scheduled on your sites, soonest first.",
                list_label="&Scheduled:",
                list_help="When each item goes out, its title, and which site it is on.",
                rows=[i.spoken() for i in items] + [f"Did not answer: {f}" for f in failed],
                actions=[dlg.Action("&Open", "Open the selected item to edit it.", open_it)],
                on_enter=open_it,
            )
            window.Destroy()

        self.background(  # type: ignore[attr-defined]
            "reading what is scheduled on your sites", lambda: ac.coming_up(sites), show
        )

    def cmd_what_changed(self) -> None:
        sites = self._every_site()
        if sites is None:
            return
        looked = ac.LastLooked(self._data_dir)
        now = ac.utc_now()

        def show(result: tuple[list[ac.Change], list[str]]) -> None:
            changes, failed = result
            looked.mark([s[0] for s in sites if s[1] not in {f.split(":")[0] for f in failed}], now)
            self.host.announce(ac.what_changed_sentence(changes, failed, len(sites)))
            if not changes and not failed:
                return

            def browse(index: int | None) -> object:
                if index is not None and index < len(changes) and changes[index].link:
                    self.host.open_in_browser(changes[index].link)
                elif index is not None:
                    self.host.announce("That one has no page to open.")
                return None

            window = dlg.show_list_window(
                self.host.parent,
                self.host.show_modal,
                title="What Changed on My Sites",
                purpose="What is new on your sites since you last looked here.",
                list_label="&Changes:",
                list_help="Each site's new comments, posts others published, and health warnings.",
                rows=[c.spoken() for c in changes] + [f"Did not answer: {f}" for f in failed],
                actions=[
                    dlg.Action("Open in &Browser", "Open the selected post on its site.", browse)
                ],
            )
            window.Destroy()

        self.background(  # type: ignore[attr-defined]
            "reading what changed on your sites", lambda: ac.what_changed(sites, looked, now), show
        )
