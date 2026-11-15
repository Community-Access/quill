"""Adding to a classic menu, as wp-admin's Add Menu Items panel does (wordpress.md 9.9).

What the Workbench's **Add Menu Item...** and **Add New Pages Automatically**
mean, kept apart from the window so they are tested without a site:

- :func:`item_sources`: every kind of thing the panel offers -- Pages, Posts,
  each custom type shown in menus, Custom Links, Categories, Tags and each
  custom taxonomy shown in menus -- read from ``wp/v2/types`` and
  ``wp/v2/taxonomies``, never a fixed list;
- :func:`find_objects`: the panel's Search tab (a search term) and its View
  All tab (no term), published items only, with a post type's archive first
  where it has one, as View All lists it;
- :func:`parent_rows` and :func:`position_rows`: where the new item goes,
  under any item and before, between or after its siblings;
- :func:`add_menu_item`: reads the menu again first and refuses when it
  changed since the preview (:class:`MenuChanged`), adds the item, renumbers
  the items after it, then reads the item back; :func:`undo_add` reverses it;
- :func:`set_auto_add`: a classic menu's ``auto_add``, "Automatically add new
  top-level pages to this menu", with the same re-read before and after;
- :data:`MENU_SHEET`: a menu's Properties, with that setting as a check box.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress import navigation as nav
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import raw_text, rendered
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

__all__ = [
    "AUTO_ADD_LABEL",
    "MENU_SHEET",
    "AddResult",
    "ItemSource",
    "MenuChanged",
    "add_menu_item",
    "find_objects",
    "item_sources",
    "layout_of",
    "parent_rows",
    "position_rows",
    "read_auto_add",
    "set_auto_add",
    "undo_add",
]

AUTO_ADD_LABEL = "Automatically add new top-level pages to this menu"
LIMIT = 100

MENU_SHEET = SheetSpec(
    "menu",
    "Menu",
    (
        PageSpec(
            "general",
            "General",
            (
                FieldSpec("name", "Menu name", FieldKind.TEXT, help="The menu's name in wp-admin."),
                FieldSpec(
                    "description",
                    "Description",
                    FieldKind.MULTILINE,
                    help="A note about the menu; visitors do not see it.",
                ),
                FieldSpec(
                    "auto_add",
                    AUTO_ADD_LABEL,
                    FieldKind.CHECK,
                    requirement="edit_theme_options",
                    help=(
                        "Checked, each new top-level page published from now on is added to the "
                        "end of this menu by WordPress itself."
                    ),
                ),
                FieldSpec(
                    "locations",
                    "Shown in",
                    FieldKind.LIST,
                    readonly=True,
                    help="The theme's places this menu is shown in.",
                ),
            ),
        ),
    ),
)
"""A classic menu's Properties: wp-admin's Menu Settings."""


class MenuChanged(CodedError):
    """The menu changed on the site after it was read for the preview; nothing was sent."""

    code = "QUILL-WP-MENU-ITEM-CHANGED"


# --------------------------------------------------------------------------- #
# What can be added


@dataclass(frozen=True)
class ItemSource:
    """One box of the Add Menu Items panel: Pages, Posts, Categories, Custom Links..."""

    label: str
    type: str  # post_type, taxonomy or custom
    object: str = ""  # page, post, category, post_tag, product...
    route: str = ""  # wp/v2/pages, wp/v2/categories...
    archive: bool = False  # a post type with an archive page View All lists first

    @property
    def noun(self) -> str:
        return {"post_tag": "tag"}.get(self.object, self.object) or "link"


_NOT_IN_MENUS = {
    "attachment",
    "nav_menu_item",
    "wp_block",
    "wp_template",
    "wp_template_part",
    "wp_navigation",
    "wp_global_styles",
    "wp_font_family",
    "wp_font_face",
    "nav_menu",
    "wp_pattern_category",
    "wp_theme",
    "wp_template_part_area",
    "link_category",
    "post_format",
}


def _in_menus(slug: str, info: Mapping[str, Any]) -> bool:
    if slug in _NOT_IN_MENUS:
        return False
    seen = info.get("visibility")
    if isinstance(seen, dict) and "show_in_nav_menus" in seen:
        return bool(seen["show_in_nav_menus"])
    return bool(info.get("viewable", True))


def _route(info: Mapping[str, Any]) -> str:
    base = str(info.get("rest_base") or "").strip("/")
    space = str(info.get("rest_namespace") or "wp/v2").strip("/")
    return f"{space}/{base}" if base else ""


def item_sources(api: WordPressApi) -> list[ItemSource]:
    """What the site lets a menu hold, in the panel's order, Custom Links among them."""
    types = api.get("wp/v2/types", context="edit")
    taxes = api.get("wp/v2/taxonomies", context="edit")
    found: list[ItemSource] = []
    rank = {"page": 0, "post": 1}
    for slug, info in sorted(
        (types if isinstance(types, dict) else {}).items(), key=lambda p: (rank.get(p[0], 2), p[0])
    ):
        if isinstance(info, dict) and _in_menus(str(slug), info) and _route(info):
            found.append(
                ItemSource(
                    str(info.get("name") or slug),
                    "post_type",
                    str(slug),
                    _route(info),
                    bool(info.get("has_archive")),
                )
            )
    found.append(ItemSource("Custom Links", "custom"))
    rank = {"category": 0, "post_tag": 1}
    for slug, info in sorted(
        (taxes if isinstance(taxes, dict) else {}).items(), key=lambda p: (rank.get(p[0], 2), p[0])
    ):
        if isinstance(info, dict) and _in_menus(str(slug), info) and _route(info):
            name = str(info.get("name") or slug)
            found.append(ItemSource(name, "taxonomy", str(slug), _route(info)))
    return found


