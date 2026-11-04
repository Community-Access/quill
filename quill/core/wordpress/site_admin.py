"""Running a site: settings, the Site Check, people, passwords, plugins and themes.

wordpress.md 9.2, 9.10 and 9.13. Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`. Each function returns plain
dataclasses or sentences, so the windows above never read JSON.

**Know before you try (9.2).** :data:`NEEDS` names the capability each
window needs, and :func:`cannot_sentence` says, in one sentence, what this
role cannot do -- so a window never offers a button the site will refuse.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlparse

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import Account, friendly_date, rendered

# --------------------------------------------------------------------------- #
# Know what you can do (9.2)

#: Window -> (capability, what it lets you do, in words).
NEEDS: dict[str, tuple[str, str]] = {
    "comments": ("moderate_comments", "moderate comments"),
    "menus": ("edit_theme_options", "change menus"),
    "widgets": ("edit_theme_options", "change widgets"),
    "settings": ("manage_options", "change site settings"),
    "site_check": ("view_site_health_checks", "run the site's health checks"),
    "terms": ("manage_categories", "manage categories and tags"),
    "users": ("list_users", "manage users"),
    "add_user": ("create_users", "add users"),
    "edit_users": ("edit_users", "change other people's accounts"),
    "delete_users": ("delete_users", "delete users"),
    "promote_users": ("promote_users", "change roles"),
    "plugins": ("activate_plugins", "manage plugins"),
    "install_plugins": ("install_plugins", "install plugins"),
    "delete_plugins": ("delete_plugins", "delete plugins"),
    "themes": ("switch_themes", "see every theme"),
    "fonts": ("edit_theme_options", "manage fonts"),
    "bulk_edit": ("edit_others_posts", "edit other people's posts"),
    "page_order": ("edit_others_pages", "arrange pages"),
    "patterns": ("edit_posts", "edit patterns"),
}


def can(account: Account, need: str) -> bool:
    capability = NEEDS[need][0]
    if capability == "view_site_health_checks" and account.can("manage_options"):
        return True
    return account.can(capability)


def cannot_sentence(site_name: str, account: Account, need: str) -> str:
    """ "Your account on Community Radio is an Author, which cannot manage users." """
    what = NEEDS[need][1]
    role = account.role_name
    article = "an" if role[:1].lower() in "aeiou" else "a"
    return f"Your account on {site_name} is {article} {role}, which cannot {what}."


# --------------------------------------------------------------------------- #
# The site's own settings (9.10, 9.13)

#: The settings Site Settings shows, in order: (key, label, kind). Kind is
#: "text", "page" (a page id), "media" (an attachment id), "bool", "number"
#: or "choice".
SETTINGS_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("title", "Site title", "text"),
    ("description", "Tagline", "text"),
    ("language", "Site language", "text"),
    ("timezone", "Time zone", "text"),
    ("date_format", "Date format", "text"),
    ("time_format", "Time format", "text"),
    ("start_of_week", "First day of the week", "choice"),
    ("email", "Administrator email", "text"),
    ("show_on_front", "Front page shows", "choice"),
    ("page_on_front", "Front page", "page"),
    ("page_for_posts", "Posts page", "page"),
    ("posts_per_page", "Posts per page", "number"),
    ("default_comment_status", "New posts take comments", "choice"),
    ("default_ping_status", "New posts take pingbacks", "choice"),
    ("use_smilies", "Turn emoticons into pictures", "bool"),
    ("default_post_format", "Default post format", "choice"),
    ("site_icon", "Site icon", "media"),
)

CHOICES: dict[str, tuple[tuple[str, str], ...]] = {
    "show_on_front": (("posts", "Your latest posts"), ("page", "A page you choose")),
    "default_comment_status": (("open", "Yes"), ("closed", "No")),
    "default_ping_status": (("open", "Yes"), ("closed", "No")),
    "start_of_week": tuple(
        (str(i), d)
        for i, d in enumerate((
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ))
    ),
    "default_post_format": tuple(
        (f, f.title() if f else "Standard")
        for f in (
            "",
            "aside",
            "chat",
            "gallery",
            "link",
            "image",
            "quote",
            "status",
            "video",
            "audio",
        )
    ),
}


def load_settings(api: WordPressApi) -> dict[str, Any]:
    raw = api.get("wp/v2/settings")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not send its settings.")
    return raw


def settings_value_text(key: str, value: Any, pages: dict[int, str]) -> str:
    kind = next((k for f, _l, k in SETTINGS_FIELDS if f == key), "text")
    if kind == "page":
        number = int(value or 0)
        return pages.get(number, f"page {number}") if number else "none"
    if kind == "media":
        return f"picture {value}" if value else "none"
    if kind == "bool":
        return "yes" if value else "no"
    if kind == "choice":
        return dict(CHOICES.get(key, ())).get(str(value if value is not None else ""), str(value))
    text = "" if value is None else str(value)
    return text or "(empty)"


def settings_rows(settings: dict[str, Any], pages: dict[int, str]) -> list[tuple[str, str, str]]:
    """``(key, label, value text)`` for every field this site sends."""
    return [
        (key, label, settings_value_text(key, settings[key], pages))
        for key, label, _kind in SETTINGS_FIELDS
        if key in settings
    ]


def save_setting(api: WordPressApi, key: str, value: Any) -> dict[str, Any]:
    raw = api.post("wp/v2/settings", {key: value})
    return raw if isinstance(raw, dict) else {}


# --------------------------------------------------------------------------- #
# The Site Check (9.10)


@dataclass(frozen=True)
class CheckLine:
    status: str  # critical, recommended, good, info
    text: str


_ORDER = {"critical": 0, "recommended": 1, "info": 2, "good": 3}


def site_check(api: WordPressApi, *, site_url: str, wp_version: str) -> list[CheckLine]:
    """Everything REST can tell about the site's health, critical first."""
    lines: list[CheckLine] = []
    index = api.get("")
    index = index if isinstance(index, dict) else {}
    lines.append(
        CheckLine("info", f"WordPress version: {wp_version}.")
        if wp_version
        else CheckLine("info", "WordPress version: the site does not say.")
    )
    home = str(index.get("home") or index.get("url") or site_url)
    if urlparse(home).scheme == "https":
        lines.append(CheckLine("good", "HTTPS: the site's address uses HTTPS."))
    else:
        lines.append(
            CheckLine(
                "critical",
                "HTTPS: the site's address does not use HTTPS. Visitors' "
                "browsers will call it not secure.",
            )
        )
    timezone = str(index.get("timezone_string") or "")
    offset = index.get("gmt_offset")
    if timezone:
        lines.append(CheckLine("info", f"Time zone: {timezone}."))
    elif offset is not None:
        lines.append(
            CheckLine(
                "recommended",
                f"Time zone: a fixed offset of {offset} hours. A city keeps daylight saving right.",
            )
        )
    lines.extend(_permalinks(api))
    lines.extend(_settings_lines(api))
    # Every Site Health test the index lists, and the recognised plugins (9.15).
    from quill.core.wordpress import site_health

    lines.extend(site_health.health_lines(api, index))
    lines.extend(site_health.recognised_lines(index))
    lines.append(
        CheckLine(
            "info",
            "Search engine visibility: WordPress does not share this over its API; "
            "it is under Settings, Reading in the dashboard.",
        )
    )
    return sorted(lines, key=lambda line: _ORDER.get(line.status, 2))


