"""Site Map, Template Outline, Page Order and Bulk Edit (wordpress.md 9.9, 9.13).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, gathered
by :class:`~quill.ui.wordpress_admin_commands.WordPressAdminCommands`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress import navigation as nav
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_library as lib
from quill.core.wordpress import site_structure as ss
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

BULK_UNDO_FILE = "wordpress-bulk-undo.json"


def _menu_links(api: Any) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    for menu in nav.load_menus(api):
        for row in nav.walk(menu.nodes):
            if row.node.object_id and row.node.kind in {"page", "post"}:
                names = found.setdefault(row.node.object_id, [])
                if menu.name not in names:
                    names.append(menu.name)
    return found


class WordPressStructureCommands(WordPressAdminBase):
    # ------------------------------------------------------------------ #
    # Site Map (9.9)

    def cmd_site_map(self) -> None:
        if self.workbench_door("wordpress.site_map"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Site Map")
        if profile is None:
            return

        def work(api: Any, account: wp.Account) -> list[ss.MapRow]:
            pages = ss.load_page_tree(api)
            posts = ss.load_posts_for_map(api)
            categories = {t.id: t.name for t in wp.list_terms(api, "category")}
            menus = _menu_links(api) if account.can("edit_theme_options") else {}
            return ss.site_map(pages, posts, categories, menus)

        self.admin_load(
            profile,
            f"reading {profile.name}'s pages and posts",
            None,
            work,
            lambda api, _account, found: self._show_site_map(profile, found),
        )

    def _show_site_map(self, profile: st.SiteProfile, found: list[ss.MapRow]) -> None:
        def row_text(row: ss.MapRow) -> str:
            return f"{row.text}, level {row.depth}" if row.kind else row.text

        def open_one(index: int | None) -> object:
            row = found[index] if index is not None else None
            if row is None or not row.kind:
                self.host.announce("That is a heading. Choose a page or post under it.")
                return None
            self.open_item(profile, row.kind, row.item_id)  # type: ignore[attr-defined]
            return dlg.CLOSE

        def on_site(index: int | None) -> object:
            row = found[index] if index is not None else None
            if row is not None and row.link:
                self.host.open_in_browser(row.link)
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Site Map, {profile.name}",
            purpose=(
                f"Where everything on {profile.name} lives: pages by parent, then posts under "
                "their categories, with the menus that link to each."
            ),
            list_label="&Site map:",
            list_help="Each row gives the title, any menu it is in, and its level in the tree.",
            rows=[row_text(r) for r in found],
            actions=[
                dlg.Action("&Open", "Open the selected page or post for editing.", open_one),
                dlg.Action("Open on Si&te", "Open the selected item in your browser.", on_site),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Template Outline (9.9)

    def cmd_template_outline(self) -> None:
        profile = self.admin_site("Template Outline")
        if profile is None:
            return
        copy = self.local.copy_for_path(self.host.current_path())  # type: ignore[attr-defined]
        first = ""
        if copy is not None:
            first = str(copy.properties.get("template") or "") or (
                "page" if copy.kind == "page" else "single"
            )

        def show(_api: Any, _account: wp.Account, templates: list[ss.Template]) -> None:
            if not templates:
                self.host.announce(
                    f"{profile.name} uses a classic theme, so it has no block templates. "
                    "Its sidebars and footer are in Widgets."
                )
                return
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Template Outline, {profile.name}",
                text=ss.template_outline(templates, first=first),
                help_text=(
                    "The theme's templates and template parts, with the blocks in each, "
                    "indented by depth. They explain things on a page that are not in the page. "
                    "Change them in the site editor."
                ),
            )

        self.admin_load(
            profile,
            f"reading {profile.name}'s templates",
            None,
            lambda api, _account: ss.list_templates(api),
            show,
        )

    # ------------------------------------------------------------------ #
    # Page Order (9.13)

    def cmd_page_order(self) -> None:
        profile = self.admin_site("Page Order")
        if profile is None:
            return
        self.admin_load(
            profile,
            f"reading {profile.name}'s pages",
            "page_order",
            lambda api, _account: ss.load_page_tree(api),
            lambda api, _account, tree: self._show_page_order(profile, api, tree),
        )

    def _show_page_order(self, profile: st.SiteProfile, api: Any, tree: list[ss.PageNode]) -> None:
        if not tree:
            self.host.announce(f"{profile.name} has no pages yet.")
            return

        def rows() -> list[str]:
            return [ss.page_row(d, n, s) for d, n, s in ss.walk_pages(tree)]

        def at(index: int | None) -> ss.PageNode | None:
            found = ss.walk_pages(tree)
            return found[index][1] if index is not None and index < len(found) else None

        def mover(how: str) -> Any:
            def run(index: int | None) -> object:
                node = at(index)
                if node is None:
                    return None
                said = ss.page_move(tree, node, how)
                if not said:
                    self.host.announce(f"{node.title} cannot move that way.")
                    return None
                self.site_job(
                    "saving the page order", lambda: ss.save_page_order(api, tree), lambda _n: said
                )
                return rows()

            return run

        def open_one(index: int | None) -> object:
            node = at(index)
            if node is None:
                return None
            self.open_item(profile, "page", node.id)  # type: ignore[attr-defined]
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Page Order, {profile.name}",
            purpose=(
                f"{profile.name}'s pages as a tree. Moving a page sets its parent and its place "
                "among its neighbours, which is the order menus and page lists use."
            ),
            list_label="&Pages:",
            list_help="Each page's title, its level, and its place among the pages beside it.",
            rows=rows(),
            actions=[
                dlg.Action("Move &Up", "Move the page before the one above it.", mover("up")),
                dlg.Action("Move &Down", "Move the page after the one below it.", mover("down")),
                dlg.Action("Move &In", "Put the page under the one above it.", mover("in")),
                dlg.Action("Move &Out", "Move the page out one level.", mover("out")),
                dlg.Action("Op&en", "Open the selected page for editing.", open_one),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Bulk Edit (9.13)

    def _bulk_path(self) -> Path:
        from quill.core.paths import app_data_dir

        base = getattr(self, "_data_dir", None)
        return Path(base or app_data_dir()) / BULK_UNDO_FILE

    def _bulk_record(self, site_id: str) -> dict[str, Any] | None:
        records = read_json(self._bulk_path(), default=None)
        record = records.get(site_id) if isinstance(records, dict) else None
        return record if isinstance(record, dict) else None

    def _keep_bulk_record(self, site_id: str, record: dict[str, Any] | None) -> None:
        records = read_json(self._bulk_path(), default=None)
        records = records if isinstance(records, dict) else {}
        if record is None:
            records.pop(site_id, None)
        else:
            records[site_id] = record
        write_json_atomic(self._bulk_path(), records)

    def cmd_bulk_edit(self) -> None:
        profile = self.admin_site("Bulk Edit")
        if profile is None:
            return
        which = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Bulk Edit",
            prompt="&Edit:",
            rows=["Posts", "Pages"],
            help_text="Which kind of item to change several of at once.",
        )
        if which is None:
            return
        kind = "post" if which == 0 else "page"

        def work(api: Any, _account: wp.Account) -> dict[str, Any]:
            return {
                "items": list(wp.list_items(api, kind)),
                "authors": _authors(api),
                "categories": wp.list_terms(api, "category") if kind == "post" else [],
                "tags": wp.list_terms(api, "post_tag") if kind == "post" else [],
            }

        self.admin_load(
            profile,
            f"reading {kind}s on {profile.name}",
            "bulk_edit",
            work,
            lambda api, _account, data: self._show_bulk(profile, api, kind, data),
        )

    def _show_bulk(
        self, profile: st.SiteProfile, api: Any, kind: str, data: dict[str, Any]
    ) -> None:
        items: list[wp.ItemSummary] = data["items"]
        chosen: set[int] = set()

        def rows() -> list[str]:
            return [("Selected, " if i.id in chosen else "") + i.spoken() for i in items]

        def toggle(index: int | None) -> object:
            if index is None:
                return None
            item_id = items[index].id
            chosen.symmetric_difference_update({item_id})
            return rows()

        def select_all(_index: int | None) -> object:
            if len(chosen) == len(items):
                chosen.clear()
            else:
                chosen.update(i.id for i in items)
            self.host.announce(f"{len(chosen)} {kind}s selected.")
            return rows()

        def change(_index: int | None) -> object:
            if not chosen:
                self.host.announce(f"Select the {kind}s to change first, with Select.")
                return None
            fields = lib.bulk_fields(kind)
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Change",
                prompt="&Change:",
                rows=[label for _f, label in fields],
                help_text=f"What to change on every selected {kind}.",
            )
            if picked is None:
                return None
            field, label = fields[picked]
            options = self._bulk_options(field, data, items)
            value_index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=label,
                prompt="&To:",
                rows=[name for _v, name in options],
                help_text=f"The new {label.lower()} for every selected {kind}.",
            )
            if value_index is None:
                return None
            value, value_name = options[value_index]
            count = len(chosen)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Bulk Edit",
                message=(
                    f"{label}: {value_name}, for {count} {kind}s on {profile.name}? Undo Bulk "
                    "Edit can put them back."
                ),
                yes_label=f"Change {count}",
            ):
                return None
            ids = sorted(chosen)

            def done(record: dict[str, Any]) -> None:
                self._keep_bulk_record(profile.id, record)
                self.host.announce(f"{count} {kind}s changed on {profile.name}.")

            self.background(  # type: ignore[attr-defined]
                "bulk edit",
                lambda: lib.bulk_edit(
                    api, site_id=profile.id, kind=kind, ids=ids, field=field, value=value
                ),
                done,
            )
            return None

        def undo(_index: int | None) -> object:
            record = self._bulk_record(profile.id)
            if record is None:
                self.host.announce(f"There is no bulk edit on {profile.name} to undo.")
                return None
            count = len(record.get("before", {}))
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Undo Bulk Edit",
                message=f"Put {count} items on {profile.name} back as they were?",
                yes_label="Undo",
            ):
                return None

            def done(n: int) -> None:
                self._keep_bulk_record(profile.id, None)
                self.host.announce(f"{n} items put back on {profile.name}.")

            self.background("undoing a bulk edit", lambda: lib.undo_bulk_edit(api, record), done)  # type: ignore[attr-defined]
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Bulk Edit {kind.title()}s, {profile.name}",
            purpose=(
                f"Select the {kind}s to change, then Change. Every change is one confirmation "
                "and one request, and Undo Bulk Edit puts the items back."
            ),
            list_label=f"&{kind.title()}s:",
            list_help=f"Each {kind}'s title, status and last change. Selected ones say so first.",
            rows=rows(),
            actions=[
                dlg.Action("&Select", f"Select or unselect the {kind}.", toggle),
                dlg.Action("Select &All", "Select every item, or none when all are.", select_all),
                dlg.Action(
                    "&Change...", "Change the selected items together.", change, needs_row=False
                ),
                dlg.Action(
                    "&Undo Bulk Edit...",
                    "Put back the items the last bulk edit on this site changed.",
                    undo,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()

    @staticmethod
    def _bulk_options(
        field: str, data: dict[str, Any], items: list[wp.ItemSummary]
    ) -> list[tuple[Any, str]]:
        if field == "status":
            return list(lib.BULK_STATUSES)
        if field == "author":
            return list(data["authors"])
        if field == "categories":
            return [(t.id, t.name) for t in data["categories"]]
        if field == "tags":
            return [(t.id, t.name) for t in data["tags"]]
        if field == "comment_status":
            return [("open", "Open"), ("closed", "Closed")]
        return [(0, "No parent")] + [(i.id, i.title) for i in items]


def _authors(api: Any) -> list[tuple[int, str]]:
    from quill.core.wordpress.api import WordPressApiError

    try:
        params: dict[str, object] = {"who": "authors", "_fields": "id,name"}
        return [
            (int(r.get("id", 0)), str(r.get("name", "")))
            for r in api.iter_collection("wp/v2/users", params)
        ]
    except WordPressApiError:
        return []
