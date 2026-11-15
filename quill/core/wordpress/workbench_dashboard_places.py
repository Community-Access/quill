"""The Dashboard, Site Editor and wp-admin map places: nodes, help and rows (9.18, 6, 7, 14).

Kept beside :mod:`quill.core.wordpress.workbench_tree`,
:mod:`quill.core.wordpress.workbench_actions` and
:mod:`quill.core.wordpress.workbench_node_help`, which splice these in, so
each stays inside its size budget (GATE-11):

- :data:`DASHBOARD_NODES`: Overview, and under it At a Glance, Activity and
  wp-admin Screens (:mod:`~quill.core.wordpress.workbench_dashboard`,
  :mod:`~quill.core.wordpress.workbench_admin_map`);
- :data:`SITE_EDITOR_NODES`: Templates, Template Parts and Additional CSS
  (:mod:`~quill.core.wordpress.workbench_site_editor`);
- :func:`dashboard_rows`: what those rows offer, and :data:`NODE_ROWS`,
  wp-admin for This Place on every node's context menu;
- :data:`KEYLESS`: why none of these has a chord (family rule 8).

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.tree import NodeSpec

__all__ = [
    "DASHBOARD_NODES",
    "DASHBOARD_NODE_HELP",
    "DASHBOARD_ROW_HELP",
    "KEYLESS",
    "NODE_ROWS",
    "MENU_ROWS",
    "SITE_EDITOR_NODES",
    "WIDGET_ROWS",
    "dashboard_rows",
]

_PREFIX = "wordpress.workbench."


def command(verb: str) -> str:
    return f"{_PREFIX}{verb}"


def _n(key: str, label: str, parent: str, **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, **kwargs)


DASHBOARD_NODES: tuple[NodeSpec, ...] = (
    _n(
        "overview",
        "Overview",
        "site",
        loader="site:overview",
        columns=("fact", "value"),
        row_type="fact",
    ),
    _n(
        "at_a_glance",
        "At a Glance",
        "overview",
        loader="dashboard:glance",
        columns=("fact", "value"),
        row_type="fact",
    ),
    _n(
        "activity",
        "Activity",
        "overview",
        loader="dashboard:activity",
        columns=("group", "title", "when"),
        row_type="item",
    ),
    _n(
        "admin_screens",
        "wp-admin Screens",
        "overview",
        loader="dashboard:screens",
        columns=("screen", "place", "reach"),
        row_type="admin_screen",
    ),
)

SITE_EDITOR_NODES: tuple[NodeSpec, ...] = (
    _n(
        "templates",
        "Templates",
        "appearance",
        loader="templates:wp_template",
        columns=("title", "source", "slug"),
        row_type="template",
    ),
    _n(
        "template_parts",
        "Template Parts",
        "appearance",
        loader="templates:wp_template_part",
        columns=("title", "source", "slug"),
        row_type="template",
    ),
    _n(
        "additional_css",
        "Additional CSS",
        "appearance",
        loader="site_editor:css",
        columns=("screen", "reach"),
        row_type="custom_css",
    ),
)

DASHBOARD_NODE_HELP: Mapping[str, str] = {
    "at_a_glance": (
        "wp-admin's At a Glance in sentences: posts, pages and comments by status, the "
        "people, WordPress's version and the theme, then a sentence for WooCommerce, The "
        "Events Calendar, Yoast SEO or Paid Memberships Pro where the site has them."
    ),
    "activity": (
        "wp-admin's Activity: publishing soon, recently published and recent comments, five "
        "of each. Enter opens a post in the editor."
    ),
    "admin_screens": (
        "Every wp-admin screen, the place in the Workbench nearest to it, and how much of it "
        "REST reaches. Enter opens the screen in your browser."
    ),
    "templates": (
        "The block theme's templates. Edit Block Markup, Earlier Versions, Reset to the "
        "Theme's Version and New Template are on each row's context menu."
    ),
    "template_parts": (
        "The block theme's template parts, such as the header and footer, edited like templates."
    ),
    "widgets": (
        "The classic theme's widget areas. Each row's context menu adds, changes, moves, "
        "removes and previews its widgets, of every kind the site has."
    ),
    "additional_css": (
        "The site's Additional CSS. In a block theme Edit Additional CSS changes it after a "
        "preview, and each save is kept in Previous Looks; a classic theme's opens the Customizer."
    ),
}

DASHBOARD_ROW_HELP: Mapping[str, str] = {
    "admin_screen": (
        "A wp-admin screen. Enter opens it in your browser after saying what REST cannot do "
        "there; Go to Its Place selects the nearest node in the Workbench."
    ),
    "custom_css": "The site's Additional CSS. Edit Additional CSS changes it, after a preview.",
    "template": (
        "A template or template part. Edit Block Markup changes it after a preview; Reset "
        "to the Theme's Version takes a customized one back to the theme's."
    ),
    "sidebar": (
        "A widget area and its widgets. Add, Change, Move and Remove a Widget are on the context "
        "menu, for every kind of widget the site has."
    ),
}


def _a(
    verb: str,
    label: str,
    help: str,  # noqa: A002 - field name
    *,
    tier: Tier = Tier.READ,
    needs: str = "",
    default: bool = False,
) -> ActionRow:
    return ActionRow(command(verb), label, tier, needs, help, default)


_THEME = "edit_theme_options"

TEMPLATE_ROWS: tuple[ActionRow, ...] = (
    _a(
        "edit_template",
        "Edit Block Markup...",
        "Change its block markup as text, then read the change line by line before it is "
        "sent. A theme's template becomes the site's own copy. Ctrl+Z puts it back.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "template_revisions",
        "Earlier Versions...",
        "The customized template's earlier versions; restore one after a preview. Ctrl+Z "
        "puts back the one replaced.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "reset_template",
        "Reset to the Theme's Version...",
        "Remove the site's customized copy, so the theme's own file applies again; a template "
        "the theme never had is deleted. Confirmed by name; Ctrl+Z brings the copy back.",
        tier=Tier.DESTRUCTIVE,
        needs=_THEME,
    ),
    _a(
        "new_template",
        "New Template...",
        "A new template or part by its name, such as single-post-news, starting from the "
        "template WordPress would use for it today. Ctrl+Z deletes it.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "open_site_editor",
        "Open in the Site Editor",
        "This template in wp-admin's Site Editor, in your browser, to lay it out by sight.",
    ),
)

CSS_ROWS: tuple[ActionRow, ...] = (
    _a(
        "edit_css",
        "Edit Additional CSS...",
        "The CSS as text; the change is read line by line before it is sent, and CSS changes "
        "every page. Kept in Previous Looks; Ctrl+Z puts it back.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
)

SCREEN_ROWS: tuple[ActionRow, ...] = (
    _a(
        "open_admin_screen",
        "Open in Dashboard",
        "Say what REST cannot do there, then open the screen in your browser. Enter.",
        default=True,
    ),
    _a(
        "go_to_place",
        "Go to Its Place in the Workbench",
        "Select the node nearest to this screen, where the Workbench does what REST allows.",
    ),
)

WIDGET_ROWS: tuple[ActionRow, ...] = (
    _a(
        "add_widget",
        "Add a Widget...",
        "Any kind of widget the site has, filled in on its own form, previewed as visitors "
        "will see it, then added to this area. Ctrl+Z removes it.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "change_widget",
        "Change a Widget...",
        "One of this area's widgets on its own form, or a block widget as text; previewed "
        "before it is sent. Ctrl+Z puts it back.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "move_widget",
        "Move a Widget...",
        "One of this area's widgets to another area. Ctrl+Z moves it back.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "remove_widget",
        "Remove a Widget...",
        "Into Inactive Widgets, where WordPress keeps it; after you confirm. Ctrl+Z brings it "
        "back.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "preview_widgets",
        "Preview Widgets",
        "Every widget in this area as a visitor sees it, in words.",
    ),
)

MENU_ROWS: tuple[ActionRow, ...] = (
    _a(
        "add_menu_item",
        "Add Menu Item...",
        "A page, post, category, tag, custom link or item of any other type, found by search "
        "or from the whole list, placed under any item and after any other, then previewed. "
        "Ctrl+N with a menu selected does it too. Ctrl+Z takes it out again.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "menu_auto_add",
        "Add New Pages Automatically...",
        "Turn on or off WordPress adding each new top-level page to this menu, after a "
        "preview of the state it is in now. Also a check box on the menu's Properties. "
        "Ctrl+Z turns it back.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "arrange_menu_items",
        "Arrange Items...",
        "The menu's items in the Menus window, where each moves up, down, in under the one "
        "above or out a level, and is renamed or removed. Each change is sent when you make it.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "menu_versions",
        "Earlier Versions...",
        "The menu as QUILL saw it before: bring back the items since removed, after a "
        "preview. Ctrl+Z takes them out again.",
        tier=Tier.WRITE,
        needs=_THEME,
    ),
    _a(
        "default_navigation",
        "Default Navigation Menu...",
        "Which Navigation menu a block theme shows where none is chosen. On a site with none, "
        "WordPress makes one, so this asks first.",
        needs=_THEME,
    ),
)

NODE_ROWS: tuple[ActionRow, ...] = (
    _a(
        "admin_here",
        "wp-admin for This Place...",
        "The wp-admin screens nearest to this node, for what REST cannot do here; the chosen "
        "one opens in your browser after its reason is said.",
    ),
)


def dashboard_rows(read: ActionRow, sheet: ActionRow) -> Mapping[str, tuple[ActionRow, ...]]:
    """The menus of templates, Additional CSS and wp-admin screens, given Read and Properties."""
    read_too = _a("read", "Read in Full", "Move to the details pane to read it.")
    return {
        "template": (read, *TEMPLATE_ROWS, sheet),
        "custom_css": (read, *CSS_ROWS, sheet),
        "admin_screen": (*SCREEN_ROWS, read_too, sheet),
        "sidebar": (read, *WIDGET_ROWS, sheet),
    }


KEYLESS: dict[str, str] = {
    command("edit_template"): "Templates change a few times a site's life (rule 9).",
    command("template_revisions"): "Looked for after a mistake, rarely (rule 9).",
    command("reset_template"): "Removes the site's copy: never a bare key (rules 4 and 9).",
    command("new_template"): "A new template is made a few times a site's life (rule 9).",
    command("open_site_editor"): "Leaves QUILL for the browser, now and then (rule 9).",
    command("edit_css"): "Additional CSS changes a few times a site's life (rule 9).",
    command("open_admin_screen"): "Enter does it on a wp-admin Screens row.",
    command("go_to_place"): "The tree is a keystroke away; this is a shortcut to it (rule 9).",
    command("admin_here"): "Leaves QUILL for wp-admin, only for what REST cannot do (rule 9).",
    command("add_widget"): "Widgets are added a few times a site's life (rule 9).",
    command("change_widget"): "Widgets change a few times a site's life (rule 9).",
    command("move_widget"): "Rare rearranging of widget areas (rule 9).",
    command("remove_widget"): "Rare, and it takes a widget off every page (rules 4 and 9).",
    command(
        "preview_widgets"
    ): "Read Widgets does it now and then, from the context menu (rule 9).",
    command("add_menu_item"): "Ctrl+N does it with a menu selected, through New Here (rule 5).",
    command("arrange_menu_items"): "Opens the Menus window for a reshuffle, now and then (rule 9).",
    command("menu_auto_add"): "Set once per menu; also a check box on Properties (rule 9).",
    command("menu_versions"): "Looked for after a mistake, rarely (rule 9).",
    command("default_navigation"): "Asked once when setting up a block theme (rule 9).",
}
"""Why each command here has no chord (family rule 8)."""
