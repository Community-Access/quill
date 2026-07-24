"""Feed Credentials dialog: source contracts for accessibility + secrecy."""

from __future__ import annotations

from pathlib import Path

_SRC = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "podcasts" / "feed_credentials_dialog.py"
)


def test_dialog_meets_the_dialog_contract() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "apply_modal_ids(" in src
    assert "show_modal_dialog(" in src


def test_password_field_is_masked_and_controls_are_named() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "wx.TE_PASSWORD" in src
    assert 'SetName("The username this feed requires")' in src
    assert 'SetName("The password this feed requires")' in src


def test_dialog_never_logs_or_prints_the_password() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "print(" not in src
    assert "logging" not in src


def test_result_shape() -> None:
    from quill.ui.podcasts.feed_credentials_dialog import FeedCredentialsResult

    result = FeedCredentialsResult(action="save", username="u", password="p")
    assert (result.action, result.username, result.password) == ("save", "u", "p")
