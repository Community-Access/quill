"""Live dictation's engine half and the worker loop, with fakes only.

Nemotron itself was measured on real speech on 2026-10-05 (the design note
records it); here a scripted stand-in says what Nemotron said, so the rules --
a mark that belongs to the phrase before, the quiet fed between phrases,
finishing the last phrase, keeping up -- are held still.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.windows_dictation import local_recognizer
from quill.core.windows_dictation.keep_up import IdleUnloader, KeepUpWatchdog
from quill.core.windows_dictation.streaming import TAIL_SECONDS, NemotronLive, split_previous_mark

np = pytest.importorskip("numpy")


class _Stream:
    def __init__(self) -> None:
        self.fed = 0
        self.options: dict[str, str] = {}

    def accept_waveform(self, _rate: int, samples: Any) -> None:
        self.fed += len(samples)

    def set_option(self, name: str, value: str) -> None:
        self.options[name] = value


class _Online:
    """Answers with the full text so far, by how much audio has been fed."""

    def __init__(self, script: list[tuple[int, str]]) -> None:
        self.script = script
        self.streams: list[_Stream] = []

    def create_stream(self) -> _Stream:
        self.streams.append(_Stream())
        return self.streams[-1]

    def is_ready(self, _stream: _Stream) -> bool:
        return False

    def decode_stream(self, _stream: _Stream) -> None:
        pass

    def get_result(self, stream: _Stream) -> str:
        text = ""
        for samples, full in self.script:
            if stream.fed >= samples:
                text = full
        return text


def test_a_leading_mark_belongs_to_the_phrase_before() -> None:
    assert split_previous_mark("?  The meeting moved") == ("?", "The meeting moved")
    assert split_previous_mark(" and then") == ("", "and then")
    assert split_previous_mark("!") == ("!", "")


def test_nemotron_live_previews_then_gives_the_next_phrases_mark() -> None:
    online = _Online([
        (8_000, "Can you send"),
        (16_000, "Can you send it"),
        (40_000, "Can you send it?  The meeting moved"),
    ])
    live = NemotronLive(online, "en")
    assert online.streams[0].options == {"language": "en"}
    live.begin(np.zeros(4_000, np.float32))
    assert live.feed(np.zeros(4_000, np.float32), speaking=True) == "Can you send"
    assert live.end() == ("", "Can you send it?")  # closed as a question at the pause
    live.begin(np.zeros(0, np.float32))
    for _ in range(5):
        live.feed(np.zeros(4_000, np.float32), speaking=True)
    mark, text = live.end()
    assert (mark, text) == ("?", "The meeting moved.")


def test_only_a_little_quiet_is_fed_between_phrases() -> None:
    online = _Online([])
    live = NemotronLive(online, "en")
    live.begin(np.zeros(0, np.float32))
    for _ in range(20):  # two seconds of quiet after speech
        live.feed(np.zeros(1_600, np.float32), speaking=False)
    assert online.streams[0].fed <= int(TAIL_SECONDS * 16_000) + 1_600
    live.end()
    assert online.streams[0].fed <= int(TAIL_SECONDS * 16_000) + 1_600


def test_escape_starts_a_fresh_stream() -> None:
    online = _Online([])
    live = NemotronLive(online, "es")
    live.clear()
    assert len(online.streams) == 2 and online.streams[1].options["language"] == "es"


# -- the worker -------------------------------------------------------------- #


class _Segment:
    start = -1

    def __init__(self, samples: Any) -> None:
        self.samples = samples


class _Vad:
    """Speech on every block; a phrase ends after *blocks* blocks."""

    def __init__(self, blocks: int = 2) -> None:
        self.blocks = blocks
        self.seen = 0
        self.queue: list[_Segment] = []
        self.flushed = False

    def accept_waveform(self, chunk: Any) -> None:
        self.seen += 1
        if self.seen % self.blocks == 0:
            self.queue.append(_Segment(np.zeros(self.blocks * 512, np.float32)))

    def is_speech_detected(self) -> bool:
        return True

    def empty(self) -> bool:
        return not self.queue

    @property
    def front(self) -> _Segment:
        return self.queue[0]

    def pop(self) -> None:
        self.queue.pop(0)

    def flush(self) -> None:
        self.flushed = True
        self.queue.append(_Segment(np.zeros(512, np.float32)))


class _Listener:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def on_speech_started(self) -> None:
        self.events.append(("speech", None))

    def on_partial(self, text: str) -> None:
        self.events.append(("partial", text))

    def on_phrase(self, phrase: Any) -> None:
        self.events.append(("phrase", (phrase.previous_mark, phrase.text)))

    def on_failure(self, message: str) -> None:
        self.events.append(("failure", message))

    def on_finished(self) -> None:
        self.events.append(("finished", None))

    def on_engine_notice(self, message: str) -> None:
        self.events.append(("notice", message))


class _FakeLive:
    def __init__(self) -> None:
        self.fed = 0

    def begin(self, lead_in: Any) -> None:
        self.fed = 0

    def feed(self, samples: Any, *, speaking: bool) -> str:
        self.fed += 1
        return "hello" if self.fed == 1 else "hello there"

    def end(self) -> tuple[str, str]:
        return "?", "Hello there."

    def clear(self) -> None:
        pass

    def close(self) -> None:
        pass


def _recogniser(listener: _Listener) -> Any:
    engine = local_recognizer.LocalDictationRecognizer(
        listener, "moonshine", post=lambda function, *args: function(*args)
    )
    engine._running.set()
    return engine


def test_a_live_engine_previews_each_change_once_then_writes_the_phrase() -> None:
    listener = _Listener()
    engine = _recogniser(listener)
    engine._live = _FakeLive()
    for _ in range(4):
        engine._audio.put(np.zeros(512, np.float32))
    engine._audio.put(None)
    engine._work(_Vad(blocks=3))
    kinds = [kind for kind, _ in listener.events]
    assert kinds.count("speech") == 1
    assert ("partial", "hello") in listener.events
    assert [value for kind, value in listener.events if kind == "partial"] == [
        "hello",
        "hello there",
    ]
    assert ("phrase", ("?", "Hello there.")) in listener.events


def test_finish_writes_the_last_phrase_then_says_finished(monkeypatch) -> None:
    monkeypatch.setattr(local_recognizer, "transcribe", lambda *_a, **_k: "Last words.")
    listener = _Listener()
    engine = _recogniser(listener)
    vad = _Vad(blocks=100)
    engine._audio.put(np.zeros(512, np.float32))
    engine.finish()
    engine._work(vad)
    assert vad.flushed
    assert listener.events[-2:] == [("phrase", ("", "Last words.")), ("finished", None)]


def test_a_downloaded_model_that_falls_behind_gives_way_once(monkeypatch) -> None:
    loaded: list[str] = []
    monkeypatch.setattr(
        local_recognizer, "_load", lambda engine, _language="en": loaded.append(engine)
    )
    listener = _Listener()
    engine = _recogniser(listener)
    engine._engine = "nemotron"
    engine._watchdog = KeepUpWatchdog(behind_seconds=0.05)
    for _ in range(5):
        engine._audio.put(np.zeros(512, np.float32))
    engine._keep_up()
    assert engine._engine == "moonshine" and loaded == ["moonshine"]
    assert engine._audio.qsize() == 0  # the backlog that made it late is dropped
    assert listener.events[-1][0] == "notice" and "faster" in listener.events[-1][1]
    engine._keep_up()  # once only
    assert [kind for kind, _ in listener.events].count("notice") == 1


def test_slow_phrases_count_as_falling_behind() -> None:
    watchdog = KeepUpWatchdog()
    watchdog.note_phrase(3.0, 1.0)
    assert not watchdog.falling_behind(0.0)
    watchdog.note_phrase(3.0, 1.0)
    assert watchdog.falling_behind(0.0)
    watchdog.note_phrase(0.1, 1.0)
    assert not watchdog.falling_behind(0.0)


def test_models_unload_only_when_no_session_is_running() -> None:
    import threading

    unloaded = threading.Event()
    unloader = IdleUnloader(unloaded.set, minutes=0.0005)
    unloader.busy()
    unloader.busy()
    unloader.idle()
    assert not unloaded.wait(0.1)  # one session is still running
    unloader.idle()
    assert unloaded.wait(2.0)


def test_a_new_session_cancels_a_pending_unload() -> None:
    import threading

    unloaded = threading.Event()
    unloader = IdleUnloader(unloaded.set, minutes=0.002)
    unloader.busy()
    unloader.idle()
    unloader.busy()
    assert not unloaded.wait(0.3)
