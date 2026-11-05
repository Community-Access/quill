"""Pictures, more from the API: sizes, editing on the site, and the library's alt text.

Plan: wordpress.md 9.15 ("Pictures", and "Library-wide alternative text").

- **Sizes.** Every picture in the library comes with the sizes WordPress made
  of it (``media_details.sizes``). The image dialog offers them by name and
  width, so "Medium, 300 wide" uses the site's smaller file.
- **Edit a picture on the site** (``POST media/{id}/edit``, WordPress 5.5+):
  rotate, flip and crop to a ratio. WordPress keeps the original and makes the
  edit a new library item. A crop to a ratio is centred, in the percentages
  the route takes, worked out after any turn.
- **The whole library's alternative text.** Every picture with none, and
  saving what was written in batches.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.media_tools import SIZE_LABELS
from quill.core.wordpress.site_media import MediaItem, list_media, media_from_payload

# --------------------------------------------------------------------------- #
# Sizes (choose one when inserting)


@dataclass(frozen=True)
class SizeChoice:
    slug: str
    width: int
    height: int
    source_url: str

    def spoken(self) -> str:
        label = SIZE_LABELS.get(self.slug, self.slug.replace("_", " ").replace("-", " ").title())
        return f"{label}, {self.width} wide" if self.width else label


def dialog_sizes(item: MediaItem) -> list[tuple[str, str, str]]:
    """``(spoken, slug, address)`` rows for the image dialog; the full size last.

    Empty when the library made no smaller sizes, so the dialog shows no
    choice at all rather than a list of one.
    """
    choices = [SizeChoice(slug, width, height, url) for slug, width, height, url in item.sizes]
    if not any(c.slug != "full" for c in choices):
        return []
    if not any(c.slug == "full" for c in choices):
        choices.append(SizeChoice("full", item.width, item.height, item.source_url))
    choices.sort(key=lambda s: (s.slug == "full", s.width))
    return [(c.spoken(), c.slug, c.source_url) for c in choices]


# --------------------------------------------------------------------------- #
# Edit a picture on the site


@dataclass(frozen=True)
class PictureEdit:
    """One edit: what it is called, and the route's modifier type it needs."""

    label: str
    needs: str  # "rotate", "flip" or "crop"
    angle: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    ratio: tuple[int, int] = (0, 0)

    def modifiers(self, width: int, height: int) -> list[dict[str, Any]]:
        if self.needs == "rotate":
            return [{"type": "rotate", "args": {"angle": self.angle}}]
        if self.needs == "flip":
            return [
                {
                    "type": "flip",
                    "args": {
                        "flip": {
                            "horizontal": self.flip_horizontal,
                            "vertical": self.flip_vertical,
                        }
                    },
                }
            ]
        return [{"type": "crop", "args": centred_crop(width, height, *self.ratio)}]


EDITS: tuple[PictureEdit, ...] = (
    PictureEdit("Turn a quarter to the right", "rotate", angle=90),
    PictureEdit("Turn a quarter to the left", "rotate", angle=270),
    PictureEdit("Turn upside down", "rotate", angle=180),
    PictureEdit("Flip left to right, as in a mirror", "flip", flip_horizontal=True),
    PictureEdit("Flip top to bottom", "flip", flip_vertical=True),
    PictureEdit("Crop to a square", "crop", ratio=(1, 1)),
    PictureEdit("Crop to 4 by 3, landscape", "crop", ratio=(4, 3)),
    PictureEdit("Crop to 16 by 9, widescreen", "crop", ratio=(16, 9)),
    PictureEdit("Crop to 3 by 4, portrait", "crop", ratio=(3, 4)),
)


def offered(modifiers: Iterable[str], item: MediaItem) -> list[PictureEdit]:
    """The edits this site takes; a crop needs the picture's size to centre it."""
    allowed = set(modifiers)
    return [
        e
        for e in EDITS
        if e.needs in allowed and (e.needs != "crop" or (item.width and item.height))
    ]


def centred_crop(width: int, height: int, ratio_w: int, ratio_h: int) -> dict[str, float]:
    """The largest centred box of *ratio_w*:*ratio_h*, in percentages of the picture."""
    if width <= 0 or height <= 0 or ratio_w <= 0 or ratio_h <= 0:
        return {"left": 0.0, "top": 0.0, "width": 100.0, "height": 100.0}
    target = ratio_w / ratio_h
    if width / height > target:
        crop_width = height * target
        left = (width - crop_width) / 2
        return {
            "left": round(left / width * 100, 4),
            "top": 0.0,
            "width": round(crop_width / width * 100, 4),
            "height": 100.0,
        }
    crop_height = width / target
    top = (height - crop_height) / 2
    return {
        "left": 0.0,
        "top": round(top / height * 100, 4),
        "width": 100.0,
        "height": round(crop_height / height * 100, 4),
    }


def result_size(edit: PictureEdit, width: int, height: int) -> tuple[int, int]:
    """Roughly how big the new picture will be, for the confirmation."""
    if edit.needs == "rotate" and edit.angle in (90, 270):
        return height, width
    if edit.needs == "crop":
        box = centred_crop(width, height, *edit.ratio)
        return round(width * box["width"] / 100), round(height * box["height"] / 100)
    return width, height


def edit_on_site(api: WordPressApi, item: MediaItem, edit: PictureEdit) -> MediaItem:
    raw = api.post(
        f"wp/v2/media/{item.id}/edit",
        {"src": item.source_url, "modifiers": edit.modifiers(item.width, item.height)},
        context="edit",
    )
    return media_from_payload(raw)


# --------------------------------------------------------------------------- #
# The whole library's alternative text

#: How many written descriptions are kept before they are saved together.
BATCH_SIZE = 10


def pictures_without_alt(api: WordPressApi) -> list[MediaItem]:
    return [m for m in list_media(api, media_type="image") if not m.alt_text.strip()]


def save_alt_texts(api: WordPressApi, texts: Mapping[int, str], *, can_batch: bool) -> list[int]:
    """Save every ``id -> alternative text``; the ids saved, in order.

    One ``batch/v1`` request per 25 where the site batches; otherwise one
    request each. A refused item in a batch does not stop the rest.
    """
    ids = sorted(texts)
    if not ids:
        return []
    if can_batch:
        answers = api.batch([
            {"method": "POST", "path": f"/wp/v2/media/{i}", "body": {"alt_text": texts[i]}}
            for i in ids
        ])
        saved = [
            i
            for i, answer in zip(ids, answers, strict=False)
            if 200 <= int(answer.get("status", 200) or 200) < 300
        ]
        if answers:
            return saved
    saved = []
    for media_id in ids:
        try:
            api.post(f"wp/v2/media/{media_id}", {"alt_text": texts[media_id]})
        except WordPressApiError:
            continue
        saved.append(media_id)
    return saved


def library_row(item: MediaItem, written: Mapping[int, str], saved: Sequence[int]) -> str:
    name = item.title or item.filename
    if item.id in saved:
        return f"{name}, saved: {written.get(item.id, '')}"
    if item.id in written:
        return f"{name}, written, not saved yet: {written[item.id]}"
    return f"{name}, no alternative text"