def _permalinks(api: WordPressApi) -> list[CheckLine]:
    try:
        recent = api.get("wp/v2/posts", per_page=1, _fields="link")
    except WordPressApiError:
        return []
    if not isinstance(recent, list) or not recent:
        return []
    link = str(recent[0].get("link", ""))
    if "?p=" in link:
        return [
            CheckLine(
                "recommended",
                "Permalinks: plain (?p=123). Readable addresses help "
                "visitors and search engines; change them under Settings, Permalinks.",
            )
        ]
    return [CheckLine("good", "Permalinks: readable addresses are on.")]


def _settings_lines(api: WordPressApi) -> list[CheckLine]:
    try:
        settings = load_settings(api)
    except WordPressApiError:
        return []
    out: list[CheckLine] = []
    if "default_comment_status" in settings:
        open_ = settings["default_comment_status"] == "open"
        out.append(
            CheckLine("info", f"Comments: new posts {'take' if open_ else 'do not take'} comments.")
        )
    if settings.get("language"):
        out.append(
            CheckLine(
                "info",
                f"Site language: {settings['language']}. It is every page's "
                "language, so it chooses the voice screen readers use.",
            )
        )
    return out


def check_text(site_name: str, lines: list[CheckLine]) -> str:
    critical = sum(1 for line in lines if line.status == "critical")
    recommended = sum(1 for line in lines if line.status == "recommended")
    head = f"Site Check for {site_name}: {critical} critical, {recommended} recommended."
    words = {"critical": "Critical", "recommended": "Recommended", "good": "Good", "info": "Note"}
    return head + "\n\n" + "\n".join(f"{words.get(x.status, 'Note')}: {x.text}" for x in lines)


