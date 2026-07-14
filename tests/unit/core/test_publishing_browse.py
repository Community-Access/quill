from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import quill.core.publishing as publishing
import quill.core.publishing_clients as publishing_clients
from quill.core.publishing import PublishingConnectionProfile
from quill.core.publishing_clients import PublishingRemoteDocument, publishing_provider_client
from quill.core.publishing_providers import AUTH_METHOD_APP_PASSWORD, PublishingOperationCancelled


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


def test_browse_publishing_content_returns_posts_and_pages(
    monkeypatch,
) -> None:
    calls: list[str] = []

    def _urlopen(request, **_kwargs):
        calls.append(request.full_url)
        if "/posts?" in request.full_url:
            return _FakeResponse([
                {
                    "id": 11,
                    "link": "https://example.com/posts/hello",
                    "title": {"rendered": "Hello post"},
                    "status": "draft",
                    "modified_gmt": "2026-06-08T04:00:00",
                    "type": "post",
                }
            ])
        return _FakeResponse([
            {
                "id": 22,
                "link": "https://example.com/about",
                "title": {"rendered": "About page"},
                "status": "publish",
                "modified_gmt": "2026-06-08T05:00:00",
                "type": "page",
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

    ok, message, items = publishing.browse_publishing_content(profile, "secret")

    assert ok is True
    assert message == "Loaded publishing content from example.com."
    assert [item.content_kind for item in items] == ["page", "post"]
    assert items[0].title == "About page"
    assert items[1].remote_url == "https://example.com/posts/hello"
    assert any("/posts?" in call and "status=publish%2Cdraft" in call for call in calls)
    assert any("/pages?" in call and "status=publish%2Cdraft" in call for call in calls)


def test_browse_publishing_content_can_request_drafts_only(monkeypatch) -> None:
    calls: list[str] = []

    def _urlopen(request, **_kwargs):
        calls.append(request.full_url)
        return _FakeResponse([
            {
                "id": 11,
                "link": "https://example.com/posts/draft",
                "title": {"rendered": "Draft post"},
                "status": "draft",
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

    ok, _message, items = publishing.browse_publishing_content(
        profile,
        "secret",
        content_kinds=("post",),
        statuses=("draft",),
    )

    assert ok is True
    assert [item.status for item in items] == ["draft"]
    assert calls == [
        "https://example.com/wp-json/wp/v2/posts?context=edit&per_page=50&status=draft&_fields=id%2Clink%2Ctitle%2Cstatus%2Cmodified_gmt%2Ctype"
    ]


def test_browse_publishing_content_returns_partial_results_when_one_kind_times_out(
    monkeypatch,
) -> None:
    def _urlopen(request, **_kwargs):
        if "/pages?" in request.full_url:
            raise TimeoutError("timed out")
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

    ok, message, items = publishing.browse_publishing_content(profile, "secret")

    assert ok is True
    assert [item.title for item in items] == ["Hello post"]
    assert message == (
        "Loaded partial publishing content from example.com. "
        "Some content could not be loaded: "
        "Pages: Connection timed out. Check the site URL and try again. "
        "Try again with a narrower content scope."
    )


def test_browse_publishing_content_raises_cancelled_before_any_request(monkeypatch) -> None:
    calls: list[str] = []

    def _urlopen(request, **_kwargs):
        calls.append(request.full_url)
        raise AssertionError("No network call should happen when already cancelled.")

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    try:
        publishing.browse_publishing_content(
            profile,
            "secret",
            content_kinds=("post", "page"),
            is_cancelled=lambda: True,
        )
    except PublishingOperationCancelled:
        pass
    else:
        raise AssertionError("Expected PublishingOperationCancelled to propagate.")

    assert calls == []


def test_browse_publishing_content_cancels_before_second_kind(monkeypatch) -> None:
    calls: list[str] = []

    def _urlopen(request, **_kwargs):
        calls.append(request.full_url)
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

    def _is_cancelled() -> bool:
        # Cancel once the loop reaches the second requested content kind.
        return len(calls) >= 1

    try:
        publishing.browse_publishing_content(
            profile,
            "secret",
            content_kinds=("post", "page"),
            is_cancelled=_is_cancelled,
        )
    except PublishingOperationCancelled:
        pass
    else:
        raise AssertionError("Expected PublishingOperationCancelled to propagate.")

    assert len(calls) == 1
    assert "/posts?" in calls[0]


def test_load_publishing_remote_item_returns_remote_document(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "About page"},
            "status": "publish",
            "modified_gmt": "2026-06-08T05:00:00",
            "type": "page",
            "content": {"rendered": "<p>About body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.load_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
    )

    assert ok is True
    assert message == "Opened publishing content from example.com."
    assert document is not None
    assert document.title == "About page"
    assert document.content_kind == "page"
    assert document.body == "<p>About body</p>"


def test_load_publishing_remote_item_decodes_typographic_html_entities(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "Writer&#8217;s notes"},
            "status": "publish",
            "modified_gmt": "2026-06-08T05:00:00",
            "type": "page",
            "content": {
                "rendered": (
                    "<p>It&#8217;s ready&#8230; &ldquo;Quoted&rdquo; text&nbsp;with spacing.</p>"
                )
            },
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, _message, document = publishing.load_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
    )

    assert ok is True
    assert document is not None
    assert document.title == "Writer’s notes"
    assert document.body == "<p>It’s ready… “Quoted” text with spacing.</p>"


def test_load_publishing_remote_item_preserves_markup_significant_escapes(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "Code sample"},
            "status": "publish",
            "modified_gmt": "2026-06-08T05:00:00",
            "type": "page",
            "content": {
                "rendered": "<pre>&lt;em&gt;keep escaped markup&lt;/em&gt; &amp; text</pre>"
            },
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, _message, document = publishing.load_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
    )

    assert ok is True
    assert document is not None
    assert document.body == "<pre>&lt;em&gt;keep escaped markup&lt;/em&gt; &amp; text</pre>"


def test_wordpress_update_remote_item_posts_json_payload(monkeypatch) -> None:
    request_details: dict[str, object] = {}

    def _urlopen(request, **_kwargs):
        request_details["url"] = request.full_url
        request_details["method"] = request.get_method()
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "About page"},
            "status": "publish",
            "modified_gmt": "2026-06-08T05:00:00",
            "type": "page",
            "content": {"rendered": "<p>About body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.update_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        title="About page",
        document_text="<p>About body</p>",
        authoring_surface="html",
    )

    assert ok is True
    assert message == "Updated publishing content on example.com."
    assert document is not None
    assert request_details["method"] == "POST"
    assert (
        request_details["url"]
        == "https://example.com/wp-json/wp/v2/pages/22?context=edit&_fields=id%2Clink%2Ctitle%2Cstatus%2Cmodified_gmt%2Cdate_gmt%2Ctype%2Ccontent"
    )
    assert json.loads(str(request_details["body"])) == {
        "title": "About page",
        "content": "<p>About body</p>",
    }


def test_wordpress_publish_remote_item_posts_publish_status(monkeypatch) -> None:
    request_details: dict[str, object] = {}

    def _urlopen(request, **_kwargs):
        request_details["url"] = request.full_url
        request_details["method"] = request.get_method()
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "About page"},
            "status": "publish",
            "modified_gmt": "2026-06-08T05:00:00",
            "type": "page",
            "content": {"rendered": "<p>About body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.update_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        title="About page",
        document_text="<p>About body</p>",
        authoring_surface="html",
        status="publish",
    )

    assert ok is True
    assert message == "Updated publishing content on example.com."
    assert document is not None
    assert document.status == "publish"
    assert request_details["method"] == "POST"
    assert (
        request_details["url"]
        == "https://example.com/wp-json/wp/v2/pages/22?context=edit&_fields=id%2Clink%2Ctitle%2Cstatus%2Cmodified_gmt%2Cdate_gmt%2Ctype%2Ccontent"
    )
    assert json.loads(str(request_details["body"])) == {
        "title": "About page",
        "content": "<p>About body</p>",
        "status": "publish",
    }


def test_wordpress_create_remote_item_posts_json_payload(monkeypatch) -> None:
    request_details: dict[str, object] = {}

    def _urlopen(request, **_kwargs):
        request_details["url"] = request.full_url
        request_details["method"] = request.get_method()
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 44,
            "link": "https://example.com/posts/draft",
            "title": {"rendered": "Draft title"},
            "status": "draft",
            "modified_gmt": "2026-06-12T22:00:00",
            "type": "post",
            "content": {"rendered": "<p>Draft body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.create_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        title="Draft title",
        document_text="<p>Draft body</p>",
        authoring_surface="html",
        status="draft",
    )

    assert ok is True
    assert message == "Created publishing content on example.com."
    assert document is not None
    assert request_details["method"] == "POST"
    assert (
        request_details["url"]
        == "https://example.com/wp-json/wp/v2/posts?context=edit&_fields=id%2Clink%2Ctitle%2Cstatus%2Cmodified_gmt%2Cdate_gmt%2Ctype%2Ccontent"
    )
    assert json.loads(str(request_details["body"])) == {
        "title": "Draft title",
        "content": "<p>Draft body</p>",
        "status": "draft",
    }


def test_wordpress_publish_current_item_posts_publish_status(monkeypatch) -> None:
    request_details: dict[str, object] = {}

    def _urlopen(request, **_kwargs):
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 45,
            "link": "https://example.com/posts/live",
            "title": {"rendered": "Live title"},
            "status": "publish",
            "modified_gmt": "2026-06-12T22:15:00",
            "type": "post",
            "content": {"rendered": "<p>Live body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.create_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        title="Live title",
        document_text="<p>Live body</p>",
        authoring_surface="html",
        status="publish",
    )

    assert ok is True
    assert message == "Created publishing content on example.com."
    assert document is not None
    assert document.status == "publish"
    assert json.loads(str(request_details["body"])) == {
        "title": "Live title",
        "content": "<p>Live body</p>",
        "status": "publish",
    }


def test_load_publishing_remote_item_rejects_unsupported_content_kind() -> None:
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.load_publishing_remote_item(
        profile,
        "secret",
        content_kind="product",
        remote_id="22",
    )

    assert ok is False
    assert message == "That publishing content type is not supported for this provider."
    assert document is None


def test_prepare_publishing_remote_content_defaults_to_readable_markdown() -> None:
    prepared = publishing.prepare_publishing_remote_content("<h1>Title</h1><p>Hello world</p>")

    assert prepared.authoring_surface == "markdown"
    assert prepared.open_representation == "readable_markdown"
    assert prepared.text == "# Title\n\nHello world\n"


def test_prepare_publishing_remote_content_allows_raw_html_override() -> None:
    prepared = publishing.prepare_publishing_remote_content(
        "<p>Hello world</p>",
        requested_open_representation="raw_html",
    )

    assert prepared.authoring_surface == "html"
    assert prepared.open_representation == "raw_html"
    assert prepared.text == "<p>Hello world</p>"


def test_prepare_publishing_remote_content_falls_back_to_raw_html_for_tables() -> None:
    prepared = publishing.prepare_publishing_remote_content("<table><tr><td>Cell</td></tr></table>")

    assert prepared.authoring_surface == "html"
    assert prepared.open_representation == "raw_html"
    assert prepared.text == "<table><tr><td>Cell</td></tr></table>"


def test_publishing_result_message_names_outcome_site_state_and_link() -> None:
    document = PublishingRemoteDocument(
        provider_id="wordpress",
        site_url="https://example.com",
        remote_id="22",
        remote_url="https://example.com/about",
        title="About page",
        status="publish",
        updated_at="2026-06-18T12:00:00",
        content_kind="page",
        body="<p>About body</p>",
    )

    assert publishing.publishing_result_message("updated", document) == (
        "Updated page on example.com.\n"
        "Title: About page\n"
        "Status: published\n"
        "Link: https://example.com/about"
    )


def test_publishing_result_message_handles_drafts_without_link() -> None:
    document = PublishingRemoteDocument(
        provider_id="wordpress",
        site_url="https://example.com",
        remote_id="11",
        remote_url="",
        title="Draft post",
        status="draft",
        updated_at="2026-06-18T12:00:00",
        content_kind="post",
        body="<p>Draft body</p>",
    )

    assert publishing.publishing_result_message("created", document) == (
        "Created post on example.com.\nTitle: Draft post\nStatus: draft"
    )


def test_update_publishing_remote_item_converts_markdown_tabs_to_html_body(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _update_remote_item(profile, secret, **kwargs):
        captured["profile"] = profile
        captured["secret"] = secret
        captured.update(kwargs)
        return True, "Updated publishing content on example.com.", None

    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    client = publishing_provider_client("wordpress")
    assert client is not None
    monkeypatch.setattr(client, "update_remote_item", _update_remote_item)

    ok, message, document = publishing.update_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        remote_id="22",
        title="Hello",
        document_text="# Title\n\nHello world",
        authoring_surface="markdown",
    )

    assert ok is True
    assert message == "Updated publishing content on example.com."
    assert document is None
    assert captured["content_kind"] == "post"
    assert captured["remote_id"] == "22"
    assert captured["title"] == "Hello"
    assert captured["body_html"] == '<h1 id="title">Title</h1>\n<p>Hello world</p>'


def test_update_publishing_remote_item_preserves_html_tabs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _update_remote_item(profile, secret, **kwargs):
        captured.update(kwargs)
        return True, "Updated publishing content on example.com.", None

    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    client = publishing_provider_client("wordpress")
    assert client is not None
    monkeypatch.setattr(client, "update_remote_item", _update_remote_item)

    ok, _message, _document = publishing.update_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        title="About",
        document_text="<p>About body</p>",
        authoring_surface="html",
    )

    assert ok is True
    assert captured["body_html"] == "<p>About body</p>"


def test_create_publishing_remote_item_converts_markdown_tabs_to_html_body(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _create_remote_item(profile, secret, **kwargs):
        captured["profile"] = profile
        captured["secret"] = secret
        captured.update(kwargs)
        return True, "Created publishing content on example.com.", None

    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    client = publishing_provider_client("wordpress")
    assert client is not None
    monkeypatch.setattr(client, "create_remote_item", _create_remote_item)

    ok, message, document = publishing.create_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        title="Hello",
        document_text="# Title\n\nHello world",
        authoring_surface="markdown",
        status="draft",
    )

    assert ok is True
    assert message == "Created publishing content on example.com."
    assert document is None
    assert captured["content_kind"] == "post"
    assert captured["title"] == "Hello"
    assert captured["status"] == "draft"
    assert captured["body_html"] == '<h1 id="title">Title</h1>\n<p>Hello world</p>'


def test_wordpress_create_remote_item_with_scheduled_at_sends_future_status_and_date_gmt(
    monkeypatch,
) -> None:
    request_details: dict[str, object] = {}
    # Use a dynamic future time so this never expires: validate_scheduled_publish_time
    # rejects a `scheduled_at` that is not strictly after "now" (which a hardcoded date
    # eventually becomes). date_gmt is formatted with the production strftime pattern.
    future = (datetime.now(UTC) + timedelta(days=7)).replace(microsecond=0)
    future_gmt = future.strftime("%Y-%m-%dT%H:%M:%S")

    def _urlopen(request, **_kwargs):
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 46,
            "link": "https://example.com/posts/future",
            "title": {"rendered": "Future title"},
            "status": "future",
            "modified_gmt": "2026-06-21T18:00:00",
            "date_gmt": future_gmt,
            "type": "post",
            "content": {"rendered": "<p>Future body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.create_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        title="Future title",
        document_text="<p>Future body</p>",
        authoring_surface="html",
        scheduled_at=future,
    )

    assert ok is True
    assert message == "Created publishing content on example.com."
    assert document is not None
    assert document.status == "future"
    assert document.scheduled_for == future_gmt
    assert json.loads(str(request_details["body"])) == {
        "title": "Future title",
        "content": "<p>Future body</p>",
        "status": "future",
        "date_gmt": future_gmt,
    }


def test_wordpress_update_remote_item_with_scheduled_at_sends_future_status_and_date_gmt(
    monkeypatch,
) -> None:
    request_details: dict[str, object] = {}
    # Dynamic future time so this never expires (the scheduler rejects a
    # non-future time) — the same pattern as the UTC-offset test below.
    future = (datetime.now(UTC) + timedelta(days=7)).replace(second=0, microsecond=0)
    expected_date_gmt = future.strftime("%Y-%m-%dT%H:%M:%S")

    def _urlopen(request, **_kwargs):
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "About page"},
            "status": "future",
            "modified_gmt": "2026-06-21T18:00:00",
            "date_gmt": expected_date_gmt,
            "type": "page",
            "content": {"rendered": "<p>About body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, document = publishing.update_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        title="About page",
        document_text="<p>About body</p>",
        authoring_surface="html",
        scheduled_at=future,
    )

    assert ok is True
    assert document is not None
    assert document.status == "future"
    assert document.scheduled_for == expected_date_gmt
    assert json.loads(str(request_details["body"])) == {
        "title": "About page",
        "content": "<p>About body</p>",
        "status": "future",
        "date_gmt": expected_date_gmt,
    }


