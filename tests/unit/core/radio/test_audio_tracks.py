"""Described audio: finding the track that narrates what is on screen.

This is the feature the app exists for, and the part worth pinning is the
*detection*, because publishers label these tracks half a dozen different ways
and none of them is a standard. The rule the tests enforce: be generous about
form, strict about meaning, and never invent a name for something.
"""

from __future__ import annotations

import pytest

from quill.core.radio.audio_tracks import (
    AudioTrack,
    describe_track,
    described_track,
    is_described,
    language_name,
    summarise,
    track_name_from_note,
    tracks_from_info,
)


@pytest.mark.parametrize(
    "label",
    [
        "English (Audio Description)",
        "English audio description",
        "AudioDescription",
        "Descriptive",
        "English described",
        "eng-desc",
        "English (AD)",
        "Commentary (ad)",
    ],
)
def test_the_forms_publishers_actually_use_are_recognised(label: str) -> None:
    assert is_described(label)


def test_a_descriptive_language_subtag_counts() -> None:
    # BCP 47 allows en-x-description, and broadcasters use it.
    assert is_described("", "en-x-description")
    assert is_described("", "en-x-ad")


@pytest.mark.parametrize("label", ["English", "Original", "Spanish", "Dubbed", "", "medium"])
def test_an_ordinary_track_is_not_mistaken_for_a_described_one(label: str) -> None:
    assert not is_described(label)


def test_a_track_is_named_never_numbered() -> None:
    # "Track 2" is a guess somebody has to make by listening, which is exactly
    # what this feature exists to remove.
    assert describe_track(AudioTrack("1", "en", "")) == "English"
    assert describe_track(AudioTrack("2", "en", "English (Audio Description)")) == (
        "English (described)"
    )
    assert describe_track(AudioTrack("3", "es", "Dubbed")) == "Spanish (Dubbed)"


def test_quality_notes_are_not_track_names() -> None:
    # yt-dlp's "medium"/"low"/"high" describe the encoding, not the content, and
    # "English (medium)" tells a listener nothing about which one to choose.
    assert describe_track(AudioTrack("1", "en", "medium")) == "English"
    assert describe_track(AudioTrack("1", "en", "DRC")) == "English"


def test_an_unknown_language_is_shown_as_itself_rather_than_guessed() -> None:
    assert language_name("qq") == "qq"
    assert language_name("") == "Unknown"
    assert language_name("en-GB") == "English"


def test_the_described_track_is_found_among_several() -> None:
    tracks = [
        AudioTrack("1", "en", ""),
        AudioTrack("2", "es", ""),
        AudioTrack("3", "en", "English (Audio Description)"),
    ]
    found = described_track(tracks)
    assert found is not None and found.track_id == "3"
    assert described_track(tracks[:2]) is None
    assert described_track([]) is None


def test_only_audio_renditions_are_listed() -> None:
    # A video rendition carries the same audio and would double every row.
    info = {
        "formats": [
            {"format_id": "251", "vcodec": "none", "acodec": "opus", "language": "en"},
            {"format_id": "137", "vcodec": "avc1", "acodec": "none", "language": "en"},
            {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "language": "en"},
        ]
    }
    assert [t.track_id for t in tracks_from_info(info)] == ["251"]


def test_identical_renditions_are_listed_once() -> None:
    info = {
        "formats": [
            {"format_id": "251", "vcodec": "none", "acodec": "opus", "language": "en"},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a", "language": "en"},
        ]
    }
    # Same language, same label: one row, because two rows offering the same
    # thing is a choice nobody can make.
    assert len(tracks_from_info(info)) == 1


def test_the_url_that_plays_each_rendition_is_kept() -> None:
    info = {
        "formats": [
            {
                "format_id": "251-1",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "English (Audio Description)",
                "url": "https://example/described",
            }
        ]
    }
    track = tracks_from_info(info)[0]
    # A rendition is a different URL, not a channel of one stream, so selecting
    # it is a reload -- and this is what gets reloaded.
    assert track.stream_url == "https://example/described"


def test_a_malformed_info_dict_yields_nothing_rather_than_raising() -> None:
    assert tracks_from_info({}) == []
    assert tracks_from_info({"formats": "nope"}) == []
    assert tracks_from_info({"formats": [None, 3, "x"]}) == []


def test_absence_is_reported_and_names_what_there_is() -> None:
    # "No described audio" alone leaves somebody wondering whether the feature
    # or the video is at fault.
    one = summarise([AudioTrack("1", "en", "")])
    assert "one audio track, English" in one
    assert "No described audio was published" in one

    two = summarise([AudioTrack("1", "en", ""), AudioTrack("2", "es", "")])
    assert "2 audio tracks: English, Spanish" in two

    assert "does not report its audio tracks" in summarise([])


def test_presence_is_reported_by_name() -> None:
    said = summarise([AudioTrack("1", "en", ""), AudioTrack("2", "en", "descriptive")])
    assert said == "Described audio is available: English (described)."


