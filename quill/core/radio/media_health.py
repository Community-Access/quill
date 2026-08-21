"""Which media tools are here, and what the listener loses when one is not.

**The bug this exists for.** ``RadioHistory.playback_engine`` defaults to
``"auto"``, and ``quill.ui.radio.engine_selection.select`` reads "auto" as
"prefer mpv whenever libmpv is present". When it is *not* present the selection
falls through to ``WxMediaEngine`` and says nothing at all -- the spoken
"The mpv playback engine is not available" line is reached only by someone who
went into Preferences and insisted on mpv by name. Everyone on the default
setting gets a radio that has quietly lost live pause and rewind, output-device
choice, Volume Boost, native Sound Enhancements, track titles from the stream,
stall detection, and every Ogg Vorbis, Opus and HLS station -- with no sentence
anywhere saying so. The listener sees a station that will not play and has no
route to the reason.

That is the same shape as the three dead speech engines in the 2026-08-17
runtime: the app asked "is it there?" and never said what the answer cost. The
lesson recorded then was *"is it present?" is not "does it work?"*. This module
is the other half of it: **absent is not the same as announced.**

**Why the probing is not here.** This module is pure: it takes two booleans and
returns what they mean. The resolution lives in
:mod:`quill.ui.radio.media_preflight`, which asks
``mpv_output_device_available()`` -- the *exact* predicate the engine selection
uses. A health report that probed differently from the code it describes would
eventually describe a machine nobody has.

wx-free, strict-typed, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

#: What only libmpv can do, in the listener's words rather than the engine's.
#: Every entry is a feature named in ``player_controller``'s own docstring as
#: mpv-delivered; if that list changes, this one is wrong.
MPV_CAPABILITIES: tuple[str, ...] = (
    "live pause and rewind",
    "choosing the output device",
    "Volume Boost",
    "Sound Enhancements without a relay",
    "track titles from the stream",
    "knowing when a stream has stalled",
    "Ogg Vorbis, Opus and HLS stations",
)

#: What only FFmpeg can do. Recording is the one everybody notices; the
#: downloads are the one nobody expects to lose.
FFMPEG_CAPABILITIES: tuple[str, ...] = (
    "recording a station, now or on a schedule",
    "downloading episodes and videos",
)

#: Stream containers Windows Media cannot decode at all, so a station using one
#: does not degrade without libmpv -- it simply does not play. Kept as suffixes
#: rather than a full content-type negotiation because the URL is what the app
#: has in hand before it opens anything.
_MPV_ONLY_SUFFIXES: tuple[str, ...] = (".ogg", ".oga", ".opus", ".m3u8")

#: Path fragments that mean the same thing where the extension is absent.
_MPV_ONLY_FRAGMENTS: tuple[str, ...] = ("/hls/", "format=opus", "format=ogg", "type=ogg")


def stream_needs_mpv(url: str) -> bool:
    """True when *url* names a container only libmpv can open.

    Used to turn "this station would not play" into "this station needs a
    component that is missing", which is a different sentence and a different
    next action. Deliberately conservative: an unrecognised URL answers False,
    because claiming a missing component for an ordinary MP3 station that was
    merely offline would send the listener to repair something that is fine.
    """
    if not url:
        return False
    lowered = url.strip().lower()
    try:
        path = urlsplit(lowered).path
    except ValueError:  # a malformed URL is not a claim about codecs
        return False
    if any(path.endswith(suffix) for suffix in _MPV_ONLY_SUFFIXES):
        return True
    return any(fragment in lowered for fragment in _MPV_ONLY_FRAGMENTS)


@dataclass(frozen=True, slots=True)
class MediaHealth:
    """What the two media tools are, and what their absence costs.

    Two booleans and the sentences they imply. Everything derived is a property
    or a method so a caller cannot construct a report whose text disagrees with
    its own state.
    """

    ffmpeg: bool
    mpv: bool

    @property
    def healthy(self) -> bool:
        """True when nothing is missing and nothing needs to be said."""
        return self.ffmpeg and self.mpv

    @property
    def lost_capabilities(self) -> tuple[str, ...]:
        """Every capability this machine cannot reach, in reading order.

        mpv's losses come first because they are the ones a listener meets
        without asking for anything: a station that will not play beats a
        Record command that reports why it cannot run.
        """
        lost: list[str] = []
        if not self.mpv:
            lost.extend(MPV_CAPABILITIES)
        if not self.ffmpeg:
            lost.extend(FFMPEG_CAPABILITIES)
        return tuple(lost)

    def signature(self) -> str:
        """A stable key for "this exact state has already been mentioned".

        Notices are remembered against this rather than against a bare "seen"
        flag, so a machine that loses a *second* tool after being told about the
        first is told again -- and a machine that gets one back and loses it
        later is not told twice about the same thing in between.
        """
        return f"ffmpeg={int(self.ffmpeg)},mpv={int(self.mpv)}"

    def summary(self) -> str:
        """One or two plain sentences naming what is missing and what it cost.

        Empty when healthy: a component that is present has nothing to announce,
        and a status line that speaks on every launch to say all is well is the
        announcement noise this app spends real effort avoiding.
        """
        if self.healthy:
            return ""
        if not self.mpv and not self.ffmpeg:
            return (
                "Two media tools are missing from this installation: the mpv "
                "playback engine and FFmpeg. Stations still play through Windows "
                "Media, but these are unavailable: "
                + _join(MPV_CAPABILITIES + FFMPEG_CAPABILITIES)
                + "."
            )
        if not self.mpv:
            return (
                "The mpv playback engine is missing, so Quill Radio is playing "
                "through Windows Media. Until it is back, these are unavailable: "
                + _join(MPV_CAPABILITIES)
                + "."
            )
        return (
            "FFmpeg is missing. Until it is back, these are unavailable: "
            + _join(FFMPEG_CAPABILITIES)
            + ". Everything else works normally."
        )

    def repair_hint(self, *, lite: bool = False) -> str:
        """What the listener can actually do about it, or "" when healthy.

        Leads with the download, because the download is the answer that works
        for everybody. Both tools ship inside the full Quill Radio installer, so
        a missing one usually means a damaged installation -- but "reinstall" is
        a poor first instruction and, for one edition, a useless one, so it
        comes second.

        Two things had to be fixed before this text could be true. Until
        2026-08-21 libmpv genuinely had no in-app download and this said so;
        the pack had been SHA-pinned on the ``assets-v1`` release the whole time
        (the *build* fetches it from there) with no route from the running app
        to it, which :mod:`quill.core.mpv_install` now provides. And the
        reinstall advice was itself untrue: the media tools rode inside the
        shared runtime's install-if-newer gate, so a reinstall behind a newer
        sibling app's runtime skipped them. ``installer\\shared-runtime.iss``
        now lays them down unconditionally.

        *lite* is the thin installer, which downloads the base shared runtime
        and carries no media tools at all (they are 306 MB, and four of the
        seven QuillVille apps never call them). Reinstalling it cannot help, so
        it is pointed at the full installer instead -- advice that sends
        somebody to repeat the install that could not have helped is worse than
        no advice. The *download* works there exactly as it does everywhere,
        which is the point of having one.
        """
        if self.healthy:
            return ""
        if lite:
            also_one = "It also ships inside the full Quill Radio installer."
            also_both = "They also ship inside the full Quill Radio installer."
        else:
            also_one = (
                "It also ships inside the Quill Radio installer, so reinstalling restores it."
            )
            also_both = (
                "They also ship inside the Quill Radio installer, so reinstalling restores them."
            )
        if not self.ffmpeg and self.mpv:
            return f"Choose Help, then Get FFmpeg, to download the official build. {also_one}"
        if self.ffmpeg and not self.mpv:
            return f"Choose Help, then Get mpv Playback Engine, to download it. {also_one}"
        return (
            "Choose Help, then Get FFmpeg, and Help, then Get mpv Playback Engine, "
            f"to download them. {also_both}"
        )

    def notice(self, *, lite: bool = False) -> str:
        """The summary and the repair hint as one spoken paragraph."""
        if self.healthy:
            return ""
        return f"{self.summary()} {self.repair_hint(lite=lite)}"

    def format_refusal(self, station_name: str, *, lite: bool = False) -> str:
        """Why *this* station will not play, when the reason is the missing engine.

        The generic stream error ("could not play") is true and useless here:
        the station is fine, the machine cannot open its container, and the fix
        is a reinstall rather than another station.
        """
        name = station_name.strip() or "This station"
        return (
            f"{name} uses Ogg, Opus or HLS audio, which needs the mpv playback "
            f"engine. It is missing from this installation. {self.repair_hint(lite=lite)}"
        )


def _join(items: tuple[str, ...]) -> str:
    """A spoken list, separated by semicolons.

    Semicolons rather than commas because two of these entries contain commas of
    their own ("Ogg Vorbis, Opus and HLS stations"; "recording, now or on a
    schedule"), and a comma-joined list of comma-containing items is one long
    run a listener cannot parse. Each sentence introduces the list with a colon,
    so no trailing "and" is needed -- and a trailing "or" was worse than none: it
    turned "no X, choosing the output device or Y" into a phrase that does not
    parse as English at all.
    """
    return "; ".join(items)
