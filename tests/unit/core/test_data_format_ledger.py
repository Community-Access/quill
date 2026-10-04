"""Release channels, Phase 0: the data-format registry, the per-machine ledger,
the saved copy taken on joining Beta, and the Update History log.

Recording only -- nothing here decides anything yet (plan 9.3, "start the
clock"). The tests pin that the clock starts, only ever goes up, never breaks a
launch, and that the joined-Beta copy really holds the settings it promises.
"""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.core import data_format_ledger as ledger_mod
from quill.core.data_formats import FORMATS, DataFormat, formats_for
from quill.core.updater import history, snapshots


def test_every_format_id_is_unique_and_reads_what_it_writes() -> None:
    ids = [fmt.id for fmt in FORMATS]
    assert len(ids) == len(set(ids))
    for fmt in FORMATS:
        assert fmt.reads_up_to >= fmt.current, fmt.id
        assert fmt.files, fmt.id


def test_shared_formats_belong_to_every_writer() -> None:
    radio = {fmt.id for fmt in formats_for("radio")}
    cast = {fmt.id for fmt in formats_for("cast")}
    assert "shared.media_bookmarks" in radio and "shared.media_bookmarks" in cast
    assert "radio.favorites" in radio and "radio.favorites" not in cast
    assert {fmt.location for fmt in formats_for("quilllite")} == {"lite_data"}


def test_the_ledger_starts_the_clock_and_only_goes_up(tmp_path: Path) -> None:
    first = (DataFormat("x.thing", "x", ("x.json",), "quill_data", 2, 2),)
    when = datetime(2026, 10, 3, tzinfo=UTC)
    result = ledger_mod.record(tmp_path, first, "x 1.0.0", now=when)
    assert result.high("x.thing") == 2
    raw = json.loads((tmp_path / ledger_mod.LEDGER_NAME).read_text(encoding="utf-8"))
    assert raw["formats"]["x.thing"] == {"high": 2, "by": "x 1.0.0", "at": when.isoformat()}
    # An older build writing version 1 never lowers it.
    older = (DataFormat("x.thing", "x", ("x.json",), "quill_data", 1, 1),)
    assert ledger_mod.record(tmp_path, older, "x 0.9.0").high("x.thing") == 2
    assert ledger_mod.read_ledger(tmp_path).formats["x.thing"].by == "x 1.0.0"


def test_an_ordinary_launch_writes_nothing(tmp_path: Path) -> None:
    fmt = (DataFormat("x.thing", "x", ("x.json",), "quill_data", 1, 1),)
    ledger_mod.record(tmp_path, fmt, "x 1.0.0")
    path = tmp_path / ledger_mod.LEDGER_NAME
    before = path.stat().st_mtime_ns
    ledger_mod.record(tmp_path, fmt, "x 1.0.1")
    assert path.stat().st_mtime_ns == before


def test_an_unreadable_ledger_reads_as_empty(tmp_path: Path) -> None:
    (tmp_path / ledger_mod.LEDGER_NAME).write_text("garbage", encoding="utf-8")
    assert ledger_mod.read_ledger(tmp_path).formats == {}


def test_recording_at_launch_lands_in_the_right_folder(
    quill_data_dir, monkeypatch, tmp_path
) -> None:
    lite = tmp_path / "lite"
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(lite))
    ledger_mod.record_running_build("radio", "3.2.0")
    ledger_mod.record_running_build("quilllite", "1.2.0")
    shared = ledger_mod.read_ledger(Path(quill_data_dir))
    assert shared.high("radio.favorites") == 1 and shared.high("lite.settings") == 0
    assert ledger_mod.read_ledger(lite).high("lite.settings") == 1


def test_recording_never_breaks_a_launch(monkeypatch) -> None:
    def _boom() -> Path:
        raise OSError("no profile")

    monkeypatch.setattr("quill.core.paths.app_data_dir", _boom)
    ledger_mod.record_running_build("quill", "1.0.0")  # must not raise


# -- the joined-Beta copy --------------------------------------------------------------


def test_quill_and_lite_copies_hold_their_settings_files(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "settings.json").write_text('{"a": 1}', encoding="utf-8")
    (data / "keymap.json").write_text("{}", encoding="utf-8")
    (data / "notes.txt").write_text("not settings", encoding="utf-8")
    copy = snapshots.take_snapshot("quilllite", "1.2.0", "joined-beta", data=data)
    assert copy.parent == data / "channel-snapshots"
    assert copy.name.startswith("quilllite-1.2.0-joined-beta-") and copy.suffix == ".zip"
    with zipfile.ZipFile(copy) as archive:
        assert sorted(archive.namelist()) == ["keymap.json", "settings.json"]


def test_radio_and_cast_reuse_their_own_backups(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "radio_favorites.json").write_text("[]", encoding="utf-8")
    (data / "podcasts_library.json").write_text("{}", encoding="utf-8")
    radio = snapshots.take_snapshot("radio", "3.2.0", "joined-beta", data=data)
    cast = snapshots.take_snapshot("cast", "2.0.0", "joined-dev", data=data)
    assert radio.suffix == ".qrbackup" and cast.suffix == ".qcbackup"
    with zipfile.ZipFile(radio) as archive:
        assert "data/radio_favorites.json" in archive.namelist()


def test_the_newest_joined_copy_and_three_others_are_kept(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    for minute in range(5):
        snapshots.take_snapshot(
            "quill",
            "1.0.0",
            "joined-beta",
            data=data,
            now=datetime(2026, 10, 3, 9, minute, tzinfo=UTC),
        )
    copies = [
        p
        for p in (data / "channel-snapshots").glob("quill-*")
        if not p.name.endswith(".ledger.json")
    ]
    # The newest joined copy is the way back from Beta (Phase 4), so it is
    # kept on top of the three newest others.
    assert len(copies) == snapshots.KEEP_PER_APP + 1


def test_a_copy_that_cannot_be_made_raises_a_plain_reason(tmp_path: Path) -> None:
    with pytest.raises(snapshots.SnapshotError) as caught:
        snapshots.take_snapshot("weather", "2.2.0", "joined-beta", data=tmp_path)
    assert "no way to copy settings" in caught.value.reason


# -- Update History ---------------------------------------------------------------------


def test_history_appends_reads_newest_first_and_filters_by_app(tmp_path: Path) -> None:
    path = tmp_path / "update-history.jsonl"
    history.record("radio", "checked", path=path)
    history.record("quill", "channel_changed", channel="beta", path=path)
    history.record("radio", "snapshot_saved", detail="C:/copy.qrbackup", path=path)
    radio = history.read_events("radio", path)
    assert [event.kind for event in radio] == ["snapshot_saved", "checked"]
    assert radio[0].what == "Saved a copy of your settings"
    path.write_text(path.read_text(encoding="utf-8") + "not json\n", encoding="utf-8")
    assert len(history.read_events(None, path)) == 3


def test_history_is_trimmed_to_its_cap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(history, "MAX_EVENTS", 5)
    path = tmp_path / "update-history.jsonl"
    for index in range(8):
        history.record("quill", "checked", detail=str(index), path=path)
    events = history.read_events("quill", path)
    assert len(events) == 5 and events[0].detail == "7"
