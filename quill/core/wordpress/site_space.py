"""How much space a site uses, and a copy of its design (wordpress.md 9.16).

* ``wp-site-health/v1/directory-sizes``: the size of uploads, themes, plugins,
  WordPress itself and the database, said in words ("Uploads: 1.2 GB").
* ``wp-block-editor/v1/export``: a zip of a block theme with the person's
  changes, saved to their computer before they try a style variation.

The export answers with a zip rather than JSON, so :func:`fetch_bytes` signs
and sends it exactly as :meth:`WordPressApi.request` does -- through the same
opener, so through ``send_to_site`` -- and only skips the JSON decode.

Wx-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from quill.core.wordpress import api as wpapi
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import human_size

DIRECTORY_SIZES = "wp-site-health/v1/directory-sizes"
EXPORT = "wp-block-editor/v1/export"

#: (key in the answer, what it is called), in the order they are said.
_PARTS = (
    ("uploads_size", "Uploads"),
    ("themes_size", "Themes"),
    ("plugins_size", "Plugins"),
    ("wordpress_size", "WordPress itself"),
    ("database_size", "Database"),
)


@dataclass(frozen=True)
class SpaceUse:
    #: (what, bytes or -1 when the site could not measure it, its own words).
    parts: tuple[tuple[str, int, str], ...]
    total: int

    def lines(self) -> list[str]:
        out: list[str] = []
        for name, size, words in self.parts:
            if size >= 0:
                out.append(f"{name}: {size_words(size)}.")
            else:
                out.append(f"{name}: the site could not measure it{_why(words)}.")
        if self.total >= 0:
            out.append(f"Altogether: {size_words(self.total)}.")
        return out


def _why(words: str) -> str:
    return f" ({words.rstrip('.')})" if words else ""


def size_words(size: int) -> str:
    """Bytes in words, up to gigabytes: ``1288490188`` -> ``1.2 GB``."""
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} GB"
    return human_size(size)


def read_space(api: WordPressApi) -> SpaceUse:
    raw = api.get(DIRECTORY_SIZES)
    raw = raw if isinstance(raw, dict) else {}
    parts = tuple((name, _bytes(raw.get(key)), _words(raw.get(key))) for key, name in _PARTS)
    total = _bytes(raw.get("total_size"))
    if total < 0:
        known = [size for _n, size, _w in parts if size >= 0]
        total = sum(known) if known else -1
    return SpaceUse(parts, total)


def _bytes(entry: Any) -> int:
    if not isinstance(entry, dict):
        return -1
    raw = entry.get("raw")
    if isinstance(raw, (int, float)) and raw >= 0:
        return int(raw)
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return -1


def _words(entry: Any) -> str:
    if not isinstance(entry, dict):
        return ""
    return re.sub(r"<[^>]+>", "", str(entry.get("size") or "")).strip()


# --------------------------------------------------------------------------- #
# The design, as a zip


def fetch_bytes(api: WordPressApi, route: str) -> tuple[bytes, dict[str, str]]:
    """GET *route* signed, and hand back the raw body and headers (a file, not JSON)."""
    url = wpapi.route_url(api.address, route)
    headers = {"Accept": "application/zip, application/json"}
    signature = api.auth.header()
    if signature:
        headers["Authorization"] = signature
    request = Request(url, headers=headers, method="GET")
    try:
        with api._opener(request, timeout=max(api.timeout, 60.0), context=wpapi._context(url)) as r:
            body = r.read()
            got = wpapi._headers(r)
    except HTTPError as exc:
        raise wpapi._error_from_http(exc, method="GET", site_name=api.site_name) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WordPressApiError(wpapi._network_sentence(exc, api.site_name)) from exc
    return body, got


def export_design(api: WordPressApi) -> tuple[bytes, str]:
    """The zip and its file name (the theme's, as the site names it)."""
    body, headers = fetch_bytes(api, EXPORT)
    if not body.startswith(b"PK"):
        raise WordPressApiError(
            f"{api.site_name} did not send a zip of its design. Only a block theme can be "
            "exported this way."
        )
    name = ""
    for key, value in headers.items():
        if key.lower() == "content-disposition":
            match = re.search(r'filename="?([^";]+)"?', value)
            name = match.group(1).strip() if match else ""
    name = re.sub(r"[^\w.\- ]", "", name) or "site-design.zip"
    return body, name if name.lower().endswith(".zip") else name + ".zip"
