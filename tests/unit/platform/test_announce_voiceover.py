"""Regression tests for the macOS announcement routing.

Two darwin paths, mutually exclusive so they never double-talk:

- VoiceOver *running*: hand the text to VoiceOver via the accessibility API and
  NEVER self-voice with the system voice (that would talk over VoiceOver).
- VoiceOver *off*: self-voice via the native macOS TTS backend
  (``NSSpeechSynthesizer``) so a low-vision Mac user without VoiceOver still
  hears announcements instead of every ``self._announce(...)`` being silently
  swallowed (#2). Mirrors the Windows SAPI self-voice fallback.

``_macos_screen_reader_active`` is monkeypatched so both branches are exercised
deterministically on any host.
"""

from __future__ import annotations

import quill.platform.macos.announce as macos_announce
import quill.platform.macos.tts as macos_tts
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


# --- VoiceOver running -> route to VoiceOver, never self-voice ---------------


def test_macos_announce_routes_to_voiceover(monkeypatch) -> None:
    received: list[str] = []
    monkeypatch.setattr(macos_announce, "announce", lambda m: received.append(m) or True)
    monkeypatch.setattr(prism_bridge, "_macos_screen_reader_active", lambda: True)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    result = engine.announce("hello voiceover")

    assert result is None
    assert received == ["hello voiceover"]


def test_macos_never_self_voices_with_sapi(monkeypatch) -> None:
    monkeypatch.setattr(macos_announce, "announce", lambda m: True)
    monkeypatch.setattr(prism_bridge, "_macos_screen_reader_active", lambda: True)
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
    monkeypatch.setattr(prism_bridge, "_macos_screen_reader_active", lambda: True)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    # A VoiceOver dispatch failure must not crash the app.
    assert engine.announce("hi") is None


# --- VoiceOver off -> self-voice via native macOS TTS (#2) -------------------


def test_macos_announce_self_voices_when_voiceover_off(monkeypatch) -> None:
    """#2: with VoiceOver off, announcements go to NSSpeechSynthesizer, not VoiceOver."""
    voiced: list[str] = []
    monkeypatch.setattr(macos_tts, "speak_announcement", lambda m: voiced.append(m) or True)
    monkeypatch.setattr(macos_tts, "available", lambda: True)

    # VoiceOver must NOT be reached on the off path.
    def _vo_tripwire(_message: str) -> bool:
        raise AssertionError("VoiceOver was reached when VoiceOver is off — should self-voice")

    monkeypatch.setattr(macos_announce, "announce", _vo_tripwire)
    monkeypatch.setattr(prism_bridge, "_macos_screen_reader_active", lambda: False)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    assert engine.announce("self voice me") is None
    assert voiced == ["self voice me"]


def test_macos_announce_self_voice_skipped_when_backend_unavailable(monkeypatch) -> None:
    """If pyobjc/native TTS is unavailable, the off-path is a harmless no-op (no crash)."""
    monkeypatch.setattr(macos_tts, "available", lambda: False)
    monkeypatch.setattr(macos_tts, "speak_announcement", lambda m: True)
    monkeypatch.setattr(prism_bridge, "_macos_screen_reader_active", lambda: False)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    assert engine.announce("hi") is None


def test_macos_announce_swallows_self_voice_errors(monkeypatch) -> None:
    def _boom(_message: str) -> bool:
        raise RuntimeError("NSSpeechSynthesizer unavailable")

    monkeypatch.setattr(macos_tts, "speak_announcement", _boom)
    monkeypatch.setattr(macos_tts, "available", lambda: True)
    monkeypatch.setattr(prism_bridge, "_macos_screen_reader_active", lambda: False)
    monkeypatch.setattr(prism_bridge.sys, "platform", "darwin")

    engine = _engine_without_backend()
    # A self-voice failure must not crash the app.
    assert engine.announce("hi") is None
