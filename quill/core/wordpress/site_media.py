"""Media and comments on a WordPress site (wordpress.md 6, 9.8).

Split from :mod:`quill.core.wordpress.site`, which holds pages, posts, terms
and the account; the same rules apply: one function per action, plain
dataclasses back, every request through :class:`WordPressApi`.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import friendly_date, human_size, plain_text, raw_text

# --------------------------------------------------------------------------- #
# Media (wordpress.md 6)


@dataclass(frozen=True)
class MediaItem:
    id: int
    title: str
    media_type: str  # image, file
    mime_type: str
    source_url: str
    alt_text: str
    caption: str
    description: str
    width: int
    height: int
    filesize: int
    date_gmt: str
    post: int  # attached to; 0 when unattached
    filename: str
    #: The sizes WordPress made of a picture: (slug, width, height, address) (9.15).
    sizes: tuple[tuple[str, int, int, str], ...] = ()

    def spoken(self) -> str:
        parts = [self.title or self.filename, self.kind_label]
        if self.width and self.height:
            parts.append(f"{self.width} by {self.height}")
        if self.filesize:
            parts.append(human_size(self.filesize))
        parts.append(f"alt text: {self.alt_text}" if self.alt_text else "no alt text")
        parts.append(f"uploaded {friendly_date(self.date_gmt)}")
        return ", ".join(parts)

    @property
    def kind_label(self) -> str:
        top = self.mime_type.split("/", 1)[0]
        return {"image": "image", "audio": "audio", "video": "video"}.get(top, "document")


def list_media(
    api: WordPressApi, *, search: str = "", media_type: str = "", unattached: bool = False
) -> Iterator[MediaItem]:
    params: dict[str, object] = {"context": "edit", "orderby": "date", "order": "desc"}
    if search.strip():
        params["search"] = search.strip()
    if media_type in {"image", "audio", "video", "application"}:
        params["media_type"] = media_type
    if unattached:
        params["parent"] = 0
    for raw in api.iter_collection("wp/v2/media", params):
        yield media_from_payload(raw)


def media_from_payload(raw: Any) -> MediaItem:
    details = raw.get("media_details", {}) if isinstance(raw.get("media_details"), dict) else {}
    source = str(raw.get("source_url", ""))
    return MediaItem(
        id=int(raw.get("id", 0)),
        title=raw_text(raw.get("title")),
        media_type=str(raw.get("media_type", "")),
        mime_type=str(raw.get("mime_type", "")),
        source_url=source,
        alt_text=str(raw.get("alt_text", "") or ""),
        caption=raw_text(raw.get("caption")),
        description=raw_text(raw.get("description")),
        width=int(details.get("width", 0) or 0),
        height=int(details.get("height", 0) or 0),
        filesize=int(details.get("filesize", 0) or 0),
        date_gmt=str(raw.get("date_gmt", "") or ""),
        post=int(raw.get("post", 0) or 0),
        filename=source.rsplit("/", 1)[-1] if source else "",
        sizes=_sizes(details),
    )


def _sizes(details: dict[str, Any]) -> tuple[tuple[str, int, int, str], ...]:
    sizes = details.get("sizes")
    return tuple(
        (
            str(slug),
            int(size.get("width", 0) or 0),
            int(size.get("height", 0) or 0),
            str(size["source_url"]),
        )
        for slug, size in (sizes.items() if isinstance(sizes, dict) else [])
        if isinstance(size, dict) and size.get("source_url")
    )


def upload_media(
    api: WordPressApi,
    filename: str,
    content: bytes,
    content_type: str,
    *,
    title: str = "",
    alt_text: str = "",
    caption: str = "",
    post: int = 0,
) -> MediaItem:
    raw = api.upload("wp/v2/media", filename, content, content_type)
    item = media_from_payload(raw)
    fields: dict[str, object] = {}
    if title:
        fields["title"] = title
    if alt_text:
        fields["alt_text"] = alt_text
    if caption:
        fields["caption"] = caption
    if post:
        fields["post"] = post
    if fields:
        item = media_from_payload(api.post(f"wp/v2/media/{item.id}", fields, context="edit"))
    return item


def update_media(api: WordPressApi, media_id: int, **fields: object) -> MediaItem:
    allowed = {
        k: v
        for k, v in fields.items()
        if k in {"title", "alt_text", "caption", "description", "post"}
    }
    return media_from_payload(api.post(f"wp/v2/media/{media_id}", allowed, context="edit"))


def delete_media(api: WordPressApi, media_id: int) -> None:
    """Permanent: media has no Trash. Callers download a copy first (6.3)."""
    api.delete(f"wp/v2/media/{media_id}", force=True)


def find_duplicate_media(api: WordPressApi, filename: str, size: int) -> MediaItem | None:
    """The same file already in the library, by name and size (wordpress.md 6.2)."""
    stem = filename.rsplit(".", 1)[0]
    for item in list_media(api, search=stem):
        same_name = item.filename.lower() == filename.lower() or item.filename.lower().startswith(
            stem.lower()
        )
        if same_name and (not size or not item.filesize or item.filesize == size):
            return item
    return None


# --------------------------------------------------------------------------- #
# Comments (wordpress.md 9.8)


@dataclass(frozen=True)
class Comment:
    id: int
    post: int
    parent: int
    author_name: str
    date_gmt: str
    status: str
    content: str

    def spoken(self) -> str:
        words = plain_text(self.content)
        first = " ".join(words.split()[:12])
        return f"{self.author_name}, {friendly_date(self.date_gmt)}: {first}"


COMMENT_STATUSES = (
    ("hold", "Waiting"),
    ("approve", "Approved"),
    ("spam", "Spam"),
    ("trash", "Trash"),
)


def list_comments(api: WordPressApi, *, status: str = "hold", post: int = 0) -> list[Comment]:
    params: dict[str, object] = {"context": "edit", "status": status}
    if post:
        params["post"] = post
    return [_comment(raw) for raw in api.iter_collection("wp/v2/comments", params)]


def count_waiting_comments(api: WordPressApi) -> int:
    response = api.request(
        "GET",
        "wp/v2/comments",
        params={"status": "hold", "per_page": 1, "_fields": "id", "context": "edit"},
    )
    return response.total or (len(response.payload) if isinstance(response.payload, list) else 0)


def set_comment_status(api: WordPressApi, comment_id: int, status: str) -> Comment:
    return _comment(api.post(f"wp/v2/comments/{comment_id}", {"status": status}, context="edit"))


def reply_to_comment(api: WordPressApi, parent: Comment, content: str) -> Comment:
    return _comment(
        api.post(
            "wp/v2/comments",
            {"post": parent.post, "parent": parent.id, "content": content},
            context="edit",
        )
    )


def _comment(raw: Any) -> Comment:
    return Comment(
        id=int(raw.get("id", 0)),
        post=int(raw.get("post", 0) or 0),
        parent=int(raw.get("parent", 0) or 0),
        author_name=str(raw.get("author_name", "") or "Anonymous"),
        date_gmt=str(raw.get("date_gmt", "") or ""),
        status=str(raw.get("status", "")),
        content=raw_text(raw.get("content")),
    )
