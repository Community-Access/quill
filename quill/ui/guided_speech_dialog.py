"""Guided offline-speech setup — a single accessible screen in the Download
Optional Components hub.

The user picks an engine (Faster Whisper vs whisper.cpp) with a plain-language
explanation, then a model (smallest preselected so they're transcribing within a
minute; the best fit for their computer is marked). All the data comes from the
wx-free :mod:`quill.core.speech.guided_setup`, so this module is a thin renderer
and the caller orchestrates the actual install of the returned choice.

Everything on one screen (no wizard paging) is deliberate: it is simpler and more
predictable for a screen-reader user than multi-step navigation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from quill.core.speech.guided_setup import ModelChoice, OfflineSpeechEngineOption
from quill.ui.dialog_contract import apply_modal_ids


class GuidedSpeechData(Protocol):
    """The wx-free data the dialog renders (backed by guided_setup)."""

    def engine_options(self) -> list[OfflineSpeechEngineOption]:
        """The offline STT engine choices, recommended first."""

    def models_for(self, engine_id: str) -> list[ModelChoice]:
        """Downloadable models for the chosen engine."""

    def recommended_engine(self) -> str:
        """The engine id to preselect."""

    def default_model(self, engine_id: str) -> str:
        """The model id to preselect for the engine (smallest, for a fast start)."""


def _model_label(model: ModelChoice) -> str:
    tag = "  (Recommended for your computer)" if model.recommended else ""
    return f"{model.display_name} — {model.size_text}{tag}"


def _engine_label(option: OfflineSpeechEngineOption) -> str:
    """A self-describing radio label so a screen reader announces the trade-off
    (and recommended/installed state) when the option gets focus, not just the name."""
    parts = [f"{option.name} — {option.tagline}"]
    if option.recommended:
        parts.append("(recommended)")
    if option.installed:
        parts.append("(installed)")
    return "  ".join(parts)


def show_guided_speech_setup(
    wx: Any,
    parent: Any,
    show_modal_dialog: Callable[[Any, str], int],
    data: GuidedSpeechData,
) -> tuple[str, str] | None:
    """Show the guided offline-speech picker.

    Returns ``(engine_id, model_id)`` to install, or ``None`` if cancelled.
    """
    options = data.engine_options()
    if not options:
        return None
    engine_ids = [o.engine_id for o in options]
    recommended = data.recommended_engine()
    start_index = engine_ids.index(recommended) if recommended in engine_ids else 0

    dialog = wx.Dialog(parent, title="Set up offline speech")
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(
        wx.StaticText(
            dialog,
            label=(
                "Offline speech lets QUILL transcribe and take dictation without "
                "the internet. Pick an engine, then a model."
            ),
        ),
        0,
        wx.ALL | wx.EXPAND,
        8,
    )

    # A wx.RadioBox is a single grouped, labelled radio control: the "Speech
    # engine" label is the accessible group name, and each choice is a radio
    # button within it (announced as "Speech engine grouping, <label>, radio
    # button N of M"). One column so arrow keys move top-to-bottom predictably.
    engine_labels = [_engine_label(o) for o in options]
    engine_box = wx.RadioBox(
        dialog,
        label="Speech engine",
        choices=engine_labels,
        majorDimension=1,
        style=wx.RA_SPECIFY_COLS,
        name="guided_speech_engine",
    )
    engine_box.SetSelection(start_index)
    root.Add(engine_box, 0, wx.ALL | wx.EXPAND, 8)

    engine_detail = wx.TextCtrl(
        dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL, size=(-1, 60)
    )
    root.Add(engine_detail, 0, wx.ALL | wx.EXPAND, 8)

    root.Add(wx.StaticText(dialog, label="&Model"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    model_list = wx.ListBox(dialog, name="guided_speech_model")
    root.Add(model_list, 1, wx.ALL | wx.EXPAND, 8)

    models_cache: dict[str, list[ModelChoice]] = {}

    def _models(engine_id: str) -> list[ModelChoice]:
        if engine_id not in models_cache:
            models_cache[engine_id] = data.models_for(engine_id)
        return models_cache[engine_id]

    def _refresh() -> None:
        opt = options[engine_box.GetSelection()]
        engine_detail.SetValue(opt.summary)
        models = _models(opt.engine_id)
        model_list.Set([_model_label(m) for m in models])
        if models:
            default_id = data.default_model(opt.engine_id)
            index = next((i for i, m in enumerate(models) if m.model_id == default_id), 0)
            model_list.SetSelection(index)

    engine_box.Bind(wx.EVT_RADIOBOX, lambda _e: _refresh())

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    install_btn = wx.Button(dialog, wx.ID_OK, label="&Install")
    cancel_btn = wx.Button(dialog, wx.ID_CANCEL, label="&Cancel")
    cancel_btn.SetDefault()
    buttons.AddStretchSpacer()
    for btn in (install_btn, cancel_btn):
        buttons.Add(btn, 0, wx.LEFT, 6)
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)

    dialog.SetSizerAndFit(root)
    _refresh()
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    engine_box.SetFocus()

    chosen: tuple[str, str] | None = None
    if show_modal_dialog(dialog, "Set up offline speech") == wx.ID_OK:
        opt = options[engine_box.GetSelection()]
        models = _models(opt.engine_id)
        sel = model_list.GetSelection()
        if models and 0 <= sel < len(models):
            chosen = (opt.engine_id, models[sel].model_id)
    dialog.Destroy()
    return chosen
