"""Style variations and the safe subset of Site Styles (wordpress.md 9.15).

A block theme ships ready-made looks (``global-styles/themes/{theme}/variations``)
and keeps the site's own changes in one global-styles record
(``global-styles/{id}``). QUILL reads both and offers two things:

* **Style Variations:** each look by name with its Palette Report (9.7), so a
  person can choose the one whose colours pass. Applying one keeps the look it
  replaces on this computer, so Put Back can restore it.
* **Site Styles, the safe subset:** the palette's colours and the font sizes,
  edited by name, each colour's contrast said as it is chosen. Nothing else in
  ``theme.json`` is touched: everything is sent as ``settings`` alone, which
  WordPress merges over what the record already holds.

Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`.
"""

from __future__ import annotations

import copy as _copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress import contrast as con
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.local import now_stamp
from quill.core.wordpress.site import raw_text
from quill.core.wordpress.site_report import palette_from_global_styles


class StyleValueError(CodedError, ValueError):
    """A colour or a font size QUILL cannot read; the message says what it takes."""

    code = "QUILL-WP-STYLES-VALUE"


#: Route patterns in the REST index (regular expressions, as site_features takes).
VARIATIONS_ROUTE = r"^/wp/v2/global-styles/themes/.+/variations$"
STYLES_ROUTE = r"^/wp/v2/global-styles/\(\?P<id>"


@dataclass(frozen=True)
class ActiveTheme:
    name: str
    stylesheet: str
    #: The id of the site's own global-styles record, 0 when the theme has none.
    styles_id: int
    block_theme: bool = True


def active_theme(api: WordPressApi) -> ActiveTheme:
    """The active theme, and where its global styles live (from ``wp:user-global-styles``)."""
    raw = api.get("wp/v2/themes", status="active", _fields="name,stylesheet,is_block_theme,_links")
    first = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], dict) else {}
    links = first.get("_links", {}) if isinstance(first.get("_links"), dict) else {}
    styles_id = 0
    for link in links.get("wp:user-global-styles", []) or []:
        match = re.search(r"/global-styles/(\d+)", str(link.get("href", "")))
        if match:
            styles_id = int(match.group(1))
            break
    return ActiveTheme(
        name=raw_text(first.get("name")),
        stylesheet=str(first.get("stylesheet", "") or ""),
        styles_id=styles_id,
        block_theme=bool(first.get("is_block_theme", styles_id > 0)),
    )


# --------------------------------------------------------------------------- #
# Style variations


@dataclass(frozen=True)
class Variation:
    title: str
    settings: dict[str, Any] = field(default_factory=dict)
    styles: dict[str, Any] = field(default_factory=dict)

    def as_global_styles(self) -> dict[str, Any]:
        return {"settings": self.settings, "styles": self.styles}


def list_variations(api: WordPressApi, stylesheet: str) -> list[Variation]:
    raw = api.get(f"wp/v2/global-styles/themes/{stylesheet}/variations")
    found: list[Variation] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        settings = entry.get("settings") if isinstance(entry.get("settings"), dict) else {}
        styles = entry.get("styles") if isinstance(entry.get("styles"), dict) else {}
        title = raw_text(entry.get("title")) or f"Variation {len(found) + 1}"
        found.append(Variation(title, dict(settings or {}), dict(styles or {})))
    return found


def theme_styles(api: WordPressApi, stylesheet: str) -> dict[str, Any]:
    raw = api.get(f"wp/v2/global-styles/themes/{stylesheet}")
    return raw if isinstance(raw, dict) else {}


