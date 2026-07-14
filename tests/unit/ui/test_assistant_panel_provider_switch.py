"""In-chat provider/model switcher and modeless lifecycle (lightweight, key-free)."""

from __future__ import annotations

import quill.core.ai.onboarding as ob
from quill.ui.assistant_panel import AskQuillChatDialog


def _bare() -> AskQuillChatDialog:
    # Bypass __init__ (which needs a wx dialog); set only what each test touches.
    return AskQuillChatDialog.__new__(AskQuillChatDialog)


def test_switch_provider_list_includes_configured_and_ollama(monkeypatch) -> None:
    monkeypatch.setattr(ob, "configured_cloud_providers", lambda: [("openai", "OpenAI")])
    items = _bare()._switch_provider_list()
    assert ("openai", "OpenAI") in items  # configured cloud providers offered
    # On-device Ollama is always offered (it needs no key).
    assert (ob.ONDEVICE_PROVIDER_OPTION.id, ob.ONDEVICE_PROVIDER_OPTION.name) in items


def test_switch_provider_list_no_duplicate_ollama(monkeypatch) -> None:
    # If Ollama is somehow already in the configured set, it isn't listed twice.
    ollama = (ob.ONDEVICE_PROVIDER_OPTION.id, ob.ONDEVICE_PROVIDER_OPTION.name)
    monkeypatch.setattr(ob, "configured_cloud_providers", lambda: [ollama])
    items = _bare()._switch_provider_list()
    assert items.count(ollama) == 1


def test_modeless_close_runs_callback_then_destroys() -> None:
    dlg = _bare()
    events: list = []
    dlg._on_close_cb = lambda: events.append("restored")

    class _Dialog:
        def Destroy(self) -> None:
            events.append("destroyed")

    dlg.dialog = _Dialog()
    dlg._on_evt_close(None)
    # The menu-restore hook runs first, then the dialog is destroyed.
    assert events == ["restored", "destroyed"]


def test_refresh_active_status_reads_unified_connection(monkeypatch) -> None:
    import quill.core.assistant_ai as aa
    from quill.core.assistant_ai import AssistantConnectionSettings

    dlg = _bare()
    labels: list[str] = []

    class _Status:
        def SetLabel(self, text: str) -> None:
            labels.append(text)

    dlg._active_status = _Status()
    monkeypatch.setattr(
        aa,
        "load_assistant_connection_settings",
        lambda: AssistantConnectionSettings(provider="openai", host="h", model="gpt-4o-mini"),
    )
    dlg._refresh_active_status()
    assert labels and "OpenAI" in labels[-1] and "gpt-4o-mini" in labels[-1]
