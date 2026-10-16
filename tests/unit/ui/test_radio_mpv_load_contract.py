"""What ``MpvRadioEngine.load`` must reset before every station.

mpv's client is one long-lived object for the whole session, and several of the
things Quill Radio sets on it are **options**, not properties of the file that
happens to be loaded. An option nobody clears leaks from one station into the
next, and every one of those leaks is silent.

This is the test that was missing when the worst of them shipped: showing the
picture for a YouTube video sets ``audio-files`` to that video's separate audio
stream (YouTube serves picture and sound apart), and nothing ever cleared it --
so the next video played with the *previous* video's sound. "It is like it is
caching whatever the last video was that worked" (2026-08-23), which is exactly
what it was doing.

No wx and no libmpv: ``load`` is called against a stub client, which is all it
needs to state its contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.radio.timeshift import TimeshiftSession
from quill.ui.radio.mpv_radio_engine import MpvRadioEngine


class _Client:
    def __init__(self) -> None:
        self.props: dict[str, str] = {}
        self.commands: list[tuple[Any, ...]] = []

        self.doubles: dict[str, float] = {}

    def set_str(self, name: str, value: str) -> int:
        self.props[name] = value
        return 0

    def command(self, *args: Any) -> None:
        self.commands.append(args)

    def get_double(self, name: str) -> float | None:
        return self.doubles.get(name)

    def close(self) -> None:
        self.props["closed"] = "yes"


class _Timer:
    def __init__(self) -> None:
        self.started = 0

    def Start(self, _ms: int) -> None:  # noqa: N802 - wx's own casing
        self.started += 1


def _engine(root: Path | None = None) -> MpvRadioEngine:
    engine = MpvRadioEngine.__new__(MpvRadioEngine)
    engine._mpv = _Client()  # type: ignore[attr-defined]
    engine._timer = _Timer()  # type: ignore[attr-defined]
    engine._volume = 70  # type: ignore[attr-defined]
    engine._loaded = False  # type: ignore[attr-defined]
    engine._timeshift = TimeshiftSession(  # type: ignore[attr-defined]
        engine._mpv.set_str,  # type: ignore[attr-defined]
        root=root or Path("unused-timeshift-root"),
    )
    return engine


def test_a_load_clears_the_external_audio_track() -> None:
    """The bug: a second video played the first one's sound.

    ``audio-files`` is client-wide, so the video whose picture was last shown
    kept supplying the audio for everything loaded afterwards -- and when
    YouTube's addresses expired a few hours later it would have supplied
    nothing at all.
    """
    engine = _engine()
    engine._mpv.set_str("audio-files", "https://previous-video/audio")  # type: ignore[attr-defined]

    assert engine.load("https://next-video/stream") is True

    assert engine._mpv.props["audio-files"] == ""  # type: ignore[attr-defined]


def test_a_load_still_resets_the_other_leaky_options() -> None:
    """Speed and referrer were already cleared per load, for the same reason."""
    engine = _engine()
    engine.load("https://stream/one")

    props = engine._mpv.props  # type: ignore[attr-defined]
    assert props["speed"] == "1.00"
    assert props["pause"] == "no"
    assert props["volume"] == "70"
    assert "referrer" in props


def test_a_load_hands_the_url_to_mpv_and_starts_polling() -> None:
    engine = _engine()
    engine.load("https://stream/one")

    assert engine._mpv.commands == [("loadfile", "https://stream/one", "replace")]  # type: ignore[attr-defined]
    assert engine._timer.started == 1  # type: ignore[attr-defined]
    assert engine._bounded is False  # every load starts live-shaped


# -- the time-shift buffer on disk (xradio2.md 4.3) ---------------------------


def test_a_load_makes_the_time_shift_folder_before_mpv_writes_into_it(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    engine.configure_timeshift(60)
    engine.load("https://stream/one")

    folder = Path(engine._mpv.props["cache-dir"])  # type: ignore[attr-defined]
    assert folder.is_dir() and folder.parent == tmp_path
    assert engine._mpv.props["cache-on-disk"] == "yes"  # type: ignore[attr-defined]


def test_terminate_removes_the_time_shift_folder(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    engine.configure_timeshift(60)
    engine.load("https://stream/one")
    folder = Path(engine._mpv.props["cache-dir"])  # type: ignore[attr-defined]
    (folder / "mpv-cache").write_bytes(b"x" * 64)

    engine.terminate()

    assert not folder.exists(), "the buffer never outlives the app"


# -- the recognition sample comes from the playing buffer ----------------------


def test_the_sample_is_dumped_from_the_cache_not_a_new_connection() -> None:
    engine = _engine()
    engine._loaded = True  # type: ignore[attr-defined]
    engine._mpv.doubles["time-pos"] = 500.0  # type: ignore[attr-defined]

    assert engine.dump_recent_audio(60, "sample.bin") is True

    assert engine._mpv.commands == [("dump-cache", "440.000", "500.000", "sample.bin")]  # type: ignore[attr-defined]


def test_no_sample_when_nothing_is_loaded() -> None:
    engine = _engine()
    assert engine.dump_recent_audio(60, "sample.bin") is False
    assert engine._mpv.commands == []  # type: ignore[attr-defined]