# --------------------------------------------------------------------------- #
# Application passwords (9.10, 9.13)


@dataclass(frozen=True)
class AppPassword:
    uuid: str
    name: str
    created: str
    last_used: str
    user_id: int = 0
    user_name: str = ""

    def spoken(self, current_uuid: str = "") -> str:
        used = f"last used {friendly_date(self.last_used)}" if self.last_used else "never used"
        mine = ", this computer's QUILL" if self.uuid == current_uuid else ""
        who = f"{self.user_name}: " if self.user_name else ""
        return f"{who}{self.name}{mine}, made {friendly_date(self.created)}, {used}"


def current_password_uuid(api: WordPressApi) -> str:
    """The uuid of the application password this request was signed with (5.9+)."""
    try:
        raw = api.get("wp/v2/users/me/application-passwords/introspect")
    except WordPressApiError as exc:
        if exc.status in (400, 401, 403, 404):
            return ""
        raise
    return str(raw.get("uuid", "")) if isinstance(raw, dict) else ""


def list_app_passwords(
    api: WordPressApi, user: str = "me", user_name: str = ""
) -> list[AppPassword]:
    raw = api.get(f"wp/v2/users/{user}/application-passwords")
    return [
        AppPassword(
            uuid=str(r.get("uuid", "")),
            name=str(r.get("name", "")),
            created=str(r.get("created", "") or ""),
            last_used=str(r.get("last_used", "") or ""),
            user_id=0 if user == "me" else int(user),
            user_name=user_name,
        )
        for r in (raw if isinstance(raw, list) else [])
        if isinstance(r, dict)
    ]


def revoke_app_password(api: WordPressApi, uuid: str, user: str = "me") -> None:
    api.delete(f"wp/v2/users/{user}/application-passwords/{quote(uuid, safe='')}")


# --------------------------------------------------------------------------- #
# Users (9.13)

ROLES = (
    ("subscriber", "Subscriber"),
    ("contributor", "Contributor"),
    ("author", "Author"),
    ("editor", "Editor"),
    ("administrator", "Administrator"),
)


@dataclass(frozen=True)
class User:
    id: int
    name: str
    username: str
    email: str
    roles: tuple[str, ...]
    description: str = ""
    url: str = ""
    nickname: str = ""
    first_name: str = ""
    last_name: str = ""

    @property
    def role_name(self) -> str:
        return dict(ROLES).get(self.roles[0], self.roles[0].title()) if self.roles else "no role"

    def spoken(self) -> str:
        email = f", {self.email}" if self.email else ""
        return f"{self.name}, {self.username}, {self.role_name}{email}"


def user_from_payload(raw: Any) -> User:
    return User(
        id=int(raw.get("id", 0)),
        name=str(raw.get("name", "")),
        username=str(raw.get("username", "") or raw.get("slug", "")),
        email=str(raw.get("email", "") or ""),
        roles=tuple(str(r) for r in raw.get("roles", []) or []),
        description=str(raw.get("description", "") or ""),
        url=str(raw.get("url", "") or ""),
        nickname=str(raw.get("nickname", "") or ""),
        first_name=str(raw.get("first_name", "") or ""),
        last_name=str(raw.get("last_name", "") or ""),
    )


def list_users(api: WordPressApi) -> list[User]:
    params: dict[str, object] = {"context": "edit", "orderby": "name"}
    return [user_from_payload(r) for r in api.iter_collection("wp/v2/users", params)]


def generated_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def add_user(api: WordPressApi, *, username: str, email: str, name: str, role: str) -> User:
    """A new account with a strong password QUILL never shows or keeps.

    The new person sets their own with "Lost your password?" on the sign-in page.
    """
    body = {
        "username": username,
        "email": email,
        "name": name,
        "roles": [role],
        "password": generated_password(),
    }
    return user_from_payload(api.post("wp/v2/users", body, context="edit"))


def update_user(api: WordPressApi, user: str | int, **fields: object) -> User:
    allowed = {
        "name",
        "email",
        "roles",
        "description",
        "url",
        "nickname",
        "first_name",
        "last_name",
    }
    body = {k: v for k, v in fields.items() if k in allowed}
    return user_from_payload(api.post(f"wp/v2/users/{user}", body, context="edit"))


