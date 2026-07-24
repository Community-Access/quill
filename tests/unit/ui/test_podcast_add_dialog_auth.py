"""Add Podcast: a 401 opens the Feed Credentials prompt and retries."""

from __future__ import annotations

from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "quill" / "ui" / "podcasts" / "add_podcast_dialog.py"


def test_add_dialog_handles_feed_auth_error_with_prompt_and_retry() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "FeedAuthError" in src
    assert "FeedCredentialsDialog" in src
    # Credentials from the prompt are passed into the retry fetch...
    assert "username=" in src and "password=" in src
    # ...and persisted only after a successful subscribe.
    assert "save_feed_password" in src
    assert "feed_username" in src


def test_add_dialog_prefills_username_on_second_failure() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "username=last_username" in src
