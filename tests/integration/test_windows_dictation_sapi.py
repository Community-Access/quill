"""Windows Dictation against the real Windows recogniser, with no microphone.

Windows speaks a sentence into a WAV file and the recogniser listens to the
file, so this runs on any Windows machine with a speech recogniser installed and
never opens an audio device. It is the one test that proves the SAPI events
really arrive, carry lexical and display forms, and reach the controller.
Skipped where Windows speech recognition is absent (non-Windows, some CI images).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows speech only")


def _speak_to_wav(text: str, path: Path) -> None:
    import win32com.client

    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    audio_format = win32com.client.Dispatch("SAPI.SpAudioFormat")
    audio_format.Type = 18  # SAFT16kHz16BitMono
    stream.Format = audio_format
    stream.Open(str(path), 3)  # SSFMCreateForWrite
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voice.AudioOutputStream = stream
    voice.Speak(text)
    stream.Close()


def test_a_spoken_sentence_arrives_as_words_with_their_punctuation(tmp_path: Path) -> None:
    from quill.platform.windows import sapi_dictation

    if not sapi_dictation.available():
        pytest.skip("no Windows speech recogniser installed")
    import pythoncom

    from quill.core.windows_dictation import compose, parse

    wav = tmp_path / "dictation.wav"
    _speak_to_wav("hello everyone period new paragraph welcome to the editor", wav)

    heard: list[object] = []
    ended: list[str] = []

    class Listener:
        def on_speech_started(self) -> None:
            pass

        def on_phrase(self, phrase: object) -> None:
            heard.append(phrase)

        def on_failure(self, message: str) -> None:
            ended.append(message)

    recognizer = sapi_dictation.SapiDictationRecognizer(Listener())
    recognizer.start_from_wav(str(wav))
    try:
        deadline = time.monotonic() + 30
        while not ended and time.monotonic() < deadline:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.02)
    finally:
        recognizer.stop()

    assert heard, "the recogniser heard nothing"
    text = compose(parse(heard[0]).pieces)  # type: ignore[arg-type]
    assert text.startswith("Hello everyone.\n\nWelcome")
