"""End-to-end dispatch tests with injected FAKE clients.

No real SDK is imported. Each adapter is built with a simple fake client that
returns canned data; we assert home_timeline/publish flow through the pure
mapping, and that with NO client the network methods raise a clear
"not enabled" AdapterError. The registry is exercised with an in-memory
credential store and monkeypatched client builders.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill_social.adapters import registry
from quill_social.adapters.base import AdapterError, PublishRequest
from quill_social.adapters.bluesky import BlueskyAdapter
from quill_social.adapters.github import GitHubAdapter
from quill_social.adapters.mastodon import MastodonAdapter
from quill_social.model import Account
from quill_social.security.credentials import InMemoryCredentialStore

# -- fakes --------------------------------------------------------------------


class FakeMastodon:
    def __init__(self):
        self.calls = []
        self._status = {
            "id": "1",
            "url": "https://ex/@ada/1",
            "content": "<p>hi from mastodon</p>",
            "created_at": "2026-07-18T12:00:00Z",
            "account": {"acct": "ada@ex", "display_name": "Ada", "id": "9"},
            "visibility": "public",
            "replies_count": 1,
            "reblogs_count": 2,
            "favourites_count": 3,
        }

    def timeline_home(self, **kw):
        self.calls.append(("timeline_home", kw))
        return [self._status]

    def status_post(self, text, **kw):
        self.calls.append(("status_post", text, kw))
        return {
            "id": "77",
            "url": "https://ex/@me/77",
            "content": f"<p>{text}</p>",
            "created_at": "2026-07-18T12:30:00Z",
            "account": {"acct": "me@ex", "display_name": "Me", "id": "1"},
        }

    def status_favourite(self, remote_id):
        self.calls.append(("status_favourite", remote_id))


class FakeBluesky:
    def __init__(self):
        self.posted = []
        self._feed = [
            {
                "post": {
                    "uri": "at://did:plc:ada/app.bsky.feed.post/1",
                    "cid": "cid1",
                    "author": {"did": "did:plc:ada", "handle": "ada.bsky.social"},
                    "record": {"text": "hi from bsky", "created_at": "2026-07-18T12:00:00Z"},
                    "reply_count": 0,
                    "repost_count": 1,
                    "like_count": 2,
                }
            }
        ]

    def get_timeline(self, limit=40):
        return SimpleNamespace(feed=self._feed)

    def send_post(self, text):
        self.posted.append(text)
        return SimpleNamespace(uri="at://did:plc:me/app.bsky.feed.post/new", cid="cidnew")


def _gh_issue(**over):
    d = {
        "id": 5,
        "number": 3,
        "title": "bug",
        "body": "b",
        "state": "open",
        "labels": [SimpleNamespace(name="accessibility")],
        "user": SimpleNamespace(login="ada"),
        "html_url": "https://github.com/o/r/issues/3",
        "updated_at": "2026-07-18T12:00:00Z",
        "pull_request": None,
    }
    d.update(over)
    return SimpleNamespace(**d)


class FakeRepo:
    def __init__(self):
        self.created = []
        self.comments = []

    def get_issues(self, state="open"):
        return [_gh_issue()]

    def get_pulls(self, state="all"):
        return [SimpleNamespace(id=8, number=10, title="pr", body="", state="open",
                                merged=True, labels=[], user=SimpleNamespace(login="alan"),
                                html_url="https://github.com/o/r/pull/10",
                                updated_at="2026-07-18T12:00:00Z")]

    def create_issue(self, title, body="", labels=None):
        issue = _gh_issue(id=99, number=42, title=title, body=body,
                          labels=[SimpleNamespace(name=x) for x in (labels or [])])
        self.created.append(issue)
        return issue

    def get_issue(self, number):
        return _gh_issue(number=number)


class FakeGithub:
    def __init__(self):
        self.repo = FakeRepo()

    def get_repo(self, repo):
        return self.repo

    def get_user(self):
        note = SimpleNamespace(
            id=1,
            subject=SimpleNamespace(title="mentioned", url="https://api/x"),
            repository=SimpleNamespace(full_name="o/r"),
            unread=True,
            updated_at="2026-07-18T12:00:00Z",
            reason="mention",
        )
        return SimpleNamespace(get_notifications=lambda: [note])


# -- mastodon -----------------------------------------------------------------


def test_mastodon_live_home_and_publish():
    a = MastodonAdapter(instance="ex", account_id="acct_m", client=FakeMastodon())
    items = a.home_timeline(limit=5)
    assert len(items) == 1
    assert items[0].text == "hi from mastodon"
    assert items[0].account_id == "acct_m"
    res = a.publish(PublishRequest(text="posting"))
    assert res.remote_id == "77"
    assert res.item.text == "posting"


def test_mastodon_favourite_dispatches():
    fake = FakeMastodon()
    MastodonAdapter(client=fake).set_favourite("1", True)
    assert ("status_favourite", "1") in fake.calls


def test_mastodon_no_client_raises_not_enabled():
    with pytest.raises(AdapterError) as exc:
        MastodonAdapter().home_timeline()
    assert "not enabled" in str(exc.value)


# -- bluesky ------------------------------------------------------------------


def test_bluesky_live_home_and_publish():
    a = BlueskyAdapter(did="did:plc:me", account_id="acct_b", client=FakeBluesky())
    items = a.home_timeline(limit=5)
    assert len(items) == 1
    assert items[0].text == "hi from bsky"
    assert items[0].author_handle == "@ada.bsky.social"
    res = a.publish(PublishRequest(text="skywrite"))
    assert res.remote_id == "at://did:plc:me/app.bsky.feed.post/new"
    assert res.item.text == "skywrite"


def test_bluesky_no_client_raises_not_enabled():
    with pytest.raises(AdapterError) as exc:
        BlueskyAdapter().home_timeline()
    assert "not enabled" in str(exc.value)


# -- github -------------------------------------------------------------------


def test_github_live_reads_and_writes():
    gh = GitHubAdapter(client=FakeGithub())
    issues = gh.issues("o/r")
    assert issues[0].number == 3
    assert issues[0].author == "@ada"
    assert issues[0].labels == ["accessibility"]
    prs = gh.pull_requests("o/r")
    assert prs[0].state == "merged"
    assert prs[0].merged
    notes = gh.notifications()
    assert notes[0].reason == "mention"
    assert notes[0].repo == "o/r"
    created = gh.create_issue("o/r", "new one", body="x", labels=["bug"])
    assert created.number == 42
    assert created.labels == ["bug"]


def test_github_no_client_raises_permission():
    with pytest.raises(AdapterError) as exc:
        GitHubAdapter().issues("o/r")
    assert exc.value.kind == "permission"
    assert "live GitHub not enabled" in str(exc.value)


# -- registry with credentials ------------------------------------------------


def test_registry_returns_live_adapter_when_credentials_resolve(monkeypatch):
    store = InMemoryCredentialStore()
    acct = Account(network="mastodon", instance="ex.social", account_id="acct_live")
    store.store("mastodon", acct.account_id, "secret-token")

    monkeypatch.setattr(registry, "_build_mastodon_client", lambda instance, token: FakeMastodon())
    adapter = registry.adapter_for(acct, store)
    assert adapter.name == "mastodon"
    # A live adapter: home_timeline flows through mapping instead of raising.
    items = adapter.home_timeline()
    assert items[0].text == "hi from mastodon"


def test_registry_bluesky_live_adapter_when_credentials_resolve(monkeypatch):
    store = InMemoryCredentialStore()
    acct = Account(network="bluesky", did="did:plc:me", handle="me.bsky.social",
                   account_id="acct_bsky")
    store.store("bluesky", acct.account_id, "app-password")

    monkeypatch.setattr(registry, "_build_bluesky_client",
                        lambda ident, service, secret: FakeBluesky())
    adapter = registry.adapter_for(acct, store)
    assert adapter.name == "bluesky"
    assert adapter.home_timeline()[0].text == "hi from bsky"


def test_registry_without_credentials_returns_descriptor():
    acct = Account(network="mastodon", instance="ex.social")
    adapter = registry.adapter_for(acct)
    assert adapter.name == "mastodon"
    with pytest.raises(AdapterError) as exc:
        adapter.home_timeline()
    assert "not enabled" in str(exc.value)


def test_registry_credentials_present_but_no_secret_returns_descriptor():
    store = InMemoryCredentialStore()  # empty
    acct = Account(network="bluesky", did="did:plc:x")
    adapter = registry.adapter_for(acct, store)
    with pytest.raises(AdapterError) as exc:
        adapter.home_timeline()
    assert "not enabled" in str(exc.value)
