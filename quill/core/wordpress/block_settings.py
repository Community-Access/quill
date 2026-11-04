"""Block Settings: a form for the block at the caret, with the theme's own names (8.4, 9.7).

Colours and font sizes come from the theme by name -- "Accent (dark green)",
"Large" -- never ``#2f5d50`` or ``1.375rem``, and every colour choice says
its contrast against what it will sit on ("Accent (dark green), 7.2 to 1,
passes"). The theme decides what is offered: with no palette from the site,
no colour is offered.

Writing settings back changes the block's comment attributes and the classes
WordPress derives from them on the block's outer element (``has-accent-color``,
``alignwide``...), and nothing else. Which classes WordPress writes is
well known; the *order* it writes them in is not documented, so QUILL keeps
existing classes where they are and adds new ones in the order the block
editor is seen to use. Preview Blocks shows what the site makes of the result.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.block_catalog import Field, assign_access_keys
from quill.core.wordpress.blocks import Block
from quill.core.wordpress.contrast import (
    ColourParseError,
    contrast_ratio,
    describe_choice,
    format_ratio,
    nearest_colour_name,
    rating,
)

__all__ = [
    "Preset",
    "ThemePresets",
    "apply_settings",
    "contrast_warning",
    "fetch_presets",
    "parse_presets",
    "settings_fields",
]


@dataclass(frozen=True)
class Preset:
    slug: str
    name: str
    value: str


@dataclass
class ThemePresets:
    colours: list[Preset] = field(default_factory=list)
    font_sizes: list[Preset] = field(default_factory=list)
    #: The page's own text and background colours, resolved to a value.
    text: str = ""
    background: str = ""
    #: True when the theme has a wide width, so "Wide" and "Full" are offered.
    wide: bool = True

    def colour(self, slug: str) -> Preset | None:
        return next((p for p in self.colours if p.slug == slug), None)


def _presets(raw: Any, value_key: str, include_default: bool) -> list[Preset]:
    if isinstance(raw, list):
        groups = [raw]
    elif isinstance(raw, Mapping):
        origins = ["theme", "custom"] + (["default"] if include_default else [])
        groups = [raw.get(o) or [] for o in origins]
    else:
        return []
    out: list[Preset] = []
    seen: set[str] = set()
    for group in groups:
        for item in group if isinstance(group, list) else []:
            if not isinstance(item, Mapping):
                continue
            slug, value = item.get("slug"), item.get(value_key)
            if not isinstance(slug, str) or not isinstance(value, str) or slug in seen:
                continue
            seen.add(slug)
            name = item.get("name")
            out.append(Preset(slug, name if isinstance(name, str) and name else slug, value))
    return out


_VAR = re.compile(r"var\(--wp--preset--color--([a-z0-9-]+)\)|var:preset\|color\|([a-z0-9-]+)")


def _resolve(value: Any, colours: Sequence[Preset]) -> str:
    if not isinstance(value, str):
        return ""
    m = _VAR.fullmatch(value.strip())
    if m:
        slug = m.group(1) or m.group(2)
        found = next((p.value for p in colours if p.slug == slug), "")
        return found
    return value.strip()


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def parse_presets(global_styles: Mapping[str, Any]) -> ThemePresets:
    """The palette, font sizes and page colours from a theme's global styles."""
    settings = _map(global_styles.get("settings"))
    color = _map(settings.get("color"))
    typography = _map(settings.get("typography"))
    layout = _map(settings.get("layout"))
    colours = _presets(
        color.get("palette"), "color", color.get("defaultPalette", True) is not False
    )
    sizes = _presets(
        typography.get("fontSizes"), "size", typography.get("defaultFontSizes", True) is not False
    )
    page = _map(_map(global_styles.get("styles")).get("color"))
    return ThemePresets(
        colours=colours,
        font_sizes=sizes,
        text=_resolve(page.get("text"), colours),
        background=_resolve(page.get("background"), colours),
        wide=bool(layout.get("wideSize")) if layout else True,
    )


def fetch_presets(api: WordPressApi) -> ThemePresets | None:
    """The active theme's presets, or None when the site does not share them."""
    try:
        themes = api.get("wp/v2/themes", status="active")
        if not isinstance(themes, list) or not themes or not isinstance(themes[0], Mapping):
            return None
        stylesheet = themes[0].get("stylesheet")
        if not isinstance(stylesheet, str) or not stylesheet:
            return None
        styles = api.get(f"wp/v2/global-styles/themes/{stylesheet}")
    except WordPressApiError:
        return None
    return parse_presets(styles) if isinstance(styles, Mapping) else None


# --------------------------------------------------------------------------- #
# Which settings a block has

