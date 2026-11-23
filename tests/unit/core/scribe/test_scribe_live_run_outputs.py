"""A live run's own record: QUILL asked correctly and collected everything.

Runs only on a live run's folder (it has ``run.json``; Pneuma's corpus does
not), through ``python -m quill.tools.scribe_check``. Three things, each
about QUILL rather than about Scribe's quality (scribe-test-plan.md 5.1-5.2):

* every format asked of an upload that finished was collected, once, under
  our name, in the layout's folder for it;
* each upload ended as planned: the web page refused before anything was
  sent, the text named ``.pdf`` refused by Scribe, everything else done;
* the settings QUILL sent show in what came back where the file itself says
  so: a BRF is as wide as the cells asked for, and a 2x voice is shorter.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from quill.tools.scribe_live.facts import brf_facts, mp3_facts
from tests.unit.core.scribe import corpus

pytestmark = corpus.needs_corpus


def _record() -> dict[str, Any] | None:
    folder = corpus.full_corpus()
    if folder is None or not (folder / "run.json").is_file():
        return None
    data = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _uploads() -> list[object]:
    record = _record()
    if record is None:
        return []
    return [pytest.param(entry, id=entry["name"]) for entry in record.get("uploads", [])]


@pytest.fixture
def folder() -> Path:
    return corpus.require_full()


@pytest.mark.parametrize("entry", _uploads())
def test_the_upload_ended_as_planned_and_everything_was_collected(
    entry: dict[str, Any], folder: Path, record_property: Callable[[str, object], None]
) -> None:
    record_property("scribe_app", "Scribe request and collection")
    record_property("scribe_format", "general")
    if entry["state"] == "not run":
        pytest.skip("the run stopped before this upload")
    assert entry.get("outcome") == "as planned", f"{entry['name']}: {entry.get('message')}"
    files = entry.get("files") or {}
    if entry["expect"] == "converts":
        assert sorted(files) == sorted(c["format"] for c in entry["conversions"])
    for relative in files.values():
        assert (folder / relative).is_file(), f"{relative} is not where run.json says"


@pytest.mark.parametrize("entry", _uploads())
def test_the_braille_is_as_wide_as_the_cells_asked_for(
    entry: dict[str, Any], folder: Path, record_property: Callable[[str, object], None]
) -> None:
    record_property("scribe_app", "Scribe request and collection")
    record_property("scribe_format", "brf")
    relative = (entry.get("files") or {}).get("brf")
    if not relative:
        pytest.skip("no BRF in this upload")
    cells = int(entry["settings"]["braille_cells_per_line"])
    widest = brf_facts((folder / relative).read_bytes())["max_cells"]
    assert 0 < widest <= cells, f"lines are {widest} cells; {cells} were asked for"


def test_a_faster_voice_makes_a_shorter_mp3(
    folder: Path, record_property: Callable[[str, object], None]
) -> None:
    record_property("scribe_app", "Scribe request and collection")
    record_property("scribe_format", "mp3")
    record = _record()
    if record is None:
        pytest.skip("not a live run's folder")
    pairs = 0
    for entry in record["uploads"]:
        fast = (entry.get("files") or {}).get("mp3")
        if not fast or float(entry["settings"].get("tts_rate", 1.0)) != 2.0:
            continue
        base = folder / "mp3" / f"{entry['stem']}.mp3"
        if not base.is_file():
            continue
        fast_s = mp3_facts(folder / fast).get("seconds")
        base_s = mp3_facts(base).get("seconds")
        if fast_s and base_s:
            pairs += 1
            assert fast_s < base_s * 0.85, f"{fast}: {fast_s} s, the 1x one {base_s} s"
    if not pairs:
        pytest.skip("this run has no 2x MP3 beside a 1x one")
