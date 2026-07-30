"""A read-only Hacker News adapter (plan xxx.md 2.3, rank 7).

Hacker News exposes a free, no-auth Firebase API. This adapter reads a listing
(top / new / best), fetches the referenced items, and maps stories onto the
shared :class:`SocialItem` model, so HN reads in the same timeline as every other
network. Two fetches are needed (the id list, then each item); both go through an
injectable fetch (tests map URLs to fixture bytes; the default is HTTPS-only).
"""

from __future__ import annotations

import json

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.adapters.rss import Fetch, default_fetch
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import SocialItem, now_ms

_BASE = "https://hacker-news.firebaseio.com/v0"
_LISTINGS = {"top": "topstories", "new": "newstories", "best": "beststories"}
_NOT_WIRED = "Hacker News is read-only."


def _item_to_social(data: dict, *, account_id: str) -> SocialItem:
    title = data.get("title", "") or ""
    url = data.get("url", "") or ""
    hn_url = f"https://news.ycombinator.com/item?id={data.get('id')}"
    text = f"{title}\n\n{url}" if url else title
    return SocialItem(
        network="hackernews",
        account_id=account_id,
        remote_id=str(data.get("id", "")),
        uri=url or hn_url,
        author_handle=data.get("by", "") or "",
        author_display=data.get("by", "") or "",
        text=text,
        created_at=int(data.get("time", 0) or 0) * 1000 or now_ms(),
        favourite_count=int(data.get("score", 0) or 0),
        reply_count=int(data.get("descendants", 0) or 0),
    )


class HackerNewsAdapter(NetworkAdapter):
    """A Hacker News listing (top/new/best) as a read-only timeline."""

    name = "hackernews"

    def __init__(
        self,
        *,
        account_id: str = "",
        listing: str = "top",
        fetch: Fetch | None = None,
    ) -> None:
        self._account_id = account_id
        self._listing = listing if listing in _LISTINGS else "top"
        self._fetch: Fetch = fetch or default_fetch

    @classmethod
    def available(cls) -> bool:
        return True

    def capabilities(self) -> Capabilities:
        return default_for("hackernews")

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        list_url = f"{_BASE}/{_LISTINGS[self._listing]}.json"
        try:
            ids = json.loads(self._fetch(list_url))
        except (ValueError, TypeError) as exc:
            raise AdapterError(f"HN listing was not JSON: {exc}", kind="validation") from exc
        if not isinstance(ids, list):
            return []
        out: list[SocialItem] = []
        for hid in ids[: max(1, min(limit, 50))]:
            try:
                data = json.loads(self._fetch(f"{_BASE}/item/{hid}.json"))
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict) and data.get("title"):
                out.append(_item_to_social(data, account_id=self._account_id))
        return out

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