def test_one_track_at_several_bitrates_is_one_track() -> None:
    """The bug this feature could least afford, found by probing real videos.

    yt-dlp returns one audio-only format per codec *and* per quality tier, with
    ``format_note`` carrying the tier -- "low", "medium", "high". Keying on that
    made an ordinary single-track video list as two or three rows, all reading
    "English", which is precisely the "Track 1 / Track 2" puzzle this module
    exists to remove. It also made the absence message count wrongly.

    Shape taken from a real TED talk: four audio-only formats, one track.
    """
    info = {
        "formats": [
            {
                "format_id": "139",
                "vcodec": "none",
                "acodec": "mp4a",
                "language": "en",
                "format_note": "low",
            },
            {
                "format_id": "249",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "low",
            },
            {
                "format_id": "140",
                "vcodec": "none",
                "acodec": "mp4a",
                "language": "en",
                "format_note": "medium",
            },
            {
                "format_id": "251",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "medium",
            },
        ]
    }
    tracks = tracks_from_info(info)
    assert len(tracks) == 1
    assert tracks[0].display_name == "English"
    assert "one audio track" in summarise(tracks)


def test_genuinely_separate_tracks_are_kept_apart() -> None:
    """When yt-dlp does report real tracks, each is its own row.

    ``audio_track`` is present only where a video actually has more than one,
    which is why it -- and not the quality tier -- is the identity.
    """
    info = {
        "formats": [
            {
                "format_id": "251-0",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "medium",
                "audio_track": {"id": "en.4", "display_name": "English original"},
            },
            {
                "format_id": "251-1",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "low",
                "audio_track": {"id": "en.4", "display_name": "English original"},
            },
            {
                "format_id": "251-2",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "medium",
                "audio_track": {"id": "en-desc.3", "display_name": "English descriptive"},
            },
        ]
    }
    tracks = tracks_from_info(info)
    assert len(tracks) == 2
    described = described_track(tracks)
    assert described is not None
    assert described.track_id == "251-2"


def test_a_quality_tier_never_becomes_a_track_name() -> None:
    info = {
        "formats": [
            {
                "format_id": "249",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "format_note": "low",
            },
        ]
    }
    assert tracks_from_info(info)[0].display_name == "English"


# --- The shape YouTube actually returns -------------------------------------
#
# Captured from live yt-dlp runs against the videos named in the 3.0 test plan.
# yt-dlp fills in no ``audio_track`` dictionary for YouTube at all: the track's
# own name arrives inside ``format_note``, comma-joined with the quality tier.
# Both halves of that fact are traps, and each one broke this module once.


def _youtube_format(format_id: str, language: str, note: str) -> dict[str, object]:
    return {
        "format_id": format_id,
        "vcodec": "none",
        "acodec": "opus",
        "language": language,
        "format_note": note,
    }


def test_youtube_original_only_is_one_track() -> None:
    """Three bitrates of one rendition, exactly as ART LAB returns them."""
    info = {
        "formats": [
            _youtube_format("249", "en", "English original (default), low"),
            _youtube_format("250", "en", "English original (default), low"),
            _youtube_format("251", "en", "English original (default), medium"),
        ]
    }
    tracks = tracks_from_info(info)
    assert [track.display_name for track in tracks] == ["English"]
    assert described_track(tracks) is None


def test_a_described_youtube_track_survives_its_shared_language() -> None:
    """The regression this module exists to prevent.

    YouTube gives the original and the descriptive rendition the *same*
    language code. Keying identity on the language alone collapsed them into
    one row and threw the described track away -- silently, in the feature
    whose entire job is to find it.
    """
    info = {
        "formats": [
            _youtube_format("249", "en", "English original (default), low"),
            _youtube_format("251", "en", "English original (default), medium"),
            _youtube_format("251-1", "en", "English descriptive, medium"),
            _youtube_format("249-1", "en", "English descriptive, low"),
        ]
    }
    tracks = tracks_from_info(info)
    assert [track.display_name for track in tracks] == ["English", "English (described)"]
    described = described_track(tracks)
    assert described is not None
    assert described.track_id == "251-1"


def test_the_language_is_never_said_twice() -> None:
    """A row reading "English (English original)" is one nobody can read."""
    info = {"formats": [_youtube_format("251", "en", "English original (default), medium")]}
    assert tracks_from_info(info)[0].display_name == "English"


def test_a_regional_youtube_track_keeps_its_region() -> None:
    """MrBeast returns ``en-US``.

    The row says "English (US)" and not "English (US) original": the region is
    the one part that could ever tell two rows apart, and "original" never can.
    """
    info = {
        "formats": [
            _youtube_format("251", "en-US", "English (US) original (default), medium"),
            _youtube_format("249", "en-US", "English (US) original (default), low"),
        ]
    }
    tracks = tracks_from_info(info)
    assert len(tracks) == 1
    assert tracks[0].display_name == "English (US)"


