"""Feed Credentials prompt + credential cleanup on unsubscribe."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "quill"


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_show_actions_exposes_feed_credentials_prompt() -> None:
    src = _read("ui/podcasts/show_actions.py")
    assert "def feed_credentials_prompt(" in src
    assert "FeedCredentialsDialog" in src
    assert "save_feed_password" in src
    assert "delete_feed_password" in src


def test_unsubscribe_deletes_stored_credentials_everywhere() -> None:
    assert "delete_feed_password(show.id)" in _read("ui/podcasts/show_actions.py")
    assert "delete_feed_password(show.id)" in _read("ui/podcasts/manager_dialog.py")


def test_context_menus_offer_feed_credentials() -> None:
    # Three surfaces, three routes to the same prompt. The standalone app's
    # tree and show_actions.py keep the shared menu helper; the Podcast
    # Manager's show menu became a Quick-Actions-ordered table in 1.1.0, so
    # its entry lives in manager_menus.py and calls the dialog's own handler.
    assert "Feed Cre&dentials..." in _read("ui/podcasts/show_actions.py")
    assert "Feed Cre&dentials..." in _read("apps/podcasts.py")
    menus = _read("ui/podcasts/manager_menus.py")
    assert "Feed Cre&dentials..." in menus
    assert "_on_feed_credentials(show)" in menus
    assert "feed_credentials_prompt(" in _read("ui/podcasts/manager_actions.py")
