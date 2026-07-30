"""Telegram adapter mapping, two-mode gating, and registry routing."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from quill_social.adapters.base import AdapterError, PublishRequest
from quill_social.adapters.registry import adapter_for
from quill_social.adapters.telegram import (
    TelegramAdapter,
    _telegram_error,
    message_to_item,
)
from quill_social.capabilities import default_for
from quill_social.model import Account


def _msg():
    return SimpleNamespace(
        id=42,
        message="Channel update: new release out.",
        date=datetime(2026, 1, 2, 18, 30, 2, tzinfo=UTC),
        sender=SimpleNamespace(first_name="Ada", username="ada"),
        chat=SimpleNamespace(title="Release Channel"),
    )


class _FakeClient:
    def __init__(self, messages):
        self._messages = messages

    def get_messages(self, entity, limit=40):
        assert entity == "releasechannel"
        return self._messages[:limit]


def test_message_to_item_maps_defensively():
    it = message_to_item(_msg(), account_id="acc")
    assert it.network == "telegram"
    assert it.remote_id == "42"
    assert it.author_display == "Ada"
    assert it.author_handle == "@ada"
    assert "[Release Channel]" in it.text
    assert "new release" in it.text
    assert it.created_at > 0


def test_descriptor_mode_requires_connection():
    adapter = TelegramAdapter(account_id="acc", chat="releasechannel")  # no client
    with pytest.raises(AdapterError) as exc:
        adapter.home_timeline()
    assert exc.value.kind == "permission"


def test_live_mode_reads_messages():
    adapter = TelegramAdapter(
        account_id="acc", chat="releasechannel", client=_FakeClient([_msg()])
    )
    items = adapter.home_timeline()
    assert len(items) == 1
    assert items[0].remote_id == "42"
    # read-only in this version
    with pytest.raises(AdapterError) as exc:
        adapter.publish(PublishRequest(text="hi"))
    assert exc.value.kind == "permission"


def test_missing_channel_is_validation_error():
    adapter = TelegramAdapter(account_id="acc", client=_FakeClient([]))
    with pytest.raises(AdapterError) as exc:
        adapter.home_timeline()
    assert exc.value.kind == "validation"


def test_error_normalizer():
    flood = type("FloodWaitError", (Exception,), {})()
    flood.seconds = 30
    err = _telegram_error(flood)
    assert err.kind == "transient"
    assert err.retry_after_ms == 30_000
    auth = type("UnauthorizedError", (Exception,), {})()
    assert _telegram_error(auth).kind == "permission"


def test_registry_routes_telegram_descriptor():
    adapter = adapter_for(Account(network="telegram", instance="releasechannel"))
    assert isinstance(adapter, TelegramAdapter)
    assert adapter._chat == "releasechannel"


def test_capability_profile():
    caps = default_for("telegram")
    assert caps.char_limit == 4096
    assert caps.supports_bookmarks is True
    assert caps.max_media_attachments == 0
