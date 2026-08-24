"""What QUILL Cast quietly cannot do when FFmpeg is missing (list.md 5.3).

Quill Radio says this once, in one plain sentence, and stays silent on a
healthy install (:mod:`quill.core.radio.media_health`). QUILL Cast said
nothing at all -- and Cast needs FFmpeg for *more* than Radio does, in ways
that are harder to notice.

That is the whole argument for this module. A missing playback engine
announces itself: the station does not play. Every one of Cast's FFmpeg
features fails **by producing a plausible result**. The download completes,
and simply is not trimmed. The episode plays, and is not normalised. The
chapter analysis finishes and finds nothing, which is exactly what it looks
like when an episode genuinely has no chapters. A listener cannot tell any of
those from working correctly, so nobody reports them, so they stay broken.

Cast needs one tool where Radio needs two: there is no libmpv path here.
Episodes are local files by the time they are played, and the FFmpeg relay is
engaged only for Sound Enhancements and Smart Speed. So this is a smaller
report than Radio's, and it is a separate one rather than a shared one because
the *sentences* are the product -- "recording a station" is not a thing Cast
does, and a listener told they have lost it would go looking for a feature
that was never there.

Pure: two booleans in, sentences out. The probing lives in
:mod:`quill.ui.podcasts.media_preflight`, beside the code it describes, for
the reason Radio's records -- a health report that probed differently from the
feature it reports on would eventually describe a machine nobody has.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FFMPEG_CAPABILITIES", "CastMediaHealth"]

#: What Cast loses without FFmpeg, in the listener's words. Every entry is a
#: real call site: ``core.podcasts.audio_processing`` (trim, normalise),
#: ``ui.podcasts.chapter_analysis`` and ``chapter_inference_ui`` (working out
#: chapters by listening), and ``ui.podcasts.player_controller``'s relay
#: (Sound Enhancements, Smart Speed). If those move, this list is wrong.
FFMPEG_CAPABILITIES: tuple[str, ...] = (
    "trimming the silence off a downloaded episode",
    "evening out the volume of a downloaded episode",
    "working out chapters for an episode that has none",
    "Sound Enhancements and Smart Speed while playing",
)


@dataclass(frozen=True, slots=True)
class CastMediaHealth:
    """Whether FFmpeg is here, and what its absence costs.

    One boolean, because Cast needs one tool. Everything else is derived, so a
    caller cannot build a report whose words disagree with its own state.
    """

    ffmpeg: bool

    @property
    def healthy(self) -> bool:
        return self.ffmpeg

    @property
    def lost_capabilities(self) -> tuple[str, ...]:
        return () if self.ffmpeg else FFMPEG_CAPABILITIES

    def signature(self) -> str:
        """A stable key for "this exact state has been mentioned already".

        Remembered against this rather than a bare "told them once" flag, so a
        machine that is repaired and later breaks again is told again, and a
        machine in the same state is not told on every launch forever. Same
        mechanism as Radio's, deliberately.
        """
        return f"ffmpeg={int(self.ffmpeg)}"

    def summary(self) -> str:
        """What is missing and what it costs. Empty when healthy.

        Empty is the important half: a launch that reports "all is well" every
        time is a launch nobody can listen past, and it trains people to talk
        over the one launch that had something to say.
        """
        if self.healthy:
            return ""
        return (
            "FFmpeg is missing from this installation. Podcasts still download "
            "and play normally, but these do nothing until it is back: "
            + _join(FFMPEG_CAPABILITIES)
            + "."
        )

    def repair_hint(self, *, lite: bool = False) -> str:
        """What the listener can do about it, or "" when healthy.

        The download comes first because it is the answer that works for
        everybody. *lite* is the thin installer, which carries no media tools
        at all -- telling somebody to reinstall the edition that could not have
        included FFmpeg is worse than telling them nothing.
        """
        if self.healthy:
            return ""
        if lite:
            return (
                "Choose Help, then Get FFmpeg, to download the official build. "
                "It also ships inside the full QUILL Cast installer."
            )
        return (
            "Choose Help, then Get FFmpeg, to download the official build. It "
            "also ships inside the QUILL Cast installer, so reinstalling restores it."
        )

    def notice(self, *, lite: bool = False) -> str:
        """The summary and the repair hint as one spoken paragraph."""
        if self.healthy:
            return ""
        return f"{self.summary()} {self.repair_hint(lite=lite)}"

    def readout(self, *, lite: bool = False) -> str:
        """The answer to *asking*, which unlike the notice is never empty.

        Somebody who chose a menu item called Media Tools asked a question and
        is owed an answer; silence there reads as a broken menu item rather
        than as good news. This is the one place a healthy install says so out
        loud, and it says it in one line.
        """
        if self.healthy:
            return (
                "FFmpeg is installed. Trimming silence, evening out volume, "
                "working out chapters, and Sound Enhancements are all available."
            )
        return self.notice(lite=lite)


def _join(items: tuple[str, ...]) -> str:
    """A spoken list separated by semicolons.

    Semicolons rather than commas because these entries contain commas and
    "and" of their own; a comma-joined list of comma-containing phrases is one
    long run that a listener cannot find the boundaries in. Each sentence
    introduces the list with a colon, so no trailing conjunction is needed.
    """
    return "; ".join(items)
