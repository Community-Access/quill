"""Audio sniffing and HLS reading for the Find Streams live check (no network).

The byte prefixes in ``fixtures/live_check`` are canned: two or more real frame
headers in a row for MP3 and AAC, an Ogg page carrying ``OpusHead``, and a
block of noise holding one lone MP3-looking sync word, which must not count.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio.audio_sniff import read_hls, sniff_codec

_FIXTURES = Path(__file__).parent / "fixtures" / "live_check"


def _bytes(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _text(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("fixture", "codec"),
    [
        ("mp3_prefix.bin", "MP3"),
        ("aac_prefix.bin", "AAC"),
        ("ogg_prefix.bin", "Ogg Opus"),
        ("noise_prefix.bin", ""),
        ("html_200.html", ""),
    ],
)
def test_sniff_recognises_each_recorded_prefix(fixture: str, codec: str) -> None:
    assert sniff_codec(_bytes(fixture)) == codec


def test_a_stream_joined_mid_frame_is_still_recognised() -> None:
    assert sniff_codec(b"\x13\x37garbage" + _bytes("mp3_prefix.bin")) == "MP3"


def test_one_lone_frame_header_is_not_enough() -> None:
    assert sniff_codec(bytes([0xFF, 0xFB, 0x90, 0x64]) + bytes(100)) == ""


def test_an_id3_tag_is_skipped_before_sniffing() -> None:
    tag = b"ID3\x04\x00\x00\x00\x00\x00\x0a" + bytes(10)
    assert sniff_codec(tag + _bytes("mp3_prefix.bin")) == "MP3"


def test_flac_wav_and_ogg_vorbis_headers() -> None:
    assert sniff_codec(b"fLaC\x00\x00\x00\x22" + bytes(64)) == "FLAC"
    assert sniff_codec(b"RIFF\x24\x00\x00\x00WAVEfmt " + bytes(64)) == "WAV"
    assert sniff_codec(b"OggS" + bytes(24) + b"\x01vorbis" + bytes(32)) == "Ogg Vorbis"


def test_empty_bytes_are_not_audio() -> None:
    assert sniff_codec(b"") == ""


def test_a_live_media_playlist_is_live() -> None:
    assert read_hls(_text("hls_live.m3u8")).kind == "live"


def test_an_end_listed_or_vod_playlist_is_a_recording() -> None:
    assert read_hls(_text("hls_vod.m3u8")).kind == "recording"


def test_an_encrypted_playlist_is_refused() -> None:
    assert read_hls(_text("hls_encrypted.m3u8")).kind == "encrypted"


def test_a_master_playlist_is_followed_to_its_audio_only_variant() -> None:
    reading = read_hls(_text("hls_master.m3u8"), "https://cdn.example.net/radio/master.m3u8")
    assert reading.kind == "master"
    assert reading.follow == "https://cdn.example.net/radio/audio/96k.m3u8"


def test_a_master_with_only_video_variants_is_video() -> None:
    assert read_hls(_text("hls_video_only.m3u8")).kind == "video"


def test_an_audio_rendition_is_preferred() -> None:
    master = (
        "#EXTM3U\n"
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",NAME="radio",URI="radio/audio.m3u8"\n'
        '#EXT-X-STREAM-INF:BANDWIDTH=900000,CODECS="avc1.4d401f,mp4a.40.2",AUDIO="a"\n'
        "video.m3u8\n"
    )
    assert (
        read_hls(master, "https://x.example/m.m3u8").follow == "https://x.example/radio/audio.m3u8"
    )


def test_a_plain_m3u_is_not_hls() -> None:
    assert read_hls("#EXTM3U\n#EXTINF:-1,KXYZ\nhttps://stream.example.org/live\n").kind == ""