def delete_user(api: WordPressApi, user_id: int, reassign: int) -> None:
    api.delete(f"wp/v2/users/{user_id}", force=True, reassign=reassign)


def post_count(api: WordPressApi, user_id: int) -> int:
    response = api.request(
        "GET",
        "wp/v2/posts",
        params={
            "author": user_id,
            "per_page": 1,
            "_fields": "id",
            "status": "any",
            "context": "edit",
        },
    )
    if response.total is not None:
        return response.total
    return len(response.payload) if isinstance(response.payload, list) else 0


# --------------------------------------------------------------------------- #
# Plugins and themes (9.13)


@dataclass(frozen=True)
class Plugin:
    plugin: str  # "akismet/akismet"
    name: str
    version: str
    author: str
    active: bool
    description: str = ""

    def spoken(self) -> str:
        state = "active" if self.active else "inactive"
        by = f", by {self.author}" if self.author else ""
        return f"{self.name}, version {self.version}, {state}{by}"


#: Well-known accessibility plugins, and what each does, in plain words.
ACCESSIBILITY_PLUGINS = {
    "wp-accessibility": "fixes common theme problems: skip links, language and focus outlines.",
    "accessibility-checker": "checks pages for accessibility problems inside the editor.",
    "one-click-accessibility": "adds a visitor toolbar for text size and contrast.",
    "pojo-accessibility": "adds a visitor toolbar for text size and contrast.",
    "wp-ada-compliance-check-basic": "scans posts for common accessibility errors.",
}


def plugin_from_payload(raw: Any) -> Plugin:
    author = rendered(raw.get("author")) if raw.get("author") else ""
    return Plugin(
        plugin=str(raw.get("plugin", "")),
        name=rendered(raw.get("name")) or str(raw.get("plugin", "")),
        version=str(raw.get("version", "") or ""),
        author=author,
        active=str(raw.get("status", "")) in {"active", "network-active"},
        description=rendered(raw.get("description")),
    )


def list_plugins(api: WordPressApi) -> list[Plugin]:
    raw = api.get("wp/v2/plugins", context="edit")
    return sorted(
        (
            plugin_from_payload(r)
            for r in (raw if isinstance(raw, list) else [])
            if isinstance(r, dict)
        ),
        key=lambda p: p.name.lower(),
    )


def accessibility_note(plugin: Plugin) -> str:
    slug = plugin.plugin.split("/", 1)[0]
    return ACCESSIBILITY_PLUGINS.get(slug, "")


def set_plugin_active(api: WordPressApi, plugin: Plugin, active: bool) -> Plugin:
    raw = api.post(f"wp/v2/plugins/{plugin.plugin}", {"status": "active" if active else "inactive"})
    return plugin_from_payload(raw)


def install_plugin(api: WordPressApi, slug: str) -> Plugin:
    """Install from WordPress.org by slug, inactive: activation is its own step."""
    return plugin_from_payload(api.post("wp/v2/plugins", {"slug": slug, "status": "inactive"}))


def delete_plugin(api: WordPressApi, plugin: Plugin) -> None:
    api.delete(f"wp/v2/plugins/{plugin.plugin}")


@dataclass(frozen=True)
class Theme:
    stylesheet: str
    name: str
    version: str
    active: bool
    supports: tuple[str, ...] = field(default_factory=tuple)

    def spoken(self) -> str:
        return f"{self.name}, version {self.version}, {'active' if self.active else 'inactive'}"


def list_themes(api: WordPressApi, *, active_only: bool = False) -> list[Theme]:
    """Every theme, or only the active one (all an account without switch_themes may see)."""
    raw = api.get("wp/v2/themes", status="active") if active_only else api.get("wp/v2/themes")
    themes: list[Theme] = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            continue
        supports = r.get("theme_supports", {}) or {}
        on = tuple(
            sorted(k.replace("-", " ") for k, v in supports.items() if v)
            if isinstance(supports, dict)
            else ()
        )
        themes.append(
            Theme(
                stylesheet=str(r.get("stylesheet", "")),
                name=rendered(r.get("name")) or str(r.get("stylesheet", "")),
                version=str(r.get("version", "") or ""),
                active=str(r.get("status", "")) == "active",
                supports=on,
            )
        )
    return sorted(themes, key=lambda t: (not t.active, t.name.lower()))
