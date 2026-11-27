"""QUILL Cast and Earshot agree on Listening Places, byte for byte (``ear.md``).

Earshot (payown/earshot, ``Earshot/Features/ListeningPlaces``) and Cast each
implement ``listening-places/1`` on their own. These tests pin the two to each
other with Earshot's *own* test material, so a change on either side that
breaks agreement fails here before it ships (``ear.md`` 6.8, item 14):

- the six episode-id vectors from Earshot's ``ListeningPlacesFormatTests.swift``;
- Earshot's fixture files ``device-phone.json`` and ``device-desktop.json``,
  copied verbatim into ``fixtures/earshot``.

They also cover the robustness rules Cast adopted for its release: one index per
pass (C1), a finish from the phone doing Cast's finish (C2), timestamps
normalized before the text comparison (C3), one sentence for every skipped file
(C4), and the clock, stale-device and size guards (6.8).
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.core.podcasts import position_sync, retention
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.sync import listening_places as lp
from quill.core.sync import listening_places_read as lpr
from quill.core.sync.places_interchange import _as_z, sync_interchange

FIXTURES = Path(__file__).parent / "fixtures" / "earshot"
NOW = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)


# -- the same identity as Earshot -------------------------------------------------


@pytest.mark.parametrize(
    ("guid", "enclosure", "expected"),
    [
        ("guid-123", "https://example.com/a.mp3", "episode:7e49cadf3ac96645"),
        (" guid-123", "https://example.com/a.mp3", "episode:7e49cadf3ac96645"),
        ("", "https://example.com/episode.mp3", "episode:a30aa1fd51eb5525"),
        ("", " https://example.com/episode.mp3\n", "episode:a30aa1fd51eb5525"),
        ("", "", ""),
        ("episode-guid", "https://example.com/episode.mp3", "episode:9373b90c819f1507"),
    ],
)
def test_episode_ids_match_earshots_own_vectors(guid: str, enclosure: str, expected: str) -> None:
    assert lp.episode_id(guid, enclosure) == expected


def test_earshots_phone_file_reads_in_full() -> None:
    raw = json.loads((FIXTURES / "device-phone.json").read_text(encoding="utf-8"))
    parsed = lp.DeviceFile.from_dict(raw)
    assert parsed is not None
    assert len(parsed.records) == len(raw["records"])
    assert lp.spoken_device(parsed) == "Jeff's iPhone"
    assert parsed.records[0].id == "episode:d49b8a9525b77556"
    assert parsed.records[0].position_ms == 2_412_000


def test_the_desktop_file_earshot_expects_from_cast_reads_in_full() -> None:
    raw = json.loads((FIXTURES / "device-desktop.json").read_text(encoding="utf-8"))
    parsed = lp.DeviceFile.from_dict(raw)
    assert parsed is not None
    assert {r.id for r in parsed.records} >= {"episode:d49b8a9525b77556"}


# -- C3: one shape of time --------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("2026-11-28T10:15:00Z", "2026-11-28T10:15:00Z"),
        ("2026-11-28T10:15:00.123Z", "2026-11-28T10:15:00Z"),
        ("2026-11-28T10:15:00+00:00", "2026-11-28T10:15:00Z"),
        ("2026-11-28T11:15:00+01:00", "2026-11-28T10:15:00Z"),
        ("2026-11-28T10:15:00", "2026-11-28T10:15:00Z"),
        ("not a time", ""),
        ("", ""),
    ],
)
def test_every_timestamp_is_normalized_before_the_text_comparison(
    given: str, expected: str
) -> None:
    assert lp.normalize_stamp(given) == expected


def test_a_local_offset_is_converted_to_utc_not_relabelled() -> None:
    """``_as_z`` used to reformat ``+01:00`` as if it were already UTC."""
    assert _as_z("2026-11-28T11:15:00+01:00") == "2026-11-28T10:15:00Z"


def test_a_place_past_the_end_is_the_end() -> None:
    record = lp.PlaceRecord.from_dict({
        "id": "episode:x",
        "position_ms": 9_000,
        "duration_ms": 5_000,
        "updated_at": "x",
    })
    assert record is not None and record.position_ms == 5_000


# -- C4 and 6.8: the folder is read defensively, and says so ----------------------


def _write_device(root: Path, name: str, payload: object) -> Path:
    folder = lp.devices_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{name}.json"
    target.write_text(
        json.dumps(payload) if not isinstance(payload, str) else payload, encoding="utf-8"
    )
    return target


def _device(written_at: str, records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "format": lp.FORMAT_ID,
        "device": "phone",
        "device_label": "Jeff's iPhone",
        "app": "earshot/1.2.5",
        "written_at": written_at,
        "records": records,
    }


def test_each_skipped_file_says_why(tmp_path: Path) -> None:
    _write_device(tmp_path, "half", '{"format": "listening-places/1", "records": [')
    _write_device(tmp_path, "later", {"format": "listening-places/2", "records": []})
    big = _write_device(tmp_path, "huge", "{}")
    big.write_bytes(b" " * (lpr.MAX_DEVICE_FILE_BYTES + 1))
    problems: list[str] = []
    assert lp.read_other_devices(tmp_path, "this-pc", problems=problems, now=NOW) == []
    assert len(problems) == 3
    assert any("too large" in p for p in problems)
    assert any("not a complete" in p for p in problems)
    assert any("this version can read" in p for p in problems)


def test_a_device_silent_for_half_a_year_no_longer_competes(tmp_path: Path) -> None:
    _write_device(
        tmp_path,
        "old",
        _device(
            "2026-04-01T00:00:00Z",
            [
                {
                    "id": "episode:a",
                    "kind": "episode",
                    "position_ms": 1,
                    "updated_at": "2026-04-01T00:00:00Z",
                }
            ],
        ),
    )
    problems: list[str] = []
    assert lp.read_other_devices(tmp_path, "this-pc", problems=problems, now=NOW) == []
    assert "180 days" in problems[0] and "Jeff's iPhone" in problems[0]


def test_a_fast_clock_cannot_win_for_ever(tmp_path: Path) -> None:
    _write_device(
        tmp_path,
        "skewed",
        _device(
            "2026-11-28T11:00:00Z",
            [
                {
                    "id": "episode:a",
                    "kind": "episode",
                    "position_ms": 1,
                    "updated_at": "2099-01-01T00:00:00Z",
                },
                {
                    "id": "episode:b",
                    "kind": "episode",
                    "position_ms": 2,
                    "updated_at": "2026-11-28T10:00:00Z",
                },
            ],
        ),
    )
    problems: list[str] = []
    files = lp.read_other_devices(tmp_path, "this-pc", problems=problems, now=NOW)
    stamps = {r.id: r.updated_at for r in files[0].records}
    assert stamps["episode:a"] == "2026-11-28T11:00:00Z"  # the file's own written_at
    assert stamps["episode:b"] == "2026-11-28T10:00:00Z"  # untouched
    assert "clock looks wrong" in problems[0]


def test_cast_subscription_rows_never_cost_the_places(tmp_path: Path) -> None:
    """Rows a reader does not use are skipped one by one (ear.md 6.3, 6.6)."""
    _write_device(
        tmp_path,
        "cast",
        _device(
            "2026-11-28T11:00:00Z",
            [
                {
                    "id": "sub:feed",
                    "kind": "subscription",
                    "feed_url": "https://x",
                    "updated_at": "x",
                },
                {"id": "folder:1", "kind": "folder", "name": "News", "updated_at": "x"},
                {
                    "id": "episode:a",
                    "kind": "episode",
                    "position_ms": 7,
                    "updated_at": "2026-11-28T10:00:00Z",
                },
            ],
        ),
    )
    files = lp.read_other_devices(tmp_path, "this-pc", now=NOW)
    assert [r.id for r in files[0].records] == ["episode:a"]


# -- C1: one index per pass --------------------------------------------------------


def _big_library(count: int) -> PodcastLibrary:
    show = PodcastShow(id="big", title="Big", feed_url="https://feeds.example.com/big")
    show.episodes = [
        PodcastEpisode(guid=f"guid-{i}", title=f"Ep {i}", audio_url=f"https://cdn/{i}.mp3")
        for i in range(count)
    ]
    library = PodcastLibrary()
    library.shows = [show]
    return library


def test_the_index_finds_what_the_scan_finds() -> None:
    library = _big_library(50)
    index = position_sync.episode_index(library)
    for episode in library.shows[0].episodes:
        key = lp.episode_id(episode.guid, episode.audio_url)
        assert index[key] is position_sync._find_episode(library, key)


def test_a_thousand_phone_places_on_a_large_library_sync_quickly(tmp_path: Path) -> None:
    library = _big_library(20_000)
    records = [
        {
            "id": lp.episode_id(f"guid-{i}"),
            "kind": "episode",
            "position_ms": 60_000,
            "updated_at": "2026-11-28T10:00:00Z",
        }
        for i in range(0, 20_000, 20)
    ]
    remote = tmp_path / "remote"
    _write_device(remote, "phone", _device("2026-11-28T10:00:00Z", records))
    started = time.perf_counter()
    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="this-pc",
        device_label="Studio PC",
        library=library,
        save_library=lambda _lib: None,
    )
    elapsed = time.perf_counter() - started
    assert report.applied == 1_000
    assert elapsed < 5.0, f"took {elapsed:.1f}s; the per-record scan took about 9s here"


# -- C2: a finish on the phone is a finish here -----------------------------------


def test_a_phone_finish_does_delete_after_play_and_tells_radio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _big_library(3)
    episode = library.shows[0].episodes[1]
    episode.downloaded_path = str(tmp_path / "ep1.mp3")
    deleted: list[str] = []
    monkeypatch.setattr(
        retention, "on_episode_played", lambda _lib, _show, ep: deleted.append(ep.guid) or True
    )
    shared: list[dict[str, object]] = []
    monkeypatch.setattr(
        "quill.core.podcasts.radio_listens.record_listen",
        lambda _dir, **kw: shared.append(kw),
    )
    remote = tmp_path / "remote"
    _write_device(
        remote,
        "phone",
        _device(
            "2026-11-28T10:00:00Z",
            [
                {
                    "id": lp.episode_id("guid-1"),
                    "kind": "episode",
                    "position_ms": 0,
                    "played": True,
                    "updated_at": "2026-11-28T10:00:00Z",
                }
            ],
        ),
    )
    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="this-pc",
        device_label="Studio PC",
        library=library,
        save_library=lambda _lib: None,
    )
    assert report.applied == 1
    assert episode.played is True
    assert deleted == ["guid-1"]
    assert shared and shared[0]["finished"] is True and shared[0]["app"] == "cast"


def test_an_already_finished_episode_is_not_finished_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _big_library(2)
    position_sync.mark_played(library.shows[0].episodes[0])
    library.shows[0].episodes[0].position_updated_at = "2026-01-01T00:00:00Z"
    calls: list[str] = []
    monkeypatch.setattr(retention, "on_episode_played", lambda *_a: calls.append("x") or True)
    remote = tmp_path / "remote"
    _write_device(
        remote,
        "phone",
        _device(
            "2026-11-28T10:00:00Z",
            [
                {
                    "id": lp.episode_id("guid-0"),
                    "kind": "episode",
                    "position_ms": 0,
                    "played": True,
                    "updated_at": "2026-11-28T10:00:00Z",
                }
            ],
        ),
    )
    sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="this-pc",
        device_label="Studio PC",
        library=library,
        save_library=lambda _lib: None,
    )
    assert calls == []


def test_fixtures_are_a_verbatim_copy_of_earshots(tmp_path: Path) -> None:
    """Refresh them from payown/earshot ``EarshotTests/Fixtures/ListeningPlaces``."""
    for name in ("device-phone.json", "device-desktop.json"):
        copy = tmp_path / name
        shutil.copy(FIXTURES / name, copy)
        assert json.loads(copy.read_text(encoding="utf-8"))["format"] == lp.FORMAT_ID


# -- 6.8, item 2: a second device with the same id --------------------------------


def test_a_device_sharing_this_id_gets_its_file_left_alone(tmp_path: Path) -> None:
    """A restored backup or a copied portable folder: two writers, one id."""
    library = _big_library(2)
    position_sync.remember_position(library.shows[0].episodes[0], 90_000)
    remote = tmp_path / "remote"
    theirs = _write_device(
        remote,
        "this-pc",
        _device(
            "2026-11-28T10:00:00Z",
            [
                {
                    "id": "episode:theirs",
                    "kind": "episode",
                    "position_ms": 5,
                    "updated_at": "2026-11-28T10:00:00Z",
                }
            ],
        ),
    )
    before = theirs.read_bytes()
    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="this-pc",
        device_label="Studio PC",
        library=library,
        save_library=lambda _lib: None,
    )
    assert theirs.read_bytes() == before  # never written over
    assert report.new_device_id and report.new_device_id != "this-pc"
    assert lp.device_file_path(remote, report.new_device_id).is_file()
    assert any("new file of its own" in p for p in report.problems)
