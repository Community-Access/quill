"""Every wp-admin screen, and its place in the Workbench (wordpress.md 9.18, package 14).

wp-admin is a set of screens; the Workbench is a tree. :data:`ADMIN_MAP` is
the whole correspondence, one :class:`AdminScreen` a screen: its exact
address under the site, WordPress's own name for it, the **nearest
Workbench node**, and how much of it REST reaches:

- ``workbench``: everything the screen does is done in that node;
- ``both``: the node does what REST allows, and the rest of the screen
  (named in ``says``) is only in wp-admin;
- ``dashboard``: REST has no route for the screen at all.

Sites > site > Overview > wp-admin Screens lists every screen the site has
(a plugin's screens only where its namespace is in the REST index), and
**wp-admin for This Place** on any node's context menu opens the screens
whose nearest node it is, so a job REST cannot do is reachable from where
somebody looks for it, with the reason said before the browser opens.

Wx-free and network-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from quill.core.wordpress.workbench_admin_map_plugins import PLUGIN_SCREENS
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "ADMIN_MAP",
    "AdminScreen",
    "REST_WORDS",
    "map_rows",
    "screen_link",
    "screens_for",
]

REST_WORDS: Mapping[str, str] = {
    "workbench": "All of it in the Workbench",
    "both": "Part in the Workbench, the rest in wp-admin",
    "dashboard": "Only in wp-admin",
}


@dataclass(frozen=True)
class AdminScreen:
    """One wp-admin screen and the Workbench node nearest to it."""

    key: str
    path: str
    name: str
    node: str
    rest: str
    says: str
    namespace: str = ""

    @property
    def rest_words(self) -> str:
        return REST_WORDS[self.rest]


def _s(
    key: str, path: str, name: str, node: str, rest: str, says: str, namespace: str = ""
) -> AdminScreen:
    return AdminScreen(key, f"wp-admin/{path}", name, node, rest, says, namespace)


ADMIN_MAP: tuple[AdminScreen, ...] = (
    _s(
        "home",
        "index.php",
        "Dashboard > Home",
        "overview",
        "both",
        "At a Glance and Activity are in Overview. WordPress Events and News come from "
        "WordPress.org, not the site, so they are only in wp-admin.",
    ),
    _s(
        "updates",
        "update-core.php",
        "Dashboard > Updates",
        "overview",
        "dashboard",
        "WordPress's REST API cannot update WordPress, its translations, a plugin or a theme.",
    ),
    _s(
        "posts",
        "edit.php",
        "Posts > All Posts",
        "posts",
        "workbench",
        "Lists, filters, counts, Quick Edit, Trash and Delete Permanently are in Posts.",
    ),
    _s(
        "new_post",
        "post-new.php",
        "Posts > Add New Post",
        "posts",
        "workbench",
        "New Here (Ctrl+N) on Posts makes a draft; writing is in the editor.",
    ),
    _s(
        "categories",
        "edit-tags.php?taxonomy=category",
        "Posts > Categories",
        "categories",
        "workbench",
        "Add, rename, merge, convert and delete are in Categories.",
    ),
    _s(
        "tags",
        "edit-tags.php?taxonomy=post_tag",
        "Posts > Tags",
        "tags",
        "workbench",
        "Add, rename, merge, convert and delete are in Tags.",
    ),
    _s(
        "media",
        "upload.php",
        "Media > Library",
        "media",
        "workbench",
        "Browse, details, alt text, edit, attach, detach and download are in Media.",
    ),
    _s(
        "media_new",
        "media-new.php",
        "Media > Add New Media File",
        "media",
        "workbench",
        "New Here (Ctrl+N) on Media uploads a file.",
    ),
    _s(
        "media_settings",
        "options-media.php",
        "Settings > Media",
        "media",
        "dashboard",
        "Image sizes and the upload folders are not in WordPress's REST settings.",
    ),
    _s(
        "pages",
        "edit.php?post_type=page",
        "Pages > All Pages",
        "pages",
        "workbench",
        "Lists, the page tree, counts and Trash are in Pages.",
    ),
    _s(
        "comments",
        "edit-comments.php",
        "Comments",
        "comments",
        "workbench",
        "Moderation, replies, Trash and spam are in Comments.",
    ),
    _s(
        "discussion",
        "options-discussion.php",
        "Settings > Discussion",
        "comments",
        "both",
        "The comment and pingback defaults are in Settings; moderation lists, avatars, "
        "threading and notification emails are not in REST.",
    ),
    _s(
        "themes",
        "themes.php",
        "Appearance > Themes",
        "themes",
        "both",
        "Themes lists them; WordPress's REST API only reads themes, so activating, live "
        "preview, updating and deleting are in wp-admin.",
    ),
    _s(
        "theme_install",
        "theme-install.php",
        "Appearance > Themes > Add New Theme",
        "themes",
        "dashboard",
        "WordPress's REST API cannot install a theme.",
    ),
    _s(
        "site_editor",
        "site-editor.php",
        "Appearance > Editor",
        "templates",
        "both",
        "Templates, Template Parts, Global Styles, Additional CSS, Patterns, Fonts and "
        "Navigation are in Appearance; laying blocks out by sight is in the Site Editor.",
    ),
    _s(
        "styles",
        "site-editor.php?p=%2Fstyles",
        "Appearance > Editor > Styles",
        "global_styles",
        "workbench",
        "Colours, font sizes and variations are in Global Styles.",
    ),
    _s(
        "customize",
        "customize.php",
        "Appearance > Customize",
        "themes",
        "both",
        "Logo, icon, title, tagline and homepage are in Settings; a classic theme's background, "
        "header and theme options are not in REST.",
    ),
    _s(
        "custom_css",
        "customize.php?autofocus%5Bsection%5D=custom_css",
        "Appearance > Customize > Additional CSS",
        "additional_css",
        "both",
        "A block theme's Additional CSS is in Additional CSS; a classic theme keeps it in the "
        "Customizer, which REST does not reach.",
    ),
    _s(
        "widgets",
        "widgets.php",
        "Appearance > Widgets",
        "widgets",
        "workbench",
        "Sidebars and their widgets are in Widgets and Sidebars.",
    ),
    _s(
        "menus",
        "nav-menus.php",
        "Appearance > Menus",
        "menus",
        "workbench",
        "Menus, their items and locations are in Menus and Navigation.",
    ),
    _s(
        "theme_editor",
        "theme-editor.php",
        "Tools > Theme File Editor",
        "themes",
        "dashboard",
        "No REST route edits theme files, and many hosts turn this screen off.",
    ),
    _s(
        "plugins",
        "plugins.php",
        "Plugins > Installed Plugins",
        "plugins",
        "both",
        "Activate, deactivate, install and delete are in Plugins; updates and automatic "
        "updates are not in REST.",
    ),
    _s(
        "plugin_install",
        "plugin-install.php",
        "Plugins > Add New Plugin",
        "plugins",
        "workbench",
        "Find a Plugin on WordPress.org installs one, after a preview.",
    ),
    _s(
        "plugin_editor",
        "plugin-editor.php",
        "Tools > Plugin File Editor",
        "plugins",
        "dashboard",
        "No REST route edits plugin files, and many hosts turn this screen off.",
    ),
    _s(
        "users",
        "users.php",
        "Users > All Users",
        "users",
        "workbench",
        "People, roles, removing and application passwords are in Users.",
    ),
    _s(
        "user_new",
        "user-new.php",
        "Users > Add New User",
        "users",
        "workbench",
        "New Here (Ctrl+N) on Users adds a person.",
    ),
    _s(
        "profile",
        "profile.php",
        "Users > Profile",
        "app_passwords",
        "both",
        "Application passwords are in People; the colour scheme, toolbar, keyboard shortcuts "
        "and Log Out Everywhere Else are only in wp-admin.",
    ),
    _s(
        "tools",
        "tools.php",
        "Tools > Available Tools",
        "more",
        "dashboard",
        "The categories and tags converter and Press This are not in REST.",
    ),
    _s(
        "import",
        "import.php",
        "Tools > Import",
        "posts",
        "dashboard",
        "Importers are not in REST; Send a Folder as Drafts, in the editor, sends files.",
    ),
    _s(
        "export",
        "export.php",
        "Tools > Export",
        "posts",
        "dashboard",
        "The WXR export is not in REST; Download My Writing, in the editor, saves posts.",
    ),
    _s(
        "site_health",
        "site-health.php",
        "Tools > Site Health > Status",
        "site_health",
        "workbench",
        "Every test the site offers over REST runs in Site Health.",
    ),
    _s(
        "site_health_info",
        "site-health.php?tab=debug",
        "Tools > Site Health > Info",
        "site_health_info",
        "dashboard",
        "The server, database and constants have no REST route.",
    ),
    _s(
        "export_personal",
        "export-personal-data.php",
        "Tools > Export Personal Data",
        "privacy_requests",
        "dashboard",
        "Privacy requests have no REST route.",
    ),
    _s(
        "erase_personal",
        "erase-personal-data.php",
        "Tools > Erase Personal Data",
        "privacy_requests",
        "dashboard",
        "Privacy requests have no REST route.",
    ),
    _s(
        "general",
        "options-general.php",
        "Settings > General",
        "settings",
        "both",
        "Title, tagline, email, language, time zone and formats are in Settings; who may "
        "register, the default role and the WordPress and site addresses are only in wp-admin. "
        "QUILL never changes the addresses: a typo locks the owner out.",
    ),
    _s(
        "writing",
        "options-writing.php",
        "Settings > Writing",
        "settings",
        "both",
        "The default category and format are in Settings; post by email and update services "
        "are not in REST.",
    ),
    _s(
        "reading",
        "options-reading.php",
        "Settings > Reading",
        "settings",
        "both",
        "The homepage and posts per page are in Settings; feeds and search engine visibility "
        "are not in REST.",
    ),
    _s(
        "permalinks",
        "options-permalink.php",
        "Settings > Permalinks",
        "settings",
        "dashboard",
        "The permalink structure is not in REST.",
    ),
    _s(
        "privacy",
        "options-privacy.php",
        "Settings > Privacy",
        "settings",
        "dashboard",
        "The privacy policy page is not in REST.",
    ),
    _s(
        "network",
        "network/",
        "Network Admin",
        "overview",
        "dashboard",
        "Only on a multisite network, and only for a Super Admin; REST has no network routes.",
    ),
    *(_s(*row) for row in PLUGIN_SCREENS),
)
"""Every wp-admin screen QUILL knows, in wp-admin's own menu order, then each plugin's."""


def _offered(screen: AdminScreen, namespaces: Iterable[str]) -> bool:
    if not screen.namespace:
        return True
    return screen.namespace in {n.strip("/") for n in namespaces}


def screen_link(site_url: str, screen: AdminScreen) -> str:
    """The screen's full address on the site ("" when the site's address is unknown)."""
    base = (site_url or "").rstrip("/")
    return f"{base}/{screen.path}" if base else ""


def screens_for(node: str, namespaces: Iterable[str] = ()) -> list[AdminScreen]:
    """The screens whose nearest node is *node*, or its parent for a status or group child."""
    offered = [s for s in ADMIN_MAP if _offered(s, list(namespaces))]
    found = [s for s in offered if s.node == node]
    if not found and "_" in node:
        parent = node.rsplit("_", 1)[0]
        found = [s for s in offered if s.node == parent]
    return found


def map_rows(
    site: str, site_url: str, namespaces: Sequence[str], places: Mapping[str, str]
) -> list[WbRow]:
    """One row a screen this site has; *places* names each node as the tree shows it."""
    rows: list[WbRow] = []
    for screen in ADMIN_MAP:
        if not _offered(screen, namespaces):
            continue
        link = screen_link(site_url, screen)
        place = places.get(screen.node, screen.node)
        rows.append(
            WbRow(
                "admin_screen",
                site,
                screen.key,
                {
                    "screen": screen.name,
                    "place": place,
                    "reach": screen.rest_words,
                    "address": screen.path,
                },
                f"{screen.name}, {screen.path}. {screen.rest_words}. {screen.says} "
                f"Nearest place in the Workbench: {place}. Enter opens it in your browser.",
                link=link,
                status=screen.rest,
                raw={"node": screen.node, "why": screen.says, "name": screen.name},
            )
        )
    return rows
