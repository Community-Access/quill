"""Tests for PLS / XSPF / ASX parsing and the M3U8 ambiguity.

All pure: no network, no files, no wx. The fixtures are shaped like the real
documents these formats arrive as, including the malformed ASX that motivates
its regex fallback.
"""

from __future__ import annotations

import pytest

from quill.core.radio.playlist_formats import (
    PlaylistFormatError,
    classify_m3u,
    is_hls_manifest,
    parse_asx,
    parse_playlist,
    parse_pls,
    parse_xspf,
    sniff,
    spoken_sniff_result,
)

_PLS = """[playlist]
NumberOfEntries=3
File1=https://ice1.somafm.com/groovesalad-128-mp3
Title1=SomaFM Groove Salad
Length1=-1
File2=https://ice2.somafm.com/groovesalad-128-mp3
Title2=SomaFM Groove Salad (2)
Length2=-1
File3=https://ice4.somafm.com/groovesalad-128-mp3
Title3=SomaFM Groove Salad (3)
Version=2
"""

_XSPF = """<?xml version="1.0" encoding="UTF-8"?>
<playlist version="1" xmlns="http://xspf.org/ns/0/">
  <trackList>
    <track>
      <location>https://stream.motherearthradio.de/listen/x/radio.ogg</location>
      <title>Mother Earth Radio</title>
      <creator>Mother Earth</creator>
    </track>
    <track>
      <location>http://quincy.torontocast.com:2720/stream</location>
      <creator>SatinJazz</creator>
    </track>
    <track>
      <title>No location, skipped</title>
    </track>
  </trackList>
</playlist>
"""

_ASX = """<ASX version="3.0">
  <TITLE>WXYZ Reading Service</TITLE>
  <ENTRY>
    <TITLE>Main Channel</TITLE>
    <REF HREF="http://stream.example.org:8000/main.mp3" />
  </ENTRY>
  <ENTRY>
    <TITLE>Second Channel</TITLE>
    <REF HREF="http://stream.example.org:8000/second.mp3" />
  </ENTRY>
</ASX>
"""

# ASX in the wild: unclosed tags, mixed case, no XML declaration. Not well-formed.
_ASX_MALFORMED = """<asx version = "3.0">
<entry>
<title>Talking Newspaper
<ref href="http://legacy.example.org:8000/listen.mp3">
</entry>
"""

_HLS_MEDIA = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXTINF:10.0,
segment0.ts
#EXTINF:10.0,
segment1.ts
"""

_HLS_MASTER = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=128000,CODECS="mp4a.40.2"
https://cdn.example/low/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=256000
https://cdn.example/high/index.m3u8
"""

_M3U_PLAYLIST = """#EXTM3U
#EXTINF:-1,Jazz FM
https://stream.example.org:8000/jazz
#EXTINF:-1,Rock FM
https://stream.example.org:8000/rock
"""


# --- the M3U8 ambiguity ------------------------------------------------------


def test_hls_media_playlist_is_not_a_station_list() -> None:
    # The bug this exists to prevent: importing an HLS manifest turns two-second
    # segments into "stations".
    assert classify_m3u(_HLS_MEDIA) == "hls"
    assert is_hls_manifest(_HLS_MEDIA)
    assert parse_playlist(_HLS_MEDIA) == []


def test_hls_master_playlist_is_still_hls() -> None:
    assert classify_m3u(_HLS_MASTER) == "hls"
    assert parse_playlist(_HLS_MASTER) == []


def test_ordinary_m3u_is_a_playlist() -> None:
    assert classify_m3u(_M3U_PLAYLIST) == "playlist"
    stations = parse_playlist(_M3U_PLAYLIST)
    assert [s.name for s in stations] == ["Jazz FM", "Rock FM"]


def test_an_hls_manifest_named_m3u_is_still_detected() -> None:
    # A server naming an HLS manifest .m3u is common; the body must win.
    assert sniff(_HLS_MEDIA, url="https://cdn.example/live.m3u") == "m3u8-hls"


# --- PLS ---------------------------------------------------------------------


def test_parse_pls_reads_files_and_titles() -> None:
    stations = parse_pls(_PLS)
    assert len(stations) == 3
    assert stations[0].name == "SomaFM Groove Salad"
    assert stations[0].stream_url == "https://ice1.somafm.com/groovesalad-128-mp3"


def test_parse_pls_matches_titles_by_number_not_position() -> None:
    # Real PLS files are not always written in order.
    text = (
        "[playlist]\nFile2=https://b.example/2\nTitle2=Two\nFile1=https://a.example/1\nTitle1=One\n"
    )
    assert [s.name for s in parse_pls(text)] == ["One", "Two"]


def test_parse_pls_falls_back_to_host_when_untitled() -> None:
    assert parse_pls("[playlist]\nFile1=https://www.example.org/stream\n")[0].name == "example.org"


def test_parse_pls_skips_unplayable_entries() -> None:
    text = "[playlist]\nFile1=mms://dead.example/x\nFile2=C:\\local\\file.mp3\nFile3=https://ok.example/s\n"
    stations = parse_pls(text)
    assert [s.stream_url for s in stations] == ["https://ok.example/s"]


