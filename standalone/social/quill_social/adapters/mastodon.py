"""Mastodon adapter (PRD 22).

Two modes share one class. Without a live client (the default,
``MastodonAdapter()``) the adapter still ships the capability descriptor and a
clear boundary: every network method raises an :class:`AdapterError` whose
message contains "not enabled", so the UI can explain the state instead of
failing opaquely. With a client injected -- either a real ``mastodon.Mastodon``
built by the registry from a stored access token (PRD 31.1), or a fake in
tests -- the same methods call the client and MAP its responses into the
domain model.

The response->model mapping lives in pure module-level functions
(:func:`_status_to_item`, :func:`_media_to_model`, :func:`_poll_to_model`) so it
can be unit-tested with fixture dicts WITHOUT importing Mastodon.py. Mastodon.py
returns ``AttribAccessDict`` values that behave like plain dicts, so the mapping
consumes the API response directly.

API assumptions (Mastodon.py, stable documented API; Context7 MCP was not
reachable in this environment so these were confirmed against the published
mastodonpy docs): the client exposes ``timeline_home(limit=, since_id=)``,
``notifications(limit=)``, ``status_context(id)``, ``status(id)``,
``status_post(status, visibility=, spoiler_text=, language=, in_reply_to_id=)``
and the ``status_(un)favourite/bookmark/reblog(id)`` toggles. A status dict
carries ``id, uri, url, content (HTML), created_at (datetime), account,
visibility, spoiler_text, sensitive, language, in_reply_to_id, replies_count,
reblogs_count, favourites_count, favourited, bookmarked, reblogged,
media_attachments, poll, reblog``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape
from typing import Any

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import Media, Poll, PollOption, SocialItem

_NOT_WIRED = (
    "The live Mastodon adapter is not enabled in this build. Install the "
    "'networks' extra and add an account to connect."
)


# -- pure mapping helpers -----------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def _to_ms(value: Any) -> int:
    """Normalize a Mastodon timestamp (datetime | ISO string | epoch) to ms."""
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


def _html_to_text(html: str) -> str:
    """Flatten Mastodon's HTML ``content`` into readable plain text."""
    if not html:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = _TAG_RE.sub("", text)
    return unescape(text).strip()


def _acct_handle(account: dict) -> str:
    acct = (account or {}).get("acct", "") or ""
    if not acct:
        return ""
    return acct if acct.startswith("@") else f"@{acct}"


def _media_to_model(attachments: list | None) -> list[Media]:
    """Map ``media_attachments`` into :class:`Media`."""
    out: list[Media] = []
    for att in attachments or []:
        if not isinstance(att, dict):
            continue
        out.append(
            Media(
                kind=att.get("type", "unknown") or "unknown",
                uri=att.get("url") or att.get("remote_url") or "",
                mime=att.get("mime_type", "") or "",
                alt_text=att.get("description", "") or "",
            )
        )
    return out


def _poll_to_model(poll: dict | None) -> Poll | None:
    """Map a Mastodon ``poll`` dict into :class:`Poll`."""
    if not poll or not isinstance(poll, dict):
        return None
    options = [
        PollOption(o.get("title", "") or "", int(o.get("votes_count", 0) or 0))
        for o in poll.get("options", []) or []
        if isinstance(o, dict)
    ]
    return Poll(
        options=options,
        multiple=bool(poll.get("multiple", False)),
        expires_at=_to_ms(poll.get("expires_at")) or None,
        voted=bool(poll.get("voted", False)),
        own_votes=list(poll.get("own_votes", []) or []),
        total_votes=int(poll.get("votes_count", 0) or 0),
    )


def _status_to_item(status: dict, *, account_id: str = "") -> SocialItem:
    """Map one Mastodon status dict into a :class:`SocialItem`.

    A boost (``reblog`` present) is represented as one row whose content is the
    boosted status', with ``reblog_by``/``reblog_of`` recording the booster,
    mirroring ``adapters/mock.py``.
    """
    boost = status.get("reblog") if isinstance(status, dict) else None
    inner = boost if isinstance(boost, dict) else status
    account = inner.get("account", {}) or {}
    item = SocialItem(
        network="mastodon",
        account_id=account_id,
        remote_id=str(inner.get("id", "") or ""),
        uri=inner.get("url") or inner.get("uri", "") or "",
        author_handle=_acct_handle(account),
        author_display=account.get("display_name", "") or "",
        author_id=str(account.get("id", "") or ""),
        text=_html_to_text(inner.get("content", "") or ""),
        lang=inner.get("language", "") or "",
        created_at=_to_ms(inner.get("created_at")),
        visibility=inner.get("visibility", "public") or "public",
        content_warning=inner.get("spoiler_text", "") or "",
        sensitive=bool(inner.get("sensitive", False)),
        in_reply_to=str(inner.get("in_reply_to_id") or "") or "",
        reply_count=int(inner.get("replies_count", 0) or 0),
        reblog_count=int(inner.get("reblogs_count", 0) or 0),
        favourite_count=int(inner.get("favourites_count", 0) or 0),
        favourited=bool(inner.get("favourited", False)),
        bookmarked=bool(inner.get("bookmarked", False)),
        reblogged=bool(inner.get("reblogged", False)),
        media=_media_to_model(inner.get("media_attachments")),
        poll=_poll_to_model(inner.get("poll")),
    )
    if isinstance(boost, dict):
        item.reblog_of = str(inner.get("id", "") or "")
        item.reblog_by = _acct_handle(status.get("account", {}) or {})
    return item


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "http_status", "status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    for arg in getattr(exc, "args", ()) or ():
        if isinstance(arg, int):
            return arg
    return None


