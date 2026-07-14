"""AI Hub "Engines" tab: pick the agentic engine, install / sign in (slice 3).

Extracted from :mod:`quill.ui.ai_hub_dialog` so the Hub stays within its GATE-11
size budget. Lists every engine (Native plus optional SDK packs) from the shared
:func:`quill.core.ai.engines.build_engine_registry`, lets the user set the active
engine (persisted via :mod:`quill.core.ai.quick_switch`), and sets up an
unavailable one inline — GitHub Copilot via its guided onboarding dialog, the
others via an on-demand wheel-only ``install_pack`` off the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.i18n import _


class EnginesPanel:
    """The Engines tab panel and its behaviour."""

    def __init__(
        self,
        notebook: object,
        *,
        parent_dialog: object,
        announce: Callable[[str], None],
        show_modal: Callable,
    ) -> None:
        import wx

        self._wx = wx
        self._parent_dialog = parent_dialog
        self._announce = announce
        self._show_modal = show_modal
        self._targets: list[object] = []
        self._registry: object | None = None

        self.panel = wx.Panel(notebook)
        self._build()
        self._reload()

    def _build(self) -> None:
        wx = self._wx
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.panel,
            label=_(
                "Choose which engine runs QUILL's agent. Native always works, using "
                "the provider you have already connected. Or bring the AI agent you "
                "already pay for: GitHub Copilot, OpenAI (ChatGPT), or Claude. Pick "
                "one and select Set Up to install the connector and sign in with "
                "your account — it runs on your existing subscription, with no extra "
                "key or per-word charge. Whichever engine you pick, QUILL owns every "
                "edit: the agent proposes, you approve a preview, and one keystroke "
                "undoes it."
            ),
        )
        intro.Wrap(620)
        sizer.Add(intro, 0, wx.ALL, 8)

        sizer.Add(wx.StaticText(self.panel, label=_("AI engines:")), 0, wx.LEFT | wx.TOP, 8)
        self.engine_list = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.engine_list.SetName("AI engines")
        sizer.Add(self.engine_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.set_active_btn = wx.Button(self.panel, label=_("Set as &Active Engine"))
        self.setup_btn = wx.Button(self.panel, label=_("Set &Up / Install..."))
        self.refresh_btn = wx.Button(self.panel, label=_("&Refresh"))
        row.Add(self.set_active_btn, 0, wx.RIGHT, 8)
        row.Add(self.setup_btn, 0, wx.RIGHT, 8)
        row.Add(self.refresh_btn, 0)
        sizer.Add(row, 0, wx.ALL, 8)

        self.status = wx.StaticText(self.panel, label="")
        sizer.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.panel.SetSizer(sizer)
        self.set_active_btn.Bind(wx.EVT_BUTTON, self._on_set_active)
        self.setup_btn.Bind(wx.EVT_BUTTON, self._on_setup)
        self.refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reload())

    def _build_registry(self) -> object:
        from quill.core.ai.engines import build_engine_registry

        # Rebuilt on each reload so a just-installed pack is reflected.
        self._registry = build_engine_registry()
        return self._registry

    def _reload(self) -> None:
        from quill.core.ai.quick_switch import list_targets

        targets = list_targets(self._build_registry())
        self._targets = targets
        self.engine_list.Clear()
        for target in targets:
            if target.active:
                state = _("Active")
            elif target.available:
                state = _("Available")
            else:
                state = _("Not installed")
            self.engine_list.Append(f"{target.display_name} — {state}")
        if targets:
            self.engine_list.SetSelection(0)

    def _selected(self) -> object | None:
        idx = self.engine_list.GetSelection()
        if idx < 0 or idx >= len(self._targets):
            return None
        return self._targets[idx]

    def _on_set_active(self, _event: object) -> None:
        from quill.core.ai.quick_switch import announce_switch, set_active

        target = self._selected()
        if target is None:
            return
        chosen = set_active(self._build_registry(), target.harness_id)
        self._reload()
        message = announce_switch(chosen)
        self.status.SetLabel(message)
        self._announce(message)
        if not chosen.available and chosen.harness_id == "copilot":
            self._on_setup(None)

    def _on_setup(self, _event: object) -> None:
        target = self._selected()
        if target is None:
            return
        if target.harness_id == "copilot":
            from quill.ui.copilot_onboarding_dialog import CopilotOnboardingDialog

            CopilotOnboardingDialog(
                self._parent_dialog, self._show_modal, announce=self._announce
            ).show()
            self._reload()
            return
        if target.available:
            self.status.SetLabel(_("{name} is already installed.").format(name=target.display_name))
            return
        self._install_pack(target.harness_id, target.display_name)

    def _install_pack(self, pack_id: str, display_name: str) -> None:
        import threading

        wx = self._wx
        self.setup_btn.Enable(False)
        self.status.SetLabel(_("Installing {name}...").format(name=display_name))
        self._announce(_("Installing {name}").format(name=display_name))

        def worker() -> None:
            from quill.core.ai.sdk_install import install_pack

            try:
                install_pack(pack_id)
                message = _("Installed {name}.").format(name=display_name)
            except Exception as exc:  # noqa: BLE001 - surface a clean message
                message = _("Could not install {name}: {error}").format(
                    name=display_name, error=exc
                )
            wx.CallAfter(self._after_install, message)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: install worker

    def _after_install(self, message: str) -> None:
        self.setup_btn.Enable(True)
        self.status.SetLabel(message)
        self._announce(message)
        self._reload()
