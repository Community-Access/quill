"""Uploads, downloads, sizes and Used In for the Media Library (wordpress.md 6.1 to 6.5).

wx-free and strict-typed. The site is reached only through
:class:`~quill.core.wordpress.api.WordPressApi`; the one request that is not a
REST call -- fetching a file by web address before uploading it (6.2), or
fetching a library file to look at or shrink -- goes through the same
injected opener, so tests never touch a network and the egress audit has one
door to read.
"""

from __future__ import annotations

import io
import mimetypes
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import Request

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import human_size, raw_text
from quill.core.wordpress.site_media import MediaItem, list_media

#: The largest file Upload from Web Address will fetch. WordPress hosts rarely
#: accept more, and a cap keeps a wrong address from filling the disk.
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024

#: What a Media Library accepts out of the box, by content type.
_ALLOWED_TOP = ("image/", "audio/", "video/")
_ALLOWED_EXACT = frozenset({
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "text/plain",
    "text/csv",
    "text/vtt",
})


class MediaDownloadError(CodedError):
    """A file by web address that could not, or should not, be fetched."""

    code = "QUILL-WP-MEDIA-DOWNLOAD"


class MediaImageError(CodedError):
    """A picture this computer could not read or re-encode."""

    code = "QUILL-WP-MEDIA-IMAGE"


# --------------------------------------------------------------------------- #
# Names and types


