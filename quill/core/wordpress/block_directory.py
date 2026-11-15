"""Install a missing block from WordPress.org's Block Directory (wordpress.md 9.17, gap 1).

``wp/v2/block-directory/search`` (WordPress 5.5 and later, ``install_plugins``
and ``activate_plugins``) asks WordPress.org's Block Directory **through the
site**, so QUILL reaches no host but the site. Each answer is a *block
plugin*: a plugin that adds one block, named by its WordPress.org slug.
Installing it is the ordinary ``POST wp/v2/plugins`` with that slug and
``status=active``, which is what the block editor itself sends.

What it cannot do, said in the preview: REST has no rollback for a plugin,
so the way back is deactivating and deleting it (:func:`remove_block_plugin`,
which is also the undo) -- an earlier version only comes back from a backup.

Wx-free; every request goes through the site's client.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import plain_text

__all__ = [
    "SEARCH_ROUTE",
    "DirectoryBlock",
    "install_block_plugin",
    "remove_block_plugin",
    "search_blocks",
]

SEARCH_ROUTE = r"^/wp/v2/block-directory/search$"
"""The route as the site's index lists it, for :meth:`SiteIndex.has_route`."""


@dataclass(frozen=True)
class DirectoryBlock:
    """One block plugin WordPress.org offers."""

    name: str  # the block's own name, such as "jetpack/markdown"
    title: str
    description: str
    slug: str  # the plugin's WordPress.org slug
    author: str = ""
    rating: float = 0.0
    installs: int = 0
    updated: str = ""

    def row(self) -> str:
        parts = [self.title]
        if self.description:
            parts.append(self.description)
        return ": ".join(parts)

    def describe(self) -> str:
        """Everything the preview says before anything is installed."""
        said = [f"{self.title} ({self.name}) comes in the plugin {self.slug}"]
        if self.author:
            said[0] += f", by {self.author}"
        facts = []
        if self.rating:
            facts.append(f"rated {self.rating:g} out of 5")
        if self.installs:
            facts.append(f"active on {self.installs:,} sites")
        if self.updated:
            facts.append(f"updated {self.updated}")
        if facts:
            said.append(", ".join(facts))
        return ". ".join(said) + "."


def _block(raw: Mapping[str, Any]) -> DirectoryBlock | None:
    slug = str(raw.get("id") or "")
    if not slug:
        return None
    rating = raw.get("rating")
    return DirectoryBlock(
        name=str(raw.get("name") or slug),
        title=plain_text(str(raw.get("title") or slug)),
        description=plain_text(str(raw.get("description") or "")),
        slug=slug,
        author=plain_text(str(raw.get("author") or "")),
        rating=float(rating) if isinstance(rating, (int, float)) else 0.0,  # out of 5 already
        installs=int(raw.get("active_installs") or 0),
        updated=str(raw.get("humanized_updated") or ""),
    )


def search_blocks(api: WordPressApi, words: str) -> list[DirectoryBlock]:
    """The Block Directory's blocks for *words*, as the site relays them."""
    found = api.get("wp/v2/block-directory/search", term=words.strip(), per_page=20)
    blocks = [_block(r) for r in (found if isinstance(found, list) else []) if isinstance(r, dict)]
    return [b for b in blocks if b is not None]


def install_block_plugin(api: WordPressApi, block: DirectoryBlock) -> str:
    """Install and activate the block's plugin; its plugin file ("slug/slug") for the undo."""
    answer = api.post("wp/v2/plugins", {"slug": block.slug, "status": "active"})
    plugin = str(answer.get("plugin", "") if isinstance(answer, dict) else "")
    if not plugin:
        raise WordPressApiError(f"The site did not say it installed {block.slug}.")
    return plugin


def remove_block_plugin(api: WordPressApi, plugin: str) -> None:
    """Deactivate, then delete, the plugin a block came in (the undo)."""
    api.post(f"wp/v2/plugins/{plugin}", {"status": "inactive"})
    api.delete(f"wp/v2/plugins/{plugin}")
