"""Tests for ordered thread publishing with pause-on-failure (PRD 16.2)."""

from quill_social.adapters.base import AdapterError
from quill_social.services.thread_publisher import publish_thread
from tests.conftest import ScriptedAdapter


def test_publishes_all_in_order_as_reply_chain():
    adapter = ScriptedAdapter(["ok", "ok", "ok"])
    result = publish_thread(adapter, ["one", "two", "three"], run_id="run1")
    assert result.ok
    assert result.published_count == 3
    # Each segment after the first replies to the previous remote id.
    assert adapter.calls[0].in_reply_to == ""
    assert adapter.calls[1].in_reply_to == "r1"
    assert adapter.calls[2].in_reply_to == "r2"


def test_pauses_on_failure_and_does_not_continue():
    adapter = ScriptedAdapter(["ok", AdapterError("boom", kind="transient")])
    result = publish_thread(adapter, ["one", "two", "three"], run_id="run1")
    assert not result.ok
    assert result.failed_index == 2
    assert result.published_count == 1
    # The third segment was never attempted.
    assert len(adapter.calls) == 2


def test_summary_is_plain_language():
    adapter = ScriptedAdapter(["ok", AdapterError("boom", kind="transient")])
    result = publish_thread(adapter, ["one", "two", "three"], run_id="run1")
    s = result.summary()
    assert "Published 1 of 3" in s
    assert "Segment 2 failed" in s


def test_repair_resumes_without_republishing():
    # First run fails on segment 2.
    a1 = ScriptedAdapter(["ok", AdapterError("boom", kind="transient")])
    r1 = publish_thread(a1, ["one", "two", "three"], run_id="run1")
    assert r1.failed_index == 2
    # Repair: resume from segment 2, chained to the last good remote id.
    a2 = ScriptedAdapter(["ok", "ok"])
    r2 = publish_thread(a2, ["one", "two", "three"], run_id="run1",
                        start_index=2, parent_remote_id=r1.parent_remote_id)
    assert r2.ok is False or r2.published_count == 2
    # Segment "one" was not published again in the repair run.
    assert a2.calls[0].text == "two"
    assert a2.calls[0].in_reply_to == "r1"


def test_idempotency_keys_are_stable_per_segment():
    adapter = ScriptedAdapter(["ok", "ok"])
    publish_thread(adapter, ["one", "two"], run_id="abc")
    assert adapter.calls[0].idempotency_key == "abc:1"
    assert adapter.calls[1].idempotency_key == "abc:2"


def test_content_warning_only_on_head():
    adapter = ScriptedAdapter(["ok", "ok"])
    publish_thread(adapter, ["one", "two"], run_id="x", content_warning="CW")
    assert adapter.calls[0].content_warning == "CW"
    assert adapter.calls[1].content_warning == ""


def test_progress_callback_fires_per_success():
    adapter = ScriptedAdapter(["ok", "ok"])
    seen = []
    publish_thread(adapter, ["one", "two"], run_id="x",
                   on_progress=lambda i, total, rid: seen.append((i, total, rid)))
    assert seen == [(1, 2, "r1"), (2, 2, "r2")]
