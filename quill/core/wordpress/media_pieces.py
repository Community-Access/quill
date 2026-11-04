"""Big uploads in pieces, and Regenerate Sizes (wordpress.md 9.16).

**In pieces.** A long video or a big audio file in one request is the upload
that fails on a shared host: a time-out or a size limit halfway, and nothing
to show for it. QUILL sends the first piece to ``wp/v2/media``, which makes
the library item, each later piece to ``media/{id}/sideload`` with its
``Content-Range``, and then asks ``media/{id}/finalize`` to join them. Progress
is reported after every piece, so it can be spoken ("Uploading 3 of 10").

**Regenerate Sizes.** After a picture is edited on the site,
``media/{id}/post-process`` remakes its thumbnail and medium copies, so the
theme shows the edit everywhere.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site_media import MediaItem, media_from_payload

#: Pieces of 4 MB: under the smallest upload limit shared hosts commonly set.
PIECE_SIZE = 4 * 1024 * 1024
#: Files above this go in pieces; smaller ones are one ordinary upload.
PIECES_FROM = 16 * 1024 * 1024


def piece_count(size: int, piece_size: int = PIECE_SIZE) -> int:
    return max(1, -(-size // piece_size))


@dataclass
class PieceUpload:
    """One big file on its way up, a piece at a time, so each step can be spoken."""

    filename: str
    content: bytes
    content_type: str
    title: str = ""
    piece_size: int = PIECE_SIZE
    media_id: int = 0
    sent: int = 0
    payload: Any = None

    @property
    def count(self) -> int:
        return piece_count(len(self.content), self.piece_size)

    @property
    def finished(self) -> bool:
        return self.sent >= self.count

    def _headers(self, start: int, end: int) -> dict[str, str]:
        safe = self.filename.replace('"', "").replace("\r", "").replace("\n", "")
        return {
            "Content-Type": self.content_type,
            "Content-Disposition": f'attachment; filename="{safe}"',
            "Content-Range": f"bytes {start}-{end - 1}/{len(self.content)}",
        }

    def send_next(self, api: WordPressApi) -> None:
        """Send the next piece: the first makes the library item, the rest join it."""
        start = self.sent * self.piece_size
        end = min(start + self.piece_size, len(self.content))
        route = "wp/v2/media" if self.sent == 0 else f"wp/v2/media/{self.media_id}/sideload"
        raw = api.request(
            "POST", route, data=self.content[start:end], headers=self._headers(start, end)
        ).payload
        if self.sent == 0:
            self.media_id = int(raw.get("id", 0)) if isinstance(raw, dict) else 0
            self.payload = raw
        self.sent += 1

    def finish(self, api: WordPressApi) -> MediaItem:
        raw: Any = self.payload
        if self.count > 1:
            raw = api.post(
                f"wp/v2/media/{self.media_id}/finalize",
                {"total": len(self.content), "pieces": self.count},
            )
        if self.title:
            raw = api.post(f"wp/v2/media/{self.media_id}", {"title": self.title}, context="edit")
        return media_from_payload(raw if isinstance(raw, dict) else {"id": self.media_id})


def upload_in_pieces(
    api: WordPressApi,
    upload: PieceUpload,
    progress: Callable[[int, int], None] | None = None,
) -> MediaItem:
    """Every piece in one go (for callers that need no step-by-step speech)."""
    while not upload.finished:
        upload.send_next(api)
        if progress is not None:
            progress(upload.sent, upload.count)
    return upload.finish(api)


def regenerate_sizes(api: WordPressApi, media_id: int) -> MediaItem:
    """Remake a picture's thumbnail and other sizes from its current original."""
    api.post(f"wp/v2/media/{media_id}/post-process", {"action": "create-image-subsizes"})
    return media_from_payload(api.get(f"wp/v2/media/{media_id}", context="edit"))
