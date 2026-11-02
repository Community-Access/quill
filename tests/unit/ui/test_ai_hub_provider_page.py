"""The AI Hub's Provider list is gone; its page opens Use My Own AI Key (decision 20).

Every provider the Hub listed is a provider in My own key now
(tests/unit/core/ai/test_own_key_providers.py), and choosing one there sets
what the advanced features use. What is left of the Hub's Provider page is a
sentence saying which provider is in use and one button that saves the Hub,
closes it, and opens Use My Own AI Key.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.ui.ai_hub_dialog import AIHubDialog

_SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "ai_hub_dialog.py").read_text(
    encoding="utf-8"
)


def test_the_hub_no_longer_has_a_provider_chooser() -> None:
    for gone in ("_PROVIDER_CHOICES", "_provider_choice", "self._key_ctrl", "_ollama_url_ctrl"):
        assert gone not in _SOURCE, gone
    assert "Open Use My Own AI &Key..." in _SOURCE


def test_open_use_my_own_ai_key_saves_the_hub_then_opens_it_after_closing() -> None:
    events: list[str] = []
    hub = AIHubDialog.__new__(AIHubDialog)
    hub._open_own_key = lambda: events.append("own key")
    hub._own_key_after_close = False
    hub._on_ok = lambda _event: events.append("saved")  # type: ignore[method-assign]

    class _Dialog:
        def Destroy(self) -> None:  # noqa: N802 - wx shape
            events.append("closed")

    hub.dialog = _Dialog()
    hub._show_modal = lambda _dialog, _label: events.append("shown")
    hub._on_open_own_key(None)
    hub.show()
    assert events == ["saved", "shown", "closed", "own key"]


def test_a_plain_close_does_not_open_it() -> None:
    opened: list[str] = []
    hub = AIHubDialog.__new__(AIHubDialog)
    hub._open_own_key = lambda: opened.append("own key")
    hub._own_key_after_close = False

    class _Dialog:
        def Destroy(self) -> None:  # noqa: N802 - wx shape
            pass

    hub.dialog = _Dialog()
    hub._show_modal = lambda _dialog, _label: None
    hub.show()
    assert opened == []


def test_quill_hands_the_hub_its_own_key_command() -> None:
    main_frame = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    assert "open_own_key=self.cmd_ai_own_key" in main_frame


@pytest.fixture
def hub_page(monkeypatch: pytest.MonkeyPatch) -> Any:
    wx = pytest.importorskip("wx")
    from tests.wx_session import shared_wx_app

    shared_wx_app()
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: assistant_ai.AssistantConnectionSettings(
            provider="claude", host="", model="claude-x"
        ),
    )
    frame = wx.Frame(None)
    hub = AIHubDialog.__new__(AIHubDialog)
    hub._wx = wx
    hub._open_own_key = lambda: None
    hub._settings = assistant_ai.load_assistant_connection_settings()
    hub._notebook = wx.Notebook(frame)
    yield hub, hub._build_provider_tab()
    frame.Destroy()


def test_the_provider_page_says_what_is_in_use(hub_page: Any) -> None:
    hub, _panel = hub_page
    text = hub._provider_summary.GetValue()
    assert "In use now: Anthropic Claude, claude-x." in text
    assert "Ollama on this computer" in text
