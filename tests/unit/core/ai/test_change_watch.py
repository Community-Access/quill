"""Tell me when this changes: local first, rare asks, hard stops."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from quill.core.ai import change_watch as cw


def _png(colour: str) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), colour).save(out, format="PNG")
    return out.getvalue()


RED, BLUE = _png("red"), _png("blue")


class Rig:
    """A fake clock, picture source, OCR and AI."""

    def __init__(self, answer: str = "A dialog opened.") -> None:
        self.now = 0.0
        self.picture = RED
        self.words = ""
        self.answer = answer
        self.asked: list[str] = []
        self.counted = 0
        self.grabs = 0

    def grab(self) -> bytes:
        self.grabs += 1
        return self.picture

    def ask(self, before: bytes, after: bytes, prompt: str) -> str:
        self.asked.append(prompt)
        return self.answer

    def count(self) -> None:
        self.counted += 1

    def watch(self, **kw: object) -> cw.ChangeWatch:
        return cw.ChangeWatch(
            grab=self.grab,
            ask=self.ask,
            ocr=lambda _b: self.words,
            count_ask=self.count,
            clock=lambda: self.now,
            safe_mode=False,
            subject="the video",
            **kw,  # type: ignore[arg-type]
        )

    def flip(self) -> None:
        self.picture = BLUE if self.picture == RED else RED


def test_pixel_difference() -> None:
    assert cw.pixel_difference(RED, RED) == 0.0
    assert cw.pixel_difference(RED, BLUE) == 1.0


def test_start_and_stop_are_spoken() -> None:
    rig = Rig()
    watch = rig.watch()
    assert watch.start() == "Watching the video for changes."
    assert watch.stop() == "Stopped watching the video."
    assert watch.stop() == "Nothing was being watched."


def test_refused_in_safe_mode() -> None:
    rig = Rig()
    watch = cw.ChangeWatch(grab=rig.grab, ask=rig.ask, safe_mode=True)
    with pytest.raises(cw.WatchRefused, match="Safe Mode"):
        watch.start()


def test_safe_mode_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    rig = Rig()
    with pytest.raises(cw.WatchRefused):
        cw.ChangeWatch(grab=rig.grab, ask=rig.ask).start()


def test_nothing_happens_without_a_change() -> None:
    rig = Rig()
    watch = rig.watch()
    watch.start()
    assert watch.tick() is None  # the first look is the baseline
    assert watch.tick() is None
    assert rig.asked == []


def test_changed_words_are_reported_locally_without_asking() -> None:
    rig = Rig()
    watch = rig.watch()
    watch.start()
    rig.words = "Recording"
    watch.tick()
    rig.flip()
    rig.words = "Paused"
    report = watch.tick()
    assert report == cw.WatchReport("The words changed to: Paused", "local", 0)
    assert rig.asked == [] and rig.counted == 0


def test_model_asked_at_most_once_a_minute_and_counted() -> None:
    rig = Rig()
    watch = rig.watch()
    watch.start()
    watch.tick()
    rig.flip()
    report = watch.tick()
    assert report is not None and report.sentence == "A dialog opened." and report.source == "model"
    assert rig.counted == 1
    rig.flip()
    rig.now = 30
    assert watch.tick() is None  # changed, but not a minute yet
    rig.now = 61
    assert watch.tick() is not None
    assert len(rig.asked) == rig.counted == 2


def test_no_change_answer_says_nothing() -> None:
    rig = Rig(answer="No change.")
    watch = rig.watch()
    watch.start()
    watch.tick()
    rig.flip()
    assert watch.tick() is None
    assert rig.counted == 1


def test_only_the_first_sentence_is_spoken() -> None:
    rig = Rig(answer="A chart appeared. It shows sales by month and more")
    watch = rig.watch()
    watch.start()
    watch.tick()
    rig.flip()
    report = watch.tick()
    assert report is not None and report.sentence == "A chart appeared."


def test_thirty_asks_then_the_watch_stops_and_says_so() -> None:
    rig = Rig()
    watch = rig.watch()
    watch.start()
    watch.tick()
    last = None
    for minute in range(cw.MAX_ASKS):
        rig.now = minute * 61.0
        rig.flip()
        last = watch.tick()
    assert rig.counted == cw.MAX_ASKS
    assert not watch.watching
    assert last is not None and "30 questions" in last.sentence
    rig.now += 100
    rig.flip()
    assert watch.tick() is None
    assert rig.counted == cw.MAX_ASKS


def test_nothing_after_the_window_closes() -> None:
    rig = Rig()
    watch = rig.watch()
    watch.start()
    watch.tick()
    watch.window_closed()
    grabs = rig.grabs
    rig.flip()
    assert watch.tick() is None
    assert rig.grabs == grabs and rig.asked == []
    with pytest.raises(cw.WatchRefused):
        watch.start()


def test_closed_while_answering_says_nothing() -> None:
    rig = Rig()
    watch = rig.watch()

    def ask(before: bytes, after: bytes, prompt: str) -> str:
        watch.window_closed()
        return "Something changed."

    watch._ask = ask
    watch.start()
    watch.tick()
    rig.flip()
    assert watch.tick() is None


def test_an_ai_failure_ends_the_watch_with_a_sentence() -> None:
    rig = Rig()
    watch = rig.watch()

    def ask(before: bytes, after: bytes, prompt: str) -> str:
        raise RuntimeError("limit reached")

    watch._ask = ask
    watch.start()
    watch.tick()
    rig.flip()
    report = watch.tick()
    assert report is not None and report.source == "watch"
    assert "limit reached" in report.sentence
    assert not watch.watching
