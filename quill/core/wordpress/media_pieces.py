"""Big uploads, and Regenerate Sizes (wordpress.md 9.16).

**Big uploads.** WordPress has no way to take one file in pieces: the
``media/{id}/sideload`` route that looks like one (WordPress 7.1) takes a
picture's *sub-size* (``image_size`` is required), and ``finalize`` takes the
list of those sizes. An earlier QUILL sent pieces of a video there, which no
site can accept. So a big file goes up in one request on a background task,
like any other upload, and :data:`LARGE_FROM` only decides when QUILL first
says how big it is and that it can take a while. If the host refuses the size,
the site's own words (``rest_upload_file_too_big``, or a 413) are what the
person hears, and the upload starts again from the beginning next time: with
no upload in pieces there is nothing to resume from. :func:`detail_fields`
and :func:`detail_changes` are the details step that follows a big upload.

**Regenerate Sizes.** After a picture is edited on the site,
``media/{id}/post-process`` remakes its thumbnail and medium copies, so the
theme shows the edit everywhere.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.block_catalog import Field
from quill.core.wordpress.site_media import MediaItem, media_from_payload

#: Files from this size get a word first that the upload can take a while.
LARGE_FROM = 16 * 1024 * 1024


def regenerate_sizes(api: WordPressApi, media_id: int) -> MediaItem:
    """Remake a picture's thumbnail and other sizes from its current original."""
    api.post(f"wp/v2/media/{media_id}/post-process", {"action": "create-image-subsizes"})
    return media_from_payload(api.get(f"wp/v2/media/{media_id}", context="edit"))


def detail_fields(media: MediaItem) -> list[Field]:
    """The details step after a big upload: title, alt text (pictures), caption, description."""
    fields = [
        Field("title", "&Title:", "text", "The file's name in the Media Library.", media.title)
    ]
    if media.kind_label == "image":
        fields.append(
            Field("alt_text", "&Alt text:", "text", "What the picture shows.", media.alt_text)
        )
    fields += [
        Field("caption", "&Caption:", "multiline", "Shown under it on the page.", media.caption),
        Field(
            "description",
            "&Description:",
            "multiline",
            "A longer description, such as a transcript's summary.",
            media.description,
        ),
    ]
    return fields


def detail_changes(media: MediaItem, answers: Mapping[str, Any]) -> dict[str, str]:
    """Only what the person changed, so a Save Details that changes nothing sends nothing."""
    now = {
        "title": media.title,
        "alt_text": media.alt_text,
        "caption": media.caption,
        "description": media.description,
    }
    return {
        key: str(value).strip()
        for key, value in answers.items()
        if key in now and str(value).strip() != now[key]
    }
