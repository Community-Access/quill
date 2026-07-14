"""Narrator support (#966): API-level liveness + the UIA notification channel."""

from __future__ import annotations

import sys

import pytest

from quill.platform.windows import narrator_announce, sr_detect


def test_narrator_event_probe_never_raises_and_is_bool() -> None:
    # On Windows this reads the real named event; elsewhere it must be a
    # quiet False. Either way: bool out, no exception.
    assert sr_detect.narrator_event_present() in (True, False)


def test_detection_prefers_process_names_then_event(monkeypatch) -> None:
    # A supplied snapshot is authoritative (test mode: no OS probes at all).
    hit = sr_detect.detect_screen_reader(["Narrator.exe"])
    assert hit.detected and hit.name == "Narrator"
    miss = sr_detect.detect_screen_reader(["notepad.exe"])
    assert not miss.detected

    # Live mode: an empty process list falls back to the named-event marker.
    monkeypatch.setattr(sr_detect, "_running_process_names", lambda: [])
    monkeypatch.setattr(sr_detect, "narrator_event_present", lambda: True)
    live = sr_detect.detect_screen_reader()
    assert live.detected and live.name == "Narrator"
    assert live.source == "NarratorRunning"
    monkeypatch.setattr(sr_detect, "narrator_event_present", lambda: False)
    assert sr_detect.detect_screen_reader().detected is False


def test_announce_declines_off_windows_or_with_empty_text(monkeypatch) -> None:
    narrator_announce.reset_for_tests()
    assert narrator_announce.announce("") is False
    if sys.platform != "win32":  # pragma: no cover - windows CI
        assert narrator_announce.announce("hello") is False
        assert narrator_announce.available() is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows UIA chain")
def test_announce_degrades_to_false_without_a_window(monkeypatch) -> None:
    # No visible top-level window owned by the process (headless test run
    # after forcing the lookup to fail): the channel reports False so the
    # caller falls back to the status bar — never an exception.
    narrator_announce.reset_for_tests()
    monkeypatch.setattr(narrator_announce, "_own_top_level_hwnd", lambda: 0)
    assert narrator_announce.announce("hello") is False


def test_prism_bridge_prefers_uia_notification_over_silence(monkeypatch) -> None:
    # With a live-but-unbridged reader, the announcement goes to the reader's
    # UIA notification channel when it works, and to the status bar when it
    # does not — the SAPI self-voice never runs either way (#966).
    from quill.platform.windows import prism_bridge
    from quill.platform.windows.prism_bridge import AnnouncementEngine

    monkeypatch.setattr(prism_bridge, "_screen_reader_active", lambda: True)
    monkeypatch.setattr(prism_bridge.sys, "platform", "win32")
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda _name: (_ for _ in ()).throw(ImportError),
    )
    # Hermetic: the machine running the tests may have a real reader that
    # accessible_output2 can drive; this test is about the unbridged case.
    monkeypatch.setattr(prism_bridge, "_ao2_live_screen_reader", lambda: (None, None))
    spoken: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        narrator_announce,
        "announce",
        lambda message, important=False: (spoken.append((message, important)), True)[1],
    )
    engine = AnnouncementEngine("auto")
    assert engine.announce("Saved", force_speech=False) is None
    assert engine.announce("QUILL key", force_speech=True) is None
    assert spoken == [("Saved", False), ("QUILL key", True)]
    assert engine.state().active_backend == "uia_notification"

    # Channel failure: quiet status-bar fallback, still no SAPI.
    monkeypatch.setattr(narrator_announce, "announce", lambda *a, **k: False)
    assert engine.announce("Another") is None
