"""Tests for the native macOS TTS backend (``quill.platform.macos.tts``, #2).

The branching/off-mac behavior runs on every platform (pyobjc is imported
lazily, so every primitive degrades to ``False`` / ``[]`` / no-op off-mac). The
live ``available()`` / ``list_voices()`` assertions run only on the macOS CI
runner, where the ``[macos]`` extra (pyobjc) is installed and the system ships
at least one voice -- so a regression that breaks the ``NSSpeechSynthesizer``
binding fails on macOS CI, not only at runtime on a user's Mac.
"""

from __future__ import annotations

import sys

import pytest

from quill.platform.macos import tts


def test_speak_announcement_empty_text_is_false():
    assert tts.speak_announcement("") is False


def test_stop_announcement_is_noop_without_a_synth():
    # No speak_announcement() has run, so the singleton is unset; must not raise.
    tts.stop_announcement()


@pytest.mark.skipif(sys.platform == "darwin", reason="off-mac branching assertions")
def test_available_is_false_off_darwin():
    assert tts.available() is False


@pytest.mark.skipif(sys.platform == "darwin", reason="off-mac branching assertions")
def test_list_voices_empty_off_darwin():
    assert tts.list_voices() == []


@pytest.mark.skipif(sys.platform == "darwin", reason="off-mac branching assertions")
def test_speak_announcement_false_off_darwin():
    # AppKit is not importable off-mac, so the synth cannot be built.
    assert tts.speak_announcement("hello") is False


@pytest.mark.skipif(sys.platform != "darwin", reason="NSSpeechSynthesizer is macOS-only")
def test_available_true_on_darwin_with_pyobjc():
    assert tts.available() is True


@pytest.mark.skipif(sys.platform != "darwin", reason="NSSpeechSynthesizer is macOS-only")
def test_list_voices_returns_at_least_one_voice_on_darwin():
    voices = tts.list_voices()
    assert voices, "macOS ships at least one system voice; availableVoices() returned none"
    # Every voice has a non-empty identifier (what `say -v` accepts).
    for v in voices:
        assert v.id
        assert isinstance(v.name, str)
