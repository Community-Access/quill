"""Big uploads, and Regenerate Sizes (wordpress.md 9.16).

**Big uploads.** WordPress has no way to take one file in pieces: the
``media/{id}/sideload`` route that looks like one (WordPress 7.1) takes a
picture's *sub-size* (``image_size`` is required), and ``finalize`` takes the
list of those sizes. An earlier QUILL sent pieces of a video there, which no
site can accept. So a big file goes up in one request on a background task,
like any other upload, and :data:`LARGE_FROM` only decides when QUILL first
says how big it is and that it can take a while. If the host refuses the size,
the site's own words (``rest_upload_file_too_big``, or a 413) are what the
person hears.

**Regenerate Sizes.** After a picture is edited on the site,
``media/{id}/post-process`` remakes its thumbnail and medium copies, so the
theme shows the edit everywhere.

Wx-free.
"""

from __future__ import annotations

from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site_media import MediaItem, media_from_payload

#: Files from this size get a word first that the upload can take a while.
LARGE_FROM = 16 * 1024 * 1024


def regenerate_sizes(api: WordPressApi, media_id: int) -> MediaItem:
    """Remake a picture's thumbnail and other sizes from its current original."""
    api.post(f"wp/v2/media/{media_id}/post-process", {"action": "create-image-subsizes"})
    return media_from_payload(api.get(f"wp/v2/media/{media_id}", context="edit"))