def content_type_for(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def is_image_name(filename: str) -> bool:
    return content_type_for(filename).startswith("image/")


def allowed_content_type(content_type: str) -> bool:
    kind = content_type.split(";", 1)[0].strip().lower()
    return kind.startswith(_ALLOWED_TOP) or kind in _ALLOWED_EXACT


def safe_filename(name: str, fallback: str = "file") -> str:
    """A file name WordPress keeps as written: letters, digits, dot, dash."""
    stem, dot, ext = name.strip().rpartition(".")
    if not dot:
        stem, ext = name.strip(), ""
    clean = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()[:60] or fallback
    clean_ext = re.sub(r"[^A-Za-z0-9]", "", ext).lower()[:8]
    return f"{clean}.{clean_ext}" if clean_ext else clean


def pasted_picture_name(alt: str, now: datetime) -> str:
    """A pasted picture's file name: from its alt text, else from the time (6.2)."""
    words = " ".join(alt.split()[:6])
    if words.strip():
        return safe_filename(words + ".png")
    return f"pasted-picture-{now:%Y-%m-%d-%H%M%S}.png"


def picture_extension(content: bytes) -> str:
    """The extension a picture's first bytes say it has, or "" when they say nothing."""
    if content.startswith(b"\x89PNG"):
        return "png"
    if content.startswith(b"\xff\xd8"):
        return "jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return ""


def smaller_copy_name(filename: str, width: int, extension: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return safe_filename(f"{stem}-{width}w.{extension}")


# --------------------------------------------------------------------------- #
# Upload from Web Address (6.2)


@dataclass(frozen=True)
class Downloaded:
    filename: str
    content: bytes
    content_type: str
    host: str


def check_download_address(address: str) -> str:
    """The host of an HTTPS address, or a sentence saying why not."""
    parsed = urlparse(address.strip())
    if parsed.scheme.lower() != "https":
        raise MediaDownloadError(
            "QUILL only fetches files over HTTPS. Check that the address starts with https://."
        )
    if not parsed.hostname:
        raise MediaDownloadError("That is not a complete web address. Copy it again and paste it.")
    return parsed.hostname


def download_file(
    opener: Callable[..., Any],
    address: str,
    *,
    timeout: float = 30.0,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
    any_type: bool = False,
) -> Downloaded:
    """Fetch *address* with *opener*: HTTPS only, capped, and a type a library takes."""
    host = check_download_address(address)
    request = Request(address.strip(), headers={"User-Agent": "QUILL"})
    try:
        with opener(request, timeout=timeout) as response:
            final = str(getattr(response, "url", "") or address)
            if urlparse(final).scheme.lower() != "https":
                raise MediaDownloadError(
                    f"{host} sent QUILL to an address that is not HTTPS, so nothing was fetched."
                )
            headers = getattr(response, "headers", {}) or {}
            declared = _header(headers, "Content-Length")
            if declared.isdigit() and int(declared) > max_bytes:
                raise MediaDownloadError(_too_big(host, int(declared), max_bytes))
            content = _read_capped(response, max_bytes)
            content_type = _header(headers, "Content-Type").split(";", 1)[0].strip().lower()
            disposition = _header(headers, "Content-Disposition")
    except MediaDownloadError:
        raise
    except Exception as exc:  # noqa: BLE001 - every network failure becomes one sentence
        raise MediaDownloadError(
            f"QUILL could not fetch the file from {host}: {exc}. Check the address and try again."
        ) from exc
    if len(content) > max_bytes:
        raise MediaDownloadError(_too_big(host, len(content), max_bytes))
    filename = _filename_from(disposition, final, content_type)
    if not content_type or content_type == "application/octet-stream":
        content_type = content_type_for(filename)
    if not any_type and not allowed_content_type(content_type):
        raise MediaDownloadError(
            f"{host} sent a {content_type or 'file of unknown type'}, which a WordPress Media "
            "Library does not take. Use the address of the picture, sound, video or document "
            "itself."
        )
    return Downloaded(filename, content, content_type, host)


def fetch_media_bytes(api: WordPressApi, item: MediaItem) -> bytes:
    """A library file's bytes, through the site's own opener (for Describe, smaller copies)."""
    return download_file(api._opener, item.source_url, timeout=api.timeout, any_type=True).content


def _too_big(host: str, size: int, cap: int) -> str:
    return (
        f"The file on {host} is {human_size(size)}, more than the {human_size(cap)} QUILL "
        "fetches. Download it yourself and use Upload Files."
    )


def _read_capped(response: Any, cap: int) -> bytes:
    try:
        data = response.read(cap + 1)
    except TypeError:  # a reader with no size argument
        data = response.read()
    return bytes(data)


def _header(headers: Any, name: str) -> str:
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    value = getter(name)
    if value is None:
        value = getter(name.lower())
    return str(value or "")


def _filename_from(disposition: str, address: str, content_type: str) -> str:
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disposition, re.IGNORECASE)
    name = unquote(match.group(1)) if match else unquote(urlparse(address).path.rsplit("/", 1)[-1])
    name = safe_filename(name or "download", "download")
    if "." not in name:
        ext = mimetypes.guess_extension(content_type or "") or ""
        name += ext
    return name


# --------------------------------------------------------------------------- #
# Image sizes (6.5)

SIZE_LABELS = {
    "thumbnail": "Thumbnail",
    "medium": "Medium",
    "medium_large": "Medium large",
    "large": "Large",
    "full": "Full size",
}


@dataclass(frozen=True)
class ImageSize:
    name: str
    width: int
    height: int
    source_url: str

    def spoken(self) -> str:
        label = SIZE_LABELS.get(self.name, self.name.replace("_", " ").replace("-", " ").title())
        return f"{label}, {self.width} by {self.height}"


def image_sizes(raw: Mapping[str, Any]) -> list[ImageSize]:
    """Every size WordPress made of a picture, narrowest first, full size last."""
    details = raw.get("media_details")
    details = details if isinstance(details, dict) else {}
    found: dict[str, ImageSize] = {}
    sizes = details.get("sizes")
    for name, size in sizes.items() if isinstance(sizes, dict) else []:
        if not isinstance(size, dict) or not size.get("source_url"):
            continue
        found[str(name)] = ImageSize(
            str(name),
            int(size.get("width", 0) or 0),
            int(size.get("height", 0) or 0),
            str(size["source_url"]),
        )
    if "full" not in found and raw.get("source_url"):
        found["full"] = ImageSize(
            "full",
            int(details.get("width", 0) or 0),
            int(details.get("height", 0) or 0),
            str(raw["source_url"]),
        )
    return sorted(found.values(), key=lambda s: (s.name == "full", s.width))


def load_image_sizes(api: WordPressApi, media_id: int) -> list[ImageSize]:
    return image_sizes(api.get(f"wp/v2/media/{media_id}", context="edit"))


def find_media_by_address(api: WordPressApi, address: str) -> MediaItem | None:
    """The library item a picture's address belongs to, sized variants included."""
    filename = unquote(urlparse(address).path.rsplit("/", 1)[-1])
    stem = _base_stem(filename)
    if not stem:
        return None
    for item in list_media(api, search=stem):
        if item.source_url == address or _base_stem(item.filename) == stem:
            return item
    return None


def _base_stem(filename: str) -> str:
    """``photo-1024x683.jpg`` and ``photo-scaled.jpg`` are both ``photo``."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    stem = re.sub(r"-\d+x\d+$", "", stem)
    return re.sub(r"-(scaled|rotated)$", "", stem).lower()


# --------------------------------------------------------------------------- #
# Make a Smaller Copy (6.5)

SMALLER_FORMATS = (
    ("JPEG", "jpg", "image/jpeg"),
    ("WebP", "webp", "image/webp"),
    ("PNG", "png", "image/png"),
)
SMALLER_WIDTHS = (1600, 1200, 1024, 800, 640)


@dataclass(frozen=True)
class SmallerCopy:
    data: bytes
    width: int
    height: int
    mime: str
    extension: str
    before_width: int
    before_height: int
    before_size: int

    def report(self) -> str:
        return (
            f"Before: {self.before_width} by {self.before_height}, {human_size(self.before_size)}. "
            f"After: {self.width} by {self.height}, {human_size(len(self.data))}."
        )


def make_smaller_copy(data: bytes, max_width: int, format_name: str) -> SmallerCopy:
    """Shrink *data* to at most *max_width* wide, keeping proportions. On this computer."""
    from PIL import Image

    fmt = next((f for f in SMALLER_FORMATS if f[0].lower() == format_name.lower()), None)
    if fmt is None:
        raise MediaImageError(f"QUILL cannot make a {format_name} copy. Choose JPEG, WebP or PNG.")
    label, extension, mime = fmt
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            before = image.size
            copy = image.copy()
    except Exception as exc:  # noqa: BLE001 - Pillow raises many kinds for one meaning
        raise MediaImageError(
            "This file is not a picture QUILL can read, so no smaller copy was made."
        ) from exc
    if copy.width > max_width:
        height = max(1, round(copy.height * max_width / copy.width))
        copy = copy.resize((max_width, height), Image.Resampling.LANCZOS)
    if label == "JPEG" and copy.mode not in ("RGB", "L"):
        copy = copy.convert("RGB")
    out = io.BytesIO()
    options: dict[str, Any] = {"optimize": True}
    if label in ("JPEG", "WebP"):
        options["quality"] = 82
    copy.save(out, format=label.upper(), **options)
    return SmallerCopy(
        out.getvalue(), copy.width, copy.height, mime, extension, before[0], before[1], len(data)
    )


# --------------------------------------------------------------------------- #
# Used In (6.1)


@dataclass(frozen=True)
class UsedIn:
    kind: str  # page or post
    id: int
    title: str

    def spoken(self) -> str:
        return f"{self.title or 'Untitled'} ({self.kind})"


_SCAN_STATUSES = "publish,future,draft,pending,private"


def used_in_all(api: WordPressApi, items: Iterable[MediaItem]) -> dict[int, list[UsedIn]]:
    """Where every item in *items* is used, from one pass over the pages and posts."""
    wanted = list(items)
    found: dict[int, list[UsedIn]] = {m.id: [] for m in wanted}
    for kind, content_id, title, content in _contents(api, ""):
        for item in wanted:
            if mentions(content, item):
                found[item.id].append(UsedIn(kind, content_id, title))
    return found


def used_in_one(api: WordPressApi, item: MediaItem) -> list[UsedIn]:
    """Where one item is used, by searching for its file name (for large libraries)."""
    stem = _base_stem(item.filename)
    return [
        UsedIn(kind, content_id, title)
        for kind, content_id, title, content in _contents(api, stem)
        if mentions(content, item)
    ]


def mentions(content: str, item: MediaItem) -> bool:
    if f'wp-image-{item.id}"' in content or f"wp-image-{item.id} " in content:
        return True
    block = (
        r"<!--\s*wp:(?:image|audio|video|file|cover|media-text)\s+\{[^}]*"
        rf'"(?:id|mediaId)":\s*{item.id}\b'
    )
    if re.search(block, content):
        return True
    if not item.source_url:
        return False
    folder = item.source_url.rsplit("/", 1)[0]
    stem = _base_stem(item.filename)
    pattern = re.escape(folder + "/") + re.escape(stem) + r"(?:-\d+x\d+|-scaled|-rotated)?\."
    return re.search(pattern, content, re.IGNORECASE) is not None


def _contents(api: WordPressApi, search: str) -> Iterable[tuple[str, int, str, str]]:
    for kind, route in (("page", "wp/v2/pages"), ("post", "wp/v2/posts")):
        params: dict[str, object] = {
            "context": "edit",
            "status": _SCAN_STATUSES,
            "_fields": "id,title,content",
        }
        if search:
            params["search"] = search
        for raw in api.iter_collection(route, params):
            yield (
                kind,
                int(raw.get("id", 0)),
                raw_text(raw.get("title")),
                raw_text(raw.get("content")),
            )
