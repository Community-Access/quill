"""Tests for on-demand health revalidation (PRD 13.4, 17.4)."""

from quill.apps.beacon import health
from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import HEALTH_BROKEN, Beacon, Resource


def _store(tmp_path):
    return BeaconStore(str(tmp_path / "h.db"))


def _web(store, title, uri):
    res = Resource(title=title, type="web", primary_uri=uri)
    b = Beacon(resource_id=res.resource_id, title=title, in_inbox=False)
    store.put_beacon(b, resource=res)
    return b


def _file(store, title, path):
    res = Resource(title=title, type="file", primary_uri=str(path))
    b = Beacon(resource_id=res.resource_id, title=title, in_inbox=False)
    store.put_beacon(b, resource=res)
    return b


def test_no_fetcher_skips_web(tmp_path):
    s = _store(tmp_path)
    b = _web(s, "A", "https://example.com/x")
    summary = health.revalidate(s)  # no fetcher
    assert summary["fetcher"] is False
    assert summary["skipped"] == 1
    assert summary["checked"] == 0
    # Health unchanged.
    assert s.get_beacon(b.beacon_id).health != HEALTH_BROKEN


def test_fetcher_marks_reachable_available(tmp_path):
    s = _store(tmp_path)
    b = _web(s, "A", "https://example.com/x")
    b.health = HEALTH_BROKEN
    s.put_beacon(b)

    def fetcher(url, timeout):
        return (200, "text/html")

    summary = health.revalidate(s, fetcher=fetcher)
    assert summary["checked"] == 1
    assert summary["available"] == 1
    assert s.get_beacon(b.beacon_id).health == "available"


def test_fetcher_marks_unreachable_broken(tmp_path):
    s = _store(tmp_path)
    b = _web(s, "A", "https://example.com/x")

    def fetcher(url, timeout):
        return (404, "")

    summary = health.revalidate(s, fetcher=fetcher)
    assert summary["broken"] == 1
    assert s.get_beacon(b.beacon_id).health == HEALTH_BROKEN


def test_fetcher_exception_is_broken(tmp_path):
    s = _store(tmp_path)
    b = _web(s, "A", "https://example.com/x")

    def fetcher(url, timeout):
        raise ConnectionError("boom")

    summary = health.revalidate(s, fetcher=fetcher)
    assert summary["broken"] == 1
    assert s.get_beacon(b.beacon_id).health == HEALTH_BROKEN


def test_fetcher_none_result_is_broken(tmp_path):
    s = _store(tmp_path)
    _web(s, "A", "https://example.com/x")

    def fetcher(url, timeout):
        return None

    summary = health.revalidate(s, fetcher=fetcher)
    assert summary["broken"] == 1


def test_local_file_checked_without_fetcher(tmp_path):
    s = _store(tmp_path)
    exists = tmp_path / "real.txt"
    exists.write_text("hi")
    b_ok = _file(s, "Real", exists)
    b_gone = _file(s, "Gone", tmp_path / "missing.txt")
    summary = health.revalidate(s)  # no fetcher -> files still checked
    assert summary["checked"] == 2
    assert summary["available"] == 1
    assert summary["broken"] == 1
    assert s.get_beacon(b_ok.beacon_id).health == "available"
    assert s.get_beacon(b_gone.beacon_id).health == HEALTH_BROKEN


def test_empty_uri_is_broken(tmp_path):
    s = _store(tmp_path)
    res = Resource(title="E", type="web", primary_uri="")
    b = Beacon(resource_id=res.resource_id, title="E", in_inbox=False)
    s.put_beacon(b, resource=res)
    summary = health.revalidate(s, fetcher=lambda u, t: (200, ""))
    assert summary["broken"] == 1


def test_revalidate_respects_beacon_ids_subset(tmp_path):
    s = _store(tmp_path)
    b1 = _web(s, "A", "https://x/1")
    b2 = _web(s, "B", "https://x/2")
    summary = health.revalidate(s, fetcher=lambda u, t: (200, ""), beacon_ids=[b1.beacon_id])
    assert summary["checked"] == 1
    assert s.get_beacon(b1.beacon_id).health == "available"
    # b2 untouched.
    assert s.get_beacon(b2.beacon_id).health == "available"  # default health


def test_revalidate_skips_trashed_by_default(tmp_path):
    s = _store(tmp_path)
    b = _web(s, "A", "https://x/1")
    s.trash(b.beacon_id)
    summary = health.revalidate(s, fetcher=lambda u, t: (200, ""))
    assert summary["checked"] == 0
