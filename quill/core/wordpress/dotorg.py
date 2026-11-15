"""WordPress.org's plugin, theme and translation directories (complete.md 10B.3, WP-G).

Questions a site's own REST API cannot answer, asked of WordPress.org's
public API at ``api.wordpress.org`` -- the one host here that is not a site
the person connected, so every request is behind a consent that names the
host and what is sent (the window asks; :func:`ask_wordpress_org` is the
egress audit's marker):

- **Theme search** (``themes/info/1.2``, ``query_themes``): the words the
  person typed, and nothing about their sites. Each theme is said in words
  (name, version, author, rating, what it needs) so it can be chosen by ear,
  then installed in each site's Appearance > Themes > Add New, because
  ``wp/v2/themes`` cannot install (:mod:`~quill.core.wordpress.workbench_no_rest`).
- **Language packs** (``translations/core/1.0``): a WordPress version number,
  nothing else. Each site's language comes from its own ``wp/v2/settings``;
  WordPress.org says whether a pack exists for that language and version.
  Whether it is installed and current on the site is not on REST, and the
  sentence says so and where to look.
- **Plugin search and details** (``plugins/info/1.2``, ``query_plugins`` and
  ``plugin_information``): the words typed, or the short names (slugs) of the
  plugins in question. Each plugin is said in words -- rating, active
  installs, last updated, tested up to, what it needs -- and a plugin
  WordPress.org has closed, or has not seen updated in over two years, says
  so (:meth:`DotorgPlugin.warning`). Installing is the site's own
  ``wp/v2/plugins``; updating and rolling back are not on REST at all.

No sign-in, no cookie and no site address is ever sent. Wx-free.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quill.core.error_codes import CodedError

__all__ = [
    "DOTORG_HOST",
    "STALE_DAYS",
    "DotorgError",
    "DotorgPlugin",
    "DotorgTheme",
    "LanguagePack",
    "ask_wordpress_org",
    "language_sentence",
    "language_packs",
    "not_listed_sentence",
    "parse_plugin",
    "parse_themes",
    "plugin_details",
    "plugin_info_url",
    "plugin_search_url",
    "plugin_slug",
    "search_plugins",
    "search_themes",
    "site_languages",
    "theme_search_url",
    "translations_url",
]

DOTORG_HOST = "api.wordpress.org"
_TIMEOUT = 20.0
_MAX_BYTES = 4 * 1024 * 1024


class DotorgError(CodedError):
    """WordPress.org did not answer, or answered with something unreadable."""

    code = "QUILL-WORDPRESS-DOTORG-REQUEST"


Opener = Callable[..., Any]


def ask_wordpress_org(request: Request, timeout: float | None = None) -> Any:
    """The one place api.wordpress.org is reached (the egress audit's marker)."""
    from quill.core.net import verified_ssl_context

    return urlopen(request, timeout=timeout, context=verified_ssl_context())


def _get(url: str, opener: Opener | None, *, answer_404: bool = False) -> Any:
    """The JSON at *url*; with *answer_404*, a 404's own JSON body (a closed plugin's)."""
    if not url.startswith(f"https://{DOTORG_HOST}/"):
        raise DotorgError("QUILL only asks api.wordpress.org.")
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with (opener or ask_wordpress_org)(request, timeout=_TIMEOUT) as response:
            raw = response.read(_MAX_BYTES)
    except HTTPError as exc:
        if answer_404 and exc.code == 404:
            try:
                return json.loads(exc.read(_MAX_BYTES) or b"{}")
            except (ValueError, OSError):
                return {}
        raise DotorgError(f"WordPress.org answered {exc.code}.") from None
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise DotorgError(f"Could not reach WordPress.org ({reason}).") from None
    try:
        return json.loads(raw)
    except ValueError:
        raise DotorgError("WordPress.org sent an answer QUILL could not read.") from None


# -- themes ------------------------------------------------------------------------------


def theme_search_url(words: str, per_page: int = 20) -> str:
    query = {
        "action": "query_themes",
        "request[search]": words.strip(),
        "request[per_page]": str(per_page),
        "request[fields][description]": "1",
        "request[fields][rating]": "1",
    }
    return f"https://{DOTORG_HOST}/themes/info/1.2/?{urlencode(query)}"


@dataclass(frozen=True)
class DotorgTheme:
    slug: str
    name: str
    version: str = ""
    author: str = ""
    rating: int = -1
    ratings: int = 0
    requires: str = ""
    requires_php: str = ""
    description: str = ""

    @property
    def sentence(self) -> str:
        parts = [f"{self.name}, version {self.version or 'not said'}"]
        if self.author:
            parts.append(f"by {self.author}")
        if self.rating >= 0:
            stars = self.rating / 20
            parts.append(f"rated {stars:.1f} of 5 by {self.ratings} people")
        needs = [
            f"WordPress {self.requires}" if self.requires else "",
            f"PHP {self.requires_php}" if self.requires_php else "",
        ]
        if any(needs):
            parts.append("needs " + " and ".join(n for n in needs if n))
        said = ", ".join(parts) + "."
        if self.description:
            said += " " + self.description.strip()
        return said


def _author(raw: Any) -> str:
    if isinstance(raw, Mapping):
        return str(raw.get("display_name") or raw.get("user_nicename") or "")
    return str(raw or "")


def _int(value: Any, fallback: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _plain(text: Any) -> str:
    from quill.core.wordpress.site import plain_text

    return plain_text(str(text or ""))


def parse_themes(payload: Any) -> list[DotorgTheme]:
    themes = payload.get("themes") if isinstance(payload, Mapping) else None
    found: list[DotorgTheme] = []
    for raw in themes or []:
        if not isinstance(raw, Mapping) or not raw.get("slug"):
            continue
        found.append(
            DotorgTheme(
                slug=str(raw["slug"]),
                name=_plain(raw.get("name")) or str(raw["slug"]),
                version=str(raw.get("version") or ""),
                author=_author(raw.get("author")),
                rating=_int(raw.get("rating"), -1),
                ratings=_int(raw.get("num_ratings"), 0),
                requires=str(raw.get("requires") or ""),
                requires_php=str(raw.get("requires_php") or ""),
                description=_plain(raw.get("description"))[:400],
            )
        )
    return found


def search_themes(words: str, *, opener: Opener | None = None) -> list[DotorgTheme]:
    """Themes on WordPress.org matching *words* (the only thing sent)."""
    if not words.strip():
        return []
    return parse_themes(_get(theme_search_url(words), opener))


# -- plugins -----------------------------------------------------------------------------

#: Older than this on WordPress.org, a plugin is said to be possibly abandoned.
STALE_DAYS = 730
_PLUGIN_FIELDS = {
    "request[fields][active_installs]": "1",
    "request[fields][short_description]": "1",
    "request[fields][description]": "0",
    "request[fields][sections]": "0",
    "request[fields][versions]": "0",
    "request[fields][reviews]": "0",
    "request[fields][banners]": "0",
    "request[fields][icons]": "0",
    "request[fields][screenshots]": "0",
    "request[fields][contributors]": "0",
    "request[fields][tags]": "0",
}


def plugin_search_url(words: str, per_page: int = 20) -> str:
    query = {
        "action": "query_plugins",
        "request[search]": words.strip(),
        "request[per_page]": str(per_page),
        **_PLUGIN_FIELDS,
    }
    return f"https://{DOTORG_HOST}/plugins/info/1.2/?{urlencode(query)}"


def plugin_info_url(slug: str, *, changelog: bool = False) -> str:
    """``plugin_information`` for *slug*; with *changelog*, its readme sections too (D3)."""
    query = {"action": "plugin_information", "request[slug]": slug.strip(), **_PLUGIN_FIELDS}
    if changelog:
        query["request[fields][sections]"] = "1"
    return f"https://{DOTORG_HOST}/plugins/info/1.2/?{urlencode(query)}"


def plugin_slug(plugin_file: str) -> str:
    """WordPress.org's short name for a ``wp/v2/plugins`` id (``akismet/akismet`` -> akismet)."""
    first = (plugin_file or "").strip().split("/", 1)[0]
    return first.removesuffix(".php")


def _text(value: Any) -> str:
    """WordPress.org writes ``false`` for a field it has no value for."""
    return "" if value in (None, False) else str(value)


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(_text(value)[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class DotorgPlugin:
    """One plugin as WordPress.org's directory describes it."""

    slug: str
    name: str
    version: str = ""
    author: str = ""
    rating: int = -1
    ratings: int = 0
    active_installs: int = -1
    last_updated: str = ""  # YYYY-MM-DD
    tested: str = ""
    requires: str = ""
    requires_php: str = ""
    closed: bool = False
    closed_date: str = ""
    closed_reason: str = ""
    description: str = ""
    changelog: str = ""  # the readme's changelog section, as plain lines (workbench_changelog)

    def warning(self, today: date) -> str:
        """Why this plugin may be abandoned or unsafe to keep ("" when nothing says so)."""
        if self.closed:
            when = f" on {self.closed_date}" if self.closed_date else ""
            why = f" ({self.closed_reason})" if self.closed_reason else ""
            return (
                f"WordPress.org closed {self.name}{when}{why}: it gets no updates there and "
                "cannot be installed from it."
            )
        updated = _day(self.last_updated)
        if updated is not None and (today - updated).days > STALE_DAYS:
            return (
                f"{self.name} has not been updated on WordPress.org since {self.last_updated}, "
                "over two years: it may be abandoned."
            )
        return ""

    def sentence(self, today: date, *, describe: bool = False) -> str:
        """The plugin in words: its facts, then any warning, then (on search) its description."""
        if self.closed:
            return self.warning(today)
        parts = [f"{self.name}, version {self.version or 'not said'}"]
        if self.author:
            parts.append(f"by {self.author}")
        if self.rating >= 0 and self.ratings:
            parts.append(f"rated {self.rating / 20:.1f} of 5 by {self.ratings} people")
        if self.active_installs >= 0:
            parts.append(f"{self.active_installs:,}+ active installs")
        if self.last_updated:
            parts.append(f"last updated {self.last_updated}")
        if self.tested:
            parts.append(f"tested up to WordPress {self.tested}")
        needs = [
            f"WordPress {self.requires}" if self.requires else "",
            f"PHP {self.requires_php}" if self.requires_php else "",
        ]
        if any(needs):
            parts.append("needs " + " and ".join(n for n in needs if n))
        said = ", ".join(parts) + "."
        warning = self.warning(today)
        if warning:
            said += " Warning: " + warning
        if describe and self.description:
            said += " " + self.description
        return said


def parse_plugin(raw: Any, slug: str = "") -> DotorgPlugin | None:
    """One plugin from ``plugin_information`` or a ``query_plugins`` row; None when unknown."""
    if not isinstance(raw, Mapping):
        return None
    if raw.get("closed") or raw.get("error") == "closed":
        found = str(raw.get("slug") or slug)
        return DotorgPlugin(
            slug=found,
            name=_plain(raw.get("name")) or found,
            closed=True,
            closed_date=_text(raw.get("closed_date"))[:10],
            closed_reason=_plain(raw.get("reason_text") or raw.get("reason")),
        )
    if raw.get("error") or not raw.get("slug"):
        return None
    return DotorgPlugin(
        slug=str(raw["slug"]),
        name=_plain(raw.get("name")) or str(raw["slug"]),
        version=_text(raw.get("version")),
        author=_plain(raw.get("author")),
        rating=_int(raw.get("rating"), -1),
        ratings=_int(raw.get("num_ratings"), 0),
        active_installs=_int(raw.get("active_installs"), -1),
        last_updated=_text(raw.get("last_updated"))[:10],
        tested=_text(raw.get("tested")),
        requires=_text(raw.get("requires")),
        requires_php=_text(raw.get("requires_php")),
        description=_plain(raw.get("short_description"))[:400],
        changelog=_changelog(raw.get("sections")),
    )


def _changelog(sections: Any) -> str:
    """The changelog section, sanitised to plain text (no markup, scripts or link targets)."""
    if not isinstance(sections, Mapping):
        return ""
    from quill.core.wordpress.workbench_changelog import plain_text

    return plain_text(_text(sections.get("changelog")))[:60_000]


def search_plugins(words: str, *, opener: Opener | None = None) -> list[DotorgPlugin]:
    """Plugins on WordPress.org matching *words* (the only thing sent)."""
    if not words.strip():
        return []
    payload = _get(plugin_search_url(words), opener)
    rows = payload.get("plugins") if isinstance(payload, Mapping) else None
    return [p for p in (parse_plugin(raw) for raw in rows or []) if p is not None]


def plugin_details(
    slugs: Iterable[str],
    *,
    opener: Opener | None = None,
    limit: int = 100,
    changelog: bool = False,
) -> dict[str, DotorgPlugin | None]:
    """Each slug's directory entry (None: not in the directory); one request a slug.

    With *changelog*, each entry carries its changelog too; still only the slug is sent.
    """
    found: dict[str, DotorgPlugin | None] = {}
    for slug in slugs:
        slug = slug.strip()
        if not slug or slug in found or len(found) >= limit:
            continue
        url = plugin_info_url(slug, changelog=changelog)
        found[slug] = parse_plugin(_get(url, opener, answer_404=True), slug)
    return found


def not_listed_sentence(name: str) -> str:
    """A plugin WordPress.org does not have: what that means."""
    return (
        f"{name} is not in the WordPress.org directory (a paid, custom or retired plugin), so "
        "QUILL cannot say whether it is kept up to date."
    )


# -- translations ------------------------------------------------------------------------


def translations_url(version: str) -> str:
    return f"https://{DOTORG_HOST}/translations/core/1.0/?{urlencode({'version': version})}"


@dataclass(frozen=True)
class LanguagePack:
    language: str
    english_name: str
    native_name: str
    version: str
    updated: str


def language_packs(version: str, *, opener: Opener | None = None) -> dict[str, LanguagePack]:
    """Every core language pack WordPress.org has for *version* (the only thing sent)."""
    payload = _get(translations_url(version), opener)
    packs: dict[str, LanguagePack] = {}
    rows = payload.get("translations") if isinstance(payload, Mapping) else None
    for raw in rows or []:
        if not isinstance(raw, Mapping) or not raw.get("language"):
            continue
        pack = LanguagePack(
            str(raw["language"]),
            str(raw.get("english_name") or raw["language"]),
            str(raw.get("native_name") or ""),
            str(raw.get("version") or version),
            str(raw.get("updated") or "")[:10],
        )
        packs[pack.language] = pack
    return packs


def language_sentence(
    site: str, locale: str, wp_version: str, packs: Mapping[str, LanguagePack]
) -> str:
    """One site's language and what WordPress.org has for it."""
    locale = (locale or "").strip()
    if not locale or locale == "en_US":
        return f"{site} uses English (United States), which needs no language pack."
    pack = packs.get(locale)
    if pack is None:
        return (
            f"{site} uses {locale}. WordPress.org has no {locale} pack for WordPress "
            f"{wp_version or 'of that version'}, so parts of wp-admin may show in English."
        )
    native = f" ({pack.native_name})" if pack.native_name else ""
    when = f", updated {pack.updated}" if pack.updated else ""
    return (
        f"{site} uses {pack.english_name}{native}. WordPress.org has its pack for WordPress "
        f"{pack.version}{when}. Whether {site} has installed it is not on WordPress's REST "
        "API; Dashboard > Updates says, and installs it."
    )


def site_languages(
    sites: Sequence[tuple[str, str, str]], *, opener: Opener | None = None
) -> list[tuple[str, str]]:
    """(site, sentence) for each (site, locale, WordPress version), one request per version."""
    by_version: dict[str, dict[str, LanguagePack]] = {}
    said: list[tuple[str, str]] = []
    for site, locale, version in sites:
        packs: Mapping[str, LanguagePack] = {}
        if locale and locale != "en_US" and version:
            if version not in by_version:
                by_version[version] = language_packs(version, opener=opener)
            packs = by_version[version]
        said.append((site, language_sentence(site, locale, version, packs)))
    return said
