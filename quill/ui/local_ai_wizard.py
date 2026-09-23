"""The guided local-AI setup dialog (issue #1558).

A thin renderer over :mod:`quill.core.ai.local_setup`'s status machine: one
window that says where you are in the three-step journey (install Ollama,
download a model, connect QUILL), lights up exactly the button that does the
next step, and does the downloading itself instead of sending the user to a
terminal. The general AI Setup Wizard stays the front door for cloud accounts
and agents; this dialog is the path for "I want it running on this computer",
which the general wizard could only describe.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai import local_setup as ls
from quill.core.ai import onboarding as ob
from quill.ui.dialog_contract import apply_modal_ids

_LOCAL_HOST = "http://localhost:11434"


class LocalAISetupWizard:
    """The Set Up Local AI (Ollama) dialog."""

    def __init__(self, parent: object, *, announce_cb: Callable[[str], None] | None = None) -> None:
        self._announce = announce_cb or (lambda _m: None)
        self._busy = False
        self._status_snapshot = ls.local_ai_setup_status(installed=False, reachable=False)
        self._last_banner = ""
        self._fit = ls.machine_fit()

        self.dialog = wx.Dialog(
            parent,
            title="Set Up Local AI (Ollama)",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(620, 520))

        root = wx.BoxSizer(wx.VERTICAL)
        self._heading = wx.StaticText(self.dialog, label="")
        self._heading.SetName("Local AI setup step")
        font = self._heading.GetFont()
        font.SetPointSize(font.GetPointSize() + 3)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._heading.SetFont(font)
        root.Add(self._heading, 0, wx.ALL, 12)

        # Per-step controls parent directly on the dialog (no intermediate
        # wx.Panel): an empty container panel becomes a stray keyboard tab stop.
        self._body = self.dialog
        self._body_sizer = wx.BoxSizer(wx.VERTICAL)
        root.Add(self._body_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Local AI setup status")
        root.Add(self._status, 0, wx.ALL, 12)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        nav.AddStretchSpacer()
        self._cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="N&ot now")
        nav.Add(self._cancel_btn, 0)
        root.Add(nav, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        # SetMinSize only constrains shrinking; open at the intended size so the
        # read-only prose wraps as full lines rather than a few words per line.
        self.dialog.SetSize(wx.Size(620, 520))
        self.dialog.Centre()
        # Affirmative deliberately ID_CANCEL: Enter must never fire a download.
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CANCEL, cancel_id=wx.ID_CANCEL)

        self._render()
        self._refresh_probe(initial=True)

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    def _alive(self) -> bool:
        """True while the dialog's widgets still exist (#1230): background
        probes/downloads marshal back via wx.CallAfter, and a destroyed wx
        window is falsy."""
        dialog = getattr(self, "dialog", None)
        try:
            return bool(dialog)
        except RuntimeError:
            return False

    # -- helpers --------------------------------------------------------------

    def _set_status(self, message: str) -> None:
        if not self._alive():
            return
        try:
            self._status.SetLabel(message)
        except RuntimeError:
            return
        if message:
            self._announce(message)

    def _set_status_quiet(self, message: str) -> None:
        """Label-only status: progress ticks must not flood the screen reader."""
        if not self._alive():
            return
        try:
            self._status.SetLabel(message)
        except RuntimeError:
            return

    def _add_text(self, text: str, *, grow: bool = False, name: str = "Information") -> wx.TextCtrl:
        """Read-only multiline prose: a screen reader can arrow through a
        read-only edit line by line, which a plain StaticText does not allow."""
        ctrl = wx.TextCtrl(
            self._body,
            value=text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        ctrl.SetName(name)
        if grow:
            self._body_sizer.Add(ctrl, 1, wx.EXPAND | wx.BOTTOM, 8)
        else:
            n_lines = text.count("\n") + 3
            ctrl.SetMinSize(wx.Size(-1, ctrl.GetCharHeight() * n_lines + 14))
            self._body_sizer.Add(ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)
        return ctrl

    # -- rendering ------------------------------------------------------------

    def _render(self) -> None:
        status = self._status_snapshot
        self._body_sizer.Clear(delete_windows=True)
        self._heading.SetLabel(status.headline)

        self._add_text(self._fit.summary, name="Your computer")
        self._add_text(status.next_step, name="What to do next")

        self._install_btn = wx.Button(self._body, label="&Download and Install Ollama")
        self._install_btn.Enable(status.can_install and not self._busy)
        self._body_sizer.Add(self._install_btn, 0, wx.BOTTOM, 4)
        self._install_btn.Bind(wx.EVT_BUTTON, lambda _e: self._download_and_install())

        self._check_btn = wx.Button(self._body, label="Check &Again")
        self._check_btn.Enable(not self._busy)
        self._body_sizer.Add(self._check_btn, 0, wx.BOTTOM, 8)
        self._check_btn.Bind(wx.EVT_BUTTON, lambda _e: self._refresh_probe())

        if status.can_pull:
            self._build_pull_section(status)
        if status.can_finish:
            self._build_finish_section(status)

        self.dialog.Layout()
        # Announce the banner only when the step actually changed -- not on
        # every refresh, and not over the reader reading a control (GATE-13).
        banner = f"{status.headline} {status.next_step}".strip()
        if self._last_banner and banner != self._last_banner:
            self._announce(banner)
        self._last_banner = banner

    def _build_pull_section(self, status: ls.LocalAISetupStatus) -> None:
        from quill.core.ai.providers import recommended_model_guidance

        installed = set(status.models)
        pullable = [g for g in recommended_model_guidance("ollama") if g.model not in installed]
        if not pullable:
            return
        self._body_sizer.Add(
            wx.StaticText(self._body, label="Model to download (the first fits this computer):"),
            0,
            wx.TOP | wx.BOTTOM,
            2,
        )
        self._pull_models = [g.model for g in pullable]
        self._pull_choice = wx.Choice(
            self._body, choices=[f"{g.model} — {g.framing}" for g in pullable]
        )
        self._pull_choice.SetName("Model to download")
        self._pull_choice.SetSelection(0)
        self._body_sizer.Add(self._pull_choice, 0, wx.EXPAND | wx.BOTTOM, 4)
        self._pull_btn = wx.Button(self._body, label="Do&wnload Model")
        self._pull_btn.Enable(not self._busy)
        self._body_sizer.Add(self._pull_btn, 0, wx.BOTTOM, 8)
        self._pull_btn.Bind(wx.EVT_BUTTON, lambda _e: self._pull_selected_model())

    def _build_finish_section(self, status: ls.LocalAISetupStatus) -> None:
        self._body_sizer.Add(
            wx.StaticText(self._body, label="Model QUILL will use:"),
            0,
            wx.TOP | wx.BOTTOM,
            2,
        )
        self._finish_choice = wx.Choice(self._body, choices=list(status.models))
        self._finish_choice.SetName("Model QUILL will use")
        self._finish_choice.SetSelection(0)
        self._body_sizer.Add(self._finish_choice, 0, wx.EXPAND | wx.BOTTOM, 4)
        self._consent = wx.CheckBox(
            self._body,
            label="&Send my text to this local Ollama when I use AI features",
        )
        self._consent.SetValue(False)
        self._body_sizer.Add(self._consent, 0, wx.BOTTOM, 4)
        self._finish_btn = wx.Button(self._body, label="&Use This Model")
        self._finish_btn.Enable(False)
        self._body_sizer.Add(self._finish_btn, 0, wx.BOTTOM, 8)
        self._consent.Bind(
            wx.EVT_CHECKBOX,
            lambda _e: self._finish_btn.Enable(self._consent.IsChecked() and not self._busy),
        )
        self._finish_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish())

    # -- the journey ------------------------------------------------------------

    def _refresh_probe(self, *, initial: bool = False) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_status_quiet("Checking this computer for Ollama...")

        def worker() -> None:
            installed = ls.ollama_executable() is not None
            reachable, models = ls.ollama_probe(_LOCAL_HOST)
            wx.CallAfter(self._on_probed, installed, reachable, tuple(models), initial)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: reachability probe.

    def _on_probed(
        self, installed: bool, reachable: bool, models: tuple[str, ...], initial: bool
    ) -> None:
        if not self._alive():
            return
        self._busy = False
        self._status_snapshot = ls.local_ai_setup_status(
            installed=installed,
            reachable=reachable,
            models=models,
            install_supported=ls.ollama_install_supported(),
        )
        self._render()
        if initial:
            # First paint: the banner IS the news, so say it once here (the
            # change-only rule in _render deliberately skips the first build).
            self._set_status(f"{self._status_snapshot.headline} {self._status_snapshot.next_step}")
        else:
            self._set_status_quiet("")

    def _download_and_install(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._install_btn.Enable(False)
        self._set_status("Downloading Ollama from ollama.com...")
        last_milestone = {"value": -1}

        def progress(fraction: float, _label: str) -> None:
            # Spoken at 25/50/75 only: a percentage on every socket read is
            # noise; three milestones say the thing is moving.
            percent = int(fraction * 100)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone in (25, 50, 75):
                last_milestone["value"] = milestone
                wx.CallAfter(self._set_status, f"Ollama download {milestone} percent")
            else:
                wx.CallAfter(self._set_status_quiet, f"Downloading Ollama: {percent} percent")

        def worker() -> None:
            from quill.core.release_assets import ReleaseAssetError

            try:
                installer = ls.download_ollama_installer(progress=progress)
                ls.launch_ollama_installer(installer)
            except (ReleaseAssetError, OSError) as exc:
                wx.CallAfter(self._on_install_failed, str(exc))
                return
            wx.CallAfter(self._on_installer_started)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: installer download.

    def _on_install_failed(self, message: str) -> None:
        if not self._alive():
            return
        self._busy = False
        self._set_status(f"Could not download Ollama: {message}")
        try:
            self._install_btn.Enable(True)
        except RuntimeError:
            pass

    def _on_installer_started(self) -> None:
        if not self._alive():
            return
        self._busy = False
        self._render()
        self._set_status(
            "The Ollama installer has started. Follow its prompts, and when it "
            "finishes choose Check Again."
        )

    def _pull_selected_model(self) -> None:
        if self._busy:
            return
        idx = self._pull_choice.GetSelection()
        if not (0 <= idx < len(self._pull_models)):
            return
        model = self._pull_models[idx]
        self._busy = True
        self._pull_btn.Enable(False)
        self._set_status(f"Downloading {model}... this can take a while for larger models.")

        def on_progress(text: str) -> None:
            # Label-only (#1230-guarded): per-tick speech would flood the reader.
            wx.CallAfter(self._set_status_quiet, f"Downloading {model}: {text}")

        def worker() -> None:
            ok, message = ob.pull_ollama_model(model, host=_LOCAL_HOST, on_progress=on_progress)
            installed = ls.ollama_executable() is not None
            reachable, models = ls.ollama_probe(_LOCAL_HOST)
            wx.CallAfter(
                self._on_model_pulled, model, ok, message, installed, reachable, tuple(models)
            )

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: model download.

    def _on_model_pulled(
        self,
        model: str,
        ok: bool,
        message: str,
        installed: bool,
        reachable: bool,
        models: tuple[str, ...],
    ) -> None:
        if not self._alive():
            return
        self._busy = False
        if not ok:
            self._set_status(f"Could not download {model}: {message}")
            try:
                self._pull_btn.Enable(True)
            except RuntimeError:
                pass
            return
        self._status_snapshot = ls.local_ai_setup_status(
            installed=installed,
            reachable=reachable,
            models=models,
            install_supported=ls.ollama_install_supported(),
        )
        self._render()
        # After the rebuild, so the success line is the last thing spoken.
        self._set_status(f"{model} is ready.")

    def _finish(self) -> None:
        if self._busy:
            return
        idx = self._finish_choice.GetSelection()
        models = self._status_snapshot.models
        if not (0 <= idx < len(models)):
            return
        model = models[idx]
        self._busy = True
        self._finish_btn.Enable(False)
        self._set_status(f"Connecting QUILL to {model}...")

        def worker() -> None:
            ok, message = ob.verify_model("ollama", model, host=_LOCAL_HOST)
            wx.CallAfter(self._on_finished, model, ok, message)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: connection check.

    def _on_finished(self, model: str, ok: bool, message: str) -> None:
        if not self._alive():
            return
        self._busy = False
        if not ok:
            self._set_status(f"Could not connect to {model}: {message}")
            try:
                self._finish_btn.Enable(self._consent.IsChecked())
            except RuntimeError:
                pass
            return
        ob.apply_on_device_setup(host=_LOCAL_HOST, model=model)
        ob.grant_provider_consent("ollama")
        ob.mark_onboarding_complete()
        self._announce(
            f"Done. QUILL's assistant is {model}, running on this computer. "
            "Nothing you write leaves this machine."
        )
        # EndModal asserts on a dialog shown non-modally (the test harness);
        # Close() is the same gesture there.
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
        else:
            self.dialog.Close()


def run_local_ai_setup(controller: Any) -> None:
    """Open the guided local-AI setup for the host MainFrame.

    Safe Mode refuses before any window opens: the journey is nothing but
    network actions (a probe, two downloads), so there is no reduced version
    of it worth showing.
    """
    import os

    announce = getattr(controller, "_announce", None) or (lambda _m: None)
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        announce(
            "Local AI setup is disabled in Safe Mode. Restart QUILL without "
            "--safe-mode (or unset QUILL_SAFE_MODE) to use network features."
        )
        return
    wizard = LocalAISetupWizard(controller.frame, announce_cb=announce)
    controller._show_modal_dialog(wizard.dialog, "Set Up Local AI (Ollama)")
    wizard.close()
    # AI state may have changed (onboarding completed, provider connected);
    # rebuild the menu the same way the general wizard does.
    rebuild = getattr(controller, "_build_menu", None)
    if callable(rebuild):
        rebuild()
    else:
        refresh = getattr(controller, "_request_menu_refresh", None)
        if callable(refresh):
            refresh()
