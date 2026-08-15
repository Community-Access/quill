"""The exact-OptiLab pass: argv shape, refusals, and the never-lose-a-file rule.

The engine itself is OptiLab Core by Lanes Audio / dgl1984, vendored under
quill/native/optilab. These tests are about QUILL's half: the three-process
pipeline, the format contract between them, and what happens when the optional
component is not there -- which is the case on every machine that has not built
it, including CI, so it is the case that must not break anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.audio import exact_optilab
from quill.core.audio.exact_optilab import ExactOptilab, ExactProcessingError


class TestSpec:
    def test_off_is_not_active(self) -> None:
        assert not ExactOptilab().active
        assert not ExactOptilab(mode="off").active

    @pytest.mark.parametrize("mode", ["podcast", "stream", "limiter"])
    def test_a_real_mode_is_active(self, mode: str) -> None:
        assert ExactOptilab(mode=mode).active

    def test_nonsense_is_not_active(self) -> None:
        assert not ExactOptilab(mode="banana").active


class TestDecodeCommand:
    def test_it_emits_the_pcm_format_the_adapter_reads(self) -> None:
        argv = exact_optilab.build_decode_command(
            "ffmpeg", Path("show.mp3"), sample_rate=44_100, channels=2
        )
        assert argv[0] == "ffmpeg"
        # The wire format is fixed and unnegotiated: the adapter has no header
        # to parse, so a mismatch here would be silence, not an error.
        assert "-f" in argv and "f32le" in argv
        assert argv[argv.index("-ar") + 1] == "44100"
        assert argv[argv.index("-ac") + 1] == "2"
        assert argv[-1] == "pipe:1"

    def test_a_filter_graph_runs_before_the_engine(self) -> None:
        argv = exact_optilab.build_decode_command(
            "ffmpeg", Path("a.wav"), sample_rate=48_000, channels=2, filter_graph="equalizer=f=100"
        )
        # Everything else first, broadcast polish last -- the same order the
        # live chain uses.
        assert argv[argv.index("-af") + 1] == "equalizer=f=100"
        assert argv.index("-af") < argv.index("-f")

    def test_no_filter_means_no_af_at_all(self) -> None:
        argv = exact_optilab.build_decode_command(
            "ffmpeg", Path("a.wav"), sample_rate=48_000, channels=2
        )
        assert "-af" not in argv

    def test_more_than_stereo_is_downmixed_not_mishandled(self) -> None:
        argv = exact_optilab.build_decode_command(
            "ffmpeg", Path("film.mkv"), sample_rate=48_000, channels=6
        )
        # OptiLab Core is mono or stereo; ffmpeg does the downmix visibly rather
        # than the engine being handed six channels labelled as two.
        assert argv[argv.index("-ac") + 1] == "2"

    def test_an_impossible_rate_falls_back_rather_than_failing(self) -> None:
        argv = exact_optilab.build_decode_command(
            "ffmpeg", Path("a.wav"), sample_rate=0, channels=2
        )
        assert argv[argv.index("-ar") + 1] == "48000"


class TestEncodeCommand:
    def test_it_reads_pcm_on_stdin_and_writes_the_target(self) -> None:
        argv = exact_optilab.build_encode_command(
            "ffmpeg",
            Path("out.mp3"),
            sample_rate=48_000,
            channels=2,
            encode_args=["-c:a", "libmp3lame", "-b:a", "192k"],
        )
        assert argv[argv.index("-i") + 1] == "pipe:0"
        assert argv[-1] == "out.mp3"
        assert "libmp3lame" in argv

    def test_input_args_match_the_decode_side(self) -> None:
        decode = exact_optilab.build_decode_command(
            "ffmpeg", Path("a.wav"), sample_rate=44_100, channels=1
        )
        pcm_in = exact_optilab.build_pcm_input_args(44_100, 1)
        # The two halves have to agree about the format, the rate and the
        # channel count or the audio arrives as noise.
        for flag in ("-f", "-ar", "-ac"):
            assert decode[decode.index(flag) + 1] == pcm_in[pcm_in.index(flag) + 1]


class TestProbeShape:
    def test_it_reads_ffprobes_two_lines(self) -> None:
        assert exact_optilab.parse_probe_shape("44100\n2\n") == (44_100, 2)

    def test_nothing_useful_falls_back_to_48k_stereo(self) -> None:
        assert exact_optilab.parse_probe_shape("") == (48_000, 2)
        assert exact_optilab.parse_probe_shape("not a number\nnope\n") == (48_000, 2)


class TestRefusals:
    def test_an_inactive_mode_is_refused_before_anything_is_spawned(self, tmp_path: Path) -> None:
        with pytest.raises(ExactProcessingError):
            exact_optilab.process_file(
                tmp_path / "in.mp3", tmp_path / "out.mp3", ExactOptilab(), encode_args=[]
            )

    def test_a_missing_adapter_says_so_in_words_a_listener_can_act_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUILL_OPTILAB_ADAPTER", str(tmp_path / "not-here.exe"))
        monkeypatch.setattr(exact_optilab.optilab_adapter, "find_adapter", lambda: None)
        assert not exact_optilab.available()
        with pytest.raises(ExactProcessingError) as caught:
            exact_optilab.process_file(
                tmp_path / "in.mp3",
                tmp_path / "out.mp3",
                ExactOptilab(mode="podcast"),
                encode_args=[],
            )
        # Never a bare "failed": the reason names the missing component and says
        # the ordinary sound enhancements are unaffected.
        assert "OptiLab component" in str(caught.value)


class TestProcessInPlace:
    def test_a_failed_pass_leaves_the_original_exactly_as_it_was(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The rule this whole feature must never break: a post-process cannot
        cost somebody the recording it was meant to improve."""
        recording = tmp_path / "show.mp3"
        recording.write_bytes(b"the original recording")

        def explode(*_args: object, **_kwargs: object) -> None:
            raise ExactProcessingError("the engine fell over")

        monkeypatch.setattr(exact_optilab, "process_file", explode)
        with pytest.raises(ExactProcessingError):
            exact_optilab.process_in_place(
                recording, ExactOptilab(mode="podcast"), encode_args=["-c:a", "libmp3lame"]
            )
        assert recording.read_bytes() == b"the original recording"
        # ... and no temp litter beside it.
        assert list(tmp_path.iterdir()) == [recording]

    def test_an_empty_result_is_treated_as_a_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recording = tmp_path / "show.mp3"
        recording.write_bytes(b"original")

        def write_nothing(_src: Path, dest: Path, *_a: object, **_k: object) -> None:
            Path(dest).write_bytes(b"")

        monkeypatch.setattr(exact_optilab, "process_file", write_nothing)
        with pytest.raises(ExactProcessingError):
            exact_optilab.process_in_place(recording, ExactOptilab(mode="stream"), encode_args=[])
        assert recording.read_bytes() == b"original"

    def test_a_good_pass_replaces_the_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recording = tmp_path / "show.mp3"
        recording.write_bytes(b"original")

        def write_processed(_src: Path, dest: Path, *_a: object, **_k: object) -> None:
            Path(dest).write_bytes(b"processed")

        monkeypatch.setattr(exact_optilab, "process_file", write_processed)
        exact_optilab.process_in_place(recording, ExactOptilab(mode="podcast"), encode_args=[])
        assert recording.read_bytes() == b"processed"
        assert list(tmp_path.iterdir()) == [recording]


@pytest.mark.skipif(
    not exact_optilab.available(), reason="the OptiLab adapter has not been built here"
)
class TestEndToEnd:
    """Only where the component exists -- which is the point of building it into
    the source tree rather than only into a release."""

    def test_a_real_pass_produces_a_playable_file(self, tmp_path: Path) -> None:
        from quill.core.speech.ffmpeg import find_ffmpeg

        ffmpeg = find_ffmpeg()
        if ffmpeg is None:
            pytest.skip("ffmpeg is not installed here")
        source = tmp_path / "tone.wav"
        import subprocess

        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                "-y",
                str(source),
            ],
            check=True,
        )
        dest = tmp_path / "processed.wav"
        exact_optilab.process_file(
            source,
            dest,
            ExactOptilab(mode="podcast"),
            encode_args=["-c:a", "pcm_s16le"],
        )
        assert dest.is_file() and dest.stat().st_size > 1000
