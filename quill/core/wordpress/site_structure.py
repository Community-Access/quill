"""Widgets, the site map, templates, and page order (wordpress.md 9.9, 9.13).

The parts of a site that the browser shows as boxes to drag become readable
lists here. Wx-free; every request through ``WordPressApi``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress import blocks as bk
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import plain_text, raw_text, rendered

# --------------------------------------------------------------------------- #
# Widgets (classic themes)


@dataclass(frozen=True)
class Sidebar:
    id: str
    name: str
    description: str
    widgets: tuple[str, ...]


@dataclass(frozen=True)
class Widget:
    id: str
    id_base: str
    sidebar: str
    content: str  # a block widget's block markup; "" for a classic widget
    rendered: str

    @property
    def is_block(self) -> bool:
        return self.id_base == "block"

    def spoken(self) -> str:
        if self.is_block:
            parsed = [b for _d, _p, b in bk.walk(bk.parse(self.content))]
            name = bk.describe(parsed[0]) if parsed else "Empty block"
            return name
        words = " ".join(plain_text(self.rendered).split()[:8])
        kind = self.id_base.replace("_", " ").replace("-", " ").title()
        return f"{kind} widget: {words}" if words else f"{kind} widget"


def list_sidebars(api: WordPressApi) -> list[Sidebar]:
    raw = api.get("wp/v2/sidebars", context="edit")
    return [
        Sidebar(
            id=str(r.get("id", "")),
            name=str(r.get("name", "")),
            description=str(r.get("description", "") or ""),
            widgets=tuple(str(w) for w in r.get("widgets", []) or []),
        )
        for r in (raw if isinstance(raw, list) else [])
        if isinstance(r, dict) and r.get("id") != "wp_inactive_widgets"
    ]


def widget_from_payload(raw: Any) -> Widget:
    instance = raw.get("instance", {}) if isinstance(raw.get("instance"), dict) else {}
    inner = instance.get("raw", {}) if isinstance(instance.get("raw"), dict) else {}
    return Widget(
        id=str(raw.get("id", "")),
        id_base=str(raw.get("id_base", "")),
        sidebar=str(raw.get("sidebar", "")),
        content=str(inner.get("content", "") or ""),
        rendered=str(raw.get("rendered", "") or ""),
    )


def list_widgets(api: WordPressApi, sidebar: str) -> list[Widget]:
    raw = api.get("wp/v2/widgets", sidebar=sidebar, context="edit")
    return [
        widget_from_payload(r)
        for r in (raw if isinstance(raw, list) else [])
        if isinstance(r, dict)
    ]


def add_block_widget(api: WordPressApi, sidebar: str, content: str) -> Widget:
    body = {"id_base": "block", "sidebar": sidebar, "instance": {"raw": {"content": content}}}
    return widget_from_payload(api.post("wp/v2/widgets", body, context="edit"))


def edit_block_widget(api: WordPressApi, widget: Widget, content: str) -> Widget:
    body = {"instance": {"raw": {"content": content}}}
    return widget_from_payload(api.post(f"wp/v2/widgets/{widget.id}", body, context="edit"))


def move_widget(api: WordPressApi, widget: Widget, sidebar: str) -> Widget:
    return widget_from_payload(
        api.post(f"wp/v2/widgets/{widget.id}", {"sidebar": sidebar}, context="edit")
    )


def remove_widget(api: WordPressApi, widget: Widget) -> None:
    """To Inactive Widgets, where the dashboard can still bring it back."""
    api.delete(f"wp/v2/widgets/{widget.id}")


def paragraph_block(text: str) -> str:
    import html as _html

    return f"<!-- wp:paragraph --><p>{_html.escape(text)}</p><!-- /wp:paragraph -->"


# --------------------------------------------------------------------------- #
# Pages as a tree: the site map and Page Order


@dataclass
class PageNode:
    id: int
    title: str
    parent: int
    menu_order: int
    status: str
    link: str = ""
    kind: str = "page"
    children: list[PageNode] = field(default_factory=list)
    loaded_parent: int = 0
    loaded_order: int = 0


def load_page_tree(api: WordPressApi) -> list[PageNode]:
    params: dict[str, object] = {
        "context": "edit",
        "status": ["publish", "draft", "pending", "private", "future"],
        "orderby": "menu_order",
        "order": "asc",
        "_fields": "id,title,parent,menu_order,status,link",
    }
    flat: list[PageNode] = []
    for raw in api.iter_collection("wp/v2/pages", params):
        parent = int(raw.get("parent", 0) or 0)
        order = int(raw.get("menu_order", 0) or 0)
        flat.append(
            PageNode(
                id=int(raw.get("id", 0)),
                title=rendered(raw.get("title")) or "(untitled)",
                parent=parent,
                menu_order=order,
                status=str(raw.get("status", "")),
                link=str(raw.get("link", "")),
                loaded_parent=parent,
                loaded_order=order,
            )
        )
    return build_tree(flat)


def build_tree(flat: list[PageNode]) -> list[PageNode]:
    by_id = {p.id: p for p in flat}
    top: list[PageNode] = []
    for page in sorted(flat, key=lambda p: (p.menu_order, p.title.lower())):
        (by_id[page.parent].children if page.parent in by_id else top).append(page)
    return top


def walk_pages(nodes: list[PageNode], depth: int = 0) -> list[tuple[int, PageNode, list[PageNode]]]:
    out: list[tuple[int, PageNode, list[PageNode]]] = []
    for node in nodes:
        out.append((depth, node, nodes))
        out.extend(walk_pages(node.children, depth + 1))
    return out


def page_row(depth: int, node: PageNode, siblings: list[PageNode]) -> str:
    status = "" if node.status == "publish" else f", {node.status}"
    return f"{node.title}{status}, level {depth + 1}, {siblings.index(node) + 1} of {len(siblings)}"


def _owner(nodes: list[PageNode], target: PageNode) -> tuple[list[PageNode], PageNode | None]:
    for depth_node in walk_pages(nodes):
        _d, node, siblings = depth_node
        if node is target:
            owner = next((n for _x, n, _s in walk_pages(nodes) if siblings is n.children), None)
            return siblings, owner
    raise ValueError("that page is not in the tree")


def page_move(nodes: list[PageNode], node: PageNode, how: str) -> str:
    """Move a page: "up", "down", "in" or "out". The sentence to speak, or ""."""
    siblings, owner = _owner(nodes, node)
    i = siblings.index(node)
    if how == "up" and i > 0:
        siblings[i - 1], siblings[i] = siblings[i], siblings[i - 1]
        return f"{node.title} moved up, {i} of {len(siblings)}."
    if how == "down" and i < len(siblings) - 1:
        siblings[i + 1], siblings[i] = siblings[i], siblings[i + 1]
        return f"{node.title} moved down, {i + 2} of {len(siblings)}."
    if how == "in" and i > 0:
        new_parent = siblings[i - 1]
        siblings.pop(i)
        new_parent.children.append(node)
        return f"{node.title} is now under {new_parent.title}."
    if how == "out" and owner is not None:
        outer, _ = _owner(nodes, owner)
        siblings.remove(node)
        outer.insert(outer.index(owner) + 1, node)
        return f"{node.title} moved out, after {owner.title}."
    return ""


def page_order_changes(nodes: list[PageNode]) -> list[tuple[PageNode, int, int]]:
    """``(page, parent, menu_order)`` for each page whose place changed."""
    changed: list[tuple[PageNode, int, int]] = []

    def visit(items: list[PageNode], parent: int) -> None:
        for order, node in enumerate(items):
            if (node.loaded_parent, node.loaded_order) != (parent, order):
                changed.append((node, parent, order))
            visit(node.children, node.id)

    visit(nodes, 0)
    return changed


def save_page_order(api: WordPressApi, nodes: list[PageNode]) -> int:
    changes = page_order_changes(nodes)
    if not changes:
        return 0
    api.batch([
        {
            "method": "POST",
            "path": f"/wp/v2/pages/{node.id}",
            "body": {"parent": parent, "menu_order": order},
        }
        for node, parent, order in changes
    ])
    for node, parent, order in changes:
        node.loaded_parent, node.loaded_order, node.parent, node.menu_order = (
            parent,
            order,
            parent,
            order,
        )
    return len(changes)


@dataclass(frozen=True)
class MapRow:
    depth: int
    text: str
    kind: str = ""  # "page", "post" or "" for a heading row
    item_id: int = 0
    link: str = ""


def site_map(
    pages: list[PageNode],
    posts: list[tuple[int, str, list[int], str]],
    categories: dict[int, str],
    in_menus: dict[int, list[str]],
) -> list[MapRow]:
    """Pages by parent, then posts under their categories (9.9).

    *posts* is ``(id, title, category ids, link)``; *in_menus* maps a page
    or post id to the menus that link to it.
    """
    out: list[MapRow] = [MapRow(0, f"Pages, {sum(1 for _ in walk_pages(pages))}")]
    for depth, node, _siblings in walk_pages(pages):
        menus = in_menus.get(node.id, [])
        where = f", in {', '.join(menus)}" if menus else ""
        status = "" if node.status == "publish" else f", {node.status}"
        out.append(MapRow(depth + 1, f"{node.title}{status}{where}", "page", node.id, node.link))
    by_category: dict[int, list[tuple[int, str, str]]] = {}
    for post_id, title, cats, link in posts:
        for cat in cats or [0]:
            by_category.setdefault(cat, []).append((post_id, title, link))
    out.append(MapRow(0, f"Posts, {len(posts)}"))
    for cat_id in sorted(by_category, key=lambda c: categories.get(c, "Uncategorised").lower()):
        items = by_category[cat_id]
        out.append(MapRow(1, f"{categories.get(cat_id, 'Uncategorised')}, {len(items)} posts"))
        for post_id, title, link in items:
            menus = in_menus.get(post_id, [])
            where = f", in {', '.join(menus)}" if menus else ""
            out.append(MapRow(2, f"{title}{where}", "post", post_id, link))
    return out


def load_posts_for_map(api: WordPressApi) -> list[tuple[int, str, list[int], str]]:
    params: dict[str, object] = {"status": "publish", "_fields": "id,title,categories,link"}
    return [
        (
            int(r.get("id", 0)),
            rendered(r.get("title")) or "(untitled)",
            [int(c) for c in r.get("categories", []) or []],
            str(r.get("link", "")),
        )
        for r in api.iter_collection("wp/v2/posts", params)
    ]


# --------------------------------------------------------------------------- #
# Templates and template parts (block themes; read-only)


@dataclass(frozen=True)
class Template:
    id: str
    slug: str
    title: str
    kind: str  # "template" or "part"
    area: str
    content: str


def list_templates(api: WordPressApi) -> list[Template]:
    out: list[Template] = []
    for route, kind in (("wp/v2/templates", "template"), ("wp/v2/template-parts", "part")):
        try:
            raw = api.get(route, context="edit")
        except WordPressApiError as exc:
            if exc.status in (404, 403, 401):
                continue
            raise
        for r in raw if isinstance(raw, list) else []:
            if not isinstance(r, dict):
                continue
            out.append(
                Template(
                    id=str(r.get("id", "")),
                    slug=str(r.get("slug", "")),
                    title=raw_text(r.get("title")) or str(r.get("slug", "")),
                    kind=kind,
                    area=str(r.get("area", "") or ""),
                    content=raw_text(r.get("content")),
                )
            )
    return out


def template_outline(templates: list[Template], *, first: str = "") -> str:
    """Each template and part with its blocks, indented by depth, *first* leading."""
    if not templates:
        return ""
    ordered = sorted(
        templates, key=lambda t: (t.slug != first, t.kind != "template", t.title.lower())
    )
    lines: list[str] = []
    for t in ordered:
        kind = "Template" if t.kind == "template" else f"Template part ({t.area or 'general'})"
        lines.append(f"{kind}: {t.title}")
        for depth, _path, block in bk.walk(bk.parse(t.content)):
            name = bk.describe(block)
            if block.name == "core/template-part":
                name = f"Template part: {block.attrs.get('slug', '')}"
            lines.append("    " * (depth + 1) + name)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
