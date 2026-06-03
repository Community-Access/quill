"""UI-agnostic registry describing user settings as searchable, groupable specs.

This is the model layer behind the tabbed Settings surface (SET-1), the search
and per-setting reset (SET-6), and export/import/reset to defaults (SET-7). It
deliberately reuses the flat :class:`~quill.core.settings.Settings` dataclass and
its :meth:`Settings.from_dict` validation, so every value set or imported through
this registry is normalized and clamped exactly as a loaded settings file would
be. No ``wx`` imports: the dialog binds to this registry, not the other way
round.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from quill.core.settings import Settings

#: Bump when the exported document shape changes in a backward-incompatible way.
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """One tunable setting, mapped to a :class:`Settings` attribute."""

    key: str
    label: str
    group: str
    kind: str  # "bool" | "choice" | "int" | "float" | "text"
    description: str = ""
    choices: tuple[tuple[str, str], ...] = ()  # (stored value, human label)
    minimum: float | None = None
    maximum: float | None = None
    feature_id: str = ""
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SettingGroup:
    """A labelled cluster of settings, surfaced as one tab."""

    id: str
    title: str
    description: str = ""


SETTING_GROUPS: tuple[SettingGroup, ...] = (
    SettingGroup("general", "General", "Appearance, window, and startup behavior."),
    SettingGroup("editing", "Editing", "How the editor behaves while you write."),
    SettingGroup(
        "navigation",
        "Navigation and QUILL Key",
        "Structural movement, browse mode, and the QUILL key.",
    ),
    SettingGroup(
        "accessibility",
        "Accessibility and Announcements",
        "Screen-reader announcements and accessibility behavior.",
    ),
    SettingGroup("read_aloud", "Read Aloud", "Spoken playback engine and voice tuning."),
    SettingGroup("ai", "AI and Assistant", "Writing assistant tone and behavior."),
    SettingGroup(
        "transcription",
        "Transcription",
        "BITS Whisperer speech-model and provider behavior.",
    ),
    SettingGroup(
        "watch",
        "Watch Folders",
        "Default behavior for watched-folder automation.",
    ),
    SettingGroup("updates", "Updates", "Update checking and release channel."),
)

_GROUP_IDS = {group.id for group in SETTING_GROUPS}


SETTING_SPECS: tuple[SettingSpec, ...] = (
    # --- General -----------------------------------------------------------
    SettingSpec(
        "theme",
        "Theme",
        "general",
        "choice",
        "Overall light or dark appearance.",
        choices=(("system", "System"), ("light", "Light"), ("dark", "Dark")),
        keywords=("dark mode", "light", "appearance", "color"),
    ),
    SettingSpec(
        "title_bar_path_mode",
        "Title bar path",
        "general",
        "choice",
        "Show just the file name or the full path in the title bar.",
        choices=(("name", "File name only"), ("full_path", "Full path")),
        keywords=("title", "path", "filename"),
    ),
    SettingSpec(
        "dirty_title_style",
        "Unsaved-change title style",
        "general",
        "choice",
        "How the title bar marks a document with unsaved changes.",
        choices=(
            ("text", "Text"),
            ("asterisk", "Asterisk"),
            ("asterisk_text", "Asterisk and text"),
        ),
        keywords=("modified", "dirty", "asterisk", "unsaved"),
    ),
    SettingSpec(
        "tray_enabled",
        "Enable system tray mode",
        "general",
        "bool",
        "Keep QUILL available from the system tray.",
        keywords=("tray", "notification area", "minimize"),
    ),
    SettingSpec(
        "show_tab_control",
        "Show tab control",
        "general",
        "bool",
        "Show a tab strip for open documents.",
        keywords=("tabs", "documents"),
    ),
    SettingSpec(
        "start_with_no_document_open",
        "Start with no document open",
        "general",
        "bool",
        "Open to an empty workspace instead of restoring a document.",
        keywords=("startup", "blank", "empty"),
    ),
    SettingSpec(
        "preview_browser",
        "Preview browser",
        "general",
        "text",
        "Which browser opens HTML previews.",
        keywords=("preview", "browser", "html"),
    ),
    SettingSpec(
        "auto_side_preview",
        "Open preview beside the editor",
        "general",
        "bool",
        "Show HTML previews in a side pane instead of a separate window.",
        keywords=("preview", "side", "pane", "html"),
    ),
    SettingSpec(
        "recent_files_limit",
        "Recent files to remember",
        "general",
        "int",
        "How many entries the Recent Files list keeps (1 to 50).",
        minimum=1,
        maximum=50,
        keywords=("recent", "history", "files"),
    ),
    SettingSpec(
        "confirm_destructive_actions",
        "Confirm destructive actions",
        "general",
        "bool",
        "Ask before actions that discard work, such as clearing or overwriting.",
        keywords=("confirm", "prompt", "destructive", "safety"),
    ),
    SettingSpec(
        "default_new_document_format",
        "Default new-document format",
        "general",
        "choice",
        "The format a brand-new document starts in.",
        choices=(
            ("markdown", "Markdown"),
            ("text", "Plain text"),
            ("html", "HTML"),
        ),
        keywords=("new document", "format", "default"),
    ),
    SettingSpec(
        "default_export_preset",
        "Default export preset",
        "general",
        "choice",
        "The format pre-selected in the export dialog.",
        choices=(
            ("html", "HTML"),
            ("markdown", "Markdown"),
            ("pdf", "PDF"),
            ("docx", "Word"),
            ("epub", "EPUB"),
            ("text", "Plain text"),
        ),
        keywords=("export", "preset", "default", "format"),
    ),
    # --- Editing -----------------------------------------------------------
    SettingSpec(
        "soft_wrap",
        "Enable soft wrap",
        "editing",
        "bool",
        "Wrap long lines to the window width.",
        keywords=("wrap", "word wrap", "lines"),
    ),
    SettingSpec(
        "wrap_find",
        "Wrap find searches",
        "editing",
        "bool",
        "Continue a search from the top after reaching the end.",
        keywords=("find", "search", "wrap"),
    ),
    SettingSpec(
        "indent_with_tabs",
        "Indent with tabs",
        "editing",
        "bool",
        "Insert tab characters instead of spaces when indenting.",
        keywords=("tab", "indent", "spaces"),
    ),
    SettingSpec(
        "indent_size",
        "Indent size",
        "editing",
        "int",
        "Number of spaces per indent level (1 to 8).",
        minimum=1,
        maximum=8,
        keywords=("indent", "spaces", "width"),
    ),
    SettingSpec(
        "spellcheck_as_you_type",
        "Spell check as you type",
        "editing",
        "bool",
        "Flag misspellings while you write.",
        feature_id="core.spellcheck",
        keywords=("spelling", "spell check", "typos"),
    ),
    SettingSpec(
        "intellisense_as_you_type",
        "Word prediction and tag IntelliSense",
        "editing",
        "bool",
        "Suggest words and tags while you type.",
        feature_id="core.intellisense",
        keywords=("autocomplete", "prediction", "intellisense"),
    ),
    SettingSpec(
        "snippet_trigger_expansion",
        "Expand snippet triggers while typing",
        "editing",
        "bool",
        "Expand a snippet trigger when you type its delimiter.",
        keywords=("snippet", "expand", "template"),
    ),
    SettingSpec(
        "persistent_undo",
        "Enable persistent undo",
        "editing",
        "bool",
        "Keep undo history across sessions.",
        keywords=("undo", "history", "persistent"),
    ),
    SettingSpec(
        "markdown_clipboard_format",
        "Markdown clipboard format",
        "editing",
        "choice",
        "Format used when copying Markdown with source.",
        choices=(("html", "HTML"), ("rtf", "Rich text")),
        keywords=("clipboard", "copy", "markdown", "format"),
    ),
    SettingSpec(
        "csv_open_mode",
        "How to open CSV files",
        "editing",
        "choice",
        "Open CSV files as plain text, as a grid, or ask each time.",
        choices=(("prompt", "Ask each time"), ("text", "Plain text"), ("grid", "Grid")),
        keywords=("csv", "open", "grid", "table"),
    ),
    SettingSpec(
        "word_open_mode",
        "How to open Word files",
        "editing",
        "choice",
        "Open Word files as plain text, as structured content, or ask each time.",
        choices=(
            ("prompt", "Ask each time"),
            ("text", "Plain text"),
            ("structured", "Structured"),
        ),
        keywords=("word", "docx", "open", "structured"),
    ),
    SettingSpec(
        "autosave_interval_seconds",
        "Autosave interval (seconds)",
        "editing",
        "int",
        "How often the editor autosaves the open document (5 to 600).",
        minimum=5,
        maximum=600,
        keywords=("autosave", "interval", "timing", "save"),
    ),
    SettingSpec(
        "autoformat_smart_quotes",
        "Autoformat straight quotes to curly",
        "editing",
        "bool",
        "Convert straight quotes to typographic quotes while you type.",
        keywords=("autoformat", "quotes", "typography", "smart quotes"),
    ),
    SettingSpec(
        "autoformat_dashes",
        "Autoformat double hyphen to dash",
        "editing",
        "bool",
        "Convert a double hyphen to an en or em dash while you type.",
        keywords=("autoformat", "dash", "hyphen", "typography"),
    ),
    # --- Navigation and QUILL key -----------------------------------------
    SettingSpec(
        "browse_mode_wrap",
        "Wrap QUILL browse navigation",
        "navigation",
        "bool",
        "Wrap to the other end at document boundaries while browsing.",
        feature_id="core.navigate",
        keywords=("browse", "wrap", "navigation"),
    ),
    SettingSpec(
        "browse_mode_feedback",
        "QUILL browse feedback",
        "navigation",
        "choice",
        "How browse-mode movement is signalled.",
        choices=(
            ("speech", "Speech only"),
            ("sound", "Sound only"),
            ("both", "Speech and sound"),
            ("none", "Silent"),
        ),
        feature_id="core.navigate",
        keywords=("browse", "feedback", "sound", "speech"),
    ),
    SettingSpec(
        "browse_mode_preload_cache",
        "Preload QUILL browse cache in background",
        "navigation",
        "bool",
        "Build the navigation cache ahead of first use.",
        feature_id="core.navigate",
        keywords=("browse", "cache", "preload", "quick nav"),
    ),
    SettingSpec(
        "quill_key_timeout_seconds",
        "QUILL key timeout (seconds)",
        "navigation",
        "float",
        "How long the QUILL key prefix and browse mode wait before expiring. 0 means no timeout.",
        minimum=0.0,
        maximum=60.0,
        keywords=("quill key", "timeout", "prefix"),
    ),
    # --- Accessibility -----------------------------------------------------
    SettingSpec(
        "ocr_engine",
        "OCR engine",
        "accessibility",
        "choice",
        "Which engine recognizes text in images. Automatic prefers the built-in "
        "Windows engine and falls back to Tesseract when it is installed.",
        choices=(
            ("auto", "Automatic"),
            ("windows", "Windows (built-in)"),
            ("tesseract", "Tesseract"),
        ),
        feature_id="core.ocr",
        keywords=("ocr", "image", "text", "tesseract", "windows", "recognition"),
    ),
    # --- External file-change watch and safe reload (FEAT-19) --------------
    SettingSpec(
        "external_change_watch_enabled",
        "Watch the open file for external changes",
        "general",
        "bool",
        "Notice when another program changes or deletes the file you are editing "
        "and react safely instead of silently losing or overwriting your work.",
        keywords=("watch", "external", "reload", "file change", "conflict"),
    ),
    SettingSpec(
        "external_change_auto_reload_when_clean",
        "Reload automatically when you have no unsaved edits",
        "general",
        "bool",
        "When the file changes on disk and your buffer is unmodified, reload in "
        "place without moving the cursor. Turn off to be prompted instead.",
        keywords=("reload", "auto", "external", "clean"),
    ),
    SettingSpec(
        "external_change_prompt_on_conflict",
        "Ask before discarding unsaved edits on a conflict",
        "general",
        "bool",
        "When the file changes on disk while you have unsaved edits, offer reload, "
        "keep-mine, or compare. Your text is never overwritten silently.",
        keywords=("conflict", "prompt", "unsaved", "external", "reload"),
    ),
    SettingSpec(
        "external_change_debounce_ms",
        "External-change debounce (milliseconds)",
        "general",
        "int",
        "How long to wait after a change is seen before reacting, so a program "
        "writing a file in several steps is handled once (0 to 10000).",
        minimum=0,
        maximum=10000,
        keywords=("debounce", "external", "timing", "watch"),
    ),
    SettingSpec(
        "quick_nav_debounce_ms",
        "Quick Nav debounce (milliseconds)",
        "navigation",
        "int",
        "How long Quick Nav waits between keystrokes before searching (0 to 2000).",
        minimum=0,
        maximum=2000,
        feature_id="core.navigate",
        keywords=("quick nav", "debounce", "timing"),
    ),
    SettingSpec(
        "quick_nav_min_chars",
        "Quick Nav minimum characters",
        "navigation",
        "int",
        "How many characters Quick Nav needs before it starts matching (1 to 5).",
        minimum=1,
        maximum=5,
        feature_id="core.navigate",
        keywords=("quick nav", "threshold", "characters"),
    ),
    SettingSpec(
        "browse_mode_sticky",
        "Sticky browse mode",
        "navigation",
        "bool",
        "Keep browse mode active after moving instead of returning to editing.",
        feature_id="core.navigate",
        keywords=("browse", "sticky", "navigation"),
    ),
    SettingSpec(
        "quick_nav_include_headings",
        "Include headings in Quick Nav",
        "navigation",
        "bool",
        "Offer headings as Quick Nav targets.",
        feature_id="core.navigate",
        keywords=("quick nav", "headings", "elements"),
    ),
    SettingSpec(
        "quick_nav_include_links",
        "Include links in Quick Nav",
        "navigation",
        "bool",
        "Offer links as Quick Nav targets.",
        feature_id="core.navigate",
        keywords=("quick nav", "links", "elements"),
    ),
    SettingSpec(
        "quick_nav_include_lists",
        "Include lists in Quick Nav",
        "navigation",
        "bool",
        "Offer lists as Quick Nav targets.",
        feature_id="core.navigate",
        keywords=("quick nav", "lists", "elements"),
    ),
    # --- Accessibility -----------------------------------------------------
    SettingSpec(
        "announcement_backend",
        "Announcement backend",
        "accessibility",
        "choice",
        "How spoken status announcements are delivered.",
        choices=(
            ("auto", "Automatic"),
            ("prism", "PRISM bridge"),
            ("status_only", "Status bar only"),
        ),
        feature_id="core.accessibility",
        keywords=("announcement", "screen reader", "speech"),
    ),
    SettingSpec(
        "announcement_trace_enabled",
        "Record announcement trace",
        "accessibility",
        "bool",
        "Log announcements for diagnostics (no document content is captured).",
        feature_id="core.accessibility",
        keywords=("trace", "diagnostics", "announcement"),
    ),
    # --- Read Aloud --------------------------------------------------------
    SettingSpec(
        "announcement_verbosity",
        "Announcement verbosity",
        "accessibility",
        "choice",
        "Overall chattiness of spoken status announcements.",
        choices=(
            ("minimal", "Minimal"),
            ("normal", "Normal"),
            ("verbose", "Verbose"),
        ),
        feature_id="core.accessibility",
        keywords=("verbosity", "announcements", "chatty", "speech"),
    ),
    SettingSpec(
        "announce_wrap",
        "Announce search and navigation wrap",
        "accessibility",
        "bool",
        "Speak a notice when a search or navigation wraps around.",
        feature_id="core.accessibility",
        keywords=("announce", "wrap", "navigation"),
    ),
    SettingSpec(
        "announce_counts",
        "Announce word and character counts",
        "accessibility",
        "bool",
        "Speak word and character counts when they are requested.",
        feature_id="core.accessibility",
        keywords=("announce", "counts", "words"),
    ),
    SettingSpec(
        "announce_mode_changes",
        "Announce mode entry and expiry",
        "accessibility",
        "bool",
        "Speak when a mode such as browse or the QUILL key is entered or expires.",
        feature_id="core.accessibility",
        keywords=("announce", "mode", "browse", "quill key"),
    ),
    SettingSpec(
        "announce_spelling",
        "Announce spelling results",
        "accessibility",
        "bool",
        "Speak spelling feedback such as misspelling counts.",
        feature_id="core.accessibility",
        keywords=("announce", "spelling", "spell check"),
    ),
    SettingSpec(
        "announce_punctuation_level",
        "Spoken punctuation level",
        "accessibility",
        "choice",
        "How much punctuation announcements include.",
        choices=(
            ("none", "None"),
            ("some", "Some"),
            ("most", "Most"),
            ("all", "All"),
        ),
        feature_id="core.accessibility",
        keywords=("punctuation", "announce", "speech"),
    ),
    SettingSpec(
        "announcement_throttle_ms",
        "Announcement throttle (milliseconds)",
        "accessibility",
        "int",
        "Minimum gap between spoken announcements; 0 means no throttle (0 to 2000).",
        minimum=0,
        maximum=2000,
        feature_id="core.accessibility",
        keywords=("throttle", "announcements", "timing"),
    ),
    # --- Read Aloud --------------------------------------------------------
    SettingSpec(
        "read_aloud_engine",
        "Read Aloud engine",
        "read_aloud",
        "choice",
        "Speech engine used for read aloud.",
        choices=(
            ("pyttsx3", "System (pyttsx3)"),
            ("dectalk", "DECtalk"),
            ("piper", "Piper"),
            ("kokoro", "Kokoro"),
            ("espeak", "eSpeak"),
            ("melotts", "MeloTTS"),
            ("chatterbox", "Chatterbox"),
            ("openvoice", "OpenVoice"),
        ),
        feature_id="core.read_aloud",
        keywords=("read aloud", "tts", "voice", "engine"),
    ),
    SettingSpec(
        "read_aloud_rate",
        "Read Aloud rate",
        "read_aloud",
        "int",
        "Words per minute for the system engine (80 to 450).",
        minimum=80,
        maximum=450,
        feature_id="core.read_aloud",
        keywords=("read aloud", "rate", "speed"),
    ),
    SettingSpec(
        "read_aloud_volume",
        "Read Aloud volume",
        "read_aloud",
        "int",
        "Playback volume percentage (0 to 100).",
        minimum=0,
        maximum=100,
        feature_id="core.read_aloud",
        keywords=("read aloud", "volume"),
    ),
    SettingSpec(
        "read_aloud_pitch",
        "Read Aloud pitch",
        "read_aloud",
        "int",
        "Voice pitch (0 to 100).",
        minimum=0,
        maximum=100,
        feature_id="core.read_aloud",
        keywords=("read aloud", "pitch"),
    ),
    SettingSpec(
        "read_aloud_sentence_pause_ms",
        "Read Aloud sentence pause (milliseconds)",
        "read_aloud",
        "int",
        "Extra pause inserted between sentences during read aloud (0 to 2000).",
        minimum=0,
        maximum=2000,
        feature_id="core.read_aloud",
        keywords=("read aloud", "pause", "pacing", "timing"),
    ),
    # --- AI and assistant --------------------------------------------------
    SettingSpec(
        "assistant_enabled",
        "Enable writing assistant",
        "ai",
        "bool",
        "Turn the local writing assistant on.",
        feature_id="future.ai",
        keywords=("assistant", "ai", "writing"),
    ),
    SettingSpec(
        "assistant_prompt_style",
        "Assistant prompt style",
        "ai",
        "choice",
        "The tone the assistant uses.",
        choices=(
            ("balanced", "Balanced"),
            ("concise", "Concise"),
            ("gentle", "Gentle"),
            ("technical", "Technical"),
        ),
        feature_id="future.ai",
        keywords=("assistant", "tone", "style", "prompt"),
    ),
    # --- Transcription -----------------------------------------------------
    SettingSpec(
        "bw_provider_mode",
        "Transcription provider preference",
        "transcription",
        "choice",
        "Prefer on-device or cloud transcription providers.",
        choices=(("local_first", "Local first"), ("cloud_first", "Cloud first")),
        feature_id="core.bw_providers",
        keywords=("transcription", "whisper", "provider", "cloud", "local"),
    ),
    SettingSpec(
        "bw_show_cloud_providers",
        "Show cloud transcription providers",
        "transcription",
        "bool",
        "List cloud providers alongside on-device ones.",
        feature_id="core.bw_providers",
        keywords=("transcription", "cloud", "providers"),
    ),
    SettingSpec(
        "bw_auto_open_status_page_on_download_start",
        "Auto-open Status Page on model download",
        "transcription",
        "bool",
        "Open the Status Page when a speech-model download starts.",
        feature_id="core.bw_transcription",
        keywords=("transcription", "status page", "download"),
    ),
    SettingSpec(
        "status_page_refresh_announcement_cadence",
        "Status page refresh announcements",
        "transcription",
        "choice",
        "How often the Status Page speaks refresh updates.",
        choices=(
            ("quiet", "Quiet"),
            ("normal", "Normal"),
            ("verbose", "Verbose"),
        ),
        feature_id="core.bw_transcription",
        keywords=("status page", "announcements", "cadence"),
    ),
    SettingSpec(
        "bw_safe_mode_lock",
        "BITS Whisperer safe mode lock",
        "transcription",
        "bool",
        "Block download and retry actions while keeping status surfaces.",
        feature_id="core.bw_transcription",
        keywords=("transcription", "safe mode", "lock"),
    ),
    SettingSpec(
        "dictation_sensitivity",
        "Dictation microphone sensitivity",
        "transcription",
        "int",
        "How sensitive dictation is to speech versus silence (0 to 100).",
        feature_id="core.bw_transcription",
        minimum=0,
        maximum=100,
        keywords=("dictation", "sensitivity", "microphone"),
    ),
    SettingSpec(
        "voice_commands_enabled",
        "Hey QUILL voice commands",
        "transcription",
        "bool",
        "Enable Hey QUILL voice commands during dictation (e.g., 'Hey QUILL save file').",
        feature_id="core.voice_commands",
        keywords=("voice commands", "hey quill", "dictation", "speech"),
    ),
    # --- Watch Folders -----------------------------------------------------
    SettingSpec(
        "watch_folder_enabled",
        "Enable folder watching by default",
        "watch",
        "bool",
        "Turn watched-folder automation on when QUILL starts.",
        feature_id="core.watch",
        keywords=("watch", "folder", "automation", "monitor"),
    ),
    SettingSpec(
        "watch_folder_path",
        "Default watch folder",
        "watch",
        "text",
        "Folder to watch for new files when watching is enabled.",
        feature_id="core.watch",
        keywords=("watch", "folder", "path", "directory"),
    ),
    SettingSpec(
        "watch_folder_include_subfolders",
        "Include subfolders",
        "watch",
        "bool",
        "Also watch files inside nested subfolders.",
        feature_id="core.watch",
        keywords=("watch", "subfolders", "recursive"),
    ),
    SettingSpec(
        "watch_folder_process_existing",
        "Process existing files on start",
        "watch",
        "bool",
        "Run actions against files already present when watching begins.",
        feature_id="core.watch",
        keywords=("watch", "existing", "backlog"),
    ),
    SettingSpec(
        "watch_folder_auto_start",
        "Start watching automatically",
        "watch",
        "bool",
        "Begin watching the default folder as soon as QUILL launches.",
        feature_id="core.watch",
        keywords=("watch", "auto start", "startup"),
    ),
    SettingSpec(
        "watch_folder_poll_interval_seconds",
        "Poll interval (seconds)",
        "watch",
        "int",
        "How often the watched folder is checked for changes (2 to 300).",
        feature_id="core.watch",
        minimum=2,
        maximum=300,
        keywords=("watch", "poll", "interval", "seconds"),
    ),
    # --- Updates -----------------------------------------------------------
    SettingSpec(
        "auto_check_updates",
        "Check for updates on startup",
        "updates",
        "bool",
        "Look for a newer release each time QUILL starts.",
        feature_id="core.updates",
        keywords=("updates", "startup", "check"),
    ),
    SettingSpec(
        "beta_updates",
        "Get beta updates",
        "updates",
        "bool",
        "Receive pre-release builds, which may be unstable.",
        feature_id="core.updates",
        keywords=("updates", "beta", "channel", "prerelease"),
    ),
)

_SPECS_BY_KEY: dict[str, SettingSpec] = {spec.key: spec for spec in SETTING_SPECS}

_SETTINGS_FIELD_NAMES: frozenset[str] = frozenset(field.name for field in fields(Settings))


def groups() -> tuple[SettingGroup, ...]:
    """Return the ordered settings groups."""
    return SETTING_GROUPS


def specs() -> tuple[SettingSpec, ...]:
    """Return every registered setting spec, in declaration order."""
    return SETTING_SPECS


def specs_for_group(group_id: str) -> list[SettingSpec]:
    """Return the specs that belong to ``group_id``, in declaration order."""
    return [spec for spec in SETTING_SPECS if spec.group == group_id]


def find_spec(key: str) -> SettingSpec | None:
    """Return the spec for ``key`` or ``None`` when it is not registered."""
    return _SPECS_BY_KEY.get(key)


def search_specs(query: str) -> list[SettingSpec]:
    """Return specs whose label, key, description, keywords, or group title match.

    The match is case-insensitive and substring-based. An empty query returns
    every spec so the caller can show the full list.
    """
    needle = query.strip().lower()
    if not needle:
        return list(SETTING_SPECS)
    group_titles = {group.id: group.title.lower() for group in SETTING_GROUPS}
    matches: list[SettingSpec] = []
    for spec in SETTING_SPECS:
        haystack = " ".join((
            spec.label.lower(),
            spec.key.lower(),
            spec.description.lower(),
            group_titles.get(spec.group, ""),
            " ".join(keyword.lower() for keyword in spec.keywords),
        ))
        if needle in haystack:
            matches.append(spec)
    return matches


def default_value(key: str) -> object:
    """Return the factory default for ``key`` from a fresh :class:`Settings`."""
    return getattr(Settings(), key)


def get_value(settings: Settings, key: str) -> object:
    """Return the current value of ``key`` on ``settings``."""
    return getattr(settings, key)


def set_value(settings: Settings, key: str, value: object) -> Settings:
    """Return a new, normalized :class:`Settings` with ``key`` set to ``value``.

    Validation and clamping reuse :meth:`Settings.from_dict`, so out-of-range or
    invalid values are corrected exactly as they would be when loading a file.
    Unknown keys raise :class:`KeyError`.
    """
    if key not in _SETTINGS_FIELD_NAMES:
        raise KeyError(key)
    data = asdict(settings)
    data[key] = value
    return Settings.from_dict(data)


def reset_setting(settings: Settings, key: str) -> Settings:
    """Return a new :class:`Settings` with ``key`` reset to its factory default."""
    return set_value(settings, key, default_value(key))


def reset_all() -> Settings:
    """Return a fresh, all-defaults :class:`Settings` (SET-7 reset to defaults)."""
    return Settings()


def export_settings(settings: Settings) -> dict[str, object]:
    """Return a documented, versioned export of the full configuration.

    Shape::

        {"schema_version": 1, "settings": {<field>: <value>, ...}}

    Every :class:`Settings` field is included so the export is a complete,
    portable snapshot (SET-7).
    """
    return {"schema_version": SCHEMA_VERSION, "settings": asdict(settings)}


def import_settings(raw: object) -> Settings:
    """Build a validated :class:`Settings` from an exported document.

    Accepts either the wrapped ``{"schema_version", "settings"}`` shape or a
    bare settings mapping. Unknown keys are ignored and every value is
    normalized through :meth:`Settings.from_dict`, so a malformed or partial
    import never produces an invalid configuration.
    """
    if not isinstance(raw, dict):
        return Settings()
    payload = raw.get("settings", raw)
    if not isinstance(payload, dict):
        return Settings()
    filtered = {
        str(key): value for key, value in payload.items() if str(key) in _SETTINGS_FIELD_NAMES
    }
    return Settings.from_dict(filtered)
