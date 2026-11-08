"""The mpv engine's live extras: song marks from timed titles, and the cushion.

A fake mpv client stands in for libmpv; a fake clock drives the cushion.
"""

from __future__ import annotations

import json
from typing import Any

from quill.core.radio import cushion
from quill.ui.radio.mpv_live_extras import TITLE_EVERY_TICKS, LiveExtras, seekable_start


class FakeMpv:
    def __init__(self) -> None:
        self.doubles: dict[str, float | None] = {"time-pos": 0.0, "demuxer-cache-time": 0.0}
        self.strings: dict[str, str | None] = {"audio-codec-name": "mp3"}
        self.sets: list[tuple[str, str]] = []
        self.commands: list[tuple[str, ...]] = []
        self.fail_commands = False

    def get_double(self, name: str) -> float | None:
        return self.doubles.get(name)

    def get_str(self, name: str) -> str | None:
        return self.strings.get(name)

    def set_str(self, name: str, value: str) -> int:
        self.sets.append((name, value))
        return 0

    def command(self, *args: str) -> None:
        if self.fail_commands:
            raise OSError("mpv said no")
        self.commands.append(args)

    def buffered(self, start: float, end: float) -> None:
        self.strings["demuxer-cache-state"] = json.dumps({
            "seekable-ranges": [{"start": start, "end": end}]
        })


class _Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


def _extras(mpv: FakeMpv, title: list[str], clock: Any = None) -> LiveExtras:
    return LiveExtras(mpv, title=lambda: title[0], clock=clock or _Clock())


def _ticks(extras: LiveExtras, count: int = TITLE_EVERY_TICKS, *, stalled: bool = False) -> None:
    for _ in range(count):
        extras.on_poll(stalled=stalled, was_stalled=stalled)


def test_seekable_start_reads_mpvs_cache_state() -> None:
    raw = json.dumps({"seekable-ranges": [{"start": 5, "end": 50}, {"start": 80, "end": 90}]})
    assert seekable_start(raw, 85.0) == 80.0
    assert seekable_start(raw, 20.0) == 5.0
    assert seekable_start(raw, None) == 5.0
    assert seekable_start("not json", 1.0) is None
    assert seekable_start(json.dumps({"seekable-ranges": []}), 1.0) is None
    assert seekable_start(None, 1.0) is None


def test_a_title_change_marks_the_playhead() -> None:
    mpv, title = FakeMpv(), ["A - One"]
    extras = _extras(mpv, title)
    mpv.buffered(0.0, 30.0)
    mpv.doubles["time-pos"] = 30.0  # too late to name the audio before it
    _ticks(extras)
    title[0] = "B - Two"
    mpv.doubles["time-pos"] = 200.0
    mpv.buffered(0.0, 200.0)
    _ticks(extras)
    assert [(m.title, m.position) for m in extras.marks.marks] == [
        ("A - One", 30.0),
        ("B - Two", 200.0),
    ]


def test_titles_are_checked_once_a_second_not_every_tick() -> None:
    mpv, title = FakeMpv(), ["A - One"]
    extras = _extras(mpv, title)
    _ticks(extras, TITLE_EVERY_TICKS - 1)
    assert len(extras.marks) == 0
    _ticks(extras, 1)
    assert len(extras.marks) == 1


def test_the_live_edge_reader_marks_the_cache_end() -> None:
    mpv = FakeMpv()
    extras = _extras(mpv, [""])
    mpv.doubles["demuxer-cache-time"] = 500.0
    mpv.buffered(0.0, 500.0)
    assert extras.mark_live_edge("A - One")
    assert extras.marks.marks[0].position == 500.0
    mpv.doubles["demuxer-cache-time"] = None
    assert not extras.mark_live_edge("B - Two")


def test_marks_whose_audio_has_left_the_buffer_are_dropped() -> None:
    mpv, title = FakeMpv(), ["A - One"]
    extras = _extras(mpv, title)
    mpv.buffered(0.0, 50.0)
    mpv.doubles["time-pos"] = 40.0
    _ticks(extras)
    title[0] = "B - Two"
    mpv.doubles["time-pos"] = 100.0
    _ticks(extras)
    title[0] = "C - Three"
    mpv.doubles["time-pos"] = 300.0
    mpv.buffered(150.0, 300.0)
    _ticks(extras)
    assert [m.title for m in extras.marks.marks] == ["B - Two", "C - Three"]


def test_a_load_clears_the_marks_and_writes_the_normal_cushion() -> None:
    mpv = FakeMpv()
    extras = _extras(mpv, [""])
    extras.marks.mark("A - One", 10.0)
    extras.on_load()
    assert len(extras.marks) == 0
    assert mpv.sets[-1] == ("cache-pause-wait", "1.0")


def test_stalls_deepen_the_cushion_and_a_clean_minute_restores_it() -> None:
    mpv, clock = FakeMpv(), _Clock()
    extras = _extras(mpv, [""], clock)
    extras.on_poll(stalled=True, was_stalled=False)
    assert mpv.sets[-1] == ("cache-pause-wait", "3.0")
    extras.on_poll(stalled=False, was_stalled=True)
    extras.on_poll(stalled=True, was_stalled=False)
    assert mpv.sets[-1] == ("cache-pause-wait", "9.0")
    extras.on_poll(stalled=False, was_stalled=True)
    writes = len(mpv.sets)
    clock.now += cushion.CLEAN_SECONDS - 1
    extras.on_poll(stalled=False, was_stalled=False)
    assert len(mpv.sets) == writes  # nothing new to say yet
    clock.now += 1
    extras.on_poll(stalled=False, was_stalled=False)
    assert mpv.sets[-1] == ("cache-pause-wait", "1.0")


def test_seek_and_dump_go_to_mpv_and_failures_are_false() -> None:
    mpv = FakeMpv()
    extras = _extras(mpv, [""])
    assert extras.seek_to(12.5)
    assert extras.dump(10.0, 20.0, "C:/x.mp3")
    assert mpv.commands == [
        ("seek", "12.500", "absolute"),
        ("dump-cache", "10.000", "20.000", "C:/x.mp3"),
    ]
    mpv.fail_commands = True
    assert not extras.seek_to(1.0)
    assert not extras.dump(1.0, 2.0, "C:/y.mp3")
    assert extras.codec() == "mp3"
