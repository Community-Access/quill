"""Build the AI Hub's provider summary and its route to connection settings."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.i18n import _
from quill.ui.dialog_contract import set_accessible_name


def build_provider_panel(
    wx: Any,
    notebook: Any,
    *,
    settings: Any,
    lite_mode: bool,
    app_name: str,
    open_choose: Callable[[], None] | None,
    open_own_key: Callable[[], None] | None,
    on_change_ai: Callable[[object], None],
) -> tuple[object, object]:
    """Build the provider summary shared by QUILL and QUILL Lite."""
    panel = wx.Panel(notebook)
    sizer = wx.BoxSizer(wx.VERTICAL)

    if lite_mode:
        from quill.core.ai.connection_caps import CONNECTION_NAMES, OWN_KEY
        from quill.core.ai.own_key_providers import PROVIDER_NAMES

        connection = str(getattr(settings, "ai_connection", "") or "")
        in_use = CONNECTION_NAMES.get(connection, str(_("not chosen")))
        provider = str(getattr(settings, "ai_own_key_provider", "") or "")
        model = (
            str(getattr(settings, "ai_own_key_model", "") or "")
            if connection == OWN_KEY
            else str(getattr(settings, "ai_copilot_model", "") or "")
            if connection == "copilot"
            else str(getattr(settings, "ai_codex_model", "") or "")
            if connection == "codex"
            else ""
        )
        if connection == OWN_KEY and provider:
            in_use = f"{in_use} ({PROVIDER_NAMES.get(provider, provider)})"
        text = _(
            "The connection selected for {app} is saved in {app}'s settings. "
            "Provider credentials use the shared Quill family credential store. "
            "Change the selected connection in Choose Your AI.\n\n"
            "In use now: {provider}{model}."
        ).format(
            app=app_name,
            provider=in_use,
            model=f", {model}" if model else "",
        )
        button_label = _("Open Choose Your &AI...")
        button_help = _(
            "Closes the AI Hub and opens Choose Your AI, where you can select "
            "the connection QUILL Lite uses."
        )
        button_callback = open_choose
    else:
        from quill.core.ai.own_key import provider_name

        provider = settings.provider or "ollama"
        model = settings.model or ""
        in_use = provider_name(provider) if provider != "off" else str(_("none"))
        text = _(
            "The AI these advanced features use is chosen in Use My Own AI Key, "
            "with the rest of QUILL's AI. Every provider this page used to list is "
            "there: OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Ollama Cloud, "
            "a custom OpenAI-compatible service, and Ollama on this computer, which "
            "needs no key. Saving a provider there makes it the one used here.\n\n"
            "In use now: {provider}{model}."
        ).format(provider=in_use, model=f", {model}" if model and provider != "off" else "")
        button_label = _("Open Use My Own AI &Key...")
        button_help = _(
            "Saves the AI Hub, closes it and opens Use My Own AI Key, where "
            "the provider, its key, its model and its address are chosen."
        )
        button_callback = open_own_key
    sizer.Add(wx.StaticText(panel, label=_("&Provider in use:")), 0, wx.ALL, 6)
    summary = wx.TextCtrl(
        panel, value=str(text), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
    )
    set_accessible_name(summary, str(_("Provider in use")))
    summary.SetHelpText(str(_("Which AI the advanced features use, and where it is chosen now.")))
    sizer.Add(summary, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    change_btn = wx.Button(panel, label=button_label)
    change_btn.SetHelpText(str(button_help))
    change_btn.Enable(button_callback is not None)
    change_btn.Bind(wx.EVT_BUTTON, on_change_ai)
    sizer.Add(change_btn, 0, wx.ALL, 6)
    panel.SetSizer(sizer)
    return panel, summary
