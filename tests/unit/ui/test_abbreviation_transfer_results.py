"""Manage Abbreviations: Import and Export end with the actual result, said once (FUX-04)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import activity
from quill.core.abbreviations import Abbreviation, AbbreviationLibrary
from quill.ui import abbreviation_transfer as transfer
from quill.ui import activity_window


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []

    def _announce(self, message: str, **_kwargs: object) -> None:
        self.said.append(message)


@pytest.fixture(autouse=True)
def _fresh_log() -> None:
    activity.LOG.clear()


def _library(*names: str) -> AbbreviationLibrary:
    return AbbreviationLibrary(
        version=1,
        abbreviations=[Abbreviation(id=n, abbreviation=n, expansion=f"{n} text") for n in names],
    )


def test_import_counts_what_was_already_there_apart_from_what_could_not_be_used() -> None:
    library = _library("brb")
    counts = transfer.merge_imported(
        library,
        [
            {"id": "brb", "abbreviation": "brb", "expansion": "be right back"},
            {"id": "omw", "abbreviation": "omw", "expansion": "on my way"},
            {"id": "x", "abbreviation": "", "expansion": "no trigger"},
            "not an entry",
        ],
    )
    assert counts == transfer.ImportCounts(added=1, already=1, unusable=2)
    assert [a.abbreviation for a in library.abbreviations] == ["brb", "omw"]


def test_import_sentence_names_the_file_and_folder() -> None:
    path = Path("Downloads") / "team.json"
    said = transfer.import_sentence(path, transfer.ImportCounts(added=5, already=2, unusable=1))
    assert said == (
        "Imported 5 abbreviations from team.json in Downloads. 2 were already in your list. "
        "1 entry could not be used: no abbreviation or no text."
    )
    nothing = transfer.import_sentence(path, transfer.ImportCounts(already=1))
    assert nothing == (
        "No abbreviations were added from team.json in Downloads. 1 was already in your list."
    )


def test_export_is_said_with_where_it_went_and_kept_with_open_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "mine.json"
    monkeypatch.setattr(transfer, "_choose", lambda *_a, **_k: target)
    boxes: list[str] = []
    monkeypatch.setattr(transfer, "_error", lambda _p, message, _t: boxes.append(message))
    host = _Host()
    transfer.export_abbreviations(None, _library("brb", "omw"), host)
    assert json.loads(target.read_text(encoding="utf-8"))["abbreviations"][0]["id"] == "brb"
    assert host.said == [f"Exported 2 abbreviations to mine.json in {tmp_path.name}."]
    assert boxes == []
    kept = activity.LOG.latest_important()
    assert kept is not None and activity_window.can_run(kept, activity.OPEN_FOLDER.id)


def test_a_failed_export_says_nothing_was_exported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "missing" / "mine.json"
    monkeypatch.setattr(transfer, "_choose", lambda *_a, **_k: target)
    boxes: list[str] = []
    monkeypatch.setattr(transfer, "_error", lambda _p, message, _t: boxes.append(message))
    host = _Host()
    transfer.export_abbreviations(None, _library("brb"), host)
    assert host.said == []
    assert boxes and boxes[0].startswith("Could not write file:")


def test_import_is_said_and_saved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "team.json"
    source.write_text(
        json.dumps({"abbreviations": [{"id": "omw", "abbreviation": "omw", "expansion": "x"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(transfer, "_choose", lambda *_a, **_k: source)
    written: list[int] = []
    monkeypatch.setattr(
        transfer, "save_abbreviation_library", lambda lib: written.append(len(lib.abbreviations))
    )
    host = _Host()
    assert transfer.import_abbreviations(None, _library("brb"), host) is True
    assert written == [2]
    assert host.said == [f"Imported 1 abbreviation from team.json in {tmp_path.name}."]
