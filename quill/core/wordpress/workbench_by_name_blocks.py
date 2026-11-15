"""By Name for shortcodes, blocks and synced patterns: convert, update, detach (PRD 15.12).

The rows of Sites > site > By Name > Blocks and Shortcodes and > Patterns Used
(:mod:`quill.core.wordpress.workbench_across`) get the operations the PRD's
table names for them, planned here as
:class:`~quill.core.wordpress.workbench_by_name.Edit` objects the window
previews item by item before anything is sent:

- **Convert to Block** (:func:`plan_convert`): a core shortcode becomes the
  core block WordPress's own editor makes of it -- ``[gallery]`` a Gallery of
  Image blocks, ``[caption]`` an Image with its caption, ``[audio]``,
  ``[video]`` and ``[embed]`` theirs. ``[playlist]`` has no core block, so it
  is said and left. A shortcode QUILL cannot turn into a block faithfully (a
  gallery whose pictures are not in the Media Library as read, an audio file
  with no address) stays as it is, and the preview names it.
- **Update Pattern Everywhere** (:func:`pattern_update_edit`): a synced
  pattern is one record, so changing its content once changes every page
  placing it.
- **Detach Copies** (:func:`plan_detach`): chosen pages get the pattern's own
  blocks in place of the ``wp:block`` reference, as the editor's Detach does.
- **Pages Using This Plugin's Blocks** (:func:`namespace_uses`): before a
  plugin is removed, every page using a block from its namespace.

Every edit carries what the item was (undo) and its ``modified_gmt`` (the
conflict check in :func:`~quill.core.wordpress.workbench_by_name.apply_edits`).
Wx-free and network-free.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from quill.core.wordpress.workbench_by_name import Edit, _content, _item_edit, _title

__all__ = [
    "CONVERTIBLE",
    "NO_BLOCK",
    "block_namespace",
    "convert_shortcodes",
    "namespace_uses",
    "pattern_update_edit",
    "plan_convert",
    "plan_detach",
    "plugin_namespaces",
    "shortcode_of",
]

CONVERTIBLE = ("gallery", "caption", "audio", "video", "embed")
"""The core shortcodes with a core block to become."""

NO_BLOCK: Mapping[str, str] = {
    "playlist": "WordPress has no core playlist block, so [playlist] stays a shortcode",
    "wp_caption": "the old [wp_caption] is converted as [caption] is; rename it first",
}

_ATTR = re.compile(
    r"""([\w-]+)\s*=\s*"([^"]*)"|([\w-]+)\s*=\s*'([^']*)'|([\w-]+)\s*=\s*([^\s'"\]]+)"""
)
_BLOCK = re.compile(r"<!--\s+wp:([a-z0-9/-]+)(?:\s+\{.*?\})?\s+/?-->")
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_AUDIO_KEYS = ("src", "mp3", "m4a", "ogg", "wav")
_VIDEO_KEYS = ("src", "mp4", "m4v", "webm", "ogv", "wmv", "flv")


def shortcode_of(value: str) -> str:
    """``gallery`` from a row value such as ``[gallery] shortcode``; ``""`` for a block."""
    match = re.fullmatch(r"\[([a-z][a-z0-9_-]*)\] shortcode", value.strip())
    return match.group(1) if match else ""


def _attrs(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in _ATTR.finditer(text):
        key = match.group(1) or match.group(3) or match.group(5)
        value = (
            match.group(2)
            if match.group(1)
            else match.group(4)
            if match.group(3)
            else match.group(6)
        )
        found[key.lower()] = value or ""
    return found


def _patterns(code: str) -> tuple[re.Pattern[str], re.Pattern[str]]:
    """One use of ``[code ...]`` (with its closing tag when it has one): alone in a
    Shortcode block, which goes with it, then anywhere else."""
    name = re.escape(code)
    use = (
        rf"\[{name}(?P<attrs>(?:\s[^\]]*)?)\]"
        rf"(?:(?P<inner>(?:(?!\[{name}[\s\]]).)*?)\[/{name}\])?"
    )
    wrapped = re.compile(
        rf"<!--\s+wp:shortcode\s+-->\s*{use}\s*<!--\s+/wp:shortcode\s+-->", re.DOTALL
    )
    return wrapped, re.compile(use, re.DOTALL)


def _q(value: str) -> str:
    return html.escape(value, quote=True)


def _comment(name: str, attrs: Mapping[str, Any]) -> str:
    said = f" {json.dumps(dict(attrs), separators=(',', ':'))}" if attrs else ""
    return f"<!-- wp:{name}{said} -->"


def _image(media: Mapping[str, Any]) -> str:
    ident = int(media.get("id", 0) or 0)
    src = _q(str(media.get("source_url", "") or ""))
    alt = _q(str(media.get("alt_text", "") or ""))
    return (
        f"{_comment('image', {'id': ident, 'sizeSlug': 'large', 'linkDestination': 'none'})}\n"
        f'<figure class="wp-block-image size-large"><img src="{src}" alt="{alt}" '
        f'class="wp-image-{ident}"/></figure>\n<!-- /wp:image -->'
    )


def _gallery(attrs: Mapping[str, str], item: Mapping[str, Any], media: Sequence[Any]) -> str:
    by_id = {int(m.get("id", 0) or 0): m for m in media}
    if attrs.get("ids"):
        wanted = [int(i) for i in re.findall(r"\d+", attrs["ids"])]
        missing = [i for i in wanted if i not in by_id]
        if missing:
            return (
                f"!its pictures {', '.join(map(str, missing))} are not in the Media Library as read"
            )
        pictures = [by_id[i] for i in wanted]
    else:
        here = int(item.get("id", 0) or 0)
        pictures = [m for m in media if int(m.get("post", 0) or 0) == here]
        pictures = [m for m in pictures if str(m.get("mime_type", "image/")).startswith("image/")]
        if not pictures:
            return "!it shows the item's attached pictures, and none were read"
    columns = int(attrs.get("columns", "3") or 3) if attrs.get("columns", "3").isdigit() else 3
    link = {"file": "media", "none": "none"}.get(attrs.get("link", ""), "attachment")
    head = _comment("gallery", {"columns": columns, "linkTo": link})
    inner = "\n".join(_image(m) for m in pictures)
    return (
        f'{head}\n<figure class="wp-block-gallery has-nested-images columns-{columns} '
        f'is-cropped">{inner}</figure>\n<!-- /wp:gallery -->'
    )


def _caption(attrs: Mapping[str, str], inner: str) -> str:
    image = _IMG.search(inner or "")
    if image is None:
        return "!it holds no picture"
    start = inner.rfind("<a ", 0, image.start())
    end = inner.find("</a>", image.end())
    if start != -1 and end != -1 and "</a>" not in inner[start : image.start()]:
        shown, text = inner[start : end + 4], inner[end + 4 :]
    else:
        shown, text = image.group(0), inner[image.end() :]
    found = re.search(r"\d+", attrs.get("id", ""))
    block: dict[str, Any] = {"id": int(found.group(0))} if found else {}
    align = attrs.get("align", "").removeprefix("align")
    classes = "wp-block-image"
    if align in ("left", "right", "center"):
        block["align"] = align
        classes += f" align{align}"
    caption = text.strip()
    figcaption = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ""
    figure = f'<figure class="{classes}">{shown}{figcaption}</figure>'
    return f"{_comment('image', block)}\n{figure}\n<!-- /wp:image -->"


def _media_tag(kind: str, attrs: Mapping[str, str], keys: Sequence[str]) -> str:
    src = next((attrs[k] for k in keys if attrs.get(k)), "")
    if not src:
        return f"!it names no {kind} file"
    extra = "".join(
        f" {flag}"
        for flag in ("autoplay", "loop", "muted")
        if attrs.get(flag) in ("on", "1", "true")
    )
    poster = f' poster="{_q(attrs["poster"])}"' if kind == "video" and attrs.get("poster") else ""
    return (
        f'<!-- wp:{kind} -->\n<figure class="wp-block-{kind}"><{kind} controls{extra}{poster} '
        f'src="{_q(src)}"></{kind}></figure>\n<!-- /wp:{kind} -->'
    )


def _embed(inner: str, attrs: Mapping[str, str]) -> str:
    url = (inner or attrs.get("src", "")).strip()
    if not re.match(r"https?://\S+$", url):
        return "!it names no address to embed"
    return (
        f'{_comment("embed", {"url": url})}\n<figure class="wp-block-embed"><div '
        f'class="wp-block-embed__wrapper">\n{_q(url)}\n</div></figure>\n<!-- /wp:embed -->'
    )


def _block_for(
    code: str, attrs: Mapping[str, str], inner: str, item: Mapping[str, Any], media: Sequence[Any]
) -> str:
    """The block markup for one use, or ``"!why not"``."""
    if code == "gallery":
        return _gallery(attrs, item, media)
    if code == "caption":
        return _caption(attrs, inner)
    if code == "audio":
        return _media_tag("audio", attrs, _AUDIO_KEYS)
    if code == "video":
        return _media_tag("video", attrs, _VIDEO_KEYS)
    if code == "embed":
        return _embed(inner, attrs)
    return "!" + NO_BLOCK.get(code, f"[{code}] has no core block QUILL knows")


def convert_shortcodes(
    text: str, code: str, item: Mapping[str, Any], media: Sequence[Any]
) -> tuple[str, int, list[str]]:
    """*text* with every ``[code]`` QUILL can convert made a block: (text, how many, why not)."""
    made = 0
    kept: list[str] = []

    def one(match: re.Match[str]) -> str:
        nonlocal made
        attrs = _attrs(match.group("attrs") or "")
        got = _block_for(code, attrs, match.group("inner") or "", item, media)
        if got.startswith("!"):
            kept.append(got[1:])
            # Kept as found; the bare pass must not try it again, so it is fenced off.
            return "\0" + match.group(0) + "\0"
        made += 1
        return got

    wrapped, bare = _patterns(code)
    text = wrapped.sub(one, text)
    parts = text.split("\0")
    # Odd parts were kept whole in the first pass; only the even ones are looked at again.
    text = "".join(p if i % 2 else bare.sub(one, p).replace("\0", "") for i, p in enumerate(parts))
    return text, made, kept


def plan_convert(
    scan: Any, value: str, item_ids: Iterable[int] | None = None
) -> tuple[list[Edit], list[str]]:
    """Convert the shortcode of row *value* to its block on every item (or the chosen ones).

    Returns the edits and one line for each use left as it is, with why.
    """
    code = shortcode_of(value)
    if not code:
        return [], ["A block is already a block; only a shortcode is converted."]
    if code not in CONVERTIBLE:
        return [], [NO_BLOCK.get(code, f"[{code}] is not a core shortcode with a core block") + "."]
    chosen = None if item_ids is None else set(item_ids)
    edits: list[Edit] = []
    left: list[str] = []
    for raw in scan.items:
        if chosen is not None and int(raw.get("id", 0) or 0) not in chosen:
            continue
        text = _content(raw)
        if f"[{code}" not in text:
            continue
        changed, made, kept = convert_shortcodes(text, code, raw, scan.media)
        left += [f"{scan.site}: {_title(raw)}: one [{code}] stays, because {why}" for why in kept]
        if made:
            noun = "use becomes" if made == 1 else "uses become"
            words = f"{made} [{code}] {noun} the {code} block"
            edits.append(_item_edit(scan.site, raw, {"content": changed}, {"content": text}, words))
    return edits, left


# -- synced patterns -----------------------------------------------------------------


def _ref_pattern(pattern_id: int) -> re.Pattern[str]:
    return re.compile(
        rf'<!--\s+wp:block\s+\{{[^}}]*"ref"\s*:\s*{int(pattern_id)}\b[^}}]*\}}\s+/-->'
    )


def pattern_update_edit(
    site: str, pattern: Mapping[str, Any], content: str, uses: int
) -> Edit | None:
    """The one edit that changes a synced pattern's content everywhere; None when unchanged."""
    old = str(_content(pattern))
    if content == old:
        return None
    title = _title(pattern)
    places = f"the {uses} pages placing it" if uses != 1 else "the page placing it"
    return Edit(
        site,
        f"wp/v2/blocks/{pattern.get('id')}",
        title,
        {"content": content},
        {"content": old},
        "modified_gmt",
        pattern.get("modified_gmt"),
        f"its content changes once, and {places} show the change",
    )