#: Blocks whose outer element takes colour and font-size classes.
COLOUR_BLOCKS = frozenset({
    "core/paragraph",
    "core/heading",
    "core/list",
    "core/quote",
    "core/group",
    "core/columns",
    "core/column",
    "core/details",
    "core/preformatted",
    "core/verse",
})
#: Text alignment, and the attribute each block keeps it in.
TEXT_ALIGN = {"core/paragraph": "align", "core/heading": "textAlign"}
#: Blocks that can be placed left, centre, right, wide or full.
BLOCK_ALIGN = frozenset({
    "core/group",
    "core/columns",
    "core/image",
    "core/table",
    "core/cover",
    "core/embed",
    "core/gallery",
    "core/buttons",
    "core/separator",
    "core/media-text",
})
_HANDLED = {"align", "textAlign", "textColor", "backgroundColor", "fontSize"}
_PLUMBING = {"lock", "metadata", "className", "style", "layout", "anchor"}
_DEFAULT_TEXT = "#000000"
_DEFAULT_BACKGROUND = "#ffffff"


def _bg_label(preset: Preset, text: str) -> str:
    try:
        ratio = contrast_ratio(text, preset.value)
        word = nearest_colour_name(preset.value)
    except ColourParseError:
        return preset.name
    name = preset.name if preset.name.casefold() == word else f"{preset.name} ({word})"
    return f"{name}, text on it {format_ratio(ratio)}, {rating(ratio)}"


def _fg_label(preset: Preset, background: str) -> str:
    try:
        return describe_choice(preset.name, preset.value, background)
    except ColourParseError:
        return preset.name


def _pair(attrs: Mapping[str, Any], presets: ThemePresets) -> tuple[str, str]:
    fg = presets.colour(str(attrs.get("textColor", "")))
    bg = presets.colour(str(attrs.get("backgroundColor", "")))
    text = fg.value if fg else presets.text or _DEFAULT_TEXT
    background = bg.value if bg else presets.background or _DEFAULT_BACKGROUND
    return text, background


def _choice(key: str, label: str, help_text: str, value: Any, rows: list[tuple[str, Any]]) -> Field:
    f = Field(key, label, "choice", help_text, value)
    f.choices = [r for r, _v in rows]
    f.values = [v for _r, v in rows]
    return f


def settings_fields(block: Block, presets: ThemePresets | None) -> list[Field]:
    """The Block Settings form: alignment, colours, size, then every other setting."""
    name = block.name or ""
    attrs = block.attrs
    fields: list[Field] = []
    if name in TEXT_ALIGN:
        key = TEXT_ALIGN[name]
        rows = [("Not set", None), ("Left", "left"), ("Centre", "center"), ("Right", "right")]
        fields.append(
            _choice(key, "Text &alignment:", "Where the lines sit.", attrs.get(key), rows)
        )
    elif name in BLOCK_ALIGN:
        rows = [("Not set", None), ("Left", "left"), ("Centre", "center"), ("Right", "right")]
        if presets is None or presets.wide:
            rows += [("Wide", "wide"), ("Full width", "full")]
        fields.append(
            _choice(
                "align",
                "&Alignment and width:",
                "Where the block sits, and how wide.",
                attrs.get("align"),
                rows,
            )
        )
    if presets is not None and name in COLOUR_BLOCKS and presets.colours:
        text, background = _pair(attrs, presets)
        fg_rows: list[tuple[str, Any]] = [("Theme default", None)]
        fg_rows += [(_fg_label(p, background), p.slug) for p in presets.colours]
        bg_rows: list[tuple[str, Any]] = [("None", None)]
        bg_rows += [(_bg_label(p, text), p.slug) for p in presets.colours]
        fields.append(
            _choice(
                "textColor",
                "&Text colour:",
                "The theme's text colours, each with its contrast against this block's background.",
                attrs.get("textColor"),
                fg_rows,
            )
        )
        fields.append(
            _choice(
                "backgroundColor",
                "&Background colour:",
                "The theme's colours, each with the contrast of this block's text on it.",
                attrs.get("backgroundColor"),
                bg_rows,
            )
        )
    if presets is not None and name in COLOUR_BLOCKS and presets.font_sizes:
        rows = [("Theme default", None)] + [(p.name, p.slug) for p in presets.font_sizes]
        fields.append(
            _choice(
                "fontSize",
                "&Font size:",
                "The theme's sizes, by name.",
                attrs.get("fontSize"),
                rows,
            )
        )
    for key, value in attrs.items():
        if key in _HANDLED or key in _PLUMBING:
            continue
        words = _words(key)
        if isinstance(value, bool):
            fields.append(Field(key, words, "check", f"Turn {words.lower()} on or off.", value))
        elif isinstance(value, (str, int, float)):
            fields.append(
                Field(key, words + ":", "text", f"The {words.lower()} setting.", str(value))
            )
    labels = assign_access_keys([f.label for f in fields])
    for f, label in zip(fields, labels, strict=True):
        f.label = label
    return fields


def _words(key: str) -> str:
    out = "".join((" " + c.lower()) if c.isupper() else c for c in key).replace("_", " ")
    out = out.strip()
    return out[:1].upper() + out[1:]


