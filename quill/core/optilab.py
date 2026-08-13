"""OptiLab broadcast polish: three one-touch chains, adapted for ffmpeg.

Adapted from OptiLab Core by Lanes Audio / dgl1984
(https://github.com/dgl1984/optilab), with thanks and attribution. Licensed
**Apache-2.0 with the Commons Clause v1.0** as of upstream v1.3.0 -- not plain
Apache-2.0, which is what this file used to say. The Commons Clause withholds
the right to *sell* the Software; upstream's NOTICE separately grants
royalty-free commercial use of OptiLab Core as a tool for producing,
processing, broadcasting or streaming audio. Nothing upstream is embedded here
either way.

We reproduce the *shape* of its three modes -- Podcast Leveler, Stream Polish,
Smooth Limiter -- as ffmpeg filter chains that ride the same graph everywhere
Sound Enhancements already reaches (mpv-native live, the relay, recordings), so
they work cross-platform, preview live, and need no compiled artifact. This is
a faithful adaptation, not a bit-for-bit port of OptiLab's custom multiband /
AGC / limiter DSP.

**Correcting the record (2026-08-13).** This file used to justify that choice
by saying OptiLab was "a GUI-only plugin with no library to call and a
Windows-64-only binary". Checked against upstream, all three claims are false:
``native/API.md`` documents ``optilab-core``, a framework-independent **C++17
static library** introduced in **v1.2.0** and described as "the same processing
engine used by the CLAP and StationPlaylist/Winamp plug-in wrappers"; only the
CLAP and Winamp *wrapper* targets are platform-gated in their CMake, while
``optilab-core`` and an ``optilab-core-cli`` build with GCC/Clang too.

So the ffmpeg adaptation is a *choice*, not a necessity, and it should be
defended on its merits: reach (one graph for live, relay and recordings), no
per-platform compiled dependency, and live preview. Upstream is explicit that
its C++ API is "not a stable C ABI", so calling it would mean owning an adapter
and a build per platform. If that trade is ever revisited, the honest upside is
the two things a feed-forward ffmpeg graph provably cannot express -- upstream's
limiter feedback loop (see below) and bit-exact fidelity -- and the right shape
is an optional enhancement over this chain, never a replacement for it.

Each mode maps OptiLab's three controls onto ffmpeg: Mode picks the chain, Input
is a front-end gain (``volume``, 0 dB by default), and Auto-Adapt (0-100%)
stages the chain the way OptiLab interpolates its internal stages.

Kept in its own module, separate from :mod:`quill.core.audio_enhance`, precisely
because it tracks someone else's release cadence: when a new OptiLab Core lands,
everything that has to be re-read and re-mapped is in this file.

**Tracking OptiLab Core 1.4.0 (2026-08-11).** What that release changed is how
Auto-Adapt blends, and Stream Polish is restaged here to match: upstream's
``core_stage`` smoothstep is ported as :func:`_core_stage`, each stage gets
upstream's own Auto-Adapt window, the leveler *eases off* as adapt rises instead
of being driven harder, a gated slow lift supplies the loudness, and the
limiter's lookahead extends toward the top of the range at upstream's -0.1 dBFS
delivery target. Podcast Leveler and Smooth Limiter are untouched: 1.4.0's
Auto-Adapt work is specific to Stream Polish.

Two parts of 1.4.0 deliberately do not transfer:

* **The limiter feedback loop.** Upstream reduces the lift and withdraws bass
  assistance *while* final limiting is running heavy. An ffmpeg filter graph is
  feed-forward -- no stage can see how hard a later one is working -- so the lift
  here is gated on program material only. Backing the lift off at high Auto-Adapt
  would trade a real feature for a guess, so it is left honest.
* **The accessibility and metering fixes** (Core's Settings window opening
  independently of the host's Preferences page, and idle meter timers). Those are
  properties of OptiLab's own plugin GUI. QUILL has no OptiLab window and no
  meters: Sound Enhancements is a wx dialog through ``_show_modal_dialog``, and
  the StationPlaylist/NVDA focus conflict has no analogue here.

wx-free, strict-typed, and pure: every function here returns filter strings.
"""

from __future__ import annotations

__all__ = [
    "OPTILAB_MODES",
    "OPTILAB_MODE_LABELS",
    "OPTILAB_INPUT_MIN_DB",
    "OPTILAB_INPUT_MAX_DB",
    "clamp_optilab_input",
    "optilab_filters",
    "optilab_active",
]

OPTILAB_MODES = ("off", "podcast", "stream", "limiter")
OPTILAB_MODE_LABELS = {
    "off": "Off",
    "podcast": "Podcast Leveler (speech)",
    "stream": "Stream Polish (music)",
    "limiter": "Smooth Limiter (mastering)",
}
#: Input trim range (dB); 0 (no change) is the default, per product choice.
OPTILAB_INPUT_MIN_DB = -12.0
OPTILAB_INPUT_MAX_DB = 18.0


