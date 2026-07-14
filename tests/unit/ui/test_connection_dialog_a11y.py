"""Source-contract tests for AI Connection dialog and Prompt Studio fixes.

wxPython cannot be imported in headless CI, so these assertions read the UI
source as text and pin the accessibility wiring fixed in issues #121, #122, and
#124:

* #121 -- Provider, Host URL, and Model each expose their own accessible name,
  so a screen reader does not announce the model selector as the URL field.
* #122 -- API key labels and hints use plain language, with no storage jargon
  ("Credential Manager", "DPAPI", "encrypted fallback").
* #124 -- Prompt Studio has a Close button bound to wx.ID_CANCEL so Escape can
  dismiss it (no keyboard trap).
"""

from __future__ import annotations

from pathlib import Path


def _assistant_tools_source() -> str:
    return Path("quill/ui/assistant_tools.py").read_text(encoding="utf-8")


def _menu_source() -> str:
    return Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8")


def _connection_dialog_source() -> str:
    source = _assistant_tools_source()
    start = source.index("class AssistantConnectionDialog")
    return source[start:]


# --- #121: each connection control names itself ------------------------------


def test_connection_controls_each_set_their_own_accessible_name() -> None:
    body = _connection_dialog_source()
    assert 'self.provider.SetName("Provider")' in body
    assert 'self.host.SetName("Host URL")' in body
    assert 'self.model.SetName("Model")' in body


# --- #122: plain-language API key copy ---------------------------------------


def test_connection_dialog_has_no_storage_jargon() -> None:
    body = _connection_dialog_source()
    for term in ("Credential Manager", "DPAPI", "encrypted fallback"):
        assert term not in body, f"connection dialog leaks storage jargon: {term!r}"


def test_connection_dialog_shows_plain_storage_hint() -> None:
    body = _connection_dialog_source()
    assert "provider_api_key_storage_hint()" in body


# Prompt Studio was retired into the unified AI Library; its Escape-close test is
# removed with the dialog.


# --- AI menu consolidation: Model/Connection merged into the AI Hub ----------


def test_ai_model_and_connection_menu_item_removed() -> None:
    # The standalone "AI Model and Connection" and "Forget API Key" menu items
    # were merged into the AI Hub (per-provider config + per-provider Forget key).
    body = _menu_source()
    assert '"AI &Model and Connection..."' not in body
    assert '"&Forget API Key"' not in body
    assert '"AI &Hub..."' in body
