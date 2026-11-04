"""The picture helpers the media commands share (wordpress.md 6.4).

The commands that lived here moved: comments and categories and tags to
``wordpress_admin_commands.py`` and ``wordpress_terms_commands.py`` (9.8, 9.13),
and the Media Library window and Insert Picture to
``wordpress_media_library.py`` (6.1, 6.4). :class:`WordPressSiteCommands` is
empty and stays only because :class:`~quill.ui.wordpress_commands.WordPressCommands`
lists it; the helpers below are imported by the media modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_item_dialogs as idlg


class WordPressSiteCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore


def picture_markup(
    text_format: str, src: str, answer: idlg.ImageAnswer, *, media_id: int = 0
) -> str:
    alt = answer.alt.replace('"', "'")
    if text_format == "markdown":
        caption = f' "{answer.caption}"' if answer.caption else ""
        extra = f" {{id={media_id}}}" if media_id else ""
        return f"\n![{alt}]({src}{caption}){extra}\n"
    width = f' width="{answer.width}"' if answer.width > 0 else ""
    decorative = ' role="presentation"' if answer.decorative else ""
    css = f' class="wp-image-{media_id}"' if media_id else ""
    img = f'<img src="{src}" alt="{alt}"{css}{width}{decorative}/>'
    if answer.link == "file":
        img = f'<a href="{src}">{img}</a>'
    elif answer.link:
        img = f'<a href="{answer.link}">{img}</a>'
    caption = f"<figcaption>{answer.caption}</figcaption>" if answer.caption else ""
    return f'\n<figure class="wp-block-image">{img}{caption}</figure>\n'


def picture_size_text(path: Path) -> str:
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
        return f"image is {width} by {height}, {wp.human_size(path.stat().st_size)}"
    except Exception:  # noqa: BLE001 - a picture Pillow cannot read still inserts
        return wp.human_size(path.stat().st_size)


def backup_media(api: Any, media: wpm.MediaItem, site_name: str) -> Path:
    """Download a copy before a permanent removal (6.3)."""
    from urllib.request import Request

    folder = Path.home() / "Documents" / "Removed from WordPress" / site_name
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (media.filename or f"media-{media.id}")
    request = Request(media.source_url, headers={"User-Agent": "QUILL"})
    with api._opener(request, timeout=api.timeout) as response:
        target.write_bytes(response.read())
    return target
