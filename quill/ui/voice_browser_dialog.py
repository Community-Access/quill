"""Voice Browser dialog — choose TTS engine, voice, and settings with live preview.

Replaces the inline ``choose_read_aloud_configuration()`` closure in MainFrame
with a proper, reusable dialog that adds:

  * Filter-as-you-type voice search (name, accent, description)
  * Per-voice detail panel (accent · style)
  * Preview via the Preview button: a downloaded voice synthesizes the preview
    phrase with its real model; a not-yet-downloaded voice plays a bundled
    pre-recorded sample so the user can still hear it. Rate/volume/pitch/speed
    controls dim until the voice is downloaded. (Enter/double-click still work.)
  * Export to Speech Audio button (closes and triggers export)
  * Clear installed vs. not-downloaded distinction for Piper/Kokoro voices
  * Embed mode: build into an existing panel (for SpeechHubDialog notebook tab)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass
class VoiceBrowserResult:
    """What the caller should do after the dialog closes."""

    action: str
    """'select' | 'download' | 'download_engine' | 'export'"""
    engine: str = ""
    voice_id: str = ""
    rate: int = 175
    volume: int = 100
    pitch: int = 50
    dectalk_rate: int = 200
    kokoro_speed: float = 1.0
    espeak_rate: int = 175


class VoiceBrowserDialog:
    """Select a TTS engine and voice with live preview and one-click export.

    Parameters
    ----------
    parent:
        wx parent window.
    engine_options:
        ``[(label, id), ...]`` for the engine RadioBox.
    current_engine:
        Initially selected engine id.
    piper_model_dir:
        Path to the local Piper model folder (used to determine download status).
    settings:
        A settings object with ``read_aloud_*`` attributes (snapshot for defaults).
    preview_fn:
        ``(engine, voice_id) -> None`` — runs on main thread, must start its own
        background work (does NOT block the UI).  Passed directly from MainFrame's
        ``_preview_voice`` method.
    engine_available:
        ``{engine_id: bool}`` mapping — True when the engine binary / packages are
        installed and ready. Engines marked False show a "Download Engine" button
        instead of the voice list action button. Defaults to all-True when omitted.
    embed_in:
        When given, build the UI into this existing ``wx.Panel`` instead of
        creating a new ``wx.Dialog``.  In this mode ``show()`` must not be called;
        use ``collect_result()`` to read the current selection.
    on_action:
        Callback invoked (with a ``VoiceBrowserResult``) when the user triggers a
        download or export action in embed mode.  Ignored when ``embed_in`` is None.
    """

    def __init__(
        self,
        parent: object,
        *,
        engine_options: list[tuple[str, str]],
        current_engine: str,
        piper_model_dir: Path,
        settings: object,
        preview_fn: Callable[..., None],
        preview_stop_fn: Callable[[], None] | None = None,
        engine_available: dict[str, bool] | None = None,
        elevenlabs_api_key: str = "",
        has_preview_sample: Callable[[str, str], bool] | None = None,
        embed_in: object | None = None,
        on_action: Callable[[VoiceBrowserResult], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._engine_options = engine_options
        self._engine_labels = [lbl for lbl, _ in engine_options]
        self._engine_values = [val for _, val in engine_options]
        self._current_engine = current_engine
        self._piper_model_dir = piper_model_dir
        self._settings = settings
        self._elevenlabs_api_key = elevenlabs_api_key
        self._preview_fn = preview_fn
        self._preview_stop_fn = preview_stop_fn or (lambda: None)
        self._previewing = False
        self._engine_available: dict[str, bool] = engine_available or {}
        # Whether a bundled pre-recorded preview clip exists for (engine, voice).
        self._has_preview_sample = has_preview_sample or (lambda _e, _v: False)
        self._result: VoiceBrowserResult | None = None
        self._all_voices: list = []
        self._displayed_voices: list = []
        self._on_action = on_action

        if embed_in is not None:
            self._root = embed_in
            self.dialog = None  # type: ignore[assignment]
            self._embed_mode = True
        else:
            self.dialog = wx.Dialog(
                parent,
                title="Manage Voices & Reading Aloud",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self.dialog.SetMinSize(wx.Size(580, 520))
            self.dialog.SetSize(wx.Size(680, 600))
            self._root = self.dialog
            self._embed_mode = False

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wx = self._wx
        s = self._settings
        root = wx.BoxSizer(wx.VERTICAL)
        parent = self._root

        # Engine radio box.
        self._engine_rb = wx.RadioBox(
            parent,
            label="&Engine",
            choices=self._engine_labels,
            style=wx.RA_SPECIFY_ROWS,
        )
        self._engine_rb.SetName("Engine")
        cur_idx = (
            self._engine_values.index(self._current_engine)
            if self._current_engine in self._engine_values
            else 0
        )
        self._engine_rb.SetSelection(cur_idx)
        root.Add(self._engine_rb, 0, wx.EXPAND | wx.ALL, 10)

        # Filter row.
        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_lbl = wx.StaticText(parent, label="Filter &voices:")
        self._filter_ctrl = wx.TextCtrl(parent)
        self._filter_ctrl.SetName("Filter voices")
        self._filter_ctrl.SetHint("type to search by name, accent, or style...")
        filter_row.Add(filter_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        filter_row.Add(self._filter_ctrl, 1, wx.EXPAND)
        root.Add(filter_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Voice list.
        voices_lbl = wx.StaticText(parent, label="&Voices (use the Preview button to hear one):")
        root.Add(voices_lbl, 0, wx.LEFT | wx.TOP, 10)
        self._voice_lb = wx.ListBox(parent, style=wx.LB_SINGLE)
        self._voice_lb.SetName("Voices")
        self._voice_lb.SetMinSize(wx.Size(-1, 160))
        root.Add(self._voice_lb, 1, wx.EXPAND | wx.ALL, 10)

        # Voice detail.
        self._detail_lbl = wx.StaticText(parent, label="")
        self._detail_lbl.SetName("Voice details")
        root.Add(self._detail_lbl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Settings panel — shown/hidden per engine.
        settings_box = wx.StaticBoxSizer(wx.StaticBox(parent, label="Settings"), wx.VERTICAL)
        sb = settings_box.GetStaticBox()

        rate_row = wx.BoxSizer(wx.HORIZONTAL)
        self._rate_lbl = wx.StaticText(sb, label="Rate:")
        self._rate_spin = wx.SpinCtrl(
            sb, min=75, max=650, initial=getattr(s, "read_aloud_rate", 175)
        )
        self._rate_spin.SetName("Rate (words per minute)")
        rate_row.Add(self._rate_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        rate_row.Add(self._rate_spin, 1, wx.EXPAND)
        settings_box.Add(rate_row, 0, wx.EXPAND | wx.ALL, 4)

        vol_row = wx.BoxSizer(wx.HORIZONTAL)
        self._vol_lbl = wx.StaticText(sb, label="Volume (0-100):")
        self._vol_spin = wx.SpinCtrl(
            sb, min=0, max=100, initial=getattr(s, "read_aloud_volume", 100)
        )
        self._vol_spin.SetName("Volume")
        vol_row.Add(self._vol_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        vol_row.Add(self._vol_spin, 1, wx.EXPAND)
        settings_box.Add(vol_row, 0, wx.EXPAND | wx.ALL, 4)

        pitch_row = wx.BoxSizer(wx.HORIZONTAL)
        self._pitch_lbl = wx.StaticText(sb, label="Pitch (0-100):")
        self._pitch_spin = wx.SpinCtrl(
            sb, min=0, max=100, initial=getattr(s, "read_aloud_pitch", 50)
        )
        self._pitch_spin.SetName("Pitch")
        pitch_row.Add(self._pitch_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        pitch_row.Add(self._pitch_spin, 1, wx.EXPAND)
        settings_box.Add(pitch_row, 0, wx.EXPAND | wx.ALL, 4)

        kok_row = wx.BoxSizer(wx.HORIZONTAL)
        self._kok_lbl = wx.StaticText(sb, label="Speed (0.5-2.0):")
        self._kok_spin = wx.SpinCtrlDouble(
            sb, min=0.5, max=2.0, initial=getattr(s, "read_aloud_kokoro_speed", 1.0), inc=0.1
        )
        self._kok_spin.SetName("Speed multiplier")
        for _child in self._kok_spin.GetChildren():
            if isinstance(_child, wx.TextCtrl):
                _child.SetName("Speed multiplier")
                break
        kok_row.Add(self._kok_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        kok_row.Add(self._kok_spin, 1, wx.EXPAND)
        settings_box.Add(kok_row, 0, wx.EXPAND | wx.ALL, 4)

        # eSpeak voice character variant (appended as accent+variant).
        from quill.core.voice_catalog import ESPEAK_VARIANTS as _ev

        self._espeak_variant_codes = [code for code, _ in _ev]
        self._espeak_variant_labels = [label for _, label in _ev]
        variant_row = wx.BoxSizer(wx.HORIZONTAL)
        self._variant_lbl = wx.StaticText(sb, label="Voice &character:")
        self._variant_choice = wx.Choice(sb, choices=self._espeak_variant_labels)
        self._variant_choice.SetName("Voice character")
        self._variant_choice.SetSelection(0)
        variant_row.Add(self._variant_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        variant_row.Add(self._variant_choice, 1, wx.EXPAND)
        settings_box.Add(variant_row, 0, wx.EXPAND | wx.ALL, 4)

        self._settings_box = settings_box
        self._rate_row = rate_row
        self._vol_row = vol_row
        self._pitch_row = pitch_row
        self._kok_row = kok_row
        self._variant_row = variant_row
        self._settings_sb = sb
        root.Add(settings_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Action buttons.
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._preview_btn = wx.Button(parent, label="&Preview Selected Voice")
        self._preview_btn.SetName("Preview selected voice")
        self._download_btn = wx.Button(parent, label="&Download Voice...")
        self._download_btn.SetName("Download voice model")
        self._export_btn = wx.Button(parent, label="E&xport to Audio File...")
        self._export_btn.SetName("Export document to audio file")
        self._set_default_btn = wx.Button(parent, label="Set as &Default")
        self._set_default_btn.SetName("Set selected voice as default")
        btn_row.Add(self._preview_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._download_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._export_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._set_default_btn, 0, wx.RIGHT, 6)

        if not self._embed_mode:
            ok_btn = wx.Button(parent, id=wx.ID_OK)
            cancel_btn = wx.Button(parent, id=wx.ID_CANCEL)
            btn_row.AddStretchSpacer()
            btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
            btn_row.Add(cancel_btn, 0)
            apply_modal_ids(parent, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._root.SetSizer(root)

        # Bindings.
        self._engine_rb.Bind(wx.EVT_RADIOBOX, lambda _e: self._on_engine_changed())
        self._filter_ctrl.Bind(wx.EVT_TEXT, lambda _e: self._on_filter_changed())
        self._voice_lb.Bind(wx.EVT_LISTBOX, lambda _e: self._on_voice_selected())
        self._voice_lb.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._do_preview())
        self._voice_lb.Bind(wx.EVT_KEY_DOWN, self._on_voice_key_down)
        self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self._do_preview())
        self._download_btn.Bind(wx.EVT_BUTTON, lambda _e: self._do_download())
        self._export_btn.Bind(wx.EVT_BUTTON, lambda _e: self._do_export())
        self._set_default_btn.Bind(wx.EVT_BUTTON, lambda _e: self._do_set_default())
        self._voice_lb.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._show_voice_context_menu())

        # Preview is the primary action after picking a voice, so place it right
        # after the voice list in tab order (without moving it visually) (#700).
        self._preview_btn.MoveAfterInTabOrder(self._voice_lb)

        self._refresh_voices(self._current_engine)

    # ------------------------------------------------------------------
    # Engine / voice refresh
    # ------------------------------------------------------------------

    def _current_engine_id(self) -> str:
        idx = self._engine_rb.GetSelection()
        if 0 <= idx < len(self._engine_values):
            return self._engine_values[idx]
        return self._engine_values[0] if self._engine_values else "sapi5"

    def _voices_for_engine(self, eng: str) -> list:

        from quill.core.read_aloud import (
            list_dectalk_voices,
            list_elevenlabs_voices,
            list_espeak_voices,
            list_kokoro_voices,
            list_piper_catalog_voices,
            list_voices,
        )

        if eng == "dectalk":
            return list_dectalk_voices()
        if eng == "piper":
            return list_piper_catalog_voices(self._piper_model_dir)
        if eng == "kokoro":
            return list_kokoro_voices()
        if eng == "espeak":
            return list_espeak_voices()
        if eng == "elevenlabs":
            return list_elevenlabs_voices(self._elevenlabs_api_key)
        # sapi5 — every installed system voice, whatever its language, so a
        # user with (say) an Italian Windows voice can pick it (#813 follow-on).
        return list_voices()

    def _current_voice_id_for(self, eng: str) -> str:
        from pathlib import Path as _Path

        s = self._settings
        if eng == "dectalk":
            return str(getattr(s, "read_aloud_dectalk_voice", "") or "paul")
        if eng == "piper":
            model = str(getattr(s, "read_aloud_piper_model", "") or "")
            return _Path(model).stem if model else ""
        if eng == "kokoro":
            return str(getattr(s, "read_aloud_kokoro_voice", "") or "af_heart")
        if eng == "espeak":
            raw = str(getattr(s, "read_aloud_espeak_voice", "") or "en-gb")
            return raw.split("+")[0]  # strip stored variant for list matching
        if eng == "elevenlabs":
            return str(getattr(s, "read_aloud_elevenlabs_voice", "") or "")
        return str(getattr(s, "read_aloud_voice", "") or "")

    def _espeak_combined_voice_id(self, accent_id: str) -> str:
        """Return ``accent`` or ``accent+variant`` for the currently selected variant."""
        idx = self._variant_choice.GetSelection()
        if 0 <= idx < len(self._espeak_variant_codes):
            code = self._espeak_variant_codes[idx]
            if code:
                return f"{accent_id}+{code}"
        return accent_id

    def _refresh_voices(self, eng: str) -> None:
        self._all_voices = self._voices_for_engine(eng)
        self._filter_ctrl.Clear()
        self._apply_filter("")
        cur_vid = self._current_voice_id_for(eng)
        idx = next((i for i, v in enumerate(self._displayed_voices) if v.id == cur_vid), 0)
        if self._displayed_voices:
            self._voice_lb.SetSelection(idx)
        self._on_voice_selected()
        self._update_settings_panel(eng)

    def _apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        if q:
            self._displayed_voices = [
                v
                for v in self._all_voices
                if q in v.name.lower()
                or q in getattr(v, "accent", "").lower()
                or q in getattr(v, "description", "").lower()
            ]
        else:
            self._displayed_voices = list(self._all_voices)

        labels = []
        for v in self._displayed_voices:
            accent = getattr(v, "accent", "")
            desc = getattr(v, "description", "")
            installed = getattr(v, "installed", True)
            parts = [p for p in [accent, desc] if p]
            meta = " · ".join(parts)
            tag = "" if installed else "  [not downloaded]"
            labels.append(f"{v.name}  —  {meta}{tag}" if meta else f"{v.name}{tag}")

        self._voice_lb.Set(labels)
        if self._displayed_voices:
            self._voice_lb.SetSelection(0)
        self._on_voice_selected()

    def _update_settings_panel(self, eng: str) -> None:
        s = self._settings
        has_rate = eng in {"sapi5", "dectalk", "espeak"}
        has_vol_pitch = eng == "sapi5"
        has_kokoro = eng == "kokoro"
        has_any = has_rate or has_vol_pitch or has_kokoro

        if eng == "sapi5":
            self._rate_spin.SetRange(80, 450)
            self._rate_spin.SetValue(getattr(s, "read_aloud_rate", 175))
        elif eng == "dectalk":
            self._rate_spin.SetRange(75, 650)
            self._rate_spin.SetValue(getattr(s, "read_aloud_dectalk_rate", 200))
        elif eng == "espeak":
            self._rate_spin.SetRange(80, 450)
            self._rate_spin.SetValue(getattr(s, "read_aloud_espeak_rate", 175))

        if has_vol_pitch:
            self._vol_spin.SetValue(getattr(s, "read_aloud_volume", 100))
            self._pitch_spin.SetValue(getattr(s, "read_aloud_pitch", 50))
        if has_kokoro:
            self._kok_spin.SetValue(getattr(s, "read_aloud_kokoro_speed", 1.0))

        has_variant = eng == "espeak"
        if has_variant:
            raw = str(getattr(s, "read_aloud_espeak_voice", "") or "en-gb")
            stored_variant = raw.split("+", 1)[1] if "+" in raw else ""
            variant_idx = (
                self._espeak_variant_codes.index(stored_variant)
                if stored_variant in self._espeak_variant_codes
                else 0
            )
            self._variant_choice.SetSelection(variant_idx)

        has_any = has_rate or has_vol_pitch or has_kokoro or has_variant
        self._settings_box.Show(self._rate_row, has_rate, recursive=True)
        self._settings_box.Show(self._vol_row, has_vol_pitch, recursive=True)
        self._settings_box.Show(self._pitch_row, has_vol_pitch, recursive=True)
        self._settings_box.Show(self._kok_row, has_kokoro, recursive=True)
        self._settings_box.Show(self._variant_row, has_variant, recursive=True)
        # No ShowItems() — it would override the per-row Show() above (#700).
        self._settings_sb.Show(has_any)

        eng_ok = self._engine_available.get(eng, True)
        if eng == "dectalk" and not eng_ok:
            self._download_btn.SetLabel("&Download DECtalk Engine (~30 MB)...")
            self._download_btn.Show(True)
        elif eng == "piper" and not eng_ok:
            self._download_btn.SetLabel("&Download Piper Engine (~22 MB)...")
            self._download_btn.Show(True)
        elif eng == "piper":
            self._download_btn.SetLabel("&Download Piper Voice...")
            self._download_btn.Show(True)
        elif eng == "kokoro" and not eng_ok:
            # Kokoro ships as one pack; once the models are downloaded there is
            # nothing more to fetch, so hide the button rather than offer a
            # redundant 114 MB re-download.
            self._download_btn.SetLabel("&Download Kokoro — all voices, one pack (~114 MB)...")
            self._download_btn.Show(True)
        elif eng == "espeak" and not eng_ok:
            self._download_btn.SetLabel("&Download eSpeak-NG (~50 MB)...")
            self._download_btn.Show(True)
        else:
            self._download_btn.Show(False)

        self._root.Layout()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_engine_changed(self) -> None:
        eng = self._current_engine_id()
        self._refresh_voices(eng)

    def _on_filter_changed(self) -> None:
        self._apply_filter(self._filter_ctrl.GetValue())

    def _set_voice_settings_enabled(self, enabled: bool) -> None:
        """Dim the rate/volume/pitch/speed/character controls.

        They only affect *real synthesis*, so they are disabled until the voice
        is downloaded (when not downloaded, Preview plays a fixed sample clip).
        """
        for name in ("_rate_spin", "_vol_spin", "_pitch_spin", "_kok_spin", "_variant_choice"):
            ctrl = getattr(self, name, None)
            if ctrl is not None:
                ctrl.Enable(enabled)

    def _on_voice_selected(self) -> None:
        idx = self._voice_lb.GetSelection()
        wx = self._wx
        eng = self._current_engine_id()
        eng_ok = self._engine_available.get(eng, True)

        if idx == wx.NOT_FOUND or idx >= len(self._displayed_voices):
            self._detail_lbl.SetLabel("")
            self._preview_btn.Enable(False)
            self._set_voice_settings_enabled(False)
            return

        v = self._displayed_voices[idx]
        ready = self._voice_is_ready(eng, v)
        has_sample = bool(self._has_preview_sample(eng, v.id))
        accent = getattr(v, "accent", "")
        desc = getattr(v, "description", "")
        parts = [p for p in [accent, desc] if p]
        detail = " · ".join(parts)
        if not eng_ok:
            _NOT_READY_MSG = {
                "dectalk": "DECtalk is not installed. Use the download button to get it.",
                "piper": "Piper is not installed. Use the download button to get it.",
                "espeak": "eSpeak-NG is not installed. Use the download button to get it.",
                "kokoro": "Kokoro models are not downloaded. Use the download button to get them.",
            }
            hint = _NOT_READY_MSG.get(eng, f"{eng} is not available.")
            detail = f"{detail} — {hint}" if detail else hint
        elif not getattr(v, "installed", True):
            not_dl = "Not downloaded. Preview plays a sample; use Download Voice for full quality."
            detail = f"{detail} — {not_dl}" if detail else not_dl
        self._detail_lbl.SetLabel(detail)
        # Preview works when the voice is ready (real synthesis) or when a
        # bundled sample clip exists for it. Stays enabled whenever a preview
        # is actually running, even if the newly-selected row isn't ready --
        # otherwise the Stop button goes disabled out from under the user.
        self._preview_btn.Enable(ready or has_sample or self._previewing)
        # Rate/volume/pitch/speed/character apply to real synthesis only.
        self._set_voice_settings_enabled(ready)

    def _on_voice_key_down(self, event: object) -> None:
        wx = self._wx
        key = event.GetKeyCode()  # type: ignore[attr-defined]
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            self._do_preview()
        else:
            event.Skip()  # type: ignore[attr-defined]

    def _voice_is_ready(self, eng: str, voice: object) -> bool:
        """True when the engine is installed AND the voice's model is present."""
        return self._engine_available.get(eng, True) and bool(getattr(voice, "installed", True))

    def _do_preview(self) -> None:
        if self._previewing:
            self._stop_preview()
            return
        idx = self._voice_lb.GetSelection()
        wx = self._wx
        if idx == wx.NOT_FOUND or idx >= len(self._displayed_voices):
            return
        eng = self._current_engine_id()
        v = self._displayed_voices[idx]
        ready = self._voice_is_ready(eng, v)
        # Downloaded -> real synthesis with the model; not downloaded -> the
        # bundled pre-recorded sample (if one ships for this voice).
        if not ready and not self._has_preview_sample(eng, v.id):
            return
        voice_id = self._espeak_combined_voice_id(v.id) if eng == "espeak" else v.id
        self._preview_fn(eng, voice_id, live=ready, on_state_change=self._on_preview_state)

    def _on_preview_state(self, state: str) -> None:
        """Toggle the Preview button between its idle and Stop labels."""
        self._previewing = state in ("generating", "playing")
        label = "&Stop Preview" if self._previewing else "&Preview Selected Voice"
        self._preview_btn.SetLabel(label)

    def _stop_preview(self) -> None:
        """Cancel the active preview via the same path a new preview would use."""
        self._preview_stop_fn()
        self._on_preview_state("idle")

    def _do_download(self) -> None:
        eng = self._current_engine_id()
        eng_ok = self._engine_available.get(eng, True)
        # If the engine binary itself is missing, request an engine download.
        if not eng_ok and eng in {"dectalk", "piper", "espeak"}:
            result = VoiceBrowserResult(
                action="download_engine",
                engine=eng,
                **self._collect_settings(eng),
            )
        else:
            idx = self._voice_lb.GetSelection()
            voice_id = ""
            if 0 <= idx < len(self._displayed_voices):
                voice_id = self._displayed_voices[idx].id
            result = VoiceBrowserResult(
                action="download",
                engine=eng,
                voice_id=voice_id,
                **self._collect_settings(eng),
            )
        self._dispatch_action(result)

    def _do_export(self) -> None:
        eng = self._current_engine_id()
        idx = self._voice_lb.GetSelection()
        voice_id = ""
        if 0 <= idx < len(self._displayed_voices):
            base_id = self._displayed_voices[idx].id
            voice_id = self._espeak_combined_voice_id(base_id) if eng == "espeak" else base_id
        result = VoiceBrowserResult(
            action="export",
            engine=eng,
            voice_id=voice_id,
            **self._collect_settings(eng),
        )
        self._dispatch_action(result)

    def _do_set_default(self) -> None:
        """Make the selected engine+voice the Read Aloud default without
        closing the dialog -- the same result OK produces, just explicit and
        reachable mid-session (#847 Set as Default)."""
        self._dispatch_action(self.collect_result())

    def _show_voice_context_menu(self) -> None:
        """Right-click on a voice row: the same actions as the buttons below,
        reached without leaving the list (keyboard: Shift+F10 / Menu key)."""
        wx = self._wx
        idx = self._voice_lb.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self._displayed_voices):
            return
        menu = wx.Menu()
        preview_item = menu.Append(wx.ID_ANY, "&Preview")
        default_item = menu.Append(wx.ID_ANY, "Set as &Default")
        download_item = menu.Append(wx.ID_ANY, "&Download Voice...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._do_preview(), preview_item)
        menu.Bind(wx.EVT_MENU, lambda _e: self._do_set_default(), default_item)
        menu.Bind(wx.EVT_MENU, lambda _e: self._do_download(), download_item)
        self._voice_lb.PopupMenu(menu)
        menu.Destroy()

    def _dispatch_action(self, result: VoiceBrowserResult) -> None:
        if self._embed_mode and self._on_action is not None:
            self._on_action(result)
        else:
            self._result = result
            self.dialog.EndModal(self._wx.ID_OK)  # type: ignore[union-attr]

    def _collect_settings(self, eng: str) -> dict:
        s = self._settings
        return {
            "rate": self._rate_spin.GetValue(),
            "volume": self._vol_spin.GetValue(),
            "pitch": self._pitch_spin.GetValue(),
            "dectalk_rate": (
                self._rate_spin.GetValue()
                if eng == "dectalk"
                else getattr(s, "read_aloud_dectalk_rate", 200)
            ),
            "kokoro_speed": self._kok_spin.GetValue(),
            "espeak_rate": (
                self._rate_spin.GetValue()
                if eng == "espeak"
                else getattr(s, "read_aloud_espeak_rate", 175)
            ),
        }

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def collect_result(self) -> VoiceBrowserResult:
        """Return the current selection as a 'select' result (for embed mode)."""
        eng = self._current_engine_id()
        idx = self._voice_lb.GetSelection()
        voice_id = ""
        if 0 <= idx < len(self._displayed_voices):
            base_id = self._displayed_voices[idx].id
            voice_id = self._espeak_combined_voice_id(base_id) if eng == "espeak" else base_id
        return VoiceBrowserResult(
            action="select",
            engine=eng,
            voice_id=voice_id,
            **self._collect_settings(eng),
        )

    def show(self, show_modal_dialog: Callable) -> VoiceBrowserResult | None:
        """Open the dialog. Returns what the user chose, or None on cancel."""
        if self._embed_mode:
            raise RuntimeError("VoiceBrowserDialog.show() cannot be called in embed mode")
        focus_primary_control(self.dialog)
        result_code = show_modal_dialog(self.dialog, "Manage Voices & Reading Aloud")
        if result_code == self._wx.ID_OK and self._result is None:
            # User clicked OK without using a special action button.
            eng = self._current_engine_id()
            idx = self._voice_lb.GetSelection()
            voice_id = ""
            if 0 <= idx < len(self._displayed_voices):
                base_id = self._displayed_voices[idx].id
                voice_id = self._espeak_combined_voice_id(base_id) if eng == "espeak" else base_id
            self._result = VoiceBrowserResult(
                action="select",
                engine=eng,
                voice_id=voice_id,
                **self._collect_settings(eng),
            )
        self.dialog.Destroy()  # type: ignore[union-attr]
        return self._result