# --------------------------------------------------------------------------- #
# Writing settings back

_FIRST_TAG = re.compile(r"<([a-zA-Z][\w-]*)((?:\s[^<>]*?)?)(/?)>")
_CLASS = re.compile(r'\sclass="([^"]*)"')


def _generated(attrs: Mapping[str, Any], name: str) -> tuple[list[str], list[str]]:
    """Classes WordPress derives from *attrs*: (alignment ones, colour and size ones)."""
    first: list[str] = []
    last: list[str] = []
    text_align = attrs.get(TEXT_ALIGN.get(name, ""))
    if isinstance(text_align, str) and text_align:
        first.append(f"has-text-align-{text_align}")
    align = attrs.get("align")
    if name not in TEXT_ALIGN and isinstance(align, str) and align:
        first.append(f"align{align}")
    text, background = attrs.get("textColor"), attrs.get("backgroundColor")
    if isinstance(text, str) and text:
        last.append(f"has-{text}-color")
    if isinstance(background, str) and background:
        last.append(f"has-{background}-background-color")
    if isinstance(text, str) and text:
        last.append("has-text-color")
    if isinstance(background, str) and background:
        last.append("has-background")
    size = attrs.get("fontSize")
    if isinstance(size, str) and size:
        last.append(f"has-{size}-font-size")
    return first, last


_STYLE = re.compile(r'\sstyle="([^"]*)"')


def _restyle_inline(name: str, attrs: Mapping[str, Any], attributes: str) -> str:
    """The two settings WordPress writes as an inline style: column width, spacer height."""
    if name == "core/column":
        width = attrs.get("width")
        style = f"flex-basis:{width}" if isinstance(width, str) and width else ""
    elif name == "core/spacer":
        height = attrs.get("height")
        style = f"height:{height if isinstance(height, str) and height else '100px'}"
    else:
        return attributes
    found = _STYLE.search(attributes)
    if found:
        replacement = f' style="{style}"' if style else ""
        return attributes[: found.start()] + replacement + attributes[found.end() :]
    if not style:
        return attributes
    after_class = _CLASS.search(attributes)
    at = after_class.end() if after_class else len(attributes)
    return attributes[:at] + f' style="{style}"' + attributes[at:]


def _restyle(block: Block, old: Mapping[str, Any]) -> None:
    head = next((i for i, part in enumerate(block.inner_content) if part is not None), None)
    if head is None:
        return
    markup = block.inner_content[head]
    assert markup is not None
    tag = _FIRST_TAG.search(markup)
    if tag is None:
        return
    name = block.name or ""
    stale = set(sum(_generated(old, name), []))
    first, last = _generated(block.attrs, name)
    attributes = tag.group(2)
    found = _CLASS.search(attributes)
    current = found.group(1).split() if found else []
    kept = [c for c in current if c not in stale]
    lead = 1 if kept and kept[0].startswith("wp-block-") else 0
    classes = kept[:lead] + first + kept[lead:] + [c for c in last if c not in kept]
    value = " ".join(dict.fromkeys(classes))
    if found:
        attributes = (
            attributes[: found.start()]
            + (f' class="{value}"' if value else "")
            + attributes[found.end() :]
        )
    elif value:
        attributes = f' class="{value}"' + attributes
    attributes = _restyle_inline(name, block.attrs, attributes)
    new_tag = f"<{tag.group(1)}{attributes}{tag.group(3)}>"
    new_markup = markup[: tag.start()] + new_tag + markup[tag.end() :]
    block.inner_content[head] = new_markup
    block.inner_html = block.inner_html.replace(markup, new_markup, 1)


def apply_settings(block: Block, answers: Mapping[str, Any]) -> None:
    """Put the form's answers into the block's attributes, and its classes to match."""
    old = dict(block.attrs)
    attrs = dict(block.attrs)
    for key, value in answers.items():
        before = old.get(key)
        if isinstance(before, (int, float)) and not isinstance(before, bool):
            if isinstance(value, str):
                try:
                    value = int(value) if isinstance(before, int) else float(value)
                except ValueError:
                    value = before
        if value is None or value == "":
            attrs.pop(key, None)
        else:
            attrs[key] = value
    block.attrs = attrs
    if attrs != old:
        _restyle(block, old)


def contrast_warning(attrs: Mapping[str, Any], presets: ThemePresets | None) -> str:
    """A sentence when the block's text and background are below WCAG AA, else ""."""
    if presets is None or not (attrs.get("textColor") or attrs.get("backgroundColor")):
        return ""
    text, background = _pair(attrs, presets)
    try:
        ratio = contrast_ratio(text, background)
    except ColourParseError:
        return ""
    verdict = rating(ratio)
    if verdict == "passes":
        return ""
    return (
        f"The text and background are {format_ratio(ratio)}, {verdict}; body text needs "
        "4.5 to 1, large text 3 to 1."
    )
