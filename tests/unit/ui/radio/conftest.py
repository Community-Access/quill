"""Fixtures for the Radio window tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _find_streams_last_results_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Find Streams saves its last results when it closes: keep them out of the real profile."""
    folder = tmp_path / "find_streams_last"
    monkeypatch.setattr("quill.ui.radio.find_streams_last._directory", lambda: folder)
    return folder
