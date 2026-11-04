"""What a site offers this account, read from its REST index (wordpress.md 9.15).

Every 9.15 command asks here before it does anything, so a site without the
feature never offers it, and the person hears one sentence saying why rather
than meeting a failure halfway through. The index is the site's own list of
routes and namespaces (``GET /wp-json/``); the account is ``users/me``. Both
are read once a session per site by the commands that use them.

Wx-free, like the rest of :mod:`quill.core.wordpress`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import Account, friendly_date
from quill.core.wordpress.site_admin import AppPassword

#: Notes on blocks arrived in WordPress 6.9.
NOTES_VERSION = (6, 9)

#: The modifiers the picture edit route takes when its index entry does not say.
DEFAULT_MODIFIERS = ("rotate", "crop")


@dataclass(frozen=True)
class SiteIndex:
    """The parts of the REST index the 9.15 commands look at."""

    namespaces: tuple[str, ...]
    #: Route pattern -> its index entry (methods, endpoints and their args).
    routes: Mapping[str, Any] = field(default_factory=dict)
    wp_version: str = ""

    def has_route(self, pattern: str) -> bool:
        """Whether any route matches *pattern* (a regular expression)."""
        rx = re.compile(pattern)
        return any(rx.search(route) for route in self.routes)

    def supports(self, namespace: str) -> bool:
        clean = namespace.strip("/")
        return clean in self.namespaces or f"/{clean}" in self.routes

    def edit_modifiers(self) -> tuple[str, ...]:
        """The picture edits this site's ``media/{id}/edit`` route accepts."""
        for route, entry in self.routes.items():
            if not _MEDIA_EDIT.search(route) or not isinstance(entry, dict):
                continue
            for endpoint in entry.get("endpoints", []) or []:
                args = endpoint.get("args", {}) if isinstance(endpoint, dict) else {}
                found = _modifier_types(args.get("modifiers") if isinstance(args, dict) else None)
                if found:
                    return found
        return DEFAULT_MODIFIERS


def _modifier_types(schema: Any) -> tuple[str, ...]:
    """``modifiers.items`` lists each modifier as a ``oneOf`` or a ``type`` enum."""
    if not isinstance(schema, dict):
        return ()
    items = schema.get("items")
    if not isinstance(items, dict):
        return ()
    found: list[str] = []
    for option in items.get("oneOf", []) or []:
        props = option.get("properties", {}) if isinstance(option, dict) else {}
        kind = props.get("type", {}) if isinstance(props, dict) else {}
        for value in kind.get("enum", []) if isinstance(kind, dict) else []:
            found.append(str(value))
    props = items.get("properties", {})
    kind = props.get("type", {}) if isinstance(props, dict) else {}
    for value in kind.get("enum", []) if isinstance(kind, dict) else []:
        found.append(str(value))
    return tuple(dict.fromkeys(found))


_MEDIA_EDIT = re.compile(r"^/wp/v2/media/[^/]+/edit$")
_INTROSPECT = re.compile(r"^/wp/v2/users/[^/]+/application-passwords/introspect$")
_COMMENTS = re.compile(r"^/wp/v2/comments$")
_MEDIA = re.compile(r"^/wp/v2/media$")


def read_index(api: WordPressApi) -> SiteIndex:
    """The REST index, kept to its namespaces, routes and WordPress version."""
    raw = api.get("")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not describe itself. The REST API may be turned off.")
    generator = str(raw.get("generator", "") or "")
    match = re.search(r"\?v=([\d.]+)", generator)
    routes = raw.get("routes")
    return SiteIndex(
        namespaces=tuple(str(n) for n in raw.get("namespaces", []) or []),
        routes=dict(routes) if isinstance(routes, dict) else {},
        wp_version=match.group(1) if match else "",
    )


def version_tuple(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version or "")
    return tuple(int(p) for p in parts[:3])


def at_least(version: str, wanted: tuple[int, ...]) -> bool:
    """Whether *version* is *wanted* or later; an unknown version is not ruled out."""
    have = version_tuple(version)
    return not have or have >= wanted


def _role(account: Account) -> str:
    role = account.role_name
    article = "an" if role[:1].lower() in "aeiou" else "a"
    return f"{article} {role}"


#: feature -> (capability, what the account could not do).
_NEEDS: dict[str, tuple[str, str]] = {
    "notes": ("edit_posts", "read or write notes on blocks"),
    "edit_picture": ("upload_files", "edit pictures in the Media Library"),
    "library_alt": ("upload_files", "change pictures in the Media Library"),
    "bulk_moderation": ("moderate_comments", "moderate comments"),
    "which_password": ("read", "see its application passwords"),
    "custom_fields": ("edit_posts", "change custom fields"),
}


def unavailable(
    feature: str,
    index: SiteIndex,
    account: Account,
    site_name: str,
    *,
    known_version: str = "",
) -> str:
    """ "" when *site_name* offers *feature* to this account, else why not, in one sentence."""
    version = index.wp_version or known_version
    if feature == "notes":
        if not at_least(version, NOTES_VERSION):
            return (
                f"Notes on blocks need WordPress 6.9 or later, and {site_name} runs {version}. "
                "Ask the site's administrator to update it."
            )
        if not index.has_route(_COMMENTS.pattern):
            return f"{site_name} does not offer comments to QUILL, so it has no notes to show."
    elif feature == "edit_picture":
        if not index.has_route(_MEDIA_EDIT.pattern):
            return (
                f"{site_name} does not offer picture editing. It needs WordPress 5.5 or later; "
                "until then, make the change on this computer and upload the result."
            )
    elif feature == "which_password":
        if not index.has_route(_INTROSPECT.pattern):
            return (
                f"{site_name} cannot say which application password QUILL is using. That needs "
                "WordPress 5.9 or later."
            )
    elif feature == "library_alt" and not index.has_route(_MEDIA.pattern):
        return f"{site_name} does not offer its Media Library to QUILL."
    capability, what = _NEEDS.get(feature, ("", ""))
    if capability and capability != "read" and not account.can(capability):
        return f"Your account on {site_name} is {_role(account)}, which cannot {what}."
    return ""


# --------------------------------------------------------------------------- #
# Which application password QUILL is using


def which_password(api: WordPressApi) -> AppPassword | None:
    """The application password this request was signed with (5.9+), or None.

    ``users/me/application-passwords/introspect`` answers with the password's
    own record, so QUILL can say its name, when it was made and when it was
    last used, and Sign Out can revoke exactly that one.
    """
    try:
        raw = api.get("wp/v2/users/me/application-passwords/introspect")
    except WordPressApiError as exc:
        if exc.status in (400, 401, 403, 404):
            return None
        raise
    if not isinstance(raw, dict) or not raw.get("uuid"):
        return None
    return AppPassword(
        uuid=str(raw.get("uuid", "")),
        name=str(raw.get("name", "") or ""),
        created=str(raw.get("created", "") or ""),
        last_used=str(raw.get("last_used", "") or ""),
    )


def password_sentence(site_name: str, found: AppPassword | None) -> str:
    if found is None:
        return f"{site_name} did not say which application password QUILL is using."
    name = f"named {found.name}" if found.name else "with no name"
    made = f", made {friendly_date(found.created)}" if found.created else ""
    used = f", last used {friendly_date(found.last_used)}" if found.last_used else ""
    return f"On {site_name}, QUILL is using the application password {name}{made}{used}."
