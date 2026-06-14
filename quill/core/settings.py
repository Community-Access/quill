from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.settings_normalizers import (
    STATUS_BAR_ITEMS,
    _clamp_int,
    _default_status_bar_hidden,
    _default_status_bar_order,
    _normalize_status_bar_hidden,
    _normalize_status_bar_order,
)
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "STATUS_BAR_ITEMS",
    "Settings",
    "load_settings",
    "save_settings",
    "settings_path",
]


@dataclass(slots=True)
class Settings:
    theme: str = "system"
    keyboard_pack: str = "Quill Default"
    soft_wrap: bool = True
    wrap_find: bool = True
    browse_mode_wrap: bool = True
    browse_mode_feedback: str = "speech"
    browse_mode_preload_cache: bool = True
    quill_key_binding: str = "Ctrl+Shift+Grave"
    quill_key_timeout_seconds: float = 1.5
    csv_open_mode: str = "prompt"
    word_open_mode: str = "prompt"
    editor_surface: str = "plain"
    save_as_surface_sync: str = "prompt"
    plain_text_link_style: str = "text_url"
    indent_with_tabs: bool = False
    indent_size: int = 4
    auto_check_updates: bool = False
    beta_updates: bool = False
    skipped_update_version: str = ""
    last_update_check: str = ""
    recent_files_limit: int = 10
    tray_enabled: bool = False
    persistent_undo: bool = False
    spellcheck_as_you_type: bool = False
    intellisense_as_you_type: bool = False
    snippet_trigger_expansion: bool = True
    preview_browser: str = "system"
    auto_side_preview: bool = True
    show_tab_control: bool = False
    title_bar_path_mode: str = "name"
    dirty_title_style: str = "text"
    start_with_no_document_open: bool = False
    read_aloud_engine: str = "pyttsx3"
    read_aloud_voice: str = ""
    read_aloud_rate: int = 200
    read_aloud_volume: int = 100
    read_aloud_pitch: int = 50
    read_aloud_dectalk_executable: str = ""
    read_aloud_dectalk_voice: str = "paul"
    read_aloud_dectalk_rate: int = 180
    read_aloud_dectalk_dictionary: str = ""
    read_aloud_piper_executable: str = ""
    read_aloud_piper_model: str = ""
    announcement_backend: str = "auto"
    read_aloud_piper_model_dir: str = ""
    read_aloud_kokoro_voice: str = "af_heart"
    read_aloud_kokoro_speed: float = 1.0
    read_aloud_espeak_executable: str = ""
    read_aloud_espeak_voice: str = "en"
    read_aloud_espeak_rate: int = 175
    read_aloud_openvoice_executable: str = ""
    read_aloud_openvoice_voice: str = "en-base"
    read_aloud_openvoice_rate: int = 180
    read_aloud_openvoice_consent: bool = False
    announcement_trace_enabled: bool = False
    assistant_enabled: bool = False
    assistant_prompt_style: str = "balanced"
    markdown_clipboard_format: str = "html"
    auto_clean_html_paste: bool = False
    abbreviation_expansion: bool = True
    abbreviation_expansion_sound: bool = False
    abbreviation_expansion_sound_file: str = ""
    multi_press_window_ms: int = 400
    dictation_engine: str = "vosk"
    dictation_language: str = "en-US"
    dictation_model: str = "base"
    dictation_device_index: int = -1
    bw_speech_selection_mode: str = "recommended"
    bw_speech_model_id: str = "whisper-base"
    bw_enable_parakeet_models: bool = False
    bw_provider_id: str = "local_whisper"
    bw_provider_mode: str = "local_first"
    bw_show_cloud_providers: bool = True
    bw_auto_open_status_page_on_download_start: bool = False
    bw_safe_mode_lock: bool = False
    status_page_refresh_announcement_cadence: str = "quiet"
    voice_commands_enabled: bool = False
    watch_folder_enabled: bool = False
    watch_folder_path: str = ""
    startup_folder: str = ""
    watch_folder_include_subfolders: bool = False
    watch_folder_process_existing: bool = False
    watch_folder_auto_start: bool = False
    watch_folder_poll_interval_seconds: int = 5
    # SET-2: tunable timing and pacing
    autosave_interval_seconds: int = 30
    quick_nav_debounce_ms: int = 250
    quick_nav_min_chars: int = 1
    announcement_throttle_ms: int = 0
    read_aloud_sentence_pause_ms: int = 0
    # OCR-2: image-to-text engine selection
    ocr_engine: str = "auto"
    # SHELL-1: file-manager "Send to Quill" context-menu verbs
    shell_integration_enabled: bool = False
    shell_verb_ocr: bool = True
    shell_verb_ocr_structured: bool = False
    shell_verb_open: bool = True
    shell_verb_read: bool = False
    shell_file_types: str = "images_pdf"
    ocr_structured: bool = False
    ocr_capture_geometry: bool = False
    # FEAT-19: external file-change watch and safe reload
    external_change_watch_enabled: bool = True
    external_change_auto_reload_when_clean: bool = True
    external_change_prompt_on_conflict: bool = True
    external_change_debounce_ms: int = 750
    # SET-3: tunable verbosity and announcements
    announcement_verbosity: str = "normal"
    announce_wrap: bool = True
    announce_counts: bool = True
    announce_mode_changes: bool = True
    announce_spelling: bool = True
    announce_punctuation_level: str = "some"
    # SET-4: tunable behavior toggles
    browse_mode_sticky: bool = False
    quill_key_sound_enter: str = ""
    quill_key_sound_exit: str = ""
    quill_key_sound_move: str = ""
    quill_key_sound_error: str = ""
    confirm_destructive_actions: bool = True
    default_export_preset: str = "html"
    default_new_document_format: str = "markdown"
    autoformat_smart_quotes: bool = False
    autoformat_dashes: bool = False
    quick_nav_include_headings: bool = True
    quick_nav_include_links: bool = True
    quick_nav_include_lists: bool = True
    status_bar_order: list[str] = field(default_factory=_default_status_bar_order)
    status_bar_hidden: list[str] = field(default_factory=_default_status_bar_hidden)
    # GLOW: the shared accessibility engine is on by default; its optional
    # networked features stay off until the user gives explicit consent (GLOW-7).
    glow_enabled: bool = True
    glow_ai_alt_text_consent: bool = False
    glow_pii_redaction_consent: bool = False
    glow_language_processing_consent: bool = False
    # SEC-9: SSH host-key trust. When false (the safer default), unknown
    # host keys cause the connection to be rejected. When true, the first
    # time we see a key we silently cache it (paramiko.AutoAddPolicy).
    ssh_trust_first_use: bool = False
    # AI chat (Phase 2): Ask AI dialog provider/model defaults.
    ai_chat_default_provider: str = "openrouter"
    ai_chat_default_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    # AI prompts (Phase 3): separate default model for prompt-library runs.
    ai_prompt_default_model: str = ""
    # Bug reporter identity: pre-fill the Report a Bug dialog for speed.
    bug_reporter_name: str = ""
    bug_reporter_email: str = ""
    # I18N: BCP 47 language tag for the UI; empty string means "use OS default".
    language: str = ""
    # WIZARD: True once the first-run setup wizard has completed.
    setup_wizard_completed: bool = False
    # QDC: Developer Console settings.
    console_enabled: bool = True
    console_python_timeout: int = 30
    console_typescript_timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        theme = str(data.get("theme", "system"))
        keyboard_pack = str(data.get("keyboard_pack", "Quill Default"))
        soft_wrap = bool(data.get("soft_wrap", True))
        wrap_find = bool(data.get("wrap_find", True))
        browse_mode_wrap = bool(data.get("browse_mode_wrap", True))
        browse_mode_feedback = str(data.get("browse_mode_feedback", "speech")).strip().lower()
        if browse_mode_feedback not in {"sound", "speech", "both", "none"}:
            browse_mode_feedback = "speech"
        browse_mode_preload_cache = bool(
            data.get(
                "browse_mode_preload_cache",
                data.get("browse_mode_prewarm_for_large_docs", True),
            )
        )
        quill_key_binding = str(data.get("quill_key_binding", "Ctrl+Shift+Grave")).strip()
        if not quill_key_binding:
            quill_key_binding = "Ctrl+Shift+Grave"
        try:
            quill_key_timeout_seconds = float(data.get("quill_key_timeout_seconds", 1.5))
        except (TypeError, ValueError):
            quill_key_timeout_seconds = 1.5
        if quill_key_timeout_seconds < 0:
            quill_key_timeout_seconds = 0.0
        if quill_key_timeout_seconds > 60:
            quill_key_timeout_seconds = 60.0
        csv_open_mode = str(data.get("csv_open_mode", "prompt")).strip().lower()
        if csv_open_mode not in {"prompt", "text", "grid"}:
            csv_open_mode = "prompt"
        word_open_mode = str(data.get("word_open_mode", "prompt")).strip().lower()
        if word_open_mode not in {"prompt", "text", "structured"}:
            word_open_mode = "prompt"
        # core.rich_text_lens is locked_off; always "plain" regardless of stored value.
        editor_surface = "plain"
        save_as_surface_sync = str(data.get("save_as_surface_sync", "prompt")).strip().lower()
        if save_as_surface_sync not in {"prompt", "always", "never"}:
            save_as_surface_sync = "prompt"
        plain_text_link_style = str(data.get("plain_text_link_style", "text_url")).strip().lower()
        if plain_text_link_style not in {"text", "text_url", "url", "markdown"}:
            plain_text_link_style = "text_url"
        indent_with_tabs = bool(data.get("indent_with_tabs", False))
        try:
            indent_size = int(data.get("indent_size", 4))
        except (TypeError, ValueError):
            indent_size = 4
        auto_check_updates = bool(data.get("auto_check_updates", False))
        beta_updates = bool(data.get("beta_updates", False))
        skipped_update_version = str(data.get("skipped_update_version", "")).strip()
        last_update_check = str(data.get("last_update_check", "")).strip()
        try:
            recent_files_limit = int(data.get("recent_files_limit", 10))
        except (TypeError, ValueError):
            recent_files_limit = 10
        tray_enabled = bool(data.get("tray_enabled", False))
        persistent_undo = bool(data.get("persistent_undo", False))
        spellcheck_as_you_type = bool(data.get("spellcheck_as_you_type", False))
        intellisense_as_you_type = bool(data.get("intellisense_as_you_type", False))
        snippet_trigger_expansion = bool(data.get("snippet_trigger_expansion", True))
        preview_browser = str(data.get("preview_browser", "system")).strip() or "system"
        auto_side_preview = bool(data.get("auto_side_preview", True))
        show_tab_control = bool(data.get("show_tab_control", False))
        title_bar_path_mode = str(data.get("title_bar_path_mode", "name"))
        if title_bar_path_mode not in {"name", "full_path"}:
            title_bar_path_mode = "name"
        dirty_title_style = str(data.get("dirty_title_style", "text"))
        if dirty_title_style not in {"text", "asterisk", "asterisk_text"}:
            dirty_title_style = "text"
        start_with_no_document_open = bool(data.get("start_with_no_document_open", False))
        read_aloud_engine = str(data.get("read_aloud_engine", "pyttsx3")).strip().lower()
        _valid_engines = {
            "pyttsx3",
            "dectalk",
            "piper",
            "kokoro",
            "espeak",
            "openvoice",
        }
        if read_aloud_engine not in _valid_engines:
            read_aloud_engine = "pyttsx3"
        read_aloud_voice = str(data.get("read_aloud_voice", ""))
        read_aloud_rate = int(data.get("read_aloud_rate", 200))
        if read_aloud_rate < 80:
            read_aloud_rate = 80
        if read_aloud_rate > 450:
            read_aloud_rate = 450
        read_aloud_volume = int(data.get("read_aloud_volume", 100))
        if read_aloud_volume < 0:
            read_aloud_volume = 0
        if read_aloud_volume > 100:
            read_aloud_volume = 100
        read_aloud_pitch = int(data.get("read_aloud_pitch", 50))
        if read_aloud_pitch < 0:
            read_aloud_pitch = 0
        if read_aloud_pitch > 100:
            read_aloud_pitch = 100
        read_aloud_dectalk_executable = str(data.get("read_aloud_dectalk_executable", "")).strip()
        read_aloud_dectalk_voice = str(data.get("read_aloud_dectalk_voice", "paul")).strip().lower()
        if not read_aloud_dectalk_voice:
            read_aloud_dectalk_voice = "paul"
        read_aloud_dectalk_rate = int(data.get("read_aloud_dectalk_rate", 180))
        if read_aloud_dectalk_rate < 75:
            read_aloud_dectalk_rate = 75
        if read_aloud_dectalk_rate > 650:
            read_aloud_dectalk_rate = 650
        read_aloud_dectalk_dictionary = str(data.get("read_aloud_dectalk_dictionary", "")).strip()
        read_aloud_piper_executable = str(data.get("read_aloud_piper_executable", "")).strip()
        read_aloud_piper_model = str(data.get("read_aloud_piper_model", "")).strip()
        announcement_backend = str(data.get("announcement_backend", "auto")).strip().lower()
        read_aloud_piper_model_dir = str(data.get("read_aloud_piper_model_dir", "")).strip()
        read_aloud_kokoro_voice = (
            str(data.get("read_aloud_kokoro_voice", "af_heart")).strip() or "af_heart"
        )
        _kokoro_speed_raw = data.get("read_aloud_kokoro_speed", 1.0)
        try:
            read_aloud_kokoro_speed = float(_kokoro_speed_raw)
        except (TypeError, ValueError):
            read_aloud_kokoro_speed = 1.0
        read_aloud_kokoro_speed = max(0.5, min(2.0, read_aloud_kokoro_speed))
        read_aloud_espeak_executable = str(data.get("read_aloud_espeak_executable", "")).strip()
        read_aloud_espeak_voice = str(data.get("read_aloud_espeak_voice", "en")).strip() or "en"
        read_aloud_espeak_rate = int(data.get("read_aloud_espeak_rate", 175))
        if read_aloud_espeak_rate < 80:
            read_aloud_espeak_rate = 80
        if read_aloud_espeak_rate > 450:
            read_aloud_espeak_rate = 450
        read_aloud_openvoice_executable = str(
            data.get("read_aloud_openvoice_executable", "")
        ).strip()
        read_aloud_openvoice_voice = (
            str(data.get("read_aloud_openvoice_voice", "en-base")).strip().lower() or "en-base"
        )
        read_aloud_openvoice_rate = int(data.get("read_aloud_openvoice_rate", 180))
        if read_aloud_openvoice_rate < 80:
            read_aloud_openvoice_rate = 80
        if read_aloud_openvoice_rate > 450:
            read_aloud_openvoice_rate = 450
        read_aloud_openvoice_consent = bool(data.get("read_aloud_openvoice_consent", False))
        if announcement_backend not in {"auto", "prism", "status_only"}:
            announcement_backend = "auto"
        announcement_trace_enabled = bool(data.get("announcement_trace_enabled", False))
        assistant_enabled = bool(data.get("assistant_enabled", False))
        assistant_prompt_style = str(data.get("assistant_prompt_style", "balanced")).strip().lower()
        if assistant_prompt_style not in {"balanced", "concise", "gentle", "technical"}:
            assistant_prompt_style = "balanced"
        markdown_clipboard_format = (
            str(data.get("markdown_clipboard_format", "html")).strip().lower() or "html"
        )
        if markdown_clipboard_format not in {"html", "rtf"}:
            markdown_clipboard_format = "html"
        dictation_engine = str(data.get("dictation_engine", "vosk")).strip().lower()
        if dictation_engine not in {"vosk", "whisper"}:
            dictation_engine = "vosk"
        dictation_language = str(data.get("dictation_language", "en-US")).strip() or "en-US"
        dictation_model = str(data.get("dictation_model", "base")).strip() or "base"
        dictation_device_index = int(data.get("dictation_device_index", -1))
        if dictation_device_index < -1:
            dictation_device_index = -1
        bw_speech_selection_mode = (
            str(data.get("bw_speech_selection_mode", "recommended")).strip().lower()
            or "recommended"
        )
        if bw_speech_selection_mode not in {"recommended", "manual"}:
            bw_speech_selection_mode = "recommended"
        bw_speech_model_id = (
            str(data.get("bw_speech_model_id", "whisper-base")).strip() or "whisper-base"
        )
        bw_enable_parakeet_models = bool(data.get("bw_enable_parakeet_models", False))
        bw_provider_id = str(data.get("bw_provider_id", "local_whisper")).strip() or "local_whisper"
        bw_provider_mode = str(data.get("bw_provider_mode", "local_first")).strip().lower()
        if bw_provider_mode not in {"local_first", "cloud_first"}:
            bw_provider_mode = "local_first"
        bw_show_cloud_providers = bool(data.get("bw_show_cloud_providers", True))
        bw_auto_open_status_page_on_download_start = bool(
            data.get("bw_auto_open_status_page_on_download_start", False)
        )
        bw_safe_mode_lock = bool(data.get("bw_safe_mode_lock", False))
        try:
            status_page_refresh_announcement_cadence = (
                str(data.get("status_page_refresh_announcement_cadence", "quiet")).strip().lower()
                or "quiet"
            )
        except (TypeError, ValueError):
            status_page_refresh_announcement_cadence = "quiet"
        if status_page_refresh_announcement_cadence not in {"quiet", "normal", "verbose"}:
            status_page_refresh_announcement_cadence = "quiet"
        watch_folder_enabled = bool(data.get("watch_folder_enabled", False))
        watch_folder_path = str(data.get("watch_folder_path", "")).strip()
        startup_folder = str(data.get("startup_folder", "")).strip()
        watch_folder_include_subfolders = bool(data.get("watch_folder_include_subfolders", False))
        watch_folder_process_existing = bool(data.get("watch_folder_process_existing", False))
        watch_folder_auto_start = bool(data.get("watch_folder_auto_start", False))
        try:
            watch_folder_poll_interval_seconds = int(
                data.get("watch_folder_poll_interval_seconds", 5)
            )
        except (TypeError, ValueError):
            watch_folder_poll_interval_seconds = 5
        if watch_folder_poll_interval_seconds < 2:
            watch_folder_poll_interval_seconds = 2
        if watch_folder_poll_interval_seconds > 300:
            watch_folder_poll_interval_seconds = 300
        voice_commands_enabled = bool(data.get("voice_commands_enabled", False))
        # SET-2: timing and pacing
        autosave_interval_seconds = _clamp_int(
            data.get("autosave_interval_seconds", 30), 30, 5, 600
        )
        quick_nav_debounce_ms = _clamp_int(data.get("quick_nav_debounce_ms", 250), 250, 0, 2000)
        quick_nav_min_chars = _clamp_int(data.get("quick_nav_min_chars", 1), 1, 1, 5)
        announcement_throttle_ms = _clamp_int(data.get("announcement_throttle_ms", 0), 0, 0, 2000)
        read_aloud_sentence_pause_ms = _clamp_int(
            data.get("read_aloud_sentence_pause_ms", 0), 0, 0, 2000
        )
        # OCR-2: image-to-text engine selection
        ocr_engine = str(data.get("ocr_engine", "auto")).strip().lower()
        if ocr_engine not in {"auto", "windows"}:
            ocr_engine = "auto"
        # SHELL-1: file-manager "Send to Quill" context-menu verbs
        shell_integration_enabled = bool(data.get("shell_integration_enabled", False))
        shell_verb_ocr = bool(data.get("shell_verb_ocr", True))
        shell_verb_ocr_structured = bool(data.get("shell_verb_ocr_structured", False))
        shell_verb_open = bool(data.get("shell_verb_open", True))
        shell_verb_read = bool(data.get("shell_verb_read", False))
        shell_file_types = str(data.get("shell_file_types", "images_pdf")).strip().lower()
        if shell_file_types not in {"images", "images_pdf", "images_pdf_docs"}:
            shell_file_types = "images_pdf"
        ocr_structured = bool(data.get("ocr_structured", False))
        ocr_capture_geometry = bool(data.get("ocr_capture_geometry", False))
        # FEAT-19: external file-change watch and safe reload
        external_change_watch_enabled = bool(data.get("external_change_watch_enabled", True))
        external_change_auto_reload_when_clean = bool(
            data.get("external_change_auto_reload_when_clean", True)
        )
        external_change_prompt_on_conflict = bool(
            data.get("external_change_prompt_on_conflict", True)
        )
        external_change_debounce_ms = _clamp_int(
            data.get("external_change_debounce_ms", 750), 750, 0, 10000
        )
        # SET-3: verbosity and announcements
        announcement_verbosity = str(data.get("announcement_verbosity", "normal")).strip().lower()
        if announcement_verbosity not in {"minimal", "normal", "verbose"}:
            announcement_verbosity = "normal"
        announce_wrap = bool(data.get("announce_wrap", True))
        announce_counts = bool(data.get("announce_counts", True))
        announce_mode_changes = bool(data.get("announce_mode_changes", True))
        announce_spelling = bool(data.get("announce_spelling", True))
        announce_punctuation_level = (
            str(data.get("announce_punctuation_level", "some")).strip().lower()
        )
        if announce_punctuation_level not in {"none", "some", "most", "all"}:
            announce_punctuation_level = "some"
        # SET-4: behavior toggles
        browse_mode_sticky = bool(data.get("browse_mode_sticky", False))
        quill_key_sound_enter = str(data.get("quill_key_sound_enter", "")).strip()
        quill_key_sound_exit = str(data.get("quill_key_sound_exit", "")).strip()
        quill_key_sound_move = str(data.get("quill_key_sound_move", "")).strip()
        quill_key_sound_error = str(data.get("quill_key_sound_error", "")).strip()
        confirm_destructive_actions = bool(data.get("confirm_destructive_actions", True))
        default_export_preset = str(data.get("default_export_preset", "html")).strip().lower()
        if default_export_preset not in {"html", "markdown", "pdf", "docx", "epub", "text"}:
            default_export_preset = "html"
        default_new_document_format = (
            str(data.get("default_new_document_format", "markdown")).strip().lower()
        )
        if default_new_document_format not in {"markdown", "text", "html"}:
            default_new_document_format = "markdown"
        autoformat_smart_quotes = bool(data.get("autoformat_smart_quotes", False))
        autoformat_dashes = bool(data.get("autoformat_dashes", False))
        quick_nav_include_headings = bool(data.get("quick_nav_include_headings", True))
        quick_nav_include_links = bool(data.get("quick_nav_include_links", True))
        quick_nav_include_lists = bool(data.get("quick_nav_include_lists", True))
        status_bar_order = _normalize_status_bar_order(data.get("status_bar_order"))
        status_bar_hidden = _normalize_status_bar_hidden(
            data.get("status_bar_hidden"), status_bar_order
        )
        # GLOW engine defaults on; networked features default off (GLOW-7).
        glow_enabled = bool(data.get("glow_enabled", True))
        glow_ai_alt_text_consent = bool(data.get("glow_ai_alt_text_consent", False))
        glow_pii_redaction_consent = bool(data.get("glow_pii_redaction_consent", False))
        glow_language_processing_consent = bool(data.get("glow_language_processing_consent", False))
        ssh_trust_first_use = bool(data.get("ssh_trust_first_use", False))
        ai_chat_default_provider = (
            str(data.get("ai_chat_default_provider", "openrouter")).strip() or "openrouter"
        )
        ai_chat_default_model = str(data.get("ai_chat_default_model", ""))
        ollama_base_url = (
            str(data.get("ollama_base_url", "http://localhost:11434")).strip()
            or "http://localhost:11434"
        )
        ai_prompt_default_model = str(data.get("ai_prompt_default_model", ""))
        bug_reporter_name = str(data.get("bug_reporter_name", "")).strip()
        bug_reporter_email = str(data.get("bug_reporter_email", "")).strip()
        language = str(data.get("language", "")).strip()
        setup_wizard_completed = bool(data.get("setup_wizard_completed", False))
        console_enabled = bool(data.get("console_enabled", True))
        try:
            console_python_timeout = int(data.get("console_python_timeout", 30))
        except (TypeError, ValueError):
            console_python_timeout = 30
        try:
            console_typescript_timeout = int(data.get("console_typescript_timeout", 30))
        except (TypeError, ValueError):
            console_typescript_timeout = 30
        abbreviation_expansion = bool(data.get("abbreviation_expansion", True))
        abbreviation_expansion_sound = bool(data.get("abbreviation_expansion_sound", False))
        abbreviation_expansion_sound_file = str(data.get("abbreviation_expansion_sound_file", ""))
        raw_mp = int(data.get("multi_press_window_ms", 400))
        multi_press_window_ms = max(100, min(1000, raw_mp))
        if recent_files_limit < 1:
            recent_files_limit = 1
        if recent_files_limit > 50:
            recent_files_limit = 50
        if indent_size < 1:
            indent_size = 1
        if indent_size > 8:
            indent_size = 8
        return cls(
            theme=theme,
            keyboard_pack=keyboard_pack,
            soft_wrap=soft_wrap,
            wrap_find=wrap_find,
            browse_mode_wrap=browse_mode_wrap,
            browse_mode_feedback=browse_mode_feedback,
            browse_mode_preload_cache=browse_mode_preload_cache,
            quill_key_binding=quill_key_binding,
            quill_key_timeout_seconds=quill_key_timeout_seconds,
            csv_open_mode=csv_open_mode,
            word_open_mode=word_open_mode,
            editor_surface=editor_surface,
            save_as_surface_sync=save_as_surface_sync,
            plain_text_link_style=plain_text_link_style,
            indent_with_tabs=indent_with_tabs,
            indent_size=indent_size,
            auto_check_updates=auto_check_updates,
            beta_updates=beta_updates,
            skipped_update_version=skipped_update_version,
            last_update_check=last_update_check,
            recent_files_limit=recent_files_limit,
            tray_enabled=tray_enabled,
            persistent_undo=persistent_undo,
            spellcheck_as_you_type=spellcheck_as_you_type,
            intellisense_as_you_type=intellisense_as_you_type,
            snippet_trigger_expansion=snippet_trigger_expansion,
            preview_browser=preview_browser,
            auto_side_preview=auto_side_preview,
            show_tab_control=show_tab_control,
            title_bar_path_mode=title_bar_path_mode,
            dirty_title_style=dirty_title_style,
            start_with_no_document_open=start_with_no_document_open,
            read_aloud_engine=read_aloud_engine,
            read_aloud_voice=read_aloud_voice,
            read_aloud_rate=read_aloud_rate,
            read_aloud_volume=read_aloud_volume,
            read_aloud_pitch=read_aloud_pitch,
            read_aloud_dectalk_executable=read_aloud_dectalk_executable,
            read_aloud_dectalk_voice=read_aloud_dectalk_voice,
            read_aloud_dectalk_rate=read_aloud_dectalk_rate,
            read_aloud_dectalk_dictionary=read_aloud_dectalk_dictionary,
            read_aloud_piper_executable=read_aloud_piper_executable,
            read_aloud_piper_model=read_aloud_piper_model,
            announcement_backend=announcement_backend,
            read_aloud_piper_model_dir=read_aloud_piper_model_dir,
            read_aloud_kokoro_voice=read_aloud_kokoro_voice,
            read_aloud_kokoro_speed=read_aloud_kokoro_speed,
            read_aloud_espeak_executable=read_aloud_espeak_executable,
            read_aloud_espeak_voice=read_aloud_espeak_voice,
            read_aloud_espeak_rate=read_aloud_espeak_rate,
            read_aloud_openvoice_executable=read_aloud_openvoice_executable,
            read_aloud_openvoice_voice=read_aloud_openvoice_voice,
            read_aloud_openvoice_rate=read_aloud_openvoice_rate,
            read_aloud_openvoice_consent=read_aloud_openvoice_consent,
            announcement_trace_enabled=announcement_trace_enabled,
            assistant_enabled=assistant_enabled,
            assistant_prompt_style=assistant_prompt_style,
            markdown_clipboard_format=markdown_clipboard_format,
            dictation_engine=dictation_engine,
            dictation_language=dictation_language,
            dictation_model=dictation_model,
            dictation_device_index=dictation_device_index,
            bw_speech_selection_mode=bw_speech_selection_mode,
            bw_speech_model_id=bw_speech_model_id,
            bw_enable_parakeet_models=bw_enable_parakeet_models,
            bw_provider_id=bw_provider_id,
            bw_provider_mode=bw_provider_mode,
            bw_show_cloud_providers=bw_show_cloud_providers,
            bw_auto_open_status_page_on_download_start=bw_auto_open_status_page_on_download_start,
            bw_safe_mode_lock=bw_safe_mode_lock,
            status_page_refresh_announcement_cadence=status_page_refresh_announcement_cadence,
            voice_commands_enabled=voice_commands_enabled,
            watch_folder_enabled=watch_folder_enabled,
            watch_folder_path=watch_folder_path,
            startup_folder=startup_folder,
            watch_folder_include_subfolders=watch_folder_include_subfolders,
            watch_folder_process_existing=watch_folder_process_existing,
            watch_folder_auto_start=watch_folder_auto_start,
            watch_folder_poll_interval_seconds=watch_folder_poll_interval_seconds,
            autosave_interval_seconds=autosave_interval_seconds,
            quick_nav_debounce_ms=quick_nav_debounce_ms,
            quick_nav_min_chars=quick_nav_min_chars,
            announcement_throttle_ms=announcement_throttle_ms,
            read_aloud_sentence_pause_ms=read_aloud_sentence_pause_ms,
            ocr_engine=ocr_engine,
            shell_integration_enabled=shell_integration_enabled,
            shell_verb_ocr=shell_verb_ocr,
            shell_verb_ocr_structured=shell_verb_ocr_structured,
            shell_verb_open=shell_verb_open,
            shell_verb_read=shell_verb_read,
            shell_file_types=shell_file_types,
            ocr_structured=ocr_structured,
            ocr_capture_geometry=ocr_capture_geometry,
            external_change_watch_enabled=external_change_watch_enabled,
            external_change_auto_reload_when_clean=external_change_auto_reload_when_clean,
            external_change_prompt_on_conflict=external_change_prompt_on_conflict,
            external_change_debounce_ms=external_change_debounce_ms,
            announcement_verbosity=announcement_verbosity,
            announce_wrap=announce_wrap,
            announce_counts=announce_counts,
            announce_mode_changes=announce_mode_changes,
            announce_spelling=announce_spelling,
            announce_punctuation_level=announce_punctuation_level,
            browse_mode_sticky=browse_mode_sticky,
            quill_key_sound_enter=quill_key_sound_enter,
            quill_key_sound_exit=quill_key_sound_exit,
            quill_key_sound_move=quill_key_sound_move,
            quill_key_sound_error=quill_key_sound_error,
            confirm_destructive_actions=confirm_destructive_actions,
            default_export_preset=default_export_preset,
            default_new_document_format=default_new_document_format,
            autoformat_smart_quotes=autoformat_smart_quotes,
            autoformat_dashes=autoformat_dashes,
            quick_nav_include_headings=quick_nav_include_headings,
            quick_nav_include_links=quick_nav_include_links,
            quick_nav_include_lists=quick_nav_include_lists,
            status_bar_order=status_bar_order,
            status_bar_hidden=status_bar_hidden,
            glow_enabled=glow_enabled,
            glow_ai_alt_text_consent=glow_ai_alt_text_consent,
            glow_pii_redaction_consent=glow_pii_redaction_consent,
            glow_language_processing_consent=glow_language_processing_consent,
            ssh_trust_first_use=ssh_trust_first_use,
            ai_chat_default_provider=ai_chat_default_provider,
            ai_chat_default_model=ai_chat_default_model,
            ollama_base_url=ollama_base_url,
            ai_prompt_default_model=ai_prompt_default_model,
            bug_reporter_name=bug_reporter_name,
            bug_reporter_email=bug_reporter_email,
            abbreviation_expansion=abbreviation_expansion,
            abbreviation_expansion_sound=abbreviation_expansion_sound,
            abbreviation_expansion_sound_file=abbreviation_expansion_sound_file,
            multi_press_window_ms=multi_press_window_ms,
            language=language,
            setup_wizard_completed=setup_wizard_completed,
            console_enabled=console_enabled,
            console_python_timeout=console_python_timeout,
            console_typescript_timeout=console_typescript_timeout,
        )


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def load_settings() -> Settings:
    raw = read_json(settings_path(), default={})
    if not isinstance(raw, dict):
        return Settings()
    # SET-5: read either the nested, versioned document or a legacy flat file.
    from quill.core.settings_migration import from_versioned

    return from_versioned(raw)


def save_settings(settings: Settings) -> None:
    # SET-5: persist the nested, versioned document shape.
    from quill.core.settings_migration import to_versioned

    write_json_atomic(settings_path(), to_versioned(settings))