def _retry_ms(exc: Exception) -> int:
    val = getattr(exc, "retry_after_ms", None)
    if isinstance(val, int):
        return val
    secs = getattr(exc, "retry_after", None)
    if isinstance(secs, (int, float)):
        return int(secs * 1000)
    return 60_000


def _mastodon_error(exc: Exception) -> AdapterError:
    """Normalize a Mastodon.py exception into an :class:`AdapterError`."""
    if isinstance(exc, AdapterError):
        return exc
    name = type(exc).__name__
    status = _status_code(exc)
    msg = str(exc) or "mastodon error"
    if "Ratelimit" in name or status == 429:
        return AdapterError(msg, kind="transient", retry_after_ms=_retry_ms(exc))
    if "Unauthorized" in name or status in (401, 403):
        return AdapterError(msg, kind="permission")
    if "NotFound" in name or "BadRequest" in name or status in (400, 404, 422):
        return AdapterError(msg, kind="validation")
    return AdapterError(msg, kind="unknown")


# -- adapter ------------------------------------------------------------------


class MastodonAdapter(NetworkAdapter):
    name = "mastodon"

    def __init__(
        self,
        instance: str = "",
        access_token: str = "",
        *,
        account_id: str = "",
        client: Any = None,
    ) -> None:
        self.instance = instance
        self._token = access_token  # never logged; resolved from the OS keystore
        self._account_id = account_id
        self._client = client  # a live mastodon.Mastodon or an injected fake
        self._caps = default_for("mastodon")

    def capabilities(self) -> Capabilities:
        return self._caps

    def refine_from_instance(self, instance_meta: dict) -> Capabilities:
        """Sharpen capabilities from a live ``/api/v1/instance`` response.

        Mastodon exposes ``configuration.statuses.max_characters``,
        ``max_media_attachments``, poll limits, and (on newer servers) whether
        quote posts are supported. We only overwrite fields the server actually
        reports, leaving conservative defaults elsewhere (PRD 11.4).
        """
        cfg = (instance_meta or {}).get("configuration", {})
        statuses = cfg.get("statuses", {})
        polls = cfg.get("polls", {})
        media = cfg.get("media_attachments", {})
        overrides: dict = {}
        if "max_characters" in statuses:
            overrides["char_limit"] = int(statuses["max_characters"])
        if "max_media_attachments" in statuses:
            overrides["max_media_attachments"] = int(statuses["max_media_attachments"])
        if "max_options" in polls:
            overrides["max_poll_options"] = int(polls["max_options"])
        if "description_limit" in media:
            overrides["max_alt_text"] = int(media["description_limit"])
        if "version" in instance_meta:
            overrides["server_version"] = str(instance_meta["version"])
        self._caps = self._caps.merge(**overrides)
        return self._caps

    # -- live methods (require an injected/built client) ----------------------

    def _require_client(self) -> Any:
        if self._client is None:
            raise AdapterError(_NOT_WIRED, kind="permission")
        return self._client

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        client = self._require_client()
        kwargs: dict[str, Any] = {"limit": limit}
        if since_id:
            kwargs["since_id"] = since_id
        try:
            statuses = client.timeline_home(**kwargs)
        except Exception as exc:  # noqa: BLE001 -- normalized below
            raise _mastodon_error(exc) from exc
        return [_status_to_item(s, account_id=self._account_id) for s in statuses or []]

    def notifications(self, *, limit: int = 40) -> list[SocialItem]:
        client = self._require_client()
        try:
            notes = client.notifications(limit=limit)
        except Exception as exc:  # noqa: BLE001
            raise _mastodon_error(exc) from exc
        out: list[SocialItem] = []
        for note in notes or []:
            status = note.get("status") if isinstance(note, dict) else None
            if isinstance(status, dict):
                out.append(_status_to_item(status, account_id=self._account_id))
        return out

    def thread(self, item: SocialItem) -> list[SocialItem]:
        client = self._require_client()
        target = item.remote_id
        try:
            context = client.status_context(target)
            focus = client.status(target)
        except Exception as exc:  # noqa: BLE001
            raise _mastodon_error(exc) from exc
        context = context or {}
        rows = list(context.get("ancestors", []) or [])
        if isinstance(focus, dict):
            rows.append(focus)
        rows.extend(context.get("descendants", []) or [])
        items = [_status_to_item(s, account_id=self._account_id) for s in rows]
        items.sort(key=lambda it: it.created_at)
        return items

    def publish(self, request: PublishRequest) -> PublishResult:
        client = self._require_client()
        try:
            status = client.status_post(
                request.text,
                visibility=request.visibility or None,
                spoiler_text=request.content_warning or None,
                language=request.lang or None,
                in_reply_to_id=request.in_reply_to or None,
            )
        except Exception as exc:  # noqa: BLE001
            raise _mastodon_error(exc) from exc
        item = _status_to_item(status, account_id=self._account_id)
        return PublishResult(remote_id=item.remote_id, uri=item.uri, item=item)

    def _toggle(self, on_method: str, off_method: str, remote_id: str, on: bool) -> None:
        client = self._require_client()
        try:
            getattr(client, on_method if on else off_method)(remote_id)
        except Exception as exc:  # noqa: BLE001
            raise _mastodon_error(exc) from exc

    def set_favourite(self, remote_id: str, on: bool = True) -> None:
        self._toggle("status_favourite", "status_unfavourite", remote_id, on)

    def set_bookmark(self, remote_id: str, on: bool = True) -> None:
        self._toggle("status_bookmark", "status_unbookmark", remote_id, on)

    def set_reblog(self, remote_id: str, on: bool = True) -> None:
        self._toggle("status_reblog", "status_unreblog", remote_id, on)

    @classmethod
    def available(cls) -> bool:
        try:
            import mastodon  # noqa: F401
        except ImportError:
            return False
        return True
