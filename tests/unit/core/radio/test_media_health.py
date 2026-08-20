"""A missing media tool has to produce a sentence, not a silence.

The failure these cover is the one described in ``media_health``'s docstring:
on the default "auto" engine preference, an installation whose ``libmpv-2.dll``
never staged loses seven capabilities and says nothing. Every assertion here is
about the app *saying* something true, so the tests are written against the
text rather than only the booleans.
"""

from __future__ import annotations

from quill.core.radio.media_health import (
    FFMPEG_CAPABILITIES,
    MPV_CAPABILITIES,
    MediaHealth,
    stream_needs_mpv,
)

HEALTHY = MediaHealth(ffmpeg=True, mpv=True)
NO_MPV = MediaHealth(ffmpeg=True, mpv=False)
NO_FFMPEG = MediaHealth(ffmpeg=False, mpv=True)
NEITHER = MediaHealth(ffmpeg=False, mpv=False)


# -- healthy says nothing ------------------------------------------------------


def test_a_healthy_install_has_nothing_to_announce() -> None:
    # A launch-time status line that speaks on every start to say all is well
    # is exactly the announcement noise this app avoids elsewhere.
    assert HEALTHY.healthy is True
    assert HEALTHY.summary() == ""
    assert HEALTHY.repair_hint() == ""
    assert HEALTHY.notice() == ""
    assert HEALTHY.lost_capabilities == ()


# -- what is lost --------------------------------------------------------------


def test_missing_mpv_costs_every_mpv_capability_and_nothing_else() -> None:
    assert NO_MPV.lost_capabilities == MPV_CAPABILITIES


def test_missing_ffmpeg_costs_recording_and_downloads_only() -> None:
    assert NO_FFMPEG.lost_capabilities == FFMPEG_CAPABILITIES


def test_losing_both_reports_playback_losses_before_recording_losses() -> None:
    # Reading order matters: a station that will not play is met without asking
    # for anything, where a Record command explains itself when it is used.
    assert NEITHER.lost_capabilities == MPV_CAPABILITIES + FFMPEG_CAPABILITIES


# -- the sentences -------------------------------------------------------------


def test_the_mpv_summary_names_the_engine_the_listener_fell_back_to() -> None:
    summary = NO_MPV.summary()
    assert "mpv playback engine is missing" in summary
    assert "Windows Media" in summary
    assert "live pause and rewind" in summary
    assert summary.endswith(".")


def test_the_ffmpeg_summary_says_the_rest_of_the_app_is_fine() -> None:
    # The distinction that keeps somebody from reinstalling over a working app.
    summary = NO_FFMPEG.summary()
    assert "FFmpeg is missing" in summary
    assert "Everything else works normally." in summary


def test_both_missing_is_one_sentence_about_both_not_two_reports() -> None:
    summary = NEITHER.summary()
    assert "Two media tools are missing" in summary
    assert "recording a station, now or on a schedule" in summary
    assert "live pause and rewind" in summary


def test_every_summary_ends_as_a_sentence() -> None:
    # Announcements that do not end in punctuation run into whatever a screen
    # reader says next (fixes.md 25g).
    for health in (NO_MPV, NO_FFMPEG, NEITHER):
        assert health.summary().endswith(".")
        assert health.repair_hint().endswith(".")
        assert health.notice().endswith(".")


def test_the_repair_hint_only_offers_get_ffmpeg_when_ffmpeg_is_the_problem() -> None:
    # Radio has no in-app mpv download; pointing at one would be a dead route.
    assert "Get FFmpeg" in NO_FFMPEG.repair_hint()
    assert "Get FFmpeg" not in NO_MPV.repair_hint()
    assert "reinstalling restores it" in NO_MPV.repair_hint()


def test_the_repair_hint_for_both_names_the_installer_and_the_download() -> None:
    hint = NEITHER.repair_hint()
    assert "reinstalling restores them" in hint
    assert "Get FFmpeg" in hint


def test_the_notice_is_the_summary_followed_by_the_hint() -> None:
    assert NO_MPV.notice() == f"{NO_MPV.summary()} {NO_MPV.repair_hint()}"


# -- the station that cannot play at all ---------------------------------------


def test_a_refusal_names_the_station_the_format_and_the_fix() -> None:
    message = NO_MPV.format_refusal("SomaFM Groove Salad")
    assert message.startswith("SomaFM Groove Salad")
    assert "Ogg, Opus or HLS" in message
    assert "reinstalling restores it" in message


def test_a_refusal_for_a_station_with_no_name_still_reads_as_a_sentence() -> None:
    assert NO_MPV.format_refusal("   ").startswith("This station uses")


# -- which streams need mpv ----------------------------------------------------


def test_the_containers_windows_media_cannot_open_are_recognised() -> None:
    assert stream_needs_mpv("https://ice.somafm.com/groovesalad-256-mp3.ogg")
    assert stream_needs_mpv("https://example.org/live/stream.opus")
    assert stream_needs_mpv("https://example.org/audio/playlist.m3u8")
    assert stream_needs_mpv("https://example.org/hls/live")


def test_an_ordinary_mp3_station_is_not_blamed_on_a_missing_component() -> None:
    # The conservative direction on purpose: sending somebody to repair a
    # healthy install because their station was merely offline is worse than
    # saying nothing.
    assert not stream_needs_mpv("https://ice.somafm.com/groovesalad-256-mp3")
    assert not stream_needs_mpv("https://example.org/stream.aac")
    assert not stream_needs_mpv("")


def test_the_test_is_case_insensitive_and_survives_a_query_string() -> None:
    assert stream_needs_mpv("HTTPS://EXAMPLE.ORG/LIVE.OPUS?token=abc")
    assert stream_needs_mpv("https://example.org/play?format=opus&bitrate=128")


def test_a_malformed_url_is_not_a_claim_about_codecs() -> None:
    assert not stream_needs_mpv("http://[not-a-host/stream")


def test_the_capability_list_is_semicolon_separated() -> None:
    """Two entries contain commas of their own.

    "Ogg Vorbis, Opus and HLS stations" and "recording a station, now or on a
    schedule" both do, so a comma-joined list of them is one long run a listener
    cannot parse. An earlier draft joined with a trailing "or" and produced
    "no live pause and rewind, choosing the output device or ..." -- a phrase
    that does not parse as English at all.
    """
    summary = NO_MPV.summary()
    assert "these are unavailable: " in summary
    assert "live pause and rewind; choosing the output device" in summary
    # And the entry that carries its own commas is still intact inside it.
    assert "Ogg Vorbis, Opus and HLS stations" in summary
