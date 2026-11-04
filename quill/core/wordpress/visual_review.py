"""Visual Review and the site logo, in words (wordpress.md 6.10, 6.11, 6.12).

What the AI is asked, what the report says, and what the site logo settings
mean -- everything about these commands that has no window and no network in
it, so it is tested directly. The capture itself is
:mod:`quill.core.wordpress.page_capture`; the commands are
:mod:`quill.ui.wordpress_picture_commands`.

Stdlib and Pillow, no wx.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.page_capture import Capture, image_state

__all__ = [
    "LOGO_SETTINGS",
    "LogoSetting",
    "PREVIEW_NEEDS_PUBLISHED",
    "UNPUBLISHED_NOTE",
    "combine_screenshots",
    "consent_text",
    "facts_lines",
    "image_width_style",
    "load_logo_history",
    "logo_settings",
    "logo_width_style",
    "picture_markup",
    "remember_logo",
    "report_text",
    "review_instruction",
]

UNPUBLISHED_NOTE = "This reviews the page as published. Your unpublished changes are not in it."

PREVIEW_NEEDS_PUBLISHED = (
    "Preview and Review works on the published page. A draft's preview opens only for "
    "someone signed in to WordPress in a browser, and QUILL's application password works "
    "for the site's API, not for that sign-in, so QUILL cannot capture a draft. Publish the "
    "page first, or open the draft with Open on Site to check it yourself. Unpublished text "
    "is never in a review."
)

_PAGE_TEXT_LIMIT = 8_000

#: The two theme settings Site Logo shows: (setting, what a person calls it).
LOGO_SETTINGS: tuple[tuple[str, str], ...] = (("site_logo", "Logo"), ("site_icon", "Site icon"))


# --------------------------------------------------------------------------- #
# Visual Review


def facts_lines(capture: Capture) -> list[str]:
    """One line per image, across the views: where it is, its sizes, alt text and state."""
    by_src: dict[str, list[tuple[str, Any, str]]] = {}
    order: list[str] = []
    for view in capture.views:
        for fact in view.images:
            if fact.src not in by_src:
                by_src[fact.src] = []
                order.append(fact.src)
            by_src[fact.src].append((view.view.name, fact, image_state(fact, view.captured_height)))
    lines: list[str] = []
    for number, src in enumerate(order, start=1):
        seen = by_src[src]
        first = seen[0][1]
        where = f"below '{first.heading}'" if first.heading else "above the first heading"
        sizes = "; ".join(
            f"{name} {fact.width} by {fact.height}"
            + (", spills out of the content area" if fact.overflows else "")
            + ("" if state == "loaded" else f", {state}")
            for name, fact, state in seen
        )
        if first.alt is None:
            alt = "no alt attribute"
        elif not first.alt.strip():
            alt = "empty alt text (marked decorative)"
        else:
            alt = f"alt text '{first.alt.strip()}'"
        real = (
            f", file is {first.natural_width} by {first.natural_height}"
            if first.natural_width
            else ""
        )
        lines.append(f"Image {number}, {first.name}, {where}: {sizes}; {alt}{real}.")
    return lines


def review_instruction(capture: Capture, *, proposal: str = "", unpublished: bool = False) -> str:
    """What the AI is asked, with the measured facts and the page text."""
    views = ", ".join(f"{v.view.name} ({v.view.width} pixels wide)" for v in capture.views)
    text = next((v.text for v in capture.views if v.text), "")
    if len(text) > _PAGE_TEXT_LIMIT:
        text = text[:_PAGE_TEXT_LIMIT] + "\n[The rest of the text was left out.]"
    facts = "\n".join(facts_lines(capture)) or "There are no images on this page."
    lines = [
        "You are helping a blind website owner understand what a sighted visitor sees on "
        "their published web page. The picture shows the page side by side: "
        f"{views}, left to right.",
        "Write plain text with these headings: Overall impression; Desktop layout; Phone "
        "layout; Spacing and balance; What works well; then Images, with one entry per image "
        "in the order below: where it is, its measured size on each view, its existing alt "
        "text, a fresh description of what it shows, and whether it suits the text around "
        "it. Where a different display width would help, say the width in pixels.",
        "Label every finding as one of: likely a problem; a design choice you may want; "
        "worth checking.",
        "These measurements were taken by the browser. They are facts: do not contradict "
        "them. 'Failed to load', 'had not finished loading' and 'not captured' are different "
        "things; never call an image broken unless it failed to load.",
    ]
    if proposal:
        lines.append(
            f"This is a preview of a proposed change, injected only into this capture: "
            f"{proposal}. Say whether the change looks right on both views."
        )
    if unpublished:
        lines.append("The owner has unpublished changes; they are not in this capture.")
    lines.append(f"Measured images:\n{facts}")
    lines.append(f"Page text:\n{text}")
    return "\n\n".join(lines)


def consent_text(site_name: str, url: str, capture: Capture) -> str:
    """What will be sent, said before anything is sent (6.11, 6.12)."""
    count = sum(len(v.images) for v in capture.views[:1])
    images = "1 image" if count == 1 else f"{count} images"
    return (
        f"Send the desktop and phone screenshots of {url} on {site_name}, the page's text and "
        f"the measurements of its {images} to your chosen AI for a Visual Review? Capturing "
        "sent nothing anywhere except a normal visit to the public page."
    )


def report_text(
    site_name: str, capture: Capture, answer: str, *, notes: list[str] | None = None
) -> str:
    """The read-only report: notes first, the AI's review, then the measured facts."""
    parts = [f"Visual Review of {capture.url} on {site_name}"]
    if capture.browser:
        parts[0] += f", captured with {capture.browser}"
    parts[0] += "."
    parts.extend(note for note in (notes or []) if note)
    parts.append(answer.strip() or "The AI sent back no review.")
    facts = facts_lines(capture)
    if facts:
        parts.append("Measured by the browser:\n" + "\n".join(facts))
    return "\n\n".join(parts)


