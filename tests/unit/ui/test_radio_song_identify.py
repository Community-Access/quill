"""Identify This Song from the app's side: every refusal is a sentence, the sample
comes from the playing buffer, and the sample never outlives the lookup.

All fakes: no credential store, no fpcalc, no network, no libmpv.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from quill.apps import radio_preferences_listening as listening
from quill.core.radio import acoustid, chromaprint, song_recognition
from quill.ui.radio import song_identify_commands as identify


class _Engine:
    def __init__(self, *, dumps: bool = True) -> None:
        self.dumps = dumps
        self.dumped: list[tuple[float, str]] = []
        self.timeshift: list[int | None] = []

    def dump_recent_audio(self, seconds: float, target: str) -> bool:
        self.dumped.append((seconds, target))
        if self.dumps:
            Path(target).write_bytes(b"audio")
        return self.dumps

    def configure_timeshift(self, minutes: int | None) -> None:
        self.timeshift.append(minutes)


class _Controller:
    def __init__(self, engine: _Engine | None, *, station: object | None = "a station") -> None:
        self._mpv_engine = engine
        self._station = station

    @property
    def state(self) -> Any:
        return type("S", (), {"station": self._station})()

    def _is_mpv_active(self) -> bool:
        return self._mpv_engine is not None


class _Tasks:
    def submit(self, _name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - mirror the task manager
            on_failure("op", error)
            return
        on_success("op", result)


class _Wx:
    @staticmethod
    def CallAfter(fn: Any, *args: Any) -> None:  # noqa: N802 - wx's name
        fn(*args)


class _Host:
    def __init__(self, controller: _Controller | None) -> None:
        self._radio_controller = controller
        self._task_manager = _Tasks()
        self._wx = _Wx()
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


@pytest.fixture
def ready(monkeypatch: pytest.MonkeyPatch, quill_data_dir: Path) -> dict[str, Any]:
    """A key, an fpcalc, and AcoustID answering -- all fake."""
    seen: dict[str, Any] = {"samples": []}
    monkeypatch.setattr(acoustid, "stored_key", lambda: "KEY")
    monkeypatch.setattr(chromaprint, "find_fpcalc", lambda dirs=None: "fpcalc.exe")

    def _recognise(sample: Path, **kwargs: Any) -> song_recognition.Recognition:
        seen["samples"].append(sample)
        assert sample.exists(), "the sample must exist while it is fingerprinted"
        seen["kwargs"] = kwargs
        return song_recognition.Recognition("Best guess: Song by Artist, 90 percent sure.")

    monkeypatch.setattr(song_recognition, "recognise", _recognise)
    return seen


def test_no_key_says_where_to_put_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acoustid, "stored_key", lambda: "")
    monkeypatch.setattr(chromaprint, "find_fpcalc", lambda dirs=None: None)
    host = _Host(_Controller(_Engine()))
    identify.identify_song(host)
    assert host.said == [acoustid.NO_KEY_SENTENCE]


def test_no_fpcalc_says_so_and_nothing_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acoustid, "stored_key", lambda: "KEY")
    monkeypatch.setattr(chromaprint, "find_fpcalc", lambda dirs=None: None)
    engine = _Engine()
    host = _Host(_Controller(engine))
    identify.identify_song(host)
    assert host.said == [chromaprint.MISSING_SENTENCE]
    assert engine.dumped == [], "no audio is touched before the tools are there"


def test_nothing_playing(ready: dict[str, Any]) -> None:
    host = _Host(_Controller(_Engine(), station=None))
    identify.identify_song(host)
    assert host.said == ["Nothing is playing."]


def test_the_classic_engine_is_told_it_needs_mpv(ready: dict[str, Any]) -> None:
    host = _Host(_Controller(None))
    identify.identify_song(host)
    assert host.said == [song_recognition.NEEDS_MPV]


def test_an_empty_buffer_asks_to_try_again(ready: dict[str, Any]) -> None:
    host = _Host(_Controller(_Engine(dumps=False)))
    identify.identify_song(host)
    assert host.said == [song_recognition.NOT_ENOUGH_AUDIO]
    assert ready["samples"] == []


def test_the_answer_is_spoken_and_the_sample_is_deleted(ready: dict[str, Any]) -> None:
    engine = _Engine()
    host = _Host(_Controller(engine))
    identify.identify_song(host)
    assert host.said == [
        song_recognition.LISTENING,
        "Best guess: Song by Artist, 90 percent sure.",
    ]
    assert engine.dumped[0][0] == song_recognition.SAMPLE_SECONDS
    sample = ready["samples"][0]
    assert not sample.exists() and not sample.parent.exists(), "no sample outlives the lookup"
    assert ready["kwargs"]["key"] == "KEY"


def test_safe_mode_refuses_before_any_audio(ready: dict[str, Any]) -> None:
    engine = _Engine()
    host = _Host(_Controller(engine))
    host._safe_mode = True  # type: ignore[attr-defined]
    identify.identify_song(host)
    assert "Safe Mode" in host.said[0]
    assert engine.dumped == []


def test_a_worker_crash_is_still_a_sentence(
    monkeypatch: pytest.MonkeyPatch, ready: dict[str, Any]
) -> None:
    def _boom(_sample: Path, **_kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(song_recognition, "recognise", _boom)
    host = _Host(_Controller(_Engine()))
    identify.identify_song(host)
    assert host.said[-1] == song_recognition.DID_NOT_FINISH


def test_the_whole_pipeline_with_fake_fpcalc_and_acoustid(
    monkeypatch: pytest.MonkeyPatch, quill_data_dir: Path
) -> None:
    """End to end through the real recognise(), with only the edges faked."""
    monkeypatch.setattr(acoustid, "stored_key", lambda: "KEY")
    monkeypatch.setattr(chromaprint, "find_fpcalc", lambda dirs=None: "fpcalc.exe")

    def _run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert Path(args[-1]).exists()
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"duration": 60, "fingerprint": "AQAD"}), stderr=""
        )

    import quill.stability.safe_subprocess as safe

    monkeypatch.setattr(safe, "run_subprocess_safely", _run)
    answer = {
        "status": "ok",
        "results": [{"score": 0.8, "recordings": [{"title": "Song", "artists": [{"name": "A"}]}]}],
    }
    monkeypatch.setattr(acoustid, "_post", lambda _body: json.dumps(answer))
    host = _Host(_Controller(_Engine()))
    identify.identify_song(host)
    assert host.said[-1] == "Best guess: Song by A, 80 percent sure."


# -- Preferences: the two rows ---------------------------------------------------


class _App:
    def __init__(self, engine: _Engine) -> None:
        from quill.core.radio.history import RadioHistory

        self._radio_history = RadioHistory()
        self._radio_controller = _Controller(engine)


def test_a_new_time_shift_length_reaches_the_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acoustid, "stored_key", lambda: "")
    engine = _Engine()
    app = _App(engine)
    said = listening.apply(app, 4, "")
    assert app._radio_history.timeshift_minutes == 180
    assert engine.timeshift == [180]
    assert "next station" in said


def test_an_unchanged_preferences_dialog_saves_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acoustid, "stored_key", lambda: "")

    def _no_save(_value: str) -> bool:
        raise AssertionError("nothing changed, so nothing is written")

    monkeypatch.setattr(acoustid, "save_key", _no_save)
    app = _App(_Engine())
    from quill.core.radio import timeshift

    index = timeshift.choice_index(app._radio_history.timeshift_minutes)
    assert listening.apply(app, index, "") == ""


def test_a_pasted_key_goes_to_the_credential_store(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[str] = []
    monkeypatch.setattr(acoustid, "stored_key", lambda: "")
    monkeypatch.setattr(acoustid, "save_key", lambda value: saved.append(value) or True)
    app = _App(_Engine())
    said = listening.apply(app, 2, "  abc123  ")
    assert saved == ["abc123"]
    assert said == "AcoustID key saved."
