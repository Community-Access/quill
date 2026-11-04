"""Menus and Navigation as one readable tree (wordpress.md 9.9).

A classic theme keeps its menus as ``nav_menu_item`` posts (``wp/v2/menus``,
``menu-items``, ``menu-locations``, WordPress 5.9+); a block theme keeps them
as the content of a ``wp_navigation`` post (``wp/v2/navigation``). The
window does not care which: both load into :class:`Menu`, a list of
:class:`MenuNode` trees, and the same operations -- add, rename, move up and
down, in and out, remove -- apply to both. What differs is only how a change
is written back: item by item for a classic menu, the whole content for a
Navigation block.

The tree operations are pure functions on lists of nodes, so they are tested
without a site.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

from quill.core.wordpress import blocks as bk
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered

Source = Literal["classic", "navigation"]

#: What a row calls each kind of item.
KIND_NAMES = {
    "page": "page",
    "post": "post",
    "category": "category",
    "tag": "tag",
    "link": "link",
    "other": "other block",
}


@dataclass
class MenuNode:
    title: str
    kind: str  # page, post, category, tag, link, other
    object_id: int = 0
    url: str = ""
    item_id: int = 0  # a classic menu item's own id; 0 in a Navigation block
    children: list[MenuNode] = field(default_factory=list)
    #: A Navigation block's own attributes, kept so a save loses none of them.
    attrs: dict[str, Any] = field(default_factory=dict)
    #: A block the window cannot edit (Page List, Search...), written back untouched.
    block: bk.Block | None = None
    #: Where the classic item stood when loaded, so a save sends only changes.
    loaded_parent: int = 0
    loaded_order: int = 0


@dataclass
class Menu:
    id: int
    name: str
    source: Source
    locations: list[str] = field(default_factory=list)
    nodes: list[MenuNode] = field(default_factory=list)

    def spoken(self) -> str:
        kind = "menu" if self.source == "classic" else "Navigation block"
        where = f", in {', '.join(self.locations)}" if self.locations else ""
        count = sum(1 for _ in walk(self.nodes))
        return f"{self.name}, {kind}, {count} items{where}"


@dataclass(frozen=True)
class Location:
    slug: str
    name: str
    menu: int


# --------------------------------------------------------------------------- #
# Walking and rows


@dataclass(frozen=True)
class Row:
    depth: int
    node: MenuNode
    siblings: list[MenuNode]
    index: int

    def spoken(self) -> str:
        title = self.node.title or "(no name)"
        kind = "" if self.node.kind == "other" else f", {KIND_NAMES.get(self.node.kind)}"
        return f"{title}{kind}, level {self.depth + 1}, {self.index + 1} of {len(self.siblings)}"


def walk(nodes: list[MenuNode], depth: int = 0) -> Iterator[Row]:
    for index, node in enumerate(nodes):
        yield Row(depth, node, nodes, index)
        yield from walk(node.children, depth + 1)


def rows(nodes: list[MenuNode]) -> list[Row]:
    return list(walk(nodes))


def _parent_list(nodes: list[MenuNode], target: MenuNode) -> tuple[list[MenuNode], MenuNode | None]:
    """The sibling list holding *target*, and the node that owns it (None at the top)."""

    def search(
        items: list[MenuNode], owner: MenuNode | None
    ) -> tuple[list[MenuNode], MenuNode | None] | None:
        for node in items:
            if node is target:
                return items, owner
            found = search(node.children, node)
            if found is not None:
                return found
        return None

    found = search(nodes, None)
    if found is None:
        raise ValueError("that item is not in this menu")
    return found


# --------------------------------------------------------------------------- #
# Tree operations: each returns the sentence to speak, or "" when it cannot move


def move_up(nodes: list[MenuNode], node: MenuNode) -> str:
    siblings, _owner = _parent_list(nodes, node)
    i = siblings.index(node)
    if i == 0:
        return ""
    siblings[i - 1], siblings[i] = siblings[i], siblings[i - 1]
    return f"{node.title} moved up, {i} of {len(siblings)}."


def move_down(nodes: list[MenuNode], node: MenuNode) -> str:
    siblings, _owner = _parent_list(nodes, node)
    i = siblings.index(node)
    if i >= len(siblings) - 1:
        return ""
    siblings[i + 1], siblings[i] = siblings[i], siblings[i + 1]
    return f"{node.title} moved down, {i + 2} of {len(siblings)}."


def move_in(nodes: list[MenuNode], node: MenuNode) -> str:
    """Make *node* the last child of the item above it."""
    siblings, _owner = _parent_list(nodes, node)
    i = siblings.index(node)
    if i == 0:
        return ""
    new_parent = siblings[i - 1]
    siblings.pop(i)
    new_parent.children.append(node)
    return f"{node.title} is now under {new_parent.title}."


def move_out(nodes: list[MenuNode], node: MenuNode) -> str:
    """Move *node* out one level, to just after the item it was under."""
    siblings, owner = _parent_list(nodes, node)
    if owner is None:
        return ""
    outer, _ = _parent_list(nodes, owner)
    siblings.remove(node)
    outer.insert(outer.index(owner) + 1, node)
    return f"{node.title} moved out, after {owner.title}."


def remove(nodes: list[MenuNode], node: MenuNode) -> None:
    """Take *node* out; its own items move up into its place."""
    siblings, _owner = _parent_list(nodes, node)
    i = siblings.index(node)
    siblings[i : i + 1] = node.children


def problems(menu: Menu, statuses: dict[int, str]) -> list[str]:
    """Items with no name, and items pointing at a page or post visitors cannot reach."""
    found: list[str] = []
    for row in walk(menu.nodes):
        node = row.node
        if node.kind == "other":
            continue
        if not node.title.strip():
            found.append(f"An item at level {row.depth + 1} has no name.")
        if node.kind in {"page", "post"} and node.object_id:
            status = statuses.get(node.object_id, "missing")
            if status in {"draft", "pending", "private", "future"}:
                found.append(f"{node.title} points to a {status} {node.kind}: a dead link.")
            elif status in {"trash", "missing"}:
                where = "in the Trash" if status == "trash" else "gone"
                found.append(f"{node.title} points to a {node.kind} that is {where}: a dead link.")
    return found


def target_statuses(api: WordPressApi, menu: Menu) -> dict[int, str]:
    found: dict[int, str] = {}
    for kind, route in (("page", "wp/v2/pages"), ("post", "wp/v2/posts")):
        ids = sorted({r.node.object_id for r in walk(menu.nodes) if r.node.kind == kind})
        ids = [i for i in ids if i]
        if not ids:
            continue
        params: dict[str, object] = {
            "include": ids,
            "status": "any",
            "context": "edit",
            "_fields": "id,status",
        }
        for raw in api.iter_collection(route, params):
            found[int(raw.get("id", 0))] = str(raw.get("status", ""))
    return found


# --------------------------------------------------------------------------- #
# Loading


def load_menus(api: WordPressApi) -> list[Menu]:
    """Every classic menu and every Navigation block the site has.

    A site with no classic menus route (a block theme, or WordPress before 5.9)
    answers 404 there; that is not a failure, just nothing to list.
    """
    menus: list[Menu] = []
    locations = {loc.slug: loc for loc in load_locations(api)}
    try:
        for raw in api.iter_collection("wp/v2/menus", {"context": "edit"}):
            menu_id = int(raw.get("id", 0))
            names = [
                locations[s].name if s in locations else s for s in raw.get("locations", []) or []
            ]
            menus.append(
                Menu(
                    menu_id, str(raw.get("name", "")), "classic", names, classic_nodes(api, menu_id)
                )
            )
    except WordPressApiError as exc:
        if exc.status not in (404, 403, 401):
            raise
    try:
        params: dict[str, object] = {"context": "edit", "status": "publish"}
        for raw in api.iter_collection("wp/v2/navigation", params):
            title = raw_text(raw.get("title")) or "Navigation"
            content = raw_text(raw.get("content"))
            menus.append(
                Menu(int(raw.get("id", 0)), title, "navigation", [], navigation_nodes(content))
            )
    except WordPressApiError as exc:
        if exc.status not in (404, 403, 401):
            raise
    return menus


def load_locations(api: WordPressApi) -> list[Location]:
    try:
        raw = api.get("wp/v2/menu-locations", context="edit")
    except WordPressApiError as exc:
        if exc.status in (404, 403, 401):
            return []
        raise
    if not isinstance(raw, dict):
        return []
    return [
        Location(
            str(slug),
            str(v.get("description") or v.get("name") or slug),
            int(v.get("menu", 0) or 0),
        )
        for slug, v in raw.items()
        if isinstance(v, dict)
    ]


_CLASSIC_KINDS = {"page": "page", "post": "post", "category": "category", "post_tag": "tag"}


def classic_nodes(api: WordPressApi, menu_id: int) -> list[MenuNode]:
    params: dict[str, object] = {"menus": menu_id, "context": "edit", "orderby": "menu_order"}
    flat: list[tuple[int, MenuNode]] = []
    for raw in api.iter_collection("wp/v2/menu-items", params):
        kind = (
            "link"
            if raw.get("type") == "custom"
            else _CLASSIC_KINDS.get(str(raw.get("object", "")), "other")
        )
        parent = int(raw.get("parent", 0) or 0)
        order = int(raw.get("menu_order", 0) or 0)
        node = MenuNode(
            title=raw_text(raw.get("title")) or rendered(raw.get("title")),
            kind=kind,
            object_id=int(raw.get("object_id", 0) or 0),
            url=str(raw.get("url", "") or ""),
            item_id=int(raw.get("id", 0)),
            loaded_parent=parent,
            loaded_order=order,
        )
        flat.append((parent, node))
    flat.sort(key=lambda pair: pair[1].loaded_order)
    by_id = {n.item_id: n for _p, n in flat}
    top: list[MenuNode] = []
    for parent, node in flat:
        (by_id[parent].children if parent in by_id else top).append(node)
    return top


_NAV_KINDS = {
    "page": "page",
    "post": "post",
    "category": "category",
    "tag": "tag",
    "custom": "link",
}


def navigation_nodes(content: str) -> list[MenuNode]:
    return [
        _nav_node(b) for b in bk.parse(content) if not (b.freeform and not b.inner_html.strip())
    ]


def _nav_node(block: bk.Block) -> MenuNode:
    if block.name in ("core/navigation-link", "core/navigation-submenu"):
        attrs = dict(block.attrs)
        return MenuNode(
            title=str(attrs.get("label", "")),
            kind=_NAV_KINDS.get(str(attrs.get("type", "custom")), "link"),
            object_id=int(attrs.get("id", 0) or 0),
            url=str(attrs.get("url", "")),
            children=[_nav_node(b) for b in block.inner_blocks],
            attrs=attrs,
        )
    return MenuNode(title=bk.describe(block), kind="other", block=block)


# --------------------------------------------------------------------------- #
# Writing back


def serialize_navigation(nodes: list[MenuNode]) -> str:
    parts: list[str] = []
    for node in nodes:
        if node.block is not None:
            parts.append(bk.serialize_block(node.block))
            continue
        attrs = dict(node.attrs)
        attrs["label"] = node.title
        kind = {v: k for k, v in _NAV_KINDS.items()}.get(node.kind, "custom")
        attrs["type"] = kind
        attrs["kind"] = {"page": "post-type", "post": "post-type", "custom": "custom"}.get(
            kind, "taxonomy"
        )
        if node.object_id:
            attrs["id"] = node.object_id
        if node.url:
            attrs["url"] = node.url
        encoded = bk.serialize_attributes(attrs)
        if node.children:
            inner = serialize_navigation(node.children)
            parts.append(
                f"<!-- wp:navigation-submenu {encoded} -->{inner}<!-- /wp:navigation-submenu -->"
            )
        else:
            parts.append(f"<!-- wp:navigation-link {encoded} /-->")
    return "".join(parts)


def classic_positions(nodes: list[MenuNode]) -> list[tuple[MenuNode, int, int]]:
    """``(node, parent item id, menu_order)`` for every item, numbered 1.. in reading order."""
    out: list[tuple[MenuNode, int, int]] = []

    def visit(items: list[MenuNode], parent: int) -> None:
        for node in items:
            out.append((node, parent, len(out) + 1))
            visit(node.children, node.item_id)

    visit(nodes, 0)
    return out


def save_menu(api: WordPressApi, menu: Menu) -> int:
    """Write the tree back. Returns how many requests it took."""
    if menu.source == "navigation":
        api.post(f"wp/v2/navigation/{menu.id}", {"content": serialize_navigation(menu.nodes)})
        return 1
    sent = 0
    for node, parent, order in classic_positions(menu.nodes):
        if not node.item_id or (node.loaded_parent, node.loaded_order) == (parent, order):
            continue
        api.post(f"wp/v2/menu-items/{node.item_id}", {"parent": parent, "menu_order": order})
        node.loaded_parent, node.loaded_order = parent, order
        sent += 1
    return sent


def add_item(api: WordPressApi, menu: Menu, node: MenuNode) -> MenuNode:
    """Add *node* at the end of the menu's top level and save it."""
    if menu.source == "navigation":
        menu.nodes.append(node)
        save_menu(api, menu)
        return node
    order = len(classic_positions(menu.nodes)) + 1
    body: dict[str, object] = {
        "title": node.title,
        "menus": menu.id,
        "status": "publish",
        "parent": 0,
        "menu_order": order,
    }
    if node.kind == "link":
        body.update(type="custom", url=node.url)
    else:
        obj = {"tag": "post_tag"}.get(node.kind, node.kind)
        body.update(
            type="taxonomy" if node.kind in {"category", "tag"} else "post_type",
            object=obj,
            object_id=node.object_id,
        )
    raw = api.post("wp/v2/menu-items", body, context="edit")
    node.item_id = int(raw.get("id", 0)) if isinstance(raw, dict) else 0
    node.loaded_order = order
    menu.nodes.append(node)
    return node


def rename_item(api: WordPressApi, menu: Menu, node: MenuNode, title: str) -> None:
    node.title = title
    if menu.source == "navigation":
        save_menu(api, menu)
    else:
        api.post(f"wp/v2/menu-items/{node.item_id}", {"title": title})


def remove_item(api: WordPressApi, menu: Menu, node: MenuNode) -> None:
    remove(menu.nodes, node)
    if menu.source == "classic" and node.item_id:
        api.delete(f"wp/v2/menu-items/{node.item_id}", force=True)
    save_menu(api, menu)


def set_locations(api: WordPressApi, menu: Menu, slugs: list[str]) -> None:
    api.post(f"wp/v2/menus/{menu.id}", {"locations": slugs})