def test_dubbed_tracks_stay_separate_rows() -> None:
    info = {
        "formats": [
            _youtube_format("251", "en", "English original (default), medium"),
            _youtube_format("251-2", "es", "Spanish, medium"),
            _youtube_format("249-2", "es", "Spanish, low"),
        ]
    }
    assert [track.display_name for track in tracks_from_info(info)] == ["English", "Spanish"]


@pytest.mark.parametrize(
    ("note", "expected"),
    [
        ("English original (default), low", "English original"),
        ("English descriptive, medium", "English descriptive"),
        ("medium", ""),
        ("low, DRC", ""),
        ("", ""),
        ("English (US) original (default), medium", "English (US) original"),
        ("English descriptive, MISSING POT", "English descriptive"),
        ("MISSING POT", ""),
    ],
)
def test_track_name_from_note(note: str, expected: str) -> None:
    assert track_name_from_note(note) == expected


def test_renditions_from_two_player_clients_merge_into_one_list() -> None:
    """The resolver asks two player clients, and their formats arrive together.

    The default clients name the original rendition; the iOS client serves the
    same rendition again -- flagged "MISSING POT" -- plus the descriptive one
    the defaults are never given. The flag is a delivery detail: left in the
    name, the one original track reads as two. Captured from the live resolve
    of the ART LAB video that proved described audio reachable on YouTube.
    """
    info = {
        "formats": [
            # Default clients' rows.
            _youtube_format("249", "en", "English original (default), low"),
            _youtube_format("251", "en", "English original (default), medium"),
            # The iOS client's rows.
            _youtube_format("139-0", "en-desc", "English descriptive, MISSING POT"),
            _youtube_format("251-0", "en-desc", "English descriptive, MISSING POT"),
            _youtube_format("139-1", "en", "English original (default), MISSING POT"),
        ]
    }
    tracks = tracks_from_info(info)
    assert [track.display_name for track in tracks] == ["English", "English (described)"]
    described = described_track(tracks)
    assert described is not None
    assert described.track_id == "139-0"


def test_a_dubbed_language_the_map_cannot_name_uses_its_own_label() -> None:
    """A dubbed video names its tracks; the label beats an unmapped code.

    And the repeat-strip must respect word boundaries: "Tamil" begins with
    "ta", and stripping mid-word produced rows reading "ta (mil)".
    """
    info = {
        "formats": [
            _youtube_format("251-0", "ta", "Tamil, medium"),
            _youtube_format("251-1", "te", "Telugu, MISSING POT"),
            _youtube_format("251-2", "fil", "Filipino, medium"),
        ]
    }
    # Sorted, because the rows are now ordered by order_tracks rather than by
    # whatever order YouTube served the formats in. This test is about the
    # names; test_english_leads_a_wall_of_dubs below is about the order.
    assert sorted(track.display_name for track in tracks_from_info(info)) == [
        "Filipino",
        "Tamil",
        "Telugu",
    ]


# -- the order twenty-four dubs are read in ---------------------------------------


def test_english_leads_a_wall_of_dubs() -> None:
    """Reported 2026-08-23: "It does show the 24 languages, and, oh, English
    should always be at the top."

    yt-dlp's order is the order YouTube happened to serve the formats in, which
    for a heavily dubbed video is effectively arbitrary -- so the one track the
    listener can understand sat somewhere in a list they had to arrow through.
    """
    info = {
        "formats": [
            _youtube_format("251-0", "es", "Spanish, medium"),
            _youtube_format("251-1", "fr", "French, medium"),
            _youtube_format("251-2", "en", "English original, medium"),
            _youtube_format("251-3", "de", "German, medium"),
        ]
    }

    rows = [track.display_name for track in tracks_from_info(info)]

    assert rows[0] == "English"
    # And the rest are findable rather than arbitrary.
    assert rows[1:] == sorted(rows[1:])


def test_the_original_track_leads_when_the_listener_speaks_another_language() -> None:
    """Rule two: a real performance beats a synthesised dub."""
    from quill.core.radio.audio_tracks import order_tracks

    info = {
        "formats": [
            _youtube_format("251-0", "de", "German, medium"),
            _youtube_format("251-1", "ja", "Japanese original, medium"),
        ]
    }

    rows = [t.display_name for t in order_tracks(tracks_from_info(info), preferred="pt")]

    assert rows[0] == "Japanese"


def test_the_original_track_is_recognised_from_yt_dlps_own_preference() -> None:
    """Not every extractor writes "original" into the note."""
    marked = _youtube_format("251-0", "ja", "Japanese, medium")
    marked["language_preference"] = 10
    info = {"formats": [_youtube_format("251-1", "de", "German, medium"), marked]}

    tracks = {t.language: t.is_default for t in tracks_from_info(info)}

    assert tracks["ja"] is True
    assert tracks["de"] is False
