"""AI Model settings: choose which on-device model Quill uses.

Defaults to "Recommended" (picked from the machine's RAM). The chosen model is
downloaded automatically (no manual file handling). Accessible; download runs
off the UI thread.
"""

from __future__ import annotations

import threading

from quill.core.ai.model_manager import (
    MODELS,
    ensure_model,
    is_downloaded,
    load_model_choice,
    recommended_id,
    resolve_spec,
    save_model_choice,
    total_ram_gb,
)
from quill.core.ai.model_tiers import (
    TIER_FAST,
    TIER_STRONG,
    active_tier_id,
    assign_model_to_tier,
    load_tiers,
    switch_active_tier,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


def _uses_foundation_models() -> bool:
    """True on a Mac where Quill uses Apple Foundation Models (Apple Intelligence)
    — there's no GGUF model to choose/download there."""
    import sys

    if sys.platform != "darwin":
        return False
    try:
        from quill.core.ai.foundation_models import FoundationModelsBackend

        return bool(FoundationModelsBackend().is_available()[0])
    except Exception:  # noqa: BLE001
        return False


class AIModelDialog:
    def __init__(self, parent: object, announce=None, open_connection=None) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._open_connection = open_connection

        self.dialog = wx.Dialog(
            parent, title="AI Model & Connection", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize((560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        wrap = 520

        def add_help(text: str) -> None:
            label = wx.StaticText(self.dialog, label=text)
            label.Wrap(wrap)
            root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        self._fm = _uses_foundation_models()
        self.choice = None
        self.download_button = None
        self.status = None
        self.tier_choice = None
        self.tier_model_choices: dict[str, object] = {}
        self.tier_status = None
        self._tier_order = (TIER_FAST, TIER_STRONG)
        self._tier_model_ids = ["auto", *MODELS.keys()]

        if self._fm:
            # macOS: Quill uses Apple Foundation Models — no GGUF model to pick.
            add_help(
                "On this Mac, Quill uses Apple Intelligence — Apple's on-device "
                "Foundation Models. It runs locally, stays private, and is built into "
                "macOS, so there's no model to choose or download."
            )
        else:
            add_help(
                "Quill includes an on-device AI model that runs entirely on your computer — "
                "private, offline, and free, with no account or setup. Choose one below; it "
                "downloads automatically the first time you use it."
            )
            rec = recommended_id()
            root.Add(
                wx.StaticText(
                    self.dialog,
                    label=f"This computer has about {total_ram_gb():.0f} GB of RAM.\n"
                    f"Recommended model: {MODELS[rec].name}.",
                ),
                0,
                wx.ALL,
                12,
            )
            # Machine-aware upgrade hint (Phase 3): when the saved choice is a smaller
            # model than this machine can comfortably run, surface a one-step, spoken
            # suggestion. Never auto-downloads — the user still picks below.
            from quill.core.model_upgrade import suggest_llm_upgrade

            saved_choice = load_model_choice()
            if saved_choice != "auto":
                suggestion = suggest_llm_upgrade(saved_choice, total_ram_gb())
                if suggestion is not None:
                    hint = wx.StaticText(self.dialog, label=suggestion.message())
                    hint.SetName("Model upgrade suggestion")
                    root.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
                    self._announce(suggestion.message())
            root.Add(wx.StaticText(self.dialog, label="On-device model"), 0, wx.LEFT | wx.RIGHT, 12)
            self._ids = ["auto", *MODELS.keys()]
            labels = [f"Recommended ({MODELS[rec].name})"]
            for model_id, spec in MODELS.items():
                tags = []
                if model_id == rec:
                    tags.append("recommended")
                if is_downloaded(spec):
                    tags.append("downloaded")
                suffix = f" ({', '.join(tags)})" if tags else ""
                labels.append(f"{spec.name} (~{spec.approx_gb:g} GB){suffix}")
            self.choice = wx.Choice(self.dialog, choices=labels)
            self.choice.SetName("AI model")
            current = load_model_choice()
            self.choice.SetSelection(self._ids.index(current) if current in self._ids else 0)
            root.Add(self.choice, 0, wx.EXPAND | wx.ALL, 12)

            self.status = wx.StaticText(self.dialog, label="")
            root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

            self._build_tier_section(root)

        # Optional: connect Ollama (local or cloud) for more models.
        if self._open_connection is not None:
            add_help(
                "More options (optional): if you have Ollama installed — or an Ollama "
                "Cloud key — you can connect it for more models. The on-device model above "
                "works on its own; this is only if you want more."
            )
            self.connection_button = wx.Button(
                self.dialog,
                label="Connect Ollama or set up a cloud key (Connection Settings)...",
            )
            self.connection_button.Bind(wx.EVT_BUTTON, self._on_connection)
            root.Add(self.connection_button, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        root.AddStretchSpacer()
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        if not self._fm:
            self.download_button = wx.Button(self.dialog, label="Download Now")
            buttons.Add(self.download_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer()
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Save"), 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Close"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.dialog.SetSizer(root)

        if self.choice is not None:
            self.choice.Bind(wx.EVT_CHOICE, lambda _e: self._refresh_status())
            self.download_button.Bind(wx.EVT_BUTTON, self._on_download)
            self._refresh_status()

    def _on_connection(self, _event: object) -> None:
        if self._open_connection is not None:
            self._open_connection()

    def _build_tier_section(self, root: object) -> None:
        """Fast/Strong speed-tier picker: choose the active tier (switchable
        mid-task with a spoken announcement) and which model backs each tier."""

        wx = self._wx
        tiers = {tier.tier_id: tier for tier in load_tiers()}

        root.Add(
            wx.StaticText(self.dialog, label="Speed tier"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            12,
        )
        intro = wx.StaticText(
            self.dialog,
            label="Pick how Quill balances speed against quality. The Fast tier "
            "answers quickly; the Strong tier is more capable. You can switch "
            "tiers at any time and Quill announces the change.",
        )
        intro.Wrap(520)
        root.Add(intro, 0, wx.LEFT | wx.RIGHT, 12)

        active = active_tier_id()
        tier_labels = [tiers[tier_id].label for tier_id in self._tier_order]
        root.Add(
            wx.StaticText(self.dialog, label="Active speed tier:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            12,
        )
        self.tier_choice = wx.Choice(self.dialog, choices=tier_labels)
        self.tier_choice.SetName("Active speed tier")
        self.tier_choice.SetSelection(
            self._tier_order.index(active) if active in self._tier_order else 0
        )
        self.tier_choice.Bind(wx.EVT_CHOICE, self._on_tier_change)
        root.Add(self.tier_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        model_labels = ["Recommended (automatic)"]
        for spec in MODELS.values():
            model_labels.append(f"{spec.name} (~{spec.approx_gb:g} GB)")
        for tier_id in self._tier_order:
            tier = tiers[tier_id]
            root.Add(
                wx.StaticText(self.dialog, label=f"{tier.label} tier model"),
                0,
                wx.LEFT | wx.RIGHT | wx.TOP,
                12,
            )
            picker = wx.Choice(self.dialog, choices=model_labels)
            picker.SetName(f"{tier.label} tier model")
            picker.SetSelection(
                self._tier_model_ids.index(tier.model_id)
                if tier.model_id in self._tier_model_ids
                else 0
            )
            picker.Bind(wx.EVT_CHOICE, self._on_tier_model_change)
            self.tier_model_choices[tier_id] = picker
            root.Add(picker, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.tier_status = wx.StaticText(self.dialog, label="")
        root.Add(self.tier_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

    def _on_tier_change(self, _event: object) -> None:
        message = switch_active_tier(self._tier_order[self.tier_choice.GetSelection()])
        if self.tier_status is not None:
            self.tier_status.SetLabel(message)
        self._announce(message)

    def _on_tier_model_change(self, _event: object) -> None:
        for tier_id, picker in self.tier_model_choices.items():
            model_id = self._tier_model_ids[picker.GetSelection()]
            assign_model_to_tier(tier_id, model_id)
        if self.tier_choice is not None:
            self._on_tier_change(None)

    def _selected_id(self) -> str:
        return self._ids[self.choice.GetSelection()]

    def _refresh_status(self) -> None:
        spec = resolve_spec(self._selected_id())
        state = (
            "already downloaded" if is_downloaded(spec) else "downloads automatically on first use"
        )
        self.status.SetLabel(
            f"{spec.note}\n{spec.name} (~{spec.approx_gb:g} GB). {state.capitalize()}."
        )

    def _on_download(self, _event: object) -> None:
        save_model_choice(self._selected_id())
        self.download_button.Enable(False)
        self.status.SetLabel("Downloading… this can take a while.")
        self._announce("Downloading model")

        def worker() -> None:
            try:
                path = ensure_model()
                message = f"Downloaded. Using: {path}"
            except Exception as exc:  # noqa: BLE001
                message = f"Download failed: {exc}"
            self._wx.CallAfter(self._after_download, message)

        threading.Thread(  # GATE-40-OK: model download worker; bounded; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _after_download(self, message: str) -> None:
        self.download_button.Enable(True)
        self.status.SetLabel(message)
        self._announce("Download finished")

    def show(self) -> None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if (
                show_modal_dialog(self.dialog, "AI Model & Connection") == wx.ID_OK
                and self.choice is not None
            ):
                save_model_choice(self._selected_id())
                self._announce("Saved AI model choice")
        finally:
            self.dialog.Destroy()
