"""FUX-11: Converter's preview measures its own encode and estimates the queue."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from quill.core.audio import assemble
from quill.core.audio.convert import ConversionSpec
from quill.core.audio.preview_estimate import estimable, queue_estimate


def _spec(**over: Any) -> ConversionSpec:
    return replace(ConversionSpec(fmt="mp3"), **over)


def test_the_estimate_scales_the_preview_to_the_queue() -> None:
    text = queue_estimate(
        source_name="a.wav",
        spec=_spec(),
        clip_seconds=15,
        encode_seconds=3,
        encoded_bytes=240_000,
        durations=[600, 300],
    )
    assert "converting the 2 files in the queue should take" in text
    assert "about 3 minutes" in text
    assert "be about 13.7 MB" in text
    assert "This sample checks 15 seconds of a.wav only" in text


def test_no_estimate_where_the_preview_is_a_poor_measure() -> None:
    assert estimable(_spec()) == ""
    assert "video" in estimable(_spec(fmt="mp4"))
    assert "copies" in estimable(_spec(copy_audio=True))
    assert "part of each file" in estimable(_spec(start_s=10.0))
    text = queue_estimate(
        source_name="a.wav",
        spec=_spec(copy_audio=True),
        clip_seconds=15,
        encode_seconds=1,
        encoded_bytes=1,
        durations=[60],
    )
    assert "there is no estimate" in text


def test_render_preview_reports_the_encode(tmp_path: Path) -> None:
    runs: list[list[str]] = []

    def run(argv: list[str]) -> object:
        runs.append(argv)
        Path(argv[-1]).write_bytes(b"x" * 1234)
        return type("Done", (), {"returncode": 0, "stderr": ""})()

    heard: list[tuple[float, int]] = []
    assemble.render_preview(
        "ffmpeg",
        tmp_path / "in.wav",
        _spec(),
        tmp_path / "out.wav",
        original=False,
        run=run,
        duration_s=120.0,
        measured=lambda seconds, size: heard.append((seconds, size)),
    )
    assert len(runs) == 2  # the encode, then the decode for playback
    assert len(heard) == 1 and heard[0][1] == 1234 and heard[0][0] >= 0


def test_the_converter_probes_the_queue_for_its_estimate(monkeypatch: Any, tmp_path: Path) -> None:
    from quill.apps.converter_lifecycle import ConverterLifecycleMixin
    from quill.core.audio import media_probe

    monkeypatch.setattr(media_probe, "probe", lambda path: type("I", (), {"duration_s": 300.0})())
    text = ConverterLifecycleMixin._preview_estimate(
        tmp_path / "a.wav", _spec(), [tmp_path / "a.wav", tmp_path / "b.wav"], [(1.5, 120_000)]
    )
    assert "converting the 2 files in the queue should take" in text
    assert ConverterLifecycleMixin._preview_estimate(tmp_path / "a.wav", _spec(), [], []) == ""
