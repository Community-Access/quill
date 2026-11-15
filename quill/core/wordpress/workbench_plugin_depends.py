"""What depends on a plugin, asked of the site before it is turned off (PRD D3, WP-R-048).

Before deactivating a plugin (and before deleting it in wp-admin) a person
should know what stops working. :func:`dependents` reads only what the site
itself exposes, through its own client:

- **Other plugins that require it**: each plugin's ``requires_plugins``
  (WordPress 6.5's Requires Plugins header), from ``wp/v2/plugins``.
- **Its blocks in use**: the block namespaces it registers
  (``wp/v2/block-types``, matched to the plugin by its slug or text domain),
  then the posts and pages whose content holds ``wp:<namespace>/``, found
  with the site's own search.
- **Its shortcodes in use**, for the plugins whose shortcode is known.
- **QUILL features that use its REST namespace**, from the site's index.

Each part that the site will not answer is left out and said so, never
guessed. :meth:`Dependents.sentence` says it all, with how to undo it.
Wx-free; runs off the UI thread.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import rendered

__all__ = ["Dependents", "dependents", "plugin_slug"]

#: Shortcodes a plugin is known by, where its blocks are not the whole story.
_SHORTCODES: Mapping[str, tuple[str, ...]] = {
    "gravityforms": ("[gravityform",),
    "contact-form-7": ("[contact-form-7",),
    "woocommerce": ("[woocommerce_", "[products", "[product_page"),
    "the-events-calendar": ("[tribe_events",),
    "paid-memberships-pro": ("[pmpro_",),
    "wpforms-lite": ("[wpforms",),
    "ninja-forms": ("[ninja_form",),
}

#: REST namespaces a plugin brings, and what QUILL does with each.
_NAMESPACES: Mapping[str, tuple[tuple[str, str], ...]] = {
    "woocommerce": (("wc/v3", "Shop: products, orders, customers and coupons"),),
    "the-events-calendar": (("tribe/events/v1", "Events: New Event and Coming Up"),),
    "wordpress-seo": (("yoast/v1", "the SEO title and description in Properties"),),
    "seo-by-rank-math": (("rankmath/v1", "the SEO title and description in Properties"),),
    "gravityforms": (("gf/v2", "Gravity Forms forms, responses and feeds"),),
    "paid-memberships-pro": (("pmpro/v1", "Memberships: levels, orders and subscriptions"),),
    "quill-accessible-forms": (("qaf/v1", "Forms and Held as Spam for form entries"),),
    "bits-accessible-forms": (("baf/v1", "Forms, under the plugin's older name"),),
    "jetpack": (("jetpack/v4", "Jetpack's site facts in Overview"),),
}


def plugin_slug(plugin: str) -> str:
    """``akismet/akismet`` -> ``akismet``."""
    return (plugin or "").split("/", 1)[0].removesuffix(".php")


def _required(raw: Mapping[str, Any]) -> list[str]:
    value = raw.get("requires_plugins")
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


@dataclass
class Dependents:
    """What would notice if a plugin went: plugins, content and QUILL features."""

    name: str
    plugins: list[str] = field(default_factory=list)  # plugins that require it
    content: list[tuple[str, str]] = field(default_factory=list)  # (title, why) using it
    features: list[str] = field(default_factory=list)  # QUILL features through its routes
    unknown: list[str] = field(default_factory=list)  # what the site would not say

    @property
    def any(self) -> bool:
        return bool(self.plugins or self.content or self.features)

    def sentence(self) -> str:
        parts: list[str] = []
        if self.plugins:
            parts.append(f"{_list(self.plugins)} require{'s' if len(self.plugins) == 1 else ''} it")
        if self.content:
            shown = [f"{title} ({why})" for title, why in self.content[:6]]
            more = f" and {len(self.content) - 6} more" if len(self.content) > 6 else ""
            parts.append(f"{_list(shown)}{more} use it")
        if self.features:
            parts.append(f"QUILL uses it for {_list(self.features)}")
        if parts:
            said = f"What depends on {self.name}: " + "; ".join(parts) + "."
        else:
            said = f"Nothing the site shows depends on {self.name}."
        if self.unknown:
            said += f" The site would not say {_list(self.unknown)}."
        return (
            said + " To undo, turn it back on: its settings stay while it is off. Deleting it "
            "in wp-admin can also remove its settings and data."
        )


def _list(words: Sequence[str]) -> str:
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


def _block_namespaces(api: WordPressApi, slug: str, textdomain: str) -> list[str]:
    raw = api.get("wp/v2/block-types", _fields="name")
    wanted = {slug, textdomain} - {""}
    found: list[str] = []
    for block in raw if isinstance(raw, list) else []:
        name = str(block.get("name", "")) if isinstance(block, Mapping) else ""
        namespace = name.partition("/")[0]
        if namespace in wanted and namespace not in found and namespace != "core":
            found.append(namespace)
    return found


def _using(api: WordPressApi, words: str, why: str, limit: int) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for route in ("wp/v2/pages", "wp/v2/posts"):
        raw = api.get(route, search=words, per_page=limit, status="any", _fields="id,title")
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, Mapping):
                title = rendered(item.get("title")) or f"item {item.get('id', '')}"
                found.append((f'"{title}"', why))
    return found


def dependents(
    api: WordPressApi,
    plugin: str,
    *,
    name: str = "",
    plugins: Sequence[Mapping[str, Any]] | None = None,
    namespaces: Iterable[str] = (),
    limit: int = 20,
) -> Dependents:
    """What depends on *plugin* (its ``wp/v2/plugins`` id) on this site."""
    slug = plugin_slug(plugin)
    found = Dependents(name or slug)
    listed: Sequence[Mapping[str, Any]] = plugins or []
    if plugins is None:
        try:
            raw = api.get("wp/v2/plugins", context="edit")
            listed = [r for r in raw if isinstance(r, Mapping)] if isinstance(raw, list) else []
        except WordPressApiError:
            found.unknown.append("which plugins require it")
    own = next((r for r in listed if str(r.get("plugin", "")) == plugin), {})
    for other in listed:
        if str(other.get("plugin", "")) != plugin and slug in _required(other):
            found.plugins.append(rendered(other.get("name")) or str(other.get("plugin", "")))
    textdomain = str(own.get("textdomain", "") or "")
    try:
        for namespace in _block_namespaces(api, slug, textdomain):
            found.content += _using(api, f"wp:{namespace}/", f"its {namespace} blocks", limit)
    except WordPressApiError:
        found.unknown.append("which pages use its blocks")
    try:
        for code in _SHORTCODES.get(slug, ()):
            found.content += _using(api, code, f"its {code}] shortcode", limit)
    except WordPressApiError:
        found.unknown.append("which pages use its shortcodes")
    present = set(namespaces)
    for namespace, feature in _NAMESPACES.get(slug, ()):
        if not present or namespace in present:
            found.features.append(feature)
    found.content = list(dict.fromkeys(found.content))
    return found