def _title(raw: Mapping[str, Any]) -> str:
    if "name" in raw and "title" not in raw:
        return rendered(raw.get("name")) or str(raw.get("name", ""))
    return raw_text(raw.get("title")) or rendered(raw.get("title")) or "(no title)"


def find_objects(api: WordPressApi, source: ItemSource, search: str = "") -> list[tuple[int, str]]:
    """``(id, title)`` for the panel's Search (a term) or View All (none); published only.

    A post type with an archive lists it first under View All, as id 0.
    """
    params: dict[str, object] = {"context": "edit"}
    if source.type == "post_type":
        params.update(status="publish", _fields="id,title")
        if not search:
            ordered = {"post": ("date", "desc")}.get(source.object, ("title", "asc"))
            params.update(orderby=ordered[0], order=ordered[1])
    else:
        params.update(_fields="id,name", orderby="name", order="asc", hide_empty=False)
    if search:
        params["search"] = search
    found: list[tuple[int, str]] = []
    if source.archive and not search:
        found.append((0, f"All {source.label} (the archive page)"))
    for raw in api.iter_collection(source.route, params, per_page=LIMIT, max_pages=1):
        found.append((int(raw.get("id", 0) or 0), _title(raw)))
    return found


# --------------------------------------------------------------------------- #
# Where it goes


def parent_rows(nodes: list[nav.MenuNode]) -> list[tuple[str, nav.MenuNode | None]]:
    """ "Top level of the menu", then every item by level, as places to go under."""
    out: list[tuple[str, nav.MenuNode | None]] = [("Top level of the menu", None)]
    for row in nav.walk(nodes):
        out.append((f"Under {row.node.title or '(no name)'}, level {row.depth + 1}", row.node))
    return out


def position_rows(siblings: list[nav.MenuNode]) -> list[str]:
    """First, after each sibling in turn; the last row is the end, the panel's own default."""
    return ["First"] + [f"After {n.title or '(no name)'}" for n in siblings]


def layout_of(nodes: list[nav.MenuNode]) -> tuple[tuple[int, int, int], ...]:
    """Every item's id, parent and order: what the preview saw, to compare before writing."""
    return tuple(sorted((n.item_id, n.loaded_parent, n.loaded_order) for n in _all(nodes)))


def _all(nodes: list[nav.MenuNode]) -> list[nav.MenuNode]:
    return [row.node for row in nav.walk(nodes)]


@dataclass
class AddResult:
    item_id: int
    sentence: str
    #: Items renumbered to make room: (item id, parent, order) before the add.
    moved: list[tuple[int, int, int]] = field(default_factory=list)


