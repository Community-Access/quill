"""Listening through the real OptiLab engine: the relay's three-process form.

This is the *only* way live playback can use the engine, and it is opt-in
because of what it costs (see the module docstring in
``quill/core/audio/exact_optilab.py`` and the user guide). What these tests pin
is the thing that would be silently wrong if it broke: the adaptation and the
real engine must never both process the same audio.
"""

from __future__ import annotations

from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.audio_enhance import build_relay_pcm_commands


def _commands(**kwargs: object) -> tuple[list[str], list[str], list[str]]:
    defaults: dict[str, object] = {
        "exact": ExactOptilab(mode="stream", input_db=1.5, auto_adapt=40),
        "bass_db": 0.0,
        "mid_db": 0.0,
        "treble_db": 0.0,
        "compressor_enabled": False,
    }
    defaults.update(kwargs)
    return build_relay_pcm_commands(
        "ffmpeg",
        "http://example.invalid/stream",
        "quill-optilab",
        **defaults,  # type: ignore[arg-type]
    )


class TestNeverBothEngines:
    def test_the_ffmpeg_optilab_chain_is_absent_from_the_decode_step(self) -> None:
        decode, _process, _encode = _commands(compressor_enabled=True)
        graph = decode[decode.index("-af") + 1] if "-af" in decode else ""
        # The chain's own signatures: if any of these appear, the stream is
        # being polished twice -- once in imitation and once for real.
        for fingerprint in ("speechnorm", "dynaudnorm=f=200", "alimiter"):
            assert fingerprint not in graph

    def test_everything_that_is_not_polish_still_applies(self) -> None:
        decode, _process, _encode = _commands(bass_db=6.0, compressor_enabled=True)
        graph = decode[decode.index("-af") + 1]
        assert "equalizer=f=100" in graph  # the listener's EQ
        assert "acompressor" in graph  # Even Out Volume


class TestPipeline:
    def test_the_decode_step_emits_what_the_engine_reads(self) -> None:
        decode, _process, _encode = _commands()
        assert decode[-1] == "pipe:1"
        assert "f32le" in decode

    def test_the_engine_is_told_the_mode_and_the_listeners_settings(self) -> None:
        _decode, process, _encode = _commands()
        assert process[process.index("--mode") + 1] == "stream"
        assert process[process.index("--input-db") + 1] == "1.50"
        assert process[process.index("--adapt") + 1] == "40"

    def test_the_encode_step_produces_the_mp3_the_relay_serves(self) -> None:
        _decode, _process, encode = _commands()
        assert encode[encode.index("-i") + 1] == "pipe:0"
        assert "libmp3lame" in encode
        assert encode[-1] == "pipe:1"

    def test_a_live_stream_keeps_its_reconnect_handling(self) -> None:
        decode, _process, _encode = _commands()
        # A network hiccup must be ridden out here exactly as on the ordinary
        # relay: the extra processing must not cost the reconnect behaviour.
        assert "-reconnect" in decode