def test_parse_pls_tolerates_junk() -> None:
    assert parse_pls("") == []
    assert parse_pls("not a playlist at all") == []


# --- XSPF --------------------------------------------------------------------


def test_parse_xspf_reads_namespaced_tracks() -> None:
    stations = parse_xspf(_XSPF)
    assert [s.name for s in stations] == ["Mother Earth Radio", "SatinJazz"]
    assert stations[0].stream_url.endswith("radio.ogg")


def test_parse_xspf_works_without_a_namespace() -> None:
    text = (
        "<playlist><trackList><track><location>https://a.example/s</location>"
        "<title>A</title></track></trackList></playlist>"
    )
    assert [s.name for s in parse_xspf(text)] == ["A"]


def test_parse_xspf_tolerates_junk() -> None:
    assert parse_xspf("") == []
    assert parse_xspf("<playlist><trackList>") == []  # malformed -> empty, not a crash


def test_parse_xspf_refuses_a_billion_laughs_payload() -> None:
    # A playlist is exactly the small attacker-supplied file this arrives in.
    hostile = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;">]><playlist><trackList><track>'
        "<location>&lol2;</location></track></trackList></playlist>"
    )
    with pytest.raises(PlaylistFormatError):
        parse_xspf(hostile)


# --- ASX ---------------------------------------------------------------------


def test_parse_asx_reads_entries_and_titles() -> None:
    stations = parse_asx(_ASX)
    assert [s.name for s in stations] == ["Main Channel", "Second Channel"]
    assert stations[0].stream_url == "http://stream.example.org:8000/main.mp3"


def test_parse_asx_falls_back_when_the_document_is_not_well_formed() -> None:
    # The common case for this format, not the exception.
    stations = parse_asx(_ASX_MALFORMED)
    assert [s.stream_url for s in stations] == ["http://legacy.example.org:8000/listen.mp3"]


def test_parse_asx_takes_a_bare_ref_outside_any_entry() -> None:
    stations = parse_asx('<asx version="3.0"><ref href="https://a.example/s"/></asx>')
    assert [s.stream_url for s in stations] == ["https://a.example/s"]


def test_parse_asx_tolerates_junk() -> None:
    assert parse_asx("") == []
    assert parse_asx("<html><body>nope</body></html>") == []


# --- sniffing ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (_PLS, "pls"),
        (_XSPF, "xspf"),
        (_ASX, "asx"),
        (_M3U_PLAYLIST, "m3u"),
        (_HLS_MEDIA, "m3u8-hls"),
        ("https://stream.example.org:8000/live", "stream"),
        ("", "stream"),
    ],
)
def test_sniff_identifies_a_document_from_its_body(text, expected) -> None:
    assert sniff(text) == expected


def test_sniff_uses_content_type_when_the_body_is_unhelpful() -> None:
    assert sniff("garbage", content_type="audio/x-scpls") == "pls"
    assert sniff("garbage", content_type="application/xspf+xml") == "xspf"
    assert sniff("garbage", content_type="video/x-ms-asf") == "asx"


def test_sniff_uses_the_extension_as_the_last_resort() -> None:
    assert sniff("garbage", url="https://x.example/list.pls") == "pls"
    assert sniff("garbage", url="https://x.example/list.wax") == "asx"
    assert sniff("garbage", url="https://x.example/list.wvx") == "asx"


def test_parse_playlist_dispatches_by_kind() -> None:
    assert len(parse_playlist(_PLS)) == 3
    assert len(parse_playlist(_XSPF)) == 2
    assert len(parse_playlist(_ASX)) == 2
    assert len(parse_playlist(_M3U_PLAYLIST)) == 2


@pytest.mark.parametrize(
    ("kind", "count", "expected"),
    [
        ("m3u8-hls", 0, "That is an HLS stream. Playing."),
        ("stream", 0, "That is a direct stream. Playing."),
        ("pls", 1, "That is a PLS playlist with 1 station."),
        ("pls", 23, "That is a PLS playlist with 23 stations."),
        ("xspf", 0, "That is a XSPF playlist, but it has no playable stations."),
    ],
)
def test_every_sniff_outcome_is_speakable(kind, count, expected) -> None:
    assert spoken_sniff_result(kind, count) == expected


# --- export round-trips ------------------------------------------------------


def _favorites():
    from quill.core.radio.favorites import FavoriteStation
    from quill.core.radio.models import RadioStation

    return [
        FavoriteStation(
            station=RadioStation(name="Jazz & Blues FM", stream_url="https://a.example/jazz")
        ),
        FavoriteStation(
            station=RadioStation(name="Rock FM", stream_url="http://b.example:8000/rock")
        ),
        FavoriteStation(station=RadioStation(name="No stream", stream_url="")),
    ]


@pytest.mark.parametrize("kind", ["pls", "xspf", "asx"])
def test_every_export_format_round_trips_through_its_own_parser(kind) -> None:
    from quill.core.radio.playlist_export import export_as

    text = export_as(kind, _favorites())
    stations = parse_playlist(text)
    assert [s.name for s in stations] == ["Jazz & Blues FM", "Rock FM"]
    assert [s.stream_url for s in stations] == [
        "https://a.example/jazz",
        "http://b.example:8000/rock",
    ]


