"""The Find Streams sounds switch: default on, stored, and a preferences row."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.apps.radio_preferences_find import GROUP, SOUNDS_LABEL, FindRows
from quill.core.radio.history import RadioHistory
from quill.core.radio.history_store import load_history, save_history


def test_the_switch_is_on_by_default_and_round_trips(tmp_path: Path) -> None:
    history = RadioHistory()
    assert history.find_streams_sounds is True
    history.find_streams_sounds = False
    save_history(tmp_path, history)
    assert load_history(tmp_path).find_streams_sounds is False


def test_the_preferences_row_reads_and_writes_it() -> None:
    history = RadioHistory()
    rows = FindRows(SimpleNamespace(_radio_history=history))
    (row,) = rows.checkboxes()
    assert row.name == SOUNDS_LABEL and row.group == GROUP and row.value is True
    assert "&" not in row.name  # no access key: the dialog has no letter left
    rows.apply([False])
    assert history.find_streams_sounds is False
