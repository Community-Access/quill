"""The site's own writing types (an Event, a Recipe), apart from posts and pages.

Split from :mod:`quill.core.wordpress.site` for size. Wx-free.
"""

from __future__ import annotations

from quill.core.wordpress.api import WordPressApi

__all__ = ["writing_types"]

#: Types WordPress lists that are not pages or posts a person writes.
_NOT_WRITING_TYPES = frozenset({
    "attachment",
    "nav_menu_item",
    "wp_block",
    "wp_template",
    "wp_template_part",
    "wp_navigation",
    "wp_global_styles",
    "wp_font_family",
    "wp_font_face",
})


def writing_types(api: WordPressApi) -> list[tuple[str, str, str]]:
    """``(post type, REST base, plural name)`` for the site's own writing types."""
    raw = api.get("wp/v2/types", context="edit")
    found: list[tuple[str, str, str]] = []
    if not isinstance(raw, dict):
        return found
    for slug, info in raw.items():
        if slug in {"post", "page"} or slug in _NOT_WRITING_TYPES or not isinstance(info, dict):
            continue
        base = str(info.get("rest_base") or "")
        if base and info.get("viewable", True):
            found.append((str(slug), base, str(info.get("name") or base.title())))
    return found
