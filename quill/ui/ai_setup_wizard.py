"""AI Setup Wizard — a gentle, magical first run for QUILL's AI.

A short, friendly, screen-reader-first wizard that takes someone from "I don't know
where to start" to "my AI is ready" in seconds, with no jargon and no dead ends. It
drives the wx-free :mod:`quill.core.ai.onboarding` model: welcome, the one real choice
(how should AI run?), a frictionless configure step, and a celebration of what just
became possible — landing the user in the gentle Basic experience mode by default.

One step is shown at a time (one focus context for screen-reader users), each with a
clear heading announced on arrival. Cloud setup pastes a key and can Test it; the
on-device path points at a local Ollama. Nothing is applied until the user reaches the
configure step's Next, and the whole thing can be cancelled at any point with nothing
lost. Reachable on first AI use and any time from ``AI > Set Up AI``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai import onboarding as ob
from quill.ui.dialog_contract import apply_modal_ids

_STEP_WELCOME = 0
_STEP_PATH = 1
_STEP_CONFIG = 2
_STEP_MODEL = 3  # cloud only: pick the model (default preselected, with reasons)
_STEP_DONE = 4


class AISetupWizard:
    """The AI Setup Wizard dialog."""

    def __init__(
        self,
        parent: object,
        *,
        announce_cb: Callable[[str], None] | None = None,
        open_engines_cb: Callable[[], None] | None = None,
    ) -> None:
        self._announce = announce_cb or (lambda _m: None)
        # Called when the user chose the "use an agent you already pay for" path,
        # to open the AI Hub's Engines tab where the pack install + sign-in live.
        self._open_engines_cb = open_engines_cb
        self._step = _STEP_WELCOME
        self._path = "cloud"
        self._provider = ob.CLOUD_PROVIDER_OPTIONS[0].id
        self._provider_name = ob.CLOUD_PROVIDER_OPTIONS[0].name
        self._model = ""  # the model chosen for the default provider on the model step
        # The local Ollama server address last verified against -- defaults to localhost
        # but can point at another machine on the network (see the Config step's host
        # field). Threaded through verify/finish/model-pull so the whole wizard talks to
        # the same server the user actually confirmed, not a silently different default.
        self._ollama_host = "http://localhost:11434"
        # Providers verified and added during this run, as (id, name). Primed from any
        # already-configured providers so relaunching "Set Up AI" remembers them.
        self._added: list[tuple[str, str]] = []
        self._busy = False
        self._configured = False
        self._prime_from_existing_config()

        self.dialog = wx.Dialog(
            parent,
            title="Set Up AI",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(620, 520))

        root = wx.BoxSizer(wx.VERTICAL)
        self._heading = wx.StaticText(self.dialog, label="")
        self._heading.SetName("AI setup step")
        font = self._heading.GetFont()
        font.SetPointSize(font.GetPointSize() + 3)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._heading.SetFont(font)
        root.Add(self._heading, 0, wx.ALL, 12)

        # Parent the per-step controls directly on the dialog (no intermediate
        # wx.Panel): an empty container panel becomes a stray keyboard tab stop, which
        # is confusing for screen-reader users. ``_body`` aliases the dialog so the
        # render code reads naturally; ``_body_sizer`` is a section of the root sizer we
        # clear and rebuild each step.
        self._body = self.dialog
        self._body_sizer = wx.BoxSizer(wx.VERTICAL)
        root.Add(self._body_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("AI setup status")
        root.Add(self._status, 0, wx.ALL, 12)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        self._back_btn = wx.Button(self.dialog, label="&Back")
        self._next_btn = wx.Button(self.dialog, label="&Next")
        self._cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="Not &now")
        nav.Add(self._back_btn, 0, wx.RIGHT, 6)
        nav.AddStretchSpacer()
        nav.Add(self._cancel_btn, 0, wx.RIGHT, 6)
        nav.Add(self._next_btn, 0)
        root.Add(nav, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        # SetMinSize only constrains shrinking; it does not resize the window, so without
        # this the dialog opens at wx's small default (~400 wide) and the read-only prose
        # wraps into a few words per line — painful to arrow through with a screen reader.
        # Open it at the intended size so each wrapped line is a full line of text.
        self.dialog.SetSize(wx.Size(620, 520))
        self.dialog.Centre()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CANCEL, cancel_id=wx.ID_CANCEL)
        self._back_btn.Bind(wx.EVT_BUTTON, lambda _e: self._go_back())
        self._next_btn.Bind(wx.EVT_BUTTON, lambda _e: self._go_next())

        self._render()

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    # -- helpers --------------------------------------------------------------

    def _prime_from_existing_config(self) -> None:
        """Remember providers/models already configured, so a relaunch shows them.

        Pre-fills the added-providers list with every cloud provider that already has a
        stored key, and defaults the path, default provider, and model to the active
        connection when it is a cloud provider. Best-effort: any read failure just leaves
        the wizard at its first-run defaults.
        """
        try:
            self._added = list(ob.configured_cloud_providers())
            active_id, active_model = ob.active_cloud_selection()
            if not active_id:
                # A local Ollama active connection isn't a "cloud" selection; detect it so
                # an on-device setup is remembered on relaunch too. But the connection
                # settings default to provider="ollama" even when AI has never been
                # configured at all (AssistantConnectionSettings.provider defaults to
                # "ollama", and that default is what a fresh/never-touched settings file
                # loads as) -- so this field alone doesn't prove the user set up Ollama.
                # Confirm a local server actually answers before treating it as already
                # added; otherwise Ollama silently vanishes from the picker on every
                # first run, leaving only key-requiring cloud providers to choose from.
                from quill.core.assistant_ai import load_assistant_connection_settings

                conn = load_assistant_connection_settings()
                if conn.provider.strip().lower() == "ollama":
                    primed_host = conn.host or self._ollama_host
                    reachable, _message, _model = ob.ollama_status(primed_host)
                    if reachable:
                        active_id, active_model = "ollama", conn.model.strip()
                        self._ollama_host = primed_host
            if active_id == "ollama":
                entry = ("ollama", ob.ONDEVICE_PROVIDER_OPTION.name)
                if entry not in self._added:
                    self._added.insert(0, entry)
            if active_id:
                self._path = "cloud"
                opt = ob.cloud_provider_option(active_id)
                if opt is not None:
                    self._provider = opt.id
                    self._provider_name = opt.name
                self._model = active_model
            elif self._added:
                self._path = "cloud"
                self._provider, self._provider_name = self._added[0]
        except Exception:  # noqa: BLE001 - priming is a convenience, never block the wizard
            self._added = []

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        if message:
            self._announce(message)

    def _clear_body(self) -> None:
        self._body_sizer.Clear(delete_windows=True)

    def _add_text(self, text: str, *, grow: bool = False, name: str = "Information") -> wx.TextCtrl:
        """A read-only, multiline, word-wrapped edit control for prose.

        Screen readers can arrow through a read-only edit line by line, which a plain
        StaticText does not allow, so all wizard prose uses this. ``grow`` lets the main
        block fill the step; secondary blocks (hints) get a height that fits the text.
        """
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
        self._clear_body()
        if self._step == _STEP_WELCOME:
            self._render_welcome()
        elif self._step == _STEP_PATH:
            self._render_path()
        elif self._step == _STEP_CONFIG:
            self._render_config()
        elif self._step == _STEP_MODEL:
            self._render_model()
        else:
            self._render_done()
        self._back_btn.Enable(self._step in (_STEP_PATH, _STEP_CONFIG, _STEP_MODEL))
        self._next_btn.SetLabel("&Finish" if self._step == _STEP_DONE else "&Next")
        self._body.Layout()
        self.dialog.Layout()
        self._announce(self._heading.GetLabel())

    def _render_welcome(self) -> None:
        self._heading.SetLabel(ob.WELCOME_TITLE)
        body = self._add_text(ob.WELCOME_BODY, grow=True, name="About QUILL's AI")
        body.SetFocus()

    def _render_path(self) -> None:
        self._heading.SetLabel("How would you like AI to run?")
        self._path_choice = wx.RadioBox(
            self._body,
            label="",
            choices=[p.title for p in ob.ONBOARDING_PATHS],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._path_choice.SetName("How AI should run — pick one; you can change it any time")
        idx = next((i for i, p in enumerate(ob.ONBOARDING_PATHS) if p.id == self._path), 0)
        self._path_choice.SetSelection(idx)
        self._body_sizer.Add(self._path_choice, 0, wx.EXPAND | wx.BOTTOM, 8)
        self._path_detail = self._add_text(
            ob.ONBOARDING_PATHS[idx].detail, grow=True, name="What this means"
        )
        self._path_choice.Bind(wx.EVT_RADIOBOX, self._on_path_changed)
        self._path_choice.SetFocus()

    def _on_path_changed(self, _event: object) -> None:
        idx = self._path_choice.GetSelection()
        path = ob.ONBOARDING_PATHS[idx]
        self._path = path.id
        self._path_detail.SetValue(path.detail)
        self._body.Layout()
        self._announce(f"{path.title}. {path.summary}")

    def _render_config(self) -> None:
        # The provider list now includes on-device Ollama alongside the cloud providers,
        # so there is a single unified "connect a provider" step (no separate path).
        self._render_cloud_config()

    def _render_cloud_config(self) -> None:
        """Add one or more providers (cloud or on-device): pick, verify, add.

        Each verified provider moves into the Added list and out of the provider combo, so
        you can pair up several in one pass; you only need one. Cloud providers take a key;
        on-device Ollama needs none and is checked against your local server. Remove puts a
        provider back. Already-configured providers appear here on relaunch.
        """
        self._heading.SetLabel("Connect your AI providers")
        self._add_text(
            "Add one or more providers. Choose a provider, then Verify and add. Cloud "
            "accounts take an API key (stored securely on this device); on-device Ollama "
            "needs no key and is checked against the Ollama running on your computer. Add as "
            "many as you like — you only need one. You'll pick the default next.",
            name="How to connect your providers",
        )
        self._add_text(
            ob.FREE_PATH_GUIDANCE,
            name="Best free options",
        )

        available = self._available_providers()
        self._body_sizer.Add(wx.StaticText(self._body, label="&Provider:"), 0, wx.BOTTOM, 2)
        self._provider_choice = wx.Choice(self._body, choices=[p.name for p in available])
        self._provider_choice.SetName("AI provider to add")
        if available:
            self._provider_choice.SetSelection(0)
        self._body_sizer.Add(self._provider_choice, 0, wx.EXPAND | wx.BOTTOM, 8)
        self._provider_hint = self._add_text(
            self._cloud_hint(available[0]) if available else "Every provider has been added.",
            name="About this provider",
        )
        self._body_sizer.Add(wx.StaticText(self._body, label="API &key:"), 0, wx.BOTTOM, 2)
        self._key_ctrl = wx.TextCtrl(self._body, style=wx.TE_PASSWORD)
        self._key_ctrl.SetName("API key (not needed for on-device Ollama)")
        self._body_sizer.Add(self._key_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)
        # One click to the right signup page for the selected provider — no hunting for
        # where to get a key. Disabled for on-device Ollama (no key needed).
        self._get_key_btn = wx.Button(self._body, label="&Get API key (opens browser)")
        self._get_key_btn.SetName("Get an API key for the selected provider")
        self._body_sizer.Add(self._get_key_btn, 0, wx.BOTTOM, 8)
        self._get_key_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_get_api_key())
        # Ollama's counterpart to the key field: where to reach it. Shown/enabled only
        # for the local, on-device option -- cloud providers have a fixed host. Defaults
        # to localhost but is editable, so Ollama running on another machine on your
        # network is a first-class, discoverable option instead of a hidden capability.
        self._body_sizer.Add(
            wx.StaticText(self._body, label="Ollama &server address:"), 0, wx.BOTTOM, 2
        )
        self._ollama_host_ctrl = wx.TextCtrl(self._body, value=self._ollama_host)
        self._ollama_host_ctrl.SetName(
            "Ollama server address — localhost for this computer, or another "
            "computer's address on your network"
        )
        self._body_sizer.Add(self._ollama_host_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)
        # Per-provider share consent. Required to add the provider: without it QUILL will
        # not use that provider (no per-chat nagging later — this is the one-time ask).
        self._consent_cb = wx.CheckBox(
            self._body, label=self._consent_label(available[0]) if available else ""
        )
        self._consent_cb.SetName("Allow this provider")
        self._body_sizer.Add(self._consent_cb, 0, wx.EXPAND | wx.BOTTOM, 8)
        self._add_btn = wx.Button(self._body, label="&Verify and add provider")
        self._body_sizer.Add(self._add_btn, 0, wx.BOTTOM, 8)
        if not available:
            self._provider_choice.Enable(False)
            self._key_ctrl.Enable(False)
            self._consent_cb.Enable(False)
            self._add_btn.Enable(False)
            self._get_key_btn.Enable(False)
            self._ollama_host_ctrl.Enable(False)
        elif available[0].local:
            self._key_ctrl.Enable(False)  # on-device needs no key
            self._get_key_btn.Enable(False)  # on-device needs no key
        else:
            self._ollama_host_ctrl.Enable(False)  # cloud providers have a fixed host

        self._body_sizer.Add(wx.StaticText(self._body, label="A&dded providers:"), 0, wx.BOTTOM, 2)
        self._added_list = wx.ListBox(self._body, choices=[name for _id, name in self._added])
        self._added_list.SetName("Added AI providers")
        self._body_sizer.Add(self._added_list, 1, wx.EXPAND | wx.BOTTOM, 8)
        self._remove_btn = wx.Button(self._body, label="&Remove selected")
        # Nothing is selected in a freshly built list, so there is nothing to remove yet;
        # enablement tracks the list's actual selection (see _on_added_list_selection),
        # not merely whether the list is non-empty.
        self._remove_btn.Enable(False)
        self._body_sizer.Add(self._remove_btn, 0, wx.BOTTOM, 8)

        self._provider_choice.Bind(wx.EVT_CHOICE, self._on_provider_changed)
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._verify_and_add())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self._remove_selected())
        self._added_list.Bind(wx.EVT_LISTBOX, self._on_added_list_selection)
        # Always land on the Provider combo, never the API key field: jumping straight
        # into a key field (when the first available provider happens to need one) is
        # disorienting -- the provider choice is the step's actual starting point.
        if available:
            self._provider_choice.SetFocus()
        else:
            self._added_list.SetFocus()

    def _on_added_list_selection(self, _event: object) -> None:
        self._remove_btn.Enable(self._added_list.GetSelection() != wx.NOT_FOUND)

    def _available_providers(self) -> list[Any]:
        """Providers not yet added (on-device Ollama first, then cloud), in catalog order."""
        added_ids = {pid for pid, _name in self._added}
        return [opt for opt in ob.SETUP_PROVIDERS if opt.id not in added_ids]

    def _cloud_hint(self, opt: Any) -> str:
        if opt.local:
            return f"{opt.blurb}\n{opt.key_hint}"
        return f"{opt.blurb}\n{opt.key_hint}\nYour key is stored securely on this device only."

    def _consent_label(self, opt: Any) -> str:
        """The allow-checkbox wording for *opt* — on-device vs off-device differ."""
        if opt.local:
            return (
                f"Allow QUILL to use {opt.name} on this computer for AI actions "
                "(your writing stays on your machine)"
            )
        return f"Allow QUILL to send my writing to {opt.name} when I run an AI action"

    def _on_provider_changed(self, _event: object) -> None:
        available = self._available_providers()
        idx = self._provider_choice.GetSelection()
        if 0 <= idx < len(available):
            opt = available[idx]
            self._provider_hint.SetValue(self._cloud_hint(opt))
            # On-device Ollama needs no key; cloud providers do.
            self._key_ctrl.Enable(not opt.local)
            self._get_key_btn.Enable(not opt.local)
            # The reverse for the host field: only on-device Ollama's address is editable.
            self._ollama_host_ctrl.Enable(opt.local)
            if opt.local:
                self._key_ctrl.SetValue("")
            else:
                self._ollama_host_ctrl.SetValue(self._ollama_host)
            # Consent is per provider: re-label and clear when the choice changes.
            self._consent_cb.SetLabel(self._consent_label(opt))
            self._consent_cb.SetValue(False)
            self._body.Layout()

    def _open_get_api_key(self) -> None:
        """Open the signup/keys page for the currently selected provider."""
        import webbrowser

        available = self._available_providers()
        idx = self._provider_choice.GetSelection()
        if not (0 <= idx < len(available)):
            return
        opt = available[idx]
        url = (opt.signup_url or "").strip()
        if not url:
            self._set_status(f"No signup page is known for {opt.name}.")
            return
        opened = False
        try:
            opened = bool(webbrowser.open(url))
        except Exception:  # noqa: BLE001 - a failed browser open must never crash the wizard
            opened = False
        if opened:
            self._set_status(
                f"Opened {opt.name}'s API key page in your browser. Paste the key here."
            )
        else:
            self._set_status(f"Couldn't open a browser. Get your {opt.name} key at: {url}")

    def _verify_and_add(self) -> None:
        if self._busy:
            return
        available = self._available_providers()
        idx = self._provider_choice.GetSelection()
        if not (0 <= idx < len(available)):
            return
        opt = available[idx]
        provider_id, name = opt.id, opt.name
        if not self._consent_cb.GetValue():
            # No standing consent -> the provider would be blocked at use time. Require it
            # up front so "added" always means "allowed".
            self._set_status(f"Check the allow box to use {name}, then add it.")
            self._consent_cb.SetFocus()
            return
        if opt.local:
            # On-device Ollama: no key; confirm a server is reachable at the entered
            # address (localhost by default, or another machine on the network).
            host = self._ollama_host_ctrl.GetValue().strip() or self._ollama_host
            self._busy = True
            self._set_status(f"Checking for {name} at {host}...")

            def local_worker() -> None:
                ok, message, _model = ob.ollama_status(host)
                wx.CallAfter(self._on_verify_result, provider_id, name, "", ok, message, host)

            threading.Thread(target=local_worker, daemon=True).start()  # GATE-40-OK: local check.
            return
        key = self._key_ctrl.GetValue().strip()
        if not key:
            self._set_status(f"Paste the API key for {name} first.")
            self._key_ctrl.SetFocus()
            return
        self._busy = True
        self._set_status(f"Verifying {name}...")

        def worker() -> None:
            ok, detail = _probe_provider(provider_id, key)
            wx.CallAfter(self._on_verify_result, provider_id, name, key, ok, detail)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: connection probe.

    def _on_verify_result(
        self, provider_id: str, name: str, key: str, ok: bool, detail: str, host: str = ""
    ) -> None:
        self._busy = False
        if not ok:
            # For on-device the detail is already friendly guidance; for cloud it's the
            # provider's error. Lead with the failing provider either way.
            self._set_status(detail or f"Couldn't verify {name}.")
            return
        if provider_id == "ollama" and host:
            # Remember the address that actually answered -- Finish and the model-pull
            # step must keep talking to this server, not silently fall back to localhost.
            self._ollama_host = host
        ob.remember_provider_key(provider_id, key)  # no-op for an empty (on-device) key
        ob.grant_provider_consent(provider_id)  # the allow checkbox was required to get here
        self._added.append((provider_id, name))
        self._render()  # rebuild: combo drops the added one, list gains it
        # Announce after the rebuild so the success line is the last thing spoken.
        self._set_status(f"{name} added. Add another provider, or click Next to continue.")

    def _remove_selected(self) -> None:
        if self._busy:
            return
        idx = self._added_list.GetSelection()
        if idx < 0 or idx >= len(self._added):
            self._set_status("Select a provider in the Added list to remove.")
            return
        provider_id, name = self._added.pop(idx)
        ob.forget_provider_key(provider_id)
        self._render()
        self._set_status(f"{name} removed. It's back in the provider list.")

    def _render_model(self) -> None:
        """Cloud-only: choose the default provider (from those added) and its model.

        The default provider is one of the providers added on the previous step; a model
        combo offers recommended ids (editable, so any id can be typed) and a read-only,
        screen-reader-navigable description explains the selected model and updates live.
        On relaunch the previously configured model is preselected.
        """
        self._heading.SetLabel("Choose your default provider and model")
        # Make sure the default provider is one that was actually added.
        added_ids = [pid for pid, _name in self._added]
        if self._provider not in added_ids and self._added:
            self._provider, self._provider_name = self._added[0]

        self._body_sizer.Add(wx.StaticText(self._body, label="Default &provider:"), 0, wx.BOTTOM, 2)
        self._model_provider_choice = wx.Choice(
            self._body, choices=[name for _id, name in self._added]
        )
        self._model_provider_choice.SetName("Default AI provider")
        if added_ids:
            self._model_provider_choice.SetSelection(added_ids.index(self._provider))
        self._body_sizer.Add(self._model_provider_choice, 0, wx.EXPAND | wx.BOTTOM, 8)

        self._body_sizer.Add(wx.StaticText(self._body, label="&Model:"), 0, wx.BOTTOM, 2)
        self._model_combo = wx.ComboBox(self._body, style=wx.CB_DROPDOWN)
        self._model_combo.SetName("Model — choose a suggestion or type a model id")
        self._body_sizer.Add(self._model_combo, 0, wx.EXPAND | wx.BOTTOM, 8)
        self._list_models_btn = wx.Button(self._body, label="&List all available models")
        self._body_sizer.Add(self._list_models_btn, 0, wx.BOTTOM, 8)

        self._model_desc = self._add_text("", name="About this model")

        self._model_provider_choice.Bind(wx.EVT_CHOICE, self._on_model_provider_changed)
        self._model_combo.Bind(wx.EVT_COMBOBOX, self._on_model_changed)
        self._model_combo.Bind(wx.EVT_TEXT, self._on_model_changed)
        self._list_models_btn.Bind(wx.EVT_BUTTON, lambda _e: self._list_models())

        self._populate_models(select=self._model)
        self._model_combo.SetFocus()

        if self._provider == "ollama":
            self._build_ollama_pull_section()

    def _build_ollama_pull_section(self) -> None:
        """Let a local-Ollama user pull a model right here, instead of a terminal.

        Shows the curated recommendations (``recommended_model_guidance``) not yet
        installed on the server at ``self._ollama_host``; picking one and clicking Pull
        downloads it via Ollama's own streaming API (``ob.pull_ollama_model``) with live
        progress, then rebuilds the step so the Model combo above offers it directly.
        """
        from quill.core.ai.providers import recommended_model_guidance

        installed = set(ob.ollama_installed_models(self._ollama_host))
        pullable = [g for g in recommended_model_guidance("ollama") if g.model not in installed]

        self._body_sizer.Add(
            wx.StaticText(self._body, label="&Pull a model (downloads it to this computer):"),
            0,
            wx.TOP | wx.BOTTOM,
            2,
        )
        if not pullable:
            self._add_text(
                "Every recommended model is already installed."
                if installed
                else "Could not reach Ollama to check installed models.",
                name="Pull a model",
            )
            return
        self._pull_models = [g.model for g in pullable]
        self._pull_choice = wx.Choice(
            self._body, choices=[f"{g.model} — {g.framing}" for g in pullable]
        )
        self._pull_choice.SetName("Model to pull")
        self._pull_choice.SetSelection(0)
        self._body_sizer.Add(self._pull_choice, 0, wx.EXPAND | wx.BOTTOM, 4)
        self._pull_btn = wx.Button(self._body, label="Pu&ll model")
        self._body_sizer.Add(self._pull_btn, 0, wx.BOTTOM, 8)
        self._pull_btn.Bind(wx.EVT_BUTTON, lambda _e: self._pull_selected_model())

    def _pull_selected_model(self) -> None:
        if self._busy:
            return
        idx = self._pull_choice.GetSelection()
        if not (0 <= idx < len(self._pull_models)):
            return
        model = self._pull_models[idx]
        host = self._ollama_host
        self._busy = True
        self._pull_btn.Enable(False)
        self._set_status(f"Pulling {model}... this can take a while for larger models.")

        def on_progress(text: str) -> None:
            wx.CallAfter(self._status.SetLabel, f"Pulling {model}: {text}")

        def worker() -> None:
            ok, message = ob.pull_ollama_model(model, host=host, on_progress=on_progress)
            wx.CallAfter(self._on_model_pulled, model, ok, message)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: model download.

    def _on_model_pulled(self, model: str, ok: bool, message: str) -> None:
        self._busy = False
        if not ok:
            self._set_status(f"Could not pull {model}: {message}")
            if getattr(self, "_pull_btn", None) is not None:
                self._pull_btn.Enable(True)
            return
        self._model = model
        self._render()  # rebuild: the pulled model is now installed and preselected
        # Announce after the rebuild so the success line is the last thing spoken.
        self._set_status(f"{model} is ready and selected.")

    def _list_models(self) -> None:
        """Fetch every model the chosen provider exposes and load them into the combo.

        For Ollama this is the locally installed models; for cloud providers, the account's
        available models. Runs off the UI thread; the curated suggestions remain the default
        until the full list arrives.
        """
        if self._busy:
            return
        provider_id, name = self._provider, self._provider_name
        host = self._ollama_host if provider_id == "ollama" else ""
        self._busy = True
        self._set_status(f"Listing models for {name}...")

        def worker() -> None:
            models, error = ob.list_provider_models(provider_id, host=host)
            wx.CallAfter(self._on_models_listed, models, error)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: model discovery.

    def _on_models_listed(self, models: list[str], error: str) -> None:
        self._busy = False
        if not models:
            self._set_status(error or f"No models were returned for {self._provider_name}.")
            return
        current = self._model_combo.GetValue().strip()
        self._model_combo.Set(models)
        self._model_combo.SetValue(current if current in models else models[0])
        self._update_model_description()
        self._set_status(f"Loaded {len(models)} models — choose one from the Model list.")

    def _populate_models(self, *, select: str = "") -> None:
        """Fill the model combo with suggestions for the current provider and describe one.

        Preference order for the preselected model: an explicit ``select``, then the model
        already stored for this provider (so a relaunch remembers it), then the provider's
        recommended default.
        """
        from quill.core.ai.providers import (
            default_model_for_provider,
            recommended_model_guidance,
            recommended_models_for_provider,
        )

        self._model_guidance = list(recommended_model_guidance(self._provider))
        suggestions = recommended_models_for_provider(self._provider)
        self._model_combo.Set(suggestions)
        # The recommended default is the first guidance entry — which now leads with a
        # strong *free* model for OpenRouter, so the free path is preselected. Fall back to
        # the provider's default only if guidance is empty.
        recommended_default = (
            self._model_guidance[0].model
            if self._model_guidance
            else default_model_for_provider(self._provider)
        )
        chosen = select.strip() or ob.stored_provider_model(self._provider) or recommended_default
        self._model_combo.SetValue(chosen)
        self._update_model_description()

    def _model_description(self, model: str) -> str:
        default_model = self._default_model_for_current_provider()
        location = "Runs locally on your device" if self._provider == "ollama" else "Cloud-hosted"
        cost = self._cost_note(model)
        for g in self._model_guidance:
            if g.model == model:
                rec = " Recommended default." if g.model == default_model else ""
                return (
                    f"{g.model} — {g.framing}. {g.reason} {location} via "
                    f"{self._provider_name}.{cost}{rec}"
                )
        if model:
            return (
                f"{model} — {location} via {self._provider_name}.{cost} QUILL will use this "
                "exact model id; make sure your account or device actually has it (for local "
                f"Ollama, run 'ollama pull {model}' first)."
            )
        return "Choose a suggested model, list all available models, or type a model id."

    def _cost_note(self, model: str) -> str:
        """A spoken 'Free' / 'Local, free' cue for the selected model, else ''.

        Local models are always free; cloud models are flagged free when the free
        catalog classifies them so (OpenRouter ``:free`` or zero-priced).
        """
        if not model:
            return ""
        if self._provider == "ollama":
            return " Free (on-device)."
        from quill.core.ai.free_models import is_free_model

        return " Free." if is_free_model(model, provider=self._provider) else ""

    def _default_model_for_current_provider(self) -> str:
        from quill.core.ai.providers import default_model_for_provider

        return default_model_for_provider(self._provider)

    def _update_model_description(self) -> None:
        if getattr(self, "_model_desc", None) is not None:
            self._model_desc.SetValue(self._model_description(self._model_combo.GetValue().strip()))
            self._body.Layout()

    def _on_model_provider_changed(self, _event: object) -> None:
        idx = self._model_provider_choice.GetSelection()
        if 0 <= idx < len(self._added):
            self._provider, self._provider_name = self._added[idx]
            self._model = ""  # let the new provider's stored/default model lead
            self._populate_models()

    def _on_model_changed(self, _event: object) -> None:
        self._update_model_description()

    def _selected_model(self) -> str:
        """The model id from the combo: a typed id or the selected suggestion."""
        return self._model_combo.GetValue().strip()

    def _render_done(self) -> None:
        self._heading.SetLabel("You're all set")
        lines = ob.celebration_lines(self._path, provider_name=self._provider_name)
        text = self._add_text("\n".join(lines), grow=True, name="You're all set")
        if self._path != "skip":
            self._basic_cb = wx.CheckBox(
                self._body, label="Keep it simple — show only the essentials (Basic mode)"
            )
            self._basic_cb.SetName("Keep AI simple (Basic mode)")
            self._basic_cb.SetValue(True)
            self._body_sizer.Add(self._basic_cb, 0, wx.TOP, 8)
            self._basic_cb.SetFocus()
        else:
            text.SetFocus()

    # -- navigation -----------------------------------------------------------

    def _go_back(self) -> None:
        if self._busy:
            return
        if self._step == _STEP_MODEL:
            self._step = _STEP_CONFIG
        elif self._step == _STEP_CONFIG:
            self._step = _STEP_PATH
        elif self._step == _STEP_PATH:
            self._step = _STEP_WELCOME
        self._set_status("")
        self._render()

    def _go_next(self) -> None:
        if self._busy:
            return
        if self._step == _STEP_WELCOME:
            self._step = _STEP_PATH
            self._render()
            return
        if self._step == _STEP_PATH:
            if self._path in ("skip", "agent"):
                # The agent path finishes here: setting up an engine you already
                # pay for happens on the AI Hub Engines tab, which the done step
                # opens for you (no provider/key/model config in the wizard).
                self._step = _STEP_DONE
            else:
                self._step = _STEP_CONFIG
            self._set_status("")
            self._render()
            return
        if self._step == _STEP_CONFIG:
            # Providers (cloud or on-device) are verified and stored as they're added; just
            # require at least one before moving to the default-provider/model step.
            if not self._added:
                self._set_status(
                    "Add at least one provider (Verify and add), or go Back to pick a "
                    "different option."
                )
                return
            self._step = _STEP_MODEL
            self._set_status("")
            self._render()
            return
        if self._step == _STEP_MODEL:
            self._model = self._selected_model()
            if not self._model:
                self._set_status("Choose or enter a model first.")
                return
            if self._provider != "ollama" and not ob.stored_provider_key(self._provider):
                # Safety net for keyed providers: no stored key. Send the user back to add
                # it; nothing is lost. (On-device Ollama needs no key, so it's exempt.)
                self._step = _STEP_CONFIG
                self._set_status(f"Add your {self._provider_name} key first.")
                self._render()
                return
            # Verify the *chosen* model actually responds before saving it as active — a
            # model that isn't installed/available is the usual cause of a chat that hangs.
            self._verify_then_finish()
            return
        # _STEP_DONE -> finish
        self._finish()

    def _verify_then_finish(self) -> None:
        if self._busy:
            return
        provider_id, name, model = self._provider, self._provider_name, self._model
        self._busy = True
        self._set_status(f"Checking that {model} responds on {name}...")

        host = self._ollama_host if provider_id == "ollama" else ""

        def worker() -> None:
            ok, detail = ob.verify_model(provider_id, model, host=host)
            wx.CallAfter(self._on_model_verified, ok, detail)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: model check.

    def _on_model_verified(self, ok: bool, detail: str) -> None:
        self._busy = False
        if not ok:
            self._set_status(
                f"Couldn't get a response from {self._model} on {self._provider_name}: "
                f"{detail} Choose another model or List all available models, then try again."
            )
            return
        if self._provider == "ollama":
            ob.apply_on_device_setup(host=self._ollama_host, model=self._model)
        else:
            ob.apply_cloud_setup(
                self._provider, ob.stored_provider_key(self._provider), model=self._model
            )
        # Guarantee the provider just committed as active is allowed. New providers were
        # consented via the add-step checkbox; this also covers one configured before the
        # consent step existed, so finishing setup never leaves the active provider blocked.
        ob.grant_provider_consent(self._provider)
        self._configured = True
        self._step = _STEP_DONE
        self._set_status("")
        self._render()

    def _finish(self) -> None:
        if self._path != "skip" and getattr(self, "_basic_cb", None) is not None:
            ob.save_experience_mode(
                ob.EXPERIENCE_BASIC if self._basic_cb.GetValue() else ob.EXPERIENCE_ADVANCED
            )
        ob.mark_onboarding_complete()
        open_engines = self._path == "agent" and self._open_engines_cb is not None
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
        # Hand off to the AI Hub Engines tab after the wizard closes, so the user
        # lands exactly where the pack install + sign-in happen. Deferred with
        # CallAfter: opening the modal AI Hub synchronously here would nest it
        # inside the wizard's still-unwinding modal handler (#801 review).
        if open_engines:

            def _hand_off() -> None:
                try:
                    self._open_engines_cb()
                except Exception:  # noqa: BLE001 - a hand-off failure must not crash setup
                    self._announce("Open AI > AI Hub > Engines to connect your agent.")

            call_after = getattr(wx, "CallAfter", None)
            if callable(call_after):
                call_after(_hand_off)
            else:  # stub wx in unit tests
                _hand_off()


def _probe_provider(provider: str, api_key: str) -> tuple[bool, str]:
    """Quick, contained connection check for a provider + key. Never raises."""
    try:
        import dataclasses

        from quill.core.ai.provider_backend import ProviderChatBackend
        from quill.core.ai.providers import default_host_for_provider, default_model_for_provider
        from quill.core.assistant_ai import AssistantConnectionSettings

        settings = AssistantConnectionSettings(
            provider=provider,
            host=default_host_for_provider(provider),
            model=default_model_for_provider(provider),
        )
        backend = ProviderChatBackend(settings=dataclasses.replace(settings), api_key=api_key)
        reply = backend.respond("Reply with exactly one word: ok")
        return (bool(reply and reply.strip()), "")
    except Exception as exc:  # noqa: BLE001 - report the reason, never crash the UI
        return (False, str(exc))


def maybe_offer_ai_setup(controller: Any, *, reason: str = "") -> bool:
    """If AI isn't ready, gently offer the setup wizard at a high-intent moment.

    Returns True when AI is usable afterward (on AND actually configured), so the caller
    can continue; False when it stays unusable (the user declined, finished without
    enabling, or a deliberate skip is left in place). "Usable" means the master switch is
    on AND the active connection is ready — saving us from the old trap where AI was
    "enabled" by default but unconfigured, so the caller proceeded into a request that
    failed with "no key / authentication failed" instead of getting this on-ramp.
    """
    from quill.core.ai.model_manager import load_ai_enabled
    from quill.core.ai.onboarding import ai_connection_ready, ai_needs_setup

    if load_ai_enabled() and ai_connection_ready():
        return True
    # Don't nag a user who deliberately turned AI off and finished setup; but always offer
    # when AI is on yet unconfigured (they clicked an AI action and otherwise just fail).
    if not load_ai_enabled() and not ai_needs_setup():
        return False
    prompt = (f"{reason}\n\n" if reason else "") + (
        "Would you like to set up AI now? It only takes a few seconds, and you can "
        "choose a private on-device option or connect an account."
    )
    dlg = wx.MessageDialog(controller.frame, prompt, "Set Up AI", wx.YES_NO | wx.ICON_QUESTION)
    apply_modal_ids(dlg, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
    try:
        yes = dlg.ShowModal() == wx.ID_YES
    finally:
        dlg.Destroy()
    if not yes:
        return False
    run_ai_setup_wizard(controller)
    return load_ai_enabled() and ai_connection_ready()


def run_ai_setup_wizard(controller: Any) -> None:
    """Open the AI Setup Wizard for the host MainFrame (keeps main_frame thin)."""
    _open_engines = getattr(controller, "open_ai_hub", None)
    wizard = AISetupWizard(
        controller.frame,
        announce_cb=getattr(controller, "_announce", None),
        open_engines_cb=(lambda: _open_engines(initial_page="Engines"))
        if callable(_open_engines)
        else None,
    )
    controller._show_modal_dialog(wizard.dialog, "Set Up AI")
    wizard.close()
    # Rebuild the menu so Basic/Advanced visibility and the new AI state take effect.
    # A plain contextual refresh only enables/disables existing items; the agentic
    # entries are gated at build time on is_basic_mode(), so the whole menu must be
    # rebuilt for the wizard's "keep it simple" choice to add or hide them.
    rebuild = getattr(controller, "_build_menu", None)
    if callable(rebuild):
        rebuild()
    else:
        refresh = getattr(controller, "_request_menu_refresh", None)
        if callable(refresh):
            refresh()
