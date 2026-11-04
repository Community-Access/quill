"""Send This Document to WordPress, Publish to Another Site, and Duplicate (wordpress.md 9.16).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_route_commands.WordPressRouteCommands`), shared by
QUILL and QUILL Lite.

* **Send This Document to WordPress:** the ordinary document in front becomes
  a new draft on a chosen site. Its first heading is the title; its pictures
  on this computer go to the Media Library with the send (the same pending
  uploads Insert Picture uses), and the draft opens as a WordPress document.
* **Publish to Another Site:** the WordPress document in front, copied to
  another connected site as a draft there, pictures uploaded again and
  categories and tags matched by name (missing ones created after asking).
* **Duplicate:** a new draft from any page or post, on the same site or
  another.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import cross_site as xs
from quill.core.wordpress import local as lc
from quill.core.wordpress import site as wp
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_more_commands import item_from_copy

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

KIND_ROWS = ("Post", "Page")


class _Copied:
    def __init__(self, item: wp.Item, pictures: int, skipped_terms: list[str]) -> None:
        self.item = item
        self.pictures = pictures
        self.skipped_terms = skipped_terms


class WordPressRouteCopies:
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # Send This Document to WordPress

    def cmd_send_document(self) -> None:
        path = self.host.current_path()
        if self.local.copy_for_path(path) is not None:
            self.host.announce(
                "This is already a WordPress document. Save Draft to Site sends it to its site."
            )
            return
        text = self.host.current_text()
        if not text.strip():
            self.host.announce("This document is empty, so there is nothing to send.")
            return
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return
        profile = self.pick_site(store, "Send This Document to WordPress")  # type: ignore[attr-defined]
        if profile is None:
            return
        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Send This Document to WordPress",
            prompt="&Make it a:",
            rows=list(KIND_ROWS),
            help_text=(
                "Whether the document becomes a post or a page. Either way it goes as a draft: "
                "nothing is public until you publish it."
            ),
        )
        if choice is None:
            return
        kind = "post" if choice == 0 else "page"
        text_format = xs.document_format(path)
        fallback = path.stem.replace("-", " ").replace("_", " ") if path else "Untitled"
        title, body = xs.title_and_body(text, text_format, fallback)
        pictures = xs.local_pictures(body, path.parent if path else None)
        body = xs.with_file_addresses(body, pictures)
        copy = lc.WorkingCopy(
            site_id=profile.id,
            kind=kind,
            local_id=lc.new_local_id(),
            title=title,
            text=body,
            text_format=text_format,
            properties={"slug": wp.slugify(title), "categories": [], "tags": []},
            pending_uploads=[{"path": str(p.path.resolve()), "alt": p.alt} for p in pictures],
        )
        features = ("writing", "media") if pictures else ("writing",)

        def send(_ready: object) -> None:
            self.host.open_path(self.local.write_document(copy))
            self.watch_documents()  # type: ignore[attr-defined]
            said = f"Sending '{title}' to {profile.name} as a new {kind} draft"
            if pictures:
                said += f"; its {len(pictures)} pictures go to the Media Library"
            self.host.announce(said + ".")
            self.cmd_save_draft()  # type: ignore[attr-defined]

        self.with_route(  # type: ignore[attr-defined]
            profile, features, f"checking {profile.name} takes drafts", lambda _api: None, send
        )

    # ------------------------------------------------------------------ #
    # Publish to Another Site

    def cmd_publish_elsewhere(self) -> None:
        found = self.current(command="Publish to Another Site")  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        target = self._other_site(profile, "Publish to Another Site")
        if target is None:
            return
        html = self.to_html(copy)[0]  # type: ignore[attr-defined]
        item = item_from_copy(copy, html, status="draft")
        self._copy_to(profile, item, target)

    def _other_site(self, profile: st.SiteProfile, title: str) -> st.SiteProfile | None:
        others = [s for s in self.sites().sites if s.id != profile.id]  # type: ignore[attr-defined]
        if not others:
            self.host.announce(
                f"{profile.name} is your only site. Connect another with Connect a Site first."
            )
            return None
        if len(others) == 1:
            return others[0]
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title=title,
            prompt="&Copy to:",
            rows=[s.spoken() for s in others],
            help_text="The site the copy goes to. It arrives there as a draft.",
        )
        return None if index is None else others[index]

    def _copy_to(self, source: st.SiteProfile, item: wp.Item, target: st.SiteProfile) -> None:
        """Copy *item* from *source* to *target* as a draft, asking about missing terms."""
        source_api = self.api(source)  # type: ignore[attr-defined]

        def terms(target_api: Any) -> tuple[Any, list[wp.Term], dict[int, int], list[wp.Term]]:
            wanted: list[wp.Term] = []
            mapping: dict[int, int] = {}
            missing: list[wp.Term] = []
            if item.kind == "post" and (item.categories or item.tags):
                for taxonomy, ids in (("category", item.categories), ("post_tag", item.tags)):
                    have = [t for t in wp.list_terms(source_api, taxonomy) if t.id in ids]
                    found, lost = xs.match_terms(have, wp.list_terms(target_api, taxonomy))
                    wanted += have
                    mapping.update(found)
                    missing += lost
            return target_api, wanted, mapping, missing

        def matched(got: tuple[Any, list[wp.Term], dict[int, int], list[wp.Term]]) -> None:
            target_api, _wanted, mapping, missing = got
            create = bool(missing) and dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Categories and Tags",
                message=(
                    f"{target.name} has no "
                    + ", ".join(t.name for t in missing)
                    + ". Create them there? Cancel copies without them."
                ),
                yes_label="Create Them",
            )

            def work() -> _Copied:
                skipped: list[str] = []
                for term in missing:
                    if create:
                        mapping[term.id] = wp.create_term(target_api, term.taxonomy, term.name).id
                    else:
                        skipped.append(term.name)
                content, uploaded = xs.move_pictures(
                    source_api, target_api, item.content, source.site_url
                )
                draft = xs.as_new_draft(item, same_site=False, terms=mapping)
                draft.content = xs.strip_image_ids(content)
                return _Copied(wp.create_item(target_api, draft), len(uploaded), skipped)

            self.background(f"copying to {target.name}", work, lambda c: self._copied(target, c))  # type: ignore[attr-defined]

        self.with_route(  # type: ignore[attr-defined]
            target, "writing", f"reading {target.name}'s categories and tags", terms, matched
        )

    def _copied(self, target: st.SiteProfile, copied: _Copied) -> None:
        said = f"'{copied.item.title}' is a draft on {target.name}."
        if copied.pictures:
            said += f" {copied.pictures} pictures were uploaded there."
        if copied.skipped_terms:
            said += f" Left without: {', '.join(copied.skipped_terms)}."
        self.host.announce(said)

    # ------------------------------------------------------------------ #
    # Duplicate

    def cmd_duplicate(self) -> None:
        found = self.local.copy_for_path(self.host.current_path())
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return
        profile = store.get(found.site_id) if found is not None else None
        if found is not None and profile is not None and found.remote_id:
            self._duplicate_where(profile, found.kind, found.remote_id, found.title)
            return
        profile = self.pick_site(store, "Duplicate")  # type: ignore[attr-defined]
        if profile is None:
            return
        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Duplicate",
            prompt="&Duplicate a:",
            rows=list(KIND_ROWS),
            help_text="Whether to duplicate a post or a page.",
        )
        if choice is None:
            return
        kind = "post" if choice == 0 else "page"
        statuses = ("publish", "draft", "pending", "future", "private")
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "writing",
            f"listing {kind}s on {profile.name}",
            lambda api: list(wp.list_items(api, kind, statuses=statuses)),
            lambda items: self._pick_duplicate(profile, kind, items),
        )

    def _pick_duplicate(
        self, profile: st.SiteProfile, kind: str, items: list[wp.ItemSummary]
    ) -> None:
        if not items:
            self.host.announce(f"{profile.name} has no {kind}s to duplicate.")
            return
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Duplicate",
            prompt=f"&{kind.title()}:",
            rows=[i.spoken() for i in items],
            help_text=f"The {kind} to make a new draft from.",
        )
        if index is not None:
            self._duplicate_where(profile, kind, items[index].id, items[index].title)

    def _duplicate_where(
        self, profile: st.SiteProfile, kind: str, item_id: int, title: str
    ) -> None:
        sites = self.sites().sites  # type: ignore[attr-defined]
        target = profile
        if len(sites) > 1:
            others = [s for s in sites if s.id != profile.id]
            index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Duplicate",
                prompt="&Where:",
                rows=[f"This site, {profile.name}"] + [s.spoken() for s in others],
                help_text=f"Where the new draft of '{title}' goes.",
            )
            if index is None:
                return
            target = profile if index == 0 else others[index - 1]
        api = self.api(profile)  # type: ignore[attr-defined]
        if target.id != profile.id:
            self.background(  # type: ignore[attr-defined]
                f"reading '{title}' on {profile.name}",
                lambda: wp.load_item(api, kind, item_id),
                lambda item: self._copy_to(profile, item, target),
            )
            return

        def same() -> wp.Item:
            return wp.create_item(
                api, xs.as_new_draft(wp.load_item(api, kind, item_id), same_site=True)
            )

        def done(item: wp.Item) -> None:
            self.host.announce(f"'{item.title}' is a new draft on {profile.name}.")
            opener = getattr(self, "open_item", None)
            if opener is not None:
                opener(profile, item.kind, item.id)

        self.background(f"duplicating '{title}'", same, done)  # type: ignore[attr-defined]
