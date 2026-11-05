"""Which of the 9.16 routes a site offers, and why not when it does not (wordpress.md 9.16).

Every 9.16 command asks :func:`unavailable` before it does anything, with the
site's REST index (:func:`quill.core.wordpress.site_features.read_index`) and
the account. A site without the route never gets the request; the person
hears one sentence that says what is missing and what would bring it.

Wx-free, like the rest of :mod:`quill.core.wordpress`.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.wordpress.site import Account
from quill.core.wordpress.site_features import SiteIndex


@dataclass(frozen=True)
class RouteNeed:
    """One feature: the route pattern it needs, what it is called, and who may use it."""

    pattern: str
    what: str
    missing: str
    capability: str = ""
    can_not: str = ""


#: feature -> what it needs. ``missing`` is said with the site's name in front.
FEATURES: dict[str, RouteNeed] = {
    "url_details": RouteNeed(
        r"^/wp-block-editor/v1/url-details$",
        "link details",
        "cannot read where a link goes. That needs WordPress 5.9 or later.",
        "edit_posts",
        "read where links go",
    ),
    "icons": RouteNeed(
        r"^/wp/v2/icons$",
        "icons",
        "has no icon library. Icons arrived in WordPress 7.0.",
        "edit_posts",
        "insert icons",
    ),
    "pieces": RouteNeed(
        r"^/wp/v2/media/\(\?P<id>[^)]*\)[^/]*/sideload$",
        "uploads in pieces",
        "cannot take an upload in pieces. Upload Files sends it in one go instead.",
        "upload_files",
        "upload files",
    ),
    "post_process": RouteNeed(
        r"^/wp/v2/media/\(\?P<id>[^)]*\)[^/]*/post-process$",
        "regenerating sizes",
        "cannot remake a picture's sizes. That needs WordPress 6.9 or later.",
        "upload_files",
        "change pictures in the Media Library",
    ),
    "style_revisions": RouteNeed(
        r"^/wp/v2/global-styles/[^/]+/revisions$",
        "previous looks",
        "keeps no history of its site styles. That needs a block theme and WordPress 6.3 or later.",
        "edit_theme_options",
        "change the site's styles",
    ),
    "navigation_revisions": RouteNeed(
        r"^/wp/v2/navigation/[^/]+/revisions$",
        "menu history",
        "keeps no history of its Navigation blocks.",
        "edit_theme_options",
        "change menus",
    ),
    "menus": RouteNeed(
        r"^/wp/v2/(menus|navigation)$",
        "menus",
        "does not offer its menus to QUILL.",
        "edit_theme_options",
        "change menus",
    ),
    "directory_sizes": RouteNeed(
        r"^/wp-site-health/v1/directory-sizes$",
        "space used",
        "does not say how much space it uses. That needs WordPress 5.6 or later.",
        "view_site_health_checks",
        "see how much space the site uses",
    ),
    "export": RouteNeed(
        r"^/wp-block-editor/v1/export$",
        "design export",
        "cannot export its design. Only a block theme on WordPress 5.9 or later can.",
        "export",
        "download the site's design",
    ),
    "media": RouteNeed(
        r"^/wp/v2/media$",
        "the Media Library",
        "does not offer its Media Library to QUILL.",
        "upload_files",
        "upload files",
    ),
    "writing": RouteNeed(
        r"^/wp/v2/(posts|pages)$",
        "pages and posts",
        "does not offer its pages and posts to QUILL.",
        "edit_posts",
        "write pages or posts",
    ),
}


def _role(account: Account) -> str:
    role = account.role_name
    article = "an" if role[:1].lower() in "aeiou" else "a"
    return f"{article} {role}"


def unavailable(feature: str, index: SiteIndex, account: Account, site_name: str) -> str:
    """ "" when *site_name* offers *feature* to this account, else why not, in one sentence."""
    need = FEATURES[feature]
    if not index.has_route(need.pattern):
        return f"{site_name} {need.missing}"
    if need.capability and not _allowed(account, need.capability):
        return f"Your account on {site_name} is {_role(account)}, which cannot {need.can_not}."
    return ""


def _allowed(account: Account, capability: str) -> bool:
    if account.can(capability):
        return True
    # An administrator always may; some sites leave meta capabilities out of users/me.
    return account.can("manage_options") and capability in {
        "view_site_health_checks",
        "export",
        "edit_theme_options",
    }
