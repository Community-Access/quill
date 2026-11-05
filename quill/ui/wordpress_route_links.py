"""Where links go, dead links, and Insert Icon (wordpress.md 9.16).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_route_commands.WordPressRouteCommands`), shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``.

* **Hear Where a Link Goes:** the title and description of the link at the
  caret, read by the site (``url-details``). With no link there, it asks for
  an address, says what is there, and offers to insert it with the page's own
  title as its words -- so a typo in an address is caught before it goes in.
* **Fix Link Text:** every "click here" or "read more" link, with the title
  of the page it goes to offered as its new words.
* **Dead links** in Check This Page (:meth:`dead_links_for`).
* **Insert Icon:** the site's icons by name; each goes in named or decorative.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import icons as ic
from quill.core.wordpress import link_targets as lt
from quill.core.wordpress.api import WordPressApiError
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.core.wordpress import local as lc
    from quill.core.wordpress import sites as st


class WordPressRouteLinks:
    host: Any

    # ------------------------------------------------------------------ #
    # Hear Where a Link Goes

    def cmd_hear_link(self) -> None:
        found = self.current(command="Hear Where a Link Goes")  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        link = lt.link_at(self.host.current_text(), self.host.caret_offset(), copy.text_format)
        if link is not None:
            self.with_route(  # type: ignore[attr-defined]
                profile,
                "url_details",
                f"asking {profile.name} where the link goes",
                lambda api: lt.read_target(api, link.url),
                lambda target: self.host.announce(target.spoken()),
            )
            return
        address = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Hear Where a Link Goes",
            prompt="&Address:",
            help_text=(
                "There is no link at the caret. Type or paste a web address: QUILL asks the site "
                "what page is there and reads its title, then offers to insert the link."
            ),
        )
        if not address or not address.strip():
            return
        url = address.strip()
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "url_details",
            f"asking {profile.name} what is at {url}",
            lambda api: lt.read_target(api, url),
            lambda target: self._offer_link(copy, target),
        )

    def _offer_link(self, copy: lc.WorkingCopy, target: lt.LinkTarget) -> None:
        self.host.announce(target.spoken())
        if not target.reachable:
            return
        words = self.host.selected_text().strip() or target.title or target.url
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Hear Where a Link Goes",
            message=f"{target.spoken()}\n\nInsert a link to it, with the words '{words}'?",
            yes_label="Insert Link",
        ):
            return
        link = lt.DocLink(0, 0, words, target.url, copy.text_format)
        self.host.insert_text(link.with_words(words))
        self.host.announce(f"Link to '{target.title or target.url}' inserted.")

    # ------------------------------------------------------------------ #
    # Fix Link Text

    def cmd_fix_link_text(self) -> None:
        found = self.current(command="Fix Link Text")  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        vague = [
            link
            for link in lt.links_in(self.host.current_text(), copy.text_format)
            if link.vague and link.url.lower().startswith(("http://", "https://"))
        ][: lt.MAX_LINKS]
        if not vague:
            self.host.announce("No 'click here' or 'read more' links in this document.")
            return
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "url_details",
            f"asking {profile.name} where {len(vague)} links go",
            lambda api: [lt.read_target(api, link.url) for link in vague],
            lambda targets: self._show_vague(copy, vague, targets),
        )

    def _show_vague(
        self, copy: lc.WorkingCopy, links: list[lt.DocLink], targets: list[lt.LinkTarget]
    ) -> None:
        pairs = list(zip(links, targets, strict=True))
        fixed: set[int] = set()

        def rows() -> list[str]:
            out = []
            for number, (link, target) in enumerate(pairs):
                if number in fixed:
                    out.append(f"Fixed: now '{target.title}'")
                elif target.reachable and target.title:
                    out.append(f"'{link.words}' goes to '{target.title}'")
                else:
                    out.append(f"'{link.words}' goes to {target.url}, which has no title")
            return out

        def fix(number: int) -> bool:
            link, target = pairs[number]
            if number in fixed or not (target.reachable and target.title):
                return False
            text = self.host.current_text()
            now = next(
                (
                    x
                    for x in lt.links_in(text, copy.text_format)
                    if x.url == link.url and x.words == link.words
                ),
                None,
            )
            if now is None:
                return False
            self.host.replace_text(lt.fixed_text(text, now, target.title))
            fixed.add(number)
            return True

        def use(index: int | None) -> object:
            if index is None:
                return None
            if fix(index):
                self.host.announce(f"The link now says '{pairs[index][1].title}'.")
            else:
                self.host.announce("That link has no page title to use; write its words yourself.")
            return rows()

        def use_all(_index: int | None) -> object:
            count = sum(1 for n in range(len(pairs)) if fix(n))
            self.host.announce(f"{count} links now say where they go.")
            return rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Fix Link Text",
            purpose=(
                "Links whose words do not say where they go, with the title of the page each one "
                "goes to. The site read each page; nothing was sent anywhere else."
            ),
            list_label="&Links:",
            list_help="Each vague link's words, and the title of the page it goes to.",
            rows=rows(),
            actions=[
                dlg.Action(
                    "&Use the Page's Title", "Make the selected link say its page's title.", use
                ),
                dlg.Action(
                    "Use &All Titles",
                    "Make every link here say its page's title.",
                    use_all,
                    needs_row=False,
                ),
            ],
            on_enter=use,
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Dead links, for Check This Page (off the UI thread)

    def dead_links_for(
        self, profile: st.SiteProfile, api: Any, copy: lc.WorkingCopy | None
    ) -> tuple[list[lt.LinkTarget], int] | None:
        """``(dead links, links checked)`` in *copy*, or None when the site cannot say."""
        if copy is None or self.route_why_not(profile, api, "url_details"):  # type: ignore[attr-defined]
            return None
        urls = lt.web_links(lt.links_in(copy.text, copy.text_format))
        try:
            return lt.dead_links(api, urls), len(urls)
        except WordPressApiError:
            return None  # the links could not be checked; the audit still stands

    # ------------------------------------------------------------------ #
    # Insert Icon

    def cmd_insert_icon(self) -> None:
        found = self.current(command="Insert Icon")  # type: ignore[attr-defined]
        if found is None:
            return
        _copy, profile = found
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "icons",
            f"reading {profile.name}'s icons",
            lambda api: (api, ic.list_icons(api)),
            lambda got: self._choose_icon(profile, got[0], got[1]),
        )

    def _choose_icon(self, profile: st.SiteProfile, api: Any, icons: list[ic.Icon]) -> None:
        if not icons:
            self.host.announce(f"{profile.name} has no icons to insert.")
            return
        shown = list(icons)

        def put(index: int | None, decorative: bool) -> object:
            if index is None:
                return None
            icon = shown[index]
            label = ""
            if not decorative:
                answer = dlg.ask_text(
                    self.host.parent,
                    self.host.show_modal,
                    title="Icon Label",
                    prompt="&Label:",
                    value=icon.label or icon.name,
                    help_text=(
                        "What the icon means, said by screen readers in its place: for example "
                        "'Phone us'. An icon that only decorates should be inserted as decorative."
                    ),
                )
                if answer is None:
                    return None
                label = answer.strip()
                if not label:
                    self.host.announce(
                        "An icon needs a label that says what it means, or to be inserted as "
                        "decorative. Nothing was inserted."
                    )
                    return None
            try:
                markup = ic.icon_markup(icon, label=label, decorative=decorative)
            except ic.IconLabelError as exc:
                self.host.announce(exc.user_message())
                return None
            self.host.insert_text("\n" + markup + "\n")
            self.host.announce(
                f"Decorative icon {icon.label or icon.name} inserted; screen readers skip it."
                if decorative
                else f"Icon inserted, labelled '{label}'."
            )
            return dlg.CLOSE

        def search(words: str) -> list[str]:
            wanted = words.strip().casefold()
            shown[:] = [
                i
                for i in icons
                if not wanted or wanted in (i.label + " " + i.name + " " + i.collection).casefold()
            ]
            return [i.spoken() for i in shown]

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Insert Icon",
            purpose=(
                f"{profile.name}'s icons by name. Each goes in with a label that says what it "
                "means, or marked decorative so screen readers skip it; never unnamed."
            ),
            list_label="&Icons:",
            list_help="Each icon's name and the collection it comes from.",
            rows=[i.spoken() for i in shown],
            actions=[
                dlg.Action(
                    "Insert with a &Label...",
                    "Insert the icon with words that say what it means.",
                    lambda index: put(index, False),
                ),
                dlg.Action(
                    "Insert as &Decorative",
                    "Insert the icon so screen readers skip it; for icons that only decorate.",
                    lambda index: put(index, True),
                ),
            ],
            filter_label="&Find:",
            filter_help="Type part of an icon's name and press Enter to narrow the list.",
            on_filter=search,
            on_enter=lambda index: put(index, False),
        )
        window.Destroy()
        del api
