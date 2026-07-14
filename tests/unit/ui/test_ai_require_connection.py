"""The keyed-AI choke point offers setup instead of dead-ending silently.

``MainFrame._ai_require_connection`` is the single guard for keyed AI text
features (spell/grammar check, translate, Document Q&A, thesaurus, agent tasks).
When AI is not ready it must offer the setup wizard (an actionable dialog), and
only return None — with a clear status — when the user declines. When AI is
ready it returns the (connection, api_key) pair unchanged.
"""

from __future__ import annotations

import quill.core.assistant_ai as assistant_ai
import quill.ui.ai_setup_wizard as ai_setup_wizard
from quill.ui.main_frame import MainFrame


def _frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._status_messages = []
    frame._set_status = frame._status_messages.append  # type: ignore[method-assign]
    return frame


def test_require_connection_returns_none_with_feedback_when_setup_declined(monkeypatch) -> None:
    monkeypatch.setattr(ai_setup_wizard, "maybe_offer_ai_setup", lambda *_a, **_k: False)
    frame = _frame()

    assert frame._ai_require_connection() is None
    # The dead-end is never silent: it tells the user how to set AI up.
    assert frame._status_messages
    assert "set up" in frame._status_messages[-1].lower()


def test_require_connection_returns_connection_when_ai_ready(monkeypatch) -> None:
    monkeypatch.setattr(ai_setup_wizard, "maybe_offer_ai_setup", lambda *_a, **_k: True)
    conn = assistant_ai.AssistantConnectionSettings(provider="openai")
    monkeypatch.setattr(assistant_ai, "load_assistant_connection_settings", lambda: conn)
    monkeypatch.setattr(assistant_ai, "load_assistant_api_key", lambda: "sk-key")
    frame = _frame()

    result = frame._ai_require_connection()

    assert result is not None
    got_conn, api_key = result
    assert got_conn.provider == "openai"
    assert api_key == "sk-key"
    assert frame._status_messages == []  # no nagging when AI is already usable
