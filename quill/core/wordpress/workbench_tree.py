"""The WordPress Workbench's Navigator tree, as data (WordPress PRD section 5).

One :class:`~quill.core.workbench.tree.NodeSpec` per node, in the order the
tree shows them. Every connected site gets the same children, so those are
the ``site`` template; each site's own post types and taxonomies are
*dynamic* nodes, one copy per thing the site describes (section 12), so a
plugin's Events or Products appear with no QUILL release.

Loaders are named, never imported, by prefix; the window maps each to an
existing :mod:`quill.core.wordpress` call or REST route
(:mod:`quill.core.wordpress.workbench_load`):

- ``attention:<what>`` gathers one thing across every connected site;
- ``items:<kind>`` is a post type's items, narrowed by the node's ``status`` preset;
- ``media:``, ``comments:``, ``terms:``, ``menus:``, ``themes:``,
  ``templates:``, ``patterns:``, ``fonts:``, ``widgets:``, ``forms:``,
  ``users:``, ``app_passwords:``, ``plugins:``, ``settings:``, ``health:``,
  ``abilities:``, ``routes:`` and ``site:`` name the site's own collections;
- ``sites:list`` lists the connected sites and ``help:<what>`` the help.

A node with no loader is a folder whose list is its children; a node whose
loader starts ``planned:`` is shown with what it will hold and where that
lives today, so nothing seems to vanish (GitHub PRD 3.3 and 9).
"""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.workbench_dashboard_places import DASHBOARD_NODES, SITE_EDITOR_NODES
from quill.core.wordpress.workbench_gravity_actions import GRAVITY_NODES
from quill.core.wordpress.workbench_node_help import PLANNED_WORDS
from quill.core.wordpress.workbench_places import (
    ACROSS_NODES,
    BY_NAME_NODES,
    HOUSEKEEPING,
    SWEEP_NODES,
)
from quill.core.wordpress.workbench_pmpro_tree import HEALTH_NODES, MEMBERSHIP_NODES
from quill.core.wordpress.workbench_shop import SHOP_NODES
from quill.core.workbench.tree import NodeSpec, Scope, TreeSpec

__all__ = [
    "DYNAMIC_NAMESPACE",
    "DYNAMIC_TAXONOMY",
    "GROUPED",
    "DYNAMIC_TYPE",
    "PLANNED_WORDS",
    "START_NODE",
    "WORDPRESS_TREE",
    "door_node",
]

START_NODE = "start"
DYNAMIC_TYPE = "custom_type"
DYNAMIC_TAXONOMY = "custom_taxonomy"
DYNAMIC_NAMESPACE = "more_namespace"

_TOPIC = ("title", "says")
_ITEM_COLUMNS = ("title", "status", "author", "modified")
_POST_STATUSES = (
    ("published", "Published", "publish"),
    ("drafts", "Drafts", "draft"),
    ("pending", "Pending", "pending"),
    ("scheduled", "Scheduled", "future"),
    ("private", "Private", "private"),
    ("trash", "Trash", "trash"),
)


def _n(key: str, label: str, parent: str | None = None, **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, **kwargs)


def _statuses(parent: str, kind: str) -> tuple[NodeSpec, ...]:
    return tuple(
        _n(
            f"{parent}_{key}",
            label,
            parent,
            loader=f"items:{kind}",
            preset=(("status", status),),
            columns=_ITEM_COLUMNS,
            row_type="item",
            home=False,
        )
        for key, label, status in _POST_STATUSES
    )


def _group(
    parent: str, loader: str, columns: tuple[str, ...], row_type: str, **kw: Any
) -> NodeSpec:
    """The node View > Group By fills with one child per value (none until grouped)."""
    return _n(
        f"{parent}_group",
        "Group",
        parent,
        loader=loader,
        columns=columns,
        row_type=row_type,
        home=False,
        dynamic=True,
        **kw,
    )


GROUPED = ("posts", "pages", "media", "comments", "plugins")
"""The nodes Group By can group: each has a ``<key>_group`` dynamic child."""

_ATTENTION = Scope.ACCOUNT

