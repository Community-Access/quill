"""Live proof that the described-audio reading of a real YouTube video is honest.

The described-audio feature is the one Quill Radio exists for, and it is the
easiest in the whole application to get quietly wrong: yt-dlp's format list is
the *only* evidence there is, its shape changes between releases, and both
failure modes are silent. One rendition split across bitrates reads as three
tracks nobody can choose between; two genuine renditions sharing a language code
collapse into one and the described track disappears. Neither raises anything.

So this module points the real resolver at real videos -- the ones named in
``docs/qa/radio-3.0-test-plan.md``, including every video reported to carry a
selectable descriptive track -- and checks the invariants that must hold *no
matter what YouTube serves on the day*:

* every video resolves and reports at least one track;
* no two rows read the same, because a duplicate row is an unanswerable
  question;
* no row is named after an encoding quality tier;
* the spoken summary agrees with the list it is summarising.

For the videos known to publish a descriptive rendition, its *presence* is
asserted too -- reaching those tracks is the point of the resolver's iOS player
client, and losing them again (a yt-dlp change, a client rotation, SABR
spreading) is precisely the regression this file exists to catch. A video that
no longer resolves at all is skipped, not failed: a pulled upload is the
publisher's act, not a defect.

Opt in -- it needs the network and yt-dlp::

    QUILL_YT_LIVE=1 pytest tests/integration/test_youtube_audio_tracks_live.py -v
"""

from __future__ import annotations

import os

import pytest

from quill.core.radio.audio_tracks import described_track, summarise
from quill.core.radio.youtube import YouTubeError, resolve_youtube_stream, youtube_available

pytestmark = pytest.mark.skipif(
    os.environ.get("QUILL_YT_LIVE") != "1",
    reason="Live YouTube probe; set QUILL_YT_LIVE=1 to run.",
)

#: Videos that publish a *selectable* descriptive audio track. YouTube's web
#: response names these renditions but serves them URL-less (SABR); the
#: resolver reaches them through the iOS player client, and each one here has
#: been verified live to resolve with a playable described stream.
DESCRIPTIVE_CANDIDATES = {
    "ART LAB introduction": "https://www.youtube.com/watch?v=UusppshIAio",
    "Tested: Fractal Vise": "https://www.youtube.com/watch?v=mZBwhJxrcW4",
    "Tested: This Old Box": "https://www.youtube.com/watch?v=1JgYMJDfPvc",
    "Tested: Milling Machine": "https://www.youtube.com/watch?v=OHfSZlfPTNc",
    "Tested: Cubby Door": "https://www.youtube.com/watch?v=WhQU-nc4xkg",
    "Tested: Camera Rig": "https://www.youtube.com/watch?v=2igc_BelOXk",
    "Apple: I'm Not Remarkable": "https://www.youtube.com/watch?v=KmFPWxjmnqE",
    "Apple: Hikawa Grip and Stand": "https://www.youtube.com/watch?v=TTb_cjCo7Nc",
}

#: Uploads where the description is mixed into the only track. One track is the
#: *right* answer for these, and claiming two would be the tier bug returning.
BAKED_IN_DESCRIBED = {
    "Apple: Designed for Shane R.": "https://www.youtube.com/watch?v=r0XRoogmJuk",
    "MSFTEnable: Be My Eyes (described)": "https://www.youtube.com/watch?v=LYKUnym0EqU",
    "MSFTEnable: Be My Eyes (plain)": "https://www.youtube.com/watch?v=VM9yLxnzQAM",
}

#: Ordinary videos: several audio formats, one rendition.
ORDINARY = {
    "TED talk": "https://www.youtube.com/watch?v=iG9CE55wbtY",
    "MrBeast": "https://www.youtube.com/watch?v=0e3GPea1Tyg",
}

ALL_VIDEOS = {**DESCRIPTIVE_CANDIDATES, **BAKED_IN_DESCRIBED, **ORDINARY}

#: Never a track name. If one of these is read aloud as a row, the note parser
#: has stopped stripping the encoding quality off the track's own name.
_TIER_WORDS = ("low", "medium", "high", "ultralow", "tiny", "drc", "default", "original")


@pytest.fixture(scope="module", autouse=True)
def _needs_yt_dlp() -> None:
    if not youtube_available():
        pytest.skip("yt-dlp is not installed.")


