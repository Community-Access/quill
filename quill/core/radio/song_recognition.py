"""Identify This Song: a sample of what is playing, fingerprinted and looked up.

The pipeline behind the command, kept here so every step and every sentence is
testable without a sound card, a network or wx:

1. **The sample** comes from the buffer that is already playing (the engine's
   ``dump_recent_audio``), never from a fresh connection -- many stations
   greet every new connection with a pre-roll advert, and a fresh connection
   would fingerprint the advert (xradio2.md 6.1).
2. **The fingerprint** comes from Chromaprint's fpcalc
   (:mod:`quill.core.radio.chromaprint`), locally. No audio leaves the computer.
3. **The lookup** goes to AcoustID (:mod:`quill.core.radio.acoustid`), only
   because the listener asked, with the listener's own application key.

**A guess is called a guess.** AcoustID is built for whole recordings, and live
radio talks over intros, cross-fades songs and plays edits; a match is reported
as "best guess" with how sure AcoustID is, and a miss says it is a miss rather
than inventing a title. wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.radio import acoustid, chromaprint

#: Seconds of the buffer to fingerprint. AcoustID matches best on long samples.
SAMPLE_SECONDS = 60

#: Below this AcoustID score a match is too weak to say out loud as a song.
MIN_SCORE = 0.5

NO_MATCH = (
    "AcoustID found no match for this song. Recognition works best on recorded "
    "music; talk, a live performance or a station's own jingle will not match, "
    "so try again in a minute."
)

NOT_ENOUGH_AUDIO = (
    "There is not enough of this station in the buffer to listen to yet. "
    "Try again in half a minute."
)

NEEDS_MPV = (
    "Song recognition listens to the audio already playing, which needs the mpv "
    "playback engine. Choose it in Preferences, Playback engine."
)

DID_NOT_FINISH = "Song recognition did not finish. Try again in a moment."

#: Said while the sample is fingerprinted and looked up, which takes seconds.
LISTENING = "Identifying the song..."


@dataclass(frozen=True, slots=True)
class Recognition:
    """The outcome, and the sentence that reports it."""

    sentence: str
    best: acoustid.Match | None = None


def describe(matches: list[acoustid.Match]) -> Recognition:
    """The spoken answer for a lookup's matches (pure)."""
    confident = [match for match in matches if match.score >= MIN_SCORE]
    if not confident:
        return Recognition(NO_MATCH)
    best = confident[0]
    percent = int(round(best.score * 100))
    sentence = f"Best guess: {best.spoken()}, {percent} percent sure."
    others = [m.spoken() for m in confident[1:3] if m.spoken() != best.spoken()]
    if others:
        sentence += f" It could also be {' or '.join(others)}."
    return Recognition(sentence, best)


def precheck(*, key: str, fpcalc: str | None) -> str:
    """What stops recognition before any audio is touched, or ``""`` (pure).

    The key first: without it nothing else matters, and it is the one step the
    listener has to take by hand.
    """
    if not key.strip():
        return acoustid.NO_KEY_SENTENCE
    if not fpcalc:
        return chromaprint.MISSING_SENTENCE
    return ""


def recognise(
    sample: Path,
    *,
    key: str,
    fpcalc: str,
    safe_mode: bool = False,
    run: chromaprint.Runner | None = None,
    post: Callable[[bytes], str] | None = None,
) -> Recognition:
    """Fingerprint *sample* and look it up. Never raises: failures are sentences.

    Runs on a worker. The caller deletes *sample* afterwards whatever happened.
    """
    try:
        print_ = chromaprint.fingerprint(sample, fpcalc=fpcalc, run=run)
        matches = acoustid.lookup(
            key, print_.fingerprint, print_.duration, safe_mode=safe_mode, post=post
        )
    except (chromaprint.ChromaprintError, acoustid.AcoustIdError) as error:
        # The sentence the module wrote, without the support code str() adds:
        # these are read aloud, and a bracketed code is noise to a listener.
        return Recognition(str(error.args[0]) if error.args else NO_MATCH)
    return describe(matches)
