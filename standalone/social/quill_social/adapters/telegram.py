"""A read-focused Telegram adapter (plan xxx.md 2.3, rank 6).

Telegram exposes a full user client via MTProto (Telethon/Pyrogram). This adapter
reads recent messages from a configured channel/chat and maps them onto the
shared :class:`SocialItem` model, so a Telegram channel reads in the same
timeline as every other network.

It follows the two-mode pattern: constructed with no ``client`` it is a
descriptor that raises a clear "not enabled" error at each network method (the
interactive api_id/api_hash + phone login is a later onboarding step); given a
(sync-wrapped) Telethon client it reads live. The message->item mapper is pure
and reads attributes defensively, so it is unit-testable with plain fake message
objects and never imports Telethon. Writing is a later increment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import SocialItem, now_ms

_NOT_WIRED = (
    "Telegram is not connected. Add a Telegram account with its API id/hash and "
    "sign in to read a channel."
)


def _date_to_ms(value: Any) -> int:
    if isinstance(value, datetime):
        try:
            return int(value.timestamp() * 1000)
        except (OverflowError, OSError, ValueError):
            return 0
    return 0


def _sender_names(message: Any) -> tuple[str, str]:
    """(display_name, handle) read defensively from a Telethon message."""
    sender = getattr(message, "sender", None)
    if sender is None:
        return "", ""
    display = (
        getattr(sender, "first_name", "")
        or getattr(sender, "title", "")
        or getattr(sender, "username", "")
        or ""
    )
    handle = getattr(sender, "username", "") or ""
    return display, (f"@{handle}" if handle else "")


def message_to_item(message: Any, *, account_id: str) -> SocialItem:
    """Map a Telethon message onto a :class:`SocialItem` (attribute-defensive)."""
    body = getattr(message, "message", "") or getattr(message, "text", "") or ""
    chat = getattr(message, "chat", None)
    chat_title = getattr(chat, "title", "") if chat is not None else ""
    text = f"[{chat_title}] {body}" if chat_title else body
    display, handle = _sender_names(message)
    return SocialItem(
        network="telegram",
        account_id=account_id,
        remote_id=str(getattr(message, "id", "")),
        uri="",
        author_handle=handle,
        author_display=display,
        text=text,
        created_at=_date_to_ms(getattr(message, "date", None)) or now_ms(),
    )


class TelegramAdapter(NetworkAdapter):
    """Recent messages from a configured Telegram channel/chat as a timeline."""

    name = "telegram"

    def __init__(
        self,
        *,
        account_id: str = "",
        chat: str = "",
        client: Any = None,
    ) -> None:
        self._account_id = account_id
        self._chat = chat  # channel username or id to read
        self._client = client

    @classmethod
    def available(cls) -> bool:
        try:
            import telethon  # noqa: F401
        except ImportError:
            return False
        return True

    def capabilities(self) -> Capabilities:
        return default_for("telegram")

    def _require_client(self) -> Any:
        if self._client is None:
            raise AdapterError(_NOT_WIRED, kind="permission")
        return self._client

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        client = self._require_client()
        if not self._chat:
            raise AdapterError("no Telegram channel configured", kind="validation")
        try:
            messages = client.get_messages(self._chat, limit=limit)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise _telegram_error(exc) from exc
        return [message_to_item(m, account_id=self._account_id) for m in messages or []]

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


def _telegram_error(exc: Exception) -> AdapterError:
    """Normalize a Telethon exception into an :class:`AdapterError`."""
    if isinstance(exc, AdapterError):
        return exc
    name = type(exc).__name__
    msg = str(exc) or "telegram error"
    if "FloodWait" in name:
        seconds = getattr(exc, "seconds", None)
        retry_ms = int(seconds * 1000) if isinstance(seconds, (int, float)) else 60_000
        return AdapterError(msg, kind="transient", retry_after_ms=retry_ms)
    if "Unauthorized" in name or "AuthKey" in name or "SessionPassword" in name:
        return AdapterError(msg, kind="permission")
    if "FloodError" in name or "ServerError" in name or "Timeout" in name:
        return AdapterError(msg, kind="transient")
    return AdapterError(msg, kind="unknown")