def test_m3u_export_still_round_trips() -> None:
    from quill.core.radio.playlist_export import export_m3u

    stations = parse_playlist(export_m3u(_favorites()))
    assert [s.name for s in stations] == ["Jazz & Blues FM", "Rock FM"]


def test_an_ampersand_in_a_station_name_survives_xml_export() -> None:
    from quill.core.radio.playlist_export import export_xspf

    text = export_xspf(_favorites())
    assert "&amp;" in text and "Jazz & Blues" not in text
    assert parse_xspf(text)[0].name == "Jazz & Blues FM"


def test_pls_export_declares_its_entry_count() -> None:
    from quill.core.radio.playlist_export import export_pls

    text = export_pls(_favorites())
    assert "NumberOfEntries=2" in text  # the stream-less favorite is skipped


def test_export_as_falls_back_to_m3u_for_an_unknown_kind() -> None:
    from quill.core.radio.playlist_export import export_as

    assert export_as("nonsense", _favorites()).startswith("#EXTM3U")


# --- the long tail, and the disagreement report (radio2.md part IX) -----------


def test_an_asf_redirector_yields_its_stream_and_loses_the_dead_scheme() -> None:
    """[Reference]/Ref1= is how older Windows Media 'listen live' links arrive."""
    from quill.core.radio.playlist_formats import parse_playlist, sniff

    text = "[Reference]\nRef1=mmsh://stream.example.org/live\nRef2=http://b.example/live2\n"
    assert sniff(text) == "asf"
    urls = [station.stream_url for station in parse_playlist(text)]
    # mmsh:// is ASF's own name for what was always an http address.
    assert urls == ["http://stream.example.org/live", "http://b.example/live2"]


def test_a_saved_url_shortcut_is_a_station() -> None:
    from quill.core.radio.playlist_formats import parse_playlist, sniff

    windows = "[InternetShortcut]\nURL=http://a.example/stream\n"
    desktop = "[Desktop Entry]\nType=Link\nLink=http://a.example/stream\n"
    for text in (windows, desktop):
        assert sniff(text) == "shortcut"
        assert [s.stream_url for s in parse_playlist(text)] == ["http://a.example/stream"]


def test_a_winamp_b4s_playlist_keeps_its_names() -> None:
    from quill.core.radio.playlist_formats import parse_playlist, sniff

    text = (
        '<?xml version="1.0"?><WinampXML><playlist>'
        '<entry Playstring="http://a.example/one"><Name>One FM</Name></entry>'
        '<entry Playstring="http://a.example/two"><Name>Two FM</Name></entry>'
        "</playlist></WinampXML>"
    )
    # B4S contains <playlist>, so it must be recognised before the XSPF test.
    assert sniff(text) == "b4s"
    assert [(s.name, s.stream_url) for s in parse_playlist(text)] == [
        ("One FM", "http://a.example/one"),
        ("Two FM", "http://a.example/two"),
    ]


def test_a_windows_media_wpl_playlist_is_not_mistaken_for_asx() -> None:
    from quill.core.radio.playlist_formats import parse_playlist, sniff

    text = (
        '<?wpl version="1.0"?><smil><body><seq>'
        '<media src="http://a.example/w"/></seq></body></smil>'
    )
    assert sniff(text) == "wpl"
    assert [s.stream_url for s in parse_playlist(text)] == ["http://a.example/w"]


def test_the_long_tail_still_refuses_unplayable_addresses() -> None:
    from quill.core.radio.playlist_formats import parse_playlist

    text = "[InternetShortcut]\nURL=file:///C:/secret.txt\n"
    assert parse_playlist(text) == []


def test_agreeing_signals_report_nothing() -> None:
    from quill.core.radio.playlist_formats import disagreements

    text = "[playlist]\nNumberOfEntries=1\nFile1=http://a.example/s\n"
    assert (
        disagreements(text, url="https://x.example/listen.pls", content_type="audio/x-scpls") == []
    )


def test_a_wrong_extension_is_reported_rather_than_silently_overruled() -> None:
    from quill.core.radio.playlist_formats import disagreements

    text = "[playlist]\nNumberOfEntries=1\nFile1=http://a.example/s\n"
    notes = disagreements(text, url="https://x.example/listen.m3u")
    assert any("ends in .m3u" in note and "pls" in note for note in notes)


def test_audio_served_where_a_playlist_was_promised_is_reported() -> None:
    """The diagnosis a listener cannot make for themselves."""
    from quill.core.radio.playlist_formats import disagreements

    text = "[playlist]\nNumberOfEntries=1\nFile1=http://a.example/s\n"
    notes = disagreements(text, content_type="audio/mpeg")
    assert any("which is audio" in note for note in notes)


def test_a_bare_stream_disagrees_with_nothing() -> None:
    from quill.core.radio.playlist_formats import disagreements

    assert disagreements("", url="https://a.example/stream", content_type="audio/mpeg") == []
