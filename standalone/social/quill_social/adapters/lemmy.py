"""A read-focused Lemmy adapter (plan xxx.md 2.3, fediverse siblings).

Lemmy is a federated link aggregator with its own open HTTP/JSON API
(``/api/v3``). This adapter reads a public post list and maps it onto the shared
:class:`SocialItem` model, so a Lemmy community reads in the same timeline as
every other network. It follows the same two-mode / injected-fetch pattern as the
RSS adapter (tests pass fixture JSON; the default fetch is HTTPS-only). Writing
(posting, commenting, voting) is a later increment -- for now those raise a
``permission`` error and the capability profile hides them.
"""

from __future__ import annotations

import json

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.adapters.rss import Fetch, default_fetch, parse_date_ms
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import SocialItem, now_ms

_NOT_WIRED = "Lemmy is read-only in this version."


def _post_to_item(node: dict, *, account_id: str) -> SocialItem:
    post = node.get("post", {}) or {}
    creator = node.get("creator", {}) or {}
    community = node.get("community", {}) or {}
    counts = node.get("counts", {}) or {}
    title = post.get("name", "") or ""
    body = post.get("body", "") or post.get("url", "") or ""
    text = f"{title}\n\n{body}" if body else title
    community_name = community.get("name", "")
    if community_name:
        text = f"[{community_name}] {text}"
    return SocialItem(
        network="lemmy",
        account_id=account_id,
        remote_id=str(post.get("ap_id") or post.get("id", "")),
        uri=post.get("ap_id") or post.get("url", "") or "",
        author_handle=creator.get("actor_id") or creator.get("name", "") or "",
        author_display=creator.get("display_name") or creator.get("name", "") or "",
        author_id=creator.get("actor_id") or "",
        text=text,
        created_at=parse_date_ms(post.get("published", "")) or now_ms(),
        reply_count=int(counts.get("comments", 0) or 0),
        favourite_count=int(counts.get("score", 0) or 0),
    )


def parse_posts(raw: bytes, *, account_id: str) -> list[SocialItem]:
    """Parse a Lemmy ``/api/v3/post/list`` response into social items."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise AdapterError(f"Lemmy response was not JSON: {exc}", kind="validation") from exc
    posts = data.get("posts") if isinstance(data, dict) else None
    if not isinstance(posts, list):
        return []
    return [_post_to_item(p, account_id=account_id) for p in posts if isinstance(p, dict)]


def _normalize_instance(instance: str) -> str:
    return instance.replace("https://", "").replace("http://", "").strip("/")


class LemmyAdapter(NetworkAdapter):
    """A Lemmy instance's local post feed, surfaced as a home timeline."""

    name = "lemmy"

    def __init__(
        self,
        *,
        instance: str,
        account_id: str = "",
        fetch: Fetch | None = None,
    ) -> None:
        self.instance = _normalize_instance(instance)
        self._account_id = account_id
        self._fetch: Fetch = fetch or default_fetch

    @classmethod
    def available(cls) -> bool:
        return True

    def capabilities(self) -> Capabilities:
        return default_for("lemmy")

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        if not self.instance:
            raise AdapterError("no Lemmy instance configured", kind="validation")
        url = (
            f"https://{self.instance}/api/v3/post/list"
            f"?type_=Local&sort=New&limit={max(1, min(limit, 50))}"
        )
        items = parse_posts(self._fetch(url), account_id=self._account_id)
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
