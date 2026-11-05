"""The WordPress commands, once, for QUILL and QUILL Lite (wordpress.md 4, 5).

Each ``cmd_*`` here is one menu row in File > WordPress, in both editors. The
editor is reached only through :class:`~quill.ui.wordpress_host.WordPressHost`.
Every network call goes through the host's background task runner, so the
window never freezes while a site is slow, and every outcome is spoken in one
sentence that names the site.

A WordPress document is an ordinary file under QUILL's data folder
(:meth:`LocalStore.document_path`), so the editor's own Save is the local save
(5.3) and needs no special case. The working copy beside it carries which site
and item it belongs to, its properties, and the ``modified_gmt`` it was opened
at, which is what conflict protection compares (5.4).
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress import local as lc
from quill.core.wordpress import site as wp
from quill.core.wordpress import sites as st
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui.wordpress_abilities_commands import WordPressAbilitiesCommands
from quill.ui.wordpress_admin_commands import WordPressAdminCommands
from quill.ui.wordpress_api_writing_commands import WordPressApiWritingCommands
from quill.ui.wordpress_block_commands import WordPressBlockCommands
from quill.ui.wordpress_check_commands import WordPressCheckCommands
from quill.ui.wordpress_connect import ConnectFlow
from quill.ui.wordpress_host import WordPressHost
from quill.ui.wordpress_link_commands import WordPressLinkCommands
from quill.ui.wordpress_listen_commands import WordPressListenCommands
from quill.ui.wordpress_look_commands import WordPressLookCommands
from quill.ui.wordpress_media_commands import WordPressMediaCommands
from quill.ui.wordpress_more_commands import WordPressMoreCommands
from quill.ui.wordpress_open_commands import WordPressOpenCommands
from quill.ui.wordpress_page_commands import WordPressPageCommands
from quill.ui.wordpress_pattern_commands import WordPressPatternCommands
from quill.ui.wordpress_picture_commands import WordPressPictureCommands
from quill.ui.wordpress_plugin_commands import WordPressPluginCommands
from quill.ui.wordpress_route_commands import WordPressRouteCommands
from quill.ui.wordpress_shop_commands import WordPressShopCommands
from quill.ui.wordpress_site_commands import WordPressSiteCommands

NOT_WORDPRESS = (
    "This is not a WordPress document. Open one with Open Page or Post, or start one with "
    "New Page or New Post, in the WordPress menu under File."
)


class WordPressCommands(
    WordPressOpenCommands,
    WordPressMoreCommands,
    WordPressSiteCommands,
    WordPressPageCommands,
    WordPressBlockCommands,
    WordPressMediaCommands,
    WordPressPictureCommands,
    WordPressCheckCommands,
    WordPressAdminCommands,
    WordPressListenCommands,
    WordPressLinkCommands,
    WordPressApiWritingCommands,
    WordPressRouteCommands,
    WordPressLookCommands,
    WordPressPatternCommands,
    WordPressPluginCommands,
    WordPressShopCommands,
    WordPressAbilitiesCommands,
):
    def __init__(self, host: WordPressHost, *, data_dir: Any = None, opener: Any = None) -> None:
        self.host = host
        self.local = lc.LocalStore(data_dir)
        self._data_dir = data_dir
        self._opener = opener
        self._last_format = "markdown"
        self.connect_flow = ConnectFlow(self)

    # ------------------------------------------------------------------ #
    # plumbing

    def sites(self) -> st.SiteStore:
        return st.load_sites(self._data_dir)

    def save_sites(self, store: st.SiteStore) -> None:
        st.save_sites(store, self._data_dir)

    def api(self, profile: st.SiteProfile) -> WordPressApi:
        # The first time a site is used in a session, say how many comments
        # wait for it (9.8). Once per site, silent on failure, and off per site.
        self.announce_waiting_once(profile)
        # And how many new form responses wait, on a site with QUILL Accessible Forms (17a.8).
        from quill.ui.forms_site_base import announce_new_responses_once

        announce_new_responses_once(
            self.host, profile, opener=self._opener, data_dir=self._data_dir
        )
        return st.api_for(profile, opener=self._opener)

    def background(self, name: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        def failed(exc: BaseException) -> None:
            self.host.announce(failure_sentence(exc))

        self.host.run_task(f"WordPress: {name}", work, done, failed)

    def current(self, command: str = "") -> tuple[lc.WorkingCopy, st.SiteProfile] | None:
        """The WordPress document in front, or say why there is none.

        *command* names the command for the sentence (wordpress.md 12): "Insert
        Block works in a WordPress page or post. Open one with File, WordPress."
        """
        copy = self.local.copy_for_path(self.host.current_path())
        if copy is None:
            self.host.announce(
                f"{command} works in a WordPress page or post. Open one with File, WordPress."
                if command
                else NOT_WORDPRESS
            )
            return None
        profile = self.sites().get(copy.site_id)
        if profile is None:
            self.host.announce(
                "The site this document belongs to is no longer in your list of sites. Connect it "
                "again with Connect a Site, and the document will find it."
            )
            return None
        return copy, profile

    def need_site(self) -> st.SiteStore | None:
        store = self.sites()
        if store.sites:
            return store
        self.host.announce("Connect a WordPress site first.")
        self.connect_flow.start()
        return None

    def pick_site(self, store: st.SiteStore, title: str) -> st.SiteProfile | None:
        if len(store.sites) == 1:
            return store.sites[0]
        default = store.default
        rows = [s.spoken() for s in store.sites]
        initial = store.sites.index(default) if default in store.sites else 0
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title=title,
            prompt="&Site:",
            rows=rows,
            initial=initial,
            help_text="Choose which of your WordPress sites to use. Your default site is selected.",
        )
        return None if index is None else store.sites[index]

    # ------------------------------------------------------------------ #
    # sites (4.4)

    def cmd_connect(self) -> None:
        self.connect_flow.start()

    def cmd_sites(self) -> None:
        store = self.sites()

        def rows() -> list[str]:
            fresh = self.sites()
            default_id = fresh.default.id if fresh.default else ""
            return [s.spoken() + (", default" if s.id == default_id else "") for s in fresh.sites]

        def chosen(index: int | None) -> st.SiteProfile | None:
            fresh = self.sites()
            return fresh.sites[index] if index is not None and index < len(fresh.sites) else None

        def rename(index: int | None) -> object:
            profile = chosen(index)
            if profile is None:
                return None
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Rename Site",
                prompt="&Name:",
                value=profile.name,
                help_text="What QUILL calls this site in lists and confirmations.",
            )
            if name and name.strip():
                fresh = self.sites()
                fresh.rename(profile.id, name)
                self.save_sites(fresh)
            return rows()

        def remove(index: int | None) -> object:
            profile = chosen(index)
            if profile is None:
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Remove Site",
                message=(
                    f"Remove {profile.name} from QUILL? This forgets the connection and its "
                    f"password on "
                    "this computer. Nothing on the site is changed, and your local drafts are kept."
                ),
                yes_label="Remove",
            ):
                return None
            fresh = self.sites()
            fresh.remove(profile.id)
            self.save_sites(fresh)
            st.forget_secret(profile.id)
            self.host.announce(f"{profile.name} removed from QUILL.")
            return rows()

        def make_default(index: int | None) -> object:
            profile = chosen(index)
            if profile is None:
                return None
            fresh = self.sites()
            fresh.default_id = profile.id
            self.save_sites(fresh)
            self.host.announce(f"{profile.name} is now your default site.")
            return rows()

        def verify(index: int | None) -> object:
            profile = chosen(index)
            if profile is not None:
                self.connect_flow.verify(profile)
            return None

        def add(_index: int | None) -> object:
            return dlg.CLOSE if self.connect_flow.start() is None else rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="WordPress Sites",
            purpose=(
                "Your connected WordPress sites. The default site is where New and Open start; "
                "every "
                "document stays with the site it came from."
            ),
            list_label="&Sites:",
            list_help="Each site's name, your role on it, and where it is.",
            rows=rows(),
            actions=[
                dlg.Action("&Add...", "Connect another WordPress site.", add, needs_row=False),
                dlg.Action("&Rename...", "Change what QUILL calls the selected site.", rename),
                dlg.Action(
                    "&Verify", "Check the selected site still accepts QUILL's sign-in.", verify
                ),
                dlg.Action(
                    "Make &Default", "Use the selected site for New and Open.", make_default
                ),
                dlg.Action("Re&move...", "Forget the selected site on this computer.", remove),
                self.which_password_action(),
            ],
        )
        window.Destroy()
        del store

    def cmd_switch_site(self) -> None:
        store = self.need_site()
        if store is None:
            return
        if len(store.sites) == 1:
            self.host.announce(f"{store.sites[0].name} is your only site.")
            return
        profile = self.pick_site(store, "Switch Site")
        if profile is None:
            return
        store.default_id = profile.id
        self.save_sites(store)
        self.host.announce(f"Default site: {profile.name}.")

    # ------------------------------------------------------------------ #
    # new, open (5.1, 5.2)

    def cmd_new_page(self) -> None:
        self._new("page")

    def cmd_new_post(self) -> None:
        self._new("post")

    def _new(self, kind: str) -> None:
        store = self.need_site()
        if store is None:
            return
        default = store.default or store.sites[0]

        def ask(terms: tuple[list[wp.Term], list[wp.Term]]) -> None:
            categories, tags = terms
            answer = idlg.ask_new_item(
                self.host.parent,
                self.host.show_modal,
                kind_label="Page" if kind == "page" else "Post",
                sites=[s.name for s in store.sites],
                site_index=store.sites.index(default),
                last_format=self._last_format,
                categories=[(t.id, t.name) for t in categories],
                tags=[(t.id, t.name) for t in tags],
            )
            if answer is None:
                return
            profile = store.sites[max(0, answer.site_index)]
            self._last_format = answer.text_format
            copy = lc.WorkingCopy(
                site_id=profile.id,
                kind=kind,
                local_id=lc.new_local_id(),
                title=answer.title,
                text="",
                text_format=answer.text_format,
                properties={
                    "slug": answer.slug,
                    "categories": answer.category_ids if profile.id == default.id else [],
                    "tags": answer.tag_ids if profile.id == default.id else [],
                },
            )
            path = self.local.write_document(copy)
            self.host.open_path(path)
            self.watch_documents()
            self.host.announce(
                f"New {kind} for {profile.name}. Ctrl+S keeps it on this computer; nothing is sent "
                "until you choose Save Draft to Site or Publish."
            )

        if kind != "post":
            ask(([], []))
            return
        api = self.api(default)
        self.background(
            "loading categories and tags",
            lambda: (wp.list_terms(api, "category"), wp.list_terms(api, "post_tag")),
            ask,
        )

    # ------------------------------------------------------------------ #
    # address and trash

    def cmd_open_on_site(self) -> None:
        found = self.current()
        if found is None:
            return
        copy, profile = found
        if not copy.link:
            self.host.announce(
                f"This is not on {profile.name} yet. Save Draft to Site or Publish first."
            )
            return
        self.host.open_in_browser(copy.link)

    def cmd_copy_address(self) -> None:
        found = self.current()
        if found is None:
            return
        copy, profile = found
        if not copy.link:
            self.host.announce(f"This is not on {profile.name} yet, so it has no address.")
            return
        self.host.set_clipboard_text(copy.link)
        if copy.status == "publish":
            self.host.announce("Address copied.")
        else:
            self.host.announce("Draft address copied. It needs a WordPress sign-in to open.")

    def cmd_trash(self) -> None:
        found = self.current()
        if found is None:
            return
        copy, profile = found
        if not copy.remote_id:
            self.host.announce(
                "This is only on this computer. There is nothing on the site to move to the Trash."
            )
            return
        self.trash(profile, copy.kind, copy.remote_id, copy.title)

    def trash(self, profile: st.SiteProfile, kind: str, item_id: int, title: str) -> None:
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Move to Trash",
            message=(
                f"Move '{title or 'untitled'}' on {profile.name} to the Trash? It can be brought "
                f"back: "
                "choose Trash as the status in Open."
            ),
            yes_label="Move to Trash",
        ):
            return
        api = self.api(profile)

        def done(_item: wp.Item) -> None:
            copy = self.local.find(profile.id, kind, item_id)
            if copy is not None:
                copy.status = "trash"
                self.local.save(copy)
            self.host.announce(f"'{title}' moved to the Trash on {profile.name}.")

        self.background("moving to the Trash", lambda: wp.trash_item(api, kind, item_id), done)

    # ------------------------------------------------------------------ #
    # compare (5.4)

    def cmd_compare(self) -> None:
        found = self.current()
        if found is None:
            return
        copy, profile = found
        if not copy.remote_id:
            self.host.announce("This is not on the site yet, so there is nothing to compare with.")
            return
        mine = self.to_html(copy)[0]
        api = self.api(profile)

        def show(item: wp.Item) -> None:
            report = compare_text(item.content, mine, site_name=profile.name)
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Compare with Site",
                text=report,
                help_text=(
                    "The differences between the site's copy and yours. Lines starting 'Site:' "
                    "are the site's; 'Yours:' are yours."
                ),
            )

        self.background(
            "loading the site's copy", lambda: wp.load_item(api, copy.kind, copy.remote_id), show
        )

    # ------------------------------------------------------------------ #

    def to_html(self, copy: lc.WorkingCopy) -> tuple[str, list[str]]:
        """What goes to the site, and any problems turning Markdown into blocks."""
        if copy.text_format == "html":
            return copy.text, []
        from quill.core.wordpress import fences

        result = fences.convert_markdown(copy.text, copy.properties.get("islands") or {})
        return result.html, [f"Line {p.line}: {p.message}" for p in result.problems]


# --------------------------------------------------------------------------- #
# helpers with no wx in them, tested directly


def failure_sentence(exc: BaseException) -> str:
    if isinstance(exc, WordPressApiError):
        return exc.plain
    if isinstance(exc, CodedError):
        return exc.user_message()
    return f"That did not work: {exc}".rstrip(".") + "."


def compare_text(site: str, mine: str, *, site_name: str) -> str:
    diff = list(difflib.ndiff(site.splitlines(), mine.splitlines()))
    lines = []
    for row in diff:
        if row.startswith("- "):
            lines.append(f"Site: {row[2:]}")
        elif row.startswith("+ "):
            lines.append(f"Yours: {row[2:]}")
    if not lines:
        return f"Your copy and the copy on {site_name} are the same."
    head = f"{sum(1 for x in lines if x.startswith('Site:'))} lines only on {site_name}, "
    head += f"{sum(1 for x in lines if x.startswith('Yours:'))} only in yours.\n\n"
    return head + "\n".join(lines)