@pytest.mark.parametrize("name", sorted(ALL_VIDEOS))
def test_a_real_video_reports_its_tracks_honestly(name: str) -> None:
    try:
        stream = resolve_youtube_stream(ALL_VIDEOS[name])
    except YouTubeError as error:  # a pulled video is not a code defect
        pytest.skip(f"{name} did not resolve: {error}")

    tracks = list(stream.audio_tracks)
    assert tracks, f"{name} resolved but reported no audio tracks at all"

    rows = [track.display_name for track in tracks]
    assert len(set(rows)) == len(rows), f"{name} lists the same row twice: {rows}"

    for row in rows:
        assert row.strip(), f"{name} has an unnamed row"
        assert row.strip().lower() not in _TIER_WORDS, (
            f"{name} named a row after an encoding tier: {row!r}"
        )

    spoken = summarise(tracks)
    described = described_track(tracks)
    if described is None:
        assert "No described audio was published." in spoken
        assert str(len(tracks)) in spoken or "one audio track" in spoken
    else:
        assert "Described audio is available" in spoken
        assert described.display_name in spoken
        # A described track that cannot be played is an offer that fails when
        # taken up, which is worse than no offer.
        assert described.stream_url, f"{name} found a described track with no stream"


@pytest.mark.parametrize("name", sorted(BAKED_IN_DESCRIBED))
def test_a_baked_in_described_upload_is_one_track(name: str) -> None:
    """The description is the audio, so one track is the honest count."""
    try:
        stream = resolve_youtube_stream(BAKED_IN_DESCRIBED[name])
    except YouTubeError as error:
        pytest.skip(f"{name} did not resolve: {error}")
    assert len(stream.audio_tracks) == 1, (
        f"{name} is a single-rendition upload but reported "
        f"{[t.display_name for t in stream.audio_tracks]}"
    )


def test_the_descriptive_videos_keep_their_described_track() -> None:
    """Every known descriptive-track video still surfaces it, playably.

    Written as one test rather than eight so the result reads as a table, and
    so a single client rotation that silences all of them is one clear failure
    instead of a scatter. This is the regression guard for the resolver's iOS
    player client -- the web client names these renditions and serves them
    URL-less, so if the second client stops answering, described audio on
    YouTube quietly vanishes again.
    """
    lines: list[str] = []
    missing: list[str] = []
    for name, url in sorted(DESCRIPTIVE_CANDIDATES.items()):
        try:
            stream = resolve_youtube_stream(url)
        except YouTubeError as error:
            lines.append(f"{name}: did not resolve ({error})")
            continue
        rows = [track.display_name for track in stream.audio_tracks]
        found = described_track(list(stream.audio_tracks))
        lines.append(f"{name}: {rows} described={found.display_name if found else None}")
        assert rows, f"{name} reported no audio tracks"
        if found is None or not found.stream_url:
            missing.append(name)
    print("\n".join(lines))
    assert not missing, (
        "These videos publish a descriptive track the resolver no longer "
        f"reaches: {missing}. The likely cause is the iOS player client no "
        "longer being served the alternate renditions."
    )


@pytest.mark.parametrize("name", sorted(ORDINARY))
def test_the_resolved_address_can_actually_be_fetched(name: str) -> None:
    """A resolve that succeeds is not the same as a video that plays.

    This is the check that was missing on 2026-08-23, and its absence is why a
    stale yt-dlp looked healthy from inside the app. Every assertion above was
    green on yt-dlp 2026.7.4 -- the page resolved, the title, length, chapters
    and track list all came back -- and the googlevideo address it handed over
    answered **403 Forbidden** to every client, yt-dlp's own downloader
    included. Quill Radio hands that address to mpv (or to ffmpeg, for a
    recording or a Sound Enhancements relay), so "there is a URL" is not the
    invariant worth guarding; "the URL serves bytes" is.

    A range request, so this costs a kilobyte rather than a video.
    """
    import urllib.error
    import urllib.request

    try:
        stream = resolve_youtube_stream(ORDINARY[name])
    except YouTubeError as error:
        pytest.skip(f"{name} did not resolve: {error}")
    assert stream.stream_url, f"{name} resolved with no stream address"

    request = urllib.request.Request(  # noqa: S310 - https, from the resolver
        stream.stream_url, headers={"Range": "bytes=0-1023"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as error:
        pytest.fail(
            f"{name} resolved but its audio address answered HTTP {error.code}. "
            "YouTube issues stream addresses per player client and stops "
            "honouring them for the others; the usual cause is a yt-dlp that "
            "has fallen behind (Station > Update YouTube Support)."
        )
    assert status in (200, 206), f"{name} answered HTTP {status}"
    assert payload, f"{name} answered {status} with no audio bytes"
