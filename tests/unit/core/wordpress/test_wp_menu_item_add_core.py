"""Add Menu Item and a menu's auto_add, without a site (quill.core.wordpress.menu_item_add)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import menu_item_add as mia
from quill.core.wordpress.workbench_edit import EditConflict, check_conflict
from quill.core.wordpress.workbench_moderation import version_of
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import sheet_for, values_for
from quill.core.workbench.properties import FieldKind


class MenuApi:
    def __init__(self) -> None:
        self.items: dict[int, dict[str, Any]] = {
            31: {
                "id": 31,
                "title": {"raw": "Home"},
                "type": "custom",
                "url": "/",
                "parent": 0,
                "menu_order": 1,
            },
            32: {
                "id": 32,
                "title": {"raw": "Shows"},
                "type": "custom",
                "url": "/s",
                "parent": 0,
                "menu_order": 2,
            },
            33: {
                "id": 33,
                "title": {"raw": "Late"},
                "type": "custom",
                "url": "/l",
                "parent": 32,
                "menu_order": 3,
            },
        }
        self.menu = {
            "id": 3,
            "name": "Top",
            "description": "",
            "auto_add": False,
            "locations": ["primary"],
        }
        self.writes: list[tuple[str, str, Any]] = []
        self.asked: list[tuple[str, dict[str, Any]]] = []
        self.next_id = 40

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/types":
            return {
                "post": {"name": "Posts", "rest_base": "posts", "viewable": True},
                "page": {"name": "Pages", "rest_base": "pages", "viewable": True},
                "attachment": {"name": "Media", "rest_base": "media", "viewable": True},
                "show": {
                    "name": "Shows",
                    "rest_base": "shows",
                    "has_archive": True,
                    "visibility": {"show_in_nav_menus": True},
                },
                "hidden": {
                    "name": "Hidden",
                    "rest_base": "hidden",
                    "visibility": {"show_in_nav_menus": False},
                },
            }
        if route == "wp/v2/taxonomies":
            return {
                "post_tag": {"name": "Tags", "rest_base": "tags"},
                "category": {"name": "Categories", "rest_base": "categories"},
                "genre": {"name": "Genres", "rest_base": "genres"},
                "nav_menu": {"name": "Menus", "rest_base": "menus"},
            }
        if route == "wp/v2/menus/3":
            return dict(self.menu)
        if route.startswith("wp/v2/menu-items/"):
            return dict(self.items[int(route.rsplit("/", 1)[1])])
        raise AssertionError(route)

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Any:
        self.asked.append((route, dict(params or {})))
        if route == "wp/v2/menu-items":
            yield from (dict(i) for i in self.items.values())
        elif route == "wp/v2/pages":
            yield {"id": 7, "title": {"raw": "Contact"}}
        elif route == "wp/v2/categories":
            yield {"id": 5, "name": "News"}

    def post(self, route: str, body: Any = None, **_params: Any) -> Any:
        self.writes.append(("POST", route, dict(body)))
        if route == "wp/v2/menus/3":
            self.menu.update(body)
            return dict(self.menu)
        if route == "wp/v2/menu-items":
            made = {"id": self.next_id, **body, "title": {"raw": body["title"]}}
            self.items[self.next_id] = made
            self.next_id += 1
            return dict(made)
        item = self.items[int(route.rsplit("/", 1)[1])]
        item.update(body)
        return dict(item)

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        self.items.pop(int(route.rsplit("/", 1)[1]), None)
        return {}


def test_sources_follow_the_panel_and_the_sites_own_types() -> None:
    sources = mia.item_sources(MenuApi())
    assert [s.label for s in sources] == [
        "Pages",
        "Posts",
        "Shows",
        "Custom Links",
        "Categories",
        "Tags",
        "Genres",
    ]
    show = sources[2]
    assert (show.type, show.object, show.route, show.archive) == (
        "post_type",
        "show",
        "wp/v2/shows",
        True,
    )
    assert sources[5].noun == "tag" and sources[3].type == "custom"


def test_search_and_view_all_ask_for_published_items() -> None:
    api = MenuApi()
    pages = mia.ItemSource("Pages", "post_type", "page", "wp/v2/pages")
    assert mia.find_objects(api, pages, "cont") == [(7, "Contact")]
    assert api.asked[-1][1]["search"] == "cont" and api.asked[-1][1]["status"] == "publish"
    assert "orderby" not in api.asked[-1][1]
    cats = mia.ItemSource("Categories", "taxonomy", "category", "wp/v2/categories")
    assert mia.find_objects(api, cats) == [(5, "News")]
    shows = mia.ItemSource("Shows", "post_type", "show", "wp/v2/shows", archive=True)
    assert mia.find_objects(api, shows)[0] == (0, "All Shows (the archive page)")


def test_add_between_items_renumbers_those_after_and_undo_puts_them_back() -> None:
    api = MenuApi()
    pages = mia.ItemSource("Pages", "post_type", "page", "wp/v2/pages")
    from quill.core.wordpress import navigation as nav

    seen = mia.layout_of(nav.classic_nodes(api, 3))
    result = mia.add_menu_item(
        api, 3, pages, object_id=7, title="Contact", parent_id=0, index=1, seen=seen
    )
    made = api.writes[0]
    assert made[1] == "wp/v2/menu-items"
    assert made[2] | {"title": "Contact"} == {
        "title": "Contact",
        "menus": 3,
        "status": "publish",
        "type": "post_type",
        "object": "page",
        "object_id": 7,
        "parent": 0,
        "menu_order": 2,
    }
    assert api.items[32]["menu_order"] == 3 and api.items[33]["menu_order"] == 4
    assert result.sentence == "Added Contact to the menu."
    mia.undo_add(api, result)
    assert 40 not in api.items
    assert api.items[32]["menu_order"] == 2 and api.items[33]["menu_order"] == 3


def test_a_custom_link_under_an_item_and_an_archive() -> None:
    api = MenuApi()
    link = mia.ItemSource("Custom Links", "custom")
    mia.add_menu_item(api, 3, link, title="Map", url="https://m.example", parent_id=32)
    assert api.items[40]["type"] == "custom" and api.items[40]["url"] == "https://m.example"
    assert api.items[40]["parent"] == 32 and api.items[40]["menu_order"] == 4
    shows = mia.ItemSource("Shows", "post_type", "show", "wp/v2/shows", archive=True)
    mia.add_menu_item(api, 3, shows, object_id=0, title="All Shows")
    assert api.items[41]["type"] == "post_type_archive" and api.items[41]["object"] == "show"


def test_a_menu_changed_since_the_preview_is_left_alone() -> None:
    api = MenuApi()
    from quill.core.wordpress import navigation as nav

    seen = mia.layout_of(nav.classic_nodes(api, 3))
    api.items[32]["menu_order"] = 9  # somebody moved Shows
    with pytest.raises(mia.MenuChanged):
        mia.add_menu_item(api, 3, mia.ItemSource("Custom Links", "custom"), title="X", seen=seen)
    assert api.writes == []


def test_where_rows_name_every_place() -> None:
    from quill.core.wordpress import navigation as nav

    nodes = nav.classic_nodes(MenuApi(), 3)
    assert [w for w, _n in mia.parent_rows(nodes)] == [
        "Top level of the menu",
        "Under Home, level 1",
        "Under Shows, level 1",
        "Under Late, level 2",
    ]
    assert mia.position_rows(nodes) == ["First", "After Home", "After Shows"]


def test_auto_add_is_checked_before_and_read_back_after() -> None:
    api = MenuApi()
    assert mia.set_auto_add(api, 3, was=False, on=True) is True
    assert api.writes == [("POST", "wp/v2/menus/3", {"auto_add": True})]
    with pytest.raises(mia.MenuChanged):
        mia.set_auto_add(api, 3, was=False, on=True)  # it is on now, not off
    assert len(api.writes) == 1


def test_a_menus_properties_show_auto_add_as_a_labelled_check_box() -> None:
    api = MenuApi()
    row = WbRow("menu", "Radio", "3", {"menu": "Top"}, "Top", route="wp/v2/menus/3", raw=api.menu)
    sheet = sheet_for(row, schema={"anything": {"type": "string"}})
    field = sheet.field("auto_add")
    assert field.kind is FieldKind.CHECK and field.label == mia.AUTO_ADD_LABEL and field.help
    assert sheet.field("locations").readonly
    assert values_for(row, api.menu)["auto_add"] is False
    loaded = version_of("menu", api.menu)
    api.menu["auto_add"] = True  # changed on the site after the sheet opened
    with pytest.raises(EditConflict):
        check_conflict(api, row, loaded)  # type: ignore[arg-type]
