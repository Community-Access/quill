"""OPDS catalogue browse bridge for the social app (plan xxx.md 4.0, 4.2).

The decided Books architecture is "both": a full Library feature in the main app
*and* an OPDS-catalogue browse bridge here, so a reader can discover books
(Standard Ebooks, Feedbooks, any OPDS catalogue) right alongside their feeds.
OPDS is Atom-based, so this is a thin read-only adapter mirroring the RSS one:
each catalogue entry becomes a :class:`SocialItem` whose ``uri`` is the book's
acquisition link. Reading/opening a chosen book is the main app's Library
feature; here it is browse-and-discover.
"""

from __future__ import annotations

from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.adapters.rss import Fetch, default_fetch, strip_html
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import SocialItem, now_ms

_NOT_WIRED = "OPDS catalogues are read-only (browse only)."
_ACQUISITION = "acquisition"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _reject_dtd(raw: bytes) -> None:
    head = raw[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise AdapterError("OPDS declares a DTD/entity; refused", kind="validation")


def _entry_to_item(entry: ET.Element, *, account_id: str, base_url: str) -> SocialItem:
    title = ""
    summary = ""
    author = ""
    entry_id = ""
    acquire = ""
    site = ""
    for child in entry:
        name = _local(child.tag)
        if name == "title":
            title = (child.text or "").strip()
        elif name == "id":
            entry_id = (child.text or "").strip()
        elif name in ("summary", "content") and not summary:
            summary = child.text or ""
        elif name == "author":
            for sub in child:
                if _local(sub.tag) == "name":
                    author = (sub.text or "").strip()
        elif name == "link":
            rel = child.attrib.get("rel", "")
            href = child.attrib.get("href", "")
            if not href:
                continue
            full = urljoin(base_url, href)
            if _ACQUISITION in rel and not acquire:
                acquire = full
            elif rel == "alternate" and not site:
                site = full
    text = f"{title}\n\n{strip_html(summary)}" if summary else title
    return SocialItem(
        network="opds",
        account_id=account_id,
        remote_id=entry_id or acquire or title,
        uri=acquire or site,
        author_handle=author,
        author_display=author,
        text=text,
        created_at=now_ms(),
    )


def parse_catalog(raw: bytes, *, account_id: str, base_url: str = "") -> list[SocialItem]:
    """Parse an OPDS catalogue feed into browsable book items."""
    if not raw:
        return []
    _reject_dtd(raw)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise AdapterError(f"OPDS is not well-formed XML: {exc}", kind="validation") from exc
    out: list[SocialItem] = []
    for entry in root:
        if _local(entry.tag) != "entry":
            continue
        item = _entry_to_item(entry, account_id=account_id, base_url=base_url)
        if item.text:
            out.append(item)
    return out


class OpdsAdapter(NetworkAdapter):
    """A book catalogue (OPDS) surfaced as a read-only browse timeline."""

    name = "opds"

    def __init__(
        self,
        *,
        catalog_url: str,
        account_id: str = "",
        fetch: Fetch | None = None,
    ) -> None:
        self.catalog_url = catalog_url
        self._account_id = account_id
        self._fetch: Fetch = fetch or default_fetch

    @classmethod
    def available(cls) -> bool:
        return True

    def capabilities(self) -> Capabilities:
        return default_for("opds")

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        if not self.catalog_url:
            raise AdapterError("no OPDS catalogue configured", kind="validation")
        raw = self._fetch(self.catalog_url)
        items = parse_catalog(raw, account_id=self._account_id, base_url=self.catalog_url)
        return items[:limit]

    def notifications(self, *, limit: int = 40) -> list[SocialItem]:
        return []

    def thread(self, item: SocialItem) -> list[SocialItem]:
        return [item]

    def publish(self, request: PublishRequest) -> PublishResult:
        raise AdapterError(_NOT_WIRED, kind="permission")

    def set_favourite(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError(_NOT_WIRED, kind="permission")

    def set_reblog(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError(_NOT_WIRED, kind="permission")

    def delete(self, remote_id: str) -> None:
        raise AdapterError(_NOT_WIRED, kind="permission")
