"""Sound Enhancements: optional EQ presets + a compressor for radio
playback.

Ported from upstream ``quill.core.audio_enhance``, but trimmed down
hard: upstream builds this filter graph for an ffmpeg subprocess whose
stdout is handed to a wx.media/mpv client through a localhost HTTP
relay (:class:`EnhanceRelay`), because neither of upstream's engines
has a filter graph of its own. This mac build is mpv-only, and libmpv
*does* have a native filter graph -- the ``af`` property accepts the
exact same ffmpeg-style filter-chain syntax this module builds. So the
relay, the subprocess plumbing, and everything HTTP is gone entirely:
:func:`build_filter_graph` produces a plain string, the player
controller (a later task) hands it straight to ``mpv_set_property(...,
"af", ...)``, and that's the whole integration. Only what a pure
filter-graph string builder needs is kept: :data:`EQ_PRESETS`,
:func:`clamp_eq_gain`, :func:`build_filter_graph`, and
:class:`EnhanceError` (kept for a later task's use if applying the
graph at the mpv layer needs a coded, user-facing failure -- nothing
in this module itself can currently raise it, since building a string
cannot fail).

Deliberately not ported: :func:`is_enhancement_active` (a caller can
just check ``build_filter_graph(...) != ""``), :func:`build_relay_command`,
:func:`probe_source_duration_ms`, :class:`EnhanceRelay`, and the
``_RelayHTTPServer``/``_RelayHTTPHandler`` HTTP plumbing -- all
relay-only and meaningless once mpv applies filters natively.

Pure and unit-tested: no wx, no IO, no subprocess, no threading.

Threading contract: pure functions and a plain dict/tuple constant;
safe to call from any thread.

macOS notes: none -- fully platform-neutral. The resulting string is
consumed by ``quill_radio_mac.ui.mpv_engine`` (a later task) via
libmpv's ``af`` property, which is available identically on every
platform mpv itself supports.
"""

from __future__ import annotations

from quill_radio_mac.core.error_codes import CodedError

#: (bass gain, mid gain, treble gain) in dB, centered at 100 Hz / 1 kHz / 8 kHz.
#: Quick-select shortcuts for the three adjustable band sliders below --
#: picking one just sets the three gains to these values; the bands stay
#: freely adjustable afterward (a preset is a starting point, not a locked
#: mode).
EQ_PRESETS: dict[str, tuple[float, float, float]] = {
    "Flat": (0.0, 0.0, 0.0),
    "Bass Boost": (7.0, 0.0, 1.0),
    "Voice Clarity": (-3.0, 4.0, 2.0),
    "Podcast": (-4.0, 3.0, 0.0),
    # Compensates small laptop/phone-dock speakers that physically cannot
    # reproduce lows: lift the bass they starve, brighten slightly.
    "Small Speakers": (6.0, 0.0, 2.0),
    # Softer top end for late-night listening at low volume (pairs well
    # with Even Out Loudness, but that toggle stays the listener's call).
    "Late Night": (2.0, 0.0, -3.0),
}
_EQ_BAND_FREQUENCIES = (100, 1000, 8000)
#: Slider range for each band, in dB. wx.Slider is integer-only, so gains
#: are whole dB steps -- plenty of resolution for a 3-band EQ (real mixing
#: consoles rarely offer finer than 1 dB per notch either).
EQ_BAND_MIN_DB = -12.0
EQ_BAND_MAX_DB = 12.0


def clamp_eq_gain(value: float) -> float:
    """Clamp a single band's gain to the slider's supported range."""
    return max(EQ_BAND_MIN_DB, min(EQ_BAND_MAX_DB, value))


# threshold/ratio/attack/release/makeup tuned to even out a typical low-bitrate
# internet radio stream without audibly pumping.
_COMPRESSOR_FILTER = "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2"

# Smart Speed (podcasts only -- see build_filter_graph): trims silence longer
# than stop_duration below stop_threshold anywhere in the audio
# (stop_periods=-1), not just leading/trailing -- the gaps between sentences
# a spoken-word episode is full of. Deliberately not exposed for radio: a
# live stream has no fixed content to trim ahead of time, and "silence" in
# music is often intentional. Kept here (unused by anything in this mac
# build yet) purely so build_filter_graph's signature stays identical to
# upstream's, per the port's interface contract.
_SMART_SPEED_FILTER = "silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-40dB"

# Mono downmix: both channels blended equally into a single channel -- an
# accessibility option for single-sided hearing (or a single earbud), where
# hard-panned stereo content simply disappears otherwise.
_MONO_FILTER = "pan=mono|c0=0.5*c0+0.5*c1"

# Night mode: real-time loudness normalization (dynaudnorm) -- lifts quiet
# program material toward a consistent level, the "boost the quiet parts"
# complement to the compressor's "tame the loud parts". frame length /
# gaussian window tuned for music-safe smoothing without audible pumping.
_NIGHT_MODE_FILTER = "dynaudnorm=f=250:g=15:p=0.9"


class EnhanceError(CodedError):
    """Sound Enhancements could not be applied.

    Upstream raises this when the ffmpeg relay process fails to start;
    this port has no relay process (mpv applies the filter graph
    natively), so nothing in this module raises it today. Kept for a
    later task -- e.g. the mpv engine wrapping a native ``af`` property
    failure -- so callers throughout the port can catch one coded
    exception type for "Sound Enhancements did not take effect."
    """

    code = "QUILL-RADIO-ENHANCE-FAILED"


def build_filter_graph(
    bass_db: float,
    mid_db: float,
    treble_db: float,
    *,
    compressor_enabled: bool,
    smart_speed_enabled: bool = False,
    mono_enabled: bool = False,
    night_mode_enabled: bool = False,
) -> str:
    """Build the ffmpeg-syntax filter graph for the three-band equalizer
    (Bass/Mid/Treble, in dB, each clamped to ``EQ_BAND_MIN_DB``..
    ``EQ_BAND_MAX_DB``) + the compressor + Smart Speed (silence trimming,
    podcasts only -- this mac build's radio-only callers never pass
    ``smart_speed_enabled=True``, but the parameter stays so the
    signature matches upstream exactly) + mono downmix + night mode
    (loudness normalization).

    Filter order matters and is deliberate: mono first (everything after
    hears the blended signal), then EQ, then the compressor, then smart
    speed, then night mode last so it levels the already-shaped result.

    Pure and unit-tested. Returns ``""`` when nothing is engaged (a
    caller should treat that as "play the stream directly, mpv's ``af``
    left unset"). On this mac build the same graph drives mpv's native
    ``af`` property directly -- no relay, no subprocess, no re-encode.
    """
    gains = (clamp_eq_gain(bass_db), clamp_eq_gain(mid_db), clamp_eq_gain(treble_db))
    filters = [_MONO_FILTER] if mono_enabled else []
    filters += [
        f"equalizer=f={freq}:t=q:w=1:g={gain}"
        for freq, gain in zip(_EQ_BAND_FREQUENCIES, gains, strict=True)
        if gain
    ]
    if compressor_enabled:
        filters.append(_COMPRESSOR_FILTER)
    if smart_speed_enabled:
        filters.append(_SMART_SPEED_FILTER)
    if night_mode_enabled:
        filters.append(_NIGHT_MODE_FILTER)
    return ",".join(filters)
