"""Bluesky adapter (PRD 23).

Same two-mode shape as the Mastodon adapter. Without a live client
(``BlueskyAdapter()``) it ships the capability descriptor and raises a clear
"not enabled" :class:`AdapterError` at every network method. With a client
injected -- a real ``atproto.Client`` built and logged in by the registry, or a
fake in tests -- the methods call the client and MAP its responses into the
domain model.

Bluesky's model differs sharply from Mastodon: durable DID identity, no native
polls, quote posts and thread gates as first-class features, custom feeds, a
300-grapheme limit. The capability defaults encode those differences so the UI
adapts without pretending the two networks are the same (PRD 6.2). Identity is
keyed on the account DID, not the mutable handle (PRD 11.3).

The response->model mapping lives in pure module-level functions
(:func:`_feedview_to_item`, :func:`_post_to_item`) that consume plain dicts, so
they can be unit-tested with fixture dicts WITHOUT importing atproto. The live
methods convert the SDK's typed models to dicts via ``model_dump()`` before
mapping.

API assumptions (atproto Python SDK, stable documented API; Context7 MCP was not
reachable so these were confirmed against the published atproto.blue docs):
``Client().login(handle, app_password)``; ``get_timeline(limit=)`` returns a
response with ``.feed`` of ``FeedViewPost`` (each ``.post`` a ``PostView`` with
``uri, cid, author{did,handle,display_name}, record{text,created_at,langs,reply},
reply_count, repost_count, like_count, indexed_at, viewer{like,repost},
embed, labels``); ``send_post(text=)`` returns ``.uri``/``.cid``;
``get_post_thread(uri)`` returns ``.thread`` (a ThreadViewPost tree);
``like(uri, cid)``/``repost(uri, cid)`` and ``unlike``/``unrepost`` toggle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import Media, SocialItem

_NOT_WIRED = (
    "The live Bluesky adapter is not enabled in this build. Install the "
    "'networks' extra and add an account to connect."
)


# -- pure mapping helpers -----------------------------------------------------


def _to_ms(value: Any) -> int:
    """Normalize an AT Protocol timestamp (ISO string | datetime | epoch) to ms."""
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return 0
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return 0
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    return 0


def _as_dict(obj: Any) -> dict:
    """Coerce an atproto typed model (or dict) to a plain dict for mapping."""
    if isinstance(obj, dict):
        return obj
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        result = dump()
        if isinstance(result, dict):
            return result
    return {}


def _handle(author: dict) -> str:
    h = (author or {}).get("handle", "") or ""
    if not h:
        return ""
    return h if h.startswith("@") else f"@{h}"


def _embed_media(embed: dict | None) -> list[Media]:
    """Map an ``app.bsky.embed.images#view`` embed into :class:`Media`."""
    if not embed or not isinstance(embed, dict):
        return []
    images = embed.get("images")
    out: list[Media] = []
    if isinstance(images, list):
        for img in images:
            if not isinstance(img, dict):
                continue
            out.append(
                Media(
                    kind="image",
                    uri=img.get("fullsize") or img.get("thumb") or "",
                    alt_text=img.get("alt", "") or "",
                )
            )
    return out


def _post_to_item(post: dict, *, account_id: str = "", reason: dict | None = None) -> SocialItem:
    """Map one Bluesky ``PostView`` dict into a :class:`SocialItem`."""
    post = post or {}
    author = post.get("author", {}) or {}
    record = post.get("record", {}) or {}
    viewer = post.get("viewer", {}) or {}
    langs = record.get("langs") or []
    uri = post.get("uri", "") or ""
    item = SocialItem(
        network="bluesky",
        account_id=account_id,
        remote_id=uri,
        uri=uri,
        author_handle=_handle(author),
        author_display=author.get("display_name", "") or "",
        author_id=author.get("did", "") or "",
        text=record.get("text", "") or "",
        lang=(langs[0] if langs else "") or "",
        created_at=_to_ms(record.get("created_at") or post.get("indexed_at")),
        reply_count=int(post.get("reply_count", 0) or 0),
        reblog_count=int(post.get("repost_count", 0) or 0),
        favourite_count=int(post.get("like_count", 0) or 0),
        favourited=bool(viewer.get("like")),
        reblogged=bool(viewer.get("repost")),
        media=_embed_media(post.get("embed")),
    )
    reply = record.get("reply") or {}
    if isinstance(reply, dict) and reply:
        item.in_reply_to = (reply.get("parent") or {}).get("uri", "") or ""
        item.thread_root = (reply.get("root") or {}).get("uri", "") or ""
    labels = post.get("labels") or []
    if labels:
        item.sensitive = True
        item.moderation_labels = [
            lbl.get("val", "") for lbl in labels if isinstance(lbl, dict) and lbl.get("val")
        ]
    if reason and isinstance(reason, dict):
        by = reason.get("by") or {}
        if by:
            item.reblog_by = _handle(by)
            item.reblog_of = uri
    return item


def _feedview_to_item(feed_view: dict, *, account_id: str = "") -> SocialItem:
    """Map one ``FeedViewPost`` dict (``{post, reason}``) into a :class:`SocialItem`."""
    feed_view = feed_view or {}
    post = feed_view.get("post") if isinstance(feed_view.get("post"), dict) else feed_view
    return _post_to_item(post, account_id=account_id, reason=feed_view.get("reason"))


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "status", "http_status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    for arg in getattr(exc, "args", ()) or ():
        if isinstance(arg, int):
            return arg
    return None


