"""Regression tests for the macOS self-voicing bug.

On macOS the announcement engine must hand text to VoiceOver via the
accessibility API and must NEVER fall back to SAPI self-voicing (the system
voice), which would talk over VoiceOver. See the darwin branch in
AnnouncementEngine.announce.
"""

from __future__ import annotations

import quill.platform.macos.announce as macos_announce
import quill.platform.windows.prism_bridge as prism_bridge


def _engine_without_backend() -> prism_bridge.AnnouncementEngine:
    engine = prism_bridge.AnnouncementEngine("auto")
    # Force the no-backend fallback path deterministically. The machine running
    # the test may have a Prism runtime AND/OR a live screen reader: the latter
    # populates the accessible_output2 speaker, whose branch in announce() runs
    # before the macOS branch. Null both so the platform routing under test is
    # actually reached regardless of the host's assistive-tech state.
    engine._runtime_backend = None
    engine._ao2_speaker = None
    return engine


def test_macos_announce_routes_to_voiceover(monkeypatch) -> None:
    received: list[str] = []
    monkeypatch.setattr(macos_announce, "announce", lambda m: received.append(m) or True)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    result = engine.announce("hello voiceover")

    assert result is None
    assert received == ["hello voiceover"]


def test_macos_never_self_voices_with_sapi(monkeypatch) -> None:
    monkeypatch.setattr(macos_announce, "announce", lambda m: True)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    def _tripwire() -> object:
        raise AssertionError("SAPI self-voicing was used on macOS — it talks over VoiceOver")

    # Building the SAPI voice would mean self-voicing; the darwin branch must
    # return before any such call.
    monkeypatch.setattr(prism_bridge, "_build_tts_voice", _tripwire)

    engine = _engine_without_backend()
    assert engine.announce("anything") is None


def test_macos_announce_swallows_voiceover_errors(monkeypatch) -> None:
    def _boom(_message: str) -> bool:
        raise RuntimeError("AppKit not available")

    monkeypatch.setattr(macos_announce, "announce", _boom)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    # A VoiceOver dispatch failure must not crash the app.
    assert engine.announce("hi") is None