def test_wordpress_schedule_converts_non_utc_offset_to_utc_date_gmt(monkeypatch) -> None:
    request_details: dict[str, object] = {}

    minus_four = timezone(timedelta(hours=-4))
    # Dynamic future time in a non-UTC zone so this never expires (the scheduler
    # rejects a non-future time); expected date_gmt is that instant converted to UTC
    # with the production strftime pattern.
    future_local = (datetime.now(minus_four) + timedelta(days=7)).replace(second=0, microsecond=0)
    future_gmt = future_local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")

    def _urlopen(request, **_kwargs):
        request_details["body"] = request.data.decode("utf-8") if request.data else ""
        return _FakeResponse({
            "id": 48,
            "link": "https://example.com/posts/future",
            "title": {"rendered": "Future title"},
            "status": "future",
            "modified_gmt": "2026-06-21T18:00:00",
            "date_gmt": future_gmt,
            "type": "post",
            "content": {"rendered": "<p>Future body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, _message, _document = publishing.create_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        title="Future title",
        document_text="<p>Future body</p>",
        authoring_surface="html",
        scheduled_at=future_local,
    )

    assert ok is True
    assert json.loads(str(request_details["body"]))["date_gmt"] == future_gmt


def test_create_publishing_remote_item_rejects_past_scheduled_time(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        raise AssertionError("No network call should happen for a past scheduled time.")

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    past = datetime(2020, 1, 1, tzinfo=UTC)

    ok, message, document = publishing.create_publishing_remote_item(
        profile,
        "secret",
        content_kind="post",
        title="Too late",
        document_text="<p>Body</p>",
        authoring_surface="html",
        scheduled_at=past,
    )

    assert ok is False
    assert message == "Choose a publish time that is in the future."
    assert document is None


def test_update_publishing_remote_item_rejects_naive_scheduled_time(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        raise AssertionError("No network call should happen for a naive scheduled time.")

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    naive = datetime(2026, 7, 1, 12, 0)

    ok, message, document = publishing.update_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        title="About page",
        document_text="<p>Body</p>",
        authoring_surface="html",
        scheduled_at=naive,
    )

    assert ok is False
    assert message == "Choose a time zone for the scheduled publish time."
    assert document is None


def test_compare_publishing_remote_item_reports_no_differences(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "About page"},
            "status": "publish",
            "modified_gmt": "2026-06-18T12:00:00",
            "type": "page",
            "content": {"rendered": "<p>About body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, _message, comparison = publishing.compare_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        local_title="About page",
        local_document_text="<p>About body</p>",
        local_authoring_surface="html",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert ok is True
    assert comparison is not None
    assert comparison.title_differs is False
    assert comparison.body_differs is False
    assert comparison.status_differs is False
    assert comparison.remote_changed_since_last_known is False


def test_compare_publishing_remote_item_reports_remote_change_honestly(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        return _FakeResponse({
            "id": 22,
            "link": "https://example.com/about",
            "title": {"rendered": "About page, edited remotely"},
            "status": "publish",
            "modified_gmt": "2026-06-20T09:00:00",
            "type": "page",
            "content": {"rendered": "<p>About body</p>"},
        })

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, comparison = publishing.compare_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        local_title="About page",
        local_document_text="<p>About body</p>",
        local_authoring_surface="html",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert ok is True
    assert message == "Opened publishing content from example.com."
    assert comparison is not None
    assert comparison.title_differs is True
    assert comparison.remote_changed_since_last_known is True
    report = publishing.publishing_comparison_message(comparison)
    assert "Title: differs" in report
    assert "Remote changed since you last synced" in report


def test_compare_publishing_remote_item_propagates_load_failure(monkeypatch) -> None:
    def _urlopen(request, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(publishing_clients, "urlopen", _urlopen)
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message, comparison = publishing.compare_publishing_remote_item(
        profile,
        "secret",
        content_kind="page",
        remote_id="22",
        local_title="About page",
        local_document_text="<p>About body</p>",
        local_authoring_surface="html",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert ok is False
    assert message == "Connection timed out. Check the site URL and try again."
    assert comparison is None
