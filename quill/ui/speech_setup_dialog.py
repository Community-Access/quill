"""Speech Setup dialog — model catalog with live install/state visibility (#669).

Replaces the three-step SingleChoiceDialog chain (engine chooser → flat model
list → action picker) with a single panel that shows every model's current
state, recommended status, and size at a glance.  The user picks one action
and closes; the caller executes it.

Supports embed mode: pass ``embed_in`` to build the UI into an existing
``wx.Panel`` (used by SpeechHubDialog for the Dictation notebook tab).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.ui.dialog_contract import apply_modal_ids

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class SpeechSetupResult:
    """What the dialog wants to happen after it closes."""

    action: str
    """One of: 'download' | 'remove' | 'ffmpeg' | 'engine' | 'vosk' | 'kokoro_engine'
    | 'hf_token'."""
    model_id: str | None = None
    model_row: object | None = None
    provider_id: str | None = None


def build_engine_descriptors(
    all_providers: list,
    *,
    whispercpp_ok: bool,
    faster_whisper_ok: bool,
    vosk_ok: bool,
) -> list[dict]:
    """Describe every dictation engine as a radio row (installed or not).

    Whisper.cpp is always present (bundled). Faster Whisper and Vosk appear
    whether or not they are installed: a not-installed row carries an
    ``install_action`` so selecting it installs the engine. Any other registered
    provider (e.g. a cloud Quillin) is appended as an already-installed engine.
    Pure and wx-free so it is unit-testable.
    """
    by_id: dict[str, object] = {}
    for provider in all_providers:
        pid = str(getattr(provider, "id", "") or "")
        if pid:
            by_id[pid] = provider
    descriptors: list[dict] = [
        {
            "label": "Whisper (built in)",
            "provider": by_id.get("whispercpp"),
            "installed": whispercpp_ok,
            "install_action": None,
        },
        {
            "label": "Faster Whisper (faster, GPU-capable)",
            "provider": by_id.get("fasterwhisper"),
            "installed": faster_whisper_ok,
            "install_action": "engine",
        },
        {
            "label": "Vosk (lightweight, low RAM, no GPU)",
            "provider": by_id.get("vosk"),
            "installed": vosk_ok,
            "install_action": "vosk",
        },
    ]
    known = {"whispercpp", "fasterwhisper", "vosk"}
    for pid, provider in by_id.items():
        if pid not in known:
            descriptors.append({
                "label": str(getattr(provider, "display_name", pid)),
                "provider": provider,
                "installed": True,
                "install_action": None,
            })
    return descriptors


class SpeechSetupDialog:
    """Rich speech model manager with full install-state visibility.

    Parameters
    ----------
    parent:
        wx parent window.
    provider:
        A SpeechProvider (has .display_name, .list_installed_models(), ...).
    rows:
        List[ModelRow] from ``service.describe_models()``.
    machine_summary:
        Short string e.g. "Your computer: 16 GB RAM and no GPU."
    ffmpeg_ok:
        Whether ffmpeg is found on this system.
    engine_ok:
        Whether Faster Whisper is installed.
    all_providers:
        All *registered* providers (available or not); enables the engine switcher
        when > 1. Not-yet-installed engines are listed and marked "(not installed)"
        so they stay discoverable and reach their guided install path.
    total_ram:
        Detected RAM in GB (used when repopulating after an engine switch).
    has_gpu:
        Whether a GPU is detected (used when repopulating after a switch).
    embed_in:
        When given, build the UI into this existing ``wx.Panel`` instead of
        creating a new ``wx.Dialog``.
    on_action:
        Callback invoked (with a ``SpeechSetupResult``) when any action button
        is triggered in embed mode.  Ignored when ``embed_in`` is None.
    """

    def __init__(
        self,
        parent: object,
        *,
        provider: object,
        rows: list,
        machine_summary: str,
        whispercpp_ok: bool,
        ffmpeg_ok: bool,
        engine_ok: bool,
        vosk_ok: bool,
        vosk_can_install: bool,
        kokoro_ok: bool,
        kokoro_can_install: bool,
        all_providers: list,
        total_ram: float = 0.0,
        has_gpu: bool = False,
        embed_in: object | None = None,
        on_action: Callable[[SpeechSetupResult], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._rows = rows
        self._machine_summary = machine_summary
        self._whispercpp_ok = whispercpp_ok
        self._ffmpeg_ok = ffmpeg_ok
        self._engine_ok = engine_ok
        self._vosk_ok = vosk_ok
        self._vosk_can_install = vosk_can_install
        self._kokoro_ok = kokoro_ok
        self._kokoro_can_install = kokoro_can_install
        self._all_providers = all_providers
        self._total_ram = total_ram
        self._has_gpu = has_gpu
        self._result: SpeechSetupResult | None = None
        self._on_action = on_action

        if embed_in is not None:
            self._root = embed_in
            self.dialog = None  # type: ignore[assignment]
            self._embed_mode = True
        else:
            self.dialog = wx.Dialog(
                parent,
                title="Manage Speech Models",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self.dialog.SetMinSize(wx.Size(560, 460))
            self.dialog.SetSize(wx.Size(700, 540))
            self._root = self.dialog
            self._embed_mode = False

        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)
        parent = self._root

        # Dictation engine: one radio choice covering every engine, installed or
        # not. Selecting an installed engine switches to it; a not-installed engine
        # (Faster Whisper, Vosk) is installed by the explicit "Install selected
        # engine" button below — not on selection, so arrowing through the radio
        # with a screen reader never triggers an install (#700).
        self._engine_descriptors = self._build_engine_descriptors()
        choices = []
        for d in self._engine_descriptors:
            if d["installed"]:
                choices.append(d["label"])
            elif d["install_action"] is None:
                # A bundled engine (whisper.cpp) whose binary isn't present — it
                # ships with the installed app, so don't imply the user installs it.
                choices.append(f"{d['label']} — engine file not found (ships with the app)")
            else:
                choices.append(f"{d['label']} — not installed")
        self._engine_radio = wx.RadioBox(
            parent,
            label="Dictation &engine",
            choices=choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._engine_radio.SetName("Dictation engine")
        current_idx = next(
            (i for i, d in enumerate(self._engine_descriptors) if d["provider"] is self._provider),
            0,
        )
        self._engine_radio.SetSelection(current_idx)
        root.Add(self._engine_radio, 0, wx.EXPAND | wx.ALL, 10)
        self._engine_radio.Bind(wx.EVT_RADIOBOX, self._on_engine_radio)

        self._btn_install_engine = wx.Button(parent, label="&Install selected engine")
        self._btn_install_engine.Bind(wx.EVT_BUTTON, lambda _e: self._on_install_engine())
        root.Add(self._btn_install_engine, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Machine summary.
        self._summary_text = wx.StaticText(parent, label=self._machine_summary)
        root.Add(self._summary_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Engine & dependency status panel.
        dep_box = wx.StaticBoxSizer(
            wx.StaticBox(parent, label="Engine & Dependency Status"), wx.VERTICAL
        )

        wc_row = wx.BoxSizer(wx.HORIZONTAL)
        wc_lbl = wx.StaticText(
            parent,
            label=(
                "Whisper engine binary: Installed"
                if self._whispercpp_ok
                else "Whisper engine binary: Not found — re-run the QUILL installer"
            ),
        )
        wc_row.Add(wc_lbl, 1, wx.ALIGN_CENTER_VERTICAL)
        dep_box.Add(wc_row, 0, wx.EXPAND | wx.ALL, 6)

        ffmpeg_row = wx.BoxSizer(wx.HORIZONTAL)
        ffmpeg_lbl = wx.StaticText(
            parent,
            label="FFmpeg: Installed" if self._ffmpeg_ok else "FFmpeg: Not installed",
        )
        ffmpeg_row.Add(ffmpeg_lbl, 1, wx.ALIGN_CENTER_VERTICAL)
        if not self._ffmpeg_ok:
            self._btn_ffmpeg = wx.Button(parent, label="Download &FFmpeg...")
            self._btn_ffmpeg.Bind(wx.EVT_BUTTON, lambda _e: self._choose("ffmpeg"))
            ffmpeg_row.Add(self._btn_ffmpeg, 0, wx.LEFT, 8)
        dep_box.Add(ffmpeg_row, 0, wx.EXPAND | wx.ALL, 6)

        root.Add(dep_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Model list.
        root.Add(
            wx.StaticText(parent, label="&Models (select one, then Download or Remove):"),
            0,
            wx.LEFT | wx.RIGHT,
            10,
        )
        self._model_list = wx.ListBox(parent, style=wx.LB_SINGLE)
        self._model_list.SetName("Models")
        self._model_list.SetMinSize(wx.Size(-1, 140))
        self._populate_model_list()
        root.Add(self._model_list, 1, wx.EXPAND | wx.ALL, 10)

        # A live note that tells the user why Download/Remove are unavailable
        # (e.g. nothing selected) instead of leaving disabled buttons unexplained.
        self._model_note = wx.StaticText(parent, label="")
        self._model_note.SetName("Model selection status")
        root.Add(self._model_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Action buttons.
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_download = wx.Button(parent, label="&Download Selected")
        self._btn_remove = wx.Button(parent, label="&Remove Selected")
        btn_hf = wx.Button(parent, label="&Hugging Face Token...")
        btn_row.Add(self._btn_download, 0, wx.RIGHT, 6)
        btn_row.Add(self._btn_remove, 0, wx.RIGHT, 6)
        btn_row.Add(btn_hf, 0, wx.RIGHT, 6)

        if not self._embed_mode:
            btn_close = wx.Button(parent, label="&Close")
            btn_row.Add(btn_close, 0)
            btn_close.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))  # type: ignore[union-attr]
            apply_modal_ids(
                parent,
                affirmative_id=self._btn_download.GetId(),
                escape_id=btn_close.GetId(),
            )

        root.Add(btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._btn_download.Bind(wx.EVT_BUTTON, lambda _e: self._on_download())
        self._btn_remove.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove())
        btn_hf.Bind(wx.EVT_BUTTON, lambda _e: self._choose("hf_token"))
        self._model_list.Bind(wx.EVT_LISTBOX, lambda _e: self._update_buttons())

        self._update_buttons()
        self._sync_engine_install_button()
        self._root.SetSizer(root)

    @staticmethod
    def _provider_label(provider: object) -> str:
        """Engine name for the chooser, marked when its runtime isn't installed.

        A registered-but-unavailable engine (e.g. whisper.cpp with no binary) must
        stay visible and discoverable, so it is shown as "Name (not installed)";
        the dependency panel below carries the guided install path.
        """
        name = str(getattr(provider, "display_name", "Engine"))
        try:
            available = bool(provider.is_available())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a broken provider must not break its label
            available = False
        return name if available else f"{name} (not installed)"

    def _populate_model_list(self) -> None:
        self._model_list.Clear()
        for row in self._rows:
            self._model_list.Append(row.label)

    def _update_buttons(self) -> None:
        sel = self._model_list.GetSelection()
        if sel == self._wx.NOT_FOUND or sel >= len(self._rows):
            self._btn_download.Enable(False)
            self._btn_remove.Enable(False)
            if not self._rows:
                self._model_note.SetLabel("No models for this engine yet.")
            else:
                self._model_note.SetLabel("Select a model above, then Download or Remove.")
            return
        installed = bool(getattr(self._rows[sel], "installed", False))
        self._btn_download.Enable(not installed)
        self._btn_remove.Enable(installed)
        self._model_note.SetLabel(
            "This model is installed — use Remove to delete it."
            if installed
            else "This model is not installed — use Download to get it."
        )

    def _on_download(self) -> None:
        sel = self._model_list.GetSelection()
        if sel == self._wx.NOT_FOUND or sel >= len(self._rows):
            return
        row = self._rows[sel]
        result = SpeechSetupResult(
            action="download",
            model_id=str(getattr(row, "id", "")),
            model_row=row,
            provider_id=getattr(self._provider, "id", None),
        )
        self._dispatch_action(result)

    def _on_remove(self) -> None:
        sel = self._model_list.GetSelection()
        if sel == self._wx.NOT_FOUND or sel >= len(self._rows):
            return
        row = self._rows[sel]
        result = SpeechSetupResult(
            action="remove",
            model_id=str(getattr(row, "id", "")),
            provider_id=getattr(self._provider, "id", None),
        )
        self._dispatch_action(result)

    def _choose(self, action: str) -> None:
        result = SpeechSetupResult(
            action=action,
            provider_id=getattr(self._provider, "id", None),
        )
        self._dispatch_action(result)

    def _dispatch_action(self, result: SpeechSetupResult) -> None:
        if self._embed_mode and self._on_action is not None:
            self._on_action(result)
        else:
            self._result = result
            self.dialog.EndModal(self._wx.ID_OK)  # type: ignore[union-attr]

    def _build_engine_descriptors(self) -> list[dict]:
        return build_engine_descriptors(
            self._all_providers,
            whispercpp_ok=self._whispercpp_ok,
            faster_whisper_ok=self._engine_ok,
            vosk_ok=self._vosk_ok,
        )

    def _selected_engine(self) -> dict | None:
        idx = self._engine_radio.GetSelection()
        if not (0 <= idx < len(self._engine_descriptors)):
            return None
        return self._engine_descriptors[idx]

    def _sync_engine_install_button(self) -> None:
        """Enable 'Install selected engine' only for a not-installed, installable
        engine. Bundled whisper.cpp has no installer, so its button stays
        disabled — there is nothing for the user to install."""
        descriptor = self._selected_engine()
        can_install = (
            descriptor is not None
            and not descriptor["installed"]
            and descriptor["install_action"] is not None
        )
        self._btn_install_engine.Enable(bool(can_install))

    def _on_engine_radio(self, event: object) -> None:
        """Switch to an installed engine on selection. Never installs on select."""
        self._sync_engine_install_button()
        descriptor = self._selected_engine()
        if descriptor is None or not descriptor["installed"]:
            # Not-installed engines are added via the explicit Install button, so
            # selecting one only updates that button — the model list is unchanged.
            return
        new_provider = descriptor["provider"]
        if new_provider is None or new_provider is self._provider:
            return
        self._provider = new_provider
        from quill.core.speech.service import describe_models

        self._rows = describe_models(new_provider, self._total_ram, self._has_gpu)
        self._populate_model_list()
        self._update_buttons()
        if not self._embed_mode and self.dialog is not None:
            self.dialog.SetTitle(
                f"Manage Speech Models — {new_provider.display_name}"  # type: ignore[attr-defined]
            )

    def _on_install_engine(self) -> None:
        """Install the selected not-installed engine via its host action."""
        descriptor = self._selected_engine()
        if descriptor is None or descriptor["installed"]:
            return
        action = descriptor["install_action"]
        if action:
            self._choose(action)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show(self, show_modal_dialog: Callable) -> SpeechSetupResult | None:
        """Open the dialog. Returns what the user chose, or None on cancel/close."""
        if self._embed_mode:
            raise RuntimeError("SpeechSetupDialog.show() cannot be called in embed mode")
        show_modal_dialog(self.dialog, "Manage Speech Models")
        self.dialog.Destroy()  # type: ignore[union-attr]
        return self._result
