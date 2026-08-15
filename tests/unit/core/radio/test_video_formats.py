"""Picking a video stream, and the caption style that makes it readable.

The two pure halves of the video work. The video-format rule that matters:
YouTube serves adaptive video and audio *separately*, so the picture is chosen
from the **video-only** formats and paired with the audio at play time. Merging
them first would mean downloading the whole file before a frame appeared, which
is not streaming and is impossible for a live broadcast.
"""

from __future__ import annotations

import pytest

from quill.core.radio.caption_style import (
    CaptionStyle,
    describe,
    mpv_properties,
)
from quill.core.radio.video_formats import (
    MAX_HEIGHT,
    VideoStream,
    describe_video,
    pick_video_stream,
)


def _fmt(**kwargs: object) -> dict:
    base = {"url": "u", "vcodec": "avc1", "acodec": "none", "height": 720, "width": 1280}
    base.update(kwargs)
    return base


def test_the_tallest_stream_within_the_cap_wins() -> None:
    info = {
        "formats": [
            _fmt(url="small", height=360, width=640),
            _fmt(url="big", height=1080, width=1920),
            _fmt(url="medium", height=720),
        ]
    }
    assert pick_video_stream(info).url == "big"


def test_a_stream_above_the_cap_is_refused() -> None:
    # 4K decoded to be glanced at is processor a screen reader needs.
    info = {"formats": [_fmt(url="uhd", height=2160, width=3840), _fmt(url="hd", height=1080)]}
    assert pick_video_stream(info).url == "hd"
    assert pick_video_stream({"formats": [_fmt(url="uhd", height=2160)]}).url == ""
    assert MAX_HEIGHT == 1080


def test_a_combined_stream_is_not_chosen() -> None:
    # It carries its own audio; pairing it with a separate audio file would play
    # the same programme twice.
    info = {"formats": [_fmt(url="combined", acodec="mp4a")]}
    assert pick_video_stream(info).url == ""


def test_an_audio_only_resolve_has_no_video() -> None:
    info = {"formats": [{"url": "a", "vcodec": "none", "acodec": "opus"}]}
    assert not pick_video_stream(info).available


def test_bitrate_then_frame_rate_break_a_tie() -> None:
    info = {
        "formats": [
            _fmt(url="low", height=1080, tbr=1000, fps=30),
            _fmt(url="high", height=1080, tbr=6000, fps=30),
        ]
    }
    assert pick_video_stream(info).url == "high"


def test_a_malformed_info_dict_yields_no_video_rather_than_raising() -> None:
    assert not pick_video_stream({}).available
    assert not pick_video_stream({"formats": "nope"}).available
    assert not pick_video_stream({"formats": [None, 7, "x"]}).available


def test_the_size_is_spoken_as_words_not_a_ratio() -> None:
    assert VideoStream(url="u", width=1280, height=720).spoken_size == "1280 by 720"
    assert VideoStream(url="u").spoken_size == ""


def test_video_information_ends_with_the_two_accessibility_facts() -> None:
    said = describe_video(
        VideoStream(url="u", width=1920, height=1080, fps=30, codec="avc1"),
        captions=True,
        described_audio=False,
    )
    assert "1920 by 1080" in said
    assert said.endswith("No described audio was published.")
    assert "Captions are available." in said


def test_video_information_on_an_audio_station_says_so() -> None:
    assert describe_video(VideoStream(), captions=False, described_audio=False) == (
        "There is no video for this station."
    )


# -- caption style ---------------------------------------------------------------


def test_captions_default_to_an_opaque_background() -> None:
    # Caption text sits over arbitrary moving pictures, so no colour can be
    # guaranteed to contrast with what is behind it. An opaque box is the only
    # honest default.
    props = mpv_properties(CaptionStyle())
    assert props["sub-back-color"] == "#FF000000"
    assert props["sub-color"] == "#FFFFFFFF"


def test_captions_scale_to_at_least_two_hundred_percent() -> None:
    # WCAG 1.4.4 asks for 200%; 300% is offered because a floor is not a target.
    assert mpv_properties(CaptionStyle(size_percent=200))["sub-scale"] == "2.00"
    assert mpv_properties(CaptionStyle(size_percent=300))["sub-scale"] == "3.00"


@pytest.mark.parametrize(
    ("field", "value"),
    [("size_percent", 9999), ("size_percent", -4), ("background_opacity", 500)],
)
def test_a_stored_oddity_is_clamped_rather_than_reaching_the_player(field: str, value: int) -> None:
    style = CaptionStyle(**{field: value}).clamped()
    assert 100 <= style.size_percent <= 300
    assert 0 <= style.background_opacity <= 100


def test_an_unknown_position_falls_back_to_the_bottom() -> None:
    assert CaptionStyle(position="sideways").clamped().position == "bottom"
    assert mpv_properties(CaptionStyle(position="top"))["sub-align-y"] == "top"


def test_opacity_maps_onto_the_colour_alpha() -> None:
    assert mpv_properties(CaptionStyle(background_opacity=0))["sub-back-color"] == "#00000000"
    assert mpv_properties(CaptionStyle(background_opacity=50))["sub-back-color"].startswith("#80")


def test_the_style_describes_itself_in_words() -> None:
    said = describe(CaptionStyle(size_percent=200, text_colour="#FFFFFF00"))
    assert "200%" in said
    assert "yellow on black" in said
    assert "opaque" in said
