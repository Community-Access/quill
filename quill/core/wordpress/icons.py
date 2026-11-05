"""Insert Icon: the site's icons by name, never left unnamed (wordpress.md 9.16).

WordPress 7.x lists its icons over REST (``wp/v2/icons``, grouped by
``wp/v2/icon-collections``). Each comes with its name, a label and its SVG.
QUILL inserts the SVG itself, in an HTML block, so the result is the same on
every theme, and it is always one of two things:

* **decorative**, ``aria-hidden="true"``, so screen readers skip it; or
* **named**, ``role="img"`` with an ``aria-label`` that says what it means.

There is no third, unnamed kind: :func:`icon_markup` refuses an empty label
unless the icon is marked decorative.

Wx-free.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi, WordPressApiError


class IconLabelError(CodedError):
    """An icon that is neither decorative nor named."""

    code = "QUILL-WP-ICON-UNNAMED"


@dataclass(frozen=True)
class Icon:
    name: str
    label: str
    collection: str
    svg: str

    def spoken(self) -> str:
        where = f", {self.collection}" if self.collection else ""
        return f"{self.label or self.name}{where}"


def list_icons(api: WordPressApi, *, search: str = "") -> list[Icon]:
    collections: dict[str, str] = {}
    try:
        raw_collections = api.get("wp/v2/icon-collections")
    except WordPressApiError as exc:
        if exc.status not in (401, 403, 404):
            raise
        raw_collections = []
    for raw in raw_collections if isinstance(raw_collections, list) else []:
        if isinstance(raw, dict):
            slug = str(raw.get("slug") or raw.get("name") or "")
            collections[slug] = str(raw.get("label") or raw.get("title") or slug)
    params: dict[str, object] = {"search": search.strip()} if search.strip() else {}
    found: list[Icon] = []
    for raw in api.iter_collection("wp/v2/icons", params):
        name = str(raw.get("name") or raw.get("slug") or "")
        if not name:
            continue
        prefix = name.split("/", 1)[0] if "/" in name else ""
        collection = str(raw.get("collection") or prefix)
        found.append(
            Icon(
                name=name,
                label=_text(raw.get("label") or raw.get("title")),
                collection=collections.get(collection, collection),
                svg=str(raw.get("content") or raw.get("svg") or ""),
            )
        )
    return sorted(found, key=lambda icon: (icon.label or icon.name).casefold())


def _text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("rendered") or value.get("raw") or ""
    return html.unescape(str(value or "")).strip()


_SVG_OPEN = re.compile(r"<svg\b([^>]*)>", re.I)
_STRIP = re.compile(r"\s(?:aria-hidden|aria-label|role|focusable)\s*=\s*([\"']).*?\1", re.I)


def icon_markup(icon: Icon, *, label: str = "", decorative: bool = False) -> str:
    """The icon as an HTML block, decorative or named; never unnamed."""
    words = label.strip()
    if not decorative and not words:
        raise IconLabelError(
            "An icon needs a label that says what it means, or to be marked decorative."
        )
    match = _SVG_OPEN.search(icon.svg)
    if match is None:
        raise IconLabelError(f"The site sent no picture for the icon {icon.name}.")
    attrs = _STRIP.sub("", match.group(1))
    if decorative:
        attrs += ' aria-hidden="true" focusable="false"'
    else:
        attrs += f' role="img" aria-label="{html.escape(words, quote=True)}" focusable="false"'
    svg = icon.svg[: match.start()] + f"<svg{attrs}>" + icon.svg[match.end() :]
    svg = re.sub(r"<title\b[^>]*>.*?</title>", "", svg, flags=re.I | re.S)
    return f"<!-- wp:html -->\n{svg.strip()}\n<!-- /wp:html -->"
