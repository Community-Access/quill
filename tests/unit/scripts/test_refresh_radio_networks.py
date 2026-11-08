"""The curated-networks refresh tool's pure parts. It never probes from a test.

The probe itself refuses to run under pytest (and in CI): those are 500 other
people's servers, and a test that depends on them fails for no reason.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "refresh_radio_networks.py"


@pytest.fixture(scope="module")
def tool() -> Any:
    spec = importlib.util.spec_from_file_location("refresh_radio_networks", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_it_refuses_to_run_under_pytest(tool: Any) -> None:
    with pytest.raises(SystemExit):
        tool.main([])


@pytest.mark.parametrize(
    "ctype, ok",
    [
        ("audio/mpeg", True),
        ("audio/aacp; charset=x", True),
        ("application/ogg", True),
        ("text/html; charset=utf-8", False),
        ("", False),
    ],
)
def test_audio_types(tool: Any, ctype: str, ok: bool) -> None:
    assert tool.is_audio_type(ctype) is ok


def test_hls_is_recognised_by_path_or_type(tool: Any) -> None:
    assert tool.is_hls("https://a/b/playlist.m3u8?x=1")
    assert tool.is_hls("https://a/b", "application/vnd.apple.mpegurl")
    assert not tool.is_hls("https://a/stream.mp3", "audio/mpeg")


def test_hls_next_follows_a_variant_then_the_newest_segment(tool: Any) -> None:
    master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nlow/index.m3u8\n"
    assert tool.hls_next(master, "https://h/live/master.m3u8") == (
        "https://h/live/low/index.m3u8",
        True,
    )
    media = "#EXTM3U\n#EXTINF:6,\nseg1.aac\n#EXTINF:6,\nseg2.aac\n"
    assert tool.hls_next(media, "https://h/live/low/index.m3u8") == (
        "https://h/live/low/seg2.aac",
        False,
    )
    assert tool.hls_next("<html>", "https://h/") == ("", False)


def test_nts_mixtapes(tool: Any) -> None:
    payload = {
        "results": [
            {
                "mixtape_alias": "poolside",
                "title": "Poolside",
                "audio_stream_endpoint": "https://stream-mixtape-geo.ntslive.net/mixtape4",
            },
            {"title": "No stream"},
        ]
    }
    assert tool.nts_channels(payload) == [
        {
            "id": "poolside",
            "name": "Poolside",
            "url": "https://stream-mixtape-geo.ntslive.net/mixtape4",
        }
    ]


def test_radio_record_leaves_out_seasonal_channels(tool: Any) -> None:
    payload = {
        "result": {
            "stations": [
                {
                    "prefix": "rr_main",
                    "title": "Record",
                    "stream_128": "https://r.example/rr_main64.aacp",
                },
                {
                    "prefix": "xmas",
                    "title": "Christmas Chill",
                    "stream_128": "https://r.example/x.aacp",
                },
            ]
        }
    }
    rows = tool.radio_record_channels(payload)
    assert [r["name"] for r in rows] == ["Record"] and rows[0]["id"] == "rr-main"


def test_bbc_roster_and_loose_names(tool: Any) -> None:
    payload = {
        "data": [
            {
                "data": [
                    {
                        "id": "bbc_6music",
                        "network": {"id": "bbc_6music", "short_title": "Radio 6 Music"},
                    },
                    {
                        "id": "bbc_6music",
                        "network": {"id": "bbc_6music", "short_title": "Radio 6 Music"},
                    },
                ]
            }
        ]
    }
    assert tool.bbc_roster(payload) == [("bbc_6music", "Radio 6 Music")]
    assert tool.roster_key("Radio 6 Music") == tool.roster_key("6 Music")


def test_a_moved_stream_keeps_its_id_and_hand_rows_stay(tool: Any) -> None:
    existing = [
        {"id": "nts-1", "name": "NTS 1", "url": "https://relay.example/stream"},
        {"id": "poolside", "name": "Poolside", "url": "https://mix.example/old"},
        {"id": "gone", "name": "Gone", "url": "https://mix.example/gone"},
    ]
    fresh = [
        {"id": "poolside", "name": "Poolside", "url": "https://mix.example/new"},
        {"id": "slow", "name": "Slow Focus", "url": "https://mix.example/slow"},
    ]
    merged, added, missing = tool.merge_channels(existing, fresh)
    by_id = {row["id"]: row for row in merged}
    assert by_id["poolside"]["url"] == "https://mix.example/new"
    assert "nts-1" in by_id, "a row the API does not know is kept"
    assert added == ["Slow Focus"] and missing == ["Gone"]
