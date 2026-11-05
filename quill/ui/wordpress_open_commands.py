"""Opening pages and posts: from a list, by web address, or a local draft (wordpress.md 5.2).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, split for
size; the same rules as the rest of the WordPress commands apply.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from quill.core.wordpress import local as lc
from quill.core.wordpress import site as wp
from quill.core.wordpress import sites as st
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.ui import wordpress_dialogs as dlg


class WordPressOpenCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    def cmd_open(self) -> None:
        store = self.need_site()
        if store is None:
            return
        profile = self.pick_site(store, "Open Page or Post")
        if profile is None:
            return
        api = self.api(profile)

        def kinds_found() -> list[tuple[str, str]]:
            # A site's own types (events, recipes...) beside Posts and Pages; a
            # site or role that will not list them still gets the two.
            try:
                return wp.list_content_types(api)
            except WordPressApiError:
                return [("post", "Posts"), ("page", "Pages")]

        self.background(
            f"reading what {profile.name} holds",
            kinds_found,
            lambda kinds: self._choose_kind(profile, api, kinds),
        )

    def _choose_kind(self, profile: st.SiteProfile, api: Any, kinds: list[tuple[str, str]]) -> None:
        kind_index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Open Page or Post",
            prompt="&Show:",
            rows=[label for _k, label in kinds],
            help_text=(
                "Posts are dated articles in the blog or news. Pages are lasting pages like About"
                " or Contact. Any other kinds are the site's own, such as events."
            ),
        )
        if kind_index is None:
            return
        kind = kinds[kind_index][0]
        statuses = [s for s, _l in wp.STATUSES]
        self.background(
            f"listing {kinds[kind_index][1].lower()} on {profile.name}",
            lambda: list(wp.list_items(api, kind, statuses=statuses)),
            lambda items: self._show_items(profile, kind, items),
        )

    def _show_items(self, profile: st.SiteProfile, kind: str, items: list[wp.ItemSummary]) -> None:
        if not items:
            self.host.announce(f"{profile.name} has no {kind}s yet.")
            return
        shown = list(items)

        def on_filter(words: str) -> list[str]:
            needle = words.strip().lower()
            shown[:] = [i for i in items if needle in i.title.lower() or needle == i.status]
            return [i.spoken() for i in shown]

        def open_one(index: int | None) -> object:
            if index is None:
                return None
            self.open_item(profile, kind, shown[index].id)
            return dlg.CLOSE

        def trash_one(index: int | None) -> object:
            if index is None:
                return None
            self.trash(profile, kind, shown[index].id, shown[index].title)
            return None

        def restore_one(index: int | None) -> object:
            if index is None:
                return None
            self.restore_listed(profile, kind, shown[index])
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Open from {profile.name}",
            purpose=(
                f"Every {kind} on {profile.name}, newest change first. "
                "Enter opens the selected one."
            ),
            list_label=f"&{kind.title()}s:" if kind in ("post", "page") else "&Items:",
            list_help="Each row says the title, its status, and when it last changed.",
            rows=[i.spoken() for i in items],
            on_enter=open_one,
            actions=[
                dlg.Action("&Open", "Open the selected item in the editor.", open_one),
                dlg.Action(
                    "Move to &Trash...", "Move the selected item to the site's Trash.", trash_one
                ),
                dlg.Action(
                    "&Restore from Trash",
                    "Bring the selected item back from the site's Trash, as a draft.",
                    restore_one,
                ),
            ],
            filter_label="&Find by title or status:",
            filter_help=(
                "Type part of a title, or a status such as draft or trash, and press Enter."
            ),
            on_filter=on_filter,
        )
        window.Destroy()

    def open_item(self, profile: st.SiteProfile, kind: str, item_id: int) -> None:
        existing = self.local.find(profile.id, kind, item_id)
        if existing is not None:
            path = self.local.document_path(existing)
            if path.exists():
                self.host.open_path(path)
                self.watch_documents()
                self.host.announce(
                    f"Opened your working copy of {existing.title or 'this item'}. Compare with "
                    f"Site "
                    "shows what changed on the site since."
                )
                return
        api = self.api(profile)
        self.background(
            f"opening from {profile.name}",
            lambda: wp.load_item(api, kind, item_id),
            lambda item: self._opened(profile, item),
        )

    def _opened(self, profile: st.SiteProfile, item: wp.Item) -> None:
        # An autosave newer than the site's copy is offered first (9.3).
        self.offer_newer_autosave(profile, item, lambda chosen: self._open_as(profile, chosen))

    def _open_as(self, profile: st.SiteProfile, item: wp.Item) -> None:
        from quill.core.wordpress import fences

        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title=f"Open {item.title}",
            prompt="Open &as:",
            rows=[
                "HTML, exactly as the site has it",
                "Markdown, easier to read; anything Markdown cannot show is kept exactly",
            ],
            help_text=(
                "HTML keeps every block exactly. Markdown shows ordinary text plainly and puts "
                "other blocks "
                "on short ::: lines; nothing is lost either way."
            ),
        )
        if choice is None:
            return
        text, text_format, islands = item.content, "html", {}
        if choice == 1:
            text, islands = fences.post_to_markdown(item.content)
            text_format = "markdown"
        copy = lc.WorkingCopy(
            site_id=profile.id,
            kind=item.kind,
            local_id=lc.new_local_id(),
            remote_id=item.id,
            title=item.title,
            text=text,
            text_format=text_format,
            properties=item_properties(item) | {"islands": islands, "date_gmt": item.date_gmt},
            base_modified_gmt=item.modified_gmt,
            link=item.link,
            status=item.status,
        )
        path = self.local.write_document(copy)
        self.local.add_version(copy, lc.REASON_OPENED)
        self.host.open_path(path)
        self.watch_documents()
        self.host.announce(f"Opened {item.title or 'untitled'} from {profile.name}.")

    def cmd_open_by_address(self) -> None:
        clip = self.host.clipboard_text().strip()
        url = clip if clip.startswith(("http://", "https://")) else ""
        if not url:
            typed = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Open by Web Address",
                prompt="Web &address:",
                help_text="Paste or type the address of any page or post on one of your sites.",
            )
            url = (typed or "").strip()
        if not url:
            return
        profile = self.sites().match_url(url)
        if profile is None:
            self.host.announce(
                "That address is not on any of your connected sites. Connect the site first, then"
                " try again."
            )
            self.connect_flow.start(site_url=f"{urlparse(url).scheme}://{urlparse(url).netloc}")
            return
        api = self.api(profile)
        self.background(
            f"finding that page on {profile.name}",
            lambda: find_by_address(api, url),
            lambda found: self._found_by_address(profile, found),
        )

    def _found_by_address(self, profile: st.SiteProfile, found: tuple[str, int] | None) -> None:
        if found is None:
            self.host.announce(
                f"QUILL could not find a page or post at that address on {profile.name}. It may "
                f"be an "
                "archive or a category page, which are not single items."
            )
            return
        self.open_item(profile, found[0], found[1])

    def cmd_open_local_draft(self) -> None:
        drafts = self.local.drafts()
        if not drafts:
            self.host.announce("You have no local WordPress drafts yet.")
            return
        names = {s.id: s.name for s in self.sites().sites}
        rows = [
            f"{d.title or '(untitled)'}, {d.kind}, "
            f"{names.get(d.site_id, 'a site no longer connected')}, "
            f"saved {wp.friendly_date(d.saved_at.split('.', 1)[0])}"
            for d in drafts
        ]
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Open Local Draft",
            prompt="&Drafts:",
            rows=rows,
            help_text="Your WordPress working copies on this computer, newest first.",
        )
        if index is None:
            return
        self.host.open_path(self.local.document_path(drafts[index]))
        self.watch_documents()


def find_by_address(api: WordPressApi, url: str) -> tuple[str, int] | None:
    """The item a web address points at: ``?p=``, ``?page_id=``, ``?<type>=`` or its slug.

    Posts and pages are asked first; the site's own types (an Event at
    ``/event/open-day/`` or ``?event=open-day``) only when neither has it, so
    an ordinary address costs no extra request.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, kind in (("p", "post"), ("page_id", "page"), ("post", "post")):
        if key in query and query[key][0].isdigit():
            return kind, int(query[key][0])
    slug = [part for part in parsed.path.split("/") if part]
    for kind in ("post", "page"):
        if slug and (found := _by_slug(api, kind, slug[-1])) is not None:
            return kind, found
    for type_slug, base, _name in wp.writing_types(api):
        last = query[type_slug][0] if type_slug in query else (slug[-1] if slug else "")
        if last and (found := _by_slug(api, base, last)) is not None:
            return base, found
    return None


def _by_slug(api: WordPressApi, kind: str, slug: str) -> int | None:
    rows = api.get(wp.kind_route(kind), slug=slug, status="any", context="edit", _fields="id")
    return int(rows[0]["id"]) if isinstance(rows, list) and rows else None


def item_properties(item: wp.Item) -> dict[str, Any]:
    return {
        "slug": item.slug,
        "excerpt": item.excerpt,
        "categories": list(item.categories),
        "tags": list(item.tags),
        "featured_media": item.featured_media,
        "comment_status": item.comment_status,
        "sticky": item.sticky,
        "author": item.author,
        "parent": item.parent,
        "template": item.template,
        "format": item.format,
    }
