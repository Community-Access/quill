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
    sounds, fallback = rows.checkboxes()
    assert sounds.name == SOUNDS_LABEL and sounds.group == GROUP and sounds.value is True
    assert fallback.value is False  # the other ways are off until asked for
    assert "&" not in sounds.name + fallback.name  # no access key: no letter left
    rows.apply([False, True])
    assert history.find_streams_sounds is False and history.find_streams_fallback is True
