"""Previous Looks, and Menu History (wordpress.md 9.16).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_route_commands.WordPressRouteCommands`), shared by
QUILL and QUILL Lite.

* **Previous Looks:** the site's earlier styles, dated, each with its palette;
  Go Back to This Look makes one current again (and is itself kept, so it can
  be undone the same way).
* **Menu History:** a Navigation block's own revisions, or, for a classic menu,
  the snapshots QUILL keeps each time the Menus window reads it
  (:meth:`remember_menus`). Bring Back adds the items a later change removed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import looks_history as lh
from quill.core.wordpress import navigation as nav
from quill.core.wordpress import site as wp
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class WordPressRouteHistory:
    host: Any
    _data_dir: Any

    # ------------------------------------------------------------------ #
    # Previous Looks

    def cmd_previous_looks(self) -> None:
        profile = self.route_site("Previous Looks")  # type: ignore[attr-defined]
        if profile is None:
            return

        def work(api: Any) -> tuple[Any, int, list[lh.Look]]:
            styles = lh.styles_id(api)
            return api, styles, (lh.list_looks(api, styles) if styles else [])

        self.with_route(  # type: ignore[attr-defined]
            profile,
            "style_revisions",
            f"reading {profile.name}'s earlier looks",
            work,
            lambda got: self._show_looks(profile, *got),
        )

    def _show_looks(
        self, profile: st.SiteProfile, api: Any, styles: int, looks: list[lh.Look]
    ) -> None:
        if not styles:
            self.host.announce(
                f"{profile.name}'s theme has no site styles of its own, so it has no earlier looks."
            )
            return
        if not looks:
            self.host.announce(f"{profile.name}'s styles have not been changed yet.")
            return

        def palette(index: int | None) -> object:
            if index is not None:
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title="Palette Report",
                    text=looks[index].palette_report(),
                    help_text="The colours this earlier look used, by name and value.",
                )
            return None

        def go_back(index: int | None) -> object:
            if index is None:
                return None
            look = looks[index]
            when = wp.friendly_date(look.date_gmt)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Go Back to This Look",
                message=(
                    f"Make the look from {when} {profile.name}'s current look? The look it has "
                    "now is kept, so Previous Looks can bring it back."
                ),
                yes_label="Go Back",
            ):
                return None
            self.background(  # type: ignore[attr-defined]
                f"going back to the look from {when}",
                lambda: lh.restore_look(api, styles, look),
                lambda _r: self.host.announce(f"{profile.name} has the look from {when} again."),
            )
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Previous Looks",
            purpose=(
                f"{profile.name}'s earlier site styles, newest first, like Previous Versions "
                "for a page."
            ),
            list_label="&Looks:",
            list_help="When each look was saved, and how many colours it named.",
            rows=[look.spoken() for look in looks],
            details=lambda index: looks[index].palette_report(),
            actions=[
                dlg.Action("&Palette Report...", "This look's colours.", palette),
                dlg.Action(
                    "&Go Back to This Look...", "Make this look the site's current one.", go_back
                ),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Menu History

    def remember_menus(self, profile: st.SiteProfile, menus: list[nav.Menu]) -> None:
        """Keep each classic menu as the Menus window read it (the Menus window calls this)."""
        store = lh.MenuSnapshots(self._data_dir)
        for menu in menus:
            store.remember(profile.id, menu, lc.now_stamp())

    def cmd_menu_history(self) -> None:
        profile = self.route_site("Menu History")  # type: ignore[attr-defined]
        if profile is None:
            return
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "menus",
            f"reading menus on {profile.name}",
            lambda api: (api, nav.load_menus(api)),
            lambda got: self._pick_menu_history(profile, got[0], got[1]),
        )

    def _pick_menu_history(self, profile: st.SiteProfile, api: Any, menus: list[nav.Menu]) -> None:
        if not menus:
            self.host.announce(f"{profile.name} has no menus or Navigation blocks.")
            return
        self.remember_menus(profile, menus)
        index = 0
        if len(menus) > 1:
            chosen = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Menu History",
                prompt="&Menu:",
                rows=[m.spoken() for m in menus],
                help_text="The menu or Navigation block whose history to see.",
            )
            if chosen is None:
                return
            index = chosen
        menu = menus[index]
        if menu.source == "navigation":
            self.background(  # type: ignore[attr-defined]
                f"reading the history of {menu.name}",
                lambda: lh.navigation_versions(api, menu),
                lambda versions: self._show_menu_history(profile, api, menu, versions),
            )
            return
        versions = lh.MenuSnapshots(self._data_dir).versions(profile.id, menu)
        self._show_menu_history(profile, api, menu, versions[1:])

    def _show_menu_history(
        self,
        profile: st.SiteProfile,
        api: Any,
        menu: nav.Menu,
        versions: list[lh.MenuVersion],
    ) -> None:
        if not versions:
            self.host.announce(
                f"{menu.name} has no earlier versions yet. QUILL keeps one each time the Menus "
                "window reads a menu, so a change made after this can be undone."
                if menu.source == "classic"
                else f"{menu.name} has no earlier versions on {profile.name}."
            )
            return

        def details(index: int) -> str:
            version = versions[index]
            gone = version.missing_from(menu)
            lines = [f"{len(version.nodes)} items then:"] + [f"- {n[0]}" for n in version.nodes]
            if gone:
                lines += ["", "Since removed:"] + [f"- {n[0]}" for n in gone]
            return "\n".join(lines)

        def bring_back(index: int | None) -> object:
            if index is None:
                return None
            version = versions[index]
            gone = version.missing_from(menu)
            if not gone:
                self.host.announce(f"Every item from then is still in {menu.name}.")
                return None
            names = ", ".join(n[0] for n in gone)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Bring Back Menu Items",
                message=f"Add {names} back to {menu.name} on {profile.name}, at the end?",
                yes_label="Bring Back",
            ):
                return None
            self.background(  # type: ignore[attr-defined]
                f"bringing items back to {menu.name}",
                lambda: lh.bring_back(api, menu, version),
                lambda added: self.host.announce(
                    f"{len(added)} items back in {menu.name}, at the end."
                ),
            )
            return dlg.CLOSE

        def restore(index: int | None) -> object:
            if index is None:
                return None
            version = versions[index]
            when = wp.friendly_date(version.stamp)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Restore This Version",
                message=(
                    f"Make {menu.name} on {profile.name} exactly as it was on {when}? Its "
                    "current version is kept in this history."
                ),
                yes_label="Restore",
            ):
                return None
            self.background(  # type: ignore[attr-defined]
                f"restoring {menu.name}",
                lambda: lh.restore_navigation(api, menu, version),
                lambda _r: self.host.announce(f"{menu.name} is as it was on {when}."),
            )
            return dlg.CLOSE

        actions = [
            dlg.Action(
                "&Bring Back Removed Items...",
                "Add back the items this version had that the menu has lost.",
                bring_back,
            )
        ]
        if menu.source == "navigation":
            actions.append(
                dlg.Action(
                    "&Restore This Version...", "Make the menu exactly as it was then.", restore
                )
            )
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Menu History",
            purpose=f"Earlier versions of {menu.name}, newest first.",
            list_label="&Versions:",
            list_help="When each version was kept, how many items it had, and what has gone since.",
            rows=[v.spoken(menu) for v in versions],
            details=details,
            actions=actions,
        )
        window.Destroy()
