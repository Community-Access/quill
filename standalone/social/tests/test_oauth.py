"""Tests for the Mastodon OAuth helper (PRD 11.1). No network, no SDK."""

from quill_social.adapters import oauth


def test_normalize_instance():
    assert oauth.normalize_instance("https://Mastodon.Social/") == "mastodon.social"
    assert oauth.normalize_instance("tweesecake.social") == "tweesecake.social"


def test_base_url_adds_scheme():
    assert oauth.base_url("mastodon.online") == "https://mastodon.online"
    assert oauth.base_url("http://local.test") == "http://local.test"


def test_register_app_caches(tmp_path):
    calls = []

    def fake_create(instance):
        calls.append(instance)
        return ("CID", "CSECRET")

    a = oauth.register_app("mastodon.social", tmp_path, create=fake_create)
    b = oauth.register_app("mastodon.social", tmp_path, create=fake_create)
    assert a == ("CID", "CSECRET")
    assert b == ("CID", "CSECRET")
    assert len(calls) == 1  # second call served from cache
    assert oauth.cached_app(tmp_path, "https://mastodon.social/") == ("CID", "CSECRET")


def test_auth_url_uses_scopes_and_redirect():
    class FakeClient:
        def __init__(self):
            self.kwargs = None

        def auth_request_url(self, scopes, redirect_uris):
            self.kwargs = (scopes, redirect_uris)
            return "https://mastodon.social/oauth/authorize?x=1"

    made = {}

    def factory(instance, cid, csec):
        made["args"] = (instance, cid, csec)
        return FakeClient()

    url = oauth.auth_url("mastodon.social", "CID", "CSEC", factory=factory)
    assert url.startswith("https://mastodon.social/oauth/authorize")
    assert made["args"] == ("mastodon.social", "CID", "CSEC")


def test_exchange_code_returns_token():
    class FakeClient:
        def log_in(self, code, scopes, redirect_uri):
            assert code == "ABC123"
            assert redirect_uri == oauth.REDIRECT
            return "ACCESS_TOKEN_XYZ"

    token = oauth.exchange_code(
        "mastodon.social", "CID", "CSEC", "  ABC123 ",
        factory=lambda *a: FakeClient())
    assert token == "ACCESS_TOKEN_XYZ"
