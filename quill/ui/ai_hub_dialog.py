"""AI Hub dialog — tabbed settings center for all AI features.

Tabs:
  1. Provider  — cloud/local provider, API key, model, host, test connection
  2. On-Device — Ollama URL and local model guidance
  3. Audio     — Deepgram API key, default max speakers (transcription/diarization)
  4. Advanced  — consent summary, network audit notes, safe mode, reset

This dialog is the single entry point for all AI configuration.
Settings are saved on OK; Cancel discards changes.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.i18n import _, lazy_gettext
from quill.ui.dialog_contract import apply_modal_ids

_PROVIDER_CHOICES: tuple[tuple[str, object], ...] = (
    ("off", lazy_gettext("Off (AI disabled)")),
    ("ollama", lazy_gettext("Ollama (local, free)")),
    ("openai", lazy_gettext("OpenAI")),
    ("claude", lazy_gettext("Anthropic Claude")),
    ("gemini", lazy_gettext("Google Gemini")),
    ("openrouter", lazy_gettext("OpenRouter")),
    ("ollama_cloud", lazy_gettext("Ollama Cloud")),
    ("custom", lazy_gettext("Custom (OpenAI-compatible)")),
)

_DEEPGRAM_KEY_CRED_TARGET = "QUILL_DEEPGRAM_API_KEY"
_DEEPGRAM_MAX_SPEAKERS_KEY = "deepgram_default_max_speakers"


def _load_deepgram_key() -> str:
    try:
        from quill.platform.windows.credential_manager import credential_load

        return credential_load(_DEEPGRAM_KEY_CRED_TARGET) or ""
    except Exception:  # noqa: BLE001
        return ""


def _save_deepgram_key(key: str) -> None:
    try:
        from quill.platform.windows.credential_manager import credential_delete, credential_save

        if key.strip():
            credential_save(_DEEPGRAM_KEY_CRED_TARGET, key.strip())
        else:
            credential_delete(_DEEPGRAM_KEY_CRED_TARGET)
    except Exception:  # noqa: BLE001
        pass


def _load_deepgram_max_speakers() -> int:
    try:
        from quill.core.paths import app_data_dir
        from quill.core.storage import read_json

        data = read_json(app_data_dir() / "ai_audio_settings.json", default={})
        return int(data.get(_DEEPGRAM_MAX_SPEAKERS_KEY, 6))
    except Exception:  # noqa: BLE001
        return 6


def _save_deepgram_max_speakers(value: int) -> None:
    try:
        from quill.core.paths import app_data_dir
        from quill.core.storage import write_json_atomic

        path = app_data_dir() / "ai_audio_settings.json"
        try:
            from quill.core.storage import read_json

            data = dict(read_json(path, default={}))
        except Exception:  # noqa: BLE001
            data = {}
        data[_DEEPGRAM_MAX_SPEAKERS_KEY] = value
        write_json_atomic(path, data)
    except Exception:  # noqa: BLE001
        pass


class AIHubDialog:
    """Tabbed AI configuration hub.

    Parameters
    ----------
    parent:
        wx parent window.
    show_modal_dialog:
        MainFrame's _show_modal_dialog gate.
    announce:
        Optional callback(message) for status bar announcements.
    open_advanced_connection:
        Optional callback to open the full AssistantConnectionDialog
        for providers not exposed in the simplified Tab 1.
    """

    def __init__(
        self,
        parent: object,
        show_modal_dialog: Callable,
        announce: Callable[[str], None] | None = None,
        open_advanced_connection: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._show_modal = show_modal_dialog
        self._announce = announce or (lambda _m: None)
        self._open_advanced = open_advanced_connection

        from quill.core.assistant_ai import (
            load_assistant_connection_settings,
            load_provider_api_key,
        )

        self._settings = load_assistant_connection_settings()
        self._provider_key = load_provider_api_key(self._settings.provider or "ollama")
        self._deepgram_key = _load_deepgram_key()
        self._deepgram_max_speakers = _load_deepgram_max_speakers()

        from quill.core.ai.custom_instructions import load_instructions

        self._instructions = load_instructions()

        from quill.core.settings import load_settings as _load_settings

        _vsettings = _load_settings()
        self._vision_disabled: set[str] = set(_vsettings.vision_disabled_builtin_styles)
        self._vision_overrides: dict[str, str] = dict(
            getattr(_vsettings, "vision_builtin_overrides", {})
        )

        self.dialog = wx.Dialog(
            parent,
            title=_("AI Hub"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(740, 600))
        self._build_ui()

    # ------------------------------------------------------------------
    # UI build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        self._notebook = wx.Notebook(self.dialog)
        root.Add(self._notebook, 1, wx.EXPAND | wx.ALL, 8)

        self._notebook.AddPage(self._build_provider_tab(), _("Provider"))
        self._notebook.AddPage(self._build_on_device_tab(), _("On-Device"))
        self._notebook.AddPage(self._build_audio_tab(), _("Audio Services"))
        self._notebook.AddPage(self._build_instructions_tab(), _("Instructions"))
        self._notebook.AddPage(self._build_advanced_tab(), _("Advanced"))

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, label=_("&OK"))
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, label=_("Cancel"))
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        apply_modal_ids(
            self.dialog,
            affirmative_id=ok_btn.GetId(),
            escape_id=cancel_btn.GetId(),
        )
        root.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        wx.CallAfter(self._notebook.SetFocus)

    # ------------------------------------------------------------------
    # Tab 1: Provider
    # ------------------------------------------------------------------

    def _build_provider_tab(self) -> object:
        wx = self._wx
        panel = wx.Panel(self._notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Provider selector
        sizer.Add(wx.StaticText(panel, label=_("AI provider:")), 0, wx.ALL, 6)
        provider_ids = [pid for pid, _label in _PROVIDER_CHOICES]
        provider_labels = [label for _pid, label in _PROVIDER_CHOICES]
        self._provider_choice = wx.Choice(panel, choices=provider_labels)
        self._provider_choice.SetName("AI provider")
        try:
            idx = provider_ids.index(self._settings.provider or "ollama")
        except ValueError:
            idx = 1
        self._provider_choice.SetSelection(idx)
        sizer.Add(self._provider_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # API key
        sizer.Add(wx.StaticText(panel, label=_("API key:")), 0, wx.LEFT | wx.TOP, 6)
        key_row = wx.BoxSizer(wx.HORIZONTAL)
        self._key_ctrl = wx.TextCtrl(
            panel,
            value=self._provider_key,
            style=wx.TE_PASSWORD,
        )
        self._key_ctrl.SetName("API key")
        self._reveal_btn = wx.ToggleButton(panel, label=_("Show"))
        key_row.Add(self._key_ctrl, 1, wx.RIGHT, 4)
        key_row.Add(self._reveal_btn, 0)
        sizer.Add(key_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Host (shown only for Ollama / custom)
        sizer.Add(
            wx.StaticText(panel, label=_("Host URL (Ollama/custom only):")), 0, wx.LEFT | wx.TOP, 6
        )
        self._host_ctrl = wx.TextCtrl(panel, value=self._settings.host or "")
        self._host_ctrl.SetName("Host URL")
        sizer.Add(self._host_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Model
        sizer.Add(wx.StaticText(panel, label=_("Model:")), 0, wx.LEFT | wx.TOP, 6)
        self._model_ctrl = wx.TextCtrl(panel, value=self._settings.model or "")
        self._model_ctrl.SetName("Model")
        sizer.Add(self._model_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Test connection button + result
        test_row = wx.BoxSizer(wx.HORIZONTAL)
        self._test_btn = wx.Button(panel, label=_("Test &Connection"))
        self._test_label = wx.StaticText(panel, label="")
        test_row.Add(self._test_btn, 0, wx.RIGHT, 8)
        test_row.Add(self._test_label, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(test_row, 0, wx.ALL, 6)

        # Full settings link
        if self._open_advanced is not None:
            adv_btn = wx.Button(panel, label=_("Full Connection Settings..."))
            sizer.Add(adv_btn, 0, wx.LEFT | wx.BOTTOM, 6)
            adv_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_advanced())

        panel.SetSizer(sizer)
        self._reveal_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_reveal_key)
        self._test_btn.Bind(wx.EVT_BUTTON, self._on_test_connection)
        return panel

    # ------------------------------------------------------------------
    # Tab 2: On-Device
    # ------------------------------------------------------------------

    def _build_on_device_tab(self) -> object:
        wx = self._wx
        panel = wx.Panel(self._notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = _(
            "QUILL supports on-device AI via Ollama. Ollama runs large language models "
            "locally on your machine — no API key or internet connection needed.\n\n"
            "Install Ollama from https://ollama.com, pull a model "
            "(e.g. 'ollama pull llama3.2:1b-instruct-q4_K_M'), then select "
            "'Ollama (local)' on the Provider tab and set the host below."
        )
        intro_label = wx.StaticText(panel, label=intro)
        intro_label.Wrap(620)
        sizer.Add(intro_label, 0, wx.ALL, 8)

        sizer.Add(wx.StaticText(panel, label=_("Ollama base URL:")), 0, wx.LEFT, 8)
        self._ollama_url_ctrl = wx.TextCtrl(
            panel,
            value=self._settings.host
            if "localhost" in (self._settings.host or "")
            else "http://localhost:11434",
        )
        self._ollama_url_ctrl.SetName("Ollama base URL")
        sizer.Add(self._ollama_url_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)

        note = wx.StaticText(
            panel,
            label=_(
                "Recommended models (2025):\n"
                "  llama3.2:1b-instruct-q4_K_M  — fast, 1 GB\n"
                "  llama3.2:3b-instruct-q4_K_M  — better quality, 2 GB\n"
                "  mistral:7b-instruct-q4_K_M   — higher quality, 4 GB\n\n"
                "Vision models (for AI Image Description):\n"
                "  llava:7b-v1.6-mistral-q4_K_M"
            ),
        )
        sizer.Add(note, 0, wx.LEFT | wx.BOTTOM, 8)

        panel.SetSizer(sizer)
        return panel

    # ------------------------------------------------------------------
    # Tab 3: Audio Services  (P4-4)
    # ------------------------------------------------------------------

    def _build_audio_tab(self) -> object:
        wx = self._wx
        panel = wx.Panel(self._notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = _(
            "Audio transcription uses OpenAI Whisper (configure your OpenAI API key on "
            "the Provider tab). Speaker diarization (identifying who said what) uses "
            "Deepgram Nova-3 and requires a separate Deepgram API key."
        )
        intro_label = wx.StaticText(panel, label=intro)
        intro_label.Wrap(620)
        sizer.Add(intro_label, 0, wx.ALL, 8)

        # Deepgram key
        sizer.Add(
            wx.StaticText(panel, label=_("Deepgram API key (for speaker diarization):")),
            0,
            wx.LEFT | wx.TOP,
            8,
        )
        dg_row = wx.BoxSizer(wx.HORIZONTAL)
        self._deepgram_key_ctrl = wx.TextCtrl(
            panel,
            value=self._deepgram_key,
            style=wx.TE_PASSWORD,
        )
        self._deepgram_key_ctrl.SetName("Deepgram API key")
        self._dg_reveal_btn = wx.ToggleButton(panel, label=_("Show"))
        dg_row.Add(self._deepgram_key_ctrl, 1, wx.RIGHT, 4)
        dg_row.Add(self._dg_reveal_btn, 0)
        sizer.Add(dg_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Max speakers default
        sizer.Add(
            wx.StaticText(panel, label=_("Default maximum speakers (2-20):")),
            0,
            wx.LEFT | wx.TOP,
            8,
        )
        self._max_speakers_spin = wx.SpinCtrl(
            panel,
            min=2,
            max=20,
            initial=self._deepgram_max_speakers,
        )
        self._max_speakers_spin.SetName("Default maximum speakers")
        sizer.Add(self._max_speakers_spin, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        note = wx.StaticText(
            panel,
            label=_(
                "Privacy note: audio is sent to Deepgram's cloud for diarization. "
                "Set this to Off on the Provider tab to keep all processing local. "
                "Transcription (without diarization) stays within OpenAI."
            ),
        )
        note.Wrap(620)
        sizer.Add(note, 0, wx.LEFT | wx.BOTTOM, 8)

        panel.SetSizer(sizer)
        self._dg_reveal_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_reveal_dg_key)
        return panel

    # ------------------------------------------------------------------
    # Tab 4: Instructions — per-task custom prompts
    # ------------------------------------------------------------------

    def _build_instructions_tab(self) -> object:
        wx = self._wx
        panel = wx.Panel(self._notebook)
        outer = wx.BoxSizer(wx.VERTICAL)

        sub = wx.Notebook(panel)
        sub.AddPage(self._build_writing_tasks_page(sub), _("Writing Tasks"))
        sub.AddPage(self._build_image_styles_page(sub), _("Image Styles"))
        outer.Add(sub, 1, wx.EXPAND | wx.ALL, 6)

        panel.SetSizer(outer)
        return panel

    # ------------------------------------------------------------------
    # Instructions sub-page: Writing Tasks
    # ------------------------------------------------------------------

    def _build_writing_tasks_page(self, parent: object) -> object:
        wx = self._wx
        page = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(page, label=_("Task:")), 0, wx.BOTTOM, 4)
        self._inst_list = wx.ListBox(page, style=wx.LB_SINGLE)
        self._inst_list.SetName("AI tasks")
        self._inst_task_ids: list[str] = []
        for task_id, inst in self._instructions.items():
            marker = " *" if inst.is_customised() else ""
            self._inst_list.Append(f"{inst.title}{marker}")
            self._inst_task_ids.append(task_id)
        left.Add(self._inst_list, 1, wx.EXPAND)
        sizer.Add(left, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticLine(page, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 4)

        right = wx.BoxSizer(wx.VERTICAL)
        self._inst_enabled_chk = wx.CheckBox(
            page, label=_("Enable custom instructions for this task")
        )
        self._inst_enabled_chk.SetName("Enable instructions")
        right.Add(self._inst_enabled_chk, 0, wx.ALL, 6)

        right.Add(
            wx.StaticText(
                page,
                label=_("Instructions (prepended to every AI call for this task):"),
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            6,
        )
        self._inst_editor = wx.TextCtrl(page, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._inst_editor.SetName("Instruction text")
        self._inst_editor.SetMinSize(wx.Size(400, 200))
        right.Add(self._inst_editor, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        right.Add(wx.StaticLine(page), 0, wx.EXPAND | wx.ALL, 6)
        right.Add(
            wx.StaticText(page, label=_("Built-in default (shown when editor is empty):")),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            6,
        )
        self._default_display = wx.TextCtrl(page, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._default_display.SetName("Built-in default instruction")
        self._default_display.SetMinSize(wx.Size(400, 120))
        right.Add(self._default_display, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._inst_reset_btn = wx.Button(page, label=_("Reset to &Default"))
        self._inst_copy_default_btn = wx.Button(page, label=_("Copy Default to &Editor"))
        btn_row.Add(self._inst_reset_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._inst_copy_default_btn, 0)
        right.Add(btn_row, 0, wx.LEFT | wx.BOTTOM, 6)

        hint = wx.StaticText(
            page,
            label=_(
                "Tip: leave the editor empty to use the built-in default. "
                "A * next to the task name means you have a custom override."
            ),
        )
        hint.Wrap(420)
        right.Add(hint, 0, wx.LEFT | wx.BOTTOM, 6)

        sizer.Add(right, 1, wx.EXPAND | wx.ALL, 8)
        page.SetSizer(sizer)

        self._inst_list.Bind(wx.EVT_LISTBOX, self._on_inst_task_selected)
        self._inst_enabled_chk.Bind(wx.EVT_CHECKBOX, self._on_inst_enabled_changed)
        self._inst_editor.Bind(wx.EVT_TEXT, self._on_inst_text_changed)
        self._inst_reset_btn.Bind(wx.EVT_BUTTON, self._on_inst_reset)
        self._inst_copy_default_btn.Bind(wx.EVT_BUTTON, self._on_inst_copy_default)

        if self._inst_task_ids:
            self._inst_list.SetSelection(0)
            wx.CallAfter(self._load_instruction_into_editor, self._inst_task_ids[0])

        return page

    # ------------------------------------------------------------------
    # Instructions sub-page: Image Styles
    # ------------------------------------------------------------------

    def _build_image_styles_page(self, parent: object) -> object:
        wx = self._wx
        from quill.core.ai.vision_prompts import BUILTIN_PROMPT_STYLES

        page = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(page, label=_("Style:")), 0, wx.BOTTOM, 4)
        self._img_list = wx.ListBox(page, style=wx.LB_SINGLE)
        self._img_list.SetName("Image description styles")
        self._img_style_ids: list[str] = []
        for style in BUILTIN_PROMPT_STYLES:
            sid = style["id"]
            marker = " *" if sid in self._vision_overrides else ""
            disabled_mark = " [hidden]" if sid in self._vision_disabled else ""
            self._img_list.Append(f"{style['title']}{marker}{disabled_mark}")
            self._img_style_ids.append(sid)
        left.Add(self._img_list, 1, wx.EXPAND)
        sizer.Add(left, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticLine(page, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 4)

        right = wx.BoxSizer(wx.VERTICAL)
        self._img_enabled_chk = wx.CheckBox(
            page, label=_("Include this style in the image style picker")
        )
        self._img_enabled_chk.SetName("Include in picker")
        right.Add(self._img_enabled_chk, 0, wx.ALL, 6)

        right.Add(
            wx.StaticText(
                page, label=_("Override prompt text (leave empty to use the built-in default):")
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            6,
        )
        self._img_editor = wx.TextCtrl(page, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self._img_editor.SetName("Image prompt override")
        self._img_editor.SetMinSize(wx.Size(400, 200))
        right.Add(self._img_editor, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        right.Add(wx.StaticLine(page), 0, wx.EXPAND | wx.ALL, 6)
        right.Add(
            wx.StaticText(page, label=_("Built-in default prompt:")),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            6,
        )
        self._img_default_display = wx.TextCtrl(page, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._img_default_display.SetName("Built-in image prompt")
        self._img_default_display.SetMinSize(wx.Size(400, 120))
        right.Add(self._img_default_display, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._img_reset_btn = wx.Button(page, label=_("Reset to &Default"))
        self._img_copy_default_btn = wx.Button(page, label=_("Copy Default to &Editor"))
        btn_row.Add(self._img_reset_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._img_copy_default_btn, 0)
        right.Add(btn_row, 0, wx.LEFT | wx.BOTTOM, 6)

        hint = wx.StaticText(
            page,
            label=_(
                "Tip: leave the editor empty to use the shipped prompt. "
                "A * means you have a custom override. Manage custom styles via "
                "Settings > AI > Image Prompt Styles."
            ),
        )
        hint.Wrap(420)
        right.Add(hint, 0, wx.LEFT | wx.BOTTOM, 6)

        sizer.Add(right, 1, wx.EXPAND | wx.ALL, 8)
        page.SetSizer(sizer)

        self._img_list.Bind(wx.EVT_LISTBOX, self._on_img_style_selected)
        self._img_enabled_chk.Bind(wx.EVT_CHECKBOX, self._on_img_enabled_changed)
        self._img_editor.Bind(wx.EVT_TEXT, self._on_img_text_changed)
        self._img_reset_btn.Bind(wx.EVT_BUTTON, self._on_img_reset)
        self._img_copy_default_btn.Bind(wx.EVT_BUTTON, self._on_img_copy_default)

        if self._img_style_ids:
            self._img_list.SetSelection(0)
            wx.CallAfter(self._load_img_style_into_editor, self._img_style_ids[0])

        return page

    # ------------------------------------------------------------------
    # Writing Tasks helpers
    # ------------------------------------------------------------------

    def _selected_inst_task_id(self) -> str | None:
        idx = self._inst_list.GetSelection()
        if idx < 0 or idx >= len(self._inst_task_ids):
            return None
        return self._inst_task_ids[idx]

    def _load_instruction_into_editor(self, task_id: str) -> None:
        inst = self._instructions.get(task_id)
        if inst is None:
            return
        self._inst_editor.ChangeValue(inst.user_prompt)
        self._default_display.ChangeValue(inst.default_prompt)
        self._inst_enabled_chk.SetValue(inst.enabled)

    def _on_inst_task_selected(self, event: object) -> None:
        task_id = self._selected_inst_task_id()
        if task_id:
            self._load_instruction_into_editor(task_id)

    def _on_inst_enabled_changed(self, event: object) -> None:
        task_id = self._selected_inst_task_id()
        if task_id and task_id in self._instructions:
            self._instructions[task_id].enabled = self._inst_enabled_chk.GetValue()

    def _on_inst_text_changed(self, event: object) -> None:
        task_id = self._selected_inst_task_id()
        if task_id and task_id in self._instructions:
            self._instructions[task_id].user_prompt = self._inst_editor.GetValue()
            self._refresh_inst_list_item(task_id)

    def _refresh_inst_list_item(self, task_id: str) -> None:
        idx = self._inst_task_ids.index(task_id) if task_id in self._inst_task_ids else -1
        if idx < 0:
            return
        inst = self._instructions[task_id]
        marker = " *" if inst.is_customised() else ""
        self._inst_list.SetString(idx, f"{inst.title}{marker}")

    def _on_inst_reset(self, event: object) -> None:
        task_id = self._selected_inst_task_id()
        if task_id and task_id in self._instructions:
            self._instructions[task_id].reset_to_default()
            self._inst_editor.ChangeValue("")
            self._refresh_inst_list_item(task_id)

    def _on_inst_copy_default(self, event: object) -> None:
        default_text = self._default_display.GetValue()
        if default_text:
            self._inst_editor.SetValue(default_text)

    # ------------------------------------------------------------------
    # Image Styles helpers
    # ------------------------------------------------------------------

    def _selected_img_style_id(self) -> str | None:
        idx = self._img_list.GetSelection()
        if idx < 0 or idx >= len(self._img_style_ids):
            return None
        return self._img_style_ids[idx]

    def _load_img_style_into_editor(self, style_id: str) -> None:
        from quill.core.ai.vision_prompts import BUILTIN_PROMPT_BY_ID

        default_text = BUILTIN_PROMPT_BY_ID.get(style_id, "")
        self._img_default_display.ChangeValue(default_text)
        self._img_editor.ChangeValue(self._vision_overrides.get(style_id, ""))
        self._img_enabled_chk.SetValue(style_id not in self._vision_disabled)

    def _on_img_style_selected(self, event: object) -> None:
        style_id = self._selected_img_style_id()
        if style_id:
            self._load_img_style_into_editor(style_id)

    def _on_img_enabled_changed(self, event: object) -> None:
        style_id = self._selected_img_style_id()
        if style_id is None:
            return
        if self._img_enabled_chk.GetValue():
            self._vision_disabled.discard(style_id)
        else:
            self._vision_disabled.add(style_id)
        self._refresh_img_list_item(style_id)

    def _on_img_text_changed(self, event: object) -> None:
        style_id = self._selected_img_style_id()
        if style_id is None:
            return
        text = self._img_editor.GetValue().strip()
        if text:
            self._vision_overrides[style_id] = text
        else:
            self._vision_overrides.pop(style_id, None)
        self._refresh_img_list_item(style_id)

    def _refresh_img_list_item(self, style_id: str) -> None:
        from quill.core.ai.vision_prompts import BUILTIN_TITLE_BY_ID

        idx = self._img_style_ids.index(style_id) if style_id in self._img_style_ids else -1
        if idx < 0:
            return
        title = BUILTIN_TITLE_BY_ID.get(style_id, style_id)
        marker = " *" if style_id in self._vision_overrides else ""
        disabled_mark = " [hidden]" if style_id in self._vision_disabled else ""
        self._img_list.SetString(idx, f"{title}{marker}{disabled_mark}")

    def _on_img_reset(self, event: object) -> None:
        style_id = self._selected_img_style_id()
        if style_id:
            self._vision_overrides.pop(style_id, None)
            self._img_editor.ChangeValue("")
            self._refresh_img_list_item(style_id)

    def _on_img_copy_default(self, event: object) -> None:
        default_text = self._img_default_display.GetValue()
        if default_text:
            self._img_editor.SetValue(default_text)

    # ------------------------------------------------------------------
    # Tab 5: Advanced  (P7-1)
    # ------------------------------------------------------------------

    def _build_advanced_tab(self) -> object:
        wx = self._wx
        panel = wx.Panel(self._notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        consent_text = _(
            "Data sent to cloud AI providers\n"
            "--------------------------------\n"
            "When cloud AI is enabled, QUILL sends your document text or selection "
            "to the provider you configured (e.g. OpenAI, Claude). The following "
            "operations send data:\n\n"
            "  - Ask Quill chat\n"
            "  - Rewrite, Summarize, Expand, Grammar check, Spell check\n"
            "  - AI Translate (when using AI provider, not LibreTranslate)\n"
            "  - AI Thesaurus\n"
            "  - Document Q&A\n"
            "  - TTS Read Aloud (text only, no document metadata)\n"
            "  - Transcribe / Translate Audio (audio file bytes)\n\n"
            "QUILL never sends your API key to any service other than the configured "
            "provider, never tracks usage, and never stores responses externally."
        )
        consent_label = wx.StaticText(panel, label=consent_text)
        consent_label.Wrap(620)
        sizer.Add(consent_label, 0, wx.ALL, 8)

        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        reset_btn = wx.Button(panel, label=_("&Reset AI Settings to Defaults"))
        sizer.Add(reset_btn, 0, wx.LEFT | wx.BOTTOM, 8)

        safe_mode_label = wx.StaticText(
            panel,
            label=_(
                "Safe Mode: Launch with --safe-mode or set QUILL_SAFE_MODE=1 to "
                "disable all AI features and network calls at startup. "
                "This is useful for troubleshooting or privacy-sensitive environments."
            ),
        )
        safe_mode_label.Wrap(620)
        sizer.Add(safe_mode_label, 0, wx.LEFT | wx.BOTTOM, 8)

        panel.SetSizer(sizer)
        reset_btn.Bind(wx.EVT_BUTTON, self._on_reset)
        return panel

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_reveal_key(self, event: object) -> None:
        if self._reveal_btn.GetValue():
            self._key_ctrl.SetWindowStyleFlag(0)
            self._reveal_btn.SetLabel(_("Hide"))
        else:
            self._key_ctrl.SetWindowStyleFlag(self._wx.TE_PASSWORD)
            self._reveal_btn.SetLabel(_("Show"))
        self._key_ctrl.Refresh()

    def _on_reveal_dg_key(self, event: object) -> None:
        if self._dg_reveal_btn.GetValue():
            self._deepgram_key_ctrl.SetWindowStyleFlag(0)
            self._dg_reveal_btn.SetLabel(_("Hide"))
        else:
            self._deepgram_key_ctrl.SetWindowStyleFlag(self._wx.TE_PASSWORD)
            self._dg_reveal_btn.SetLabel(_("Show"))
        self._deepgram_key_ctrl.Refresh()

    def _on_advanced(self) -> None:
        if self._open_advanced:
            self._open_advanced()

    def _on_test_connection(self, event: object) -> None:
        import threading

        provider_idx = self._provider_choice.GetSelection()
        provider = _PROVIDER_CHOICES[provider_idx][0] if provider_idx >= 0 else "ollama"
        api_key = self._key_ctrl.GetValue().strip()
        host = self._host_ctrl.GetValue().strip()
        model = self._model_ctrl.GetValue().strip()

        self._test_label.SetLabel(_("Testing..."))
        self._test_btn.Enable(False)

        from quill.core.assistant_ai import AssistantConnectionSettings

        conn = AssistantConnectionSettings(provider=provider, host=host, model=model)

        def _run() -> None:
            import wx as _wx

            try:
                from quill.core.assistant_ai import generate_assistant_response

                text, error = generate_assistant_response(
                    conn,
                    api_key,
                    "Reply with only the word OK.",
                    max_tokens=10,
                    timeout_seconds=15.0,
                )
                if error:
                    msg = _("Failed: {error}").format(error=error)
                else:
                    msg = _("Connection OK.")
            except Exception as exc:  # noqa: BLE001
                msg = _("Error: {exc}").format(exc=exc)
            _wx.CallAfter(self._on_test_done, msg)

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _on_test_done(self, message: str) -> None:
        self._test_label.SetLabel(message)
        self._test_btn.Enable(True)

    def _on_reset(self, event: object) -> None:
        wx = self._wx
        result = wx.MessageBox(  # GATE-41-OK: standalone dialog  # MSGBOX-OK: standalone dialog
            _(
                "Reset all AI settings to defaults? This clears the provider, model, and host "
                "settings (but not stored API keys)."
            ),
            _("Reset AI Settings"),
            wx.YES_NO | wx.ICON_WARNING,
            self.dialog,
        )
        if result != wx.YES:
            return
        from quill.core.assistant_ai import (
            AssistantConnectionSettings,
            save_assistant_connection_settings,
        )

        save_assistant_connection_settings(AssistantConnectionSettings())
        self._announce(_("AI settings reset to defaults."))
        self.dialog.EndModal(wx.ID_OK)

    def _on_ok(self, event: object) -> None:
        provider_idx = self._provider_choice.GetSelection()
        provider = _PROVIDER_CHOICES[provider_idx][0] if provider_idx >= 0 else "ollama"
        api_key = self._key_ctrl.GetValue().strip()
        host = self._host_ctrl.GetValue().strip() or None
        model = self._model_ctrl.GetValue().strip()

        # Ollama URL from on-device tab overrides if provider is ollama
        ollama_url = self._ollama_url_ctrl.GetValue().strip()
        if provider == "ollama" and ollama_url:
            host = ollama_url

        from quill.core.assistant_ai import (
            AssistantConnectionSettings,
            save_assistant_connection_settings,
            save_provider_api_key,
        )

        settings = AssistantConnectionSettings(
            provider=provider,
            host=host or "",
            model=model,
        )
        save_assistant_connection_settings(settings)
        if api_key:
            save_provider_api_key(provider, api_key)

        # Audio settings
        _save_deepgram_key(self._deepgram_key_ctrl.GetValue())
        _save_deepgram_max_speakers(self._max_speakers_spin.GetValue())

        # Custom instructions — flush any in-progress edit before saving
        task_id = self._selected_inst_task_id()
        if task_id and task_id in self._instructions:
            self._instructions[task_id].user_prompt = self._inst_editor.GetValue()
        from quill.core.ai.custom_instructions import save_instructions

        save_instructions(self._instructions)

        # Image style overrides + enabled state
        img_style_id = self._selected_img_style_id()
        if img_style_id:
            text = self._img_editor.GetValue().strip()
            if text:
                self._vision_overrides[img_style_id] = text
            else:
                self._vision_overrides.pop(img_style_id, None)
        from quill.core.settings import (
            load_settings as _load_settings2,
        )
        from quill.core.settings import (
            save_settings as _save_settings,
        )

        _vsettings = _load_settings2()
        _vsettings.vision_disabled_builtin_styles = sorted(self._vision_disabled)
        _vsettings.vision_builtin_overrides = dict(self._vision_overrides)
        if _vsettings.vision_default_prompt_style in self._vision_disabled:
            _vsettings.vision_default_prompt_style = "accessibility"
        _save_settings(_vsettings)

        self._announce(_("AI Hub settings saved."))
        self.dialog.EndModal(self._wx.ID_OK)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        self._show_modal(self.dialog)
        self.dialog.Destroy()
