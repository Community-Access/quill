"""GitHub Copilot onboarding dialog (Phase 6 UI, AI-19).

A guided, accessible two-step setup for the Copilot engine:

1. **Install** the Copilot SDK on demand (wheel-only, user-writable, Safe-Mode
   aware) via :func:`quill.core.ai.sdk_install.install_pack`.
2. **Sign in** to GitHub using the OAuth 2.0 device flow — a short, speakable
   code the user types in their browser (:mod:`quill.core.ai.device_login` driven
   by the real :func:`quill.core.ai.oauth_poster.post_form`), with the token
   persisted to the OS secure store and handed to the SDK for the session.

Accessibility: one status text area narrates every step and carries the device
code / verification URL / expiry as live text a screen reader can review; each
action is a labelled button; the dialog follows the modal contract (escape to
Close, focus on the status content, ``Destroy`` on every exit). Heavy work
(install, polling) runs off the UI thread and reports back via ``wx.CallAfter``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from quill.core.ai import copilot_auth
from quill.core.ai.device_login import (
    announce_device_code,
    describe_login_result,
    request_device_code,
    run_device_login,
)
from quill.core.ai.oauth_poster import post_form
from quill.core.ai.sdk_install import (
    install_pack,
    is_pack_importable,
    manual_install_hint,
)
from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control

_PACK_ID = "copilot"


class CopilotOnboardingDialog:
    """Install + sign in to GitHub Copilot, accessibly."""

    def __init__(
        self,
        parent: object,
        show_modal_dialog: Callable,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._show_modal = show_modal_dialog
        self._announce = announce or (lambda _m: None)
        self._grant: object | None = None
        self._busy = False

        self.dialog = wx.Dialog(
            parent,
            title="Set Up GitHub Copilot",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(560, 440))
        self._build_ui()
        self._refresh_state()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "GitHub Copilot runs agentic edits through your GitHub account. "
                "This sets it up in two steps: install the Copilot SDK, then sign "
                "in to GitHub with a short code — no key to paste."
            ),
        )
        intro.Wrap(520)
        root.Add(intro, 0, wx.ALL, 12)

        self.status = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self.status.SetName("Setup status")
        self.status.SetMinSize(wx.Size(520, 160))
        root.Add(self.status, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.gauge = wx.Gauge(self.dialog, range=100)
        self.gauge.SetName("Install progress")
        self.gauge.Hide()
        root.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 12)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.install_btn = wx.Button(self.dialog, label="&Install Copilot SDK")
        self.signin_btn = wx.Button(self.dialog, label="&Sign in to GitHub")
        self.browser_btn = wx.Button(self.dialog, label="Open Sign-in Page in &Browser")
        actions.Add(self.install_btn, 0, wx.RIGHT, 8)
        actions.Add(self.signin_btn, 0, wx.RIGHT, 8)
        actions.Add(self.browser_btn, 0)
        root.Add(actions, 0, wx.ALL, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        self.close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="&Close")
        buttons.Add(self.close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        self.install_btn.Bind(wx.EVT_BUTTON, self._on_install)
        self.signin_btn.Bind(wx.EVT_BUTTON, self._on_sign_in)
        self.browser_btn.Bind(wx.EVT_BUTTON, self._on_open_browser)

    def _set_status(self, message: str, *, announce: bool = True) -> None:
        self.status.SetValue(message)
        if announce:
            self._announce(message)

    def _refresh_state(self) -> None:
        installed = is_pack_importable(_PACK_ID)
        self.install_btn.Enable(not installed and not self._busy)
        self.signin_btn.Enable(installed and not self._busy)
        self.browser_btn.Enable(self._grant is not None)
        if self._busy:
            return
        if not installed:
            self._set_status(
                "Step 1 of 2: install the Copilot SDK. "
                f"You can also run this yourself: {manual_install_hint(_PACK_ID)}",
                announce=False,
            )
        else:
            self._set_status(
                "Step 2 of 2: sign in to GitHub to finish connecting Copilot.",
                announce=False,
            )

    # ------------------------------------------------------------------
    # Step 1: install
    # ------------------------------------------------------------------

    def _on_install(self, _event: object) -> None:
        wx = self._wx
        self._busy = True
        self._refresh_state()
        self.gauge.Show()
        self.dialog.Layout()
        self._set_status("Installing the Copilot SDK. This can take a few minutes...")

        def progress(fraction: float, message: str) -> None:
            wx.CallAfter(self._on_install_progress, fraction, message)

        def worker() -> None:
            try:
                install_pack(_PACK_ID, progress)
                wx.CallAfter(self._on_install_done, None)
            except Exception as exc:  # noqa: BLE001 - surface a clean message
                wx.CallAfter(self._on_install_done, str(exc))

        threading.Thread(  # GATE-40-OK: bounded install worker; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _on_install_progress(self, fraction: float, message: str) -> None:
        self.gauge.SetValue(max(0, min(100, int(fraction * 100))))
        self.status.SetValue(message)

    def _on_install_done(self, error: str | None) -> None:
        self._busy = False
        self.gauge.Hide()
        self.dialog.Layout()
        if error:
            self._set_status(f"Could not install the Copilot SDK: {error}")
        else:
            self._set_status("Copilot SDK installed. Now sign in to GitHub.")
        self._refresh_state()

    # ------------------------------------------------------------------
    # Step 2: device-flow sign-in
    # ------------------------------------------------------------------

    def _on_sign_in(self, _event: object) -> None:
        wx = self._wx
        if not copilot_auth.is_configured():
            self._set_status(
                "Automatic GitHub sign-in is not configured in this build. "
                "Sign in once with the Copilot CLI (run: copilot) or the GitHub "
                "CLI (gh auth login), then choose GitHub Copilot as your engine."
            )
            return
        self._busy = True
        self._refresh_state()
        self._set_status("Contacting GitHub for a sign-in code...")

        def worker() -> None:
            try:
                config = copilot_auth.github_device_flow_config()
                grant = request_device_code(config, poster=post_form)
                wx.CallAfter(self._on_code_ready, config, grant, None)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(self._on_code_ready, None, None, str(exc))

        threading.Thread(  # GATE-40-OK: device-code request; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _on_code_ready(self, config: object, grant: object, error: str | None) -> None:
        wx = self._wx
        if error or grant is None:
            self._busy = False
            self._set_status(f"Could not start GitHub sign-in: {error or 'unknown error'}")
            self._refresh_state()
            return
        self._grant = grant
        message = announce_device_code(grant)  # type: ignore[arg-type]
        self._set_status(message)
        self.browser_btn.Enable(True)

        def worker() -> None:
            try:
                result = run_device_login(
                    config,  # type: ignore[arg-type]
                    grant,  # type: ignore[arg-type]
                    poster=post_form,
                    clock=time.monotonic,
                    sleeper=time.sleep,
                )
                wx.CallAfter(self._on_login_result, result, None)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(self._on_login_result, None, str(exc))

        threading.Thread(  # GATE-40-OK: device-login poll loop; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _on_login_result(self, result: object, error: str | None) -> None:
        self._busy = False
        self._grant = None
        if error or result is None:
            self._set_status(f"Sign-in did not complete: {error or 'unknown error'}")
            self._refresh_state()
            return
        spoken = describe_login_result(result)  # type: ignore[arg-type]
        tokens = getattr(result, "tokens", None) or {}
        token = str(tokens.get("access_token", "")) if isinstance(tokens, dict) else ""
        if token:
            copilot_auth.persist_token(token)
            copilot_auth.apply_token_to_environment(token)
        self._set_status(spoken)
        self._refresh_state()

    def _on_open_browser(self, _event: object) -> None:
        if self._grant is None:
            return
        uri = getattr(self._grant, "verification_uri", "")
        if uri:
            self._wx.LaunchDefaultBrowser(uri)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        self.dialog.CentreOnParent()
        focus_primary_control(self.dialog)
        try:
            self._show_modal(self.dialog)
        finally:
            self.dialog.Destroy()
