"""Menus, Navigation and Widgets (wordpress.md 9.9): the drag-and-drop parts, as lists.

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, gathered
by :class:`~quill.ui.wordpress_admin_commands.WordPressAdminCommands`.

Menus and Navigation blocks share one window: :mod:`quill.core.wordpress.navigation`
loads either into the same tree and writes each back its own way. Each row
reads "Sessions, page, level 1, 3 of 7".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import navigation as nav
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_structure as ss
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class _MenuData:
    """What the Menus window needs, read in one background task."""

    def __init__(self, api: Any, page_id: int) -> None:
        self.menus = nav.load_menus(api)
        self.locations = nav.load_locations(api)
        self.pages = _titles(api, "wp/v2/pages")
        self.posts = _titles(api, "wp/v2/posts")
        self.categories = [(t.id, t.name) for t in wp.list_terms(api, "category")]
        self.page_title = dict(self.pages).get(page_id, "") if page_id else ""


def _titles(api: Any, route: str) -> list[tuple[int, str]]:
    params: dict[str, object] = {"status": "publish", "_fields": "id,title"}
    return [
        (int(r.get("id", 0)), wp.rendered(r.get("title")) or "(untitled)")
        for r in api.iter_collection(route, params)
    ]


def _holder(location: nav.Location, menu: nav.Menu) -> str:
    if location.menu == menu.id:
        return "this menu"
    return "another menu" if location.menu else "empty"


class WordPressMenuCommands(WordPressAdminBase):
    # ------------------------------------------------------------------ #
    # Menus and Navigation

    def cmd_menus(self, page_id: int = 0, *, menu_id: int = 0) -> None:
        """The Menus window. With *page_id*, first add that page to a menu the person picks."""
        profile = self.admin_site("Menus")
        if profile is None:
            return
        self.admin_load(
            profile,
            f"reading menus on {profile.name}",
            "menus",
            lambda api, _account: _MenuData(api, page_id),
            lambda api, _account, data: self._menus_ready(profile, api, data, page_id, menu_id),
        )

    def _menus_ready(
        self, profile: st.SiteProfile, api: Any, data: _MenuData, page_id: int, menu_id: int
    ) -> None:
        if not data.menus:
            self.host.announce(
                f"{profile.name} has no menus or Navigation blocks yet. Make the first one in "
                "the site's editor; QUILL then lists and changes it here."
            )
            return
        # Menu History keeps each classic menu as read here, so a change can be undone (9.16).
        remember = getattr(self, "remember_menus", None)
        if remember is not None:
            remember(profile, data.menus)
        menu = next((m for m in data.menus if m.id == menu_id), None)
        if menu is None and len(data.menus) == 1:
            menu = data.menus[0]
        if menu is None:
            title = data.page_title or "this page"
            index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Add to Menu" if page_id else "Menus",
                prompt="&Menu:",
                rows=[m.spoken() for m in data.menus],
                help_text=(
                    f"Which menu to add {title} to."
                    if page_id
                    else "Which menu or Navigation block to open."
                ),
            )
            if index is None:
                return
            menu = data.menus[index]
        if page_id:
            node = nav.MenuNode(data.page_title or f"Page {page_id}", "page", page_id)
            self.site_job(
                "adding to the menu",
                lambda: nav.add_item(api, menu, node),
                lambda _n: f"{node.title} added to {menu.name} on {profile.name}, at the end.",
            )
        self._show_menu(profile, api, data, menu)

    def _show_menu(
        self, profile: st.SiteProfile, api: Any, data: _MenuData, menu: nav.Menu
    ) -> None:

        def rows() -> list[str]:
            return [r.spoken() for r in nav.rows(menu.nodes)]

        def at(index: int | None) -> nav.MenuNode | None:
            found = nav.rows(menu.nodes)
            return found[index].node if index is not None and index < len(found) else None

        def details(index: int) -> str:
            node = at(index)
            if node is None:
                return ""
            if node.kind == "other":
                return (
                    f"{node.title}. QUILL keeps this block as it is; change it in the site editor."
                )
            where = node.url or (f"{node.kind} {node.object_id}" if node.object_id else "")
            return f"Name: {node.title}\nKind: {nav.KIND_NAMES.get(node.kind)}\nGoes to: {where}"

        def save(said: str) -> None:
            self.site_job(f"saving {menu.name}", lambda: nav.save_menu(api, menu), lambda _n: said)

        def adder(kind: str, choices: list[tuple[int, str]]) -> Any:
            def run(_index: int | None) -> object:
                if not choices:
                    self.host.announce(f"{profile.name} has no published {kind}s to add.")
                    return None
                picked = dlg.ask_choice(
                    self.host.parent,
                    self.host.show_modal,
                    title=f"Add {kind.title()} to {menu.name}",
                    prompt=f"&{kind.title()}:",
                    rows=[name for _i, name in choices],
                    help_text=f"The {kind} to add. It goes at the end; move it after.",
                )
                if picked is None:
                    return None
                object_id, name = choices[picked]
                node = nav.MenuNode(name, kind, object_id)
                self.site_job(
                    f"adding to {menu.name}",
                    lambda: nav.add_item(api, menu, node),
                    lambda _n: f"{name} added to {menu.name}, at the end.",
                )
                return rows()

            return run

        def add_link(_index: int | None) -> object:
            url = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Add Link to {menu.name}",
                prompt="&Address:",
                help_text="The web address the menu item goes to, for example https://example.org.",
            )
            if not url or not url.strip():
                return None
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Add Link to {menu.name}",
                prompt="&Name:",
                help_text="What the menu item says. Every item needs a name visitors can hear.",
            )
            if not name or not name.strip():
                self.host.announce("A menu item needs a name, so nothing was added.")
                return None
            node = nav.MenuNode(name.strip(), "link", url=url.strip())
            self.site_job(
                f"adding to {menu.name}",
                lambda: nav.add_item(api, menu, node),
                lambda _n: f"{node.title} added to {menu.name}, at the end.",
            )
            return rows()

        def rename(index: int | None) -> object:
            node = at(index)
            if node is None or node.kind == "other":
                return None
            name = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Rename Menu Item",
                prompt="&Name:",
                value=node.title,
                help_text="What the menu item says to visitors.",
            )
            if not name or not name.strip() or name.strip() == node.title:
                return None
            new = name.strip()
            self.site_job(
                f"saving {menu.name}",
                lambda: nav.rename_item(api, menu, node, new),
                lambda _n: f"Renamed to {new}.",
            )
            node.title = new
            return rows()

        def mover(how: Any) -> Any:
            def run(index: int | None) -> object:
                node = at(index)
                if node is None:
                    return None
                said = how(menu.nodes, node)
                if not said:
                    self.host.announce(f"{node.title} cannot move that way.")
                    return None
                save(said)
                return rows()

            return run

        def remove(index: int | None) -> object:
            node = at(index)
            if node is None:
                return None
            under = (
                f" Its {len(node.children)} items move up into its place." if node.children else ""
            )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Remove from Menu",
                message=(
                    f"Remove {node.title} from {menu.name} on {profile.name}? The page or link "
                    f"itself is not touched.{under}"
                ),
                yes_label=f"Remove {node.title}",
            ):
                return None
            self.site_job(
                f"saving {menu.name}",
                lambda: nav.remove_item(api, menu, node),
                lambda _n: f"{node.title} removed from {menu.name}.",
            )
            return rows()

        def locations(_index: int | None) -> object:
            if not data.locations:
                self.host.announce(f"The theme on {profile.name} names no menu locations.")
                return None
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=f"Locations for {menu.name}",
                prompt="&Location:",
                rows=[f"{loc.name}, {_holder(loc, menu)}" for loc in data.locations],
                help_text=(
                    "Where the theme shows this menu. Choosing a location this menu is in takes "
                    "it out; choosing another puts it there."
                ),
            )
            if picked is None:
                return None
            chosen = data.locations[picked]
            slugs = [loc.slug for loc in data.locations if loc.menu == menu.id]
            leaving = chosen.slug in slugs
            slugs = [s for s in slugs if s != chosen.slug] if leaving else [*slugs, chosen.slug]
            data.locations[picked] = nav.Location(
                chosen.slug, chosen.name, 0 if leaving else menu.id
            )
            self.site_job(
                "setting menu locations",
                lambda: nav.set_locations(api, menu, slugs),
                lambda _r: (
                    f"{menu.name} {'taken out of' if leaving else 'now shows in'} {chosen.name}."
                ),
            )
            return None

        def check(_index: int | None) -> object:
            def done(statuses: dict[int, str]) -> None:
                found = nav.problems(menu, statuses)
                if not found:
                    self.host.announce(f"{menu.name}: every item has a name and goes somewhere.")
                    return
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title=f"Check {menu.name}",
                    text=f"{len(found)} problems in {menu.name}:\n\n" + "\n".join(found),
                    help_text="Menu items visitors cannot use: no name, or a dead link.",
                )

            self.background(  # type: ignore[attr-defined]
                f"checking {menu.name}", lambda: nav.target_statuses(api, menu), done
            )
            return None

        def other_menu(_index: int | None) -> object:
            others = [m for m in data.menus if m is not menu]
            if not others:
                self.host.announce(f"{menu.name} is the only menu on {profile.name}.")
                return None
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Other Menu",
                prompt="&Menu:",
                rows=[m.spoken() for m in others],
                help_text="Which menu or Navigation block to open instead.",
            )
            if picked is None:
                return None
            chosen = others[picked]
            self.after_close(lambda: self._show_menu(profile, api, data, chosen))
            return dlg.CLOSE

        actions = [
            dlg.Action(
                "Add &Page...",
                "Add a page at the end of the menu.",
                adder("page", data.pages),
                needs_row=False,
            ),
            dlg.Action(
                "Add P&ost...",
                "Add a post at the end of the menu.",
                adder("post", data.posts),
                needs_row=False,
            ),
            dlg.Action(
                "Add &Category...",
                "Add a category's archive at the end of the menu.",
                adder("category", data.categories),
                needs_row=False,
            ),
            dlg.Action("Add &Link...", "Add a link to any web address.", add_link, needs_row=False),
            dlg.Action("&Rename...", "Change what the selected item says.", rename),
            dlg.Action(
                "Move &Up", "Move the selected item before the one above it.", mover(nav.move_up)
            ),
            dlg.Action(
                "Move Do&wn", "Move the selected item after the one below it.", mover(nav.move_down)
            ),
            dlg.Action(
                "Move &In", "Put the selected item under the one above it.", mover(nav.move_in)
            ),
            dlg.Action("Move Ou&t", "Move the selected item out one level.", mover(nav.move_out)),
            dlg.Action("Re&move...", "Take the selected item out of the menu.", remove),
            dlg.Action(
                "C&heck Menu",
                "Find items with no name, and links to drafts or deleted pages.",
                check,
                needs_row=False,
            ),
            dlg.Action(
                "Other M&enu...", "Open another menu on this site.", other_menu, needs_row=False
            ),
        ]
        if menu.source == "classic":
            actions.insert(
                10,
                dlg.Action(
                    "Locatio&ns...",
                    "Choose where the theme shows this menu, such as the header or footer.",
                    locations,
                    needs_row=False,
                ),
            )
        kind = "menu" if menu.source == "classic" else "Navigation block"
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"{menu.name}, {profile.name}",
            purpose=(
                f"The {kind} {menu.name} on {profile.name}, as a tree. Items under another "
                "item are a level deeper."
            ),
            list_label="Menu item&s:",
            list_help=(
                "Each item's name, what it goes to, its level, and its place among its neighbours."
            ),
            rows=rows(),
            details=details,
            actions=actions,
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Widgets (classic themes)

    def cmd_widgets(self) -> None:
        profile = self.admin_site("Widgets")
        if profile is None:
            return

        def work(api: Any, _account: wp.Account) -> tuple[list[ss.Sidebar], list[ss.Widget]]:
            sidebars = ss.list_sidebars(api)
            widgets = [w for s in sidebars for w in ss.list_widgets(api, s.id)]
            return sidebars, widgets

        def show(api: Any, _account: wp.Account, data: Any) -> None:
            sidebars, widgets = data
            if not sidebars:
                self.host.announce(
                    f"{profile.name} has no widget areas. A block theme keeps its header and "
                    "footer in templates instead: see Template Outline."
                )
                return
            self._show_widgets(profile, api, sidebars, widgets)

        self.admin_load(profile, f"reading widgets on {profile.name}", "widgets", work, show)

    def _show_widgets(
        self,
        profile: st.SiteProfile,
        api: Any,
        sidebars: list[ss.Sidebar],
        widgets: list[ss.Widget],
    ) -> None:
        live = list(widgets)
        names = {s.id: s.name for s in sidebars}

        def ordered() -> list[ss.Widget]:
            return [w for s in sidebars for w in live if w.sidebar == s.id]

        def rows() -> list[str]:
            out = []
            for w in ordered():
                same = [x for x in live if x.sidebar == w.sidebar]
                out.append(
                    f"{names.get(w.sidebar, w.sidebar)}: {w.spoken()}, "
                    f"{same.index(w) + 1} of {len(same)}"
                )
            return out

        def at(index: int | None) -> ss.Widget | None:
            items = ordered()
            return items[index] if index is not None and index < len(items) else None

        def choose_area(title: str, exclude: str = "") -> ss.Sidebar | None:
            areas = [s for s in sidebars if s.id != exclude]
            if len(areas) == 1:
                return areas[0]
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=title,
                prompt="&Widget area:",
                rows=[f"{s.name}: {s.description}" if s.description else s.name for s in areas],
                help_text="The widget areas the theme offers, such as a sidebar or the footer.",
            )
            return None if picked is None else areas[picked]

        def add(_index: int | None) -> object:
            area = choose_area("Add Text Widget")
            if area is None:
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Add Text to {area.name}",
                prompt="&Text:",
                multiline=True,
                help_text="The words for a new paragraph widget at the end of this area.",
            )
            if not text or not text.strip():
                return None

            def done(widget: ss.Widget) -> None:
                live.append(widget)
                self.host.announce(f"Text widget added to {area.name} on {profile.name}.")

            self.background(  # type: ignore[attr-defined]
                "adding a widget",
                lambda: ss.add_block_widget(api, area.id, ss.paragraph_block(text.strip())),
                done,
            )
            return None

        def edit(index: int | None) -> object:
            widget = at(index)
            if widget is None:
                return None
            if not widget.is_block:
                self.host.announce(
                    "This is a classic widget; its settings are only in the dashboard. "
                    "Open in Dashboard takes you there."
                )
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Edit Widget",
                prompt="&Blocks:",
                value=widget.content,
                multiline=True,
                help_text="The widget's blocks, as the site keeps them. Keep the block comments.",
            )
            if text is None or text == widget.content:
                return None
            self.site_job(
                "saving a widget",
                lambda: ss.edit_block_widget(api, widget, text),
                lambda _w: f"Widget saved in {names.get(widget.sidebar)}.",
            )
            live[live.index(widget)] = ss.Widget(
                widget.id, widget.id_base, widget.sidebar, text, widget.rendered
            )
            return rows()

        def move_to(index: int | None) -> object:
            widget = at(index)
            if widget is None or len(sidebars) < 2:
                return None
            area = choose_area("Move Widget To", exclude=widget.sidebar)
            if area is None:
                return None
            self.site_job(
                "moving a widget",
                lambda: ss.move_widget(api, widget, area.id),
                lambda _w: f"Widget moved to {area.name}.",
            )
            live[live.index(widget)] = ss.Widget(
                widget.id, widget.id_base, area.id, widget.content, widget.rendered
            )
            return rows()

        def remove(index: int | None) -> object:
            widget = at(index)
            if widget is None:
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Remove Widget",
                message=(
                    f"Take {widget.spoken()} out of {names.get(widget.sidebar)} on "
                    f"{profile.name}? It goes to Inactive Widgets, where the dashboard can "
                    "bring it back."
                ),
                yes_label="Remove Widget",
            ):
                return None
            self.site_job(
                "removing a widget",
                lambda: ss.remove_widget(api, widget),
                lambda _r: f"Widget removed from {names.get(widget.sidebar)}.",
            )
            live.remove(widget)
            return rows()

        def dashboard(_index: int | None) -> object:
            self.host.open_in_browser(profile.site_url.rstrip("/") + "/wp-admin/widgets.php")
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Widgets, {profile.name}",
            purpose=f"Every widget on {profile.name}, by the area the theme shows it in.",
            list_label="&Widgets:",
            list_help="Each row gives the area, what the widget is, and its place in that area.",
            rows=rows(),
            details=lambda i: wp.plain_text((at(i) or live[0]).rendered),
            actions=[
                dlg.Action(
                    "&Add Text...", "Add a paragraph widget to an area.", add, needs_row=False
                ),
                dlg.Action("&Edit...", "Change a block widget's content.", edit),
                dlg.Action(
                    "&Move to Area...", "Show the selected widget in another area.", move_to
                ),
                dlg.Action("&Remove...", "Take the selected widget out of its area.", remove),
                dlg.Action(
                    "Open in Dash&board",
                    "Open the site's Widgets screen in your browser.",
                    dashboard,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()
