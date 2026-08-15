"""Conversion through the real OptiLab engine.

A conversion is a saved file, which is the one place the engine can run without
costing anything: the file is processed once, afterwards, with no live preview to
protect. These tests cover the encode half's argv and the refusals.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.audio import convert
from quill.core.audio.convert import ConversionJob, ConversionSpec, build_convert_command
from quill.core.audio.exact_optilab import ExactOptilab


def _job(spec: ConversionSpec) -> ConversionJob:
    return ConversionJob(source=Path("in.wav"), dest=Path("out.mp3"), spec=spec)


class TestPcmEncodeHalf:
    def test_it_reads_stdin_instead_of_the_source_file(self) -> None:
        argv = build_convert_command(
            "ffmpeg", _job(ConversionSpec(fmt="mp3")), pcm_input=(48000, 2)
        )
        assert argv[argv.index("-i") + 1] == "pipe:0"
        assert "in.wav" not in argv

    def test_the_specs_own_filters_are_not_applied_twice(self) -> None:
        """They ran in the decode half, ahead of the engine. Repeating them here
        would double every DSP setting the listener chose."""
        spec = ConversionSpec(fmt="mp3", filters=("volume=3dB",))
        assert "-af" in build_convert_command("ffmpeg", _job(spec))
        assert "-af" not in build_convert_command("ffmpeg", _job(spec), pcm_input=(48000, 2))

    def test_the_chosen_codec_and_quality_still_apply(self) -> None:
        spec = ConversionSpec(fmt="mp3", bitrate_kbps=256)
        argv = build_convert_command("ffmpeg", _job(spec), pcm_input=(44100, 2))
        assert "libmp3lame" in argv
        assert argv[argv.index("-b:a") + 1] == "256k"


class TestSpec:
    def test_conversion_is_unchanged_by_default(self) -> None:
        assert ConversionSpec().exact_optilab is None

    def test_an_ordinary_command_is_untouched_by_the_new_parameter(self) -> None:
        spec = ConversionSpec(fmt="mp3")
        assert build_convert_command("ffmpeg", _job(spec)) == build_convert_command(
            "ffmpeg", _job(spec), pcm_input=None
        )


class TestRunner:
    def test_a_missing_component_fails_that_job_with_a_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Never a file that claims to be exactly processed and is not: the job
        fails, with a sentence the batch summary can say out loud."""
        from quill.core.audio import exact_optilab

        monkeypatch.setattr(exact_optilab, "available", lambda: False)
        source = tmp_path / "in.wav"
        source.write_bytes(b"not really audio")
        job = ConversionJob(
            source=source,
            dest=tmp_path / "out.mp3",
            spec=ConversionSpec(fmt="mp3", exact_optilab=ExactOptilab(mode="podcast")),
        )
        result = convert._exact_optilab_runner("ffmpeg", job, tmp_path / "tmp.mp3")
        assert not result.ok
        assert "OptiLab component" in result.error

    def test_a_stream_copy_never_takes_the_exact_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A copy is never decoded, so it cannot be processed and stay a copy."""
        taken: list[str] = []
        monkeypatch.setattr(
            convert,
            "_exact_optilab_runner",
            lambda *_a, **_k: taken.append("exact"),
        )
        source = tmp_path / "in.wav"
        source.write_bytes(b"x")
        job = ConversionJob(
            source=source,
            dest=tmp_path / "out.wav",
            spec=ConversionSpec(
                fmt="wav", copy_audio=True, exact_optilab=ExactOptilab(mode="podcast")
            ),
        )
        # The runner will fail on the fake input, which is fine; what matters is
        # that it never reached the exact path.
        convert._default_single_runner("ffmpeg-does-not-exist", job)
        assert taken == []
