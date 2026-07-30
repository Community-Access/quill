"""One-time Spotify network-access consent flag."""

from __future__ import annotations

from pathlib import Path

from quill.core.spotify import consent


def test_consent_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(consent, "app_data_dir", lambda: tmp_path)
    assert consent.load_spotify_consent_complete() is False
    consent.save_spotify_consent_complete()
    assert consent.load_spotify_consent_complete() is True
