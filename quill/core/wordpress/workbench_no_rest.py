"""What WordPress's REST API cannot do, and the wp-admin screen that can (complete.md 10B.3).

WordPress's REST API stops short of the jobs people most often open wp-admin
for, and the Workbench says so **in the row, before anyone acts**, rather
than offering a command that fails:

- ``wp/v2/plugins`` installs, activates, deactivates and deletes a plugin.
  It cannot update one, and it cannot turn automatic updates on or off.
- ``wp/v2/themes`` only reads. It cannot activate, install, update or delete
  a theme, nor turn its automatic updates on.
- WordPress itself, and its translations, have no route at all.
- Site Health's Info tab (server, database, constants) has no route; only
  the tests and the directory sizes do.

Each job has an exact wp-admin address (:data:`ADMIN_SCREENS`), which the
Workbench opens in the browser (Open in Dashboard). Jetpack's ``jetpack/v4``
namespace can update plugins on a site connected to WordPress.com; that is
planned with the Jetpack node and not used here, so no row claims it.

Wx-free and network-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

__all__ = [
    "ADMIN_SCREENS",
    "AdminScreen",
    "PLUGIN_RECOVERY",
    "REST_CANNOT",
    "admin_link",
    "across_note",
    "screen_for_row",
]


@dataclass(frozen=True)
class AdminScreen:
    """A wp-admin screen: its path from the site's address, its name, and why it is needed."""

    path: str
    name: str
    why: str


ADMIN_SCREENS: Mapping[str, AdminScreen] = {
    "updates": AdminScreen(
        "wp-admin/update-core.php",
        "Dashboard > Updates",
        "WordPress's REST API cannot update WordPress, its translations, a plugin or a theme.",
    ),
    "plugin_auto_updates": AdminScreen(
        "wp-admin/plugins.php",
        "Plugins",
        "WordPress's REST API cannot update a plugin or turn its automatic updates on or off.",
    ),
    "theme_activate": AdminScreen(
        "wp-admin/themes.php",
        "Appearance > Themes",
        "WordPress's REST API only reads themes: it cannot activate, update or delete one, "
        "or turn its automatic updates on.",
    ),
    "theme_install": AdminScreen(
        "wp-admin/theme-install.php",
        "Appearance > Themes > Add New",
        "WordPress's REST API cannot install a theme.",
    ),
    "site_health_info": AdminScreen(
        "wp-admin/site-health.php?tab=debug",
        "Tools > Site Health > Info",
        "The Info tab (server, PHP, database and constants) has no REST route.",
    ),
    "language": AdminScreen(
        "wp-admin/options-general.php",
        "Settings > General > Site Language",
        "WordPress's REST API cannot install or update a language pack.",
    ),
    "pmpro_discount_codes": AdminScreen(
        "wp-admin/admin.php?page=pmpro-discountcodes",
        "Memberships > Discount Codes",
        "Paid Memberships Pro's REST routes read one discount code at a time, by its code.",
    ),
}

REST_CANNOT = (
    "WordPress's REST API: wp/v2/plugins installs, activates, deactivates and deletes; "
    "wp/v2/themes only reads; WordPress and translation updates have no route."
)
"""The sentence the Updates node, the coverage ledger and the docs share."""

PLUGIN_RECOVERY = (
    "There is no rollback: WordPress's REST API cannot put a plugin back to an earlier "
    "version. If it causes trouble, deactivating or deleting it are the only recovery here; "
    "an earlier version comes back only from the site's own backup or an upload in wp-admin."
)
"""Said in every preview that installs a plugin (WP-G), beside the update limit."""


def admin_link(site_url: str, key: str, **query: str) -> str:
    """The full address of *key*'s screen on the site ("" when the site's address is unknown)."""
    base = (site_url or "").rstrip("/")
    screen = ADMIN_SCREENS.get(key)
    if not base or screen is None:
        return ""
    link = f"{base}/{screen.path}"
    if query:
        link += ("&" if "?" in link else "?") + urlencode(query)
    return link


#: Which screen Open in Dashboard opens for a row, by row kind (and Across Sites kind).
_ROW_SCREENS: Mapping[str, str] = {
    "plugin": "plugin_auto_updates",
    "theme": "theme_activate",
    "update": "updates",
    "across:plugins": "plugin_auto_updates",
    "across:themes": "theme_activate",
}


def screen_for_row(kind: str, subkind: str = "") -> str:
    """The :data:`ADMIN_SCREENS` key for a row ("" when it has none)."""
    return _ROW_SCREENS.get(f"{kind}:{subkind}") or _ROW_SCREENS.get(kind, "")


def across_note(kind: str) -> str:
    """What Across Sites can and cannot do everywhere for *kind*, said in the row."""
    if kind == "plugins":
        return (
            " Activating, deactivating and installing from WordPress.org work here; updating "
            "and automatic updates are not on WordPress's REST API, so Open in Dashboard goes "
            "to each site's Plugins screen."
        )
    if kind == "themes":
        return (
            " WordPress's REST API only reads themes, so activating, installing, updating and "
            "automatic updates are done in each site's Appearance > Themes; Open in Dashboard "
            "goes there."
        )
    return ""