def combine_screenshots(capture: Capture, out_path: Path, *, max_height: int = 4000) -> Path:
    """The views side by side in one PNG, desktop first, for an AI that takes one picture."""
    from PIL import Image

    pictures = []
    for view in capture.views:
        with Image.open(view.screenshot) as source:
            picture = source.convert("RGB")
        if picture.height > max_height:
            width = max(1, round(picture.width * max_height / picture.height))
            picture = picture.resize((width, max_height))
        pictures.append(picture)
    gap = 40
    width = sum(p.width for p in pictures) + gap * max(0, len(pictures) - 1)
    height = max((p.height for p in pictures), default=1)
    sheet = Image.new("RGB", (max(1, width), height), (128, 128, 128))
    x = 0
    for picture in pictures:
        sheet.paste(picture, (x, 0))
        x += picture.width + gap
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="PNG")
    return out_path


def image_width_style(file_name: str, width: int) -> str:
    """A style showing images whose address contains *file_name* at *width* pixels."""
    safe = file_name.replace("\\", "").replace('"', "")
    return (
        f'img[src*="{safe}"], img[srcset*="{safe}"] '
        f"{{ width: {int(width)}px !important; max-width: 100% !important; "
        "height: auto !important; }"
    )


def logo_width_style(width: int) -> str:
    """A style showing the theme's logo at *width* pixels (6.10)."""
    return (
        ".custom-logo, .wp-block-site-logo img, .site-logo img "
        f"{{ width: {int(width)}px !important; max-width: 100% !important; "
        "height: auto !important; }"
    )


# --------------------------------------------------------------------------- #
# The site logo (6.10)


@dataclass(frozen=True)
class LogoSetting:
    key: str  # "site_logo" or "site_icon"
    label: str
    media_id: int
    supported: bool  # the theme and WordPress offer this setting at all


def logo_settings(payload: Any) -> list[LogoSetting]:
    """The logo and icon in a ``wp/v2/settings`` answer; ``supported`` False when absent."""
    data = payload if isinstance(payload, dict) else {}
    found: list[LogoSetting] = []
    for key, label in LOGO_SETTINGS:
        raw = data.get(key)
        try:
            media_id = int(raw or 0)
        except (TypeError, ValueError):
            media_id = 0
        found.append(LogoSetting(key, label, media_id, key in data))
    return found


def _history_path(root: Path, site_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in site_id) or "site"
    return root / "logos" / f"{safe}.json"


def load_logo_history(root: Path, site_id: str) -> list[dict[str, Any]]:
    """What QUILL replaced on this site, newest first: setting, media id, label, when."""
    raw = read_json(_history_path(root, site_id), default=[])
    return [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []


def remember_logo(
    root: Path, site_id: str, *, key: str, media_id: int, label: str, when: str
) -> None:
    """Keep the value a replace took away, so Restore Earlier can put it back."""
    rows = load_logo_history(root, site_id)
    rows.insert(0, {"key": key, "media_id": int(media_id), "label": label, "when": when})
    write_json_atomic(_history_path(root, site_id), rows[:20])


# --------------------------------------------------------------------------- #
# A made picture, inserted (6.9)


def picture_markup(text_format: str, url: str, alt: str, caption: str, media_id: int) -> str:
    """The picture as the document writes it: QUILL's Markdown line, or its image block."""
    safe_alt = alt.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    line = f"![{safe_alt}]({url}"
    if caption.strip():
        line += ' "' + caption.strip().replace("\\", "\\\\").replace('"', '\\"') + '"'
    line += ")" + (f" {{id={int(media_id)}}}" if media_id else "")
    if text_format == "html":
        from quill.core.wordpress import fences

        return "\n" + fences.convert_markdown(line, {}).html.strip() + "\n"
    return f"\n{line}\n"