def _db_to_linear(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def _core_stage(x: float, a: float, b: float) -> float:
    """OptiLab Core's ``core_stage`` staging curve, ported verbatim in shape.

    Upstream (Apache-2.0)::

        function core_stage(x a b) local(t)
        (
          t = clamp((x-a)/max(b-a,0.000001),0,1);
          t*t*(3-2*t);
        );

    A smoothstep between two Auto-Adapt positions. Each stage is given its own
    ``a``/``b`` window, so stages fade in one after another with zero gradient at
    both ends rather than all rising together on one straight line. That is what
    1.4.0 means by blending continuously "with no abrupt switch at a particular
    setting": a linear ramp has a corner where it starts and stops, and those
    corners are audible as level steps when the slider is moved during playback.
    """
    span = max(b - a, 0.000001)
    t = max(0.0, min(1.0, (x - a) / span))
    return float(t * t * (3.0 - 2.0 * t))


def clamp_optilab_input(value: float) -> float:
    """Clamp OptiLab's Input trim to its supported range."""
    return max(OPTILAB_INPUT_MIN_DB, min(OPTILAB_INPUT_MAX_DB, value))


def optilab_filters(mode: str, input_db: float, auto_adapt: int) -> list[str]:
    """The ffmpeg filter chain for an OptiLab mode (empty for ``"off"``).

    Adapted from OptiLab Core (dgl1984, Apache-2.0): a leveling -> density ->
    tone -> lookahead-limiter chain per mode, with Auto-Adapt (0-100%) leaning
    the leveling/density more assertive. ``input_db`` is a front-end trim
    (0 = unchanged).
    """
    if mode not in ("podcast", "stream", "limiter"):
        return []
    depth = max(0.0, min(1.0, auto_adapt / 100.0))
    filters: list[str] = []
    trim = clamp_optilab_input(input_db)
    if trim:
        filters.append(f"volume={trim:.2f}dB")
    if mode == "podcast":
        # Speech: subsonic HPF, speech leveling (AGC), gentle density, a small
        # 65 Hz bass tame, then a lookahead limiter near -1.5 dBFS.
        expansion = 6.25 + 6.25 * depth
        ratio = 3.0 + 1.0 * depth
        filters.append("highpass=f=30")
        filters.append(f"speechnorm=e={expansion:.2f}:r=0.0005:l=1")
        filters.append(
            f"acompressor=threshold=-17dB:ratio={ratio:.2f}:attack=20:release=250:makeup=2"
        )
        filters.append("equalizer=f=65:t=q:w=1.4:g=-2")
        filters.append(f"alimiter=limit={_db_to_linear(-1.5):.4f}:attack=5:release=50")
    elif mode == "stream":
        # Music, restaged to follow OptiLab Core 1.4.0. Each stage gets its own
        # Auto-Adapt window through _core_stage, matching upstream's:
        #   g = core_stage(a,0.35,0.88)  leveler, which EASES OFF as adapt rises
        #   f = core_stage(a,0.50,1.00)  the slow sustained lift, upper half only
        #   d = core_stage(a,0.50,0.78)  density
        #   l = core_stage(a,0.65,1.00)  limiter lookahead
        #
        # The important inversion: turning Auto-Adapt up no longer drives every
        # stage harder. Upstream reduces its AGC amount (56 -> 50) as adapt rises
        # and hands the loudness to a separate slow lift, because pushing the
        # leveler *and* the compressor *and* the limiter together is what caused
        # the edge-case volume jumps 1.4.0 fixes.
        ease = _core_stage(depth, 0.35, 0.88)
        lift = _core_stage(depth, 0.50, 1.00)
        density = _core_stage(depth, 0.50, 0.78)
        lookahead_stage = _core_stage(depth, 0.65, 1.00)

        # Leveler. maxgain falls as adapt rises (the lift below takes over), and
        # the threshold gate is what makes the lift "respond only to qualifying
        # program material" -- silence, low-level noise and rumble no longer
        # build gain, which is the other half of the 1.4.0 fix.
        max_gain = 7.0 - 2.0 * ease
        gate = 0.015 + 0.035 * ease
        filters.append(f"dynaudnorm=f=200:g=15:p=0.90:maxgain={max_gain:.2f}:t={gate:.3f}")
        # Density, engaging over the upper-middle of the range only.
        makeup = 1.5 + 1.7 * density
        ratio = 2.5 + 0.5 * density
        filters.append(
            f"acompressor=threshold=-15dB:ratio={ratio:.2f}:attack=10:release=200:"
            f"makeup={makeup:.2f}"
        )
        # High frequencies get firmer control as adapt rises rather than a fixed
        # presence lift: the old flat +1.5 dB at 12 kHz was the opposite of the
        # "bright events are less likely to pass through" behaviour 1.4.0 wants.
        presence = 1.5 - 1.5 * lift
        if presence > 0.01:
            filters.append(f"equalizer=f=12000:t=q:w=1:g={presence:.2f}")
        top_tame = -1.8 * lift
        if top_tame < -0.01:
            filters.append(f"treble=g={top_tame:.2f}:f=9000:width_type=q:width=0.7")
        # The slow sustained lift, up to +3 dB, mirroring upstream's
        # stream_agc_lift_target_db = 3 * f.
        lift_db = 3.0 * lift
        if lift_db > 0.01:
            filters.append(f"volume={lift_db:.2f}dB")
        # Final stage: upstream's -0.1 dBFS delivery target, with lookahead
        # extending 0.54 -> 1.50 ms. level=disabled matters -- alimiter's auto
        # level would renormalise every passage up to the ceiling, which is
        # exactly the blanket loudness the gated lift above replaces.
        lookahead_ms = 0.54 + (1.50 - 0.54) * lookahead_stage
        filters.append(
            f"alimiter=limit={_db_to_linear(-0.1):.4f}:attack={lookahead_ms:.2f}:"
            f"release=50:level=disabled"
        )
    else:  # limiter
        # Clean mastering-style peak control: a light compressor then a
        # transparent lookahead limiter near -2.0 dBFS.
        ratio = 2.0 + 1.0 * depth
        filters.append(
            f"acompressor=threshold=-12dB:ratio={ratio:.2f}:attack=5:release=150:makeup=1"
        )
        filters.append(f"alimiter=limit={_db_to_linear(-2.0):.4f}:attack=5:release=60")
    return filters


def optilab_active(optilab_enabled: bool, optilab_mode: str) -> bool:
    """True when the OptiLab chain should apply (enabled and a real mode)."""
    return bool(optilab_enabled) and optilab_mode in ("podcast", "stream", "limiter")
