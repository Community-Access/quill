"""API-key onboarding dialog for env-var-authenticated SDK harnesses (AI-19
follow-up): OpenAI Agents SDK and Claude Agent SDK, modeled on
:class:`~quill.ui.copilot_onboarding_dialog.CopilotOnboardingDialog`'s shape but
simpler, since these two authenticate with a single pasted key rather than an
OAuth device flow.

Accessibility: one status text area narrates the current state; the key field
is password-masked with an accessible name; Save/Remove/Close are all plain
labelled buttons; the dialog follows the modal contract (escape to Close,
focus on the primary control, ``Destroy`` on every exit).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.ai import harness_credentials as hc
from quill.ui.dialog_contract import apply_modal_ids


class HarnessApiKeyDialog:
    """Add, replace, or remove the API key an SDK harness reads from the
    environment (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``)."""

    def __init__(
        self,
        parent: object,
        pack_id: str,
        display_name: str,
        show_modal_dialog: Callable,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._pack_id = pack_id
        self._display_name = display_name
        self._show_modal = show_modal_dialog
        self._announce = announce or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent,
            title=f"Set Up {display_name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(520, 300))
        self._build_ui()
        self._refresh_state()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)
        env_vars = ", ".join(hc.env_var_names(self._pack_id)) or "an environment variable"

        intro = wx.StaticText(
            self.dialog,
            label=(
                f"{self._display_name} reads its API key from {env_vars}. Paste "
                "your key below and QUILL keeps it in the same secure store your "
                "other AI provider keys use, and applies it for this session "
                "immediately -- no restart needed."
            ),
        )
        intro.Wrap(480)
        root.Add(intro, 0, wx.ALL, 12)

        key_label = wx.StaticText(self.dialog, label="&API key:")
        root.Add(key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.key_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PASSWORD)
        self.key_ctrl.SetName(f"{self._display_name} API key")
        root.Add(self.key_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.status = wx.StaticText(self.dialog, label="")
        self.status.SetName("Setup status")
        self.status.Wrap(480)
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = wx.Button(self.dialog, label="&Save Key")
        self.remove_btn = wx.Button(self.dialog, label="&Remove Key")
        actions.Add(self.save_btn, 0, wx.RIGHT, 8)
        actions.Add(self.remove_btn, 0)
        root.Add(actions, 0, wx.ALL, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        self.close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="&Close")
        buttons.Add(self.close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        self.save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        self.remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)

    def _set_status(self, message: str, *, announce: bool = True) -> None:
        self.status.SetLabel(message)
        self.dialog.Layout()
        if announce:
            self._announce(message)

    def _refresh_state(self) -> None:
        has_key = bool(hc.stored_key(self._pack_id))
        self.remove_btn.Enable(has_key)
        if has_key:
            self._set_status(
                f"A key is already saved for {self._display_name}. Paste a new "
                "one and Save to replace it, or Remove to clear it.",
                announce=False,
            )
        else:
            self._set_status(
                f"No key saved yet for {self._display_name}.", announce=False
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_save(self, _event: object) -> None:
        key = self.key_ctrl.GetValue().strip()
        if not key:
            self._set_status("Paste an API key first.")
            self.key_ctrl.SetFocus()
            return
        if not hc.persist_key(self._pack_id, key):
            self._set_status("Could not save the key to the secure store.")
            return
        hc.apply_key_to_environment(self._pack_id, key)
        self.key_ctrl.SetValue("")
        self._set_status(f"Key saved for {self._display_name} and applied for this session.")
        self._refresh_state()

    def _on_remove(self, _event: object) -> None:
        hc.forget_key(self._pack_id)
        self._set_status(f"Removed the saved key for {self._display_name}.")
        self._refresh_state()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def show(self) -> None:
        try:
            self._show_modal(self.dialog, f"Set Up {self._display_name}")
        finally:
            self.dialog.Destroy()
