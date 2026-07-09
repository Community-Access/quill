from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.ai.vision_prompts import BUILTIN_STYLE_IDS
from quill.core.paths import app_data_dir
from quill.core.settings_normalizers import (
    STATUS_BAR_ITEMS,
    _clamp_int,
    _default_status_bar_hidden,
    _default_status_bar_order,
    _normalize_status_bar_hidden,
    _normalize_status_bar_order,
)
from quill.core.storage import write_json_atomic
from quill.core.versioned_store import load_with_migration

__all__ = [
    "STATUS_BAR_ITEMS",
    "Settings",
    "load_settings",
    "save_settings",
    "settings_path",
]


def _coerce_non_negative_float(value: object, default: float) -> float:
    """Float clamped to >= 0; ``default`` for a malformed value (never raises)."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return result if result >= 0 else 0.0


@dataclass(slots=True)
class Settings:
    theme: str = "system"
    keyboard_pack: str = "Quill Default"
    soft_wrap: bool = True
    wrap_find: bool = True
    browse_mode_wrap: bool = True
    browse_mode_feedback: str = "speech"
    browse_mode_move_detail: str = "position"
    browse_mode_preload_cache: bool = True
    quill_key_binding: str = "Ctrl+Shift+Grave"
    quill_key_timeout_seconds: float = 2.5
    browse_mode_followon_timeout: str = "unlimited"
    browse_mode_followon_custom_ms: int = 4000
    csv_open_mode: str = "prompt"
    word_open_mode: str = "prompt"
    editor_surface: str = "plain"
    save_as_surface_sync: str = "prompt"
    # Conversion engine preferences for Word documents. "auto" keeps QUILL's
    # default chains: MarkItDown-first when opening a .docx, the native
    # python-docx writer first when saving one. The explicit choices trade
    # differently: see the Settings descriptions for what each keeps and drops.
    docx_read_engine: str = "auto"
    docx_write_engine: str = "auto"
    plain_text_link_style: str = "text_url"
    indent_with_tabs: bool = False
    indent_size: int = 4
    # On by default so signed safety advisories (the remote feature kill
    # switch) actually reach installs; the check fetches QUILL's own signed
    # feed and sends nothing about the user. An explicit stored False is
    # honored, and Safe Mode skips the check entirely.
    auto_check_updates: bool = True
    beta_updates: bool = False
    # Recommended (force-once) updates to important defaults, e.g. restoring
    # Find to Ctrl+F for users who had it on a QUILL-key chord. This is the
    # opt-out toggle (default on); ``applied_recommended_updates`` records which
    # updates have already fired so each applies at most once per user. See
    # quill.core.recommended_updates.
    apply_recommended_keymap_updates: bool = True
    applied_recommended_updates: list[str] = field(default_factory=list)
    # How QUILL surfaces a one-time settings/keymap migration after an upgrade:
    # "silent" (do nothing), "announce" (brief spoken + status message), or
    # "prompt" (a small dialog summarizing what changed, with an Undo).
    migration_notice: str = "announce"
    skipped_update_version: str = ""
    last_update_check: str = ""
    recent_files_limit: int = 10
    recent_files_auto_clear_missing: bool = False
    # When saving an untitled document, suggest a filename from its first line
    # (works across formats; strips leading markup). On by default: it only
    # pre-fills the name for an untitled document, never renames anything.
    first_line_as_title: bool = True
    # Restore points: snapshot the document text on every save so File >
    # Restore Previous Version can bring any earlier save back. On by default;
    # recording is content-addressed (an unchanged save stores nothing) and
    # best-effort (it can never be the reason a save fails).
    restore_points_enabled: bool = True
    # Per-document disk cap for restore-point history, in megabytes. Age
    # thinning (keep a week fully, then daily, then weekly) runs first; the
    # newest five versions are never pruned regardless of the cap.
    restore_points_max_mb: int = 200
    # Background model warm-up after startup so the first use is fast. Loads the
    # model into memory; turn off to save RAM if you don't use the feature.
    warm_dictation_model: bool = True
    warm_kokoro_model: bool = True
    tray_enabled: bool = False
    persistent_undo: bool = False
    spellcheck_as_you_type: bool = False
    # When True, saving a document first opens the F7 spelling review so the user
    # can correct misspellings before the file is written. Off by default.
    spell_check_before_save: bool = False
    # Hunspell language the spell checker validates against. en_US ships bundled;
    # other languages download on demand (quill.core.spellcheck.install_language).
    spellcheck_language: str = "en_US"
    # Reveal Codes pane (WordPerfect-style hidden-code inspector). Hidden by
    # default; Alt+F3 toggles it, F6 cycles focus into it.
    reveal_codes_visible: bool = False
    reveal_codes_view: str = "structured"  # "structured" | "flowed"
    reveal_codes_verbosity: str = "balanced"  # "quiet" | "balanced" | "detailed"
    intellisense_as_you_type: bool = False
    snippet_trigger_expansion: bool = True
    preview_browser: str = "system"
    auto_side_preview: bool = True
    show_tab_control: bool = False
    title_bar_path_mode: str = "name"
    dirty_title_style: str = "text"
    start_with_no_document_open: bool = False
    read_aloud_engine: str = "sapi5"
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
    # ElevenLabs premium cloud voice for Read Aloud (opt-in, per-session consent,
    # billed to the user's ElevenLabs quota). Blank ids use the module defaults.
    read_aloud_elevenlabs_voice: str = ""
    read_aloud_elevenlabs_model: str = ""
    # AI Voice (cloud TTS): which provider/model/voice the AI read-aloud and
    # export actions use. Provider is "openai" or "gemini".
    ai_tts_provider: str = "openai"
    ai_tts_model: str = ""
    ai_tts_voice: str = ""
    ai_tts_speed: float = 1.0
    announcement_trace_enabled: bool = False
    announcement_startup_tips_enabled: bool = False
    verbosity_speech_enabled: bool = True
    announce_screen_reader_detected: bool = False
    assistant_enabled: bool = False
    assistant_prompt_style: str = "balanced"
    markdown_clipboard_format: str = "html"
    markdown_profile_id: str = "standard"
    citation_style: str = "footnotes"
    auto_clean_html_paste: bool = False
    list_auto_fill_numbers: bool = False
    abbreviation_expansion: bool = False
    abbreviation_expansion_sound: bool = False
    abbreviation_expansion_sound_file: str = ""
    multi_press_window_ms: int = 400
    dictation_engine: str = "windows"
    dictation_language: str = "en-US"
    dictation_model: str = "base"
    dictation_device_index: int = -1
    # Hold-to-Dictate / Locked Dictation policy (PRD §10, §20). These feed the
    # core DictationConfig the controller consults; 0 disables the time limits.
    dictation_max_locked_seconds: float = 300.0  # locked session cap (5 min)
    dictation_stop_on_focus_loss: bool = True  # stop+keep speech when QUILL blurs
    dictation_intelligent_spacing: bool = True  # conservative insertion spacing
    dictation_onboarding_shown: bool = False  # one-time first-use dictation hint shown
    dictation_min_hold_seconds: float = 0.0  # ignore accidental F9 taps below this
    # Speak the formatting delta as the caret moves (hidden-codes interrogation);
    # off by default so navigation stays quiet (Describe Formatting is on-demand).
    announce_formatting_on_move: bool = False
    # Speak "Entered/Exited <name> dialog" as dialogs open/close. Off by default:
    # every supported screen reader already announces the dialog and its title,
    # so the cue is redundant; turn it back on to hear the explicit transition.
    announce_dialog_transitions: bool = False
    # Runtime-memory policy (AI footprint & optimization, QUILL-PRD.md §5.25f).
    # low_resource_mode caps concurrently-loaded engines to one and biases model
    # selection to the smallest that fits — trading concurrency for fit, never
    # disabling AI or speech. idle_unload_minutes unloads a model untouched for
    # that many minutes (0 = never unload); a later use simply reloads.
    low_resource_mode: bool = False
    idle_unload_minutes: int = 10
    # Speak the new indentation depth ("4 spaces" / "1 tab") when Tab / Shift+Tab
    # indents, instead of the terse "Indented lines". Aware of indent_with_tabs
    # and indent_size; on by default, off restores the terse message.
    announce_indent_depth: bool = True
    # Double-press an informational command (Describe Formatting, Document
    # Summary, Context Help, Announce Contrast) to open the Spoken Echo review
    # dialog instead of re-speaking. The dedicated Echo key works regardless; this
    # only governs the double-press shortcut. See quill/core/spoken_echo.py.
    spoken_echo_on_double_press: bool = True
    # Braille leading-cell experiment. The editor defaults to a Windows RichEdit
    # for accessible value reporting (#616). "editor_control_kind" lets a braille
    # user switch the native control: "rich2" (RichEdit 3.0, default), "rich"
    # (RichEdit 2.0), or "plain" (a Notepad-style EDIT control). Takes effect for
    # documents opened after the change.
    editor_control_kind: str = "rich2"
    # Experimental (testing) overrides — see the Experimental settings tab. Changing
    # either takes effect on the next QUILL restart.
    #   experimental_editor_surface: which control backs the editor, overriding
    #   editor_control_kind for testing. "default" follows editor_control_kind;
    #   otherwise "rich2" (RichEdit 3.0), "rich" (RichEdit 2.0), "plain" (Notepad-style
    #   EDIT control), or "rtf" (a wx.RichTextCtrl rich-text surface, experimental).
    experimental_editor_surface: str = "default"
    #   editor_hide_border: draw the editor control with no border for a cleaner,
    #   Notepad-like frame. Off keeps the platform default border.
    editor_hide_border: bool = False
    #   experimental_richedit_emulate_sysedit: the QuillRichEdit braille lever.
    #   When on (and the QuillRichEdit surface is selected), the native Rich Edit
    #   is put in SES_EMULATESYSEDIT mode to A/B whether emulating a classic EDIT
    #   control fixes the JAWS cell-2 offset (#616) and selection dots 7-8 (#813).
    #   Gated by experimental_acknowledged; needs JAWS + a braille display to judge.
    experimental_richedit_emulate_sysedit: bool = False
    #   experimental_acknowledged: the master Experimental switch — the user has
    #   opted in to experimental features as a group. Every experimental option
    #   below is ignored (and its controls disabled) until this is True.
    experimental_acknowledged: bool = False
    #   experimental_editor_surfaces_enabled: the secondary gate for the two
    #   editor-surface options above; carries the "features may degrade based on
    #   the control selected" acknowledgement. Both gates must be on before a
    #   non-default surface or border override is applied.
    experimental_editor_surfaces_enabled: bool = False
    #   glow_experimental_enabled: opt-in for the GLOW accessibility review and
    #   repair suite (Tools > GLOW). Gated by experimental_acknowledged; off by
    #   default while GLOW matures; takes effect on settings apply (menu rebuild).
    glow_experimental_enabled: bool = False
    #   publishing_experimental_enabled: opt-in for the read-only WordPress
    #   publishing connections tools (File > Publishing). Gated by
    #   experimental_acknowledged; the send/publish half stays locked regardless.
    publishing_experimental_enabled: bool = False
    #   table_studio_experimental_enabled: opt-in for the accessible Table
    #   Studio grid surface (Tools menu) — one surface for both a new table and
    #   an opened CSV. Gated by experimental_acknowledged; off by default while
    #   it matures; takes effect on settings apply (menu rebuild).
    table_studio_experimental_enabled: bool = False
    #   edge_read_aloud_enabled: opt-in experimental read-aloud that opens an
    #   accessible reader page in the user's real browser (see
    #   quill/core/browser_reader.py), where the full/online Web Speech voices
    #   are available. Gated by experimental_acknowledged; takes effect on
    #   settings apply — command always registered, menu appears on the settings
    #   menu rebuild, no restart. Voice is chosen/remembered in the page itself.
    edge_read_aloud_enabled: bool = False
    # What to do when a document that carries hidden formatting is saved as plain
    # text: "ask" (offer to keep the formatting), "illuminate" (always write a
    # <name>.illumination sidecar so the .txt round-trips formatting in QUILL), or
    # "plain" (drop the formatting, the classic lossy save). See quill/io/illumination.py.
    plain_text_with_formatting: str = "ask"
    # Pronunciation dictionaries (batch-document-to-speech-plan §4.7). The
    # dictionaries themselves live in JSON files (global under app_data_dir, project
    # under <project>/.quill/pronunciation); settings holds only the selection state.
    pronunciation_enabled: bool = True
    pronunciation_enabled_dictionary_ids: list[str] = field(default_factory=list)
    # TTS text cleanup/normalization (batch-document-to-speech §4.9): master toggle
    # plus the serialized TextNormalizationOptions (empty = recommended defaults).
    tts_normalization_enabled: bool = True
    tts_normalization: dict[str, Any] = field(default_factory=dict)
    # Offline speech engine: "" = bundled whisper.cpp; "fasterwhisper" or "vosk"
    # opt into those engines on machines that have them installed.
    speech_provider: str = ""
    # The model id to prefer for speech_provider (e.g. "small", "base.en"); ""
    # falls back to the first installed model of whichever engine is active.
    # Set by the guided offline-speech picker and "Set as Default".
    speech_default_model_id: str = ""
    bw_speech_selection_mode: str = "recommended"
    bw_speech_model_id: str = "whisper-base"
    bw_provider_id: str = "local_whisper"
    bw_provider_mode: str = "local_first"
    bw_show_cloud_providers: bool = True
    bw_auto_open_status_page_on_download_start: bool = False
    bw_safe_mode_lock: bool = False
    status_page_refresh_announcement_cadence: str = "quiet"
    voice_commands_enabled: bool = False
    # Voice conversation mode (Hey QUILL Phase 2). Hands-free multi-command
    # loop timing, in milliseconds; 0 disables the corresponding window. See
    # quill/core/speech/conversation.py (Timing) and the plan doc §3.2.
    voice_conversation_enabled: bool = False
    voice_conversation_silence_ms: int = 2000
    voice_conversation_review_ms: int = 900
    voice_conversation_followup_ms: int = 3000
    voice_conversation_thinking_ms: int = 2000
    # Refinements: an optional name for warm spoken prompts ("Listening, Jeff."),
    # spoken cue phrases (welcome/follow-up) via TTS, and speaking answers in the
    # voice loop. When a screen reader is active, spoken cues stay off by default
    # so QUILL never talks over the reader (SR-parity).
    voice_conversation_user_name: str = ""
    voice_conversation_spoken_cues: bool = False
    # Which on-device speech engine powers the voice-interaction features
    # (Voice Command, Conversation Mode, Hey QUILL). "" = follow the main speech
    # engine; "whispercpp" for accuracy, "vosk" for fast, low-overhead streaming
    # (recommended for the always-listening wake word). Falls back gracefully
    # when the chosen engine or a model for it is unavailable.
    voice_recognition_engine: str = ""
    # Wake word (Hey QUILL Phase 3). Always-listening for "Hey QUILL" on-device;
    # off by default and never persisted-on across a restart unless the user
    # opts in. See quill/core/speech/wakeword.py.
    voice_wakeword_enabled: bool = False
    voice_wakeword_persist: bool = False
    watch_folder_enabled: bool = False
    watch_folder_path: str = ""
    startup_folder: str = ""
    vault_root: str = ""  # active Accessible Vault folder ("" = no vault open)
    vault_templates_folder: str = ""  # vault-relative Templates folder ("" = "Templates")
    vault_daily_pattern: str = ""  # daily-note path pattern ("" = "Journal/{{date:YYYY-MM-DD}}.md")
    # Free-first document conversion (Import / Convert Document): the local
    # Tesseract OCR language (three-letter code, "" = "eng") and an optional
    # explicit tesseract executable override ("" = auto-discover).
    ocr_language: str = ""
    tesseract_path: str = ""
    # Tier 3 — Datalab Chandra cloud OCR (consent-gated, BYOK; PRD §5.93).
    # The API key is NEVER stored here — it lives in the credential vault
    # (see quill/core/datalab_ocr.py). These are the non-secret knobs from the
    # AI Hub Services tab. Every upload still requires a per-action consent.
    datalab_enabled: bool = False
    datalab_endpoint: str = "https://www.datalab.to"
    datalab_mode: str = "balanced"  # fast | balanced | accurate
    datalab_output: str = "markdown"  # markdown | html | json
    datalab_paginate: bool = True
    # #620: Simple File Open dialog. When true, File > Open... shows a
    # keyboard-friendly picker with a small filter, recent locations, and
    # a hidden-files toggle. The standard Windows file dialog is still
    # available via the "Use Windows Dialog" button inside the simple
    # dialog.
    use_simple_file_dialog: bool = False
    watch_folder_include_subfolders: bool = False
    watch_folder_process_existing: bool = False
    watch_folder_auto_start: bool = False
    watch_folder_poll_interval_seconds: int = 5
    # #262: Pandoc Import / Export batch conversion defaults. The wizard
    # reads these as starting values; the user can override per batch.
    import_export_recursive: bool = True
    import_export_overwrite: str = "ask"
    import_export_output_layout: str = "subfolder"
    import_export_last_folder: str = ""
    # File > Convert File dialog memory: the last output folder and the last
    # chosen output format (a Pandoc writer token, e.g. "gfm", "docx"). Session
    # memory, not a user-tunable policy, so not exposed in Preferences.
    convert_file_last_output_dir: str = ""
    convert_file_last_format: str = "gfm"
    # SET-2: tunable timing and pacing
    autosave_interval_seconds: int = 30
    quick_nav_debounce_ms: int = 250
    quick_nav_min_chars: int = 1
    announcement_throttle_ms: int = 0
    read_aloud_sentence_pause_ms: int = 0
    # When True, Read Aloud selects each sentence as it is spoken so sighted
    # users can follow along. Off by default: QUILL is screen-reader-first, and
    # moving the selection makes the screen reader announce "selected" over
    # QUILL's chosen voice. Sighted/low-vision users can opt in.
    read_aloud_follow_cursor: bool = False
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
    # Verbosity system (rebuild) — scalar prefs. Collection-typed state
    # (custom profiles, per-verb/chord overrides, QVP packs) persists separately
    # in verbosity_custom.json via quill.core.verbosity.storage.
    verbosity_mastery_enabled: bool = True
    verbosity_mastery_threshold: int = 25
    verbosity_validation_mode: str = "on_button"
    verbosity_history_enabled: bool = True
    verbosity_history_limit: int = 100
    verbosity_history_clear_on_exit: bool = False
    verbosity_task_profile_suggestions: bool = False
    verbosity_safe_mode_enabled: bool = False
    # Anti-spam for the spoken channel (#408/#409). Repetition collapse drops
    # identical consecutive speech within a short window; the budget caps spoken
    # announcements per rolling window (0 = no cap). Visual status is never affected.
    verbosity_collapse_repeats: bool = True
    verbosity_max_announcements_per_window: int = 0
    # #181: automatic Document Language detection on paste/typing. One of
    # "off" (default), "hint" (status bar only), "prompt" (announce a suggestion),
    # or "auto" (switch automatically). Only ever acts on unpinned untitled/.txt
    # documents; never overrides a real extension or a user choice.
    language_detection_mode: str = "off"
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
    ai_chat_default_provider: str = ""
    ai_chat_default_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    # AI prompts (Phase 3): separate default model for prompt-library runs.
    ai_prompt_default_model: str = ""
    # STABILITY: when True, an unhandled exception shows the crash-submit
    # dialog so the user can review a redacted preview and choose whether
    # to send the report to the developers. When False, the local-only
    # path runs (file is still saved to app_data_dir()/crash-reports).
    # Default is True during the beta phase so the team can hear about
    # crashes without forcing the user to opt in every time.
    auto_ask_crash_submit: bool = True
    # I18N: BCP 47 language tag for the UI; empty string means "use OS default".
    language: str = ""
    # WIZARD: True once the first-run setup wizard has completed.
    setup_wizard_completed: bool = False
    # WIZARD: intent profile picked by the user in the first-run setup wizard.
    # Empty string means "no choice yet" (defaults to the writer of the default
    # text_editor profile in main_frame.run_startup_wizard). Mirrors the values
    # that the wizard writes to settings so subsequent reads survive a save/reload.
    setup_wizard_intent: str = ""
    # WIZARD: optional extras toggled on by the wizard (used to apply Quillins
    # after the dialog closes). Defaults match the getattr fallbacks that the
    # caller historically used when these fields were not persisted.
    setup_wizard_wants_ai: bool = False
    setup_wizard_wants_braille: bool = False
    setup_wizard_wants_automation: bool = False
    # UPGRADE: True once we have shown the post-upgrade braille-pack install prompt.
    upgrade_prompt_braille_pack: bool = False
    # QDC: Developer Console settings.
    console_enabled: bool = True
    console_python_timeout: int = 30
    console_typescript_timeout: int = 30
    # QSP: sound notification system (earcons).
    sound_enabled: bool = True
    sound_pack_path: str = ""  # empty = bundled Ink pack
    sound_volume: int = 80  # 0-100; passed to sound_lib Output.set_volume()
    sound_events_disabled: str = ""  # comma-separated SoundEvent IDs to silence
    # Indent tone overlay: "" = off, else one of pentatonic/whole_tone/diatonic/chromatic.
    # When set, moving the caret across indent levels plays a pitched tone per level.
    indent_tone_scale: str = ""
    # Abbreviation backspace: "delete" removes expansion, "revert" puts the original back.
    abbreviation_backspace_behavior: str = "delete"
    # Braille Mode (BR-008): page geometry, page-break heuristic, sidecar,
    # and status-string / auto-announcement toggles. The defaults match the
    # historical `one_crazy_night.brf` corpus fixture so existing
    # documents round-trip unchanged.
    braille_cells_per_line: int = 40
    braille_lines_per_page: int = 25
    # Page indicator (#872): word-count basis for the estimated page count
    # shown for documents with no real page breaks (plain text, Markdown,
    # most DOCX). This is an approximation, not a printed page count.
    page_estimate_words_per_page: int = 300
    braille_use_form_feeds: bool = True
    braille_calculate_pages: bool = True
    braille_save_sidecar: bool = True
    braille_status_verbosity: str = "normal"
    braille_auto_announce_page_changes: bool = False
    braille_auto_announce_print_page_changes: bool = False
    braille_auto_announce_line_overflow: bool = False
    braille_include_proofing_status: bool = True
    braille_include_running_head: bool = False
    braille_include_continuation: bool = True
    # Spelling Review (F7) settings.
    spell_review_verbosity: str = "balanced"
    spell_review_spell_word: bool = True
    spell_review_spell_word_pause_ms: int = 800
    spell_review_wrap_to_beginning: bool = True
    spell_review_context_mode: str = "sentence"
    # Vision prompt library: image description style management.
    vision_default_prompt_style: str = "accessibility"
    vision_prompt_picker_enabled: bool = False
    vision_disabled_builtin_styles: list[str] = field(default_factory=list)
    vision_custom_prompts: list[dict[str, Any]] = field(default_factory=list)
    vision_builtin_overrides: dict[str, str] = field(default_factory=dict)
    # Structured List Studio app-scope defaults (serialized StructuredListSettings);
    # empty means "use the PRD recommended defaults". See quill/core/lists.
    list_studio_settings: dict[str, Any] = field(default_factory=dict)
    dev_console_consent_accepted: bool = False
    # ERASER: Quill Eraser text hygiene checker.
    hygiene_min_confidence: str = "high"
    hygiene_allow_double_space_after_period: bool = False
    hygiene_max_blank_lines: int = 2
    hygiene_rules_disabled: str = ""  # comma-separated rule IDs
    # #303: Heading Organizer duplicate-H1 check. When true, the
    # organizer flags documents that have more than one H1 as an
    # accessibility warning. The default of False preserves the
    # pre-#303 behavior (only "must start at H1" and "skipped level"
    # issues were surfaced). Opt-in so existing users who deliberately
    # split long works into multiple top-level chapters are not
    # surprised by a new warning.
    heading_organizer_warn_duplicate_h1: bool = False
    # Batch document-to-speech chapterization (§4.8). When a document has
    # headings, the batch exporter can split each article into its own file
    # ("separate"), embed MP3 CHAP/CTOC chapter markers in one combined file
    # ("single"), or do neither ("none"). An optional configurable transition
    # sound plays at each article boundary, and a silence gap is inserted
    # between articles so listeners hear the transition. Chapter titles come
    # from the heading text; the lead-in section before the first heading uses
    # batch_speech_intro_section_title.
    batch_speech_chapter_mode: str = "none"  # none | single | separate
    batch_speech_chapter_sound_enabled: bool = False
    batch_speech_chapter_sound_id: str = ""
    batch_speech_chapter_sound_volume: int = 100  # 0-100
    batch_speech_article_gap_ms: int = 1200  # 0-10000
    batch_speech_sentence_gap_ms: int = 0  # 0-10000; pause between sentences (opt-in; see docs)
    batch_speech_tail_padding_ms: int = 300  # 0-10000; trailing pad per section (anti-clipping)
    batch_speech_intro_section_title: str = "Introduction"
    batch_speech_temp_folder: str = ""  # parent for scratch dirs; blank = system temp
    batch_speech_save_spoken_text: bool = False  # also save the text sent to the engine
    audio_studio_last_journey: str = "documents"  # remembered journey

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
        browse_mode_move_detail = (
            str(data.get("browse_mode_move_detail", "position")).strip().lower()
        )
        if browse_mode_move_detail not in {"none", "line", "position"}:
            browse_mode_move_detail = "position"
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
            quill_key_timeout_seconds = float(data.get("quill_key_timeout_seconds", 2.5))
        except (TypeError, ValueError):
            quill_key_timeout_seconds = 2.5
        if quill_key_timeout_seconds < 0:
            quill_key_timeout_seconds = 0.0
        if quill_key_timeout_seconds > 60:
            quill_key_timeout_seconds = 60.0
        # #265 follow-up: replace float seconds with a string-valued choice
        # (preset token) plus an integer custom-ms override. Unknown tokens
        # fall back to 'unlimited' so the consumer treats them as no
        # timeout. Custom-ms clamps to [0, 60000] ms = [0, 60] s.
        browse_mode_followon_timeout = (
            str(data.get("browse_mode_followon_timeout", "unlimited")).strip().lower()
        )
        if browse_mode_followon_timeout not in {
            "instant",
            "fast",
            "normal",
            "slow",
            "custom",
            "unlimited",
        }:
            browse_mode_followon_timeout = "unlimited"
        try:
            browse_mode_followon_custom_ms = int(data.get("browse_mode_followon_custom_ms", 4000))
        except (TypeError, ValueError):
            browse_mode_followon_custom_ms = 4000
        if browse_mode_followon_custom_ms < 0:
            browse_mode_followon_custom_ms = 0
        if browse_mode_followon_custom_ms > 60000:
            browse_mode_followon_custom_ms = 60000
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
        docx_read_engine = str(data.get("docx_read_engine", "auto")).strip().lower()
        if docx_read_engine not in {"auto", "markitdown", "pandoc"}:
            docx_read_engine = "auto"
        docx_write_engine = str(data.get("docx_write_engine", "auto")).strip().lower()
        if docx_write_engine not in {"auto", "native", "pandoc"}:
            docx_write_engine = "auto"
        plain_text_link_style = str(data.get("plain_text_link_style", "text_url")).strip().lower()
        if plain_text_link_style not in {"text", "text_url", "url", "markdown"}:
            plain_text_link_style = "text_url"
        indent_with_tabs = bool(data.get("indent_with_tabs", False))
        try:
            indent_size = int(data.get("indent_size", 4))
        except (TypeError, ValueError):
            indent_size = 4
        auto_check_updates = bool(data.get("auto_check_updates", True))
        beta_updates = bool(data.get("beta_updates", False))
        apply_recommended_keymap_updates = bool(data.get("apply_recommended_keymap_updates", True))
        raw_applied = data.get("applied_recommended_updates", [])
        applied_recommended_updates = (
            [str(item) for item in raw_applied if isinstance(item, str)]
            if isinstance(raw_applied, list)
            else []
        )
        migration_notice = str(data.get("migration_notice", "announce")).strip().lower()
        if migration_notice not in {"silent", "announce", "prompt"}:
            migration_notice = "announce"
        skipped_update_version = str(data.get("skipped_update_version", "")).strip()
        last_update_check = str(data.get("last_update_check", "")).strip()
        try:
            recent_files_limit = int(data.get("recent_files_limit", 10))
        except (TypeError, ValueError):
            recent_files_limit = 10
        recent_files_auto_clear_missing = bool(data.get("recent_files_auto_clear_missing", False))
        first_line_as_title = bool(data.get("first_line_as_title", True))
        restore_points_enabled = bool(data.get("restore_points_enabled", True))
        restore_points_max_mb = _clamp_int(data.get("restore_points_max_mb", 200), 200, 10, 5000)
        warm_dictation_model = bool(data.get("warm_dictation_model", True))
        warm_kokoro_model = bool(data.get("warm_kokoro_model", True))
        tray_enabled = bool(data.get("tray_enabled", False))
        persistent_undo = bool(data.get("persistent_undo", False))
        spellcheck_as_you_type = bool(data.get("spellcheck_as_you_type", False))
        spell_check_before_save = bool(data.get("spell_check_before_save", False))
        spellcheck_language = str(data.get("spellcheck_language", "en_US")).strip() or "en_US"
        reveal_codes_visible = bool(data.get("reveal_codes_visible", False))
        reveal_codes_view = str(data.get("reveal_codes_view", "structured")).strip().lower()
        if reveal_codes_view not in {"structured", "flowed"}:
            reveal_codes_view = "structured"
        reveal_codes_verbosity = str(data.get("reveal_codes_verbosity", "balanced")).strip().lower()
        if reveal_codes_verbosity not in {"quiet", "balanced", "detailed"}:
            reveal_codes_verbosity = "balanced"
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
        read_aloud_engine = str(data.get("read_aloud_engine", "sapi5")).strip().lower()
        if read_aloud_engine == "pyttsx3":  # migrate the retired engine id
            read_aloud_engine = "sapi5"
        _valid_engines = {
            "sapi5",
            "dectalk",
            "piper",
            "kokoro",
            "espeak",
            "elevenlabs",
        }
        if read_aloud_engine not in _valid_engines:
            read_aloud_engine = "sapi5"
        read_aloud_elevenlabs_voice = str(data.get("read_aloud_elevenlabs_voice", "")).strip()
        read_aloud_elevenlabs_model = str(data.get("read_aloud_elevenlabs_model", "")).strip()
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
        ai_tts_provider = str(data.get("ai_tts_provider", "openai")).strip().lower()
        if ai_tts_provider not in {"openai", "gemini", "elevenlabs"}:
            ai_tts_provider = "openai"
        ai_tts_model = str(data.get("ai_tts_model", "")).strip()
        ai_tts_voice = str(data.get("ai_tts_voice", "")).strip()
        try:
            ai_tts_speed = float(data.get("ai_tts_speed", 1.0))
        except (TypeError, ValueError):
            ai_tts_speed = 1.0
        ai_tts_speed = max(0.25, min(4.0, ai_tts_speed))
        if announcement_backend not in {"auto", "prism", "status_only"}:
            announcement_backend = "auto"
        announcement_trace_enabled = bool(data.get("announcement_trace_enabled", False))
        announcement_startup_tips_enabled = bool(
            data.get("announcement_startup_tips_enabled", False)
        )
        verbosity_speech_enabled = bool(data.get("verbosity_speech_enabled", True))
        announce_screen_reader_detected = bool(data.get("announce_screen_reader_detected", False))
        assistant_enabled = bool(data.get("assistant_enabled", False))
        assistant_prompt_style = str(data.get("assistant_prompt_style", "balanced")).strip().lower()
        if assistant_prompt_style not in {"balanced", "concise", "gentle", "technical"}:
            assistant_prompt_style = "balanced"
        markdown_clipboard_format = (
            str(data.get("markdown_clipboard_format", "html")).strip().lower() or "html"
        )
        if markdown_clipboard_format not in {"html", "rtf"}:
            markdown_clipboard_format = "html"
        engine = str(data.get("dictation_engine", "windows")).strip().lower()
        engine = "offline" if engine in {"vosk", "whisper"} else engine  # #617 migrate
        dictation_engine = engine if engine in {"offline", "windows", "cloud"} else "windows"
        dictation_language = str(data.get("dictation_language", "en-US")).strip() or "en-US"
        dictation_model = str(data.get("dictation_model", "base")).strip() or "base"
        dictation_device_index = int(data.get("dictation_device_index", -1))
        if dictation_device_index < -1:
            dictation_device_index = -1
        # Dictation policy: durations clamp non-negative (0 disables a cap).
        dictation_max_locked_seconds = _coerce_non_negative_float(
            data.get("dictation_max_locked_seconds", 300.0), 300.0
        )
        dictation_min_hold_seconds = _coerce_non_negative_float(
            data.get("dictation_min_hold_seconds", 0.0), 0.0
        )
        dictation_stop_on_focus_loss = bool(data.get("dictation_stop_on_focus_loss", True))
        dictation_intelligent_spacing = bool(data.get("dictation_intelligent_spacing", True))
        dictation_onboarding_shown = bool(data.get("dictation_onboarding_shown", False))
        announce_formatting_on_move = bool(data.get("announce_formatting_on_move", False))
        announce_dialog_transitions = bool(data.get("announce_dialog_transitions", False))
        low_resource_mode = bool(data.get("low_resource_mode", False))
        idle_unload_minutes = _clamp_int(data.get("idle_unload_minutes", 10), 10, 0, 240)
        announce_indent_depth = bool(data.get("announce_indent_depth", True))
        spoken_echo_on_double_press = bool(data.get("spoken_echo_on_double_press", True))
        editor_control_kind = str(data.get("editor_control_kind", "")).strip().lower()
        if editor_control_kind not in {"rich2", "rich", "plain"}:
            # Back-compat: the earlier editor_use_legacy_richedit bool -> "rich".
            editor_control_kind = (
                "rich" if bool(data.get("editor_use_legacy_richedit", False)) else "rich2"
            )
        experimental_editor_surface = (
            str(data.get("experimental_editor_surface", "default")).strip().lower()
        )
        allowed_surfaces = {
            "default",
            "rich2",
            "rich",
            "plain",
            "rtf",
            "win32",
            "stc",
            "richedit_rtf",
        }
        if experimental_editor_surface not in allowed_surfaces:
            experimental_editor_surface = "default"
        editor_hide_border = bool(data.get("editor_hide_border", False))
        experimental_acknowledged = bool(data.get("experimental_acknowledged", False))
        experimental_editor_surfaces_enabled = bool(
            data.get("experimental_editor_surfaces_enabled", False)
        )
        experimental_richedit_emulate_sysedit = bool(
            data.get("experimental_richedit_emulate_sysedit", False)
        )
        glow_experimental_enabled = bool(data.get("glow_experimental_enabled", False))
        publishing_experimental_enabled = bool(data.get("publishing_experimental_enabled", False))
        table_studio_experimental_enabled = bool(
            data.get("table_studio_experimental_enabled", False)
        )
        edge_read_aloud_enabled = bool(data.get("edge_read_aloud_enabled", False))
        plain_text_with_formatting = str(data.get("plain_text_with_formatting", "ask"))
        if plain_text_with_formatting not in {"ask", "illuminate", "plain"}:
            plain_text_with_formatting = "ask"
        pronunciation_enabled = bool(data.get("pronunciation_enabled", True))
        pronunciation_ids_raw = data.get("pronunciation_enabled_dictionary_ids")
        pronunciation_enabled_dictionary_ids = (
            [str(i) for i in pronunciation_ids_raw if isinstance(i, str)]
            if isinstance(pronunciation_ids_raw, list)
            else []
        )
        tts_normalization_enabled = bool(data.get("tts_normalization_enabled", True))
        tts_normalization_raw = data.get("tts_normalization")
        tts_normalization = (
            dict(tts_normalization_raw) if isinstance(tts_normalization_raw, dict) else {}
        )
        speech_provider = str(data.get("speech_provider", "")).strip().lower()
        if speech_provider not in {"", "whispercpp", "fasterwhisper", "vosk"}:
            speech_provider = ""
        speech_default_model_id = str(data.get("speech_default_model_id", "")).strip()
        bw_speech_selection_mode = (
            str(data.get("bw_speech_selection_mode", "recommended")).strip().lower()
            or "recommended"
        )
        if bw_speech_selection_mode not in {"recommended", "manual"}:
            bw_speech_selection_mode = "recommended"
        bw_speech_model_id = (
            str(data.get("bw_speech_model_id", "whisper-base")).strip() or "whisper-base"
        )
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
        vault_root = str(data.get("vault_root", "")).strip()
        vault_templates_folder = str(data.get("vault_templates_folder", "")).strip()
        vault_daily_pattern = str(data.get("vault_daily_pattern", "")).strip()
        ocr_language = str(data.get("ocr_language", "")).strip()
        tesseract_path = str(data.get("tesseract_path", "")).strip()
        datalab_enabled = bool(data.get("datalab_enabled", False))
        datalab_endpoint = str(data.get("datalab_endpoint", "https://www.datalab.to")).strip()
        if not datalab_endpoint.lower().startswith("https://"):
            datalab_endpoint = "https://www.datalab.to"
        datalab_mode = str(data.get("datalab_mode", "balanced")).strip().lower()
        if datalab_mode not in {"fast", "balanced", "accurate"}:
            datalab_mode = "balanced"
        datalab_output = str(data.get("datalab_output", "markdown")).strip().lower()
        if datalab_output not in {"markdown", "html", "json"}:
            datalab_output = "markdown"
        datalab_paginate = bool(data.get("datalab_paginate", True))
        # #620: Simple File Open dialog opt-in.
        use_simple_file_dialog = bool(data.get("use_simple_file_dialog", False))
        watch_folder_include_subfolders = bool(data.get("watch_folder_include_subfolders", False))
        watch_folder_process_existing = bool(data.get("watch_folder_process_existing", False))
        watch_folder_auto_start = bool(data.get("watch_folder_auto_start", False))
        # #262: Pandoc Import / Export defaults.
        import_export_recursive = bool(data.get("import_export_recursive", True))
        import_export_overwrite = str(data.get("import_export_overwrite", "ask")).strip()
        if import_export_overwrite not in {"ask", "never", "always"}:
            import_export_overwrite = "ask"
        import_export_output_layout = str(
            data.get("import_export_output_layout", "subfolder")
        ).strip()
        if import_export_output_layout not in {"subfolder", "same_folder"}:
            import_export_output_layout = "subfolder"
        import_export_last_folder = str(data.get("import_export_last_folder", "")).strip()
        convert_file_last_output_dir = str(data.get("convert_file_last_output_dir", "")).strip()
        convert_file_last_format = str(data.get("convert_file_last_format", "gfm")).strip()
        if not convert_file_last_format:
            convert_file_last_format = "gfm"
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
        voice_conversation_enabled = bool(data.get("voice_conversation_enabled", False))

        def _voice_ms(key: str, default: int) -> int:
            try:
                value = int(data.get(key, default))
            except (TypeError, ValueError):
                return default
            return value if value >= 0 else default

        voice_conversation_silence_ms = _voice_ms("voice_conversation_silence_ms", 2000)
        voice_conversation_review_ms = _voice_ms("voice_conversation_review_ms", 900)
        voice_conversation_followup_ms = _voice_ms("voice_conversation_followup_ms", 3000)
        voice_conversation_thinking_ms = _voice_ms("voice_conversation_thinking_ms", 2000)
        voice_conversation_user_name = str(data.get("voice_conversation_user_name", "")).strip()
        voice_conversation_spoken_cues = bool(data.get("voice_conversation_spoken_cues", False))
        voice_recognition_engine = str(data.get("voice_recognition_engine", "")).strip().lower()
        if voice_recognition_engine not in {"", "whispercpp", "vosk"}:
            voice_recognition_engine = ""
        voice_wakeword_persist = bool(data.get("voice_wakeword_persist", False))
        # Always-listening never survives a restart unless the user opted into
        # persistence; otherwise it always loads off, no matter what was saved.
        voice_wakeword_enabled = voice_wakeword_persist and bool(
            data.get("voice_wakeword_enabled", False)
        )
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
        read_aloud_follow_cursor = bool(data.get("read_aloud_follow_cursor", False))
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
        # Verbosity system (rebuild) scalar prefs.
        verbosity_mastery_enabled = bool(data.get("verbosity_mastery_enabled", True))
        verbosity_mastery_threshold = _clamp_int(
            data.get("verbosity_mastery_threshold", 25), 25, 1, 1000
        )
        verbosity_validation_mode = (
            str(data.get("verbosity_validation_mode", "on_button")).strip().lower()
        )
        if verbosity_validation_mode not in {"on_button", "on_focus", "live"}:
            verbosity_validation_mode = "on_button"
        language_detection_mode = str(data.get("language_detection_mode", "off")).strip().lower()
        if language_detection_mode not in {"off", "hint", "prompt", "auto"}:
            language_detection_mode = "off"
        verbosity_history_enabled = bool(data.get("verbosity_history_enabled", True))
        verbosity_collapse_repeats = bool(data.get("verbosity_collapse_repeats", True))
        verbosity_max_announcements_per_window = _clamp_int(
            data.get("verbosity_max_announcements_per_window", 0), 0, 0, 1000
        )
        verbosity_history_limit = _clamp_int(
            data.get("verbosity_history_limit", 100), 100, 1, 10000
        )
        verbosity_history_clear_on_exit = bool(data.get("verbosity_history_clear_on_exit", False))
        verbosity_task_profile_suggestions = bool(
            data.get("verbosity_task_profile_suggestions", False)
        )
        verbosity_safe_mode_enabled = bool(data.get("verbosity_safe_mode_enabled", False))
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
        ai_chat_default_provider = str(data.get("ai_chat_default_provider", "")).strip()
        ai_chat_default_model = str(data.get("ai_chat_default_model", ""))
        ollama_base_url = (
            str(data.get("ollama_base_url", "http://localhost:11434")).strip()
            or "http://localhost:11434"
        )
        ai_prompt_default_model = str(data.get("ai_prompt_default_model", ""))
        language = str(data.get("language", "")).strip()
        setup_wizard_completed = bool(data.get("setup_wizard_completed", False))
        setup_wizard_intent = str(data.get("setup_wizard_intent", "")).strip()
        setup_wizard_wants_ai = bool(data.get("setup_wizard_wants_ai", False))
        setup_wizard_wants_braille = bool(data.get("setup_wizard_wants_braille", False))
        setup_wizard_wants_automation = bool(data.get("setup_wizard_wants_automation", False))
        upgrade_prompt_braille_pack = bool(data.get("upgrade_prompt_braille_pack", False))
        console_enabled = bool(data.get("console_enabled", True))
        auto_ask_crash_submit = bool(data.get("auto_ask_crash_submit", True))
        try:
            console_python_timeout = int(data.get("console_python_timeout", 30))
        except (TypeError, ValueError):
            console_python_timeout = 30
        try:
            console_typescript_timeout = int(data.get("console_typescript_timeout", 30))
        except (TypeError, ValueError):
            console_typescript_timeout = 30
        dev_console_consent_accepted = bool(data.get("dev_console_consent_accepted", False))
        abbreviation_expansion = bool(data.get("abbreviation_expansion", False))
        abbreviation_expansion_sound = bool(data.get("abbreviation_expansion_sound", False))
        abbreviation_expansion_sound_file = str(data.get("abbreviation_expansion_sound_file", ""))
        sound_enabled = bool(data.get("sound_enabled", True))
        sound_pack_path = str(data.get("sound_pack_path", ""))
        try:
            sound_volume = int(data.get("sound_volume", 80))
        except (TypeError, ValueError):
            sound_volume = 80
        sound_volume = max(0, min(100, sound_volume))
        sound_events_disabled = str(data.get("sound_events_disabled", ""))
        indent_tone_scale = str(data.get("indent_tone_scale", ""))
        if indent_tone_scale not in ("", "pentatonic", "whole_tone", "diatonic", "chromatic"):
            indent_tone_scale = ""
        abbreviation_backspace_behavior = str(data.get("abbreviation_backspace_behavior", "delete"))
        if abbreviation_backspace_behavior not in {"delete", "revert"}:
            abbreviation_backspace_behavior = "delete"
        # Braille Mode (BR-008) field parsing with clamping and validation.
        try:
            braille_cells_per_line = int(data.get("braille_cells_per_line", 40))
        except (TypeError, ValueError):
            braille_cells_per_line = 40
        braille_cells_per_line = max(28, min(42, braille_cells_per_line))
        try:
            braille_lines_per_page = int(data.get("braille_lines_per_page", 25))
        except (TypeError, ValueError):
            braille_lines_per_page = 25
        braille_lines_per_page = max(20, min(30, braille_lines_per_page))
        try:
            page_estimate_words_per_page = int(data.get("page_estimate_words_per_page", 300))
        except (TypeError, ValueError):
            page_estimate_words_per_page = 300
        page_estimate_words_per_page = max(150, min(600, page_estimate_words_per_page))
        braille_use_form_feeds = bool(data.get("braille_use_form_feeds", True))
        braille_calculate_pages = bool(data.get("braille_calculate_pages", True))
        braille_save_sidecar = bool(data.get("braille_save_sidecar", True))
        braille_status_verbosity = str(data.get("braille_status_verbosity", "normal"))
        if braille_status_verbosity not in {"brief", "normal", "detailed"}:
            braille_status_verbosity = "normal"
        braille_auto_announce_page_changes = bool(
            data.get("braille_auto_announce_page_changes", False)
        )
        braille_auto_announce_print_page_changes = bool(
            data.get("braille_auto_announce_print_page_changes", False)
        )
        braille_auto_announce_line_overflow = bool(
            data.get("braille_auto_announce_line_overflow", False)
        )
        braille_include_proofing_status = bool(data.get("braille_include_proofing_status", True))
        braille_include_running_head = bool(data.get("braille_include_running_head", False))
        braille_include_continuation = bool(data.get("braille_include_continuation", True))
        # Spelling Review (F7) fields.
        spell_review_verbosity = str(data.get("spell_review_verbosity", "balanced")).strip().lower()
        if spell_review_verbosity not in {"concise", "balanced", "detailed"}:
            spell_review_verbosity = "balanced"
        spell_review_spell_word = bool(data.get("spell_review_spell_word", True))
        spell_review_spell_word_pause_ms = max(
            100, min(3000, int(data.get("spell_review_spell_word_pause_ms", 800)))
        )
        spell_review_wrap_to_beginning = bool(data.get("spell_review_wrap_to_beginning", True))
        spell_review_context_mode = (
            str(data.get("spell_review_context_mode", "sentence")).strip().lower()
        )
        if spell_review_context_mode not in {"sentence", "paragraph"}:
            spell_review_context_mode = "sentence"
        # Vision prompt library fields
        vision_default_prompt_style = str(
            data.get("vision_default_prompt_style", "accessibility")
        ).strip()
        vision_prompt_picker_enabled = bool(data.get("vision_prompt_picker_enabled", False))
        vision_disabled_builtin_styles_raw = data.get("vision_disabled_builtin_styles")
        vision_disabled_builtin_styles: list[str] = (
            [str(s) for s in vision_disabled_builtin_styles_raw]
            if isinstance(vision_disabled_builtin_styles_raw, list)
            else []
        )
        vision_custom_prompts_raw = data.get("vision_custom_prompts")
        vision_custom_prompts: list[dict[str, Any]] = (
            [e for e in vision_custom_prompts_raw if isinstance(e, dict) and e.get("id")]
            if isinstance(vision_custom_prompts_raw, list)
            else []
        )
        vision_builtin_overrides_raw = data.get("vision_builtin_overrides")
        vision_builtin_overrides: dict[str, str] = (
            {
                k: str(v)
                for k, v in vision_builtin_overrides_raw.items()
                if isinstance(k, str) and isinstance(v, str) and v.strip()
            }
            if isinstance(vision_builtin_overrides_raw, dict)
            else {}
        )
        list_studio_settings_raw = data.get("list_studio_settings")
        list_studio_settings = (
            dict(list_studio_settings_raw) if isinstance(list_studio_settings_raw, dict) else {}
        )
        if vision_default_prompt_style not in BUILTIN_STYLE_IDS and not any(
            e.get("id") == vision_default_prompt_style for e in vision_custom_prompts
        ):
            vision_default_prompt_style = "accessibility"
        raw_mp = int(data.get("multi_press_window_ms", 400))
        multi_press_window_ms = max(100, min(1000, raw_mp))
        hygiene_min_confidence = str(data.get("hygiene_min_confidence", "high")).strip().lower()
        if hygiene_min_confidence not in {"high", "medium", "low"}:
            hygiene_min_confidence = "high"
        hygiene_allow_double_space_after_period = bool(
            data.get("hygiene_allow_double_space_after_period", False)
        )
        try:
            hygiene_max_blank_lines = max(1, min(10, int(data.get("hygiene_max_blank_lines", 2))))
        except (TypeError, ValueError):
            hygiene_max_blank_lines = 2
        hygiene_rules_disabled = str(data.get("hygiene_rules_disabled", "")).strip()
        # #303: Heading Organizer duplicate-H1 warning opt-in. Default
        # to False so existing users are not surprised.
        heading_organizer_warn_duplicate_h1 = bool(
            data.get("heading_organizer_warn_duplicate_h1", False)
        )
        # Batch document-to-speech chapterization (§4.8).
        batch_speech_chapter_mode = (
            str(data.get("batch_speech_chapter_mode", "none")).strip().lower()
        )
        if batch_speech_chapter_mode not in {"none", "single", "separate"}:
            batch_speech_chapter_mode = "none"
        batch_speech_chapter_sound_enabled = bool(
            data.get("batch_speech_chapter_sound_enabled", False)
        )
        batch_speech_chapter_sound_id = str(data.get("batch_speech_chapter_sound_id", "")).strip()
        batch_speech_chapter_sound_volume = _clamp_int(
            data.get("batch_speech_chapter_sound_volume", 100), 100, 0, 100
        )
        batch_speech_article_gap_ms = _clamp_int(
            data.get("batch_speech_article_gap_ms", 1200), 1200, 0, 10000
        )
        batch_speech_sentence_gap_ms = _clamp_int(
            data.get("batch_speech_sentence_gap_ms", 0), 0, 0, 10000
        )
        batch_speech_tail_padding_ms = _clamp_int(
            data.get("batch_speech_tail_padding_ms", 300), 300, 0, 10000
        )
        batch_speech_intro_section_title = (
            str(data.get("batch_speech_intro_section_title", "Introduction")).strip()
            or "Introduction"
        )
        batch_speech_temp_folder = str(data.get("batch_speech_temp_folder", "")).strip()
        batch_speech_save_spoken_text = bool(data.get("batch_speech_save_spoken_text", False))
        # Remember the last journey so the wizard's first page lands on
        # the radio the user used last. Falls back to "documents" when
        # missing or unrecognized so older settings files still work.
        audio_studio_last_journey = (
            str(data.get("audio_studio_last_journey", "documents")).strip().lower()
        )
        if audio_studio_last_journey not in {"documents", "audio", "edit"}:
            audio_studio_last_journey = "documents"
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
            browse_mode_move_detail=browse_mode_move_detail,
            browse_mode_preload_cache=browse_mode_preload_cache,
            quill_key_binding=quill_key_binding,
            quill_key_timeout_seconds=quill_key_timeout_seconds,
            browse_mode_followon_timeout=browse_mode_followon_timeout,
            browse_mode_followon_custom_ms=browse_mode_followon_custom_ms,
            csv_open_mode=csv_open_mode,
            word_open_mode=word_open_mode,
            editor_surface=editor_surface,
            save_as_surface_sync=save_as_surface_sync,
            docx_read_engine=docx_read_engine,
            docx_write_engine=docx_write_engine,
            plain_text_link_style=plain_text_link_style,
            indent_with_tabs=indent_with_tabs,
            indent_size=indent_size,
            auto_check_updates=auto_check_updates,
            beta_updates=beta_updates,
            apply_recommended_keymap_updates=apply_recommended_keymap_updates,
            applied_recommended_updates=applied_recommended_updates,
            migration_notice=migration_notice,
            skipped_update_version=skipped_update_version,
            last_update_check=last_update_check,
            recent_files_limit=recent_files_limit,
            recent_files_auto_clear_missing=recent_files_auto_clear_missing,
            first_line_as_title=first_line_as_title,
            restore_points_enabled=restore_points_enabled,
            restore_points_max_mb=restore_points_max_mb,
            warm_dictation_model=warm_dictation_model,
            warm_kokoro_model=warm_kokoro_model,
            tray_enabled=tray_enabled,
            persistent_undo=persistent_undo,
            spellcheck_as_you_type=spellcheck_as_you_type,
            spell_check_before_save=spell_check_before_save,
            spellcheck_language=spellcheck_language,
            reveal_codes_visible=reveal_codes_visible,
            reveal_codes_view=reveal_codes_view,
            reveal_codes_verbosity=reveal_codes_verbosity,
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
            read_aloud_elevenlabs_voice=read_aloud_elevenlabs_voice,
            read_aloud_elevenlabs_model=read_aloud_elevenlabs_model,
            ai_tts_provider=ai_tts_provider,
            ai_tts_model=ai_tts_model,
            ai_tts_voice=ai_tts_voice,
            ai_tts_speed=ai_tts_speed,
            announcement_trace_enabled=announcement_trace_enabled,
            announcement_startup_tips_enabled=announcement_startup_tips_enabled,
            verbosity_speech_enabled=verbosity_speech_enabled,
            announce_screen_reader_detected=announce_screen_reader_detected,
            assistant_enabled=assistant_enabled,
            assistant_prompt_style=assistant_prompt_style,
            markdown_clipboard_format=markdown_clipboard_format,
            dictation_engine=dictation_engine,
            dictation_language=dictation_language,
            dictation_model=dictation_model,
            dictation_device_index=dictation_device_index,
            dictation_max_locked_seconds=dictation_max_locked_seconds,
            dictation_stop_on_focus_loss=dictation_stop_on_focus_loss,
            dictation_intelligent_spacing=dictation_intelligent_spacing,
            announce_formatting_on_move=announce_formatting_on_move,
            announce_dialog_transitions=announce_dialog_transitions,
            low_resource_mode=low_resource_mode,
            idle_unload_minutes=idle_unload_minutes,
            announce_indent_depth=announce_indent_depth,
            spoken_echo_on_double_press=spoken_echo_on_double_press,
            editor_control_kind=editor_control_kind,
            experimental_editor_surface=experimental_editor_surface,
            editor_hide_border=editor_hide_border,
            experimental_richedit_emulate_sysedit=experimental_richedit_emulate_sysedit,
            experimental_acknowledged=experimental_acknowledged,
            experimental_editor_surfaces_enabled=experimental_editor_surfaces_enabled,
            glow_experimental_enabled=glow_experimental_enabled,
            publishing_experimental_enabled=publishing_experimental_enabled,
            table_studio_experimental_enabled=table_studio_experimental_enabled,
            edge_read_aloud_enabled=edge_read_aloud_enabled,
            plain_text_with_formatting=plain_text_with_formatting,
            dictation_onboarding_shown=dictation_onboarding_shown,
            pronunciation_enabled=pronunciation_enabled,
            pronunciation_enabled_dictionary_ids=pronunciation_enabled_dictionary_ids,
            tts_normalization_enabled=tts_normalization_enabled,
            tts_normalization=tts_normalization,
            dictation_min_hold_seconds=dictation_min_hold_seconds,
            speech_provider=speech_provider,
            speech_default_model_id=speech_default_model_id,
            bw_speech_selection_mode=bw_speech_selection_mode,
            bw_speech_model_id=bw_speech_model_id,
            bw_provider_id=bw_provider_id,
            bw_provider_mode=bw_provider_mode,
            bw_show_cloud_providers=bw_show_cloud_providers,
            bw_auto_open_status_page_on_download_start=bw_auto_open_status_page_on_download_start,
            bw_safe_mode_lock=bw_safe_mode_lock,
            status_page_refresh_announcement_cadence=status_page_refresh_announcement_cadence,
            voice_commands_enabled=voice_commands_enabled,
            voice_conversation_enabled=voice_conversation_enabled,
            voice_conversation_silence_ms=voice_conversation_silence_ms,
            voice_conversation_review_ms=voice_conversation_review_ms,
            voice_conversation_followup_ms=voice_conversation_followup_ms,
            voice_conversation_thinking_ms=voice_conversation_thinking_ms,
            voice_conversation_user_name=voice_conversation_user_name,
            voice_conversation_spoken_cues=voice_conversation_spoken_cues,
            voice_recognition_engine=voice_recognition_engine,
            voice_wakeword_enabled=voice_wakeword_enabled,
            voice_wakeword_persist=voice_wakeword_persist,
            watch_folder_enabled=watch_folder_enabled,
            watch_folder_path=watch_folder_path,
            startup_folder=startup_folder,
            vault_root=vault_root,
            vault_templates_folder=vault_templates_folder,
            vault_daily_pattern=vault_daily_pattern,
            ocr_language=ocr_language,
            tesseract_path=tesseract_path,
            datalab_enabled=datalab_enabled,
            datalab_endpoint=datalab_endpoint,
            datalab_mode=datalab_mode,
            datalab_output=datalab_output,
            datalab_paginate=datalab_paginate,
            use_simple_file_dialog=use_simple_file_dialog,
            watch_folder_include_subfolders=watch_folder_include_subfolders,
            watch_folder_process_existing=watch_folder_process_existing,
            watch_folder_auto_start=watch_folder_auto_start,
            watch_folder_poll_interval_seconds=watch_folder_poll_interval_seconds,
            import_export_recursive=import_export_recursive,
            import_export_overwrite=import_export_overwrite,
            import_export_output_layout=import_export_output_layout,
            import_export_last_folder=import_export_last_folder,
            convert_file_last_output_dir=convert_file_last_output_dir,
            convert_file_last_format=convert_file_last_format,
            autosave_interval_seconds=autosave_interval_seconds,
            quick_nav_debounce_ms=quick_nav_debounce_ms,
            quick_nav_min_chars=quick_nav_min_chars,
            announcement_throttle_ms=announcement_throttle_ms,
            read_aloud_sentence_pause_ms=read_aloud_sentence_pause_ms,
            read_aloud_follow_cursor=read_aloud_follow_cursor,
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
            verbosity_mastery_enabled=verbosity_mastery_enabled,
            verbosity_mastery_threshold=verbosity_mastery_threshold,
            verbosity_validation_mode=verbosity_validation_mode,
            language_detection_mode=language_detection_mode,
            verbosity_history_enabled=verbosity_history_enabled,
            verbosity_history_limit=verbosity_history_limit,
            verbosity_history_clear_on_exit=verbosity_history_clear_on_exit,
            verbosity_task_profile_suggestions=verbosity_task_profile_suggestions,
            verbosity_safe_mode_enabled=verbosity_safe_mode_enabled,
            verbosity_collapse_repeats=verbosity_collapse_repeats,
            verbosity_max_announcements_per_window=verbosity_max_announcements_per_window,
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
            abbreviation_expansion=abbreviation_expansion,
            abbreviation_expansion_sound=abbreviation_expansion_sound,
            abbreviation_expansion_sound_file=abbreviation_expansion_sound_file,
            multi_press_window_ms=multi_press_window_ms,
            language=language,
            setup_wizard_completed=setup_wizard_completed,
            setup_wizard_intent=setup_wizard_intent,
            setup_wizard_wants_ai=setup_wizard_wants_ai,
            setup_wizard_wants_braille=setup_wizard_wants_braille,
            setup_wizard_wants_automation=setup_wizard_wants_automation,
            upgrade_prompt_braille_pack=upgrade_prompt_braille_pack,
            console_enabled=console_enabled,
            auto_ask_crash_submit=auto_ask_crash_submit,
            console_python_timeout=console_python_timeout,
            console_typescript_timeout=console_typescript_timeout,
            sound_enabled=sound_enabled,
            sound_pack_path=sound_pack_path,
            sound_volume=sound_volume,
            sound_events_disabled=sound_events_disabled,
            indent_tone_scale=indent_tone_scale,
            abbreviation_backspace_behavior=abbreviation_backspace_behavior,
            braille_cells_per_line=braille_cells_per_line,
            braille_lines_per_page=braille_lines_per_page,
            page_estimate_words_per_page=page_estimate_words_per_page,
            braille_use_form_feeds=braille_use_form_feeds,
            braille_calculate_pages=braille_calculate_pages,
            braille_save_sidecar=braille_save_sidecar,
            braille_status_verbosity=braille_status_verbosity,
            braille_auto_announce_page_changes=braille_auto_announce_page_changes,
            braille_auto_announce_print_page_changes=braille_auto_announce_print_page_changes,
            braille_auto_announce_line_overflow=braille_auto_announce_line_overflow,
            braille_include_proofing_status=braille_include_proofing_status,
            braille_include_running_head=braille_include_running_head,
            braille_include_continuation=braille_include_continuation,
            spell_review_verbosity=spell_review_verbosity,
            spell_review_spell_word=spell_review_spell_word,
            spell_review_spell_word_pause_ms=spell_review_spell_word_pause_ms,
            spell_review_wrap_to_beginning=spell_review_wrap_to_beginning,
            spell_review_context_mode=spell_review_context_mode,
            vision_default_prompt_style=vision_default_prompt_style,
            vision_prompt_picker_enabled=vision_prompt_picker_enabled,
            vision_disabled_builtin_styles=vision_disabled_builtin_styles,
            vision_custom_prompts=vision_custom_prompts,
            vision_builtin_overrides=vision_builtin_overrides,
            list_studio_settings=list_studio_settings,
            dev_console_consent_accepted=dev_console_consent_accepted,
            hygiene_min_confidence=hygiene_min_confidence,
            hygiene_allow_double_space_after_period=hygiene_allow_double_space_after_period,
            hygiene_max_blank_lines=hygiene_max_blank_lines,
            hygiene_rules_disabled=hygiene_rules_disabled,
            heading_organizer_warn_duplicate_h1=heading_organizer_warn_duplicate_h1,
            batch_speech_chapter_mode=batch_speech_chapter_mode,
            batch_speech_chapter_sound_enabled=batch_speech_chapter_sound_enabled,
            batch_speech_chapter_sound_id=batch_speech_chapter_sound_id,
            batch_speech_chapter_sound_volume=batch_speech_chapter_sound_volume,
            batch_speech_article_gap_ms=batch_speech_article_gap_ms,
            batch_speech_sentence_gap_ms=batch_speech_sentence_gap_ms,
            batch_speech_tail_padding_ms=batch_speech_tail_padding_ms,
            batch_speech_temp_folder=batch_speech_temp_folder,
            batch_speech_save_spoken_text=batch_speech_save_spoken_text,
            batch_speech_intro_section_title=batch_speech_intro_section_title,
            audio_studio_last_journey=audio_studio_last_journey,
        )


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def load_settings() -> Settings:
    """Load settings, converting any legacy file to the canonical delta on the way.

    The on-disk file is a *delta* of the user's overrides relative to
    ``Settings()`` plus a ``schema_version`` stamp (see
    :mod:`quill.core.settings_migration`), so any field the user never
    customized always tracks the current default. The generic load / migrate /
    backup / resave is shared with every other versioned store
    (:func:`quill.core.versioned_store.load_with_migration`): a pre-current-schema
    file is backed up and rewritten to the canonical delta exactly once.
    """
    # SET-5: read the nested versioned document, a legacy flat file, or junk.
    from quill.core.settings_migration import (
        from_versioned,
        is_legacy_settings_document,
        to_versioned,
    )

    return load_with_migration(
        settings_path(),
        store_name="settings",
        parse=from_versioned,
        serialize=to_versioned,
        is_legacy=is_legacy_settings_document,
        default=Settings,
    )


def save_settings(settings: Settings) -> None:
    # SET-5: persist the nested, versioned *delta* document (overrides only),
    # so future default changes flow through to the user automatically.
    from quill.core.settings_migration import to_versioned

    write_json_atomic(settings_path(), to_versioned(settings))