_FIXED: tuple[NodeSpec, ...] = (
    _n(START_NODE, "Start Here"),
    _n("attention", "Needs My Attention", scope=_ATTENTION),
    _n(
        "inbox",
        "Inbox",
        "attention",
        loader="attention:inbox",
        columns=("what", "site", "when"),
        row_type="mixed",
    ),
    _n(
        "waiting",
        "Comments Waiting",
        "attention",
        loader="attention:waiting",
        columns=("author", "on", "site", "when"),
        row_type="comment",
    ),
    _n(
        "pending_review",
        "Pending Review",
        "attention",
        loader="attention:pending",
        columns=("title", "site", "author", "queue", "modified"),
        row_type="item",
    ),
    _n(
        "scheduled",
        "Scheduled",
        "attention",
        loader="attention:scheduled",
        columns=("title", "site", "date"),
        row_type="item",
    ),
    _n(
        "my_drafts",
        "Drafts",
        "attention",
        loader="attention:drafts",
        columns=("title", "site", "modified"),
        row_type="item",
    ),
    _n(
        "updates",
        "Updates",
        "attention",
        loader="attention:updates",
        columns=("what", "site", "installed", "update"),
        row_type="update",
    ),
    _n(
        "health_problems",
        "Site Health",
        "attention",
        loader="attention:health",
        columns=("problem", "site", "status"),
        row_type="problem",
    ),
    _n(
        "accessibility",
        "Accessibility",
        "attention",
        loader="attention:accessibility",
        columns=("title", "site", "alt_text", "uploaded"),
        row_type="media",
    ),
    _n(
        "broken_links",
        "Broken Links",
        "attention",
        loader="attention:broken_links",
        columns=("problem", "test", "site", "target", "status"),
        row_type="problem",
    ),
    _n(
        "held_as_spam",
        "Held as Spam",
        "attention",
        loader="attention:spam",
        columns=("what", "site", "from", "when"),
        row_type="mixed",
    ),
    _n(
        "form_responses",
        "Form Responses",
        "attention",
        loader="attention:responses",
        columns=("form", "site", "status", "when"),
        row_type="form_entry",
    ),
    _n(
        "orders",
        "Membership Orders",
        "attention",
        loader="attention:orders",
        columns=("what", "site", "status", "total", "date"),
        row_type="pmpro",
    ),
    _n(
        "watches",
        "Watches",
        "attention",
        loader="watches:kinds",
        columns=("watch", "state"),
        row_type="fact",
    ),
    _n(
        "sites",
        "Sites",
        loader="sites:list",
        columns=("site", "address", "role"),
        row_type="site",
        template="site",
    ),
    _n(
        "calendar",
        "Calendar",
        loader="calendar:days",
        columns=("day", "scheduled", "published"),
        row_type="day",
    ),
    _n(
        "calendar_day",
        "Day",
        "calendar",
        loader="calendar:day",
        columns=("title", "site", "status", "date"),
        row_type="item",
        dynamic=True,
    ),
    *ACROSS_NODES,
    _n(
        "search",
        "Search",
        loader="search:all",
        columns=("title", "type", "site", "address"),
        row_type="search_result",
    ),
    _n(
        "practice",
        "Practice Site",
        loader="practice:status",
        columns=("fact", "value"),
        row_type="fact",
    ),
    _n("help", "Help and Learning"),
    _n("how_it_thinks", "How WordPress Thinks", "help"),
    _n("words", "Words", "help", loader="help:words", columns=("word", "meaning"), row_type="help"),
    _n("keys", "Keys", "help", loader="help:keys", columns=("key", "does"), row_type="help"),
    # Do Something, The Guide, What Changed and Ask a Person, as GitHub's has (WP-R-046).
    *(
        _n(key, label, "help", loader=f"help:{view}", columns=_TOPIC, row_type="help_topic")
        for key, label, view in (
            ("help_tasks", "Do Something", "tasks"),
            ("help_guide", "The Guide", "guide"),
            ("help_changes", "What Changed", "changes"),
            ("help_ask", "Ask a Person", "ask"),
        )
    ),
)