def plan_detach(
    scan: Any, pattern_id: int, content: str, item_ids: Iterable[int] | None = None
) -> list[Edit]:
    """Put the pattern's blocks in place of each reference to it, on every (or each chosen) item."""
    chosen = None if item_ids is None else set(item_ids)
    pattern = _ref_pattern(pattern_id)
    name = scan.patterns.get(int(pattern_id), f"pattern {pattern_id}")
    edits: list[Edit] = []
    for raw in scan.items:
        if chosen is not None and int(raw.get("id", 0) or 0) not in chosen:
            continue
        text = _content(raw)
        changed, count = pattern.subn(lambda _m: content, text)
        if count:
            words = f"{name} becomes its own blocks here, no longer synced"
            edits.append(_item_edit(scan.site, raw, {"content": changed}, {"content": text}, words))
    return edits


def pattern_items(scan: Any, pattern_id: int) -> list[Mapping[str, Any]]:
    """The items that place the synced pattern *pattern_id*."""
    pattern = _ref_pattern(pattern_id)
    return [raw for raw in scan.items if pattern.search(_content(raw))]


# -- a plugin's blocks ---------------------------------------------------------------


def block_namespace(value: str) -> str:
    """``jetpack`` from ``jetpack/slideshow block``; ``core`` for a core block; ``""`` otherwise."""
    match = re.fullmatch(r"([a-z0-9-]+)(?:/([a-z0-9-]+))? block", value.strip())
    if match is None:
        return ""
    return match.group(1) if match.group(2) else "core"


def plugin_namespaces(plugin: Mapping[str, Any]) -> list[str]:
    """The block namespaces a plugin's blocks most likely use: its text domain and folder."""
    found = [
        str(plugin.get("textdomain", "") or ""),
        str(plugin.get("plugin", "") or "").partition("/")[0],
    ]
    return [n.lower() for n in dict.fromkeys(found) if n and n.lower() != "core"]


def namespace_uses(scan: Any, namespaces: Sequence[str]) -> list[tuple[str, list[str]]]:
    """(item title, the blocks it uses from *namespaces*) for every item using one."""
    wanted = {n.lower() for n in namespaces if n}
    found: list[tuple[str, list[str]]] = []
    for raw in scan.items:
        names = sorted({
            name
            for name in _BLOCK.findall(_content(raw))
            if name.partition("/")[0] in wanted and "/" in name
        })
        if names:
            found.append((_title(raw), names))
    return found
