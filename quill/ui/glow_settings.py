"""GLOW Accessibility settings, as a function of the QUILL frame.

Moved out of ``main_frame_preferences.py`` under GATE-11 so the Preferences
hub could gain Task Recipes and Profiles (qc.md X-02, X-03).
"""

from __future__ import annotations

from typing import Any

from quill.core.settings import save_settings


def open_glow_settings(host: Any) -> None:
    """Open the GLOW accessibility settings (engine toggle + network consent).

    GLOW is enabled by default and runs locally; the optional networked
    features stay off until the user explicitly turns them on here (GLOW-7).
    """
    from quill.ui.web_form import show_web_form

    values = show_web_form(
        host.frame,
        host._wx,
        title="GLOW Accessibility",
        intro=(
            "GLOW is Quill's built-in accessibility engine. It is on by default "
            "and runs entirely on your computer. The optional features below can "
            "use a network connection and are off until you turn them on. Quill "
            "never sends your document anywhere without asking first."
        ),
        fields=[
            {
                "name": "enabled",
                "label": "Enable the GLOW accessibility engine",
                "type": "checkbox",
                "value": getattr(host.settings, "glow_enabled", True),
            },
            {
                "name": "ai_alt_text",
                "label": "Allow optional AI alt-text generation (uses the network)",
                "type": "checkbox",
                "value": getattr(host.settings, "glow_ai_alt_text_consent", False),
            },
            {
                "name": "pii_redaction",
                "label": "Allow optional PII redaction (uses the network)",
                "type": "checkbox",
                "value": getattr(host.settings, "glow_pii_redaction_consent", False),
            },
            {
                "name": "language_processing",
                "label": "Allow optional WCAG language processing (uses the network)",
                "type": "checkbox",
                "value": getattr(host.settings, "glow_language_processing_consent", False),
            },
        ],
    )
    if values is None:
        host._set_status("GLOW settings cancelled")
        return
    host.settings.glow_enabled = bool(values.get("enabled", True))
    host.settings.glow_ai_alt_text_consent = bool(values.get("ai_alt_text"))
    host.settings.glow_pii_redaction_consent = bool(values.get("pii_redaction"))
    host.settings.glow_language_processing_consent = bool(values.get("language_processing"))
    save_settings(host.settings)
    host._set_status("GLOW settings saved")