_SITE: tuple[NodeSpec, ...] = (
    _n("site", "Site", scope=Scope.ORGANIZATION),
    *DASHBOARD_NODES,  # Overview, At a Glance, Activity, wp-admin Screens
    _n(
        "posts",
        "Posts",
        "site",
        loader="items:post",
        preset=(("status", "any"),),
        columns=_ITEM_COLUMNS,
        row_type="item",
    ),
    *_statuses("posts", "post"),
    _group("posts", "items:post", _ITEM_COLUMNS, "item", preset=(("status", "any"),)),
    _n(
        "pages",
        "Pages",
        "site",
        loader="items:page",
        preset=(("status", "any"), ("tree", "parent")),
        columns=("title", "level", "status", "modified"),
        row_type="item",
    ),
    *_statuses("pages", "page"),
    _group("pages", "items:page", _ITEM_COLUMNS, "item", preset=(("status", "any"),)),
    _n(
        "content_types",
        "More Content Types",
        "site",
        loader="types:list",
        columns=("type", "route", "taxonomies"),
        row_type="writing_type",
    ),
    _n(
        DYNAMIC_TYPE,
        "Content Type",
        "content_types",
        loader="items:custom",
        preset=(("status", "any"),),
        columns=_ITEM_COLUMNS,
        row_type="item",
        dynamic=True,
    ),
    _n(
        "media",
        "Media",
        "site",
        loader="media:all",
        columns=("title", "type", "alt_text", "uploaded"),
        row_type="media",
    ),
    *(
        _n(
            f"media_{key}",
            label,
            "media",
            loader=f"media:{key}",
            columns=("title", "type", "alt_text", "uploaded"),
            row_type="media",
            home=False,
        )
        for key, label in (
            ("pictures", "Pictures"),
            ("audio", "Audio"),
            ("video", "Video"),
            ("documents", "Documents"),
            ("unattached", "Unattached"),
            ("no_alt", "Without Alt Text"),
        )
    ),
    _group("media", "media:all", ("title", "type", "alt_text", "uploaded"), "media"),
    HOUSEKEEPING,
    _n(
        "comments",
        "Comments",
        "site",
        loader="comments:all",
        columns=("author", "on", "status", "when"),
        row_type="comment",
    ),
    *(
        _n(
            f"comments_{key}",
            label,
            "comments",
            loader=f"comments:{status}",
            columns=("author", "on", "status", "when"),
            row_type="comment",
            home=False,
        )
        for key, label, status in (
            ("waiting", "Waiting", "hold"),
            ("approved", "Approved", "approve"),
            ("spam", "Spam", "spam"),
            ("trash", "Trash", "trash"),
        )
    ),
    _group("comments", "comments:all", ("author", "on", "status", "when"), "comment"),
    _n(
        "categories",
        "Categories",
        "site",
        loader="terms:category",
        columns=("name", "level", "count", "slug"),
        row_type="term",
    ),
    _n(
        "tags",
        "Tags",
        "site",
        loader="terms:post_tag",
        columns=("name", "count", "slug"),
        row_type="term",
    ),
    _n(
        "taxonomies",
        "More Taxonomies",
        "site",
        loader="taxonomies:list",
        columns=("taxonomy", "route", "types"),
        row_type="taxonomy",
    ),
    _n(
        DYNAMIC_TAXONOMY,
        "Taxonomy",
        "taxonomies",
        loader="terms:custom",
        columns=("name", "level", "count", "slug"),
        row_type="term",
        dynamic=True,
    ),
    _n(
        "menus",
        "Menus and Navigation",
        "site",
        loader="menus:all",
        columns=("menu", "locations", "items"),
        row_type="menu",
    ),
    _n("appearance", "Appearance", "site"),
    _n(
        "themes",
        "Themes",
        "appearance",
        loader="themes:all",
        columns=("theme", "version", "status"),
        row_type="theme",
    ),
    _n(
        "global_styles",
        "Global Styles",
        "appearance",
        loader="global_styles:all",
        columns=("setting", "kind", "value", "contrast"),
        row_type="global_style",
    ),
    *SITE_EDITOR_NODES,  # Templates, Template Parts, Additional CSS
    _n(
        "patterns",
        "Patterns",
        "appearance",
        loader="patterns:wp_block",
        columns=("title", "status", "modified"),
        row_type="pattern",
    ),
    _n(
        "fonts",
        "Fonts",
        "appearance",
        loader="fonts:all",
        columns=("family", "slug"),
        row_type="font",
    ),
    _n(
        "widgets",
        "Widgets and Sidebars",
        "appearance",
        loader="widgets:sidebars",
        columns=("sidebar", "widgets", "status"),
        row_type="sidebar",
    ),
    _n(
        "forms",
        "Forms",
        "site",
        loader="forms:all",
        columns=("form", "plugin", "entries", "status"),
        row_type="form",
    ),
    *MEMBERSHIP_NODES,
    _n(
        "form_entries",
        "Responses",
        "forms",
        loader="forms:entries",
        columns=("form", "plugin", "status", "when"),
        row_type="form_entry",
    ),
    _n(
        "form_spam",
        "Held as Spam",
        "forms",
        loader="forms:spam",
        columns=("form", "plugin", "status", "when"),
        row_type="form_entry",
        home=False,
    ),
    *GRAVITY_NODES,
    *SHOP_NODES,  # Shop, Shop Orders (WooCommerce) and Podcast
    _n("people", "People", "site"),
    _n(
        "users",
        "Users",
        "people",
        loader="users:all",
        columns=("name", "username", "role", "email"),
        row_type="user",
    ),
    _n(
        "app_passwords",
        "Application Passwords",
        "people",
        loader="app_passwords:me",
        columns=("name", "created", "last_used"),
        row_type="app_password",
    ),
    _n(
        "plugins",
        "Plugins",
        "site",
        loader="plugins:all",
        columns=("plugin", "version", "status", "author"),
        row_type="plugin",
    ),
    _group("plugins", "plugins:all", ("plugin", "version", "status", "author"), "plugin"),
    _n(
        "settings",
        "Settings",
        "site",
        loader="settings:all",
        columns=("setting", "value"),
        row_type="setting",
    ),
    _n(
        "site_health",
        "Site Health",
        "site",
        loader="health:tests",
        columns=("test", "status", "says"),
        row_type="problem",
    ),
    *HEALTH_NODES,
    _n(
        "abilities",
        "Abilities",
        "site",
        loader="abilities:all",
        columns=("ability", "plugin", "category", "says"),
        row_type="ability",
    ),
    *BY_NAME_NODES,
    *SWEEP_NODES,
    _n(
        "content_model",
        "Content Model",
        "site",
        loader="model:all",
        columns=("name", "kind", "registered_by", "definition", "in_rest"),
        row_type="model",
    ),
    _n(
        "more",
        "More from This Site",
        "site",
        loader="routes:namespaces",
        columns=("namespace", "routes", "reached"),
        row_type="namespace",
    ),
    _n(
        DYNAMIC_NAMESPACE,
        "Namespace",
        "more",
        loader="routes:namespace",
        columns=("route", "methods", "coverage"),
        row_type="route",
        dynamic=True,
    ),
)

WORDPRESS_TREE = TreeSpec(_FIXED, {"site": _SITE})
"""The whole tree: the fixed nodes and the ``site`` template every site gets."""

#: The node each Tools > WordPress door opens, by QUILL command id (PRD 14).
_DOORS: dict[str, str] = {
    "wordpress.comments": "comments_waiting",
    "wordpress.media_library": "media",
    "wordpress.manage_terms": "categories",
    "wordpress.menus": "menus",
    "wordpress.site_check": "site_health",
    "wordpress.site_settings": "settings",
    "wordpress.site_map": "pages",
    "wordpress.users": "users",
    "wordpress.app_passwords": "app_passwords",
    "wordpress.plugins": "plugins",
    "wordpress.themes": "themes",
    "wordpress.fonts": "fonts",
    "wordpress.synced_patterns": "patterns",
    "wordpress.widgets": "widgets",
    "wordpress.abilities": "abilities",
}


def door_node(command_id: str) -> str:
    """The ``site`` template node a door opens ("" when it has none)."""
    return _DOORS.get(command_id, "")
