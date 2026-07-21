"""Tests for the network adapters (PRD 22, 23, 42)."""

from quill_social.adapters.base import AdapterError, PublishRequest
from quill_social.adapters.bluesky import BlueskyAdapter
from quill_social.adapters.mastodon import MastodonAdapter
from quill_social.adapters.mock import MockNetwork
from quill_social.adapters.registry import adapter_for
from quill_social.model import Account


def test_mock_timeline_is_deterministic():
    a = MockNetwork().home_timeline()
    b = MockNetwork().home_timeline()
    assert [i.remote_id for i in a] == [i.remote_id for i in b]
    assert len(a) == 15


def test_mock_publish_appends_and_returns_id():
    net = MockNetwork()
    before = len(net.home_timeline())
    res = net.publish(PublishRequest(text="hi"))
    assert res.remote_id.startswith("mock-")
    assert len(net.home_timeline()) == before + 1
    assert net.home_timeline()[0].text == "hi"


def test_mock_thread_returns_chain_in_order():
    net = MockNetwork()
    root = next(i for i in net.home_timeline() if i.remote_id == "seed-005")
    chain = net.thread(root)
    assert [i.remote_id for i in chain] == ["seed-005", "seed-006", "seed-007"]


def test_mock_has_a_poll_and_a_cw_and_missing_alt():
    items = MockNetwork().home_timeline()
    assert any(i.poll for i in items)
    assert any(i.content_warning for i in items)
    assert any(i.missing_alt_count for i in items)


def test_mastodon_refine_from_instance():
    m = MastodonAdapter(instance="example.social")
    caps = m.refine_from_instance({
        "version": "4.3.0",
        "configuration": {
            "statuses": {"max_characters": 5000, "max_media_attachments": 8},
            "polls": {"max_options": 5},
            "media_attachments": {"description_limit": 2200},
        },
    })
    assert caps.char_limit == 5000
    assert caps.max_media_attachments == 8
    assert caps.max_poll_options == 5
    assert caps.max_alt_text == 2200
    assert caps.server_version == "4.3.0"


def test_live_adapters_report_clear_boundary():
    for adapter in (MastodonAdapter(), BlueskyAdapter()):
        try:
            adapter.home_timeline()
        except AdapterError as exc:
            assert "not enabled" in str(exc)
        else:
            raise AssertionError("expected AdapterError")


def test_registry_maps_networks():
    assert adapter_for(Account(network="mock")).name == "mock"
    assert adapter_for(Account(network="mastodon")).name == "mastodon"
    assert adapter_for(Account(network="bluesky")).name == "bluesky"
    # unknown network never dead-ends
    assert adapter_for(Account(network="weird")).name == "mock"


def test_bluesky_defaults_no_polls():
    assert not BlueskyAdapter().capabilities().supports_polls