def _body(menu_id: int, source: ItemSource, object_id: int, title: str, url: str) -> dict[str, Any]:
    body: dict[str, Any] = {"title": title, "menus": menu_id, "status": "publish"}
    if source.type == "custom":
        body.update(type="custom", url=url)
    elif object_id == 0:
        body.update(type="post_type_archive", object=source.object)
    else:
        body.update(type=source.type, object=source.object, object_id=object_id)
    return body


def add_menu_item(
    api: WordPressApi,
    menu_id: int,
    source: ItemSource,
    *,
    object_id: int = 0,
    title: str = "",
    url: str = "",
    parent_id: int = 0,
    index: int = -1,
    seen: tuple[tuple[int, int, int], ...] | None = None,
) -> AddResult:
    """Add one item under *parent_id* at *index* among its siblings (-1: the end).

    Reads the menu first; when *seen* is given and the menu is not as the
    preview saw it, raises :class:`MenuChanged` and sends nothing.
    """
    nodes = nav.classic_nodes(api, menu_id)
    if seen is not None and layout_of(nodes) != seen:
        raise MenuChanged("The menu was changed on the site after the preview. Nothing was sent.")
    owner = next((r.node for r in nav.walk(nodes) if r.node.item_id == parent_id), None)
    siblings = owner.children if owner is not None else nodes
    if parent_id and owner is None:
        raise MenuChanged("The item it was to go under is no longer in the menu. Nothing was sent.")
    node = nav.MenuNode(title, source.noun, object_id, url=url)
    siblings.insert(len(siblings) if index < 0 else min(index, len(siblings)), node)
    before = {n.item_id: (n.loaded_parent, n.loaded_order) for n in _all(nodes)}
    order = next(o for n, _p, o in nav.classic_positions(nodes) if n is node)
    body = _body(menu_id, source, object_id, title, url)
    body.update(parent=parent_id, menu_order=order)
    made = api.post("wp/v2/menu-items", body, context="edit")
    node.item_id = int(made.get("id", 0) or 0) if isinstance(made, dict) else 0
    node.loaded_parent, node.loaded_order = parent_id, order
    moved = [
        (n.item_id, *before[n.item_id])
        for n, parent, place in nav.classic_positions(nodes)
        if n is not node and n.item_id in before and before[n.item_id] != (parent, place)
    ]
    nav.save_menu(api, nav.Menu(menu_id, "", "classic", [], nodes))
    back = api.get(f"wp/v2/menu-items/{node.item_id}", context="edit") if node.item_id else {}
    back = back if isinstance(back, dict) else {}
    named = raw_text(back.get("title")) or rendered(back.get("title")) or title
    kept = node.item_id and int(back.get("parent", 0) or 0) == parent_id
    sentence = (
        f"Added {named} to the menu."
        if kept
        else (f"Sent {title}, but the site did not keep it where it was asked to go.")
    )
    return AddResult(node.item_id, sentence, moved)


def undo_add(api: WordPressApi, result: AddResult) -> None:
    """Delete the added item and put every renumbered item back where it was."""
    if result.item_id:
        api.delete(f"wp/v2/menu-items/{result.item_id}", force=True)
    for item_id, parent, order in result.moved:
        api.post(f"wp/v2/menu-items/{item_id}", {"parent": parent, "menu_order": order})


# --------------------------------------------------------------------------- #
# Automatically add new top-level pages


def read_auto_add(api: WordPressApi, menu_id: int) -> bool:
    raw = api.get(f"wp/v2/menus/{menu_id}", context="edit")
    return bool(raw.get("auto_add")) if isinstance(raw, dict) else False


def set_auto_add(api: WordPressApi, menu_id: int, *, was: bool, on: bool) -> bool:
    """Turn ``auto_add`` *on* or off, if it is still *was*; returns what the site kept."""
    if read_auto_add(api, menu_id) != was:
        raise MenuChanged("The menu's setting was changed on the site meanwhile. Nothing was sent.")
    api.post(f"wp/v2/menus/{menu_id}", {"auto_add": on}, context="edit")
    return read_auto_add(api, menu_id)
