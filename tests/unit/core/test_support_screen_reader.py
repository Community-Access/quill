"""Support includes live reader versions without leaking local machine paths."""

from __future__ import annotations

import sys

from quill.core import support_screen_reader
from quill.platform.windows import screen_reader_info, sr_detect


def test_jaws_version_is_collected_without_path_or_pid(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        screen_reader_info,
        "get_running_screen_readers",
        lambda: [
            {
                "name": "JAWS",
                "version": "2026.2608.25.400",
                "file_version": "27.6.18.0",
                "pid": 20280,
                "executable": r"C:\Users\person\JAWS\jfw.exe",
            }
        ],
    )
    monkeypatch.setattr(sr_detect, "narrator_event_present", lambda: False)

    assert support_screen_reader.detected_reader_name() == "JAWS"
    facts = support_screen_reader.screen_reader_support_facts("JAWS")
    assert facts["Screen reader version"] == "2026.2608.25.400"
    assert facts["Screen reader file version"] == "27.6.18.0"
    assert "20280" not in str(facts)
    assert "C:\\Users" not in str(facts)


def test_two_running_readers_do_not_claim_to_identify_the_active_one(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        screen_reader_info,
        "get_running_screen_readers",
        lambda: [{"name": "JAWS"}, {"name": "NVDA"}],
    )
    monkeypatch.setattr(sr_detect, "narrator_event_present", lambda: False)

    assert support_screen_reader.detected_reader_name() == ""


def test_probe_failure_does_not_block_support(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")

    def unavailable():
        raise OSError("process access denied")

    monkeypatch.setattr(screen_reader_info, "get_running_screen_readers", unavailable)
    assert support_screen_reader.screen_reader_support_facts("JAWS") == {}
