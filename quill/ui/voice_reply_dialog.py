"""Voice Reply Settings dialog: how Ask Quill answers a spoken question.

One place for the whole chain -- the reply mode, and the cloud voice used when
the mode is *AI voice*. Before this, the AI Voice provider/model/voice lived as
three unrelated rows in the generic settings list, which had a real defect: the
voice list was one flat catalog of every provider's voices, so you could pick a
Gemini voice while OpenAI was selected and only find out when synthesis failed.
Here the voice and model lists are rebuilt from the chosen provider, so an
impossible combination cannot be expressed.

Cost and privacy are stated in the dialog rather than in a footnote, because
"read the reply with the AI voice" is the one choice here that bills money and
sends the reply text off the machine. The estimate comes from
:func:`quill.core.ai.cloud_tts.estimate_cost_usd`, the same one the export flow
uses.

The caller owns the ``wx.Dialog`` (so the hardened modal path and
``apply_modal_ids`` stay in one place) and reads :attr:`result` after OK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.ai.voice_reply import mode_label
from quill.core.settings import VOICE_REPLY_MODES

#: (value, label) for the reply-mode radio box, in the dialog's order. Ordered
#: offline-first so the cheapest, most private options read first.
_MODE_CHOICES: tuple[tuple[str, str], ...] = (
    ("announce", "&Announce a short summary (offline, free)"),
    ("text", "Show as &text only, do not speak"),
    ("local_tts", "Read aloud with QUILL's own &voice (offline, free)"),
    ("ai_voice", "Read aloud with the A&I voice (cloud, billed per character)"),
)

#: A representative reply length for the standing cost estimate. Real replies
#: vary wildly, so this is labelled as "a typical reply" rather than presented
#: as a prediction.
_ESTIMATE_CHARS = 600


@dataclass(slots=True)
class VoiceReplyResult:
    """The values chosen in the dialog (applied to ``settings`` by the caller)."""

    reply_mode: str
    announce_limit: int
    provider: str
    model: str
    voice: str
    speed: float


class VoiceReplyDialog:
    """Builds the voice-reply controls and exposes the choice after OK."""

    def __init__(self, wx: Any, *, settings: Any, on_preview: Any = None) -> None:
        self._wx = wx
        self._settings = settings
        #: Optional callable(provider, model, voice, speed, text) -> None. The
        #: dialog never synthesises audio itself; previewing is the caller's job.
        self._on_preview = on_preview
        self.result: VoiceReplyResult | None = None
        self.dialog: Any = None
        self._outer_sizer: Any = None
        self._provider_ids: list[str] = []
        self._model_ids: list[str] = []
        self._voice_ids: list[str] = []

    # -- construction ---------------------------------------------------------

    def populate(self, dlg: Any) -> Any:
        wx = self._wx
        self.dialog = dlg
        outer = wx.BoxSizer(wx.VERTICAL)

        self._mode = wx.RadioBox(
            dlg,
            label="When I ask by voice, answer me with",
            choices=[label for _value, label in _MODE_CHOICES],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        outer.Add(self._mode, 0, wx.EXPAND | wx.ALL, 12)

        grid = wx.FlexGridSizer(0, 2, 8, 10)
        grid.AddGrowableCol(1, 1)

        def _add(label_text: str, factory: Any) -> Any:
            # Label BEFORE the control so it precedes its field in tab order --
            # the A11Y z-order contract (dialog z-order gate).
            grid.Add(wx.StaticText(dlg, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
            control = factory()
            grid.Add(control, 0, wx.EXPAND)
            return control

        self._announce_limit = _add(
            "Announcement &length (characters, 0 for the whole reply):",
            lambda: wx.SpinCtrl(dlg, min=0, max=2000),
        )
        self._provider = _add("AI voice &provider:", lambda: wx.Choice(dlg, choices=[]))
        self._model = _add("&Model:", lambda: wx.Choice(dlg, choices=[]))
        self._voice = _add("V&oice:", lambda: wx.Choice(dlg, choices=[]))
        self._speed = _add(
            "&Speed (0.25 to 4.0):",
            lambda: wx.SpinCtrlDouble(dlg, min=0.25, max=4.0, inc=0.05),
        )
        outer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self._preview = wx.Button(dlg, label="&Preview this voice")
        outer.Add(self._preview, 0, wx.LEFT | wx.TOP, 12)

        # A live, screen-reader-readable summary rather than a static footnote:
        # this is where the money and the privacy trade-off are stated.
        self._summary = wx.StaticText(dlg, label="")
        outer.Add(self._summary, 0, wx.EXPAND | wx.ALL, 12)

        dlg.Bind(wx.EVT_RADIOBOX, self._on_mode_changed, self._mode)
        dlg.Bind(wx.EVT_CHOICE, self._on_provider_changed, self._provider)
        dlg.Bind(wx.EVT_CHOICE, self._on_voice_changed, self._voice)
        dlg.Bind(wx.EVT_BUTTON, self._on_preview_clicked, self._preview)
        dlg.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._outer_sizer = outer
        return outer

    def finalize(self) -> None:
        s = self._settings
        self.dialog.SetSizerAndFit(self._outer_sizer)

        mode = str(getattr(s, "ai_voice_reply_mode", "announce"))
        values = [value for value, _label in _MODE_CHOICES]
        self._mode.SetSelection(values.index(mode) if mode in values else 0)
        self._announce_limit.SetValue(int(getattr(s, "ai_voice_reply_announce_limit", 140)))
        self._speed.SetValue(float(getattr(s, "ai_tts_speed", 1.0)))

        self._load_providers()
        self._refresh_provider_lists()
        self._sync_enabled()

    # -- catalogs -------------------------------------------------------------

    def _load_providers(self) -> None:
        """Fill the provider list from the cloud-TTS catalog.

        Degrades to a static pair if the optional AI modules are unavailable, so
        the dialog always opens -- the same posture as the settings table.
        """
        try:
            from quill.core.ai.cloud_tts import PROVIDERS, provider_label

            self._provider_ids = list(PROVIDERS)
            labels = [provider_label(p) for p in self._provider_ids]
        except Exception:  # noqa: BLE001 - dialog must open without the AI extras
            self._provider_ids = ["openai", "gemini"]
            labels = ["OpenAI", "Google Gemini"]
        self._provider.Set(labels)
        current = str(getattr(self._settings, "ai_tts_provider", "openai")).lower()
        self._provider.SetSelection(
            self._provider_ids.index(current) if current in self._provider_ids else 0
        )

    def _refresh_provider_lists(self) -> None:
        """Rebuild the model and voice lists for the selected provider.

        This is the point of the dialog: the flat settings list let a Gemini
        voice be chosen for OpenAI. Rebuilding per provider makes that
        unrepresentable rather than merely discouraged.
        """
        provider = self._selected_provider()
        try:
            from quill.core.ai.cloud_tts import default_model, default_voice, models_for, voices_for

            models = list(models_for(provider))
            voices = list(voices_for(provider))
            fallback_model = default_model(provider)
            fallback_voice = default_voice(provider)
        except Exception:  # noqa: BLE001 - keep the dialog usable
            models, voices, fallback_model, fallback_voice = [], [], "", ""

        self._model_ids = ["", *models]
        self._model.Set(["Provider default", *models])
        self._select(self._model, self._model_ids, getattr(self._settings, "ai_tts_model", ""))

        self._voice_ids = ["", *[vid for vid, _name in voices]]
        self._voice.Set(
            [f"Provider default ({fallback_voice})" if fallback_voice else "Provider default"]
            + [name for _vid, name in voices]
        )
        self._select(self._voice, self._voice_ids, getattr(self._settings, "ai_tts_voice", ""))
        self._update_summary(fallback_model or "")

    @staticmethod
    def _select(control: Any, ids: list[str], wanted: str) -> None:
        """Select *wanted* in *control*, falling back to the first entry.

        A voice saved for another provider simply is not in this list; falling
        back to the provider default is the honest outcome.
        """
        value = str(wanted or "")
        control.SetSelection(ids.index(value) if value in ids else 0)

    def _selected_provider(self) -> str:
        index = self._provider.GetSelection()
        if 0 <= index < len(self._provider_ids):
            return self._provider_ids[index]
        return "openai"

    def _selected(self, control: Any, ids: list[str]) -> str:
        index = control.GetSelection()
        return ids[index] if 0 <= index < len(ids) else ""

    def _selected_mode(self) -> str:
        index = self._mode.GetSelection()
        values = [value for value, _label in _MODE_CHOICES]
        return values[index] if 0 <= index < len(values) else "announce"

    # -- live state -----------------------------------------------------------

    def _sync_enabled(self) -> None:
        """Grey out what the chosen mode does not use.

        Disabled-but-present beats hidden: the controls keep their place, so the
        dialog does not reshuffle under a screen-reader user mid-review.
        """
        mode = self._selected_mode()
        self._announce_limit.Enable(mode == "announce")
        cloud = mode == "ai_voice"
        for control in (self._provider, self._model, self._voice, self._speed, self._preview):
            control.Enable(cloud)

    def _update_summary(self, default_model: str = "") -> None:
        mode = self._selected_mode()
        if mode != "ai_voice":
            self._summary.SetLabel(
                f"Replies come back as {mode_label(mode)}. "
                "Nothing is sent off this computer and nothing is billed."
            )
            return
        provider = self._selected_provider()
        model = self._selected(self._model, self._model_ids) or default_model
        try:
            from quill.core.ai.cloud_tts import estimate_cost_usd, format_cost, provider_label

            cost = format_cost(estimate_cost_usd(provider, model, _ESTIMATE_CHARS))
            label = provider_label(provider)
        except Exception:  # noqa: BLE001
            cost, label = "", provider
        estimate = (
            f" A typical {_ESTIMATE_CHARS}-character reply costs about {cost}." if cost else ""
        )
        self._summary.SetLabel(
            f"Replies are read aloud by {label}. The reply text is sent to "
            f"{label} to be spoken, and you are billed for it.{estimate}"
        )

    # -- events ---------------------------------------------------------------

    def _on_mode_changed(self, event: Any) -> None:
        self._sync_enabled()
        self._update_summary()
        event.Skip()

    def _on_provider_changed(self, event: Any) -> None:
        self._refresh_provider_lists()
        event.Skip()

    def _on_voice_changed(self, event: Any) -> None:
        self._update_summary()
        event.Skip()

    def _on_preview_clicked(self, event: Any) -> None:
        if self._on_preview is not None:
            self._on_preview(
                self._selected_provider(),
                self._selected(self._model, self._model_ids),
                self._selected(self._voice, self._voice_ids),
                float(self._speed.GetValue()),
                "This is how Quill will read your answers.",
            )
        event.Skip()

    def _on_ok(self, event: Any) -> None:
        self.result = VoiceReplyResult(
            reply_mode=self._selected_mode(),
            announce_limit=int(self._announce_limit.GetValue()),
            provider=self._selected_provider(),
            model=self._selected(self._model, self._model_ids),
            voice=self._selected(self._voice, self._voice_ids),
            speed=float(self._speed.GetValue()),
        )
        event.Skip()  # let the dialog close with ID_OK


__all__ = ["VOICE_REPLY_MODES", "VoiceReplyDialog", "VoiceReplyResult"]
