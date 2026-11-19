"""Widgets (wordpress.md 9.9): a classic theme's widget areas, as lists.

Split from :mod:`quill.ui.wordpress_menu_commands` (GATE-11), whose class
inherits this one, so :class:`~quill.ui.wordpress_commands.WordPressCommands`
reaches it exactly as before.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_structure as ss
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

__all__ = ["WordPressWidgetCommands"]


class WordPressWidgetCommands(WordPressAdminBase):
    """Appearance > Widgets, for a classic theme."""

    # ------------------------------------------------------------------ #
    # Widgets (classic themes)

    def cmd_widgets(self) -> None:
        if self.workbench_door("wordpress.widgets"):
            return  # the developer flag sends this door to the WordPress Workbench
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
