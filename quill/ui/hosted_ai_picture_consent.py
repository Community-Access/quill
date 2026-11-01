"""The first-time picture consent, asked the same way in every app (codex.md 10B.4).

The words and the bookkeeping are :mod:`quill.core.ai.picture_consent`; this is
the one place the question is shown, so QUILL Studio's Describe a Picture,
Quill Radio's Describe the Video, QUILL Cast's Ask About an Image and
QuillBeacon's Describe a Saved Picture ask it identically. The first picture on
each connection (and each company, for an own key) says where pictures go and
asks Yes or No, No the default; the answer is kept in the app's own AI
settings (``ai_picture_consent``), so it is asked again only when the
connection changes, because then the company changes.

An app whose settings have no ``ai_picture_consent`` list yet is asked every
time rather than never: a consent nobody can remember is a consent asked again.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CAPTION", "ask_picture_consent"]

CAPTION = "Pictures and your AI"


def ask_picture_consent(host: Any, connection: str) -> bool:
    """True when pictures may go on *connection* from *host*'s app; asks once.

    *host* is a ``HostedAiMixin`` adapter: ``_ai_host()`` holds the settings and
    the agent name, ``_ai_service()`` the own key's company, and
    ``_show_message_box`` (or the shared message box) asks.
    """
    import wx

    from quill.core.ai.picture_consent import (
        consent_key,
        consent_sentence,
        given,
        needs_consent,
    )

    app = host._ai_host()
    settings = app.settings
    provider = str(getattr(host._ai_service(), "own_key_provider", "") or "openai")
    key = consent_key(connection, provider)
    consented = list(getattr(settings, "ai_picture_consent", None) or [])
    if not needs_consent(consented, key):
        return True
    name = str(getattr(app, "ai_agent_name", "") or "QUILL")
    message = (
        consent_sentence(name, connection, provider) + " Send pictures you ask about this way?"
    )
    style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
    ask = getattr(host, "_show_message_box", None)
    if callable(ask):
        answer = ask(message, CAPTION, style)
    else:
        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(message, CAPTION, style, host._ai_parent())
    if answer not in (wx.YES, wx.ID_YES):
        return False
    if hasattr(settings, "ai_picture_consent"):
        settings.ai_picture_consent = given(consented, key)
        app.save_settings()
    return True
