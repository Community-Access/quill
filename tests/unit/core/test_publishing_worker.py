from __future__ import annotations

import json

import quill.core.publishing_clients as publishing_clients
from quill.core.publishing import PublishingConnectionProfile
from quill.core.publishing_providers import AUTH_METHOD_APP_PASSWORD
from quill.core.publishing_worker import browse_publishing_content_task
from quill.stability.task_manager import CancellationToken, CancelledError


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.headers: dict[str, str] = {}

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _noop_progress(_payload: object) -> None:
    return None


def test_browse_publishing_content_task_delegates_on_success(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        return _FakeResponse([
            {
                "id": 11,
                "link": "https://example.com/posts/hello",
                "title": {"rendered": "Hello post"},
                "status": "publish",
                "modified_gmt": "2026-06-08T04:00:00",
                "type": "post",
            }
        ])

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, items = browse_publishing_content_task(
        cancellation_token=CancellationToken(),
        operation_id="op-1",
        progress_callback=_noop_progress,
        profile=profile,
        secret="secret",
        content_kinds=("post",),
    )

    assert ok is True
    assert message == "Loaded publishing content from example.com."
    assert [item.title for item in items] == ["Hello post"]


def test_browse_publishing_content_task_raises_cancelled_error_when_token_cancelled(
    monkeypatch,
) -> None:
    calls: list[str] = []

    def _urlopen(request, **_kwargs):
        calls.append(request.full_url)
        raise AssertionError("No network call should happen once cancellation is requested.")

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    token = CancellationToken()
    token.cancel()

    try:
        browse_publishing_content_task(
            cancellation_token=token,
            operation_id="op-1",
            progress_callback=_noop_progress,
            profile=profile,
            secret="secret",
            content_kinds=("post", "page"),
        )
    except CancelledError:
        pass
    else:
        raise AssertionError("Expected CancelledError to propagate.")

    assert calls == []