def _bluesky_error(exc: Exception) -> AdapterError:
    """Normalize an atproto exception into an :class:`AdapterError`."""
    if isinstance(exc, AdapterError):
        return exc
    name = type(exc).__name__
    status = _status_code(exc)
    msg = str(exc) or "bluesky error"
    if "RateLimit" in name or "Ratelimit" in name or status == 429:
        return AdapterError(msg, kind="transient", retry_after_ms=60_000)
    if "Auth" in name or "Unauthorized" in name or status in (401, 403):
        return AdapterError(msg, kind="permission")
    if "NotFound" in name or "BadRequest" in name or status in (400, 404, 422):
        return AdapterError(msg, kind="validation")
    return AdapterError(msg, kind="unknown")


# -- adapter ------------------------------------------------------------------


class BlueskyAdapter(NetworkAdapter):
    name = "bluesky"

    def __init__(
        self,
        did: str = "",
        service: str = "https://bsky.social",
        *,
        account_id: str = "",
        client: Any = None,
    ) -> None:
        self.did = did  # durable identity; handles are mutable (PRD 11.3)
        self.service = service
        self._account_id = account_id or did
        self._client = client  # a live atproto.Client or an injected fake
        self._caps = default_for("bluesky")

    def capabilities(self) -> Capabilities:
        return self._caps

    def refine_from_server(self, describe: dict) -> Capabilities:
        """Sharpen capabilities from a live ``describeServer`` / limits probe.

        Most Bluesky limits are protocol constants (300 graphemes, 4 images),
        already the defaults; a PDS can still report availability of video and
        DM features, which we honor when present.
        """
        overrides: dict = {}
        if "video" in describe:
            overrides["supports_video"] = bool(describe["video"])
        if "chat" in describe:
            overrides["supports_direct_messages"] = bool(describe["chat"])
        if "version" in describe:
            overrides["server_version"] = str(describe["version"])
        self._caps = self._caps.merge(**overrides)
        return self._caps

    # -- live methods (require an injected/built client) ----------------------

    def _require_client(self) -> Any:
        if self._client is None:
            raise AdapterError(_NOT_WIRED, kind="permission")
        return self._client

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        client = self._require_client()
        try:
            resp = client.get_timeline(limit=limit)
        except Exception as exc:  # noqa: BLE001 -- normalized below
            raise _bluesky_error(exc) from exc
        feed = _attr(resp, "feed", []) or []
        return [
            _feedview_to_item(_as_dict(fv), account_id=self._account_id) for fv in feed
        ]

    def notifications(self, *, limit: int = 40) -> list[SocialItem]:
        client = self._require_client()
        getter = getattr(client, "get_notifications", None)
        try:
            resp = getter() if getter is not None else client.get_timeline(limit=limit)
        except Exception as exc:  # noqa: BLE001
            raise _bluesky_error(exc) from exc
        notes = _attr(resp, "notifications", None)
        if notes is not None:
            return [_post_to_item(_as_dict(n), account_id=self._account_id) for n in notes]
        feed = _attr(resp, "feed", []) or []
        return [_feedview_to_item(_as_dict(fv), account_id=self._account_id) for fv in feed]

    def thread(self, item: SocialItem) -> list[SocialItem]:
        client = self._require_client()
        target = item.remote_id or item.uri
        try:
            resp = client.get_post_thread(target)
        except Exception as exc:  # noqa: BLE001
            raise _bluesky_error(exc) from exc
        node = _as_dict(_attr(resp, "thread", resp))
        collected: dict[str, SocialItem] = {}
        _collect_thread(node, collected, self._account_id)
        items = list(collected.values())
        items.sort(key=lambda it: it.created_at)
        return items

    def publish(self, request: PublishRequest) -> PublishResult:
        client = self._require_client()
        try:
            resp = client.send_post(text=request.text)
        except Exception as exc:  # noqa: BLE001
            raise _bluesky_error(exc) from exc
        uri = _attr(resp, "uri", "") or ""
        item = SocialItem(
            network="bluesky",
            account_id=self._account_id,
            remote_id=uri,
            uri=uri,
            author_id=self.did,
            text=request.text,
            visibility="public",
        )
        return PublishResult(remote_id=uri, uri=uri, item=item)

    def _cid_for(self, uri: str) -> str:
        getter = getattr(self._client, "get_posts", None)
        if getter is None:
            return ""
        try:
            resp = getter([uri])
        except Exception:  # noqa: BLE001 -- best-effort cid lookup
            return ""
        for post in _attr(resp, "posts", []) or []:
            pd = _as_dict(post)
            if pd.get("uri") == uri:
                return pd.get("cid", "") or ""
        return ""

    def _interact(self, on_method: str, off_method: str, remote_id: str, on: bool) -> None:
        client = self._require_client()
        try:
            if on:
                getattr(client, on_method)(remote_id, self._cid_for(remote_id))
            else:
                getattr(client, off_method)(remote_id)
        except AdapterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _bluesky_error(exc) from exc

    def set_favourite(self, remote_id: str, on: bool = True) -> None:
        self._interact("like", "unlike", remote_id, on)

    def set_reblog(self, remote_id: str, on: bool = True) -> None:
        self._interact("repost", "unrepost", remote_id, on)

    @classmethod
    def available(cls) -> bool:
        try:
            import atproto  # noqa: F401
        except ImportError:
            return False
        return True


def _collect_thread(node: dict, out: dict, account_id: str) -> None:
    """Flatten a ThreadViewPost tree (parents + replies) into ``out`` by uri."""
    if not isinstance(node, dict):
        return
    post = node.get("post")
    if isinstance(post, dict):
        item = _post_to_item(post, account_id=account_id)
        if item.remote_id:
            out.setdefault(item.remote_id, item)
    parent = node.get("parent")
    if isinstance(parent, dict):
        _collect_thread(parent, out, account_id)
    for reply in node.get("replies") or []:
        if isinstance(reply, dict):
            _collect_thread(reply, out, account_id)
