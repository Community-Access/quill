"""Add Menu Item and Add New Pages Automatically on a classic menu (wordpress.md 9.9).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`;
what each step means is :mod:`quill.core.wordpress.menu_item_add`.

- **Add Menu Item...** (on a menu's context menu, and Ctrl+N with a menu
  selected under Menus and Navigation) walks wp-admin's Add Menu Items panel
  in order: what kind (pages, posts, every custom type and taxonomy shown in
  menus, custom links), Search or View All, then where -- under which item and
  after which sibling -- then a preview. The menu is read again before the
  write, and a menu changed meanwhile is left alone. Ctrl+Z takes the item out
  and puts the items it moved back.
- **Add New Pages Automatically** turns a menu's ``auto_add`` on or off after
  a preview naming the state it is in now; the setting is read again before
  and after, and Ctrl+Z turns it back.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import menu_item_add as mia
from quill.core.wordpress import navigation as nav
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchMenuItemCommands"]


def _named(row: WbRow) -> str:
    """A menu row's name: its Menu column, since a row's title falls back to its id."""
    return row.cell("menu") or row.title


class WorkbenchMenuItemCommands:
    """A classic menu's items and its "add new top-level pages" setting."""

    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    commands: Any
    profile: Callable[[str], Any]

    def _a_menu(self, row: WbRow | None) -> bool:
        if row is None or row.kind != "menu":
            self.say("Choose a menu in Menus and Navigation first.")
            return False
        return True

    # -- Arrange Items: the Menus window, on this menu -----------------------------

    def do_arrange_menu_items(self, _ref: Any, row: WbRow | None) -> None:
        """Menu row > Arrange Items...: the Menus window, where items move up, down, in and out."""
        if not self._a_menu(row):
            return
        assert row is not None
        profile = self.profile(row.site)
        if profile is None:
            self.say(f"{row.site} is not a connected site here.")
            return
        self.commands.cmd_menus(menu_id=int(row.key), profile=profile)

    # -- Add Menu Item ------------------------------------------------------------

    def do_add_menu_item(self, _ref: Any, row: WbRow | None) -> None:
        if not self._a_menu(row):
            return
        assert row is not None
        api = self.ctx(row.site).api
        menu_id = int(row.key)
        self.background(
            f"reading what {_named(row)} can hold",
            lambda: (mia.item_sources(api), nav.classic_nodes(api, menu_id)),
            lambda got: self._choose_source(row, api, *got),
        )

    def _choose_source(
        self, row: WbRow, api: Any, sources: list[mia.ItemSource], nodes: list[nav.MenuNode]
    ) -> None:
        picked = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Add Menu Item to {_named(row)}",
            prompt="&Kind of item:",
            rows=[s.label for s in sources],
            help_text=(
                "What the new item links to: a page, a post, an item of any other type, a "
                "category, a tag or other term, or a custom link to any address."
            ),
        )
        if picked is None:
            return
        source = sources[picked]
        if source.type == "custom":
            url = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="Add a Custom Link",
                prompt="&URL:",
                value="https://",
                help_text="The address the item goes to, on this site or any other.",
            )
            if not url or not url.strip() or url.strip() == "https://":
                return
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="Add a Custom Link",
                prompt="&Link text:",
                help_text="The words the menu shows for the link.",
            )
            if not text or not text.strip():
                self.say("A custom link needs link text, so nothing was added.")
                return
            self._choose_place(row, api, nodes, source, 0, text.strip(), url.strip())
            return
        term = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Add {source.label} to {_named(row)}",
            prompt="&Search, or leave empty to view all:",
            help_text=(
                f"Words from the name of the {source.noun}. Empty lists them all, as wp-admin's "
                "View All does; only published items are listed."
            ),
        )
        if term is None:
            return
        self.background(
            f"finding {source.label.lower()}",
            lambda: mia.find_objects(api, source, term.strip()),
            lambda found: self._choose_object(row, api, nodes, source, term.strip(), found),
        )

    def _choose_object(
        self,
        row: WbRow,
        api: Any,
        nodes: list[nav.MenuNode],
        source: mia.ItemSource,
        term: str,
        found: list[tuple[int, str]],
    ) -> None:
        if not found:
            where = f" matching {term}" if term else ""
            self.say(f"{row.site} has no published {source.label.lower()}{where}.")
            return
        picked = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Add {source.label} to {_named(row)}",
            prompt=f"&{source.label}:",
            rows=[title for _id, title in found],
            help_text=f"The {source.noun} the new item links to; its name becomes the item's.",
        )
        if picked is None:
            return
        object_id, title = found[picked]
        self._choose_place(row, api, nodes, source, object_id, title, "")

    def _choose_place(
        self,
        row: WbRow,
        api: Any,
        nodes: list[nav.MenuNode],
        source: mia.ItemSource,
        object_id: int,
        title: str,
        url: str,
    ) -> None:
        parents = mia.parent_rows(nodes)
        index = 0
        if len(parents) > 1:
            chosen = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Where {title} Goes",
                prompt="&Under:",
                rows=[words for words, _node in parents],
                help_text="The top level of the menu, or the item it becomes a sub-item of.",
            )
            if chosen is None:
                return
            index = chosen
        owner = parents[index][1]
        siblings = owner.children if owner is not None else nodes
        place = len(siblings)
        if siblings:
            choices = mia.position_rows(siblings)
            chosen = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Where {title} Goes",
                prompt="&Position:",
                rows=choices,
                initial=len(choices) - 1,
                help_text="First, or after one of the items already there. The end is chosen.",
            )
            if chosen is None:
                return
            place = chosen
        under = f"under {owner.title}" if owner is not None else "at the top level"
        after = "first" if place == 0 else f"after {siblings[place - 1].title}"
        moving = len(siblings) - place
        lines = [
            f"Adds: {title}, {nav.KIND_NAMES.get(source.noun, source.noun)}"
            + (f", to {url}" if url else ""),
            f"Where: {under}, {after}, {place + 1} of {len(siblings) + 1}.",
        ]
        if moving:
            lines.append(f"The {moving} items after it there move down one.")
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Add Menu Item to {_named(row)}",
            summary=f"Add {title} to the menu {_named(row)} on {row.site}?",
            lines=lines,
            yes="Add",
        ):
            return
        seen = mia.layout_of(nodes)

        def work() -> mia.AddResult | mia.MenuChanged:
            try:
                return mia.add_menu_item(
                    api,
                    int(row.key),
                    source,
                    object_id=object_id,
                    title=title,
                    url=url,
                    parent_id=owner.item_id if owner is not None else 0,
                    index=place,
                    seen=seen,
                )
            except mia.MenuChanged as exc:
                return exc

        def done(result: mia.AddResult | mia.MenuChanged) -> None:
            if isinstance(result, mia.MenuChanged):
                self.say(str(result.args[0]))
                return
            summary = f"Added {title} to {_named(row)} on {row.site}."

            def undo() -> str:
                mia.undo_add(api, result)
                return f"Took {title} out of {_named(row)} again."

            self.history.record(Change(_named(row), summary, undo=undo))
            self.say(result.sentence)
            self.refresh()

        self.background(f"adding {title} to {_named(row)}", work, done)

    # -- Add New Pages Automatically ----------------------------------------------

    def do_menu_auto_add(self, _ref: Any, row: WbRow | None) -> None:
        if not self._a_menu(row):
            return
        assert row is not None
        api = self.ctx(row.site).api
        menu_id = int(row.key)
        self.background(
            f"reading {_named(row)}'s settings",
            lambda: mia.read_auto_add(api, menu_id),
            lambda was: self._auto_add(row, api, menu_id, bool(was)),
        )

    def _auto_add(self, row: WbRow, api: Any, menu_id: int, was: bool) -> None:
        on = not was
        if on:
            lines = [
                "Now: off. New pages are added to menus by hand.",
                f"After: on. Each new top-level page published joins the end of {_named(row)}.",
            ]
        else:
            lines = [
                f"Now: on. New top-level pages are added to {_named(row)} by themselves.",
                "After: off. Pages already in the menu stay; new ones are not added.",
            ]
        verb = "Turn On" if on else "Turn Off"
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Add New Pages Automatically",
            summary=f"{verb} {mia.AUTO_ADD_LABEL.lower()} for {_named(row)} on {row.site}?",
            lines=lines,
            yes=verb,
        ):
            return

        def work() -> bool | mia.MenuChanged:
            try:
                return mia.set_auto_add(api, menu_id, was=was, on=on)
            except mia.MenuChanged as exc:
                return exc

        def done(kept: bool | mia.MenuChanged) -> None:
            if isinstance(kept, mia.MenuChanged):
                self.say(str(kept.args[0]))
                return
            if kept != on:
                still = "on" if was else "off"
                self.say(f"{row.site} did not keep the change; it is still {still}.")
                return
            state = "on" if on else "off"
            summary = f"Adding new pages automatically to {_named(row)} is {state}."

            def undo() -> str:
                mia.set_auto_add(api, menu_id, was=on, on=was)
                again = "on" if was else "off"
                return f"Adding new pages automatically to {_named(row)} is {again} again."

            self.history.record(Change(_named(row), summary, undo=undo))
            self.say(summary)
            self.refresh()

        self.background(f"changing {_named(row)}", work, done)