def readable(colours: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Only the colours QUILL can read; a gradient or a CSS variable is left out."""
    kept = []
    for name, value in colours:
        try:
            con.parse_colour(value)
        except con.ColourParseError:
            continue
        kept.append((name, value))
    return kept


def variation_report(variation: Variation, base: dict[str, Any]) -> list[str]:
    """The Palette Report for one look; the theme's own colours where it sets none."""
    merged = {
        "settings": _merge(base.get("settings") or {}, variation.settings),
        "styles": _merge(base.get("styles") or {}, variation.styles),
    }
    palette, backgrounds = palette_from_global_styles(merged)
    return con.palette_report(readable(palette), readable(backgrounds))


def report_summary(lines: list[str]) -> str:
    """ "12 pairings, 3 below the minimum for body text"."""
    faint = sum(1 for line in lines if not line.endswith(", passes"))
    if not lines:
        return "no colours QUILL can read"
    return f"{len(lines)} pairings, {faint} below the minimum for body text"


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = _copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = _copy.deepcopy(value)
    return out


def load_user_styles(api: WordPressApi, styles_id: int) -> dict[str, Any]:
    raw = api.get(f"wp/v2/global-styles/{styles_id}", context="edit")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not send its site styles.")
    return {
        "title": raw_text(raw.get("title")),
        "settings": raw.get("settings") if isinstance(raw.get("settings"), dict) else {},
        "styles": raw.get("styles") if isinstance(raw.get("styles"), dict) else {},
    }


def save_user_styles(api: WordPressApi, styles_id: int, body: dict[str, Any]) -> None:
    api.post(f"wp/v2/global-styles/{styles_id}", body)


def apply_variation(api: WordPressApi, styles_id: int, variation: Variation) -> None:
    body = variation.as_global_styles()
    body["title"] = variation.title
    save_user_styles(api, styles_id, body)


# --------------------------------------------------------------------------- #
# The look before a change, kept on this computer for Put Back


def _backup_path(root: Path, site_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", site_id) or "site"
    return root / "styles" / f"{safe}-before.json"


def keep_previous(root: Path, site_id: str, user: dict[str, Any], *, reason: str) -> None:
    write_json_atomic(
        _backup_path(root, site_id),
        {"saved_at": now_stamp(), "reason": reason, **user},
    )


def previous(root: Path, site_id: str) -> dict[str, Any] | None:
    raw = read_json(_backup_path(root, site_id), default=None)
    return raw if isinstance(raw, dict) and "settings" in raw else None


def put_back(api: WordPressApi, styles_id: int, saved: dict[str, Any]) -> None:
    body = {"settings": saved.get("settings") or {}, "styles": saved.get("styles") or {}}
    if saved.get("title"):
        body["title"] = saved["title"]
    save_user_styles(api, styles_id, body)


# --------------------------------------------------------------------------- #
# Site Styles: colours and font sizes by name


@dataclass(frozen=True)
class StyleEntry:
    kind: str  # "colour" or "size"
    slug: str
    name: str
    value: str


def _origin_list(settings: dict[str, Any], *path: str) -> list[dict[str, Any]]:
    """``settings.color.palette`` as a list: the theme origin of a user record,
    or the plain list a theme.json holds."""
    node: Any = settings
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, dict):
        node = node.get("theme")
    return [dict(e) for e in node if isinstance(e, dict)] if isinstance(node, list) else []


def entries(base: dict[str, Any], user: dict[str, Any]) -> list[StyleEntry]:
    """The palette and the font sizes in effect: the site's own where it set them,
    else the theme's."""
    b, u = base.get("settings") or {}, user.get("settings") or {}
    colours = _origin_list(u, "color", "palette") or _origin_list(b, "color", "palette")
    sizes = _origin_list(u, "typography", "fontSizes") or _origin_list(b, "typography", "fontSizes")
    out = [
        StyleEntry(
            "colour",
            str(c.get("slug", "")),
            str(c.get("name") or c.get("slug")),
            str(c.get("color", "")),
        )
        for c in colours
        if c.get("color")
    ]
    out += [
        StyleEntry(
            "size",
            str(s.get("slug", "")),
            str(s.get("name") or s.get("slug")),
            str(s.get("size", "")),
        )
        for s in sizes
        if s.get("size")
    ]
    return out


def page_colours(base: dict[str, Any], user: dict[str, Any]) -> tuple[str, str]:
    """``(background, text)`` of the page, with palette references resolved."""
    styles = _merge(base.get("styles") or {}, user.get("styles") or {})
    colour = styles.get("color", {}) if isinstance(styles.get("color"), dict) else {}
    by_slug = {e.slug: e.value for e in entries(base, user) if e.kind == "colour"}

    def resolve(value: Any, fallback: str) -> str:
        text = str(value or "")
        match = re.search(r"--color--([a-z0-9-]+)|var:preset\|color\|([a-z0-9-]+)", text)
        if match:
            text = by_slug.get(match.group(1) or match.group(2), "")
        try:
            con.parse_colour(text)
        except con.ColourParseError:
            return fallback
        return text

    return resolve(colour.get("background"), "#ffffff"), resolve(colour.get("text"), "#000000")


def entry_row(entry: StyleEntry, background: str, text: str) -> str:
    if entry.kind == "size":
        return f"Font size: {entry.name}, {entry.value}"
    return f"Colour: {contrast_sentence(entry.name, entry.value, background, text)}"


def contrast_sentence(name: str, colour: str, background: str, text: str) -> str:
    """ "Accent (dark green), #1a4d2e, 7.2 to 1 on the page background, passes"."""
    try:
        seen = con.parse_colour(colour)
    except con.ColourParseError:
        return f"{name}, {colour}, a colour QUILL cannot read"
    if seen == con.parse_colour(background):
        ratio = con.contrast_ratio(text, colour)
        word = con.nearest_colour_name(seen)
        return (
            f"{name} ({word}), {colour}, the page background; the text on it is "
            f"{con.format_ratio(ratio)}, {con.rating(ratio)}"
        )
    choice = con.describe_choice(name, colour, background)
    label, _ratio, verdict = choice.rsplit(", ", 2)
    return f"{label}, {colour}, {_ratio} on the page background, {verdict}"


def check_colour(value: str) -> str:
    clean = value.strip()
    try:
        con.parse_colour(clean)
    except con.ColourParseError as exc:
        raise StyleValueError(
            f"QUILL cannot read {clean or 'that'} as a colour. Type it as a hex code such as "
            "#1a4d2e, or as rgb(26, 77, 46)."
        ) from exc
    return clean


_SIZE = re.compile(r"^\d+(\.\d+)?(px|rem|em|%|pt|vw|vh)$|^(clamp|min|max|calc)\(.+\)$")


def check_size(value: str) -> str:
    clean = value.strip().lower()
    if not _SIZE.match(clean):
        raise StyleValueError(
            f"QUILL cannot read {value.strip() or 'that'} as a font size. Type a number with "
            "its unit, such as 1.125rem or 18px."
        )
    return clean


def changed_settings(
    base: dict[str, Any], user: dict[str, Any], entry: StyleEntry, value: str
) -> dict[str, Any]:
    """The user record's settings with one colour or size changed, and nothing else.

    The whole list in effect goes in as the ``theme`` origin, the shape the
    Site Editor saves, so the other colours or sizes stay as they are.
    """
    settings = _copy.deepcopy(user.get("settings") or {})
    b = base.get("settings") or {}
    if entry.kind == "colour":
        path, key = ("color", "palette"), "color"
    else:
        path, key = ("typography", "fontSizes"), "size"
    current = _origin_list(settings, *path) or _origin_list(b, *path)
    for item in current:
        if str(item.get("slug", "")) == entry.slug:
            item[key] = value
            if key == "size" and isinstance(item.get("fluid"), dict):
                # The old fluid range would override the new size; plain wins.
                item.pop("fluid")
    group = settings.setdefault(path[0], {})
    holder = group.get(path[1])
    if not isinstance(holder, dict):
        holder = {}
    holder["theme"] = current
    group[path[1]] = holder
    return settings
